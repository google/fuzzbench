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


def get_terminated_instances(project, zone):
    """Returns a list of terminated instances in |project| and |zone|."""
    instances = thread_local.service.instances()
    request = instances.list(project=project, zone=zone)
    while request is not None:
        response = request.execute()
        for instance in response['items']:
            if instance['status'] == 'TERMINATED':
                yield instance['name']
        request = instances.list_next(previous_request=request,
                                      previous_response=response)
