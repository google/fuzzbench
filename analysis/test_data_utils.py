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

# pylint: disable=missing-function-docstring
"""Tests for data_utils.py"""
import pandas as pd
import pandas.testing as pd_test

from analysis import data_utils


def test_label_fuzzers_by_experiment():
    """Tests that label_fuzzers_by_experiment includes the experiment name in
    the fuzzer name"""
    input_df = pd.DataFrame({
        'experiment': ['experiment-a', 'experiment-b'],
        'fuzzer': ['fuzzer-1', 'fuzzer-2']
    })
    labeled_df = data_utils.label_fuzzers_by_experiment(input_df)

    expected_fuzzers_df = pd.DataFrame(
        {'fuzzer': ['fuzzer-1-experiment-a', 'fuzzer-2-experiment-b']})

    assert (labeled_df['fuzzer'] == expected_fuzzers_df['fuzzer']).all()


def create_trial_data(trial_id, benchmark, fuzzer, reached_coverage):
    """Utility function to create test trial data."""
    return pd.DataFrame([{
        'experiment': 'test_experiment',
        'benchmark': benchmark,
        'fuzzer': fuzzer,
        'trial_id': trial_id,
        'time_started': 0,
        'time_ended': 24,
        'time': t,
        'edges_covered': reached_coverage,
    } for t in range(10)])


def create_experiment_data():
    """Utility function to create test experiment data."""
    return pd.concat([
        create_trial_data(0, 'libpng', 'afl', 100),
        create_trial_data(1, 'libpng', 'afl', 200),
        create_trial_data(2, 'libpng', 'libfuzzer', 200),
        create_trial_data(3, 'libpng', 'libfuzzer', 300),
        create_trial_data(4, 'libxml', 'afl', 1000),
        create_trial_data(5, 'libxml', 'afl', 1200),
        create_trial_data(6, 'libxml', 'libfuzzer', 600),
        create_trial_data(7, 'libxml', 'libfuzzer', 800),
    ])


def test_benchmark_rank_by_mean():
    experiment_df = create_experiment_data()
    benchmark_df = experiment_df[experiment_df.benchmark == 'libxml']
    snapshot_df = data_utils.get_benchmark_snapshot(benchmark_df)
    ranking = data_utils.benchmark_rank_by_mean(snapshot_df)

    expected_ranking = pd.Series(index=['afl', 'libfuzzer'], data=[1100, 700])
    assert ranking.equals(expected_ranking)


def test_benchmark_rank_by_median():
    experiment_df = create_experiment_data()
    benchmark_df = experiment_df[experiment_df.benchmark == 'libxml']
    snapshot_df = data_utils.get_benchmark_snapshot(benchmark_df)
    ranking = data_utils.benchmark_rank_by_median(snapshot_df)

    expected_ranking = pd.Series(index=['afl', 'libfuzzer'], data=[1100, 700])
    assert ranking.equals(expected_ranking)


def test_benchmark_rank_by_average_rank():
    experiment_df = create_experiment_data()
    benchmark_df = experiment_df[experiment_df.benchmark == 'libxml']
    snapshot_df = data_utils.get_benchmark_snapshot(benchmark_df)
    ranking = data_utils.benchmark_rank_by_average_rank(snapshot_df)

    expected_ranking = pd.Series(index=['afl', 'libfuzzer'], data=[3.5, 1.5])
    assert ranking.equals(expected_ranking)


def test_benchmark_rank_by_stat_test_wins():
    experiment_df = create_experiment_data()
    benchmark_df = experiment_df[experiment_df.benchmark == 'libxml']
    snapshot_df = data_utils.get_benchmark_snapshot(benchmark_df)
    ranking = data_utils.benchmark_rank_by_stat_test_wins(snapshot_df)

    expected_ranking = pd.Series(index=['libfuzzer', 'afl'], data=[0, 0])
    assert ranking.equals(expected_ranking)


def test_experiment_pivot_table():
    experiment_df = create_experiment_data()
    snapshots_df = data_utils.get_experiment_snapshots(experiment_df)
    pivot_table = data_utils.experiment_pivot_table(
        snapshots_df, data_utils.benchmark_rank_by_median)

    # yapf: disable
    expected_data = pd.DataFrame([
        {'benchmark': 'libpng', 'fuzzer': 'afl', 'median':  150},
        {'benchmark': 'libpng', 'fuzzer': 'libfuzzer', 'median':  250},
        {'benchmark': 'libxml', 'fuzzer': 'afl', 'median': 1100},
        {'benchmark': 'libxml', 'fuzzer': 'libfuzzer', 'median':  700},
    ])
    # yapf: enable
    expected_pivot_table = pd.pivot_table(expected_data,
                                          index=['benchmark'],
                                          columns=['fuzzer'],
                                          values='median')
    assert pivot_table.equals(expected_pivot_table)


def test_experiment_rank_by_average_rank():
    experiment_df = create_experiment_data()
    snapshots_df = data_utils.get_experiment_snapshots(experiment_df)
    ranking = data_utils.experiment_level_ranking(
        snapshots_df, data_utils.benchmark_rank_by_median,
        data_utils.experiment_rank_by_average_rank)

    expected_ranking = pd.Series(index=['afl', 'libfuzzer'], data=[1.5, 1.5])
    assert ranking.equals(expected_ranking)


def test_experiment_rank_by_num_firsts():
    experiment_df = create_experiment_data()
    snapshots_df = data_utils.get_experiment_snapshots(experiment_df)
    ranking = data_utils.experiment_level_ranking(
        snapshots_df, data_utils.benchmark_rank_by_median,
        data_utils.experiment_rank_by_num_firsts)

    expected_ranking = pd.Series(index=['libfuzzer', 'afl'], data=[1.0, 1.0])
    assert ranking.equals(expected_ranking)


def test_experiment_rank_by_average_normalized_score():
    experiment_df = create_experiment_data()
    snapshots_df = data_utils.get_experiment_snapshots(experiment_df)
    ranking = data_utils.experiment_level_ranking(
        snapshots_df, data_utils.benchmark_rank_by_median,
        data_utils.experiment_rank_by_average_normalized_score)

    expected_ranking = pd.Series(index=['libfuzzer', 'afl'],
                                 data=[81.81, 80.00])
    pd_test.assert_series_equal(ranking,
                                expected_ranking,
                                check_names=False,
                                check_less_precise=True)
