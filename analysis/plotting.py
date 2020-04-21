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
"""Plotting functions."""

import matplotlib.pyplot as plt
import numpy as np
import Orange
import scikit_posthocs as sp
import seaborn as sns

from analysis import data_utils

_DEFAULT_SPINE_OFFSET = 10
_DEFAULT_TICKS_COUNT = 12
_DEFAULT_LABEL_ROTATION = 30


def _formatted_hour_min(seconds):
    """Turns |seconds| seconds into %H:%m format.

    We don't use to_datetime() or to_timedelta(), because we want to
    show hours larger than 23, e.g.: 24h:00m.
    """
    time_string = ''
    hours = int(seconds / 60 / 60)
    minutes = int(seconds / 60) % 60
    if hours:
        time_string += '%dhr' % hours
    if minutes:
        if hours:
            time_string += ':'
        time_string += '%dmin' % minutes
    return time_string


def _formatted_title(benchmark_snapshot_df):
    """Return a formatted title with time and trial count."""
    benchmark_name = benchmark_snapshot_df.benchmark.unique()[0]
    stats_string = benchmark_name
    stats_string += ' ('

    snapshot_time = benchmark_snapshot_df.time.unique()[0]
    stats_string += _formatted_hour_min(snapshot_time)

    trial_count = benchmark_snapshot_df.fuzzer.value_counts().min()
    stats_string += ', %d trials/fuzzer' % trial_count
    stats_string += ')'
    return stats_string


