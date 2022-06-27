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
import matplotlib.colors as colors
import numpy as np
import Orange
import seaborn as sns

from analysis import data_utils
from common import experiment_utils

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
        time_string += '%dh' % hours
    if minutes:
        if hours:
            time_string += ':'
        time_string += '%dm' % minutes
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
        '#1f77b4',
        '#98df8a',
        '#d62728',
        '#c7c7c7',
        '#ff7f0e',
        '#ff9896',
        '#e377c2',
        '#dbdb8d',
        '#2ca02c',
        '#c5b0d5',
        '#7f7f7f',
        '#9edae5',
        '#aec7e8',
        '#8c564b',
        '#c49c94',
        '#bcbd22',
        '#ffbb78',
        '#9467bd',
        '#f7b6d2',
        '#17becf',
    ]

    # We need a manually specified marker list due to:
    # https://github.com/mwaskom/seaborn/issues/1513
    # We specify 20 markers for the 20 colors above.
    _MARKER_PALETTE = [
        'o', 'v', '^', '<', '>', '8', 's', 'p', '*', 'h', 'H', 'D', 'd', 'P',
        'X', ',', '+', 'x', '|', '_'
    ]

    def __init__(self, fuzzers, quick=False, logscale=False):
        """Instantiates plotter with list of |fuzzers|. If |quick| is True,
        creates plots faster but, with less detail.
        """
        self._fuzzer_colors = {
            fuzzer: self._COLOR_PALETTE[idx % len(self._COLOR_PALETTE)]
            for idx, fuzzer in enumerate(sorted(fuzzers))
        }
        self._fuzzer_markers = {
            fuzzer: self._MARKER_PALETTE[idx % len(self._MARKER_PALETTE)]
            for idx, fuzzer in enumerate(sorted(fuzzers))
        }

        self._quick = quick
        self._logscale = logscale

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

    def _common_datafame_checks(self, benchmark_df, snapshot=False):
        """Assertions common to several plotting functions."""
        benchmark_names = benchmark_df.benchmark.unique()
        assert len(benchmark_names) == 1, 'Not a single benchmark data!'
        if snapshot:
            assert benchmark_df.time.nunique() == 1, 'Not a snapshot!'

    def coverage_growth_plot(self,
                             benchmark_df,
                             axes=None,
                             logscale=False,
                             bugs=False):
        """Draws edge (or bug) coverage growth plot on given |axes|.

        The fuzzer labels will be in the order of their mean coverage at the
        snapshot time (typically, the end of experiment).
        """
        self._common_datafame_checks(benchmark_df)

        column_of_interest = 'bugs_covered' if bugs else 'edges_covered'

        benchmark_snapshot_df = data_utils.get_benchmark_snapshot(benchmark_df)
        snapshot_time = benchmark_snapshot_df.time.unique()[0]
        fuzzer_order = data_utils.benchmark_rank_by_mean(
            benchmark_snapshot_df, key=column_of_interest).index

        axes = sns.lineplot(
            y=column_of_interest,
            x='time',
            hue='fuzzer',
            hue_order=fuzzer_order,
            data=benchmark_df[benchmark_df.time <= snapshot_time],
            ci=None if bugs or self._quick else 95,
            estimator=np.median,
            palette=self._fuzzer_colors,
            style='fuzzer',
            dashes=False,
            markers=self._fuzzer_markers,
            ax=axes)

        axes.set_title(_formatted_title(benchmark_snapshot_df))

        # Indicate the snapshot time with a big red vertical line.
        axes.axvline(x=snapshot_time, color='r')

        # Move legend outside of the plot.
        axes.legend(bbox_to_anchor=(1.00, 1),
                    borderaxespad=0,
                    loc='upper left',
                    frameon=False)

        axes.set(ylabel='Bug coverage' if bugs else 'Code branch coverage')
        axes.set(xlabel='Time (hour:minute)')

        if self._logscale or logscale:
            axes.set_xscale('log')
            ticks = np.logspace(
                # Start from the time of the first measurement.
                np.log10(experiment_utils.DEFAULT_SNAPSHOT_SECONDS),
                np.log10(snapshot_time + 1),  # Include tick at end time.
                _DEFAULT_TICKS_COUNT)
        else:
            ticks = np.arange(
                experiment_utils.DEFAULT_SNAPSHOT_SECONDS,
                snapshot_time + 1,  # Include tick at end time.
                snapshot_time / _DEFAULT_TICKS_COUNT)

        axes.set_xticks(ticks)
        axes.set_xticklabels([_formatted_hour_min(t) for t in ticks])

        sns.despine(ax=axes, trim=True)

    def write_coverage_growth_plot(  # pylint: disable=too-many-arguments
            self,
            benchmark_df,
            image_path,
            wide=False,
            logscale=False,
            bugs=False):
        """Writes coverage growth plot."""
        self._write_plot_to_image(self.coverage_growth_plot,
                                  benchmark_df,
                                  image_path,
                                  wide=wide,
                                  logscale=logscale,
                                  bugs=bugs)

    def box_or_violin_plot(self,
                           benchmark_snapshot_df,
                           axes=None,
                           bugs=False,
                           violin=False):
        """Draws a box or violin plot based on parameter.

        The fuzzer labels will be in the order of their median coverage.
        With boxplot the median/min/max/etc is more visible than on the violin,
        especially with distributions with high variance. It does not have
        however violinplot's kernel density estimation.
        """
        self._common_datafame_checks(benchmark_snapshot_df, snapshot=True)

        column_of_interest = 'bugs_covered' if bugs else 'edges_covered'

        fuzzer_order = data_utils.benchmark_rank_by_median(
            benchmark_snapshot_df, key=column_of_interest).index

        mean_props = {
            'markersize': '10',
            'markeredgecolor': 'black',
            'markerfacecolor': 'white'
        }

        common_args = dict(y=column_of_interest,
                           x='fuzzer',
                           data=benchmark_snapshot_df,
                           order=fuzzer_order,
                           ax=axes)

        if violin:
            sns.violinplot(**common_args, palette=self._fuzzer_colors)

        else:
            sns.boxplot(**common_args,
                        palette=self._fuzzer_colors,
                        showmeans=True,
                        meanprops=mean_props)

            sns.stripplot(**common_args, size=3, color="black", alpha=0.6)

        axes.set_title(_formatted_title(benchmark_snapshot_df))
        ylabel = 'Reached {} coverage'.format('bug' if bugs else 'branch')
        axes.set(ylabel=ylabel)
        axes.set(xlabel='Fuzzer (highest median coverage on the left)')
        axes.set_xticklabels(axes.get_xticklabels(),
                             rotation=_DEFAULT_LABEL_ROTATION,
                             horizontalalignment='right')

        sns.despine(ax=axes, trim=True)

    def write_violin_plot(self, benchmark_snapshot_df, image_path, bugs=False):
        """Writes violin plot."""
        self._write_plot_to_image(self.box_or_violin_plot,
                                  benchmark_snapshot_df,
                                  image_path,
                                  bugs=bugs,
                                  violin=True)

    def write_box_plot(self, benchmark_snapshot_df, image_path, bugs=False):
        """Writes box plot."""
        self._write_plot_to_image(self.box_or_violin_plot,
                                  benchmark_snapshot_df,
                                  image_path,
                                  bugs=bugs)

    def distribution_plot(self, benchmark_snapshot_df, axes=None, bugs=False):
        """Draws distribution plot.

        The fuzzer labels will be in the order of their median coverage.
        """
        self._common_datafame_checks(benchmark_snapshot_df, snapshot=True)

        column_of_interest = 'bugs_covered' if bugs else 'edges_covered'

        fuzzers_in_order = data_utils.benchmark_rank_by_median(
            benchmark_snapshot_df, key=column_of_interest).index
        for fuzzer in fuzzers_in_order:
            measurements_for_fuzzer = benchmark_snapshot_df[
                benchmark_snapshot_df.fuzzer == fuzzer]
            sns.distplot(measurements_for_fuzzer[column_of_interest],
                         hist=False,
                         label=fuzzer,
                         color=self._fuzzer_colors[fuzzer],
                         ax=axes)

        axes.set_title(_formatted_title(benchmark_snapshot_df))
        axes.legend(loc='upper right', frameon=False)

        axes.set(xlabel='Bug coverage' if bugs else 'Code branch coverage')
        axes.set(ylabel='Density')
        axes.set_xticklabels(axes.get_xticklabels(),
                             rotation=_DEFAULT_LABEL_ROTATION,
                             horizontalalignment='right')

    def write_distribution_plot(self, benchmark_snapshot_df, image_path):
        """Writes distribution plot."""
        self._write_plot_to_image(self.distribution_plot, benchmark_snapshot_df,
                                  image_path)

    def ranking_plot(self, benchmark_snapshot_df, axes=None, bugs=False):
        """Draws ranking plot.

        The fuzzer labels will be in the order of their median coverage.
        """
        self._common_datafame_checks(benchmark_snapshot_df, snapshot=True)

        column_of_interest = 'bugs_covered' if bugs else 'edges_covered'

        fuzzer_order = data_utils.benchmark_rank_by_median(
            benchmark_snapshot_df, key=column_of_interest).index

        axes = sns.barplot(y=column_of_interest,
                           x='fuzzer',
                           data=benchmark_snapshot_df,
                           order=fuzzer_order,
                           estimator=np.median,
                           palette=self._fuzzer_colors,
                           ax=axes)

        axes.set_title(_formatted_title(benchmark_snapshot_df))
        ylabel = 'Reached {} coverage'.format('bug' if bugs else 'branch')
        axes.set(ylabel=ylabel)
        axes.set(xlabel='Fuzzer (highest median coverage on the left)')
        axes.set_xticklabels(axes.get_xticklabels(),
                             rotation=_DEFAULT_LABEL_ROTATION,
                             horizontalalignment='right')

        sns.despine(ax=axes, trim=True)

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
        axes.set_xticklabels(axes.get_xticklabels(),
                             rotation=_DEFAULT_LABEL_ROTATION,
                             horizontalalignment='right')

    def write_better_than_plot(self, better_than_table, image_path):
        """Writes better than plot."""
        self._write_plot_to_image(self.better_than_plot, better_than_table,
                                  image_path)

    @staticmethod
    def _generic_heatmap_plot(values, axes, args, shrink_cbar=0.2):
        """Custom heatmap plot which mimics SciPy's sign_plot."""
        args.update({'linewidths': 0.5, 'linecolor': '0.5', 'square': True})
        # Annotate with values if less than 12 fuzzers.
        if values.shape[0] > 11 and args.get('annot'):
            args['annot'] = False

        axis = sns.heatmap(values, ax=axes, **args)
        axis.set_ylabel("")
        axis.set_xlabel("")
        label_args = {'rotation': 0, 'horizontalalignment': 'right'}
        axis.set_yticklabels(axis.get_yticklabels(), **label_args)
        label_args = {'rotation': 270, 'horizontalalignment': 'right'}
        axis.set_xticklabels(axis.get_xticklabels(), **label_args)

        cbar_ax = axis.collections[0].colorbar
        cbar_ax.outline.set_linewidth(1)
        cbar_ax.outline.set_edgecolor('0.5')

        pos_bbox = cbar_ax.ax.get_position()
        pos_bbox.y0 += shrink_cbar
        pos_bbox.y1 -= shrink_cbar
        cbar_ax.ax.set_position(pos_bbox)
        return axis

    def _pvalue_heatmap_plot(self, p_values, axes=None, symmetric=False):
        """Draws heatmap plot for visualizing statistical test results.

        If |symmetric| is enabled, it masks out the upper triangle of the
        p-value table (as it is redundant with the lower triangle).
        """
        cmap_colors = ['#005a32', '#238b45', '#a1d99b', '#fbd7d4']
        cmap = colors.ListedColormap(cmap_colors)

        # TODO(lszekeres): Add 1 back to this list.
        boundaries = [0, 0.001, 0.01, 0.05]
        norm = colors.BoundaryNorm(boundaries, cmap.N)

        if symmetric:
            mask = np.zeros_like(p_values)
            mask[np.triu_indices_from(p_values)] = True

        heatmap_args = {
            'cmap': cmap,
            'mask': mask if symmetric else None,
            'fmt': ".3f",
            'norm': norm
        }

        axis = self._generic_heatmap_plot(p_values, axes, heatmap_args)

        cbar_ax = axis.collections[0].colorbar
        cbar_ax.set_ticklabels(['p < 0.001', 'p < 0.01', 'p < 0.05', 'NS'])
        cbar_ax.set_ticks([0.0005, 0.005, 0.03, 0.5])
        cbar_ax.ax.tick_params(size=0)
        return axis

    def write_heatmap_plot(self, p_values, image_path, symmetric=False):
        """Writes heatmap plot."""
        self._write_plot_to_image(self._pvalue_heatmap_plot,
                                  p_values,
                                  image_path,
                                  symmetric=symmetric)

    def _a12_heatmap_plot(self, a12_values, axes=None):
        """Draws heatmap plot for visualizing effect size results.
        """

        palette_args = {
            'h_neg': 12,
            'h_pos': 128,
            's': 99,
            'l': 47,
            'sep': 20,
            'as_cmap': True
        }

        rdgn = sns.diverging_palette(**palette_args)

        heatmap_args = {
            'cmap': rdgn,
            'vmin': 0.0,
            'vmax': 1.0,
            'square': True,
            'annot': True,
            'fmt': ".2f"
        }
        return self._generic_heatmap_plot(a12_values,
                                          axes,
                                          heatmap_args,
                                          shrink_cbar=0.1)

    def write_a12_heatmap_plot(self, a12_values, image_path):
        """Writes A12 heatmap plot."""
        self._write_plot_to_image(self._a12_heatmap_plot, a12_values,
                                  image_path)

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

    def unique_coverage_ranking_plot(self,
                                     unique_branch_cov_df_combined,
                                     axes=None):
        """Draws unique_coverage_ranking plot. The fuzzer labels will be in
        the order of their coverage."""

        fuzzer_order = unique_branch_cov_df_combined.sort_values(
            by='unique_branches_covered', ascending=False).fuzzer

        axes = sns.barplot(y='unique_branches_covered',
                           x='fuzzer',
                           data=unique_branch_cov_df_combined,
                           order=fuzzer_order,
                           palette=self._fuzzer_colors,
                           ax=axes)

        for patch in axes.patches:
            axes.annotate(
                format(patch.get_height(), '.0f'),
                (patch.get_x() + patch.get_width() / 2., patch.get_height()),
                ha='center',
                va='center',
                xytext=(0, 10),
                textcoords='offset points')

        sns.barplot(y='aggregated_edges_covered',
                    x='fuzzer',
                    data=unique_branch_cov_df_combined,
                    order=fuzzer_order,
                    facecolor=(1, 1, 1, 0),
                    edgecolor='0.2',
                    ax=axes)

        axes.set(ylabel='Reached unique edge coverage')
        axes.set(xlabel='Fuzzer (highest coverage on the left)')
        axes.set_xticklabels(axes.get_xticklabels(),
                             rotation=_DEFAULT_LABEL_ROTATION,
                             horizontalalignment='right')

        sns.despine(ax=axes, trim=True)

    def write_unique_coverage_ranking_plot(self, unique_branch_cov_df_combined,
                                           image_path):
        """Writes ranking plot for unique coverage."""
        self._write_plot_to_image(self.unique_coverage_ranking_plot,
                                  unique_branch_cov_df_combined,
                                  image_path,
                                  wide=True)

    def pairwise_unique_coverage_heatmap_plot(self,
                                              pairwise_unique_coverage_table,
                                              axes=None):
        """Draws the heatmap to visualize the unique coverage between
        each pair of fuzzers."""
        heatmap_args = {
            'annot': True,
            'fmt': 'd',
            'cmap': 'Blues',
            'linewidths': 0.5
        }
        axes = sns.heatmap(pairwise_unique_coverage_table,
                           ax=axes,
                           **heatmap_args)
        axes.set(ylabel='Not covered by')
        axes.set(xlabel='Covered by')

    def write_pairwise_unique_coverage_heatmap_plot(
            self, pairwise_unique_coverage_table, image_path):
        """Writes pairwise unique coverage heatmap plot."""
        self._write_plot_to_image(self.pairwise_unique_coverage_heatmap_plot,
                                  pairwise_unique_coverage_table,
                                  image_path,
                                  wide=True)
