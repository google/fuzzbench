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
"""Determines if an experiment should be run and runs one if necessary."""
import argparse
import datetime
import sys

import pytz

from common import logs
from common import utils
from experiment import run_experiment

experiment_config_file = os.path.join(utils.ROOT_DIR, 'service', 'experiment-config.yaml')

def get_experiment_name():
    """Returns the name of the experiment to run."""
    tz = pytz.timezone('America/Los_Angeles')
    time_now = datetime.datetime.now(tz)
    return time_now.strftime('%Y-%M-%d')


def run_diff_experiment():
    # TODO(metzman): Finish this.
    pass


def run_full_experiment():
    experiment_name = get_experiment_name()
    fuzzers = utils.get_all_fuzzers()
    benchmarks = utils.get_all_benchmarks()
    run_experiment.start_experiment(
        experiment_name, experiment_config_file, benchmarks, fuzzers, [])


def main():
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
