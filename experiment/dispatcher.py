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

import multiprocessing
import os
import posixpath
import sys
import threading
import time
from typing import List

from common import experiment_utils
from common import fuzzer_config_utils
from common import logs
from common import yaml_utils
from database import models
from database import utils as db_utils
from experiment.build import builder
from experiment import measurer
from experiment import reporter
from experiment import scheduler

LOOP_WAIT_SECONDS = 5 * 60

# TODO(metzman): Convert more uses of os.path.join to exp_path.path.


def create_work_subdirs(subdirs: List[str]):
    """Create |subdirs| in work directory."""
    for subdir in subdirs:
        os.mkdir(os.path.join(experiment_utils.get_work_dir(), subdir))


def _initialize_experiment_in_db(experiment: str, git_hash: str,
                                 trials: List[models.Trial]):
    """Initializes |experiment| in the database by creating the experiment
    entity and entities for each trial in the experiment."""
    db_utils.add_all([
        db_utils.get_or_create(models.Experiment,
                               name=experiment,
                               git_hash=git_hash)
    ])

    # TODO(metzman): Consider doing this without sqlalchemy. This can get
    # slow with SQLalchemy (it's much worse with add_all).
    db_utils.bulk_save(trials)


class Experiment:
    """Class representing an experiment."""

    def __init__(self, experiment_config_filepath: str):
        self.config = yaml_utils.read(experiment_config_filepath)

        self.benchmarks = self.config['benchmarks'].split(',')

        self.fuzzers = [
            fuzzer_config_utils.get_fuzzer_name(filename) for filename in
            os.listdir(fuzzer_config_utils.get_fuzzer_configs_dir())
        ]
        self.num_trials = self.config['trials']
        self.experiment_name = self.config['experiment']
        self.git_hash = self.config['git_hash']

        self.web_bucket = posixpath.join(self.config['cloud_web_bucket'],
                                         experiment_utils.get_experiment_name())


def build_images_for_trials(fuzzers: List[str], benchmarks: List[str],
                            num_trials: int) -> List[models.Trial]:
    """Builds the images needed to run |experiment| and returns a list of trials
    that can be run for experiment. This is the number of trials specified in
    experiment times each pair of fuzzer+benchmark that builds successfully."""
    # This call will raise an exception if the images can't be built which will
    # halt the experiment.
    builder.build_base_images()

    # Only build fuzzers for benchmarks whose measurers built successfully.
    benchmarks = builder.build_all_measurers(benchmarks)
    build_successes = builder.build_all_fuzzer_benchmarks(fuzzers, benchmarks)
    experiment_name = experiment_utils.get_experiment_name()
    trials = []
    for fuzzer, benchmark in build_successes:
        fuzzer_benchmark_trials = [
            models.Trial(fuzzer=fuzzer,
                         experiment=experiment_name,
                         benchmark=benchmark) for _ in range(num_trials)
        ]
        trials.extend(fuzzer_benchmark_trials)
    return trials


def dispatcher_main():
    """Do the experiment and report results."""
    logs.info('Starting experiment.')

    # Set this here because we get failures if we do it in measurer for some
    # reason.
    multiprocessing.set_start_method('spawn')
    db_utils.initialize()
    if os.getenv('LOCAL_EXPERIMENT'):
        models.Base.metadata.create_all(db_utils.engine)

    experiment_config_file_path = os.path.join(fuzzer_config_utils.get_dir(),
                                               'experiment.yaml')
    experiment = Experiment(experiment_config_file_path)
    trials = build_images_for_trials(experiment.fuzzers, experiment.benchmarks,
                                     experiment.num_trials)
    _initialize_experiment_in_db(experiment.experiment_name,
                                 experiment.git_hash, trials)

    create_work_subdirs(['experiment-folders', 'measurement-folders'])

    # Start measurer and scheduler in threads.
    scheduler_loop_thread = threading.Thread(target=scheduler.schedule_loop,
                                             args=(experiment.config,))
    scheduler_loop_thread.start()
    measurer_loop_thread = multiprocessing.Process(
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
        reporter.output_report(experiment.web_bucket,
                               in_progress=not is_complete)

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
