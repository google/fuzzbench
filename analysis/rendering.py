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
"""Report rendering functions."""

import os

import jinja2

from common import utils


def _warm_benchmark_plot_cache(benchmark_and_attrs):
    """Warm up cache for benchmark plots by making plots. |benchmark_and_attrs|
    is a tuple containing the benchmark and a list of attributes that when
    accessed on the benchmark, cause plots to be created."""
    benchmark, attrs = benchmark_and_attrs
    for attr in attrs:
        getattr(benchmark, attr)


def _warm_cache(experiment_results, coverage_report, pool):
    """"Warm plot caches by plotting plots for each benchmark in parallel before
    it is done sequentially in jinja."""
    # Plotting each benchmark's plots in parallel seems to be faster than
    # plotting each plot in parallel. I suspect this is because each call to
    # _warm_benchmark_plot_cache requires copying a benchmark, which has some
    # overhead.
    arguments = []
    for benchmark in experiment_results.benchmarks:
        attrs = []
        if benchmark.type == 'bug':
            attrs.extend([
                'bug_box_plot',
                'bug_coverage_growth_plot',
                'bug_coverage_growth_plot_logscale',
                'bug_vargha_delaney_plot',
                'bug_mann_whitney_plot',
            ])
        else:
            attrs.extend([
                'ranking_plot',
                'coverage_growth_plot',
                'coverage_growth_plot_logscale',
                'vargha_delaney_plot',
                'mann_whitney_plot',
            ])
        if coverage_report:
            attrs.extend([
                'unique_coverage_ranking_plot',
                'pairwise_unique_coverage_plot',
            ])
        arguments.append([benchmark, attrs])

    list(pool.map(_warm_benchmark_plot_cache, arguments))


def render_report(  # pylint:disable=too-many-arguments
        experiment_results, template, in_progress, coverage_report, description,
        pool):
    """Renders report with |template| using data provided by the
    |experiment_results| context.

    Arguments:
      template: filename of the report template. E.g., 'default.html'.
      experiment_results: an ExperimentResults object.
      in_progress: Whether the experiment is still in progress.
      coverage_report: Whether to report detailed info about coverage.
      description: A description of the experiment.

    Returns the rendered template.
    """

    _warm_cache(experiment_results, coverage_report, pool)
    templates_dir = os.path.join(utils.ROOT_DIR, 'analysis', 'report_templates')
    environment = jinja2.Environment(
        undefined=jinja2.StrictUndefined,
        loader=jinja2.FileSystemLoader(templates_dir),
    )
    template = environment.get_template(template)

    return template.render(experiment=experiment_results,
                           in_progress=in_progress,
                           coverage_report=coverage_report,
                           description=description)
