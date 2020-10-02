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
# See the License for the specific language governing permissions andsss
# limitations under the License.
"""Tests for coverage_utils.py"""
import os

import pandas as pd
from experiment import coverage_utils

TEST_DATA_PATH = os.path.join(os.path.dirname(__file__), 'test_data')


def get_test_data_path(*subpaths):
    """Returns the path of |subpaths| relative to TEST_DATA_PATH."""
    return os.path.join(TEST_DATA_PATH, *subpaths)


def test_extract_segment_and_function_from_summary_json(fs):
    """Tests that extract_covered_regions_from_summary_json returns the covered
    regions from summary json file."""
    num_functions_in_cov_summary = 3  # for testing
    num_covered_segments_in_cov_summary = 16  # for testing
    summary_json_file = get_test_data_path('cov_summary.json')
    fs.add_real_file(summary_json_file, read_only=False)
    benchmark = 'freetype2'  # for testing
    fuzzer = 'afl'  # for testing
    trial_id = 2  # for testing
    segment_df = pd.DataFrame(
        columns=["benchmark", "fuzzer", "trial_id", "file_name", "line", "col"])
    function_df = pd.DataFrame(
        columns=["benchmark", "fuzzer", "trial_id", "function_name", "hits"])
    benchmark_name_df = pd.DataFrame(columns=['benchmark_id', 'benchmark'])
    fuzzer_name_df = pd.DataFrame(columns=['fuzzer_id', 'fuzzer'])
    filename_df = pd.DataFrame(columns=['file_id', 'file_name'])
    function_name_df = pd.DataFrame(columns=['function_id', 'function_name'])
    df_container = coverage_utils.DataFrameContainer(segment_df, function_df,
                                                     benchmark_name_df, fuzzer_name_df,
                                                     filename_df, function_name_df)
    coverage_utils.extract_covered_segments_and_functions_from_summary_json(
        summary_json_file, benchmark, fuzzer, trial_id, df_container)
    assert ((len(
        df_container.segment_df) == num_covered_segments_in_cov_summary) and
            (len(df_container.function_df) == num_functions_in_cov_summary))


def test_populate_all_dfs_for_3nf(fs):
    """Tests that extract_covered_regions_from_summary_json returns the covered
    regions from summary json file."""
    summary_json_file = get_test_data_path('cov_summary.json')
    fs.add_real_file(summary_json_file, read_only=False)
    benchmark = 'freetype2'  # for testing
    fuzzer = 'afl'  # for testing
    trial_id = 2  # for testing
    segment_df = pd.DataFrame(
        columns=["benchmark", "fuzzer", "trial_id", "file_name", "line", "col"])
    function_df = pd.DataFrame(
        columns=["benchmark", "fuzzer", "trial_id", "function_name", "hits"])
    benchmark_name_df = pd.DataFrame(columns=['benchmark_id', 'benchmark'])
    fuzzer_name_df = pd.DataFrame(columns=['fuzzer_id', 'fuzzer'])
    filename_df = pd.DataFrame(columns=['file_id', 'file_name'])
    function_name_df = pd.DataFrame(columns=['function_id', 'function_name'])
    df_container = coverage_utils.DataFrameContainer(segment_df, function_df,
                                                     benchmark_name_df, fuzzer_name_df,
                                                     filename_df, function_name_df)
    coverage_utils.extract_covered_segments_and_functions_from_summary_json(
        summary_json_file, benchmark, fuzzer, trial_id, df_container)
    coverage_utils.populate_all_dfs_for_3nf(df_container)
    assert (len(df_container.function_name_df) != 0
            and
            len(df_container.benchmark_name_df) != 0
            and
            len(df_container.filename_df) != 0
            and
            len(df_container.fuzzer_name_df) != 0)


def test_wrangle_df_for_csv_generation(fs):
    """Tests that extract_covered_regions_from_summary_json returns the covered
    regions from summary json file."""
    summary_json_file = get_test_data_path('cov_summary.json')
    fs.add_real_file(summary_json_file, read_only=False)
    benchmark = 'freetype2'  # for testing
    fuzzer = 'afl'  # for testing
    trial_id = 2  # for testing
    segment_df = pd.DataFrame(
        columns=["benchmark", "fuzzer", "trial_id", "file_name", "line", "col"])
    function_df = pd.DataFrame(
        columns=["benchmark", "fuzzer", "trial_id", "function_name", "hits"])
    benchmark_name_df = pd.DataFrame(columns=['benchmark_id', 'benchmark'])
    fuzzer_name_df = pd.DataFrame(columns=['fuzzer_id', 'fuzzer'])
    filename_df = pd.DataFrame(columns=['file_id', 'file_name'])
    function_name_df = pd.DataFrame(columns=['function_id', 'function_name'])
    df_container = coverage_utils.DataFrameContainer(segment_df, function_df,
                                                     benchmark_name_df, fuzzer_name_df,
                                                     filename_df, function_name_df)
    coverage_utils.extract_covered_segments_and_functions_from_summary_json(
        summary_json_file, benchmark, fuzzer, trial_id, df_container)
    coverage_utils.populate_all_dfs_for_3nf(df_container)
    coverage_utils.wrangle_df_for_csv_generation(df_container)
    assert (len(df_container.function_name_df['function_id']) ==
            len(df_container.function_df['function_id'].unique())
            and
            len(df_container.filename_df['file_id']) ==
            len(df_container.segment_df['file_id'].unique())
            and
            len(df_container.benchmark_name_df['benchmark_id']) ==
            len(df_container.segment_df['benchmark_id'].unique())
            and
            len(df_container.benchmark_name_df['benchmark_id']) ==
            len(df_container.function_df['benchmark_id'].unique())
            and
            len(df_container.fuzzer_name_df['fuzzer_id']) ==
            len(df_container.segment_df['fuzzer_id'].unique())
            and
            len(df_container.fuzzer_name_df['fuzzer_id']) ==
            len(df_container.function_df['fuzzer_id'].unique()))


def test_extract_covered_regions_from_summary_json(fs):
    """Tests that extract_covered_regions_from_summary_json returns the covered
    regions from summary json file."""
    summary_json_file = get_test_data_path('cov_summary.json')
    fs.add_real_file(summary_json_file, read_only=False)
    covered_regions = coverage_utils.extract_covered_regions_from_summary_json(
        summary_json_file)
    assert len(covered_regions) == 15
