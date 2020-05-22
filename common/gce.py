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

api = threading.local()  # pylint: disable=invalid-name
api.credentials = None
api.service = None


def initialize():
    """Initialize the thread-local configuration with things we need to use the
    GCE API."""
    nonlocal api  # pylint: disable=nonlocal-without-binding
    api.credentials = GoogleCredentials.get_application_default()
    api.service = discovery.build('compute', 'v1', credentials=api.credentials)


def get_operations(project, zone):
    """Generator that yields GCE operations for compute engine |project| and
    |zone| in descendending order by time."""
    zone_operations = api.service.zoneOperations()  # pylint: disable=no-member
    request = zone_operations.list(project=project,
                                   zone=zone,
                                   orderBy='creationTimestamp desc')
    while request is not None:
        response = request.execute()
        for operation in response['items']:
            yield operation

        request = zone_operations.list_next(previous_request=request,
                                            previous_response=response)


def get_preemption_operations(operations):
    """Generator that yields GCE preemption operations in |operations|."""
    # This endpoint doesn't support filtering by time (despite implications
    # otherwise). Instead it supports ordering by time. It also supports
    # filtering by operation but doesn't support it when combined with ordering.
    # So we must filter manually.
    # https://cloud.google.com/compute/docs/reference/rest/v1/zoneOperations/list?apix_params=%7B%22project%22%3A%22fuzzbench%22%2C%22zone%22%3A%22us-central1-a%22%2C%22filter%22%3A%22(operationType%20%3D%20%5C%22compute.instances.preempted%5C%22)%22%2C%22orderBy%22%3A%22creationTimestamp%20desc%22%7D
    for operation in operations:
        if operation['operationType'] == 'compute.instances.preempted':
            yield operation


def filter_by_end_time(min_end_time, operations):
    """Generator that yields GCE preemption operations in |operations|."""
    # operations must be a generator that is ordered by time.
    for operation in operations:
        end_time = operation.get('endTime')
        if not end_time:
            yield operation
            continue
        operation_end_time = dateutil.parser.isoparse(end_time)

        if operation_end_time < min_end_time:
            break
        yield operation
