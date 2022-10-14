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
import json

from common import experiment_path as exp_path
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


def generate_coverage_reports(experiment_config: dict):
    """Generates coverage reports for each benchmark and fuzzer."""
    logs.initialize()
    logger.info('Start generating coverage reports.')

    benchmarks = experiment_config['benchmarks']
    fuzzers = experiment_config['fuzzers']
    experiment = experiment_config['experiment']
    region_coverage = experiment_config['region_coverage']

    for benchmark in benchmarks:
        for fuzzer in fuzzers:
            generate_coverage_report(experiment, benchmark, fuzzer,
                                     region_coverage)

    logger.info('Finished generating coverage reports.')


def generate_coverage_report(experiment, benchmark, fuzzer, region_coverage):
    """Generates the coverage report for one pair of benchmark and fuzzer."""
    logger.info(
        ('Generating coverage report for '
         'benchmark: {benchmark} fuzzer: {fuzzer}.').format(benchmark=benchmark,
                                                            fuzzer=fuzzer))

    try:
        coverage_reporter = CoverageReporter(experiment, fuzzer, benchmark,
                                             region_coverage)

        # Merges all the profdata files.
        coverage_reporter.merge_profdata_files()

        # Generate the coverage summary json file based on merged profdata file.
        coverage_reporter.generate_coverage_summary_json()

        # Generate the coverage branches json file.
        coverage_reporter.generate_coverage_branches_json()

        # Generates the html reports using llvm-cov.
        coverage_reporter.generate_coverage_report()

        logger.info('Finished generating coverage report.')
    except Exception:  # pylint: disable=broad-except
        logger.error('Error occurred when generating coverage report.')


class CoverageReporter:  # pylint: disable=too-many-instance-attributes
    """Class used to generate coverage report for a pair of
    fuzzer and benchmark."""

    # pylint: disable=too-many-arguments
    def __init__(self, experiment, fuzzer, benchmark, region_coverage):
        self.fuzzer = fuzzer
        self.benchmark = benchmark
        self.experiment = experiment
        self.trial_ids = get_trial_ids(experiment, fuzzer, benchmark)
        self.region_coverage = region_coverage

        coverage_info_dir = get_coverage_info_dir()
        self.report_dir = os.path.join(coverage_info_dir, 'reports', benchmark,
                                       fuzzer)
        self.data_dir = os.path.join(coverage_info_dir, 'data', benchmark,
                                     fuzzer)

        benchmark_fuzzer_dir = exp_utils.get_benchmark_fuzzer_dir(
            benchmark, fuzzer)
        work_dir = exp_utils.get_work_dir()

        benchmark_fuzzer_measurement_dir = os.path.join(work_dir,
                                                        'measurement-folders',
                                                        benchmark_fuzzer_dir)
        self.merged_profdata_file = os.path.join(
            benchmark_fuzzer_measurement_dir, 'merged.profdata')
        self.merged_summary_json_file = os.path.join(
            benchmark_fuzzer_measurement_dir, 'merged.json')

        coverage_binaries_dir = build_utils.get_coverage_binaries_dir()
        self.source_files_dir = os.path.join(coverage_binaries_dir, benchmark)
        self.binary_file = get_coverage_binary(benchmark)

    def merge_profdata_files(self):
        """Merge profdata files from |src_files| to |dst_files|."""
        logger.info('Merging profdata for fuzzer: '
                    '{fuzzer},benchmark: {benchmark}.'.format(
                        fuzzer=self.fuzzer, benchmark=self.benchmark))

        files_to_merge = []
        for trial_id in self.trial_ids:
            profdata_file = TrialCoverage(self.fuzzer, self.benchmark,
                                          trial_id).profdata_file
            if not os.path.exists(profdata_file):
                continue
            files_to_merge.append(profdata_file)

        result = merge_profdata_files(files_to_merge, self.merged_profdata_file)
        if result.retcode != 0:
            logger.error('Profdata files merging failed.')

    def generate_coverage_summary_json(self):
        """Generates the coverage summary json from merged profdata file."""
        coverage_binary = get_coverage_binary(self.benchmark)
        result = generate_json_summary(coverage_binary,
                                       self.merged_profdata_file,
                                       self.merged_summary_json_file,
                                       summary_only=False)
        if result.retcode != 0:
            logger.error(
                'Merged coverage summary json file generation failed for '
                'fuzzer: {fuzzer},benchmark: {benchmark}.'.format(
                    fuzzer=self.fuzzer, benchmark=self.benchmark))

    def generate_coverage_report(self):
        """Generates the coverage report and stores in bucket."""
        command = [
            'llvm-cov', 'show', '-format=html',
            '-path-equivalence=/,{prefix}'.format(prefix=self.source_files_dir),
            '-output-dir={dst_dir}'.format(dst_dir=self.report_dir),
            '-Xdemangler', 'c++filt', '-Xdemangler', '-n', self.binary_file,
            '-instr-profile={profdata}'.format(
                profdata=self.merged_profdata_file)
        ]
        result = new_process.execute(command, expect_zero=False)
        if result.retcode != 0:
            logger.error('Coverage report generation failed for '
                         'fuzzer: {fuzzer},benchmark: {benchmark}.'.format(
                             fuzzer=self.fuzzer, benchmark=self.benchmark))
            return

        src_dir = self.report_dir
        dst_dir = exp_path.filestore(self.report_dir)
        filestore_utils.cp(src_dir, dst_dir, recursive=True, parallel=True)

    def generate_coverage_branches_json(self):
        """Stores the coverage data in a json file."""
        if self.region_coverage:
            edges_covered = extract_covered_regions_from_summary_json(
                self.merged_summary_json_file)
        else:
            edges_covered = extract_covered_branches_from_summary_json(
                self.merged_summary_json_file)
        coverage_json_src = os.path.join(self.data_dir, 'covered_branches.json')
        coverage_json_dst = exp_path.filestore(coverage_json_src)
        filesystem.create_directory(self.data_dir)
        with open(coverage_json_src, 'w') as file_handle:
            json.dump(edges_covered, file_handle)
        filestore_utils.cp(coverage_json_src,
                           coverage_json_dst,
                           expect_zero=False)


