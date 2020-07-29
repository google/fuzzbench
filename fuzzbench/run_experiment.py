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

from fuzzbench import jobs


def run_experiment():
    """Main experiment logic."""
    print('Initializing the job queue.')
    queue = rq.Queue('build_n_run_queue')
    jobs_list = []
    jobs_list.append(
        queue.enqueue(jobs.build_image,
                      'base-image',
                      job_timeout=600,
                      job_id='base-image'))
    jobs_list.append(
        queue.enqueue(jobs.build_image,
                      'base-builder',
                      job_timeout=600,
                      job_id='base-builder',
                      depends_on='base-image'))
    jobs_list.append(
        queue.enqueue(jobs.build_image,
                      'base-runner',
                      job_timeout=600,
                      job_id='base-runner',
                      depends_on='base-image'))

    while True:
        print('Current status of jobs:')
        print('\tqueued:\t%d' % queue.count)
        print('\tstarted:\t%d' % queue.started_job_registry.count)
        print('\tdeferred:\t%d' % queue.deferred_job_registry.count)
        print('\tfinished:\t%d' % queue.finished_job_registry.count)
        print('\tfailed:\t%d' % queue.failed_job_registry.count)
        for job in jobs_list:
            print('  %s : %s\t(%s)' % (job.func_name, job.get_status(), job.id))

        if all([job.result is not None for job in jobs_list]):
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
