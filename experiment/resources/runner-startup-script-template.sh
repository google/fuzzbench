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

# Configure the host.

# Make everything ptrace-able.
echo 0 > /proc/sys/kernel/yama/ptrace_scope

# Do not notify external programs about core dumps.
echo core >/proc/sys/kernel/core_pattern

# Start docker.
{% if not local_experiment %}
while ! docker pull {{docker_image_url}}
do
  echo 'Error pulling image, retrying...'
done{% endif %}

docker run \
--privileged --cpus=1 --rm \
-e INSTANCE_NAME={{instance_name}} \
-e FUZZER={{fuzzer}} \
-e BENCHMARK={{benchmark}} \
-e EXPERIMENT={{experiment}} \
-e TRIAL_ID={{trial_id}} \
-e MAX_TOTAL_TIME={{max_total_time}} \
-e DOCKER_REGISTRY={{docker_registry}} {% if not local_experiment %}-e CLOUD_PROJECT={{cloud_project}} -e CLOUD_COMPUTE_ZONE={{cloud_compute_zone}} {% endif %}\
-e EXPERIMENT_FILESTORE={{experiment_filestore}} {% if local_experiment %}-v {{experiment_filestore}}:{{experiment_filestore}} {% endif %}\
-e REPORT_FILESTORE={{report_filestore}} {% if local_experiment %}-v {{report_filestore}}:{{report_filestore}} {% endif %}\
-e FUZZ_TARGET={{fuzz_target}} \
-e LOCAL_EXPERIMENT={{local_experiment}} \
{% if not local_experiment %}--name=runner-container {% endif %}\
--cap-add SYS_NICE --cap-add SYS_PTRACE \
{{docker_image_url}} 2>&1 | tee /tmp/runner-log.txt
