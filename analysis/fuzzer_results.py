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
"""FuzzerResults class."""

import os
import functools

from analysis import data_utils


# pylint: disable=too-many-public-methods, too-many-arguments
class FuzzerResults:
    """Represents results of various analysis done on benchmark data.

    NOTE: Do not create this class manually! Instead, use the |fuzzers|
    property of the ExperimentResults class.

    Each results is a property, which is lazily evaluated and memoized if used
    by other properties. Therefore, when used as a context of a report
    template, properties are computed on demand and only once.
    """

    def __init__(self, fuzzer_name, experiment_df, coverage_dict,
                 output_directory, plotter):
        self.name = fuzzer_name

        self._experiment_df = experiment_df
        self._coverage_dict = coverage_dict
        self._output_directory = output_directory
        self._plotter = plotter

    def _prefix_with_name(self, filename):
        return "{}_{}".format(self.name, filename)

    def _get_full_path(self, filename):
        return os.path.join(self._output_directory, filename)

    @property
    @functools.lru_cache()
    def _experiment_snapshots_df(self):
        """Data frame containing only the time snapshots, for each benchmark,
        based on which we do further analysis, i.e., statistical tests and
        ranking."""
        df = data_utils.get_experiment_snapshots(self._experiment_df)
        df = data_utils.experiment_add_rank_column(df)
        return df

    @property
    @functools.lru_cache()
    def _fuzzer_df(self):
        exp_df = self._experiment_df
        return exp_df[exp_df.fuzzer == self.name]

    @property
    @functools.lru_cache()
    def _fuzzer_snapshot_df(self):
        exp_df = self._experiment_snapshots_df
        print("_fuzzer_snapshot_df", list(exp_df.columns))
        return exp_df[exp_df.fuzzer == self.name]

    @property
    @functools.lru_cache()
    def ntrials(self):
        """Return the number of unique trials for this fuzzer."""
        grouped = self._fuzzer_snapshot_df.groupby('benchmark')
        nunique_trials = grouped['trial_id'].nunique()
        return nunique_trials.min()

    @property
    @functools.lru_cache()
    def ranks(self):
        """Determine rank per benchmark"""
        key = 'edges_covered'
        ranks = self._experiment_snapshots_df.copy()
        ranks = ranks.groupby(['benchmark',
                               'fuzzer']).aggregate({key: 'median'})
        ranks = ranks.groupby('benchmark')[key].rank(method='average',
                                                     ascending=False)
        return ranks[:, self.name]

    @property
    def summary_table(self):
        """Statistical summary table."""
        table = data_utils.fuzzer_summary(self._experiment_snapshots_df)
        table = table[table.fuzzer == self.name]
        visible_columns = [
            'benchmark', 'rank', 'N', 'mean', 'mean_%', 'median', 'median_%',
            'f_max', 'max_%'
        ]
        table = table[visible_columns]
        table = table.sort_values(by=['median_%', 'mean_%', 'rank'],
                                  ascending=[False, False, True])

        col_formats = {
            'rank': "{:.1f}",
            'mean': "{:.0f}",
            'mean_%': "{:.1%}",
            'median': "{:.0f}",
            'median_%': "{:.1%}",
            'max_%': "{:.1%}",
        }

        table = table.style\
                .hide_index()\
                .format(col_formats)\
                .set_properties(**{'font-size': '11pt'})
        return table

    @property
    def average_rank_plot(self):
        """Fuzzer ranking box plot"""
        plot_filename = self._prefix_with_name('ranking.svg')
        self._plotter.write_fuzzer_rank_boxplot(
            self._fuzzer_snapshot_df,
            self._get_full_path(plot_filename),
            wide=True,
            ranks=self.ranks)
        return plot_filename

    @property
    def experiment_relative_max_plot(self):
        """Fuzzer reached region coverage as a percentage of the
        experiment max reached region coverage."""
        plot_filename = self._prefix_with_name('percent_experiment_max.svg')
        self._plotter.write_fuzzer_experiment_max_boxplot(
            self._fuzzer_snapshot_df,
            self._get_full_path(plot_filename),
            wide=True,
            tall=True)
        return plot_filename

    @property
    def fuzzer_relative_max_plot(self):
        """Fuzzer reached region coverage as a percentage of the
        experiment max reached region coverage."""
        plot_filename = self._prefix_with_name('percent_fuzzer_max.svg')
        self._plotter.write_fuzzer_max_boxplot(
            self._fuzzer_snapshot_df,
            self._get_full_path(plot_filename),
            wide=True,
            tall=True)
        return plot_filename

    def _coverage_growth_plot(self, filename, bugs=False, logscale=False):
        """Generic coverage gwoth plot helper function."""
        plot_filename = self._prefix_with_name(filename)
        self._plotter.write_fuzzer_coverage_growth_plot(
            self._fuzzer_df,
            self._get_full_path(plot_filename),
            wide=True,
            logscale=logscale,
            bugs=bugs)
        return plot_filename

    @property
    def fuzzer_coverage_growth_plot(self):
        """Coverage growth plot for all benchmarks."""
        return self._coverage_growth_plot('fuzzer_coverage_growth.svg')

    @property
    def fuzzer_coverage_growth_plot_logscale(self):
        """Coverage growth plot for all benchmarks (logscale)."""
        return self._coverage_growth_plot('fuzzer_coverage_growth_logscale.svg',
                                          logscale=True)

    @property
    def fuzzer_bug_coverage_growth_plot(self):
        """Coverage growth plot for all benchmarks."""
        return self._coverage_growth_plot('fuzzer_coverage_growth.svg',
                                          bugs=True,
                                          logscale=True)

    @property
    def fuzzer_bug_coverage_growth_plot_logscale(self):
        """Coverage growth plot for all benchmarks (logscale)."""
        return self._coverage_growth_plot('fuzzer_coverage_growth_logscale.svg',
                                          bugs=True)
