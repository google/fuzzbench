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

from experiment import coverage_utils

TEST_DATA_PATH = os.path.join(os.path.dirname(__file__), 'test_data')


def get_test_data_path(*subpaths):
    """Returns the path of |subpaths| relative to TEST_DATA_PATH."""
    return os.path.join(TEST_DATA_PATH, *subpaths)


def test_extract_segments_and_functions_from_summary_json(fs):
    """Tests that extract_covered_regions_from_summary_json returns the covered
    segments and functions from summary json file."""
    num_functions_in_cov_summary = 3  # for testing
    num_covered_segments_in_cov_summary = 16  # for testing
    summary_json_file = get_test_data_path('cov_summary.json')
    fs.add_real_file(summary_json_file, read_only=False)
    benchmark = 'freetype2'  # for testing
    fuzzer = 'afl'  # for testing
    trial_id = 2  # for testing
    timestamp = 900

    df_container = (
        coverage_utils.extract_segments_and_functions_from_summary_json(
            summary_json_file, benchmark, fuzzer, trial_id, timestamp))

    assert len(df_container.segment_df) == num_covered_segments_in_cov_summary
    assert len(df_container.function_df) == num_functions_in_cov_summary


def test_extract_covered_regions_from_summary_json(fs):
    """Tests that extract_covered_regions_from_summary_json returns the covered
    regions from summary json file."""
    summary_json_file = get_test_data_path('cov_summary.json')
    fs.add_real_file(summary_json_file, read_only=False)
    covered_regions = coverage_utils.extract_covered_regions_from_summary_json(
        summary_json_file)
    assert len(covered_regions) == 15
