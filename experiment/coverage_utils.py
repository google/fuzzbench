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
import hashlib
import pandas as pd

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
    """Returns the directory to store coverage information including coverage
    report and json summary file."""
    work_dir = exp_utils.get_work_dir()
    return os.path.join(work_dir, 'coverage')


def generate_coverage_reports(experiment_config: dict):
    """Generates coverage reports for each benchmark and fuzzer."""
    logs.initialize()
    logger.info('Start generating coverage reports.')

    benchmarks = experiment_config['benchmarks']
    fuzzers = experiment_config['fuzzers']
    experiment = experiment_config['experiment']

    for benchmark in benchmarks:
        for fuzzer in fuzzers:
            generate_coverage_report(experiment, benchmark, fuzzer)

    logger.info('Finished generating coverage reports.')


class DataFrameContainer:
    """Maintains segment and function coverage information, and writes this
    information to CSV files."""

    def __init__(self):
        """Construct data frames."""
        self.segment_df = pd.DataFrame(columns=[
            "benchmark_id", "fuzzer_id", "trial_id", "file_id", "line", "col",
            "time_stamp"
        ])
        self.function_df = pd.DataFrame(columns=[
            "benchmark_id", "fuzzer_id", "trial_id", "function_id", "hits",
            "time_stamp"
        ])
        self.name_df = pd.DataFrame(columns=['id', 'name', 'type'])

    def remove_redundant_duplicates(self):
        """Removes redundant entries in segment_df. Before calling this
        function, for each time stamp, segment_df contains all segments that are
        covered in this time stamp. After calling this function, for each time
        stamp, segment_df only contains segments that have been covered since
        the previous time stamp. This significantly reduces the size of the
        resulting CSV file."""
        try:
            # Drop duplicates but with different timestamps in segment data.
            self.segment_df = self.segment_df.sort_values(by=['time_stamp'])
            self.segment_df = self.segment_df.drop_duplicates(
                subset=self.segment_df.columns.difference(['time_stamp']),
                keep="first")
            self.name_df = self.name_df.drop_duplicates(keep="first")

        except (ValueError, KeyError, IndexError):
            logger.error('Error occurred when removing duplicates.')

    def check_if_all_ids_in_name_df_are_unique(self):
        """Checks if all ids in name_df are unique"""
        list_of_ids = self.name_df['id'].to_list()

        if len(list_of_ids) == len(set(list_of_ids)):
            logger.info("All ids in name_df are unique")
        else:
            logger.info("Ids in name_df are not unique")

    def reorder_columns_in_segment_and_function_df(self):
        """Re-orders the columns of segment_df and fucntion_df to the desired
        order"""
        try:
            # Re-order columns in segment_df.
            segmentdf_col_names = [
                "benchmark_id", "fuzzer_id", "trial_id", "time_stamp",
                "file_id", "line", "col"
            ]
            self.segment_df = self.segment_df.reindex(
                columns=segmentdf_col_names)
            # Re-order columns in function_df.
            functiondf_col_names = [
                "benchmark_id", "fuzzer_id", "trial_id", "time_stamp",
                "function_id", "hits"
            ]
            self.function_df = self.function_df.reindex(
                columns=functiondf_col_names)
        except (IndexError, ValueError, KeyError):
            logger.error('Error occurred when reordering columns in '
                         'DataFrames.')

    def generate_csv_files(self):
        """Generates three compressed CSV files containing coverage information
        for all fuzzers, benchmarks, and trials. To maintain a small file size,
        all strings, such as file and function names, are referenced by id and
        resolved in 'names.csv'."""

        # Clean and prune experiment-specific data frames.
        self.remove_redundant_duplicates()
        self.check_if_all_ids_in_name_df_are_unique()
        self.reorder_columns_in_segment_and_function_df()

        # Write CSV files to file store.
        def csv_filestore_helper(file_name, df):
            """Helper function for storing csv files in filestore."""
            src = os.path.join(get_coverage_info_dir(), 'data', file_name)
            dst = exp_path.filestore(src)
            df.to_csv(src, index=False, compression='infer')
            filestore_utils.cp(src, dst)

        csv_filestore_helper('functions.csv.gz', self.function_df)
        csv_filestore_helper('segments.csv.gz', self.segment_df)
        csv_filestore_helper('names.csv.gz', self.name_df)


