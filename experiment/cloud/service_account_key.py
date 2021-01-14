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
"""Script for getting a service account key for use in an experiment."""
import sys
import base64
import json

import google.api_core.exceptions
import google.auth
import googleapiclient.discovery

from common import filesystem
from common import gcloud
from common import logs
from experiment.cloud import secret_manager

SECRET_ID = 'service-account-key'


def get_iam_service():
    """Returns the IAM Google Cloud service."""
    credentials, _ = google.auth.default()
    return googleapiclient.discovery.build('iam', 'v1', credentials=credentials)


def create_key(project):
    """Creates a service account key in |project|."""
    service = get_iam_service()
    account = gcloud.get_account()
    name = f'projects/{project}/serviceAccounts/{account}'
    key = service.projects().serviceAccounts().keys().create(  # pylint: disable=no-member
        name=name, body={}).execute()
    # Load and dump json to remove formatting.
    return str.encode(
        json.dumps(json.loads(base64.b64decode(key['privateKeyData']))))


def get_or_create_key(project, file_path):
    """Gets the service account key (for |project|) from the secret manager and
    saves it to |file_path| or creates one, saves it using the secretmanager
    (for future use) and saves it to |file_path|."""
    try:
        service_account_key = secret_manager.get(SECRET_ID, project)
    except google.api_core.exceptions.NotFound:
        service_account_key = create_key(project)
        secret_manager.save(SECRET_ID, service_account_key, project)
    filesystem.write(file_path, service_account_key, 'wb')


def main():
    """Creates or gets an already created service account key and saves it to
    the provided path."""
    logs.initialize()
    try:
        keyfile = sys.argv[1]
        get_or_create_key(sys.argv[2], keyfile)
        logs.info('Saved key to %s.', keyfile)
    except Exception:  # pylint: disable=broad-except
        logs.error('Failed to get or create key.')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
