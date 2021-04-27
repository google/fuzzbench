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
from experiment.build import docker_images
from fuzzbench import jobs


def run_experiment(config):
    """Main experiment logic."""
    print('Initializing the job queue.')
    # Create the queue for scheduling build jobs and run jobs.
    queue = rq.Queue('build_n_run_queue')

    images_to_build = docker_images.get_images_to_build(config['fuzzers'],
                                                        config['benchmarks'])
    jobs_list = []
    # TODO(#643): topological sort before enqueuing jobs.
    for name, image in images_to_build.items():
        depends = image.get('depends_on', None)
        if depends is not None:
            assert len(depends) == 1, 'image %s has %d dependencies. Multiple '\
            'dependencies are currently not supported.' % (name, len(depends))
        jobs_list.append(
            queue.enqueue(
                jobs.build_image,
                image=image,
                job_timeout=30 * 60,
                result_ttl=-1,
                job_id=name,
                depends_on=depends[0] if 'depends_on' in image else None))

    while True:
        print('Current status of jobs:')
        print('\tqueued:\t%d' % queue.count)
        print('\tstarted:\t%d' % queue.started_job_registry.count)
        print('\tdeferred:\t%d' % queue.deferred_job_registry.count)
        print('\tfinished:\t%d' % queue.finished_job_registry.count)
        print('\tfailed:\t%d' % queue.failed_job_registry.count)
        for job in jobs_list:
            print('  %s : %s\t(%s)' % (job.func_name, job.get_status(), job.id))

        if all([job.result is not None for job in jobs_list]):  # pylint: disable=use-a-generator
            break
        time.sleep(3)
    print('All done!')


def main():
    """Set up Redis connection and start the experiment."""
    redis_connection = redis.Redis(host="queue-server")

    config_path = environment.get('EXPERIMENT_CONFIG',
                                  'fuzzbench/local-experiment-config.yaml')
    config = yaml_utils.read(config_path)
    config = config_utils.validate_and_expand(config)

    with rq.Connection(redis_connection):
        return run_experiment(config)


if __name__ == '__main__':
    main()
