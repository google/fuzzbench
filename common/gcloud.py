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
import time
from typing import List

from common import logs
from common import new_process

# Constants for dispatcher specs.
DISPATCHER_MACHINE_TYPE = 'n1-standard-96'
DISPATCHER_BOOT_DISK_SIZE = '4TB'

# Constants for runner specs.
RUNNER_MACHINE_TYPE = 'n1-standard-1'
RUNNER_BOOT_DISK_SIZE = '30GB'

# Number of instances to process at once.
INSTANCE_BATCH_SIZE = 100


def ssh(instance: str, *args, **kwargs):
    """SSH into |instance|."""
    zone = kwargs.pop('zone', None)
    command = kwargs.pop('command', None)
    ssh_command = ['gcloud', 'beta', 'compute', 'ssh', instance]
    if command:
        ssh_command.append('--command=%s' % command)
    if zone:
        ssh_command.append('--zone=%s' % zone)
    return new_process.execute(ssh_command, *args, **kwargs)


def robust_begin_gcloud_ssh(instance_name: str, zone: str):
    """Try to SSH into an instance, |instance_name| in |zone| that might not be
    ready."""
    for _ in range(10):
        result = ssh(instance_name,
                     zone=zone,
                     command='echo ping',
                     expect_zero=False)
        if result.retcode == 0:
            return
        logs.info('GCP instance isn\'t ready yet. Rerunning SSH momentarily.')
        time.sleep(5)
    raise Exception('Couldn\'t SSH to instance.')


class InstanceType(enum.Enum):
    """Types of instances we need for the experiment."""
    DISPATCHER = 0
    RUNNER = 1


def create_instance(instance_name: str,
                    instance_type: InstanceType,
                    config: dict,
                    metadata: dict = None,
                    startup_script: str = None,
                    **kwargs) -> bool:
    """Creates a GCE instance with name, |instance_name|, type, |instance_type|
    and with optionally provided |metadata| and |startup_script|."""
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
        ])
    else:
        command.extend([
            '--no-address',
            '--machine-type=%s' % RUNNER_MACHINE_TYPE,
            '--boot-disk-size=%s' % RUNNER_BOOT_DISK_SIZE,
        ])
    if metadata:
        metadata_str = ','.join('{key}={value}'.format(key=key, value=value)
                                for key, value in metadata.items())
        command.extend(['--metadata', metadata_str])
    if startup_script:
        command.extend(
            ['--metadata-from-file', 'startup-script=' + startup_script])

    return new_process.execute(command, expect_zero=False, **kwargs)[0] == 0


def delete_instances(instance_names: List[str], zone: str, **kwargs) -> bool:
    """Delete gcloud instance |instance_names|."""
    error_occurred = False
    # Delete instances in batches, otherwise we run into rate limit errors.
    for idx in range(0, len(instance_names), INSTANCE_BATCH_SIZE):
        # -q is needed otherwise gcloud will prompt "Y/N?".
        command = ['gcloud', 'compute', 'instances', 'delete', '-q']
        command.extend(instance_names[idx:idx + INSTANCE_BATCH_SIZE])
        command.extend(['--zone', zone])
        result = new_process.execute(command, expect_zero=False, **kwargs)
        error_occurred = error_occurred or result.retcode != 0

    return error_occurred


def list_instances() -> List[str]:
    """Return list of current running instances."""
    result = new_process.execute(['gcloud', 'compute', 'instances', 'list'])
    return [instance.split(' ')[0] for instance in result.output.splitlines()]


def set_default_project(cloud_project: str):
    """Set default project for future gcloud and gsutil commands."""
    return new_process.execute(
        ['gcloud', 'config', 'set', 'project', cloud_project])
