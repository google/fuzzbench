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
"""Report generator tool."""

import argparse
import os
import sys

import pandas as pd

from analysis import data_utils
from analysis import experiment_results
from analysis import plotting
from analysis import queries
from analysis import rendering
from analysis import report_utils
from common import filesystem
from common import logs

logger = logs.Logger('reporter')


def get_arg_parser():
    """Returns argument parser."""
    parser = argparse.ArgumentParser(description='Report generator.')
    parser.add_argument('experiments', nargs='+', help='Experiment names')
    parser.add_argument(
        '-n',
        '--report-name',
        help='Name of the report. Default: name of the first experiment.')
    parser.add_argument(
        '-t',
        '--report-type',
        choices=['default', 'experimental'],
        default='default',
        help='Type of the report (which template to use). Default: default.')
    parser.add_argument(
        '-d',
        '--report-dir',
        default='./report',
        help='Directory for writing a report. Default: ./report')
    parser.add_argument(
        '-q',
        '--quick',
        action='store_true',
        default=False,
        help='If set, plots are created faster, but contain less details.')
    parser.add_argument(
        '--log-scale',
        action='store_true',
        default=False,
        help='If set, the time axis of the coverage growth plot is log scale.')
    parser.add_argument(
        '-b',
        '--benchmarks',
        nargs='*',
        help='Names of the benchmarks to include in the report.')
    parser.add_argument(
        '-e',
        '--end-time',
        default=None,
        type=int,
        help=('The last time (in seconds) during an experiment to include in '
              'the report.'))
    parser.add_argument('-f',
                        '--fuzzers',
                        nargs='*',
                        help='Names of the fuzzers to include in the report.')

    # It doesn't make sense to clobber and label by experiment, since nothing
    # can get clobbered like this.
    mutually_exclusive_group = parser.add_mutually_exclusive_group()
    mutually_exclusive_group.add_argument(
        '-l',
        '--label-by-experiment',
        action='store_true',
        default=False,
        help='If set, then the report will track progress made in experiments')
    mutually_exclusive_group.add_argument(
        '-m',
        '--merge-with-clobber',
        action='store_true',
        default=False,
        help=('When generating a report from multiple experiments, and trials '
              'exist for fuzzer-benchmark pairs in multiple experiments, only '
              'include trials for that pair from the last experiment. For '
              'example, if experiment "A" has all fuzzers but experiment "B" '
              'has used an updated version of afl++, this option allows you to '
              'get a report of all trials in "A" except for afl++ and all the '
              'trials from "B". "Later experiments" are those whose names come '
              'later when passed to this script.'))
    mutually_exclusive_group.add_argument(
        '-p',
        '--merge-with-clobber-nonprivate',
        action='store_true',
        default=False,
        help=('Does --merge-with-clobber but includes all experiments that are '
              'not private. See help for --merge-with-clobber for more '
              'details.'))
    parser.add_argument(
        '-c',
        '--from-cached-data',
        action='store_true',
        default=False,
        help=('If set, and the experiment data is already cached, '
              'don\'t query the database again to get the data.'))

    return parser


# pylint: disable=too-many-arguments,too-many-locals
def generate_report(experiment_names,
                    report_directory,
                    report_name=None,
                    label_by_experiment=False,
                    benchmarks=None,
                    fuzzers=None,
                    report_type='default',
                    quick=False,
                    log_scale=False,
                    from_cached_data=False,
                    in_progress=False,
                    end_time=None,
                    merge_with_clobber=False,
                    merge_with_clobber_nonprivate=False):
    """Generate report helper."""
    if merge_with_clobber_nonprivate:
        experiment_names = (
            queries.add_nonprivate_experiments_for_merge_with_clobber(
                experiment_names))

    report_name = report_name or experiment_names[0]

    filesystem.create_directory(report_directory)

    data_path = os.path.join(report_directory, 'data.csv.gz')
    if from_cached_data and os.path.exists(data_path):
        experiment_df = pd.read_csv(data_path)
    else:
        experiment_df = queries.get_experiment_data(experiment_names)
        # Save the raw data along with the report.
        experiment_df.to_csv(data_path)

    data_utils.validate_data(experiment_df)

    if benchmarks is not None:
        experiment_df = data_utils.filter_benchmarks(experiment_df, benchmarks)

    if fuzzers is not None:
        experiment_df = data_utils.filter_fuzzers(experiment_df, fuzzers)

    if label_by_experiment:
        experiment_df = data_utils.label_fuzzers_by_experiment(experiment_df)

    if end_time is not None:
        experiment_df = data_utils.filter_max_time(experiment_df, end_time)

    if merge_with_clobber:
        experiment_df = data_utils.clobber_experiments_data(
            experiment_df, experiment_names)

    # Generate coverge reports for each benchmark.
    benchmark_names = experiment_df.benchmark.unique()
    fuzzer_names = experiment_df.fuzzer.unique()
    coverage_report_directory = os.path.join(report_directory,
                                             'coverage-reports')
    if not in_progress:
        logger.info('Generating coverage reports.')
        try:
            if not from_cached_data:
                report_utils.fetch_source_files(benchmark_names,
                                                coverage_report_directory)
                report_utils.fetch_binary_files(benchmark_names,
                                                coverage_report_directory)
                report_utils.get_profdata_files(experiment_names[0],
                                                benchmark_names, fuzzer_names,
                                                coverage_report_directory)

            # Generate coverage reports for each benchmark.
            report_utils.generate_cov_reports(benchmark_names, fuzzer_names,
                                              coverage_report_directory)
        except Exception:  # pylint: disable=broad-except
            logger.error('Failed when generating coverage reports.')

    plotter = plotting.Plotter(fuzzer_names, quick, log_scale)
    experiment_ctx = experiment_results.ExperimentResults(
        experiment_df, report_directory, plotter, experiment_name=report_name)

    template = report_type + '.html'
    detailed_report = rendering.render_report(experiment_ctx, template,
                                              in_progress)

    filesystem.write(os.path.join(report_directory, 'index.html'),
                     detailed_report)


def main():
    """Generates report."""
    logs.initialize()

    parser = get_arg_parser()
    args = parser.parse_args()

    generate_report(experiment_names=args.experiments,
                    report_directory=args.report_dir,
                    report_name=args.report_name,
                    label_by_experiment=args.label_by_experiment,
                    benchmarks=args.benchmarks,
                    fuzzers=args.fuzzers,
                    report_type=args.report_type,
                    quick=args.quick,
                    log_scale=args.log_scale,
                    from_cached_data=args.from_cached_data,
                    end_time=args.end_time,
                    merge_with_clobber=args.merge_with_clobber)


if __name__ == '__main__':
    sys.exit(main())
