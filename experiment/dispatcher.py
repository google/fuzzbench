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

import datetime
import multiprocessing
import os
import sys
import threading
import time
from typing import List

from common import experiment_path as exp_path
from common import experiment_utils
from common import logs
from common import yaml_utils
from database import models
from database import utils as db_utils
from experiment.build import builder
from experiment.measurer import measure_manager
from experiment import reporter
from experiment import scheduler
from experiment import stop_experiment

LOOP_WAIT_SECONDS = 5 * 60

# TODO(metzman): Convert more uses of os.path.join to exp_path.path.


def _get_config_file_path():
    """Return config file path."""
    return exp_path.path(
        experiment_utils.get_internal_experiment_config_relative_path())


def create_work_subdirs(subdirs: List[str]):
    """Create |subdirs| in work directory."""
    for subdir in subdirs:
        os.mkdir(os.path.join(experiment_utils.get_work_dir(), subdir))


def _initialize_experiment_in_db(experiment_config: dict):
    """Initializes |experiment| in the database by creating the experiment
    entity."""
    with db_utils.session_scope() as session:
        experiment_exists = session.query(models.Experiment).filter(
            models.Experiment.name == experiment_config['experiment']).first()
    if experiment_exists:
        raise Exception('Experiment already exists in database.')

    db_utils.add_all([
        db_utils.get_or_create(
            models.Experiment,
            name=experiment_config['experiment'],
            git_hash=experiment_config['git_hash'],
            private=experiment_config.get('private', True),
            experiment_filestore=experiment_config['experiment_filestore'],
            description=experiment_config['description']),
    ])


def _record_experiment_time_ended(experiment_name: str):
    """Record |experiment| end time in the database."""
    with db_utils.session_scope() as session:
        experiment = session.query(models.Experiment).filter(
            models.Experiment.name == experiment_name).one()
    experiment.time_ended = datetime.datetime.utcnow()
    db_utils.add_all([experiment])


def _initialize_trials_in_db(trials: List[models.Trial]):
    """Initializes entities for each trial in the experiment."""
    # TODO(metzman): Consider doing this without sqlalchemy. This can get
    # slow with SQLalchemy (it's much worse with add_all).
    db_utils.bulk_save(trials)


class Experiment:  # pylint: disable=too-many-instance-attributes
    """Class representing an experiment."""

    def __init__(self, experiment_config_filepath: str):
        self.config = yaml_utils.read(experiment_config_filepath)

        self.benchmarks = self.config['benchmarks']
        self.fuzzers = self.config['fuzzers']
        self.num_trials = self.config['trials']
        self.experiment_name = self.config['experiment']
        self.git_hash = self.config['git_hash']
        self.preemptible = self.config.get('preemptible_runners')


def build_images_for_trials(fuzzers: List[str],
                            benchmarks: List[str],
                            num_trials: int,
                            preemptible: bool,
                            concurrent_builds=None) -> List[models.Trial]:
    """Builds the images needed to run |experiment| and returns a list of trials
    that can be run for experiment. This is the number of trials specified in
    experiment times each pair of fuzzer+benchmark that builds successfully."""
    # This call will raise an exception if the images can't be built which will
    # halt the experiment.
    builder.build_base_images()

    # Only build fuzzers for benchmarks whose measurers built successfully.
    if concurrent_builds is None:
        benchmarks = builder.build_all_measurers(benchmarks)
        build_successes = builder.build_all_fuzzer_benchmarks(
            fuzzers, benchmarks)
    else:
        benchmarks = builder.build_all_measurers(benchmarks, concurrent_builds)
        build_successes = builder.build_all_fuzzer_benchmarks(
            fuzzers, benchmarks, concurrent_builds)
    experiment_name = experiment_utils.get_experiment_name()
    trials = []
    for fuzzer, benchmark in build_successes:
        fuzzer_benchmark_trials = [
            models.Trial(fuzzer=fuzzer,
                         experiment=experiment_name,
                         benchmark=benchmark,
                         preemptible=preemptible) for _ in range(num_trials)
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
    if experiment_utils.is_local_experiment():
        models.Base.metadata.create_all(db_utils.engine)

    experiment_config_file_path = _get_config_file_path()
    experiment = Experiment(experiment_config_file_path)

    _initialize_experiment_in_db(experiment.config)

    trials = build_images_for_trials(experiment.fuzzers, experiment.benchmarks,
                                     experiment.num_trials,
                                     experiment.preemptible,
                                     experiment.config['concurrent_builds'])
    _initialize_trials_in_db(trials)

    create_work_subdirs(['experiment-folders', 'measurement-folders'])

    # Start measurer and scheduler in seperate threads/processes.
    scheduler_loop_thread = threading.Thread(target=scheduler.schedule_loop,
                                             args=(experiment.config,))
    scheduler_loop_thread.start()

    measurer_main_process = multiprocessing.Process(
        target=measure_manager.measure_main, args=(experiment.config,))

    measurer_main_process.start()

    is_complete = False
    while True:
        time.sleep(LOOP_WAIT_SECONDS)
        if not scheduler_loop_thread.is_alive():
            is_complete = not measurer_main_process.is_alive()

        # Generate periodic output reports.
        reporter.output_report(experiment.config,
                               in_progress=not is_complete,
                               coverage_report=is_complete)

        if is_complete:
            # Experiment is complete, bail out.
            break

    scheduler_loop_thread.join()
    measurer_main_process.join()

    _record_experiment_time_ended(experiment.experiment_name)
    logs.info('Experiment ended.')


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

    if experiment_utils.is_local_experiment():
        return 0

    experiment_config_file_path = _get_config_file_path()

    if stop_experiment.stop_experiment(experiment_utils.get_experiment_name(),
                                       experiment_config_file_path):
        return 0

    return 1


if __name__ == '__main__':
    sys.exit(main())
