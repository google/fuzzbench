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

from redis import Redis
from rq import Queue
import sys
import time

from common import filesystem
from experiment.task_module import build_task, run_task, measure_task


def main():
    """Run an experiment."""

    # Initialize Redis server and task queues.
    build_n_run_queue = Queue(name='build_n_run_queue', connection=Redis())
    measure_queue = Queue(name='measure_queue', connection=Redis())

    # Initialize the filestore.
    filesystem.create_directory('/tmp/queue_test')

    # Initialize the SQL database.

    # Obtain the docker registry.

    while True:
        # Push tasks into queues.
        build_n_run_queue.enqueue(build_task, fuzzer='test_fuzzer', benchmark='test_benchmark')
        build_n_run_queue.enqueue(run_task, fuzzer='test_fuzzer', benchmark='test_benchmark')
        measure_queue.enqueue(measure_task, fuzzer='test_fuzzer', benchmark='test_benchmark')
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
