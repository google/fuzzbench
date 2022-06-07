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
from unittest import mock

import pandas as pd
import pandas.testing as pd_test

from analysis import coverage_data_utils

FUZZER = 'afl'
BENCHMARK = 'libpng-1.2.56'
EXPERIMENT_FILESTORE_PATH = 'gs://fuzzbench-data/myexperiment'
SAMPLE_DF = pd.DataFrame([{
    'experiment_filestore': 'gs://fuzzbench-data',
    'experiment': 'exp1',
    'fuzzer': FUZZER,
    'benchmark': BENCHMARK
}, {
    'experiment_filestore': 'gs://fuzzbench-data2',
    'experiment': 'exp2',
    'fuzzer': 'libfuzzer',
    'benchmark': BENCHMARK
}])


def create_coverage_data():
    """Utility function to create test data."""
    return {
        'afl libpng-1.2.56': [[0, 0, 1, 1], [0, 0, 2, 2], [0, 0, 3, 3]],
        'libfuzzer libpng-1.2.56': [[0, 0, 1, 1], [0, 0, 2, 3], [0, 0, 3, 3],
                                    [0, 0, 4, 4]]
    }


def test_get_unique_branch_dict():
    """Tests get_unique_branch_dict() function."""
    coverage_dict = create_coverage_data()
    benchmark_coverage_dict = coverage_data_utils.get_benchmark_cov_dict(
        coverage_dict, 'libpng-1.2.56')
    unique_branch_dict = coverage_data_utils.get_unique_branch_dict(
        benchmark_coverage_dict)
    expected_dict = {
        (0, 0, 2, 2): ['afl'],
        (0, 0, 2, 3): ['libfuzzer'],
        (0, 0, 4, 4): ['libfuzzer']
    }
    assert expected_dict == unique_branch_dict


def test_get_unique_branch_cov_df():
    """Tests get_unique_branch_cov_df() function."""
    coverage_dict = create_coverage_data()
    benchmark_coverage_dict = coverage_data_utils.get_benchmark_cov_dict(
        coverage_dict, 'libpng-1.2.56')
    unique_branch_dict = coverage_data_utils.get_unique_branch_dict(
        benchmark_coverage_dict)
    fuzzer_names = ['afl', 'libfuzzer']
    unique_branch_df = coverage_data_utils.get_unique_branch_cov_df(
        unique_branch_dict, fuzzer_names)
    unique_branch_df = unique_branch_df.sort_values(by=['fuzzer']).reset_index(
        drop=True)
    expected_df = pd.DataFrame([{
        'fuzzer': 'afl',
        'unique_branches_covered': 1
    }, {
        'fuzzer': 'libfuzzer',
        'unique_branches_covered': 2
    }])
    assert unique_branch_df.equals(expected_df)


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


def test_get_fuzzer_benchmark_covered_branches_filestore_path():
    """Tests that get_fuzzer_benchmark_covered_branches_filestore_path returns
    the correct result."""
    assert (coverage_data_utils.
            get_fuzzer_benchmark_covered_branches_filestore_path(
                FUZZER, BENCHMARK, EXPERIMENT_FILESTORE_PATH) == (
                    'gs://fuzzbench-data/myexperiment/'
                    'coverage/data/libpng-1.2.56/afl/'
                    'covered_branches.json'))


def test_fuzzer_and_benchmark_to_key():
    """Tests that fuzzer_and_benchmark_to_key returns the correct result."""
    assert (coverage_data_utils.fuzzer_and_benchmark_to_key(
        FUZZER, BENCHMARK) == 'afl libpng-1.2.56')


def test_key_to_fuzzer_and_benchmark():
    """Tests that key_to_fuzzer_and_benchmark returns the correct result."""
    assert (coverage_data_utils.key_to_fuzzer_and_benchmark('afl libpng-1.2.56')
            == (FUZZER, BENCHMARK))


def test_fuzzer_benchmark_key_roundtrip():
    """Tests that key_to_fuzzer_and_benchmark(fuzzer_and_benchmark_to_key(X, Y))
    returns (X, Y)."""
    assert (coverage_data_utils.key_to_fuzzer_and_benchmark(
        coverage_data_utils.fuzzer_and_benchmark_to_key(
            FUZZER, BENCHMARK)) == (FUZZER, BENCHMARK))


def test_get_experiment_filestore_path_for_fuzzer_benchmark():
    """Tests that get_experiment_filestore_path_for_fuzzer_benchmark returns the
    right result."""
    filestore_path = (
        coverage_data_utils.get_experiment_filestore_path_for_fuzzer_benchmark(
            FUZZER, BENCHMARK, SAMPLE_DF))
    assert filestore_path == 'gs://fuzzbench-data/exp1'


@mock.patch('analysis.coverage_data_utils.logger.warning')
def test_get_experiment_filestore_path_for_fuzzer_benchmark_multiple(
        mocked_warning):
    """Tests that get_experiment_filestore_path_for_fuzzer_benchmark returns the
    right result when there are multiple filestores for a single pair and that a
    warning is logged.."""
    df = pd.DataFrame([{
        'experiment_filestore': 'gs://fuzzbench-data',
        'experiment': 'exp1',
        'fuzzer': FUZZER,
        'benchmark': BENCHMARK
    }, {
        'experiment_filestore': 'gs://fuzzbench-data2',
        'experiment': 'exp2',
        'fuzzer': FUZZER,
        'benchmark': BENCHMARK
    }])
    filestore_path = (
        coverage_data_utils.get_experiment_filestore_path_for_fuzzer_benchmark(
            FUZZER, BENCHMARK, df))
    assert filestore_path in ('gs://fuzzbench-data/exp1',
                              'gs://fuzzbench-data2/exp2')

    assert mocked_warning.call_count == 1


def test_get_experiment_filestore_paths():
    """Tests that get_experiment_filestore_paths returns the right result."""
    df = pd.DataFrame([{
        'experiment_filestore': 'gs://fuzzbench-data',
        'experiment': 'exp1'
    }, {
        'experiment_filestore': 'gs://fuzzbench-data2',
        'experiment': 'exp2'
    }])
    assert sorted(coverage_data_utils.get_experiment_filestore_paths(df)) == [
        'gs://fuzzbench-data/exp1', 'gs://fuzzbench-data2/exp2'
    ]


def test_coverage_report_filestore_path():
    """Tests that get_coverage_report_filestore_path returns the correct
    result."""
    expected_cov_report_url = ('gs://fuzzbench-data/exp1/coverage/reports/'
                               'libpng-1.2.56/afl/index.html')
    assert coverage_data_utils.get_coverage_report_filestore_path(
        FUZZER, BENCHMARK, SAMPLE_DF) == expected_cov_report_url
