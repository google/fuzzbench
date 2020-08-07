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
import queue

from common import experiment_utils as exp_utils
from common import new_process
from common import benchmark_utils
from common import fuzzer_utils
from common import logs
from common import filestore_utils
from common import experiment_path as exp_path
from common import filesystem
from database import utils as db_utils
from database import models
from experiment.build import build_utils
from experiment import reporter

logger = logs.Logger('coverage_utils')  # pylint: disable=invalid-name

COV_DIFF_QUEUE_GET_TIMEOUT = 1


def update_coverage_to_bucket():
    """Copies the coverage reports to gcs bucket."""
    report_dir = reporter.get_reports_dir()
    src_dir = get_coverage_report_dir()
    dst_dir = exp_path.filestore(report_dir)
    filestore_utils.cp(src_dir, dst_dir, recursive=True, parallel=True)


def generate_cov_reports(experiment_config: dict):
    """Generates coverage reports for each benchmark and fuzzer."""
    logger.info('Start generating coverage report for benchmarks.')
    benchmarks = experiment_config['benchmarks'].split(',')
    fuzzers = experiment_config['fuzzers'].split(',')
    experiment = experiment_config['experiment']
    with multiprocessing.Pool() as pool:
        generate_cov_report_args = [(experiment, benchmark, fuzzer)
                                    for benchmark in benchmarks
                                    for fuzzer in fuzzers]
        pool.starmap(generate_cov_report, generate_cov_report_args)
        pool.close()
        pool.join()
    logger.info('Finished generating coverage report.')


