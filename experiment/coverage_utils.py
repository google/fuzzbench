# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Utility functions for coverage report generation."""

import os
import multiprocessing
import json

from common import experiment_utils as exp_utils
from common import new_process
from common import benchmark_utils
from common import fuzzer_utils
from common import logs
from common import filestore_utils
from common import filesystem
from database import utils as db_utils
from database import models
from experiment.build import build_utils

logger = logs.Logger('coverage_utils')  # pylint: disable=invalid-name

COV_DIFF_QUEUE_GET_TIMEOUT = 1


def get_coverage_info_dir():
    """Returns the directory to store coverage information including
    coverage report and json summary file."""
    work_dir = exp_utils.get_work_dir()
    return os.path.join(work_dir, 'coverage')


def upload_coverage_info_to_bucket():
    """Copies the coverage reports and json summary files to gcs bucket."""
    src_dir = get_coverage_info_dir()
    dst_dir = exp_utils.get_experiment_filestore_path()
    filestore_utils.cp(src_dir, dst_dir, recursive=True, parallel=True)


def generate_all_coverage_info(experiment_config: dict):
    """Generates coverage reports and summary json file
    for each benchmark and fuzzer."""
    logger.info('Start generating coverage report for benchmarks.')
    benchmarks = experiment_config['benchmarks'].split(',')
    fuzzers = experiment_config['fuzzers'].split(',')
    experiment = experiment_config['experiment']
    with multiprocessing.Pool() as pool:
        generate_coverage_info_args = [(experiment, benchmark, fuzzer)
                                       for benchmark in benchmarks
                                       for fuzzer in fuzzers]
        pool.starmap(generate_coverage_info, generate_coverage_info_args)
    logger.info('Finished generating coverage report.')


def generate_coverage_info(experiment, benchmark, fuzzer):
    """Generates the coverage report and summary json file
    for one pair of benchmark and fuzzer."""
    logs.initialize()
    logger.info('Generating coverage report for benchmark: {benchmark} \
                fuzzer: {fuzzer}.'.format(benchmark=benchmark, fuzzer=fuzzer))
    generator = CoverageReporter(fuzzer, benchmark, experiment)
    # Merge all the profdata files.
    generator.merge_profdata_files()
    # Generate the json file based on merged profdata file.
    generator.generate_merged_json_summary()
    # Generate the reports using llvm-cov.
    generator.generate_cov_report()
    # Post process the report.
    generator.post_process_report()
    # Generate the json file to store all coverage data.
    generator.generate_coverage_data_json_file()

    logger.info('Finished generating coverage report for '
                'benchmark:{benchmark} fuzzer:{fuzzer}.'.format(
                    benchmark=benchmark, fuzzer=fuzzer))


class CoverageReporter:  # pylint: disable=too-many-instance-attributes
    """Class used to generate coverage report for a pair of
    fuzzer and benchmark."""

    # pylint: disable=too-many-arguments
    def __init__(self, fuzzer, benchmark, experiment):
        self.fuzzer = fuzzer
        self.benchmark = benchmark
        self.experiment = experiment
        self.trial_ids = get_trial_ids(experiment, fuzzer, benchmark)
        cov_report_directory = get_coverage_report_dir()
        self.report_dir = os.path.join(cov_report_directory, benchmark, fuzzer)
        coverage_info_dir = get_coverage_info_dir()
        self.json_file_dir = os.path.join(coverage_info_dir, 'data', benchmark,
                                          fuzzer)
        self.json_file = os.path.join(self.json_file_dir,
                                      'covered_regions.json')
        benchmark_fuzzer_dir = exp_utils.get_benchmark_fuzzer_dir(
            benchmark, fuzzer)
        work_dir = exp_utils.get_work_dir()
        benchmark_fuzzer_measurement_dir = os.path.join(work_dir,
                                                        'measurement-folders',
                                                        benchmark_fuzzer_dir)
        self.merged_profdata_file = os.path.join(
            benchmark_fuzzer_measurement_dir, 'merged.profdata')
        self.merged_json_summary_file = os.path.join(
            benchmark_fuzzer_measurement_dir, 'merged.json')
        coverage_binaries_dir = build_utils.get_coverage_binaries_dir()
        self.source_files_dir = os.path.join(coverage_binaries_dir, benchmark)
        self.binary_file = get_coverage_binary(benchmark)

    def merge_profdata_files(self):
        """Merge profdata files from |src_files| to |dst_files|."""
        files_to_merge = [
            TrialCoverage(self.fuzzer, self.benchmark, trial_id).profdata_file
            for trial_id in self.trial_ids
        ]
        result = merge_profdata_files(files_to_merge, self.merged_profdata_file)
        if result.retcode != 0:
            logger.error('Profdata files merging failed.')

    def generate_cov_report(self):
        """Generates the coverage report."""
        command = [
            'llvm-cov', 'show', '-format=html',
            '-path-equivalence=/,{prefix}'.format(prefix=self.source_files_dir),
            '-output-dir={dst_dir}'.format(dst_dir=self.report_dir),
            '-Xdemangler', 'c++filt', '-Xdemangler', '-n', self.binary_file,
            '-instr-profile={profdata}'.format(
                profdata=self.merged_profdata_file)
        ]
        result = new_process.execute(command)
        if result.retcode != 0:
            logger.error('Coverage report generation failed for '
                         'fuzzer: {fuzzer},benchmark: {benchmark}.'.format(
                             fuzzer=self.fuzzer, benchmark=self.benchmark))

    def generate_merged_json_summary(self):
        """Generates the json summary file."""
        coverage_binary = get_coverage_binary(self.benchmark)
        result = generate_json_summary(coverage_binary,
                                       self.merged_profdata_file,
                                       self.merged_json_summary_file,
                                       summary_only=False)
        if result.retcode != 0:
            logger.error(
                'Merged coverage summary json file generation failed for '
                'fuzzer: {fuzzer},benchmark: {benchmark}.'.format(
                    fuzzer=self.fuzzer, benchmark=self.benchmark))

    def post_process_report(self):
        """Posts process the html report to generate hierarchical directory."""
        command = [
            'python3', '/opt/code_coverage/coverage_utils.py', '-v',
            'post_process', '-src-root-dir=/',
            '-summary-file={json_file}'.format(
                json_file=self.merged_json_summary_file),
            '-output-dir={report_dir}'.format(report_dir=self.report_dir),
            '-path-equivalence=/,{prefix}'.format(prefix=self.source_files_dir)
        ]
        result = new_process.execute(command)
        if result.retcode != 0:
            logger.error('Coverage report post process failed for '
                         'fuzzer: {fuzzer},benchmark: {benchmark}.'.format(
                             fuzzer=self.fuzzer, benchmark=self.benchmark))

    def generate_coverage_data_json_file(self):
        """Stores the coverage data in a json file."""
        covered_regions = extract_coverage_from_json(
            self.merged_json_summary_file)
        json_src_dir = self.json_file_dir
        filesystem.create_directory(json_src_dir)
        with open(self.json_file, 'w') as src_file:
            json.dump(covered_regions, src_file)


