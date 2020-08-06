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
import tarfile
import posixpath

from common import filesystem
from common import experiment_utils
from common import new_process
from common import benchmark_utils
from common import fuzzer_utils
from common import logs
from common import filestore_utils
from experiment import measurer

logger = logs.Logger('coverage_utils')  # pylint: disable=invalid-name


def generate_cov_reports(experiments, benchmarks, fuzzers, report_dir):
    """Generate coverage reports for each benchmark and fuzzer."""
    logger.info('Start generating coverage report for benchmarks.')
    set_up_coverage_files(experiments, report_dir, benchmarks)
    with multiprocessing.Pool() as pool:
        generate_cov_report_args = [(experiments, benchmark, fuzzer, report_dir)
                                    for benchmark in benchmarks
                                    for fuzzer in fuzzers]
        pool.starmap(generate_cov_report, generate_cov_report_args)
        pool.close()
        pool.join()
    logger.info('Finished generating coverage report.')


def generate_cov_report(experiments, benchmark, fuzzer, report_dir):
    """Generate the coverage report for one pair of benchmark and fuzzer."""
    logs.initialize()
    logger.info('Generating coverage report for benchmark: {benchmark} \
                fuzzer: {fuzzer}.'.format(benchmark=benchmark, fuzzer=fuzzer))
    generator = CoverageReporter(fuzzer, benchmark, experiments, report_dir,
                                 logger)
    # Gets and merges all the profdata files.
    generator.fetch_profdata_file()
    generator.merge_profdata_files()
    # Generates the reports using llvm-cov.
    generator.generate_cov_report()

    logger.info('Finished generating coverage report for '
                'benchmark:{benchmark} fuzzer:{fuzzer}.'.format(
                    benchmark=benchmark, fuzzer=fuzzer))


def set_up_coverage_files(experiment_names, report_dir, benchmarks):
    """Sets up coverage files for all benchmarks."""
    with multiprocessing.Pool() as pool:
        set_up_coverage_file_args = [(experiment_names, report_dir, benchmark)
                                     for benchmark in benchmarks]
        pool.starmap(set_up_coverage_file, set_up_coverage_file_args)
        pool.close()
        pool.join()


def set_up_coverage_file(experiment_names, report_dir, benchmark):
    """Sets up coverage files for |benchmark|."""
    logs.initialize()
    logger.info('Started setting up coverage file for'
                'benchmark: {benchmark}'.format(benchmark=benchmark))
    for experiment in experiment_names:
        archive_filestore_path = get_benchmark_archive(experiment, benchmark)
        archive_exist = filestore_utils.ls(archive_filestore_path,
                                           must_exist=False).retcode == 0
        if archive_exist:
            benchmark_report_dir = get_benchmark_report_dir(
                benchmark, report_dir)
            filesystem.create_directory(benchmark_report_dir)
            filestore_utils.cp(archive_filestore_path,
                               str(benchmark_report_dir))
            print(benchmark_report_dir)
            archive_name = 'coverage-build-%s.tar.gz' % benchmark
            archive_path = os.path.join(benchmark_report_dir, archive_name)
            tar = tarfile.open(archive_path, 'r:gz')
            tar.extractall(benchmark_report_dir)
            os.remove(archive_path)
            break
    logger.info('Finished setting up coverage file for'
                'benchmark: {benchmark}'.format(benchmark=benchmark))


def get_benchmark_archive(experiment_name, benchmark):
    """Returns the path of the coverage archive in gcs bucket
    for |benchmark|."""
    experiment_filestore_dir = get_experiment_filestore_path(experiment_name)
    archive_name = 'coverage-build-%s.tar.gz' % benchmark
    return posixpath.join(experiment_filestore_dir, 'coverage-binaries',
                          archive_name)


def get_experiment_filestore_path(experiment_name):
    """Returns the path of the storage folder for |experiment_name|."""
    if 'EXPERIMENT_FILESTORE' in os.environ:
        experiment_filestore = os.environ['EXPERIMENT_FILESTORE']
    else:
        experiment_filestore = 'gs://fuzzbench-data'
    return posixpath.join(experiment_filestore, experiment_name)


def get_benchmark_report_dir(benchmark, report_dir):
    """Gets the directory path which stores files to generate coverage
    report for |benchmark|."""
    return os.path.join(report_dir, benchmark)


