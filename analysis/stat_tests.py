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


def _create_p_value_table(benchmark_snapshot_df,
                          statistical_test,
                          alternative="two-sided"):
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
                                alternative=alternative).pvalue

    groups = benchmark_snapshot_df.groupby('fuzzer')
    samples = groups['edges_covered'].apply(list)
    fuzzers = samples.index

    data = []
    for f_i in fuzzers:
        row = []
        for f_j in fuzzers:
            if f_i == f_j:
                # TODO(lszekeres): With Pandas 1.0.0+, switch to:
                # p_value = pd.NA
                p_value = np.nan
            elif set(samples[f_i]) == set(samples[f_j]):
                p_value = np.nan
            else:
                p_value = test_pair(samples[f_i], samples[f_j])
            row.append(p_value)
        data.append(row)

    p_values = pd.DataFrame(data, index=fuzzers, columns=fuzzers)
    return p_values


def one_sided_u_test(benchmark_snapshot_df):
    """Returns p-value table for one-tailed Mann-Whitney U test."""
    return _create_p_value_table(benchmark_snapshot_df,
                                 ss.mannwhitneyu,
                                 alternative='greater')


def two_sided_u_test(benchmark_snapshot_df):
    """Returns p-value table for two-tailed Mann-Whitney U test."""
    return _create_p_value_table(benchmark_snapshot_df,
                                 ss.mannwhitneyu,
                                 alternative='two-sided')


def one_sided_wilcoxon_test(benchmark_snapshot_df):
    """Returns p-value table for one-tailed Wilcoxon signed-rank test."""
    return _create_p_value_table(benchmark_snapshot_df,
                                 ss.wilcoxon,
                                 alternative='greater')


def two_sided_wilcoxon_test(benchmark_snapshot_df):
    """Returns p-value table for two-tailed Wilcoxon signed-rank test."""
    return _create_p_value_table(benchmark_snapshot_df,
                                 ss.wilcoxon,
                                 alternative='two-sided')


def anova_test(benchmark_snapshot_df):
    """Returns p-value for ANOVA test.

    Results should only considered when we can assume normal distributions.
    """
    groups = benchmark_snapshot_df.groupby('fuzzer')
    sample_groups = groups['edges_covered'].apply(list).values

    _, p_value = ss.f_oneway(*sample_groups)
    return p_value


def anova_posthoc_tests(benchmark_snapshot_df):
    """Returns p-value tables for various ANOVA posthoc tests.

    Results should considered only if ANOVA test rejects null hypothesis.
    """
    common_args = {
        'a': benchmark_snapshot_df,
        'group_col': 'fuzzer',
        'val_col': 'edges_covered',
        'sort': True
    }
    p_adjust = 'holm'

    posthoc_tests = {}
    posthoc_tests['student'] = sp.posthoc_ttest(**common_args,
                                                equal_var=False,
                                                p_adjust=p_adjust)
    posthoc_tests['turkey'] = sp.posthoc_tukey(**common_args)
    return posthoc_tests


def kruskal_test(benchmark_snapshot_df):
    """Returns p-value for Kruskal test."""
    groups = benchmark_snapshot_df.groupby('fuzzer')
    sample_groups = groups['edges_covered'].apply(list).values

    _, p_value = ss.kruskal(*sample_groups)
    return p_value


def kruskal_posthoc_tests(benchmark_snapshot_df):
    """Returns p-value tables for various Kruskal posthoc tests.

    Results should considered only if Kruskal test rejects null hypothesis.
    """
    common_args = {
        'a': benchmark_snapshot_df,
        'group_col': 'fuzzer',
        'val_col': 'edges_covered',
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
