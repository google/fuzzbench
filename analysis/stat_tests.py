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
"""Statistical tests."""

import numpy as np
import pandas as pd
import scikit_posthocs as sp
import scipy.stats as ss

SIGNIFICANCE_THRESHOLD = 0.05


def _create_pairwise_table(benchmark_snapshot_df,
                           key,
                           statistical_test,
                           alternative="two-sided",
                           statistic='pvalue'):
    """Given a benchmark snapshot data frame and a statistical test function,
    returns a p-value table. The |alternative| parameter defines the alternative
    hypothesis to be tested. Use "two-sided" for two-tailed (default), and
    "greater" or "less" for one-tailed test.

    The p-value table is a square matrix where each row and column represents a
    fuzzer, and each cell contains the resulting p-value of the pairwise
    statistical test of the fuzzer in the row and column of the cell.
    """

    def test_pair(measurements_x, measurements_y):
        return statistical_test(measurements_x,
                                measurements_y,
                                alternative=alternative)

    groups = benchmark_snapshot_df.groupby('fuzzer')
    samples = groups[key].apply(list)
    fuzzers = samples.index

    data = []
    for f_i in fuzzers:
        row = []
        for f_j in fuzzers:
            value = np.nan
            if f_i != f_j and set(samples[f_i]) != set(samples[f_j]):
                res = test_pair(samples[f_i], samples[f_j])
                value = getattr(res, statistic, np.nan)
            row.append(value)
        data.append(row)

    p_values = pd.DataFrame(data, index=fuzzers, columns=fuzzers)
    return p_values


def one_sided_u_test(benchmark_snapshot_df, key):
    """Returns p-value table for one-tailed Mann-Whitney U test."""
    return _create_pairwise_table(benchmark_snapshot_df,
                                  key,
                                  ss.mannwhitneyu,
                                  alternative='greater')


def two_sided_u_test(benchmark_snapshot_df, key):
    """Returns p-value table for two-tailed Mann-Whitney U test."""
    return _create_pairwise_table(benchmark_snapshot_df,
                                  key,
                                  ss.mannwhitneyu,
                                  alternative='two-sided')


def one_sided_wilcoxon_test(benchmark_snapshot_df, key):
    """Returns p-value table for one-tailed Wilcoxon signed-rank test."""
    return _create_pairwise_table(benchmark_snapshot_df,
                                  key,
                                  ss.wilcoxon,
                                  alternative='greater')


def two_sided_wilcoxon_test(benchmark_snapshot_df, key):
    """Returns p-value table for two-tailed Wilcoxon signed-rank test."""
    return _create_pairwise_table(benchmark_snapshot_df,
                                  key,
                                  ss.wilcoxon,
                                  alternative='two-sided')


def a_measure_test(benchmark_snapshot_df, key='edges_covered'):
    """Returns a Vargha-Delaney A measure table."""
    return _create_pairwise_table(benchmark_snapshot_df,
                                  key,
                                  a12,
                                  statistic='a12')


def anova_test(benchmark_snapshot_df, key):
    """Returns p-value for ANOVA test.

    Results should only considered when we can assume normal distributions.
    """
    groups = benchmark_snapshot_df.groupby('fuzzer')
    sample_groups = groups[key].apply(list).values

    _, p_value = ss.f_oneway(*sample_groups)
    return p_value


def anova_posthoc_tests(benchmark_snapshot_df, key):
    """Returns p-value tables for various ANOVA posthoc tests.

    Results should considered only if ANOVA test rejects null hypothesis.
    """
    common_args = {
        'a': benchmark_snapshot_df,
        'group_col': 'fuzzer',
        'val_col': key,
        'sort': True
    }
    p_adjust = 'holm'

    posthoc_tests = {}
    posthoc_tests['student'] = sp.posthoc_ttest(**common_args,
                                                equal_var=False,
                                                p_adjust=p_adjust)
    posthoc_tests['turkey'] = sp.posthoc_tukey(**common_args)
    return posthoc_tests


