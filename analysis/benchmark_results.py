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
"""BenchmarkResults class."""

import os
import functools

from analysis import data_utils
from analysis import coverage_data_utils
from analysis import stat_tests
from common import benchmark_utils
from common import filestore_utils


# pylint: disable=too-many-public-methods, too-many-arguments
class BenchmarkResults:
    """Represents results of various analysis done on benchmark data.

    NOTE: Do not create this class manually! Instead, use the |benchmarks|
    property of the ExperimentResults class.

    Each results is a property, which is lazily evaluated and memoized if used
    by other properties. Therefore, when used as a context of a report
    template, properties are computed on demand and only once.
    """

    def __init__(self, benchmark_name, experiment_df, coverage_dict,
                 output_directory, plotter):
        self.name = benchmark_name

        self._experiment_df = experiment_df
        self._coverage_dict = coverage_dict
        self._output_directory = output_directory
        self._plotter = plotter

    def _prefix_with_benchmark(self, filename):
        return self.name + '_' + filename

    def _get_full_path(self, filename):
        return os.path.join(self._output_directory, filename)

    def get_coverage_report_path(self, fuzzer_name, benchmark_name):
        """Returns the filestore name of the |fuzzer_name|."""
        filestore_path = coverage_data_utils.get_coverage_report_filestore_path(
            fuzzer_name, benchmark_name, self._benchmark_df)
        return filestore_utils.get_user_facing_path(filestore_path)

    @property
    @functools.lru_cache()
    def type(self):
        """Returns the type of the benchmark, which can be 'code' or 'bug',
        depending whether its for measuring code coverage only, or bug coverage
        as well.

        Raises ValueError in case of invalid benchmark type in the config.
        """
        return benchmark_utils.get_type(self.name)

    @property
    def _relevant_column(self):
        """Returns the name of the column that will be used as the basis of
        the analysis (e.g., 'edges_covered', or 'bugs_covered')."""
        return 'edges_covered' if self.type == 'code' else 'bugs_covered'

    @property
    @functools.lru_cache()
    # TODO(lszekeres): With python3.8+, replace above two decorators with:
    # @functools.cached_property
    def _benchmark_df(self):
        exp_df = self._experiment_df
        return exp_df[exp_df.benchmark == self.name]

    @property
    @functools.lru_cache()
    def fuzzer_names(self):
        """Names of all fuzzers."""
        return self._benchmark_df.fuzzer.unique()

    @property
    @functools.lru_cache()
    def _benchmark_snapshot_df(self):
        return data_utils.get_benchmark_snapshot(self._benchmark_df)

    @property
    @functools.lru_cache()
    def _benchmark_coverage_dict(self):
        """Covered branches of each fuzzer on this benchmark."""
        return coverage_data_utils.get_benchmark_cov_dict(
            self._coverage_dict, self.name)

    @property
    @functools.lru_cache()
    def _benchmark_aggregated_coverage_df(self):
        """Aggregated covered branches of each fuzzer on this benchmark."""
        return coverage_data_utils.get_benchmark_aggregated_cov_df(
            self._coverage_dict, self.name)

    @property
    @functools.lru_cache()
    def _unique_branch_dict(self):
        """Unique branches with the fuzzers that cover it."""
        return coverage_data_utils.get_unique_branch_dict(
            self._benchmark_coverage_dict)

    @property
    @functools.lru_cache()
    def unique_branch_cov_df(self):
        """Fuzzers with the number of covered unique branches."""
        return coverage_data_utils.get_unique_branch_cov_df(
            self._unique_branch_dict, self.fuzzer_names)

    @property
    def fuzzers_with_not_enough_samples(self):
        """Fuzzers with not enough samples."""
        return data_utils.get_fuzzers_with_not_enough_samples(
            self._benchmark_snapshot_df)

    @property
    def summary_table(self):
        """Statistical summary table."""
        return data_utils.benchmark_summary(self._benchmark_snapshot_df)

    @property
    def bug_summary_table(self):
        """Statistical summary table."""
        return data_utils.benchmark_summary(self._benchmark_snapshot_df,
                                            key='bugs_covered')

    @property
    def rank_by_mean(self):
        """Fuzzer ranking by mean coverage."""
        return data_utils.benchmark_rank_by_mean(self._benchmark_snapshot_df)

    @property
    def rank_by_median(self):
        """Fuzzer ranking by median coverage."""
        return data_utils.benchmark_rank_by_median(self._benchmark_snapshot_df)

    @property
    def rank_by_average_rank(self):
        """Fuzzer ranking by coverage rank average."""
        return data_utils.benchmark_rank_by_average_rank(
            self._benchmark_snapshot_df)

    @property
    def rank_by_stat_test_wins(self):
        """Fuzzer ranking by then number of pairwise statistical test wins."""
        return data_utils.benchmark_rank_by_stat_test_wins(
            self._benchmark_snapshot_df, key=self._relevant_column)

    @property
    @functools.lru_cache()
    def mann_whitney_p_values(self):
        """Mann Whitney U test result."""
        return stat_tests.two_sided_u_test(self._benchmark_snapshot_df,
                                           key='edges_covered')

    @property
    @functools.lru_cache()
    def bug_mann_whitney_p_values(self):
        """Mann Whitney U test result based on bugs covered."""
        return stat_tests.two_sided_u_test(self._benchmark_snapshot_df,
                                           key='bugs_covered')

    @property
    @functools.lru_cache()
    def vargha_delaney_a12_values(self):
        """Vargha Delaney A12 mesaure results (code coverage)."""
        return stat_tests.a12_measure_test(self._benchmark_snapshot_df)

    @property
    @functools.lru_cache()
    def bug_vargha_delaney_a12_values(self):
        """Vargha Delaney A12 mesaure results (bug coverage)."""
        return stat_tests.a12_measure_test(self._benchmark_snapshot_df,
                                           key='bugs_covered')

    def _mann_whitney_plot(self, filename, p_values):
        """Generic Mann Whitney U test plot."""
        plot_filename = self._prefix_with_benchmark(filename)
        self._plotter.write_heatmap_plot(p_values,
                                         self._get_full_path(plot_filename))
        return plot_filename

    @property
    def mann_whitney_plot(self):
        """Mann Whitney U test plot (code coverage)."""
        return self._mann_whitney_plot('mann_whitney_plot.svg',
                                       self.mann_whitney_p_values)

    @property
    def bug_mann_whitney_plot(self):
        """Mann Whitney U test plot (bug coverage)."""
        return self._mann_whitney_plot('bug_mann_whitney_plot.svg',
                                       self.bug_mann_whitney_p_values)

    def _vargha_delaney_plot(self, filename, a12_values):
        """Generic Vargha Delany A12 measure plot."""
        plot_filename = self._prefix_with_benchmark(filename)
        self._plotter.write_a12_heatmap_plot(a12_values,
                                             self._get_full_path(plot_filename))
        return plot_filename

    @property
    def vargha_delaney_plot(self):
        """Vargha Delany A12 measure plot (code coverage)."""
        return self._vargha_delaney_plot('varga_delaney_a12_plot.svg',
                                         self.vargha_delaney_a12_values)

    @property
    def bug_vargha_delaney_plot(self):
        """Vargha Delany A12 measure plot (bug coverage)."""
        return self._vargha_delaney_plot('bug_varga_delaney_a12_plot.svg',
                                         self.bug_vargha_delaney_a12_values)

    @property
    def anova_p_value(self):
        """ANOVA test result."""
        return stat_tests.anova_test(self._benchmark_snapshot_df,
                                     key=self._relevant_column)

    @property
    @functools.lru_cache()
    def anova_posthoc_p_values(self):
        """ANOVA posthoc test results."""
        return stat_tests.anova_posthoc_tests(self._benchmark_snapshot_df,
                                              key=self._relevant_column)

    @property
    def anova_student_plot(self):
        """ANOVA/Student T posthoc test plot."""
        plot_filename = self._prefix_with_benchmark('anova_student_plot.svg')
        self._plotter.write_heatmap_plot(self.anova_posthoc_p_values['student'],
                                         self._get_full_path(plot_filename))
        return plot_filename

    @property
    def anova_turkey_plot(self):
        """ANOVA/Turkey posthoc test plot."""
        plot_filename = self._prefix_with_benchmark('anova_turkey_plot.svg')
        self._plotter.write_heatmap_plot(self.anova_posthoc_p_values['turkey'],
                                         self._get_full_path(plot_filename))
        return plot_filename

    @property
    def kruskal_p_value(self):
        """Kruskal test result."""
        return stat_tests.kruskal_test(self._benchmark_snapshot_df,
                                       key=self._relevant_column)

    @property
    @functools.lru_cache()
    def kruskal_posthoc_p_values(self):
        """Kruskal posthoc test results."""
        return stat_tests.kruskal_posthoc_tests(self._benchmark_snapshot_df,
                                                key=self._relevant_column)

    @property
    def kruskal_conover_plot(self):
        """Kruskal/Conover posthoc test plot."""
        plot_filename = self._prefix_with_benchmark('kruskal_conover_plot.svg')
        self._plotter.write_heatmap_plot(
            self.kruskal_posthoc_p_values['conover'],
            self._get_full_path(plot_filename))
        return plot_filename

    @property
    def kruskal_mann_whitney_plot(self):
        """Kruskal/Mann-Whitney posthoc test plot."""
        plot_filename = self._prefix_with_benchmark(
            'kruskal_mann_whitney_plot.svg')
        self._plotter.write_heatmap_plot(
            self.kruskal_posthoc_p_values['mann_whitney'],
            self._get_full_path(plot_filename),
            symmetric=True)
        return plot_filename

    @property
    def kruskal_wilcoxon_plot(self):
        """Kruskal/Wilcoxon posthoc test plot."""
        plot_filename = self._prefix_with_benchmark('kruskal_wilcoxon_plot.svg')
        self._plotter.write_heatmap_plot(
            self.kruskal_posthoc_p_values['wilcoxon'],
            self._get_full_path(plot_filename))
        return plot_filename

    @property
    def kruskal_dunn_plot(self):
        """Kruskal/Dunn posthoc test plot."""
        plot_filename = self._prefix_with_benchmark('kruskal_dunn_plot.svg')
        self._plotter.write_heatmap_plot(self.kruskal_posthoc_p_values['dunn'],
                                         self._get_full_path(plot_filename))
        return plot_filename

    @property
    def kruskal_nemenyi_plot(self):
        """Kruskal/Nemenyi posthoc test plot."""
        plot_filename = self._prefix_with_benchmark('kruskal_nemenyi_plot.svg')
        self._plotter.write_heatmap_plot(
            self.kruskal_posthoc_p_values['nemenyi'],
            self._get_full_path(plot_filename))
        return plot_filename

    def _coverage_growth_plot(self, filename, bugs=False, logscale=False):
        """Coverage growth plot helper function"""
        plot_filename = self._prefix_with_benchmark(filename)
        self._plotter.write_coverage_growth_plot(
            self._benchmark_df,
            self._get_full_path(plot_filename),
            wide=True,
            logscale=logscale,
            bugs=bugs)
        return plot_filename

    @property
    def coverage_growth_plot(self):
        """Coverage growth plot (linear scale)."""
        return self._coverage_growth_plot('coverage_growth.svg')

    @property
    def coverage_growth_plot_logscale(self):
        """Coverage growth plot (logscale)."""
        return self._coverage_growth_plot('coverage_growth_logscale.svg',
                                          logscale=True)

    def _generic_violin_plot(self, filename, bugs=False):
        """Violin plot."""
        plot_filename = self._prefix_with_benchmark(filename)
        self._plotter.write_violin_plot(self._benchmark_snapshot_df,
                                        self._get_full_path(plot_filename),
                                        bugs=bugs)
        return plot_filename

    @property
    def violin_plot(self):
        """Branch coverage violin plot."""
        return self._generic_violin_plot('violin.svg')

    @property
    def bug_violin_plot(self):
        """Branch coverage violin plot."""
        return self._generic_violin_plot('bug_violin.svg', bugs=True)

    def _generic_box_plot(self, filename, bugs=False):
        """Generic internal boxplot."""
        plot_filename = self._prefix_with_benchmark(filename)
        self._plotter.write_box_plot(self._benchmark_snapshot_df,
                                     self._get_full_path(plot_filename),
                                     bugs=bugs)
        return plot_filename

    @property
    def box_plot(self):
        """Branch coverage boxplot."""
        return self._generic_box_plot('boxplot.svg')

    @property
    def bug_box_plot(self):
        """Bug coverage boxplot."""
        return self._generic_box_plot('bug_boxplot.svg', bugs=True)

    @property
    def distribution_plot(self):
        """Distribution plot."""
        plot_filename = self._prefix_with_benchmark('distribution.svg')
        self._plotter.write_distribution_plot(
            self._benchmark_snapshot_df, self._get_full_path(plot_filename))
        return plot_filename

    @property
    def ranking_plot(self):
        """Ranking plot."""
        plot_filename = self._prefix_with_benchmark('ranking.svg')
        self._plotter.write_ranking_plot(self._benchmark_snapshot_df,
                                         self._get_full_path(plot_filename))
        return plot_filename

    @property
    def better_than_plot(self):
        """Better than matrix plot."""
        better_than_table = data_utils.create_better_than_table(
            self._benchmark_snapshot_df)
        plot_filename = self._prefix_with_benchmark('better_than.svg')
        self._plotter.write_better_than_plot(better_than_table,
                                             self._get_full_path(plot_filename))
        return plot_filename

    @property
    def unique_coverage_ranking_plot(self):
        """Ranking plot for unique coverage."""
        plot_filename = self._prefix_with_benchmark('ranking_unique_branch.svg')
        unique_branch_cov_df_combined = self.unique_branch_cov_df.merge(
            self._benchmark_aggregated_coverage_df, on='fuzzer')
        self._plotter.write_unique_coverage_ranking_plot(
            unique_branch_cov_df_combined, self._get_full_path(plot_filename))
        return plot_filename

    @property
    @functools.lru_cache()
    def pairwise_unique_coverage_table(self):
        """Pairwise unique coverage table for each pair of fuzzers."""
        fuzzers = self.unique_branch_cov_df.sort_values(
            by='unique_branches_covered', ascending=False).fuzzer
        return coverage_data_utils.get_pairwise_unique_coverage_table(
            self._benchmark_coverage_dict, fuzzers)

    @property
    def pairwise_unique_coverage_plot(self):
        """Pairwise unique coverage plot for each pair of fuzzers."""
        plot_filename = self._prefix_with_benchmark(
            'pairwise_unique_coverage_plot.svg')
        self._plotter.write_pairwise_unique_coverage_heatmap_plot(
            self.pairwise_unique_coverage_table,
            self._get_full_path(plot_filename))
        return plot_filename

    @property
    def bug_coverage_growth_plot(self):
        """Bug coverage growth plot (linear scale)."""
        return self._coverage_growth_plot('bug_coverage_growth_plot.svg',
                                          bugs=True)

    @property
    def bug_coverage_growth_plot_logscale(self):
        """Bug coverage growth plot (logscale)."""
        return self._coverage_growth_plot(
            'bug_coverage_growth_plot_logscale.svg', bugs=True, logscale=True)
