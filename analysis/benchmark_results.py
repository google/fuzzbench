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
from analysis import stat_tests


class BenchmarkResults:  # pylint: disable=too-many-public-methods
    """Represents results of various analysis done on benchmark data.

    NOTE: Do not create this class manually! Instead, use the |benchmarks|
    property of the ExperimentResults class.

    Each results is a property, which is lazily evaluated and memoized if used
    by other properties. Therefore, when used as a context of a report
    template, properties are computed on demand and only once.
    """

    def __init__(self, benchmark_name, experiment_df, output_directory,
                 plotter):
        self.name = benchmark_name

        self._experiment_df = experiment_df
        self._output_directory = output_directory
        self._plotter = plotter

    def _prefix_with_benchmark(self, filename):
        return self.name + '_' + filename

    def _get_full_path(self, filename):
        return os.path.join(self._output_directory, filename)

    @property
    @functools.lru_cache()
    # TODO(lszekeres): With python3.8+, replace above two decorators with:
    # @functools.cached_property
    def _benchmark_df(self):
        exp_df = self._experiment_df
        return exp_df[exp_df.benchmark == self.name]

    @property
    @functools.lru_cache()
    def _benchmark_snapshot_df(self):
        return data_utils.get_benchmark_snapshot(self._benchmark_df)

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
            self._benchmark_snapshot_df)

    @property
    @functools.lru_cache()
    def mann_whitney_p_values(self):
        """Mann Whitney U test result."""
        return stat_tests.two_sided_u_test(self._benchmark_snapshot_df)

    @property
    def mann_whitney_plot(self):
        """Mann Whitney U test plot."""
        plot_filename = self._prefix_with_benchmark('mann_whitney_plot.svg')
        self._plotter.write_heatmap_plot(self.mann_whitney_p_values,
                                         self._get_full_path(plot_filename))
        return plot_filename

    @property
    def anova_p_value(self):
        """ANOVA test result."""
        return stat_tests.anova_test(self._benchmark_snapshot_df)

    @property
    @functools.lru_cache()
    def anova_posthoc_p_values(self):
        """ANOVA posthoc test results."""
        return stat_tests.anova_posthoc_tests(self._benchmark_snapshot_df)

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
        return stat_tests.kruskal_test(self._benchmark_snapshot_df)

    @property
    @functools.lru_cache()
    def kruskal_posthoc_p_values(self):
        """Kruskal posthoc test results."""
        return stat_tests.kruskal_posthoc_tests(self._benchmark_snapshot_df)

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

    @property
    def coverage_growth_plot(self):
        """Coverage growth plot."""
        plot_filename = self._prefix_with_benchmark('coverage_growth.svg')
        self._plotter.write_coverage_growth_plot(
            self._benchmark_df, self._get_full_path(plot_filename), wide=True)
        return plot_filename

    @property
    def violin_plot(self):
        """Violin plot."""
        plot_filename = self._prefix_with_benchmark('violin.svg')
        self._plotter.write_violin_plot(self._benchmark_snapshot_df,
                                        self._get_full_path(plot_filename))
        return plot_filename

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