def get_coverage_archive_name(benchmark):
    """Gets the archive name for |benchmark|."""
    return 'coverage-build-%s.tar.gz' % benchmark


def get_profdata_file_name(trial_id):
    """Returns the profdata file name for |trial_id|."""
    return 'data-{id}.profdata'.format(id=trial_id)


def get_coverage_binary(benchmark: str) -> str:
    """Gets the coverage binary for benchmark."""
    coverage_binaries_dir = build_utils.get_coverage_binaries_dir()
    fuzz_target = benchmark_utils.get_fuzz_target(benchmark)
    return fuzzer_utils.get_fuzz_target_binary(coverage_binaries_dir /
                                               benchmark,
                                               fuzz_target_name=fuzz_target)


def get_trial_ids(experiment: str, fuzzer: str, benchmark: str):
    """Gets ids of all finished trials for a pair of fuzzer and benchmark."""
    with db_utils.session_scope() as session:
        trial_ids = [
            trial_id_tuple[0]
            for trial_id_tuple in session.query(models.Trial.id).filter(
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
    """Generates the json summary file from |coverage_binary|
    and |profdata_file|."""
    command = [
        'llvm-cov', 'export', '-format=text', '-num-threads=1',
        '-region-coverage-gt=0', '-skip-expansions', coverage_binary,
        '-instr-profile=%s' % profdata_file
    ]

    if summary_only:
        command.append('-summary-only')

    with open(output_file, 'w') as dst_file:
        result = new_process.execute(command,
                                     output_file=dst_file,
                                     expect_zero=False)
    return result


def extract_covered_branches_from_summary_json(summary_json_file):
    """Returns the covered branches given a coverage summary json file."""
    covered_branches = []
    try:
        coverage_info = get_coverage_infomation(summary_json_file)
        functions_data = coverage_info['data'][0]['functions']

        # The fourth and the fifth item tell whether the branch is evaluated to
        # true or false respectively.
        hit_true_index = 4
        hit_false_index = 5
        # The last number in the branch-list indicates what type of the
        # region it is; 'branch_region' is represented by number 4.
        type_index = -1
        branch_region_type = 4
        # The number of index 6 represents the file number.
        file_index = 6
        for function_data in functions_data:
            for branch in function_data['branches']:
                if branch[hit_true_index] != 0 or branch[
                        hit_false_index] != 0 and branch[
                            type_index] == branch_region_type:
                    covered_branches.append(branch[:hit_true_index] +
                                            branch[file_index:])

    except Exception:  # pylint: disable=broad-except
        logger.error('Coverage summary json file defective or missing.')
    return covered_branches


def extract_covered_regions_from_summary_json(summary_json_file):
    """Returns the covered regions given a coverage summary json file."""
    covered_regions = []
    try:
        coverage_info = get_coverage_infomation(summary_json_file)
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
                    covered_regions.append(region[:hit_index] +
                                           region[file_index:])
    except Exception:  # pylint: disable=broad-except
        logger.error('Coverage summary json file defective or missing.')
    return covered_regions
