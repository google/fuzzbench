#!/bin/bash

echo 0 > /proc/sys/kernel/yama/ptrace_scope
echo core >/proc/sys/kernel/core_pattern
{% if not local_experiment %}
while ! docker pull {{docker_image_url}}
do
  echo 'Error pulling image, retrying...'
done{% endif %}

docker run {% if local_experiment %}-v ~/.config/gcloud:/root/.config/gcloud {% endif %}\
--privileged --cpuset-cpus=0 --rm \
-e INSTANCE_NAME={{instance_name}} \
-e FUZZER={{fuzzer}} \
-e BENCHMARK={{benchmark}} \
-e FUZZER_VARIANT_NAME={{fuzzer_variant_name}} \
-e EXPERIMENT={{experiment}} \
-e TRIAL_ID={{trial_id}} \
-e MAX_TOTAL_TIME={{max_total_time}} \
-e CLOUD_PROJECT={{cloud_project}} \
-e CLOUD_COMPUTE_ZONE={{cloud_compute_zone}} \
-e CLOUD_EXPERIMENT_BUCKET={{cloud_experiment_bucket}} \
-e FUZZ_TARGET={{fuzz_target}} \
{{additional_env}} \
{% if not local_experiment %}--name=runner-container \{% endif %}
--cap-add SYS_NICE --cap-add SYS_PTRACE \
{{docker_image_url}} 2>&1 | tee /tmp/runner-log.txt
