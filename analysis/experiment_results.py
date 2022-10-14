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
import pandas as pd
import seaborn as sns

from analysis import benchmark_results
from analysis import coverage_data_utils
from analysis import data_utils
from analysis import stat_tests


def strip_gs_protocol(url):
    """Removes the leading gs:// from |url|."""
    protocol = 'gs://'
    if url.startswith(protocol):
        return url[len(protocol):]
    return url


class ExperimentResults:  # pylint: disable=too-many-instance-attributes
    """Provides the main interface for getting various analysis results and
    plots about an experiment, represented by |experiment_df|.

    Can be used as the context of template based report generation. Each
    result is a property, which is lazily computed and memorized when
    needed multiple times. Therefore, when used as a context of a report
    template, only the properties needed for the given report will be computed.
    """

    # Summary table style
    _SUMMARY_TABLE_STYLE = [
        dict(selector='td, th',
             props=[('width', '25px'), ('padding', '7px 5px')]),
        dict(selector='th.col_heading',
             props=[('max-width', '25px'), ('overflow', 'visible'),
                    ('transform-origin', 'bottom left'),
                    ('transform', 'translateX(20px) rotate(-45deg)')])
    ]

    def __init__(  # pylint: disable=too-many-arguments
            self,
            experiment_df,
            coverage_dict,
            output_directory,
            plotter,
            experiment_name=None):
        if experiment_name:
            self.name = experiment_name
        else:
            # Take name from first row.
            self.name = experiment_df.experiment.iloc[0]

        # FuzzBench repo commit hash.
        self.git_hash = None
        if 'git_hash' in experiment_df.columns:
            # Not possible to represent hashes for multiple experiments.
            if len(experiment_df.experiment.unique()) == 1:
                self.git_hash = experiment_df.git_hash.iloc[0]

        # Earliest trial start time.
        self.started = experiment_df.time_started.dropna().min()
        # Latest trial end time.
        self.ended = experiment_df.time_ended.dropna().max()

        # Keep a full version of the dataframe (to count unique bugs)
        self._full_experiment_df = experiment_df

        # Keep data frame without non-interesting columns.
        experiment_df = data_utils.drop_uninteresting_columns(experiment_df)

        # Add relative columns (% of experiment max, % of fuzzer max)
        self._experiment_df = data_utils.add_relative_columns(experiment_df)

        # Directory where the rendered plots are written to.
        self._output_directory = output_directory

        self._plotter = plotter

        # Dictionary to store the full coverage data.
        self._coverage_dict = coverage_dict

        self.experiment_filestore = strip_gs_protocol(
            experiment_df.experiment_filestore.iloc[0])

    def _get_full_path(self, filename):
        return os.path.join(self._output_directory, filename)

    def linkify_names(self, df):
        """For any DataFrame which is indexed by fuzzer names, turns the fuzzer
        names into links to their directory with a description on GitHub."""
        assert df.index.name == 'fuzzer'

        def description_link(commit, fuzzer):
            return (f'<a href="https://github.com/google/fuzzbench/blob/'
                    f'{commit}/fuzzers/{fuzzer}">{fuzzer}</a>')

        commit = self.git_hash if self.git_hash else 'master'
        df.index = df.index.map(lambda fuzzer: description_link(commit, fuzzer))
        return df

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
                                               self._coverage_dict,
                                               self._output_directory,
                                               self._plotter)
            for name in sorted(benchmark_names)
        ]

    @property
    @functools.lru_cache()
    def type(self):
        """Returns the type of the experiment i.e., 'code' or 'bug', indicating
        whether the experiments involved code coverage benchmarks or bug
        coverage benchmarks.

        Raises ValueError if the benchmark types are mixed.
        """
        if all(b.type == 'bug' for b in self.benchmarks):
            return 'bug'
        if all(b.type == 'code' for b in self.benchmarks):
            return 'code'
        raise ValueError(
            'Cannot mix bug benchmarks with code coverage benchmarks.')

    @property
    def _relevant_column(self):
        """Returns the name of the column that will be used as the basis of
        the analysis (e.g., 'edges_covered', or 'bugs_covered')."""
        return 'edges_covered' if self.type == 'code' else 'bugs_covered'

    @property
    @functools.lru_cache()
    def summary_table(self):
        """A pivot table of medians for each fuzzer on each benchmark."""
        return data_utils.experiment_pivot_table(
            self._experiment_snapshots_df,
            functools.partial(data_utils.benchmark_rank_by_median,
                              key=self._relevant_column))

    def _relative_summary_table(self, key_column='edges_covered'):
        """A pivot table of medians ( % of experiment max per benchmark )
        for each fuzzer on each benchmark."""
        pivot = data_utils.experiment_pivot_table(
            self._experiment_snapshots_df,
            functools.partial(data_utils.benchmark_rank_by_percent,
                              key=key_column))

        # Remove names
        pivot = pivot.rename_axis(index=None, columns=None)

        # Add rows for Median and Mean values
        nrows, _ = pivot.shape
        pivot.loc['FuzzerMedian'] = pivot.iloc[0:nrows].median()
        pivot.loc['FuzzerMean'] = pivot.iloc[0:nrows].mean()
        # Sort fuzzers left to right by FuzzerMean
        pivot = pivot.sort_values(by='FuzzerMean', axis=1, ascending=False)

        # Move Median and Mean to top rows
        row_index = pivot.index.to_list()
        pivot = pivot.reindex(row_index[-2:] + row_index[:-2])
        # Mean row slicer
        idx = pd.IndexSlice['FuzzerMean', :]

        whbl = sns.light_palette('lightblue', n_colors=30, as_cmap=True)
        pivot = pivot.style\
                .background_gradient(axis=1, cmap=whbl, vmin=95, vmax=100)\
                .highlight_max(axis=1, color='lightgreen')\
                .format("{:.2f}")\
                .apply(data_utils.underline_row, axis=1, subset=idx)\
                .set_table_styles(self._SUMMARY_TABLE_STYLE)
        return pivot

    @property
    @functools.lru_cache()
    def relative_code_summary_table(self):
        """Summary table of median relative code coverage."""
        return self._relative_summary_table()

    @property
    @functools.lru_cache()
    def relative_bug_summary_table(self):
        """Summary table of median relative bug coverage."""
        return self._relative_summary_table(key_column='bugs_covered')

    @property
    def found_bugs_summary_table(self):
        """A pivot table of total found bugs by each fuzzer on each
        bug benchmark."""
        grouping = ['benchmark', 'fuzzer']
        groups = self._full_experiment_df.groupby(grouping).crash_key.nunique()
        groups = groups.reset_index()
        pivot = groups.pivot(index='benchmark',
                             columns='fuzzer',
                             values="crash_key")
        # save fuzzer names
        fuzzer_names = pivot.columns
        pivot['Total'] = self._full_experiment_df.groupby(
            'benchmark').crash_key.nunique()
        pivot = pivot.rename_axis(index=None, columns=None)

        # Add row for sum of all bugs found
        nrows, _ = pivot.shape
        pivot.loc['FuzzerSum'] = pivot.iloc[0:nrows].sum()

        # Move Sum to top row
        row_index = pivot.index.to_list()
        pivot = pivot.reindex(row_index[-1:] + row_index[:-1])
        # Sum row slicer
        idx = pd.IndexSlice['FuzzerSum', :]

        # highlight max (skip all zeros)
        def highlight_max(row):
            if row.sum() == 0:
                return ['' for v in row]
            row_max = row.max()
            is_max = row == row_max
            return ['background-color: lightgreen' if v else '' for v in is_max]

        # Sort fuzzers left to right by FuzzerSum
        pivot = pivot.sort_values(by='FuzzerSum', axis=1, ascending=False)
        pivot = pivot.style\
                .format("{:.0f}")\
                .apply(highlight_max, axis=1, subset=fuzzer_names)\
                .apply(data_utils.underline_row, axis=1, subset=idx)\
                .set_table_styles(self._SUMMARY_TABLE_STYLE)
        return pivot

    @property
    def rank_by_unique_coverage_average_normalized_score(self):
        """Rank fuzzers using average normalized score on unique code coverage
        across benchmarks."""
        benchmarks_unique_coverage_list = [
            benchmark.unique_branch_cov_df for benchmark in self.benchmarks
        ]
        return coverage_data_utils.rank_by_average_normalized_score(
            benchmarks_unique_coverage_list)

    def _ranking(self, benchmark_level_ranking_function,
                 experiment_level_ranking_function):
        return data_utils.experiment_level_ranking(
            self._experiment_snapshots_df,
            functools.partial(benchmark_level_ranking_function,
                              key=self._relevant_column),
            experiment_level_ranking_function)

    @property
    def rank_by_average_rank_and_average_rank(self):
        """Rank fuzzers using average rank per benchmark and average rank
        across benchmarks."""
        return self._ranking(data_utils.benchmark_rank_by_average_rank,
                             data_utils.experiment_rank_by_average_rank)

    @property
    def rank_by_mean_and_average_rank(self):
        """Rank fuzzers using mean coverage per benchmark and average rank
        across benchmarks."""
        return self._ranking(data_utils.benchmark_rank_by_mean,
                             data_utils.experiment_rank_by_average_rank)

    @property
    def rank_by_median_and_average_rank(self):
        """Rank fuzzers using median coverage per benchmark and average rank
        across benchmarks."""
        return self._ranking(data_utils.benchmark_rank_by_median,
                             data_utils.experiment_rank_by_average_rank)

    @property
    def rank_by_median_and_average_normalized_score(self):
        """Rank fuzzers using median coverage per benchmark and average
        normalized score across benchmarks."""
        return self._ranking(
            data_utils.benchmark_rank_by_median,
            data_utils.experiment_rank_by_average_normalized_score)

    @property
    def rank_by_median_and_number_of_firsts(self):
        """Rank fuzzers using median coverage per benchmark and number of first
        places across benchmarks."""
        return self._ranking(data_utils.benchmark_rank_by_median,
                             data_utils.experiment_rank_by_num_firsts)

    @property
    def rank_by_stat_test_wins_and_average_rank(self):
        """Rank fuzzers using statistical test wins per benchmark and average
        rank across benchmarks."""
        return self._ranking(data_utils.benchmark_rank_by_stat_test_wins,
                             data_utils.experiment_rank_by_num_firsts)

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
        average_ranks = self.rank_by_median_and_average_rank
        num_of_benchmarks = self.summary_table.shape[0]

        plot_filename = 'experiment_critical_difference_plot.svg'
        self._plotter.write_critical_difference_plot(
            average_ranks, num_of_benchmarks,
            self._get_full_path(plot_filename))
        return plot_filename
