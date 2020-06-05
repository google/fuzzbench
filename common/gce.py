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
"""Module for using the Google Compute Engine (GCE) API."""
import threading

import dateutil.parser

from googleapiclient import discovery
from oauth2client.client import GoogleCredentials

thread_local = threading.local()  # pylint: disable=invalid-name


def initialize():
    """Initialize the thread-local configuration with things we need to use the
    GCE API."""
    credentials = GoogleCredentials.get_application_default()
    thread_local.service = discovery.build('compute',
                                           'v1',
                                           credentials=credentials)


def get_operations(project, zone):
    """Generator that yields GCE operations for compute engine |project| and
    |zone| in descendending order by time."""
    zone_operations = thread_local.service.zoneOperations()  # pylint: disable=no-member
    request = zone_operations.list(project=project,
                                   zone=zone,
                                   orderBy='creationTimestamp desc')
    while request is not None:
        response = request.execute()
        for operation in response['items']:
            yield operation

        request = zone_operations.list_next(previous_request=request,
                                            previous_response=response)


def get_preempted_operations(operations):
    """Generator that yields GCE preempted operations in |operations|."""
    # This endpoint doesn't support filtering by time (despite implications
    # otherwise). Instead it supports ordering by time. It also supports
    # filtering by operation but doesn't support it when combined with ordering.
    # So we must filter manually.
    # See the link below for an example of this query in action.
    # https://cloud.google.com/compute/docs/reference/rest/v1/zoneOperations/list?apix_params=%7B%22project%22%3A%22fuzzbench%22%2C%22zone%22%3A%22us-central1-a%22%2C%22filter%22%3A%22(operationType%20%3D%20%5C%22compute.instances.preempted%5C%22)%22%2C%22orderBy%22%3A%22creationTimestamp%20desc%22%7D
    for operation in operations:
        if operation['operationType'] == 'compute.instances.preempted':
            yield operation


def filter_by_end_time(min_end_time, operations):
    """Generator that yields GCE operations in |operations| that finished before
    |min_end_time|. |operations| must be an iterable that is ordered by time."""
    for operation in operations:
        end_time = operation.get('endTime')
        if not end_time:
            # Try to handle cases where the operation hasn't finished.
            yield operation
            continue

        operation_end_time = dateutil.parser.isoparse(end_time)
        if operation_end_time < min_end_time:
            break
        yield operation


def get_base_target_link(experiment_config):
    """Returns the base of the target link for this experiment so that
    get_instance_from_preempted_operation can return the instance."""
    return ('https://www.googleapis.com/compute/v1/projects/{project}/zones/'
            '{zone}/instances/').format(
                project=experiment_config['cloud_project'],
                zone=experiment_config['cloud_compute_zone'])


def get_instance_from_preempted_operation(operation, base_target_link) -> str:
    """Returns the instance name from a preempted |operation|."""
    return operation['targetLink'][len(base_target_link):]


def get_instance_group_managers():
    """Returns the instance group managers resource."""
    return thread_local.service.instanceGroupManagers()


def get_instance_group_size(instance_group: str, project: str,
                            zone: str) -> int:
    """Returns the number of instances running in |instance_group|."""
    managers = get_instance_group_managers()
    request = managers.get(instanceGroupManager=instance_group,
                           project=project,
                           zone=zone)
    return request.execute()['targetSize']


def resize_instance_group(size, instance_group, project, zone):
    """Changes the number of instances running in |instance_group| to |size|."""
    assert size >= 1
    managers = get_instance_group_managers()
    request = managers.resize(instanceGroupManager=instance_group,
                              size=size,
                              project=project,
                              zone=zone)
    return request.execute()


def delete_instance_group(instance_group, project, zone):
    """Deletes |instance_group|."""
    managers = get_instance_group_managers()
    request = managers.delete(instanceGroupManager=instance_group,
                              zone=zone,
                              project=project)
    return request.execute()


def create_instance_group(name: str, instance_template_url: str,
                          experiment: str, project: str, zone: str):
    """Creates an instance group named |name| from the template specified by
    |instance_template_url|."""
    managers = get_instance_group_managers()
    target_size = 1
    base_instance_name = 'w-' + experiment

    body = {
        'baseInstanceName': base_instance_name,
        'targetSize': target_size,
        'name': name,
        'instanceTemplate': instance_template_url
    }
    request = managers.insert(body=body, project=project, zone=zone)
    return request.execute()
