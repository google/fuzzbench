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
"""Stops a running experiment."""

import sys

from common import experiment_utils
from common import logs
from common import gce
from common import gcloud
from common import yaml_utils

logger = logs.Logger('stop_experiment')  # pylint: disable=invalid-name


def stop_experiment(experiment_name, experiment_config_filename):
    """Stop the experiment specified by |experiment_config_filename|."""
    experiment_config = yaml_utils.read(experiment_config_filename)
    if experiment_config.get('local_experiment', False):
        raise NotImplementedError(
            'Local experiment stop logic is not implemented.')

    logger.info('Stopping experiment.')
    cloud_project = experiment_config['cloud_project']
    cloud_compute_zone = experiment_config['cloud_compute_zone']

    gce.initialize()
    instances = list(gce.get_instances(cloud_project, cloud_compute_zone))

    experiment_instances = []
    dispatcher_instance = experiment_utils.get_dispatcher_instance_name(
        experiment_name)
    if dispatcher_instance not in instances:
        logger.warning('Dispatcher instance not running, skip.')
    else:
        experiment_instances.append(dispatcher_instance)

    trial_prefix = 'r-' + experiment_name
    experiment_instances.extend([
        instance for instance in instances if instance.startswith(trial_prefix)
    ])
    if not experiment_instances:
        logger.warning('No experiment instances found, no work to do.')
        return True

    logger.info('Deleting instance.')
    if not gcloud.delete_instances(experiment_instances, cloud_compute_zone):
        logger.error('Failed to stop experiment instances.')
        return False

    logger.info('Successfully stopped experiment.')
    return True


def main():
    """Stop the experiment."""
    if len(sys.argv) != 3:
        print("Usage {0} <experiment-name> <experiment-config.yaml>")
        return 1
    logs.initialize()
    return 0 if stop_experiment(sys.argv[1], sys.argv[2]) else 1


if __name__ == '__main__':
    sys.exit(main())