class CoverageReporter:  # pylint: disable=too-many-instance-attributes
    """Class used to generate coverage report for a pair of
    fuzzer and benchmark."""

    # pylint: disable=too-many-arguments
    def __init__(self, fuzzer, benchmark, experiments, report_dir, cov_logger):
        self.fuzzer = fuzzer
        self.benchmark = benchmark
        self.experiments = experiments
        self.report_dir = report_dir
        self.logger = cov_logger
        self.benchmark_report_dir = os.path.join(self.report_dir, benchmark)
        self.fuzzer_report_dir = os.path.join(self.benchmark_report_dir, fuzzer)
        self.merged_profdata_file = os.path.join(self.fuzzer_report_dir,
                                                 'merged.profdata')
        self.source_files = os.path.join(self.benchmark_report_dir, 'src-files')
        fuzz_target = benchmark_utils.get_fuzz_target(self.benchmark)
        self.binary_file = fuzzer_utils.get_fuzz_target_binary(
            self.benchmark_report_dir, fuzz_target_name=fuzz_target)

    def merge_profdata_files(self):
        """Merge profdata files from |src_files| to |dst_files|."""
        self.logger.info('Merging profdata for fuzzer: '
                         '{fuzzer},benchmark: {benchmark}.'.format(
                             fuzzer=self.fuzzer, benchmark=self.benchmark))
        profdata_files = os.listdir(self.fuzzer_report_dir)
        files_to_merge = [os.path.join(self.fuzzer_report_dir, profdata_file)
                          for profdata_file in profdata_files]
        command = ['llvm-profdata', 'merge', '-sparse']
        command.extend(files_to_merge)
        command.extend(['-o', self.merged_profdata_file])
        result = new_process.execute(command, expect_zero=False)
        if result.retcode != 0:
            logger.error('Profdata files merging failed.')

    def fetch_profdata_file(self):
        """Fetches the profdata files for |fuzzer| on |benchmark| from gcs."""
        self.logger.info('Fetching profdata for fuzzer: '
                         '{fuzzer},benchmark: {benchmark}.'.format(
                             fuzzer=self.fuzzer, benchmark=self.benchmark))
        files_to_merge = []
        for experiment in self.experiments:
            trial_ids = measurer.get_trial_ids(experiment, self.fuzzer,
                                               self.benchmark)
            files_to_merge.extend([
                self.get_profdata_file_path(experiment, trial_id)
                for trial_id in trial_ids
            ])
        filesystem.create_directory(self.fuzzer_report_dir)
        for file_path in files_to_merge:
            filestore_utils.cp(file_path,
                               self.fuzzer_report_dir,
                               expect_zero=False)

    def get_profdata_file_path(self, experiment, trial_id):
        """Gets profdata file path for a specific trial."""
        benchmark_fuzzer_trial_dir = experiment_utils.get_trial_dir(
            self.fuzzer, self.benchmark, trial_id)
        experiment_filestore_dir = get_experiment_filestore_path(experiment)
        profdata_file_path = posixpath.join(
            experiment_filestore_dir, 'experiment-folders',
            benchmark_fuzzer_trial_dir,
            'data-{id}.profdata'.format(id=trial_id))
        return profdata_file_path

    def generate_cov_report(self):
        """Generates the coverage report."""
        dst_dir = self.fuzzer_report_dir
        profdata_file_path = self.merged_profdata_file
        binary_file_path = self.binary_file
        source_file_path_prefix = self.source_files
        command = [
            'llvm-cov-11', 'show', '-format=html',
            '-path-equivalence=/,{prefix}'.format(
                prefix=source_file_path_prefix),
            '-output-dir={dst_dir}'.format(dst_dir=dst_dir), '-Xdemangler',
            'c++filt', '-Xdemangler', '-n', binary_file_path,
            '-instr-profile={profdata}'.format(profdata=profdata_file_path)
        ]
        result = new_process.execute(command, expect_zero=False)
        if result.retcode != 0:
            logger.error('Coverage report generation failed for '
                         'fuzzer: {fuzzer},benchmark: {benchmark}.'.format(
                             fuzzer=self.fuzzer, benchmark=self.benchmark))