def generate_cov_report(experiment, benchmark, fuzzer):
    """Generates the coverage report for one pair of benchmark and fuzzer."""
    logs.initialize()
    logger.info('Generating coverage report for benchmark: {benchmark} \
                fuzzer: {fuzzer}.'.format(benchmark=benchmark, fuzzer=fuzzer))
    generator = CoverageReporter(fuzzer, benchmark, experiment)
    # Merges all the profdata files.
    generator.merge_profdata_files()
    # Generates the reports using llvm-cov.
    generator.generate_cov_report()

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
        benchmark_fuzzer_dir = exp_utils.get_benchmark_fuzzer_dir(
            benchmark, fuzzer)
        work_dir = exp_utils.get_work_dir()
        self.merged_profdata_file = os.path.join(work_dir,
                                                 'measurement-folders',
                                                 benchmark_fuzzer_dir,
                                                 'merged.profdata')
        coverage_binaries_dir = build_utils.get_coverage_binaries_dir()
        self.source_files = os.path.join(coverage_binaries_dir, benchmark,
                                         'src')
        self.binary_file = get_coverage_binary(benchmark)

    def merge_profdata_files(self):
        """Merge profdata files from |src_files| to |dst_files|."""
        logger.info('Merging profdata for fuzzer: '
                    '{fuzzer},benchmark: {benchmark}.'.format(
                        fuzzer=self.fuzzer, benchmark=self.benchmark))
        files_to_merge = [
            TrialCoverage(self.fuzzer, self.benchmark, trial_id,
                          logger).profdata_file for trial_id in self.trial_ids
        ]
        result = merge_profdata_files(files_to_merge, self.merged_profdata_file)
        if result != 0:
            logger.error('Profdata files merging failed.')

    def generate_cov_report(self):
        """Generates the coverage report."""
        command = [
            'llvm-cov', 'show', '-format=html',
            '-path-equivalence=/,{prefix}'.format(prefix=self.source_files),
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


def get_coverage_archive_name(benchmark):
    """Gets the archive name for |benchmark|."""
    return 'coverage-build-%s.tar.gz' % benchmark


def get_experiment_folders_dir():
    """Returns experiment folders directory."""
    return exp_path.path('experiment-folders')


def get_fuzzer_benchmark_key(fuzzer: str, benchmark: str):
    """Returns the key in coverage dict for a pair of fuzzer-benchmark."""
    return fuzzer + ' ' + benchmark


def get_profdata_file_name(trial_id):
    """Returns the profdata file name for |trial_id|."""
    return 'data-{id}.profdata'.format(id=trial_id)


def get_coverage_report_dir():
    """Returns the directory to store all the coverage reports."""
    report_dir = reporter.get_reports_dir()
    return os.path.join(report_dir, 'coverage')


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
    return result.retcode


def get_coverage_infomation(coverage_summary_file):
    """Reads the coverage information from |coverage_summary_file|
    and skip possible warnings in the file."""
    with open(coverage_summary_file) as summary:
        return json.loads(summary.readlines()[-1])


def store_coverage_data(experiment_config: dict):
    """Generates the specific coverage data and store in cloud bucket."""
    logger.info('Start storing coverage data')
    with multiprocessing.Pool() as pool, multiprocessing.Manager() as manager:
        q = manager.Queue()  # pytype: disable=attribute-error
        covered_regions = get_all_covered_regions(experiment_config, pool, q)
        json_src_dir = reporter.get_reports_dir()
        filesystem.recreate_directory(json_src_dir)
        json_src = os.path.join(json_src_dir, 'covered_regions.json')
        with open(json_src, 'w') as src_file:
            json.dump(covered_regions, src_file)
        json_dst = exp_path.filestore(json_src)
        filestore_utils.cp(json_src, json_dst)

    logger.info('Finished storing coverage data')


def get_all_covered_regions(experiment_config: dict, pool, q) -> dict:
    """Gets regions covered for each pair for fuzzer and benchmark."""
    logger.info('Measuring all fuzzer-benchmark pairs for final coverage data.')

    benchmarks = experiment_config['benchmarks'].split(',')
    fuzzers = experiment_config['fuzzers'].split(',')
    experiment = experiment_config['experiment']

    get_covered_region_args = [(experiment, fuzzer, benchmark, q)
                               for fuzzer in fuzzers
                               for benchmark in benchmarks]

    result = pool.starmap_async(get_covered_region, get_covered_region_args)

    # Poll the queue for covered region data and save them in a dict until the
    # pool is done processing each combination of fuzzers and benchmarks.
    all_covered_regions = {}

    while True:
        try:
            covered_regions = q.get(timeout=COV_DIFF_QUEUE_GET_TIMEOUT)
            all_covered_regions.update(covered_regions)
        except queue.Empty:
            if result.ready():
                # If "ready" that means pool has finished. Since it is
                # finished and the queue is empty, we can stop checking
                # the queue for more covered regions.
                logger.debug(
                    'Finished call to map with get_all_covered_regions.')
                break

    for key in all_covered_regions:
        all_covered_regions[key] = list(all_covered_regions[key])
    logger.info('Done measuring all coverage data.')
    return all_covered_regions


def get_covered_region(experiment: str, fuzzer: str, benchmark: str,
                       q: multiprocessing.Queue):
    """Gets the final covered region for a specific pair of fuzzer-benchmark."""
    logs.initialize()
    logger.debug('Measuring covered region: fuzzer: %s, benchmark: %s.', fuzzer,
                 benchmark)
    key = get_fuzzer_benchmark_key(fuzzer, benchmark)
    covered_regions = {key: set()}
    trial_ids = get_trial_ids(experiment, fuzzer, benchmark)
    for trial_id in trial_ids:
        logger.info('Measuring covered region: trial_id = %d.', trial_id)
        snapshot_logger = logs.Logger('measurer',
                                      default_extras={
                                          'fuzzer': fuzzer,
                                          'benchmark': benchmark,
                                          'trial_id': str(trial_id),
                                      })
        trial_coverage = TrialCoverage(fuzzer, benchmark, trial_id,
                                       snapshot_logger)
        trial_coverage.generate_summary(0, summary_only=False)
        new_covered_regions = trial_coverage.get_current_covered_regions()
        covered_regions[key] = covered_regions[key].union(new_covered_regions)
    q.put(covered_regions)
    logger.debug('Done measuring covered region: fuzzer: %s, benchmark: %s.',
                 fuzzer, benchmark)


class TrialCoverage:  # pylint: disable=too-many-instance-attributes
    """Base class for storing and getting coverage data for a trial."""

    def __init__(self, fuzzer: str, benchmark: str, trial_num: int,
                 trial_logger: logs.Logger):
        self.fuzzer = fuzzer
        self.benchmark = benchmark
        self.trial_num = trial_num
        self.logger = trial_logger
        self.benchmark_fuzzer_trial_dir = exp_utils.get_trial_dir(
            fuzzer, benchmark, trial_num)
        self.work_dir = exp_utils.get_work_dir()
        self.measurement_dir = os.path.join(self.work_dir,
                                            'measurement-folders',
                                            self.benchmark_fuzzer_trial_dir)
        self.report_dir = os.path.join(self.measurement_dir, 'reports')

        # Store the profdata file for the current trial.
        self.profdata_file = os.path.join(self.report_dir, 'data.profdata')

        # Store the coverage information in json form.
        self.cov_summary_file = os.path.join(self.report_dir,
                                             'cov_summary.json')

    def get_current_covered_regions(self):
        """Get the covered regions for the current trial."""
        covered_regions = set()
        try:
            coverage_info = get_coverage_infomation(self.cov_summary_file)
            functions_data = coverage_info['data'][0]['functions']
            # The fourth number in the region-list indicates if the region
            # is hit.
            hit_index = 4
            # The last number in the region-list indicates what type of the
            # region it is; 'code_region' is used to obtain various code
            # coverage statistic and is represented by number 0.
            type_index = -1
            for function_data in functions_data:
                for region in function_data['regions']:
                    if region[hit_index] != 0 and region[type_index] == 0:
                        covered_regions.add(tuple(region[:hit_index]))
        except Exception:  # pylint: disable=broad-except
            self.logger.error(
                'Coverage summary json file defective or missing.')
        return covered_regions

    def generate_summary(self, cycle: int, summary_only=True):
        """Transforms the .profdata file into json form."""
        coverage_binary = get_coverage_binary(self.benchmark)
        command = [
            'llvm-cov', 'export', '-format=text', coverage_binary,
            '-instr-profile=%s' % self.profdata_file
        ]

        if summary_only:
            command.append('-summary-only')

        with open(self.cov_summary_file, 'w') as output_file:
            result = new_process.execute(command,
                                         output_file=output_file,
                                         expect_zero=False)
        if result.retcode != 0:
            self.logger.error(
                'Coverage summary json file generation failed for \
                    cycle: %d.', cycle)
            if cycle != 0:
                self.logger.error(
                    'Coverage summary json file generation failed for \
                        cycle: %d.', cycle)
            else:
                self.logger.error(
                    'Coverage summary json file generation failed in the end.')
