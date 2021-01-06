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
"""Tests for coverage_printer_utils.py"""
import os

from experiment.measurer import coverage_printer_utils

TEST_DATA_PATH = os.path.join(os.path.dirname(__file__), 'test_data')

# Expected Constants.
SUMMARY_JSON_FILE = 'cov_summary.json'
NUM_FUNCTION_IN_COV_SUMMARY = 3
NUM_COVERED_SEGMENTS_IN_COV_SUMMARY = 16
FILE_NAME = "/home/test/fuzz_no_fuzzer.cc"
FUNCTION_NAMES = ['main', '_Z3fooIfEvT_', '_Z3fooIiEvT_']
BENCHMARK = 'benchmark_1'
FUZZER = 'fuzzer_1'
TIMESTAMP = 900
TRIAL_ID = 2


def get_test_data_path(*subpaths):
    """Returns the path of |subpaths| relative to TEST_DATA_PATH."""
    return os.path.join(TEST_DATA_PATH, *subpaths)


def test_data_frame_container_remove_redundant_duplicates(fs):
    """Tests that remove_redundant_duplicates removes all duplicates entries in
    name_df and segment_df."""

    summary_json_file = get_test_data_path(SUMMARY_JSON_FILE)
    fs.add_real_file(summary_json_file, read_only=False)

    df_container = (
        coverage_printer_utils.extract_segments_and_functions_from_summary_json(
            summary_json_file, BENCHMARK, FUZZER, TRIAL_ID, TIMESTAMP))

    # Check whether the length of the segment data frame is the same if we
    # request pandas to drop all duplicates with the same time stamp
    deduplicated = df_container.segment_df.drop_duplicates(
        subset=df_container.segment_df.columns.difference(['time']))
    old_length = len(df_container.segment_df)
    assert old_length == len(deduplicated)


def test_extract_segments_and_functions_from_summary_json_for_segments(fs):
    """Tests that segments and functions from summary json properly extracts the
     information and also test for integrity of fuzzer, benchmark and function
     ids in segment_df for a given summary json file."""

    summary_json_file = get_test_data_path(SUMMARY_JSON_FILE)
    fs.add_real_file(summary_json_file, read_only=False)

    df_container = (
        coverage_printer_utils.extract_segments_and_functions_from_summary_json(
            summary_json_file, BENCHMARK, FUZZER, TRIAL_ID, TIMESTAMP))

    fuzzer_ids = df_container.segment_df['fuzzer'].unique()
    benchmark_ids = df_container.segment_df['benchmark'].unique()
    file_ids = df_container.segment_df['file'].unique()

    # Assert length of resulting data frame is as expected.
    assert len(df_container.segment_df) == NUM_COVERED_SEGMENTS_IN_COV_SUMMARY

    # Assert integrity for fuzzer and benchmark ids.
    for fuzzer_id in fuzzer_ids:
        integrity_check_helper(df_container, fuzzer_id, "fuzzer", FUZZER)

    # Assert integrity for fuzzer ids.
    for benchmark_id in benchmark_ids:
        integrity_check_helper(df_container, benchmark_id, "benchmark",
                               BENCHMARK)

    # Assert integrity for file ids.
    for file_id in file_ids:
        integrity_check_helper(df_container, file_id, "file", FILE_NAME)


def test_extract_segments_and_functions_from_summary_json_for_functions(fs):
    """Tests that segments and functions from summary json properly extracts the
     information and also test for integrity of fuzzer, benchmark and function
     ids in function_df for a given summary json file.."""

    summary_json_file = get_test_data_path(SUMMARY_JSON_FILE)
    fs.add_real_file(summary_json_file, read_only=False)

    df_container = (
        coverage_printer_utils.extract_segments_and_functions_from_summary_json(
            summary_json_file, BENCHMARK, FUZZER, TRIAL_ID, TIMESTAMP))

    fuzzer_ids = df_container.function_df['fuzzer'].unique()
    benchmark_ids = df_container.function_df['benchmark'].unique()
    function_ids = df_container.function_df['function'].unique()

    # Assert length of resulting data frame is as expected.
    assert len(df_container.function_df) == NUM_FUNCTION_IN_COV_SUMMARY

    # Assert integrity for fuzzer ids.
    for fuzzer_id in fuzzer_ids:
        integrity_check_helper(df_container, fuzzer_id, "fuzzer", FUZZER)

    # Assert integrity for benchmark ids.
    for benchmark_id in benchmark_ids:
        integrity_check_helper(df_container, benchmark_id, "benchmark",
                               BENCHMARK)

    # Assert integrity for function ids.
    for function_id in function_ids:
        integrity_check_helper(df_container, function_id, "function",
                               FUNCTION_NAMES)


def integrity_check_helper(df_container, _id, _type, name):
    """Helper function to check the integrity of resulting df_container after
    recording segment and function information for the given id, type and
    name."""

    # Check whether the given id has the expected type.
    assert (df_container.name_df[df_container.name_df['id'] == _id]
            ['type'].item() == _type)

    if _type == "function":
        # check if all function names for each fucntion id is already known.
        assert (set(df_container.name_df[df_container.name_df['id'] == _id]
                    ['name'].unique()).issubset(name))
    else:
        # Check whether the given name resolves to the expected id.
        assert (_id == df_container.name_df[df_container.name_df['name'] ==
                                            name]['id'].item())
