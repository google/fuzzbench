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
import pandas as pd
import numpy as np

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


def generate_coverage_reports(experiment_config: dict, df_container):
    """Generates coverage reports for each benchmark and fuzzer."""
    logs.initialize()
    logger.info('Start generating coverage reports.')

    benchmarks = experiment_config['benchmarks']
    fuzzers = experiment_config['fuzzers']
    experiment = experiment_config['experiment']

    for benchmark in benchmarks:
        for fuzzer in fuzzers:
            generate_coverage_report(experiment, benchmark, fuzzer)
    # Generate experiment-specific CSV files
    prepare_name_dataframe(df_container)
    remove_redundant_duplicates(df_container)
    generate_segment_and_function_csv_files(df_container)
    logger.info('Finished generating coverage reports.')


class DataFrameContainer:
    """ Holds experiment-specific segment and function coverage information for
    all fuzzers, benchmarks, and trials"""

    def __init__(self, segment_df, function_df, name_df):
        self.segment_df = segment_df
        self.function_df = function_df
        self.name_df = name_df


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

        # Generate the coverage summary json file based on merged profdata file
        coverage_reporter.generate_coverage_summary_json()

        # Generate the coverage regions json file.
        coverage_reporter.generate_coverage_regions_json()

        # Generates the html reports using llvm-cov.
        coverage_reporter.generate_coverage_report()

        logger.info('Finished generating coverage report.')
    except Exception:  # pylint: disable=broad-except
        logger.error('Error occurred when generating coverage report.')


