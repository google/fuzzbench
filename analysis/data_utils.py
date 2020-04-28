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
"""Utility functions for data (frame) transformations."""

# score.rename('stat wins', inplace=True) in rank_by_stat_test_wins breaks
# pylint and causes it to stack overflow. Don't lint this file because of it.
# pylint: skip-file

from analysis import stat_tests


def validate_data(experiment_df):
    """Checks if the experiment data is valid."""
    if experiment_df.empty:
        raise ValueError('Empty experiment data.')

    expected_columns = {
        'experiment', 'benchmark', 'fuzzer', 'trial_id', 'time_started',
        'time_ended', 'time', 'edges_covered'
    }
    missing_columns = expected_columns.difference(experiment_df.columns)
    if missing_columns:
        raise ValueError(
            'Missing columns in experiment data: {}'.format(missing_columns))


def drop_uninteresting_columns(experiment_df):
    """Returns table with only interesting columns."""
    return experiment_df[[
        'benchmark', 'fuzzer', 'trial_id', 'time', 'edges_covered'
    ]]


def filter_fuzzers(experiment_df, included_fuzzers):
    """Returns table with only rows where fuzzer is in |included_fuzzers|."""
    return experiment_df[experiment_df['fuzzer'].isin(included_fuzzers)]


def filter_benchmarks(experiment_df, included_benchmarks):
    """Returns table with only rows where benchmark is in
    |included_benchmarks|."""
    return experiment_df[experiment_df['benchmark'].isin(included_benchmarks)]


def label_fuzzers_by_experiment(experiment_df):
    """Returns table where every fuzzer is labeled by the experiment it
    was run in."""
    experiment_df['fuzzer'] = (experiment_df['fuzzer'] + '-' +
                               experiment_df['experiment'])

    return experiment_df


def filter_max_time(experiment_df, max_time):
    """Returns table with snapshots that have time less than or equal to
    |max_time|."""
    return experiment_df[experiment_df['time'] <= max_time]


# Creating "snapshots" (see README.md for definition).

_DEFAULT_BENCHMARK_SAMPLE_NUM_THRESHOLD = 0.8


def get_benchmark_snapshot(benchmark_df,
                           threshold=_DEFAULT_BENCHMARK_SAMPLE_NUM_THRESHOLD):
    """Finds the latest time where 80% of the trials were still running. In most
    cases, this is the end of the experiment. In this case, we won't consider
    the <20% of the trials that ended early for our analysis. If more than 20%
    of the trials ended early, it's better to pick an earlier snapshot time.
    The 80% can be overridden using the |threshold| argument. E.g., to find the
    latest time where each trials were running, set |threshold| to 1.0.

    Returns data frame that only contains the measurements of the picked
    snapshot time.
    """
    num_trials = benchmark_df.trial_id.nunique()
    trials_running_at_time = benchmark_df.time.value_counts()
    criteria = trials_running_at_time > threshold * num_trials
    ok_times = trials_running_at_time[criteria]
    latest_ok_time = ok_times.index.max()
    benchmark_snapshot_df = benchmark_df[benchmark_df.time == latest_ok_time]
    return benchmark_snapshot_df


_DEFAULT_FUZZER_SAMPLE_NUM_THRESHOLD = 0.8


def get_fuzzers_with_not_enough_samples(
        benchmark_snapshot_df, threshold=_DEFAULT_FUZZER_SAMPLE_NUM_THRESHOLD):
    """Retruns fuzzers that didn't have enough trials running at snapshot time.
    It takes a benchmark snapshot and finds the fuzzers that have a sample size
    smaller than 80% of the largest sample size. Default threshold can be
    overridden.
    """
    samples_per_fuzzer = benchmark_snapshot_df.fuzzer.value_counts()
    max_samples = samples_per_fuzzer.max()
    few_sample_criteria = samples_per_fuzzer < threshold * max_samples
    few_sample_fuzzers = samples_per_fuzzer[few_sample_criteria].index
    return few_sample_fuzzers.tolist()


def get_experiment_snapshots(experiment_df):
    """Finds a good snapshot time for each benchmark in the experiment data.

    Returns the data frame that only contains the measurements made at these
    snapshot times.
    """
    benchmark_groups = experiment_df.groupby('benchmark')
    experiment_snapshots = benchmark_groups.apply(get_benchmark_snapshot)
    # We don't need the extra index added by the groupby('benchmark').
    experiment_snapshots.reset_index(drop=True, inplace=True)
    return experiment_snapshots


# Summary tables containing statistics on the samples.


def benchmark_summary(benchmark_snapshot_df):
    """Creates summary table for a benchmark snapshot with columns:
    |fuzzer|time||count|mean|std|min|25%|median|75%|max|
    """
    groups = benchmark_snapshot_df.groupby(['fuzzer', 'time'])
    summary = groups['edges_covered'].describe()
    summary.rename(columns={'50%': 'median'}, inplace=True)
    return summary.sort_values(('median'), ascending=False)


def experiment_summary(experiment_snapshots_df):
    """Creates summary table for all benchmarks in experiment, i.e. table like:
    |benchmark|| < benchmark level summary >
    """
    groups = experiment_snapshots_df.groupby('benchmark')
    summaries = groups.apply(benchmark_summary)
    return summaries


# Per-benchmark fuzzer ranking options.


