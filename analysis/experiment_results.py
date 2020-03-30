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
"""ExperimentResults class."""

import functools
import os

from analysis import benchmark_results
from analysis import data_utils
from analysis import stat_tests


class ExperimentResults:
    """Provides the main interface for getting various analysis results and
    plots about an experiment, represented by |experiment_df|.

    Can be used as the context of template based report generation. Each
    result is a property, which is lazily computed and memorized when
    needed multiple times. Therefore, when used as a context of a report
    template, only the properties needed for the given report will be computed.
    """

    def __init__(self,
                 experiment_df,
                 output_directory,
                 plotter,
                 experiment_name=None):
        if experiment_name:
            self.name = experiment_name
        else:
            # Take name from first row.
            self.name = experiment_df.experiment[0]

        # FuzzBench repo commit hash.
        self.git_hash = None
        if 'git_hash' in experiment_df.columns:
            # Not possible to represent hashes for multiple experiments.
            if len(experiment_df.experiment.unique()) == 1:
                self.git_hash = experiment_df.git_hash[0]

        # Earliest trial start time.
        self.started = experiment_df.time_started.min()
        # Latest trial end time.
        self.ended = experiment_df.time_ended.max()

        # Keep data frame without non-interesting columns.
        self._experiment_df = data_utils.drop_uninteresting_columns(
            experiment_df)

        # Directory where the rendered plots are written to.
        self._output_directory = output_directory

        self._plotter = plotter

    def _get_full_path(self, filename):
        return os.path.join(self._output_directory, filename)

    @property
    @functools.lru_cache()
    # TODO(lszekeres): With python3.8+, replace above two decorators with:
    # @functools.cached_property
    def _experiment_snapshots_df(self):
        """Data frame containing only the time snapshots, for each benchmark,
        based on which we do further analysis, i.e., statistical tests and
        ranking."""
        return data_utils.get_experiment_snapshots(self._experiment_df)

    @property
    @functools.lru_cache()
    def benchmarks(self):
        """Returns the list of BenchmarkResults.

        This is cheap as no computation is done on the benchmark data,
        until a property is evaluated.
        """
        benchmark_names = self._experiment_df.benchmark.unique()
        return [
            benchmark_results.BenchmarkResults(name, self._experiment_df,
                                               self._output_directory,
                                               self._plotter)
            for name in sorted(benchmark_names)
        ]

    @property
    @functools.lru_cache()
    def summary_table(self):
        """A pivot table of medians for each fuzzer on each benchmark."""
        return data_utils.experiment_pivot_table(self._experiment_snapshots_df,
                                                 data_utils.rank_by_median)

    @property
    def rank_by_mean(self):
        """Ranking across benchmarks (using mean based per-benchmark
        ranking.)"""
        pivot_table_of_means = data_utils.experiment_pivot_table(
            self._experiment_snapshots_df, data_utils.rank_by_mean)
        return data_utils.experiment_rank_by_average_rank(pivot_table_of_means)

    @property
    @functools.lru_cache()
    def rank_by_median(self):
        """Ranking across benchmarks (using median based per-benchmark
        ranking.)"""
        pivot_table_of_medians = data_utils.experiment_pivot_table(
            self._experiment_snapshots_df, data_utils.rank_by_median)
        return data_utils.experiment_rank_by_average_rank(
            pivot_table_of_medians)

    @property
    def rank_by_average_rank(self):
        """Ranking across benchmarks (using rank average based per-benchmark
        ranking.)"""
        pivot_table_of_average_ranks = data_utils.experiment_pivot_table(
            self._experiment_snapshots_df, data_utils.rank_by_average_rank)
        return data_utils.experiment_rank_by_average_rank(
            pivot_table_of_average_ranks)

    @property
    def rank_by_stat_test_wins(self):
        """Ranking across benchmarks (using statistical test wins based per-
        benchmark ranking.)"""
        pivot_table_of_stat_test_wins = data_utils.experiment_pivot_table(
            self._experiment_snapshots_df, data_utils.rank_by_average_rank)
        return data_utils.experiment_rank_by_average_rank(
            pivot_table_of_stat_test_wins)

    @property
    def friedman_p_value(self):
        """Friedman test result."""
        return stat_tests.friedman_test(self.summary_table)

    @property
    @functools.lru_cache()
    def friedman_posthoc_p_values(self):
        """Friedman posthoc test results."""
        return stat_tests.friedman_posthoc_tests(self.summary_table)

    @property
    def friedman_conover_plot(self):
        """Friedman/Conover posthoc test result plot."""
        plot_filename = 'experiment_friedman_conover_plot.svg'
        self._plotter.write_heatmap_plot(
            self.friedman_posthoc_p_values['conover'],
            self._get_full_path(plot_filename),
            symmetric=True)
        return plot_filename

    @property
    def friedman_nemenyi_plot(self):
        """Friedman/Nemenyi posthoc test result plot."""
        plot_filename = 'experiment_friedman_nemenyi_plot.svg'
        self._plotter.write_heatmap_plot(
            self.friedman_posthoc_p_values['nemenyi'],
            self._get_full_path(plot_filename),
            symmetric=True)
        return plot_filename

    @property
    def critical_difference_plot(self):
        """Critical difference diagram.

        Represents average ranks of fuzzers across all benchmarks,
        considering medians on final coverage.
        """
        average_ranks = self.rank_by_median
        num_of_benchmarks = self.summary_table.shape[0]

        plot_filename = 'experiment_critical_difference_plot.svg'
        self._plotter.write_critical_difference_plot(
            average_ranks, num_of_benchmarks,
            self._get_full_path(plot_filename))
        return plot_filename
