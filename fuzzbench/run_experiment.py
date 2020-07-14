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
"""Runs a FuzzBench experiment."""

import time

import redis
import rq

import fake_jobs


def run_experiment():
    """Main experiment logic."""
    print('Initializing the job queue.')
    queue = rq.Queue()
    jobs = []
    for i in range(6):
        jobs.append(queue.enqueue(fake_jobs.build_image, 'something-%d' % i))

    while True:
        print('Current status of jobs:')
        for job in jobs:
            print('  %s%s : %s' % (job.func_name, job.args, job.get_status()))
        if all([job.result is not None for job in jobs]):
            break
        time.sleep(3)
    print('All done!')


def main():
    """Set up Redis connection and start the experiment."""
    redis_connection = redis.Redis(host="queue-server")
    with rq.Connection(redis_connection):
        return run_experiment()


if __name__ == '__main__':
    main()
