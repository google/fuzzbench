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
"""Determines if an experiment should be run and runs one if necessary.
Note that this code uses a config file for experiments that is not generic.
Thus, it only works on the official fuzzbench service."""
import argparse
import datetime
import os
import sys

import pytz

from common import logs
from common import benchmark_utils
from common import fuzzer_utils
from common import utils

from experiment import run_experiment

EXPERIMENT_CONFIG_FILE = os.path.join(utils.ROOT_DIR, 'service',
                                      'experiment-config.yaml')


def get_experiment_name():
    """Returns the name of the experiment to run."""
    timezone = pytz.timezone('America/Los_Angeles')
    time_now = datetime.datetime.now(timezone)
    return time_now.strftime('%Y-%m-%d')


def run_diff_experiment():
    """Run a diff expeirment. This is an experiment that runs only on
    fuzzers that have changed since the last experiment."""
    # TODO(metzman): Implement this.
    raise NotImplementedError('Diff experiments not implemented yet.')


def run_full_experiment():
    """Run a full experiment."""
    experiment_name = get_experiment_name()
    fuzzer_configs = fuzzer_utils.get_fuzzer_configs()
    benchmarks = benchmark_utils.get_all_benchmarks()
    run_experiment.start_experiment(experiment_name, EXPERIMENT_CONFIG_FILE,
                                    benchmarks, fuzzer_configs)


def main():
    """Run an experiment."""
    logs.initialize()
    parser = argparse.ArgumentParser(
        description='Run a full or diff experiment (if needed).')
    parser.add_argument('experiment_type', choices=['diff', 'full'])
    args = parser.parse_args()
    if args.experiment_type == 'diff':
        run_diff_experiment()
    else:
        run_full_experiment()
    return 0


if __name__ == '__main__':
    sys.exit(main())
