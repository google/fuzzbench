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
"""Tests for gcloud.py."""

from unittest import mock

from common import gcloud
from common import new_process
from test_libs import utils as test_utils

INSTANCE_NAME = 'instance-a'
ZONE = 'zone-a'
MACHINE_TYPE = 'my-machine-type'
CONFIG = {
    'cloud_compute_zone': ZONE,
    'service_account': 'blah',
    'runner_machine_type': MACHINE_TYPE
}


def test_create_instance():
    """Tests create_instance creates an instance."""
    with test_utils.mock_popen_ctx_mgr(returncode=1) as mocked_popen:
        gcloud.create_instance(INSTANCE_NAME, gcloud.InstanceType.DISPATCHER,
                               CONFIG)
        assert mocked_popen.commands == [[
            'gcloud',
            'compute',
            'instances',
            'create',
            'instance-a',
            '--image-family=cos-stable',
            '--image-project=cos-cloud',
            '--zone=zone-a',
            '--scopes=cloud-platform',
            '--machine-type=n1-highmem-96',
            '--boot-disk-size=4TB',
            '--boot-disk-type=pd-ssd',
        ]]


def _get_expected_create_runner_command(is_preemptible):
    command = [
        'gcloud',
        'compute',
        'instances',
        'create',
        'instance-a',
        '--image-family=cos-stable',
        '--image-project=cos-cloud',
        '--zone=zone-a',
        '--scopes=cloud-platform',
        '--machine-type=my-machine-type',
        '--no-address',
        '--boot-disk-size=30GB',
    ]
    if is_preemptible:
        command.append('--preemptible')
    return command


def test_create_instance_not_preemptible():
    """Tests create_instance doesn't specify preemptible when it isn't supposed
    to."""
    with test_utils.mock_popen_ctx_mgr(returncode=1) as mocked_popen:
        gcloud.create_instance(INSTANCE_NAME, gcloud.InstanceType.RUNNER,
                               CONFIG)
        assert mocked_popen.commands == [
            _get_expected_create_runner_command(False)
        ]


def test_create_instance_preemptible():
    """Tests create_instance doesn't specify preemptible when it isn't supposed
    to."""
    with test_utils.mock_popen_ctx_mgr(returncode=1) as mocked_popen:
        gcloud.create_instance(INSTANCE_NAME,
                               gcloud.InstanceType.RUNNER,
                               CONFIG,
                               preemptible=True)
        assert mocked_popen.commands == [
            _get_expected_create_runner_command(True)
        ]


@mock.patch('common.new_process.execute')
def test_create_instance_failed_create(mocked_execute):
    """Tests create_instance creates an instance if it doesn't already
    exist."""
    mocked_execute.return_value = new_process.ProcessResult(1, '', False)
    # We shouldn't exception here.
    assert not gcloud.create_instance(INSTANCE_NAME,
                                      gcloud.InstanceType.DISPATCHER, CONFIG)
    # Check that the first call is to create the instance.
    assert 'create' in mocked_execute.call_args_list[0][0][0]


@mock.patch('common.new_process.execute')
def test_delete_instances_less_than_batch_size(mocked_execute):
    """Test that delete_instances works as intended when instance count is less
    than batch size."""
    instances = ['instance-%d' % i for i in range(5)]
    mocked_execute.return_value = new_process.ProcessResult(0, '', False)
    zone = 'us-central1-a'
    expected_command = (['gcloud', 'compute', 'instances', 'delete', '-q'] +
                        instances + ['--zone', zone])
    result = gcloud.delete_instances(instances, zone)
    assert result
    mocked_execute.assert_called_with(expected_command, expect_zero=False)


@mock.patch('common.new_process.execute')
def test_delete_instances_greater_than_batch_size(mocked_execute):
    """Test that delete_instances works as intended when instance count is more
  than batch size."""
    instances = ['instance-%d' % i for i in range(103)]
    mocked_execute.return_value = new_process.ProcessResult(0, '', False)
    zone = 'us-central1-a'
    result = gcloud.delete_instances(instances, zone)
    assert result
    expected_command_1 = (['gcloud', 'compute', 'instances', 'delete', '-q'] +
                          ['instance-%d' % i for i in range(100)] +
                          ['--zone', zone])
    expected_command_2 = (['gcloud', 'compute', 'instances', 'delete', '-q'] +
                          ['instance-%d' % i for i in range(100, 103)] +
                          ['--zone', zone])
    mocked_execute.assert_has_calls([
        mock.call(expected_command_1, expect_zero=False),
        mock.call(expected_command_2, expect_zero=False)
    ])


@mock.patch('common.new_process.execute')
def test_delete_instances_fail(mocked_execute):
    """Test that delete_instances returns False when instance deletion fails."""
    instances = ['instance-%d' % i for i in range(5)]
    mocked_execute.return_value = new_process.ProcessResult(1, 'Error', False)
    zone = 'us-central1-a'
    expected_command = (['gcloud', 'compute', 'instances', 'delete', '-q'] +
                        instances + ['--zone', zone])
    result = gcloud.delete_instances(instances, zone)
    assert not result
    mocked_execute.assert_called_with(expected_command, expect_zero=False)


@mock.patch('common.new_process.execute')
def test_create_instance_template(mocked_execute):
    """Tests that create_instance_template uses the correct gcloud command and
    returns the correct instance template URL."""
    template_name = 'my-template'
    docker_image = 'docker_image'
    env = {'ENV_VAR': 'value'}
    project = 'fuzzbench'
    result = gcloud.create_instance_template(template_name, docker_image, env,
                                             project, ZONE)
    expected_command = [
        'gcloud', 'compute', '--project', project, 'instance-templates',
        'create-with-container', template_name, '--no-address',
        '--image-family=cos-stable', '--image-project=cos-cloud',
        '--region=zone-a', '--scopes=cloud-platform',
        '--machine-type=n1-standard-1', '--boot-disk-size=50GB',
        '--preemptible', '--container-image', docker_image, '--container-env',
        'ENV_VAR=value'
    ]
    mocked_execute.assert_called_with(expected_command)
    expected_result = (
        'https://www.googleapis.com/compute/v1/projects/{project}'
        '/global/instanceTemplates/{name}').format(project=project,
                                                   name=template_name)
    assert result == expected_result


@mock.patch('common.new_process.execute')
def test_delete_instance_template(mocked_execute):
    """Tests that delete_instance_template uses the correct gcloud command to
    delete an instance template."""
    template_name = 'my-template'
    gcloud.delete_instance_template(template_name)
    expected_command = [
        'gcloud', 'compute', 'instance-templates', 'delete', template_name
    ]
    mocked_execute.assert_called_with(expected_command)
