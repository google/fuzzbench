# Copyright 2021 Google LLC
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
"""Module for dealing with the Google Cloud secret manager."""
import posixpath

from google.cloud import secretmanager


def get_secret_manager_client():
    """Returns the secretmanager client."""
    return secretmanager.SecretManagerServiceClient()


def get_parent_resource(project):
    """Returns the parent resource."""
    return f'projects/{project}'


def _create_secret(client, secret_id, project):
    """Creates and returns a secret (identified by |secret_id| for |project|)
    using |client."""
    client = get_secret_manager_client()
    parent = get_parent_resource(project)
    return client.create_secret(
        request={
            'parent': parent,
            'secret_id': secret_id,
            'secret': {
                'replication': {
                    'automatic': {}
                }
            },
        })


def save(secret_id, value, project):
    """Saves |value| using |secret_id| in |project|."""
    client = get_secret_manager_client()
    secret = _create_secret(client, secret_id, project)
    client.add_secret_version(request={
        'parent': secret.name,
        'payload': {
            'data': value
        }
    })


def get(secret_id, project):
    """Returns the value of the secret identified by |secret_id| in
    |project|."""
    parent = get_parent_resource(project)
    name = posixpath.join(parent, 'secrets', secret_id, 'versions', '1')
    client = get_secret_manager_client()
    response = client.access_secret_version(request={'name': name})
    return response.payload.data
