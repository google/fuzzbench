#!/bin/bash
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

# Hack because container-optmized-os doesn't support writing to /home/root.
# docker-credential-gcr needs to write to a dotfile in $HOME.
export HOME=/home/chronos
mkdir -p $HOME
docker-credential-gcr configure-docker -include-artifact-registry
echo 0 | sudo tee /proc/sys/kernel/yama/ptrace_scope
docker run --rm \
  -e INSTANCE_NAME={{instance_name}} -e EXPERIMENT={{experiment}} \
  -e CLOUD_PROJECT={{cloud_project}} \
  -e EXPERIMENT_FILESTORE={{experiment_filestore}} \
  -e POSTGRES_PASSWORD={{postgres_password}} \
  -e CLOUD_SQL_INSTANCE_CONNECTION_NAME={{cloud_sql_instance_connection_name}} \
  -e DOCKER_REGISTRY={{docker_registry}} \
  --cap-add=SYS_PTRACE --cap-add=SYS_NICE \
  -v /var/run/docker.sock:/var/run/docker.sock --name=dispatcher-container \
  {{docker_registry}}/dispatcher-image /work/startup-dispatcher.sh
