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
"""Tests for coverage_data_utils.py"""

import pandas as pd
import pandas.testing as pd_test

from analysis import coverage_data_utils


def create_coverage_data():
    """Utility function to create test data."""
    return {
        "afl libpng-1.2.56": [[0, 0, 1, 1], [0, 0, 2, 2], [0, 0, 3, 3]],
        "libfuzzer libpng-1.2.56": [[0, 0, 1, 1], [0, 0, 2, 3], [0, 0, 3, 3],
                                    [0, 0, 4, 4]]
    }


def test_get_unique_region_dict():
    """Tests get_unique_region_dict() function."""
    coverage_dict = create_coverage_data()
    benchmark_coverage_dict = coverage_data_utils.get_benchmark_cov_dict(
        coverage_dict, 'libpng-1.2.56')
    unique_region_dict = coverage_data_utils.get_unique_region_dict(
        benchmark_coverage_dict)
    expected_dict = {
        (0, 0, 2, 2): ['afl'],
        (0, 0, 2, 3): ['libfuzzer'],
        (0, 0, 4, 4): ['libfuzzer']
    }
    assert expected_dict == unique_region_dict


def test_get_unique_region_cov_df():
    """Tests get_unique_region_cov_df() function."""
    coverage_dict = create_coverage_data()
    benchmark_coverage_dict = coverage_data_utils.get_benchmark_cov_dict(
        coverage_dict, 'libpng-1.2.56')
    unique_region_dict = coverage_data_utils.get_unique_region_dict(
        benchmark_coverage_dict)
    fuzzer_names = ['afl', 'libfuzzer']
    unique_region_df = coverage_data_utils.get_unique_region_cov_df(
        unique_region_dict, fuzzer_names)
    unique_region_df = unique_region_df.sort_values(by=['fuzzer']).reset_index(
        drop=True)
    expected_df = pd.DataFrame([{
        'fuzzer': 'afl',
        'unique_regions_covered': 1
    }, {
        'fuzzer': 'libfuzzer',
        'unique_regions_covered': 2
    }])
    assert unique_region_df.equals(expected_df)


def test_get_benchmark_cov_dict():
    """Tests that get_benchmark_cov_dict() returns correct dictionary."""
    coverage_dict = create_coverage_data()
    benchmark = 'libpng-1.2.56'
    benchmark_cov_dict = coverage_data_utils.get_benchmark_cov_dict(
        coverage_dict, benchmark)
    expected_cov_dict = {
        "afl": {(0, 0, 3, 3), (0, 0, 2, 2), (0, 0, 1, 1)},
        "libfuzzer": {(0, 0, 4, 4), (0, 0, 3, 3), (0, 0, 2, 3), (0, 0, 1, 1)}
    }
    assert expected_cov_dict == benchmark_cov_dict


def test_get_pairwise_unique_coverage_table():
    """Tests that get_pairwise_unique_coverage_table() gives the
    correct dataframe."""
    coverage_dict = create_coverage_data()
    benchmark_coverage_dict = coverage_data_utils.get_benchmark_cov_dict(
        coverage_dict, 'libpng-1.2.56')
    fuzzers = ['libfuzzer', 'afl']
    table = coverage_data_utils.get_pairwise_unique_coverage_table(
        benchmark_coverage_dict, fuzzers)
    expected_table = pd.DataFrame([[0, 1], [2, 0]],
                                  index=fuzzers,
                                  columns=fuzzers)
    pd_test.assert_frame_equal(table, expected_table)
