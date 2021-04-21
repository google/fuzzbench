#!/usr/bin/env python3
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
import sys

from common import logs
from common import yaml_utils
from experiment import run_experiment


def validate_config(config):
    """Quickly validates the config. We only do this because it is confusing
    that FuzzBench internally creates another config file that is supposed to be
    used to reproduce experiments."""
    if 'benchmarks' not in config:
        raise Exception('Must specify benchmarks, are you sure this is the'
                        'config file created by fuzzbench and not the one '
                        'you created?')

    if 'fuzzers' not in config:
        raise Exception('Must specify fuzzers, are you sure this is the'
                        'config file created by fuzzbench and not the one '
                        'you created?')


def main():
    """Reproduce a specified experiment."""
    logs.initialize()
    parser = argparse.ArgumentParser(
        description='Reproduce an experiment from a full config file.')
    parser.add_argument('-c',
                        '--experiment-config',
                        help='Path to the experiment configuration yaml file.',
                        required=True)

    parser.add_argument('-e',
                        '--experiment-name',
                        help='Experiment name.',
                        required=True)

    parser.add_argument('-d',
                        '--description',
                        help='Description of the experiment.',
                        required=False)

    args = parser.parse_args()
    config = yaml_utils.read(args.experiment_config)
    run_experiment.validate_experiment_name(args.experiment_name)
    if args.experiment_name == config['experiment']:
        raise Exception('Must use a different experiment name.')
    config['experiment'] = args.experiment_name
    config['description'] = args.description
    validate_config(config)
    run_experiment.start_experiment_from_full_config(config)
    return 0


if __name__ == '__main__':
    sys.exit(main())