def generate_coverage_report(experiment, benchmark, fuzzer):
    """Generates the coverage report for one pair of benchmark and fuzzer."""
    logger.info(
        ('Generating coverage report for '
         'benchmark: {benchmark} fuzzer: {fuzzer}.').format(benchmark=benchmark,
                                                            fuzzer=fuzzer))

    try:
        coverage_reporter = CoverageReporter(experiment, fuzzer, benchmark)

        # Merges all the profdata files.
        coverage_reporter.merge_profdata_files()

        # Generate the coverage summary json file based on merged profdata file.
        coverage_reporter.generate_coverage_summary_json()

        # Generate the coverage regions json file.
        coverage_reporter.generate_coverage_regions_json()

        # Generates the html reports using llvm-cov.
        coverage_reporter.generate_coverage_report()

        logger.info('Finished generating coverage report.')
    except Exception:  # pylint: disable=broad-except
        logger.error('Error occurred when generating coverage report.')


class CoverageReporter:  # pylint: disable=too-many-instance-attributes
    """Class used to generate coverage report for a pair of fuzzer and
    benchmark."""

    # pylint: disable=too-many-arguments
    def __init__(self, experiment, fuzzer, benchmark):
        self.fuzzer = fuzzer
        self.benchmark = benchmark
        self.experiment = experiment
        self.trial_ids = get_trial_ids(experiment, fuzzer, benchmark)

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

    def generate_coverage_regions_json(self):
        """Stores the coverage data in a json file."""
        covered_regions = extract_covered_regions_from_summary_json(
            self.merged_summary_json_file)
        coverage_json_src = os.path.join(self.data_dir, 'covered_regions.json')
        coverage_json_dst = exp_path.filestore(coverage_json_src)
        filesystem.create_directory(self.data_dir)
        with open(coverage_json_src, 'w') as file_handle:
            json.dump(covered_regions, file_handle)
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
    """Generates the json summary file from |coverage_binary|
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


def extract_segments_and_functions_from_summary_json(
        # pylint: disable=too-many-locals
        summary_json_file,
        benchmark,
        fuzzer,
        trial_id,
        time_stamp):
    """Return a trial-specific data frame container with segment and function
     coverage information given a trial-specific coverage summary json file."""

    process_specific_df_container = DataFrameContainer()

    def append_to_specified_df(list_to_append, data_frame):
        series_to_append = pd.Series(list_to_append, index=data_frame.columns)
        df = data_frame.append(series_to_append, ignore_index=True)
        return df

    def generate_hexdecimal_hash(obj):
        return hashlib.md5(obj.encode()).hexdigest()[:7]

    # Allocating unique ids by computing hash.
    benchmark_id = generate_hexdecimal_hash(benchmark)
    fuzzer_id = generate_hexdecimal_hash(fuzzer)

    # Append benchmark-name with id to name_df.
    to_append = [benchmark_id, benchmark, "benchmark"]
    process_specific_df_container.name_df = append_to_specified_df(
        to_append, process_specific_df_container.name_df)

    # Append fuzzer-name with id to name_df.
    to_append = [fuzzer_id, fuzzer, "fuzzer"]
    process_specific_df_container.name_df = append_to_specified_df(
        to_append, process_specific_df_container.name_df)

    try:
        coverage_info = get_coverage_infomation(summary_json_file)
        # Extract coverage information for functions.
        for function_data in coverage_info['data'][0]['functions']:
            function_name = function_data['name']
            # Allocating unique ids by computing hash.
            function_id = generate_hexdecimal_hash(function_name)
            # Append function-name with id to name_df.
            to_append = [function_id, function_name, "function"]
            process_specific_df_container.name_df = append_to_specified_df(
                to_append, process_specific_df_container.name_df)

            # Append function coverage info to function_df.
            to_append = [
                benchmark_id, fuzzer_id, trial_id, function_id,
                function_data['count'], time_stamp
            ]
            process_specific_df_container.function_df = append_to_specified_df(
                to_append, process_specific_df_container.function_df)

        # Extract coverage information for segments.
        line_index = 0
        col_index = 1
        hits_index = 2
        for file in coverage_info['data'][0]['files']:
            filename = file['filename']
            # Allocating unique ids by computing hash.
            file_id = generate_hexdecimal_hash(filename)
            # Append file-name with id to name_df.
            to_append = [file_id, filename, "file"]
            process_specific_df_container.name_df = append_to_specified_df(
                to_append, process_specific_df_container.name_df)
            for segment in file['segments']:
                if segment[hits_index] != 0:
                    to_append = [
                        benchmark_id, fuzzer_id, trial_id, file_id,
                        segment[line_index], segment[col_index], time_stamp
                    ]
                    process_specific_df_container.segment_df = (
                        append_to_specified_df(
                            to_append,
                            process_specific_df_container.segment_df))

    except (ValueError, KeyError, IndexError):
        logger.error('Failed when extracting trial-specific segment and'
                     'function information from coverage summary')
    return process_specific_df_container


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
