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
"""Initializes the task queue, generates and pushes jobs into it for one
experiment."""

from dacite import from_dict
import os
from redis import Redis
from rq import Queue
from rq.job import Job
import sys
import time

from common import logs
from common import filesystem
from database import utils as db_utils
from database import models
from experiment import reporter, scheduler
from experiment.build import local_build
from experiment.build import builder
from experiment.dispatcher import create_work_subdirs
from experiment.run_experiment import get_git_hash
from queue_experiment import queue_watcher, filestore_watcher
from queue_experiment.config import Config


def main():
    """Run an experiment."""
    # TODO: an initial prototype for pure-local running.
    #       only for demonstrate and discuss basic architecture design.

    logs.initialize()

    # Read and validate the user configurations.
    # TODO: add read logic later.
    """
    config_data = {
        'local_experiment': True,
        'docker_registry': 'gcr.io/fuzzbench',
        'experiment_filestore': 'qd',
        'report_filestore': 'qr',
        'benchmarks': ['zlib_zlib_uncompress_fuzzer', 'jsoncpp_jsoncpp_fuzzer'],
        'fuzzers': ['afl', 'libfuzzer'],
        'trials': 2,
        'max_total_time': 3600
    }
    """
    config_data = {
        'local_experiment': True,
        'docker_registry': 'gcr.io/fuzzbench',
        'experiment_filestore': 'qdata',
        'report_filestore': 'qreport',
        'benchmarks': ['jsoncpp_jsoncpp_fuzzer'],
        'fuzzers': ['libfuzzer'],
        'trials': 2,
        'max_total_time': 3600,
        'experiment': 'singletest'
    }
    config_obj = from_dict(data_class=Config, data=config_data)
    if not config_obj.validate_all():
        logs.error('Please validate your configuration accordingly.')
        return

    experiment_name = config_data['experiment']
    num_trials = config_data['trials']
    local_experiment = config_data['local_experiment']


    # Initialize Redis server and task queues.
    # TODO: use user specified server settings later.
    build_n_run_queue = Queue(name='build_n_run_queue', connection=Redis())
    measure_queue = Queue(name='measure_queue', connection=Redis())

    # Initialize the filestore.
    filesystem.create_directory(os.path.abspath(config_data['experiment_filestore']))
    filesystem.create_directory(os.path.abspath(config_data['report_filestore']))

    # Connect to the SQL database.
    db_utils.initialize()
    models.Base.metadata.create_all(db_utils.engine)


    # Push build and run tasks into queues.

    # 1.1 base images build tasks
    # build_n_run_queue.enqueue(new_process.execute, ['make', '-j', 'base-runner', 'base-builder'], cwd=utils.ROOT_DIR)

    # job_id = build_n_run_queue.enqueue(local_build.build_base_images)
    jobs = []
    jobs.append(build_n_run_queue.enqueue(builder.build_base_images))
    jobs.append(build_n_run_queue.enqueue(builder.build_all_measurers,
                                          benchmarks=config_data['benchmarks'],
                                          job_timeout=600))
    jobs.append(build_n_run_queue.enqueue(
        builder.build_all_fuzzer_benchmarks,
        fuzzers=config_data['fuzzers'],
        benchmarks=config_data['benchmarks'],
        job_timeout=600))

    while(1):
        num = 0
        for job in jobs:
            if job.result is None:
                continue
            num = num + 1

        if num == 3:
            for job in jobs:
                print(job.result)
            break
        time.sleep(5)

    # Save trails data into database.
    trials = []
    for fuzzer, benchmark in jobs[2].result:
        fuzzer_benchmark_trials = [
            models.Trial(fuzzer=fuzzer,
                         experiment=experiment_name,
                         benchmark=benchmark,
                         preemptible=False) for _ in range(num_trials)
        ]
        trials.extend(fuzzer_benchmark_trials)
    db_utils.add_all([
        db_utils.get_or_create(
            models.Experiment,
            name=experiment_name,
            git_hash=get_git_hash())])
    db_utils.bulk_save(trials)
    create_work_subdirs(['experiment-folders', 'measurement-folders'])


    # Start watchers and generate reports.
    queue_watcher_instance = queue_watcher.QueueWatcher(
        config_obj,
        build_n_run_queue,
        measure_queue
    )
    filestore_watcher_instance = filestore_watcher.FilestoreWatcher(
        config_obj,
        measure_queue
    )

    # Schedule all trails run tasks into build_n_run_queue.
    pending_trials = scheduler.get_pending_trials(experiment_name)
    start_trial_args = [
        (scheduler.TrialProxy(trial), config_data) for trial in pending_trials
    ]
    for (trial, experiment_config) in start_trial_args:
        instance_name = experiment_utils.get_trial_instance_name(
            experiment_config['experiment'], trial.id)
        startup_script = scheduler.render_startup_script_template(
            instance_name,
            trial.fuzzer,
            trial.benchmark,
            trial.id,
            experiment_config)
        startup_script_path = '/tmp/%s-start-docker-%d.sh' % (instance_name, int(time.time()))
        with open(startup_script_path, 'w') as file_handle:
            file_handle.write(startup_script)
        job_id = Job.create(gcloud.run_local_instance,
                            startup_script=startup_script_path,
                            depends_on=job[2], # TODO: change to the build task prepared for this trial only.
                            id=str(trial.id),
                            timeout=config_data['max_total_time']
                            )
        queue_watcher.add_task(job_id)
        build_n_run_queue.enqueue_job(job_id)

    is_complete = False
    while(1):
        # Check the queue status and update the database.
        queue_watcher_instance.check()

        # Check the filestore and assign measurement tasks.
        filestore_watcher.check()

        if queue_watcher.finished() and filestore_watcher.no_measure_tasks():
            is_complete = True

        # Generate report.
        reporter.output_report(config_data['report_filestore'],
                               in_progress=not is_complete)
        if is_complete:
            break
        time.sleep(10)

    return 0


