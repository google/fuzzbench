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
import posixpath

from common import gcloud
from common import gce
from common import logs
from common import queue_utils

logger = logs.Logger('scheduler')  # pylint: disable=invalid-name


def get_instance_group_name(experiment: str):
    """Returns the name of the instance group of measure workers for
    |experiment|."""
    return experiment + '-measure-worker'


def get_measure_worker_instance_template_name(experiment: str):
    """Returns an instance template name for measurer workers running in
    |experiment|."""
    return experiment + '-measure-worker'


def initialize(experiment_config: dict):
    """Initialize everything that will be needed to schedule measurers."""
    experiment = experiment_config['experiment']
    instance_template_name = get_measure_worker_instance_template_name(
        experiment)
    project = experiment_config['cloud_project']
    docker_image = posixpath.join('gcr.io', project, 'measure-worker')
    redis_host = experiment_config['redis_host']
    env = {'REDIS_HOST': redis_host}
    zone = experiment_config['cloud_compute_zone']
    instance_template_url = gcloud.create_instance_template(
        instance_template_name, docker_image, env, project, zone)
    instance_group_name = get_instance_group_name(experiment)
    gce.create_instance_group(instance_group_name, instance_template_url,
                              experiment, project, zone)
    queue = queue_utils.initialize_queue(redis_host)
    return queue


def teardown(experiment_config: dict):
    """Teardown all resources used for running measurer workers."""
    instance_group_name = get_instance_group_name(
        experiment_config['experiment'])
    project = experiment_config['cloud_project']
    zone = experiment_config['cloud_compute_zone']
    gce.delete_instance_group(instance_group_name, project, zone)
    gcloud.delete_measure_worker_template(experiment_config['experiment'])


def schedule(experiment_config: dict, queue):
    """Schedule measurer workers. This cannot be called before
    initialize_measurers."""
    jobs = queue.get_jobs()
    counts = collections.defaultdict(int)
    for job in jobs:
        counts[job.get_status()] += 1

    num_instances_needed = counts['queued'] + counts['started']
    instance_group_name = get_instance_group_name(
        experiment_config['experiment'])
    project = experiment_config['cloud_project']
    zone = experiment_config['cloud_compute_zone']
    num_instances = gce.get_instance_group_size(instance_group_name, project,
                                                zone)

    if num_instances_needed < num_instances and num_instances == 1:
        # Can't go below 1 instance per group.
        return

    if num_instances_needed != num_instances:
        # !!! TODO(metzman): Add limits.
        gce.resize_instance_group(num_instances_needed, instance_group_name,
                                  project, zone)
