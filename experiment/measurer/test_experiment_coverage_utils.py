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
"""Tests for experiment_coverage_utils.py"""
import os

from experiment.measurer import experiment_coverage_utils as exp_cov_utils

TEST_DATA_PATH = os.path.join(os.path.dirname(__file__), 'test_data')

# Arbitrary values to use in tests.
SUMMARY_JSON_FILE = 'cov_summary.json'
NUM_FUNCTION_IN_COV_SUMMARY = 3
NUM_COVERED_SEGMENTS_IN_COV_SUMMARY = 16
BENCHMARK = 'freetype2'
FILE_NAME = "/home/test/fuzz_no_fuzzer.cc"
FUNCTION_NAMES = ['main', '_Z3fooIfEvT_', '_Z3fooIiEvT_']
FUZZER = 'afl'
TRIAL_ID = 2
TIMESTAMP = 900


def get_test_data_path(*subpaths):
    """Returns the path of |subpaths| relative to TEST_DATA_PATH."""
    return os.path.join(TEST_DATA_PATH, *subpaths)


def test_extract_segments_and_functions_from_summary_json_for_segments(fs):
    """Tests that extract_covered_regions_from_summary_json returns the covered
    segments and functions from summary json file."""

    summary_json_file = get_test_data_path(SUMMARY_JSON_FILE)
    fs.add_real_file(summary_json_file, read_only=False)

    df_container = (exp_cov_utils.
                    extract_segments_and_functions_from_summary_json(
                        summary_json_file, BENCHMARK, FUZZER, TRIAL_ID,
                        TIMESTAMP))

    fuzzer_ids = df_container.segment_df['fuzzer'].unique()
    benchmark_ids = df_container.segment_df['benchmark'].unique()
    file_ids = df_container.segment_df['file'].unique()

    assert len(df_container.segment_df) == NUM_COVERED_SEGMENTS_IN_COV_SUMMARY

    for fuzzer_id in fuzzer_ids:
        # Check if type recorded for the ID id is "fuzzer".
        assert (df_container.name_df[df_container.name_df['id'] == fuzzer_id]
                ['type'].item() == "fuzzer")
        # Check if fuzzer ids match in "segment" data frame and "name" data
        # frame.
        assert (fuzzer_id == df_container.name_df[df_container.name_df['name']
                                                  == FUZZER]['id'].item())
    for benchmark_id in benchmark_ids:
        # Check if type recorded for the ID id is "benchmark".
        assert (df_container.name_df[df_container.name_df['id'] == benchmark_id]
                ['type'].item() == "benchmark")
        # Check if benchmark ids match in "segment" data frame and "name" data
        # frame.
        assert (benchmark_id == df_container.name_df[
            df_container.name_df['name'] == BENCHMARK]['id'].item())

    for file_id in file_ids:
        # check all file names in the dat frame are already known.
        assert (df_container.name_df[df_container.name_df['id'] == file_id]
                ['type'].item() == "file")
        # Check if file ids exactly match in "segment" data frame and "name"
        # data frame.
        assert (file_id == df_container.name_df[df_container.name_df['name'] ==
                                                FILE_NAME]['id'].item())


def test_extract_segments_and_functions_from_summary_json_for_functions(fs):
    """Tests that name_to_id ."""

    summary_json_file = get_test_data_path(SUMMARY_JSON_FILE)
    fs.add_real_file(summary_json_file, read_only=False)

    df_container = (
        exp_cov_utils.extract_segments_and_functions_from_summary_json(
            summary_json_file, BENCHMARK, FUZZER, TRIAL_ID, TIMESTAMP))

    fuzzer_ids = df_container.function_df['fuzzer'].unique()
    benchmark_ids = df_container.function_df['benchmark'].unique()
    function_ids = df_container.function_df['function'].unique()

    assert len(df_container.segment_df) == NUM_COVERED_SEGMENTS_IN_COV_SUMMARY
    assert len(df_container.function_df) == NUM_FUNCTION_IN_COV_SUMMARY

    for fuzzer_id in fuzzer_ids:
        # Check if type recorded for the ID id is "fuzzer".
        assert (df_container.name_df[df_container.name_df['id'] == fuzzer_id]
                ['type'].item() == "fuzzer")
        # Check if fuzzer ids match in "function" data frame and "name" data
        # frame.
        assert (fuzzer_id == df_container.name_df[df_container.name_df['name']
                                                  == FUZZER]['id'].item())
    for benchmark_id in benchmark_ids:
        # Check if type recorded for the ID id is "benchmark".
        assert (df_container.name_df[df_container.name_df['id'] == benchmark_id]
                ['type'].item() == "benchmark")
        # Check if benchmark ids match in "function" data frame and "name" data
        # frame.
        assert (benchmark_id == df_container.name_df[
            df_container.name_df['name'] == BENCHMARK]['id'].item())

    for function_id in function_ids:
        # check all function names in the data frames are already known.
        assert (set(
            df_container.name_df[df_container.name_df['id'] == function_id]
            ['name'].unique()).issubset(FUNCTION_NAMES))
        # Check if function ids match in "function" data frame and "name" data
        # frame.
        assert (df_container.name_df[df_container.name_df['id'] == function_id]
                ['type'].item() == "function")


def test_data_frame_container_remove_redundant_duplicates(fs):
    """Tests that remove_redundant_duplicates removes all duplicates entries in
    name_df and segment_df."""

    summary_json_file = get_test_data_path(SUMMARY_JSON_FILE)
    fs.add_real_file(summary_json_file, read_only=False)

    df_container = (
        exp_cov_utils.extract_segments_and_functions_from_summary_json(
            summary_json_file, BENCHMARK, FUZZER, TRIAL_ID, TIMESTAMP))

    # Drop duplicates using remove_redundant_duplicates().
    df_container.remove_redundant_duplicates()

    # length of data frame after calling remove_redundant_duplicates().
    df_length = len(df_container.segment_df)

    # Force dropping of duplicates again.
    df_after_drop = df_container.segment_df.drop_duplicates(
        subset=df_container.segment_df.columns.difference(['time']))

    # Data frame length after for drop.
    df_length_after_drop = len(df_after_drop)

    # assert length didn't change.
    assert (df_length - df_length_after_drop) == 0