if __name__ == '__main__':
    sys.exit(main())

    """
    # Demo run.
    #
    # Terminal A: Prepare.
    $ sudo apt install python3-pip redis-server
    $ pip3 install rq
    $ cd fuzzbench
    $ PYTHONPATH=. python3 experiment/queue_init.py

    # Terminal B: Watch the files showing up under /tmp/queue_test folder.
    $ watch ls /tmp/queue_test
    Every 2.0s: ls queue_test                       hostname: Wed Jul  1 03:47:56 2020

    # Terminal C: Monitor the queue.
    $ watch rq info
    Every 2.0s: rq info                             hostname: Wed Jul  1 03:48:46 2020

    measure_queue | 1
    build_n_run_queue | 2
    2 queues, 3 jobs total

    0 workers, 2 queues

    Updated: 2020-07-01 03:48:46.915734

    # Terminal D: Start a worker.
    $ rq worker build_n_run_queue measure_queue
    03:46:37 Worker rq:worker:a6e0de1f41234f5eabc1cd4315a28b0c: started, version 1.4.3
    03:46:37 *** Listening on build_n_run_queue, measure_queue...

    # Terminal C:
    Every 2.0s: rq info                             hostname: Wed Jul  1 03:48:46 2020

    measure_queue | 0
    build_n_run_queue | 0
    2 queues, 0 jobs total

    a6e0de1f41234f5eabc1cd4315a28b0c (hostname 1486732): idle build_n_run_queue, measure_queue
    1 workers, 2 queues

    Updated: 2020-07-01 03:48:49.915734

    # Terminal B:
    Every 2.0s: ls queue_test                       hostname: Wed Jul  1 03:47:56 2020
    build_1593575197.2148492_test_fuzzer_test_benchmark
    measure_1593575197.7839473_test_fuzzer_test_benchmark
    run_1593575197.5345345_test_fuzzer_test_benchmark
    """