class Plotter:
    """Plotter that uses the same color for the same fuzzer."""
    # Tableau 20 colors.
    _COLOR_PALETTE = [
        '#1f77b4', '#aec7e8', '#ff7f0e', '#ffbb78', '#2ca02c', '#98df8a',
        '#d62728', '#ff9896', '#9467bd', '#c5b0d5', '#8c564b', '#c49c94',
        '#e377c2', '#f7b6d2', '#7f7f7f', '#c7c7c7', '#bcbd22', '#dbdb8d',
        '#17becf', '#9edae5'
    ]

    def __init__(self, fuzzers, quick):
        """Instantiates plotter with list of |fuzzers|. If |quick| is True,
        creates plots faster but, with less detail.
        """
        self._fuzzer_colors = {
            fuzzer: self._COLOR_PALETTE[idx % len(self._COLOR_PALETTE)]
            for idx, fuzzer in enumerate(sorted(fuzzers))
        }

        self._quick = quick

    # pylint: disable=no-self-use
    def _write_plot_to_image(self,
                             plot_function,
                             data,
                             image_path,
                             wide=False,
                             **kwargs):
        """Writes the result of |plot_function(data)| to |image_path|.

        If |wide|, then the image size will be twice as wide as normal.
        """
        width = 6.4
        height = 4.8
        figsize = (2 * width, height) if wide else (width, height)
        fig, axes = plt.subplots(figsize=figsize)
        try:
            plot_function(data, axes=axes, **kwargs)
            fig.savefig(image_path, bbox_inches="tight")
        finally:
            plt.close(fig)

    def coverage_growth_plot(self, benchmark_df, axes=None):
        """Draws coverage growth plot on given |axes|.

        The fuzzer labels will be in the order of their mean coverage at the
        snapshot time (typically, the end of experiment).
        """
        benchmark_names = benchmark_df.benchmark.unique()
        assert len(benchmark_names) == 1, 'Not a single benchmark data!'

        benchmark_snapshot_df = data_utils.get_benchmark_snapshot(benchmark_df)
        snapshot_time = benchmark_snapshot_df.time.unique()[0]
        fuzzer_order = data_utils.benchmark_rank_by_mean(
            benchmark_snapshot_df).index

        axes = sns.lineplot(
            y='edges_covered',
            x='time',
            hue='fuzzer',
            hue_order=fuzzer_order,
            data=benchmark_df[benchmark_df.time <= snapshot_time],
            ci=None if self._quick else 95,
            palette=self._fuzzer_colors,
            ax=axes)

        sns.despine(offset=_DEFAULT_SPINE_OFFSET, trim=True)

        axes.set_title(_formatted_title(benchmark_snapshot_df))

        # Indicate the snapshot time with a big red vertical line.
        axes.axvline(x=snapshot_time, color='r')

        # Move legend outside of the plot.
        axes.legend(bbox_to_anchor=(1.00, 1),
                    borderaxespad=0,
                    loc='upper left',
                    frameon=False)

        axes.set(ylabel='Edge coverage')
        axes.set(xlabel='Time (hour:minute)')

        ticks = np.arange(
            0,
            snapshot_time + 1,  # Include tick at end time.
            snapshot_time / _DEFAULT_TICKS_COUNT)
        axes.set_xticks(ticks)
        axes.set_xticklabels([_formatted_hour_min(t) for t in ticks])

    def write_coverage_growth_plot(self, benchmark_df, image_path, wide=False):
        """Writes coverage growth plot."""
        self._write_plot_to_image(self.coverage_growth_plot,
                                  benchmark_df,
                                  image_path,
                                  wide=wide)

    def violin_plot(self, benchmark_snapshot_df, axes=None):
        """Draws violin plot.

        The fuzzer labels will be in the order of their median coverage.
        """
        benchmark_names = benchmark_snapshot_df.benchmark.unique()
        assert len(benchmark_names) == 1, 'Not a single benchmark data!'
        assert benchmark_snapshot_df.time.nunique() == 1, 'Not a snapshot!'

        fuzzer_order = data_utils.benchmark_rank_by_median(
            benchmark_snapshot_df).index

        # Another options is to use |boxplot| instead of |violinplot|. With
        # boxplot the median/min/max/etc is more visible than on the violin,
        # especially with distributions with high variance. It does not have
        # however violinplot's kernel density estimation.

        sns.violinplot(y='edges_covered',
                       x='fuzzer',
                       data=benchmark_snapshot_df,
                       order=fuzzer_order,
                       palette=self._fuzzer_colors,
                       ax=axes)

        sns.despine(offset=_DEFAULT_SPINE_OFFSET, trim=True)

        axes.set_title(_formatted_title(benchmark_snapshot_df))
        axes.set(ylabel='Reached edge coverage')
        axes.set(xlabel='Fuzzer (highest median coverage on the left)')
        plt.xticks(rotation=_DEFAULT_LABEL_ROTATION,
                   horizontalalignment='right')

    def write_violin_plot(self, benchmark_snapshot_df, image_path):
        """Writes violin plot."""
        self._write_plot_to_image(self.violin_plot, benchmark_snapshot_df,
                                  image_path)

    def distribution_plot(self, benchmark_snapshot_df, axes=None):
        """Draws distribution plot.

        The fuzzer labels will be in the order of their median coverage.
        """
        benchmark_names = benchmark_snapshot_df.benchmark.unique()
        assert len(benchmark_names) == 1, 'Not a single benchmark data!'
        assert benchmark_snapshot_df.time.nunique() == 1, 'Not a snapshot!'

        fuzzers_in_order = data_utils.benchmark_rank_by_median(
            benchmark_snapshot_df).index
        for fuzzer in fuzzers_in_order:
            measurements_for_fuzzer = benchmark_snapshot_df[
                benchmark_snapshot_df.fuzzer == fuzzer]
            sns.distplot(measurements_for_fuzzer['edges_covered'],
                         hist=False,
                         label=fuzzer,
                         color=self._fuzzer_colors[fuzzer],
                         ax=axes)

        axes.set_title(_formatted_title(benchmark_snapshot_df))
        axes.legend(loc='upper right', frameon=False)

        axes.set(xlabel='Edge coverage')
        axes.set(ylabel='Density')
        plt.xticks(rotation=_DEFAULT_LABEL_ROTATION,
                   horizontalalignment='right')

    def write_distribution_plot(self, benchmark_snapshot_df, image_path):
        """Writes distribution plot."""
        self._write_plot_to_image(self.distribution_plot, benchmark_snapshot_df,
                                  image_path)

    def ranking_plot(self, benchmark_snapshot_df, axes=None):
        """Draws ranking plot.

        The fuzzer labels will be in the order of their median coverage.
        """
        benchmark_names = benchmark_snapshot_df.benchmark.unique()
        assert len(benchmark_names) == 1, 'Not a single benchmark data!'
        assert benchmark_snapshot_df.time.nunique() == 1, 'Not a snapshot!'

        fuzzer_order = data_utils.benchmark_rank_by_median(
            benchmark_snapshot_df).index

        axes = sns.barplot(y='edges_covered',
                           x='fuzzer',
                           data=benchmark_snapshot_df,
                           order=fuzzer_order,
                           estimator=np.median,
                           palette=self._fuzzer_colors,
                           ax=axes)

        sns.despine(offset=_DEFAULT_SPINE_OFFSET, trim=True)

        axes.set_title(_formatted_title(benchmark_snapshot_df))
        axes.set(ylabel='Reached edge coverage')
        axes.set(xlabel='Fuzzer (highest median coverage on the left)')

        plt.xticks(rotation=_DEFAULT_LABEL_ROTATION,
                   horizontalalignment='right')

    def write_ranking_plot(self, benchmark_snapshot_df, image_path):
        """Writes ranking plot."""
        self._write_plot_to_image(self.ranking_plot, benchmark_snapshot_df,
                                  image_path)

    def better_than_plot(self, better_than_table, axes=None):
        """Draws better than plot."""
        cmap = ['white', '#005a32']
        sns.heatmap(better_than_table,
                    vmin=0,
                    vmax=1,
                    cmap=cmap,
                    linewidths=0.5,
                    linecolor='0.5',
                    cbar=False,
                    ax=axes)

        axes.set_title('One-tailed statistical test result')
        axes.set(ylabel='If green, then fuzzer in the row')
        xlabel = 'is statistically significantly better than fuzzer in column.'
        axes.set(xlabel=xlabel)
        plt.xticks(rotation=_DEFAULT_LABEL_ROTATION,
                   horizontalalignment='right')

    def write_better_than_plot(self, better_than_table, image_path):
        """Writes better than plot."""
        self._write_plot_to_image(self.better_than_plot, better_than_table,
                                  image_path)

    def heatmap_plot(self, p_values, axes=None, symmetric=False):
        """Draws heatmap plot for visualizing statistical test results.

        If |symmetric| is enabled, it masks out the upper triangle of the
        p-value table (as it is redundant with the lower triangle).
        """
        if symmetric:
            mask = np.zeros_like(p_values)
            mask[np.triu_indices_from(p_values)] = True

        heatmap_args = {
            'linewidths': 0.5,
            'linecolor': '0.5',
            'clip_on': False,
            'square': True,
            'cbar_ax_bbox': [0.85, 0.35, 0.04, 0.3],
            'mask': mask if symmetric else None
        }
        sp.sign_plot(p_values, ax=axes, **heatmap_args)

    def write_heatmap_plot(self, p_values, image_path, symmetric=False):
        """Writes heatmap plot."""
        self._write_plot_to_image(self.heatmap_plot,
                                  p_values,
                                  image_path,
                                  symmetric=symmetric)

    def write_critical_difference_plot(self, average_ranks, num_of_benchmarks,
                                       image_path):
        """Writes critical difference diagram."""
        critical_difference = Orange.evaluation.compute_CD(
            average_ranks.values, num_of_benchmarks)

        Orange.evaluation.graph_ranks(average_ranks.values, average_ranks.index,
                                      critical_difference)
        fig = plt.gcf()
        try:
            fig.savefig(image_path, bbox_inches="tight")
        finally:
            plt.close(fig)
