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

from common import experiment_utils
from common import utils


def _warm_plot_cache(benchmark_and_attrs):
    benchmark, attrs = benchmark_and_attrs
    print('warming cache', benchmark.name, attrs)
    for attr in attrs:
        getattr(benchmark, attr)
    return None


def _warm_cache(experiment_results, coverage_report, num_processes=-1):
    arguments = []

    # for benchmark in experiment_results.benchmarks:
        # if benchmark.type == 'bug':
        #     arguments.append((benchmark, 'bug_box_plot'))
        #     arguments.append((benchmark, 'bug_coverage_growth_plot'))
        #     arguments.append((benchmark, 'bug_coverage_growth_plot_logscale'))
        #     arguments.append((benchmark, 'bug_vargha_delaney_plot'))
        #     arguments.append((benchmark, 'bug_mann_whitney_plot'))
        # else:
        #     arguments.append((benchmark, 'ranking_plot'))
        #     arguments.append((benchmark, 'coverage_growth_plot'))
        #     arguments.append((benchmark, 'coverage_growth_plot_logscale'))
        #     arguments.append((benchmark, 'vargha_delaney_plot'))
        #     arguments.append((benchmark, 'mann_whitney_plot'))
        # if coverage_report:
        #     arguments.append((benchmark, 'unique_coverage_ranking_plot'))
        #     arguments.append((benchmark, 'pairwise_unique_coverage_plot'))

    for benchmark in experiment_results.benchmarks:
        attrs = []
        if benchmark.type == 'bug':
            attrs.extend(['bug_box_plot',
                          'bug_coverage_growth_plot',
                          'bug_coverage_growth_plot_logscale',
                          'bug_vargha_delaney_plot',
                          'bug_mann_whitney_plot',])
        else:
            attrs.extend(['ranking_plot',
                          'coverage_growth_plot',
                          'coverage_growth_plot_logscale',
                          'vargha_delaney_plot',
                          'mann_whitney_plot',])
        if coverage_report:
            attrs.extend(['unique_coverage_ranking_plot',
                          'pairwise_unique_coverage_plot',])
        arguments.append([benchmark, attrs])

    if num_processes == -1:
        num_processes = None
    import multiprocessing
    pool = multiprocessing.Pool()
    print('processes', pool._processes)
    list(pool.map(_warm_plot_cache, arguments))


def render_report(experiment_results, template, in_progress, coverage_report,
                  description, pool):
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

    _warm_cache(experiment_results, coverage_report)
    templates_dir = os.path.join(utils.ROOT_DIR, 'analysis', 'report_templates')
    environment = jinja2.Environment(
        undefined=jinja2.StrictUndefined,
        loader=jinja2.FileSystemLoader(templates_dir),
    )
    template = environment.get_template(template)

    config_path = (
        experiment_utils.get_internal_experiment_config_relative_path())
    return template.render(experiment=experiment_results,
                           in_progress=in_progress,
                           coverage_report=coverage_report,
                           description=description,
                           experiment_config_relative_path=config_path)
