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
"""Google cloud related code."""

import enum
import posixpath
import subprocess
from typing import List

from common import experiment_utils
from common import logs
from common import new_process

# Constants for dispatcher specs.
DISPATCHER_MACHINE_TYPE = 'n1-highmem-96'
DISPATCHER_BOOT_DISK_SIZE = '4TB'
DISPATCHER_BOOT_DISK_TYPE = 'pd-ssd'

# Constants for runner specs.
RUNNER_BOOT_DISK_SIZE = '30GB'

# Constants for measurer worker specs.
MEASURER_WORKER_MACHINE_TYPE = 'n1-standard-1'
MEASURER_WORKER_BOOT_DISK_SIZE = '50GB'

# Number of instances to process at once.
INSTANCE_BATCH_SIZE = 100


class InstanceType(enum.Enum):
    """Types of instances we need for the experiment."""
    DISPATCHER = 0
    RUNNER = 1


def create_instance(instance_name: str,
                    instance_type: InstanceType,
                    config: dict,
                    startup_script: str = None,
                    preemptible: bool = False,
                    **kwargs) -> bool:
    """Creates a GCE instance with name, |instance_name|, type, |instance_type|
    and with optionally provided and |startup_script|."""

    if experiment_utils.is_local_experiment():
        return run_local_instance(startup_script)

    command = [
        'gcloud',
        'compute',
        'instances',
        'create',
        instance_name,
        '--image-family=cos-stable',
        '--image-project=cos-cloud',
        '--zone=%s' % config['cloud_compute_zone'],
        '--scopes=cloud-platform',
    ]
    if instance_type == InstanceType.DISPATCHER:
        command.extend([
            '--machine-type=%s' % DISPATCHER_MACHINE_TYPE,
            '--boot-disk-size=%s' % DISPATCHER_BOOT_DISK_SIZE,
            '--boot-disk-type=%s' % DISPATCHER_BOOT_DISK_TYPE,
        ])
    else:
        machine_type = config['runner_machine_type']
        if machine_type is not None:
            command.append('--machine-type=%s' % machine_type)
        else:
            # Do this to support KLEE experiments.
            command.append([
                '--custom-memory=%s' % config['runner_memory'],
                '--custom-cpu=%s' % config['runner_num_cpu_cores']
            ])

        command.extend([
            '--no-address',
            '--boot-disk-size=%s' % RUNNER_BOOT_DISK_SIZE,
        ])

    if preemptible:
        command.append('--preemptible')
    if startup_script:
        command.extend(
            ['--metadata-from-file', 'startup-script=' + startup_script])

    result = new_process.execute(command, expect_zero=False, **kwargs)
    if result.retcode == 0:
        return True

    logs.info('Failed to create instance. Command: %s failed. Output: %s',
              command, result.output)
    return False


def delete_instances(instance_names: List[str], zone: str, **kwargs) -> bool:
    """Delete gcloud instance |instance_names|. Returns true if the operation
    succeeded or false otherwise."""
    error_occurred = False
    # Delete instances in batches, otherwise we run into rate limit errors.
    for idx in range(0, len(instance_names), INSTANCE_BATCH_SIZE):
        # -q is needed otherwise gcloud will prompt "Y/N?".
        command = ['gcloud', 'compute', 'instances', 'delete', '-q']
        command.extend(instance_names[idx:idx + INSTANCE_BATCH_SIZE])
        command.extend(['--zone', zone])
        result = new_process.execute(command, expect_zero=False, **kwargs)
        error_occurred = error_occurred or result.retcode != 0

    return not error_occurred


def set_default_project(cloud_project: str):
    """Set default project for future gcloud and gsutil commands."""
    return new_process.execute(
        ['gcloud', 'config', 'set', 'project', cloud_project])


def run_local_instance(startup_script: str = None) -> bool:
    """Does the equivalent of "create_instance" for local experiments, runs
    |startup_script| in the background."""
    command = ['/bin/bash', startup_script]
    subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return new_process.ProcessResult(0, '', False)


def create_instance_template(template_name, docker_image, env, project, zone):
    """Returns a ProcessResult from running the command to create an instance
    template."""
    # Creating an instance template cannot be done using the GCE API because
    # there is no public API for handling some docker related functionality that
    # we need.
    command = [
        'gcloud', 'compute', '--project', project, 'instance-templates',
        'create-with-container', template_name, '--no-address',
        '--image-family=cos-stable', '--image-project=cos-cloud',
        '--region=%s' % zone, '--scopes=cloud-platform',
        '--machine-type=%s' % MEASURER_WORKER_MACHINE_TYPE,
        '--boot-disk-size=%s' % MEASURER_WORKER_BOOT_DISK_SIZE, '--preemptible',
        '--container-image', docker_image
    ]
    for item in env.items():
        command.extend(['--container-env', '%s=%s' % item])
    new_process.execute(command)
    return posixpath.join('https://www.googleapis.com/compute/v1/projects/',
                          project, 'global', 'instanceTemplates', template_name)


def delete_instance_template(template_name: str):
    """Returns a ProcessResult from running the command to delete the
    measure_worker template for this |experiment|."""
    command = [
        'gcloud', 'compute', 'instance-templates', 'delete', template_name
    ]
    return new_process.execute(command)


def get_account():
    """Returns the email address of the current account being used."""
    return new_process.execute(['gcloud', 'config', 'get-value',
                                'account']).output.strip()
