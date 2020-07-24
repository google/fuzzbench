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
from rq.job import Job

from common import config_utils, environment, yaml_utils
from experiment.build import docker_images
from fuzzbench import jobs

redis_connection = redis.Redis(host="queue-server")  # pylint: disable=invalid-name


def run_experiment(config):
    """Main experiment logic."""
    print('Initializing the job queue.')
    queue = rq.Queue()

    images_to_build = docker_images.get_images_to_build(config['fuzzers'],
                                                        config['benchmarks'])
    jobs_list = []
    unqueued_build_images = []
    for name, obj in images_to_build.items():
        if name in ['base-image']:
            jobs_list.append(
                queue.enqueue(jobs.build_image,
                              tag=obj['tag'],
                              context=obj['context'],
                              job_timeout=600,
                              job_id=name))
            continue

        if len(obj['depends_on']) > 1:
            unqueued_build_images.append((name, obj))
            continue

        jobs_list.append(
            queue.enqueue(jobs.build_image,
                          tag=obj['tag'],
                          context=obj['context'],
                          dockerfile=obj.get('dockerfile', None),
                          buildargs=obj.get('build_arg', None),
                          job_timeout=600,
                          job_id=name,
                          depends_on=obj['depends_on'][0]))

    while True:
        print('Current status of jobs:')
        for job in jobs_list:
            print('  %s : %s\t(%s)' % (job.func_name, job.get_status(), job.id))

        for name, obj in unqueued_build_images:
            depended_jobs = Job.fetch_many(obj['depends_on'],
                                           connection=redis_connection)
            if all([
                    depended_job.get_status() == 'finished'
                    for depended_job in depended_jobs
            ]):
                try:
                    Job.fetch(name, connection=redis_connection)
                except:  #pylint: disable=bare-except
                    jobs_list.append(
                        queue.enqueue(jobs.build_image,
                                      tag=obj['tag'],
                                      context=obj['context'],
                                      dockerfile=obj.get('dockerfile', None),
                                      buildargs=obj.get('build_arg', None),
                                      job_timeout=600,
                                      job_id=name))

        if all([job.result is not None for job in jobs_list]):
            break
        time.sleep(3)
    print('All done!')


def main():
    """Set up Redis connection and start the experiment."""
    config_path = environment.get('EXPERIMENT_CONFIG', 'config.yaml')
    config = yaml_utils.read(config_path)

    config = config_utils.validate_and_expand(config)

    with rq.Connection(redis_connection):
        return run_experiment(config)


if __name__ == '__main__':
    main()