class CoverageReporter:  # pylint: disable=too-many-instance-attributes
    """Class used to generate coverage report for a pair of
    fuzzer and benchmark."""

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
        """Generates the coverage summary json from merged profdata file and
        trial-specific coverage summary json from trial-specific profdata file.
        """
        coverage_binary = get_coverage_binary(self.benchmark)
        # Generate merged coverage summary json.
        result = generate_json_summary(coverage_binary,
                                       self.merged_profdata_file,
                                       self.merged_summary_json_file,
                                       summary_only=False)

        if result.retcode != 0:
            logger.error(
                'Merged coverage summary json file generation failed for '
                'fuzzer: {fuzzer}, benchmark: {benchmark}.'.format(
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


def extract_segments_and_functions_from_summary_json(  # pylint: disable=too-many-locals
        summary_json_file, benchmark, fuzzer, trial_id, time_stamp):
    """Extracts and stores information on segment and function coverage for a
    trial in experiment-specific data frames given a trial-specific coverage
    summary json file."""

    segment_df = pd.DataFrame(columns=[
        "benchmark", "fuzzer", "trial_id", "file_name", "line", "col",
        "timestamp"
    ])
    function_df = pd.DataFrame(columns=[
        "benchmark", "fuzzer", "trial_id", "function_name", "hits", "timestamp"
    ])

    try:
        coverage_info = get_coverage_infomation(summary_json_file)

        # Extract coverage information for functions.
        for function_data in coverage_info['data'][0]['functions']:
            to_append = [
                benchmark, fuzzer, trial_id, function_data['name'],
                function_data['count'], time_stamp
            ]
            series = pd.Series(to_append, index=function_df.columns)
            function_df = function_df.append(series, ignore_index=True)

        # Extract coverage information for functions and segments.
        line_index = 0
        col_index = 1
        hits_index = 2
        for file in coverage_info['data'][0]['files']:
            filename = file['filename']
            for segment in file['segments']:
                if segment[hits_index] != 0:
                    to_append = [
                        benchmark, fuzzer, trial_id, filename,
                        segment[line_index], segment[col_index], time_stamp
                    ]
                    series = pd.Series(to_append, index=segment_df.columns)
                    segment_df = segment_df.append(series, ignore_index=True)

    except (ValueError, KeyError, IndexError):
        logger.error('Failed when extracting trial-specific segment and'
                     'function information from coverage summary')
    return segment_df, function_df


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


def prepare_name_dataframe(df_container):
    """Populates name data frame with experiment specific benchmark names,
    fuzzer names, file names and function names and also replaces names with ids
    in segment and function data frames."""
    try:
        # Stack all names into a single numpy array.
        names = np.hstack([
            df_container.segment_df['benchmark'].unique(),
            df_container.segment_df['fuzzer'].unique(),
            df_container.function_df['function_name'].unique(),
            df_container.segment_df['file_name'].unique()
        ])

        # Create a list with "type" of names to match the stack above.
        types = ['benchmark'] * len(
            df_container.segment_df['benchmark'].unique())
        types.extend(['fuzzer'] *
                     len(df_container.segment_df['fuzzer'].unique()))
        types.extend(['function'] *
                     len(df_container.function_df['function_name'].unique()))
        types.extend(['file'] *
                     len(df_container.segment_df['file_name'].unique()))

        # Populate name DataFrame.
        df_container.name_df['name'] = names
        df_container.name_df['type'] = types
        df_container.name_df.reset_index()
        df_container.name_df['id'] = df_container.name_df.index + 1

        # Reshape DataFrames for joins.
        reshaped_name_df = df_container.name_df.pivot(index='name',
                                                      columns='type',
                                                      values='id')
        # making "name" as a column again
        reshaped_name_df['name'] = reshaped_name_df.index

        # Replacing names with ids by joining DataFrames.
        df_container.segment_df = rename_drop_columns_and_leftjoin(
            df_container.segment_df, reshaped_name_df, ['fuzzer', 'fuzzer_id'])

        df_container.function_df = rename_drop_columns_and_leftjoin(
            df_container.function_df, reshaped_name_df, ['fuzzer', 'fuzzer_id'])

        df_container.segment_df = rename_drop_columns_and_leftjoin(
            df_container.segment_df, reshaped_name_df,
            ['benchmark', 'benchmark_id'])

        df_container.function_df = rename_drop_columns_and_leftjoin(
            df_container.function_df, reshaped_name_df,
            ['benchmark', 'benchmark_id'])

        df_container.segment_df = rename_drop_columns_and_leftjoin(
            df_container.segment_df, reshaped_name_df, ['file_name', 'file_id'])

        df_container.function_df = rename_drop_columns_and_leftjoin(
            df_container.function_df, reshaped_name_df,
            ['function_name', 'function_id'])

    except (ValueError, KeyError, IndexError):
        logger.error('Error occurred when preparing name DataFrame.')


def remove_redundant_duplicates(df_container):
    """Removes entries with same segment coverage information but different
    timestamps (keeps the data with smallest timestamp (in secs)). Also removes
    redundant rows from function data frame, if any, to reduce the size of the
    data being exported"""
    try:
        # Drop duplicates but with different timestamps in segment data.
        df_container.segment_df = df_container.segment_df.sort_values(
            by=['timestamp'])
        df_container.segment_df = df_container.segment_df.drop_duplicates(
            subset=df_container.segment_df.columns.difference(['timestamp']),
            keep="first")
        # Drop duplicates in segments data if any.
        df_container.segment_df = df_container.segment_df.drop_duplicates(
            keep="first")
        # Drop duplicates in function data with if any.
        df_container.function_df = df_container.function_df.sort_values(
            by=['timestamp'])
        df_container.function_df = df_container.function_df.drop_duplicates(
            keep="first")
    except (ValueError, KeyError, IndexError):
        logger.error('Error occurred when removing duplicates.')


def generate_segment_and_function_csv_files(df_container):
    """Generates three compressed CSV files containing coverage information for
    all fuzzers, benchmarks, and trials. To maintain a small file size, all
    strings, such as file and function names, are referenced by id and resolved
    in "names.csv"."""
    # Store compressed (gzip) function csv in filestore.
    csv_filestore_helper('functions.csv.gz', df_container.function_df)

    # Store compressed (gzip) segment csv in filestore.
    csv_filestore_helper('segment.csv.gz', df_container.segment_df)

    # Store compressed (gzip) names csv in filestore.
    csv_filestore_helper('names.csv.gz', df_container.name_df)


def csv_filestore_helper(file_name, df):
    """Helper function for storing csv files in filestore."""
    src = os.path.join(get_coverage_info_dir(), 'data', file_name)
    dst = exp_path.filestore(src)
    df.to_csv(src, index=False, compression='infer')
    filestore_utils.cp(src, dst)


def rename_drop_columns_and_leftjoin(df1, df2, name_list):
    """Helper function to rename data frame df2 and merge data frame df1 and df2
    on a given column."""
    column_name = name_list[0]
    df2.columns = [
        'benchmark_id', 'file_id', 'function_id', 'fuzzer_id', column_name
    ]
    # Select columns to drop.
    cols = [col for col in df2.columns if col not in name_list]
    # Lef-join action.
    df = pd.merge(df1, df2.drop(columns=cols), on=column_name, how='outer')
    # Drop unnecessary columns.
    df = df.drop(columns=[column_name])
    return df.dropna()
