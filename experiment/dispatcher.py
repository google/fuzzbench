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
"""Script to run on the dispatcher. Builds each benchmark with each fuzzing
configuration, spawns a runner VM for each benchmark-fuzzer combo, and then
records coverage data received from the runner VMs."""

import itertools
import multiprocessing
import os
import posixpath
import sys
import threading
import time
from typing import List

from common import experiment_utils
from common import fuzzer_config_utils
from common import gcloud
from common import logs
from common import yaml_utils
from database import models
from database import utils as db_utils
from experiment import builder
from experiment import measurer
from experiment import reporter
from experiment import scheduler

LOOP_WAIT_SECONDS = 5 * 60

# TODO(metzman): Convert more uses of os.path.join to exp_path.path.


def create_work_subdirs(subdirs: List[str]):
    """Create |subdirs| in work directory."""
    for subdir in subdirs:
        os.mkdir(os.path.join(experiment_utils.get_work_dir(), subdir))


def _initialize_experiment_in_db(experiment: str, benchmarks: List[str],
                                 fuzzers: List[str], num_trials: int):
    """Initializes |experiment| in the database by creating the experiment
    entity and entities for each trial in the experiment."""
    db_utils.add_all(
        [db_utils.get_or_create(models.Experiment, name=experiment)])

    trials_args = itertools.product(sorted(benchmarks), range(num_trials),
                                    sorted(fuzzers))
    trials = [
        models.Trial(fuzzer=fuzzer, experiment=experiment, benchmark=benchmark)
        for benchmark, _, fuzzer in trials_args
    ]
    # TODO(metzman): Consider doing this without sqlalchemy. This can get
    # slow with SQLalchemy (it's much worse with add_all).
    db_utils.bulk_save(trials)


class Experiment:
    """Class representing an experiment."""

    def __init__(self, experiment_config_filepath: str):
        self.config = yaml_utils.read(experiment_config_filepath)

        benchmarks = self.config['benchmarks'].split(',')
        self.benchmarks = builder.build_all_measurers(benchmarks)

        self.fuzzers = [
            fuzzer_config_utils.get_fuzzer_name(filename) for filename in
            os.listdir(fuzzer_config_utils.get_fuzzer_configs_dir())
        ]

        _initialize_experiment_in_db(self.config['experiment'], self.benchmarks,
                                     self.fuzzers, self.config['trials'])
        self.web_bucket = posixpath.join(self.config['cloud_web_bucket'],
                                         experiment_utils.get_experiment_name())


def dispatcher_main():
    """Do the experiment and report results."""
    logs.info('Starting experiment.')

    # Set this here because we get failures if we do it in measurer for some
    # reason.
    multiprocessing.set_start_method('spawn')
    builder.gcb_build_base_images()

    experiment_config_file_path = os.path.join(fuzzer_config_utils.get_dir(),
                                               'experiment.yaml')
    experiment = Experiment(experiment_config_file_path)

    # When building, we only care about the underlying fuzzer rather than the
    # display name that we use to identify a specific configuration.
    unique_fuzzers = list({
        fuzzer_config_utils.get_underlying_fuzzer_name(f)
        for f in experiment.fuzzers
    })
    builder.build_all_fuzzer_benchmarks(unique_fuzzers, experiment.benchmarks)

    create_work_subdirs(['experiment-folders', 'measurement-folders'])

    # Start measurer and scheduler in threads.
    scheduler_loop_thread = threading.Thread(target=scheduler.schedule_loop,
                                             args=(experiment.config,))
    scheduler_loop_thread.start()
    measurer_loop_thread = threading.Thread(
        target=measurer.measure_loop,
        args=(
            experiment.config['experiment'],
            experiment.config['max_total_time'],
        ))
    measurer_loop_thread.start()

    while True:
        time.sleep(LOOP_WAIT_SECONDS)
        is_complete = (not scheduler_loop_thread.is_alive() and
                       not measurer_loop_thread.is_alive())

        # Generate periodic output reports.
        reporter.output_report(experiment.web_bucket)

        if is_complete:
            # Experiment is complete, bail out.
            break


def main():
    """Do the experiment and report results."""
    logs.initialize(default_extras={
        'component': 'dispatcher',
    })

    try:
        dispatcher_main()
    except Exception as error:
        logs.error('Error conducting experiment.')
        raise error


if __name__ == '__main__':
    sys.exit(main())
