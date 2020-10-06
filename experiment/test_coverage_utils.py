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
    segments and functions from summary json file."""
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
    name_df = pd.DataFrame(columns=['id', 'name', 'type'])

    df_container = coverage_utils.DataFrameContainer(segment_df, function_df,
                                                     name_df)

    coverage_utils.extract_covered_segments_and_functions_from_summary_json(
        summary_json_file, benchmark, fuzzer, trial_id, df_container)

    assert len(df_container.segment_df) == num_covered_segments_in_cov_summary
    assert len(df_container.function_df) == num_functions_in_cov_summary


def test_prepare_name_dataframes(fs):
    """Tests that prepare_name_dataframes extracts all the names from segment
    and function data frames and creates name data frame with all names and ids
    to reference the same"""
    summary_json_file = get_test_data_path('cov_summary.json')
    fs.add_real_file(summary_json_file, read_only=False)
    benchmark = 'freetype2'  # for testing
    fuzzer = 'afl'  # for testing
    trial_id = 2  # for testing
    function_name_test_cov_summary = ['main', '_Z3fooIiEvT_', '_Z3fooIfEvT_']
    filename_test_cov_summary = ['/home/test/fuzz_no_fuzzer.cc']

    segment_df = pd.DataFrame(
        columns=["benchmark", "fuzzer", "trial_id", "file_name", "line", "col"])
    function_df = pd.DataFrame(
        columns=["benchmark", "fuzzer", "trial_id", "function_name", "hits"])
    name_df = pd.DataFrame(columns=['id', 'name', 'type'])

    df_container = coverage_utils.DataFrameContainer(segment_df, function_df,
                                                     name_df)

    coverage_utils.extract_covered_segments_and_functions_from_summary_json(
        summary_json_file, benchmark, fuzzer, trial_id, df_container)
    coverage_utils.prepare_name_dataframes(df_container)

    for func_id in list(df_container.function_df['function_id'].unique()):
        assert (df_container.name_df.loc[df_container.name_df['id'] ==
                                         func_id, 'name'].iloc[0] in
                function_name_test_cov_summary)

    for file_id in list(df_container.segment_df['file_id'].unique()):
        assert (df_container.name_df.loc[df_container.name_df['id'] ==
                                         file_id, 'name'].iloc[0] in
                filename_test_cov_summary)

    for fuzzer_id in list(df_container.segment_df['fuzzer_id'].unique()):
        assert df_container.name_df.loc[df_container.name_df['id'] ==
                                        fuzzer_id, 'name'].iloc[0] == 'afl'

    for fuzzer_id in list(df_container.function_df['fuzzer_id'].unique()):
        assert df_container.name_df.loc[df_container.name_df['id'] ==
                                        fuzzer_id, 'name'].iloc[0] == 'afl'

    for benchmark_id in list(df_container.segment_df['benchmark_id'].unique()):
        assert df_container.name_df.loc[df_container.name_df['id'] ==
                                        benchmark_id,
                                        'name'].iloc[0] == 'freetype2'

    for benchmark_id in list(df_container.segment_df['benchmark_id'].unique()):
        assert df_container.name_df.loc[df_container.name_df['id'] ==
                                        benchmark_id,
                                        'name'].iloc[0] == 'freetype2'

    assert len(df_container.name_df.loc[df_container.name_df['type'] ==
                                        'fuzzer', 'id']) == 1
    assert len(df_container.name_df.loc[df_container.name_df['type'] ==
                                        'benchmark', 'id']) == 1
    assert len(df_container.name_df.loc[df_container.name_df['type'] ==
                                        'file', 'id']) == 1
    assert len(df_container.name_df.loc[df_container.name_df['type'] ==
                                        'function', 'id']) == 3


def test_extract_covered_regions_from_summary_json(fs):
    """Tests that extract_covered_regions_from_summary_json returns the covered
    regions from summary json file."""
    summary_json_file = get_test_data_path('cov_summary.json')
    fs.add_real_file(summary_json_file, read_only=False)
    covered_regions = coverage_utils.extract_covered_regions_from_summary_json(
        summary_json_file)
    assert len(covered_regions) == 15