def benchmark_rank_by_mean(benchmark_snapshot_df):
    """Returns ranking of fuzzers based on mean coverage."""
    assert benchmark_snapshot_df.time.nunique() == 1, 'Not a snapshot!'
    means = benchmark_snapshot_df.groupby('fuzzer')['edges_covered'].mean()
    means.rename('mean cov', inplace=True)
    return means.sort_values(ascending=False)


def benchmark_rank_by_median(benchmark_snapshot_df):
    """Returns ranking of fuzzers based on median coverage."""
    assert benchmark_snapshot_df.time.nunique() == 1, 'Not a snapshot!'
    medians = benchmark_snapshot_df.groupby('fuzzer')['edges_covered'].median()
    medians.rename('median cov', inplace=True)
    return medians.sort_values(ascending=False)


def benchmark_rank_by_average_rank(benchmark_snapshot_df):
    """Ranks all coverage measurements in the snapshot across fuzzers.

    Returns the average rank by fuzzer.
    """
    # Make a copy of the dataframe view, because we want to add a new column.
    measurements = benchmark_snapshot_df[['fuzzer', 'edges_covered']].copy()
    measurements['rank'] = measurements['edges_covered'].rank()
    avg_rank = measurements.groupby('fuzzer').mean()
    avg_rank.rename(columns={'rank': 'avg rank'}, inplace=True)
    avg_rank.sort_values('avg rank', ascending=False, inplace=True)
    return avg_rank['avg rank']


def benchmark_rank_by_stat_test_wins(benchmark_snapshot_df):
    """Carries out one-tailed statistical tests for each fuzzer pair.

    Returns ranking according to the number of statistical test wins.
    """
    p_values = stat_tests.one_sided_u_test(benchmark_snapshot_df)

    # Turn "significant" p-values into 1-s.
    better_than = p_values.applymap(
        lambda p: p < stat_tests.SIGNIFICANCE_THRESHOLD)
    better_than = better_than.applymap(int)

    score = better_than.sum(axis=1).sort_values(ascending=False)
    score.rename('stat wins', inplace=True)

    return score


def create_better_than_table(benchmark_snapshot_df):
    """Creates table showing whether fuzzer in row is statistically
    significantly better than the fuzzer in the column."""
    p_values = stat_tests.one_sided_u_test(benchmark_snapshot_df)

    # Turn "significant" p-values into 1-s.
    better_than = p_values.applymap(
        lambda p: p < stat_tests.SIGNIFICANCE_THRESHOLD)
    better_than = better_than.applymap(int)

    # Order rows and columns of matrix according to score ranking.
    score = better_than.sum(axis=1).sort_values(ascending=False)
    better_than = better_than.reindex(index=score.index,
                                      columns=score.index[::-1])
    return better_than


# Experiment level ranking of fuzzers (across-benchmarks).
# Experiment level ranking depends on the per-benchmark ranking method.


def experiment_pivot_table(experiment_snapshots_df,
                           benchmark_level_ranking_function):
    """Creates a pivot table according to a given per benchmark ranking, where
    the columns are the fuzzers, the rows are the benchmarks, and the values
    are the scores according to the per benchmark ranking."""
    benchmark_blocks = experiment_snapshots_df.groupby('benchmark')
    groups_ranked = benchmark_blocks.apply(benchmark_level_ranking_function)
    already_unstacked = groups_ranked.index.names == ['benchmark']
    pivot_df = groups_ranked if already_unstacked else groups_ranked.unstack()
    return pivot_df


def experiment_rank_by_average_rank(experiment_pivot_df):
    """Creates experiment level ranking of fuzzers.

    Takes a pivot table representing per benchmark ranking scores. Ranks
    fuzzers per benchmark, then takes the average rank across benchmarks
    (smaller is better).
    """
    # Rank fuzzers in each benchmark block.
    pivot_ranked = experiment_pivot_df.rank('columns',
                                            na_option='keep',
                                            ascending=False)
    average_ranks = pivot_ranked.mean().sort_values()
    return average_ranks.rename('average rank')


def experiment_rank_by_num_firsts(experiment_pivot_df):
    """Creates experiment level ranking by number of first places in per
    benchmark rankings (higher is better)."""
    # Rank fuzzers in each benchmark block.
    pivot_ranked = experiment_pivot_df.rank('columns',
                                            na_option='keep',
                                            ascending=False)
    # Count first places for each fuzzer.
    firsts = pivot_ranked[pivot_ranked == 1]
    num_firsts = firsts.sum().sort_values(ascending=False)
    return num_firsts.rename('number of wins')


def experiment_rank_by_average_normalized_score(experiment_pivot_df):
    """Creates experiment level ranking by taking the average of normalized per
    benchmark scores from 0 to 100, where 100 is the highest reach coverage."""
    # Normalize coverage values.
    benchmark_maximum = experiment_pivot_df.max(axis='columns')
    normalized_score = experiment_pivot_df.div(benchmark_maximum,
                                               axis='index').mul(100)

    average_score = normalized_score.mean().sort_values(ascending=False)
    return average_score.rename('average normalized score')


def experiment_level_ranking(experiment_snapshots_df,
                             benchmark_level_ranking_function,
                             experiment_level_ranking_function):
    pivot_table = experiment_pivot_table(experiment_snapshots_df,
                                         benchmark_level_ranking_function)
    return experiment_level_ranking_function(pivot_table)