def get_coverage_archive_name(benchmark):
    """Gets the archive name for |benchmark|."""
    return 'coverage-build-%s.tar.gz' % benchmark


def get_profdata_file_name(trial_id):
    """Returns the profdata file name for |trial_id|."""
    return 'data-{id}.profdata'.format(id=trial_id)


def get_coverage_report_dir():
    """Returns the directory to store all the coverage reports."""
    coverage_info_dir = get_coverage_info_dir()
    return os.path.join(coverage_info_dir, 'reports')


def get_coverage_binary(benchmark: str) -> str:
    """Gets the coverage binary for benchmark."""
    coverage_binaries_dir = build_utils.get_coverage_binaries_dir()
    fuzz_target = benchmark_utils.get_fuzz_target(benchmark)
    return fuzzer_utils.get_fuzz_target_binary(coverage_binaries_dir /
                                               benchmark,
                                               fuzz_target_name=fuzz_target)


def get_trial_ids(experiment: str, fuzzer: str, benchmark: str):
    """Gets ids of all finished trials for a pair of fuzzer and benchmark."""
    trial_ids = [
        trial_id_tuple[0]
        for trial_id_tuple in db_utils.query(models.Trial.id).filter(
            models.Trial.experiment == experiment, models.Trial.fuzzer ==
            fuzzer, models.Trial.benchmark == benchmark,
            ~models.Trial.preempted)
    ]
    return trial_ids


def merge_profdata_files(src_files, dst_file):
    """Uses llvm-profdata to merge |src_files| to |dst_files|."""
    command = ['llvm-profdata', 'merge', '-sparse']
    command.extend(src_files)
    command.extend(['-o', dst_file])
    result = new_process.execute(command, expect_zero=False)
    return result


def get_coverage_infomation(coverage_summary_file):
    """Reads the coverage information from |coverage_summary_file|
    and skip possible warnings in the file."""
    with open(coverage_summary_file) as summary:
        return json.loads(summary.readlines()[-1])


class TrialCoverage:  # pylint: disable=too-many-instance-attributes
    """Base class for storing and getting coverage data for a trial."""

    def __init__(self, fuzzer: str, benchmark: str, trial_num: int):
        self.fuzzer = fuzzer
        self.benchmark = benchmark
        self.trial_num = trial_num
        self.benchmark_fuzzer_trial_dir = exp_utils.get_trial_dir(
            fuzzer, benchmark, trial_num)
        self.work_dir = exp_utils.get_work_dir()
        self.measurement_dir = os.path.join(self.work_dir,
                                            'measurement-folders',
                                            self.benchmark_fuzzer_trial_dir)
        self.report_dir = os.path.join(self.measurement_dir, 'reports')

        # Store the profdata file for the current trial.
        self.profdata_file = os.path.join(self.report_dir, 'data.profdata')


def generate_json_summary(coverage_binary,
                          profdata_file,
                          output_file,
                          summary_only=True):
    """Generate the json summary file from |coverage_binary|
    and |profdata_file|."""
    command = [
        'llvm-cov', 'export', '-format=text', coverage_binary,
        '-instr-profile=%s' % profdata_file
    ]

    if summary_only:
        command.append('-summary-only')

    with open(output_file, 'w') as dst_file:
        result = new_process.execute(command,
                                     output_file=dst_file,
                                     expect_zero=False)
    return result


def extract_coverage_from_json(json_file):
    """Get the covered regions for the current trial."""
    covered_regions = set()
    try:
        coverage_info = get_coverage_infomation(json_file)
        functions_data = coverage_info['data'][0]['functions']
        # The fourth number in the region-list indicates if the region
        # is hit.
        hit_index = 4
        # The last number in the region-list indicates what type of the
        # region it is; 'code_region' is used to obtain various code
        # coverage statistic and is represented by number 0.
        type_index = -1
        # The number of index 5 represents the file number.
        file_index = 5
        for function_data in functions_data:
            for region in function_data['regions']:
                if region[hit_index] != 0 and region[type_index] == 0:
                    covered_regions.add(
                        tuple(region[:hit_index] + region[file_index:]))
    except Exception:  # pylint: disable=broad-except
        logger.error('Coverage summary json file defective or missing.')
    return covered_regions
