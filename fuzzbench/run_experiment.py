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

from common import config_utils, environment, yaml_utils
from fuzzbench import fake_jobs


def run_experiment(config):
    """Main experiment logic."""
    print('Initializing the job queue.')
    queue = rq.Queue()
    jobs = []
    jobs.append(queue.enqueue(fake_jobs.build_image, 'base-images'))
    for benchmark in config.get('benchmarks'):
        jobs.append(queue.enqueue(fake_jobs.build_image, benchmark))
    for fuzzer in config.get('fuzzers'):
        for benchmark in config.get('benchmarks'):
            jobs.append(queue.enqueue(fake_jobs.build_image,
                                      fuzzer + benchmark))

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
    config_path = environment.get('EXPERIMENT_CONFIG', 'config.yaml')
    config = yaml_utils.read(config_path)

    config = config_utils.validate_and_expand(config)

    with rq.Connection(redis_connection):
        return run_experiment(config)


if __name__ == '__main__':
    main()
