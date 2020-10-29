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
"""Module for starting instances to run measure workers."""
import collections
import os
import posixpath
import sys
import time

from common import experiment_utils
from common import gce
from common import gcloud
from common import logs
from common import queue_utils
from common import yaml_utils

logger = logs.Logger('schedule_measure_workers')  # pylint: disable=invalid-name

# This is the default quota on GCE.
# TODO(metzman): Use the GCE API to determine this quota.
MAX_INSTANCES_PER_GROUP = 1000


def get_instance_group_name(experiment: str):
    """Returns the name of the instance group of measure workers for
    |experiment|."""
    # "worker-" needs to come first because name cannot start with number.
    return 'worker-' + experiment


def get_measure_worker_instance_template_name(experiment: str):
    """Returns an instance template name for measurer workers running in
    |experiment|."""
    return 'worker-' + experiment


def get_base_worker_instance_name(experiment):
    """GCE will create instances for this group in the format
    "w-|experiment|-$UNIQUE_ID". 'w' is short for "worker"."""
    return 'w-' + experiment


def initialize(experiment_config: dict):
    """Initialize everything that will be needed to schedule measurers."""
    logger.info('Initializing worker scheduling.')
    gce.initialize()
    experiment = experiment_config['experiment']
    project = experiment_config['project']
    instance_template_name = get_measure_worker_instance_template_name(
        experiment)
    docker_image = posixpath.join(experiment_config['docker_registry'],
                                  'measure-worker:{}'.format(experiment))

    redis_host = experiment_config['redis_host']
    experiment_filestore = experiment_config['experiment_filestore']
    local_experiment = experiment_utils.is_local_experiment()
    cloud_compute_zone = experiment_config.get('cloud_compute_zone')
    env = {
        'REDIS_HOST': redis_host,
        'EXPERIMENT_FILESTORE': experiment_filestore,
        'EXPERIMENT': experiment,
        'LOCAL_EXPERIMENT': local_experiment,
        'CLOUD_COMPUTE_ZONE': cloud_compute_zone,
    }

    zone = experiment_config['cloud_compute_zone']
    instance_template_url = gcloud.create_instance_template(
        instance_template_name, docker_image, env, project, zone)

    instance_group_name = get_instance_group_name(experiment)

    base_instance_name = get_base_worker_instance_name(experiment)

    gce.create_instance_group(instance_group_name, instance_template_url,
                              base_instance_name, project, zone)
    queue = queue_utils.initialize_queue(redis_host)
    return queue


def teardown(experiment_config: dict):
    """Teardown all resources used for running measurer workers."""
    instance_group_name = get_instance_group_name(
        experiment_config['experiment'])
    project = experiment_config['cloud_project']
    zone = experiment_config['cloud_compute_zone']
    gce.delete_instance_group(instance_group_name, project, zone)
    gcloud.delete_instance_template(experiment_config['experiment'])


def schedule(experiment_config: dict, queue):
    """Schedule measurer workers. This cannot be called before
    initialize_measurers."""
    logger.info('Scheduling measurer workers.')

    # TODO(metzman): This method doesn't seem to correctly take into account
    # jobs that are running (the API provided by rq doesn't work intuitively).
    # That is OK for now since scheduling only happens while nothing is being
    # measured but this should be fixed.
    jobs = queue_utils.get_all_jobs(queue)
    counts = collections.defaultdict(int)
    for job in jobs:
        counts[job.get_status(refresh=False)] += 1

    num_instances_needed = counts['queued'] + counts['started']
    num_instances_needed = min(num_instances_needed, MAX_INSTANCES_PER_GROUP)

    logger.info('Scheduling %d workers.', num_instances_needed)
    instance_group_name = get_instance_group_name(
        experiment_config['experiment'])
    project = experiment_config['cloud_project']
    zone = experiment_config['cloud_compute_zone']
    num_instances = gce.get_instance_group_size(instance_group_name, project,
                                                zone)

    # TODO(metzman): Use autoscaling as it probably can deal with quotas more
    # easily.
    if not num_instances_needed:
        # Can't go below 1 instance per group.
        logs.info('num_instances_needed = 0, resizing to 1.')
        num_instances_needed = 1

    if num_instances_needed != num_instances:
        # TODO(metzman): Add some limits so always have some measurers but not
        # too many.
        gce.resize_instance_group(num_instances_needed, instance_group_name,
                                  project, zone)


def main():
    """Run schedule_measure_workers as a standalone script by calling schedule
    in a loop. Useful for debugging."""
    logs.initialize(
        default_extras={
            'experiment': os.environ['EXPERIMENT'],
            'component': 'dispatcher',
            'subcomponent': 'scheduler'
        })
    gce.initialize()
    config_path = sys.argv[1]
    config = yaml_utils.read(config_path)
    queue = initialize(config)
    while True:
        schedule(config, queue)
        time.sleep(30)


if __name__ == '__main__':
    main()