def kruskal_test(benchmark_snapshot_df, key):
    """Returns p-value for Kruskal test."""
    groups = benchmark_snapshot_df.groupby('fuzzer')
    sample_groups = groups[key].apply(list).values

    _, p_value = ss.kruskal(*sample_groups)
    return p_value


def kruskal_posthoc_tests(benchmark_snapshot_df, key):
    """Returns p-value tables for various Kruskal posthoc tests.

    Results should considered only if Kruskal test rejects null hypothesis.
    """
    common_args = {
        'a': benchmark_snapshot_df,
        'group_col': 'fuzzer',
        'val_col': key,
        'sort': True
    }
    p_adjust = 'holm'

    posthoc_tests = {}
    posthoc_tests['mann_whitney'] = sp.posthoc_mannwhitney(**common_args,
                                                           p_adjust=p_adjust)
    posthoc_tests['conover'] = sp.posthoc_conover(**common_args,
                                                  p_adjust=p_adjust)
    posthoc_tests['wilcoxon'] = sp.posthoc_wilcoxon(**common_args,
                                                    p_adjust=p_adjust)
    posthoc_tests['dunn'] = sp.posthoc_dunn(**common_args, p_adjust=p_adjust)
    posthoc_tests['nemenyi'] = sp.posthoc_nemenyi(**common_args)

    return posthoc_tests


def friedman_test(experiment_pivot_df):
    """Returns p-value for Friedman test."""
    pivot_df_as_matrix = experiment_pivot_df.values
    _, p_value = ss.friedmanchisquare(*pivot_df_as_matrix)
    return p_value


def friedman_posthoc_tests(experiment_pivot_df):
    """Returns p-value tables for various Friedman posthoc tests.

    Results should considered only if Friedman test rejects null hypothesis.
    """
    posthoc_tests = {}
    posthoc_tests['conover'] = sp.posthoc_conover_friedman(experiment_pivot_df)
    posthoc_tests['nemenyi'] = sp.posthoc_nemenyi_friedman(experiment_pivot_df)
    return posthoc_tests


class Result:
    """Anonymous class, like a namedtuple, but more flexible"""

    def __init__(self, **kwds):
        self.__dict__.update(kwds)


def a12(measurements_x, measurements_y, alternative=None):
    """Returns Vargha-Delaney A12 measure effect size for two distributions

    A. Vargha and H. D. Delaney.
    A critique and improvement of the CL common language effect size statistics of McGraw and Wong.
    Journal of Educational and Behavioral Statistics, 25(2):101-132, 2000

    The Vargha and Delaney A12 statistic is a non-parametric effect size
    measure.

    The formula to compute A has been transformed to minimize accuracy errors
    See: http://mtorchiano.wordpress.com/2014/05/19/effect-size-of-r-precision/

    Significant levels from original paper:
      Large   is > 0.714
      Mediumm is > 0.638
      Small   is > 0.556

    Given observations of a metric (edges_covered or bugs_covered) for
    fuzzer 1 (F2) and fuzzer 2 (F2), the A12 measures the probability that
    running fuzzer 1 will yield a higher metric than running fuzzer 2."""

    x = np.asarray(measurements_x)
    y = np.asarray(measurements_y)
    n1, n2 = x.size, y.size
    ranked = ss.rankdata(np.concatenate((x, y)))
    rank_x = ranked[0:n1]  # get the x-ranks

    # Compute the A12 measure
    R1 = rank_x.sum()
    # A = (R1/n1 - (n1+1)/2)/n2 # formula (14) in Vargha and Delaney, 2000
    A = (2 * R1 - n1 * (n1 + 1)) / (
        2 * n2 * n1)  # equivalent formula to avoid accuracy errors
    return Result(a12=A)


def benchmark_a12(benchmark_snapshot_df, f1, f2, key='edges_covered'):
    """Compute Vargha-Delaney A measure given a benchmark snapshot and the names
    of two fuzzers to compare."""
    df = benchmark_snapshot_df
    f1_metric = df[df.fuzzer == f1][key]
    f2_metric = df[df.fuzzer == f2][key]
    return a12(f1_metric, f2_metric).a12
