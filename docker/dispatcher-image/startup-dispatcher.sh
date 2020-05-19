#!/bin/bash -ex
# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Script to run on creation of the dispatcher container.
# Configures dispatcher container and runs the dispatcher script.

# This needs to be before dispatcher.py runs so that it finishes initializing
# before dispatcher.py needs it. In practice this will always happen.
# TODO(metzman): Run this as a daemon.
cloud_sql_proxy -instances="$CLOUD_SQL_INSTANCE_CONNECTION_NAME" &

# Setup source code, virtualenv and dependencies.
gsutil -m rsync -r "${CLOUD_EXPERIMENT_BUCKET}/${EXPERIMENT}/input" "${WORK}"
mkdir ${WORK}/src
tar -xvzf ${WORK}/src.tar.gz -C ${WORK}/src
source "${WORK}/.venv/bin/activate"
pip3 install -r "${WORK}/src/requirements.txt"

# Set up credentials locally as cloud metadata service does not scale.
credentials_file=${WORK}/creds.json
iam_account=`gcloud config get-value account`
gcloud iam service-accounts keys create ${credentials_file} \
    --iam-account=${iam_account}

# Start dispatcher.
PYTHONPATH=${WORK}/src GOOGLE_APPLICATION_CREDENTIALS=${credentials_file} \
    python3 "${WORK}/src/experiment/dispatcher.py"

# Revoke created credentials.
key_id=$(cat "${credentials_file}" | jq -r ".private_key_id")
gcloud iam service-accounts keys delete ${key_id} -q \
    --iam-account=${iam_account}
