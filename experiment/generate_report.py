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

from analysis import experiment_results
from analysis import plotting
from analysis import queries
from analysis import rendering
from common import filesystem
from common import logs


def get_arg_parser():
    """Returns argument parser."""
    parser = argparse.ArgumentParser(description='Report generator.')
    parser.add_argument('experiment', nargs='+', help='Experiment name')
    parser.add_argument(
        '-n',
        '--report_name',
        help='Name of the report. Default: name of the first experiment.')
    parser.add_argument(
        '-t',
        '--report_type',
        choices=['default'],
        default='default',
        help='Type of the report (which template to use). Default: default.')
    parser.add_argument(
        '-d',
        '--report_dir',
        default='./report',
        help='Directory for writing a report. Default: ./report')
    parser.add_argument(
        '-q',
        '--quick',
        action='store_true',
        default=False,
        help='If set, plots are created faster, but contain less details.')
    parser.add_argument(
        '-c',
        '--from_cached_data',
        action='store_true',
        default=False,
        help=('If set, and the experiment data is already cached, '
              'don\'t query the database again to get the data.'))

    return parser


# pylint: disable=too-many-arguments
def generate_report(experiment_names,
                    report_directory,
                    report_name=None,
                    report_type='default',
                    quick=False,
                    from_cached_data=False):
    """Generate report helper."""
    report_name = report_name or experiment_names[0]

    filesystem.create_directory(report_directory)

    data_path = os.path.join(report_directory, 'data.csv.zip')
    if from_cached_data and os.path.exists(data_path):
        experiment_df = pd.read_csv(data_path)
    else:
        experiment_df = queries.get_experiment_data(experiment_names)
        # Save the raw data along with the report.
        experiment_df.to_csv(data_path)

    fuzzer_names = experiment_df.fuzzer.unique()
    plotter = plotting.Plotter(fuzzer_names, quick)
    experiment_ctx = experiment_results.ExperimentResults(
        experiment_df, report_directory, plotter, experiment_name=report_name)

    template = report_type + '.html'
    detailed_report = rendering.render_report(experiment_ctx, template)

    filesystem.write(os.path.join(report_directory, 'index.html'),
                     detailed_report)


def main():
    """Generates report."""
    logs.initialize()

    parser = get_arg_parser()
    args = parser.parse_args()

    generate_report(args.experiment, args.report_dir, args.report_name,
                    args.report_type, args.quick, args.from_cached_data)


if __name__ == '__main__':
    sys.exit(main())
