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

import pytest

from common import gcloud
from common import new_process
from test_libs import utils as test_utils

INSTANCE_NAME = 'instance-a'
ZONE = 'zone-a'
CONFIG = {'cloud_compute_zone': ZONE, 'service_account': 'blah'}


def test_ssh():
    """Tests that ssh works as expected."""
    with test_utils.mock_popen_ctx_mgr() as mocked_popen:
        gcloud.ssh(INSTANCE_NAME)
        assert mocked_popen.commands == [[
            'gcloud', 'beta', 'compute', 'ssh', INSTANCE_NAME
        ]]


@pytest.mark.parametrize(('kwargs_for_ssh', 'expected_argument'),
                         [
                             ({'command': 'ls'}, '--command=ls'),
                             ({'zone': ZONE}, '--zone=' + ZONE),
                         ]) # yapf: disable
def test_ssh_optional_arg(kwargs_for_ssh, expected_argument):
    """Tests that ssh works as expected when given an optional argument."""
    with test_utils.mock_popen_ctx_mgr() as mocked_popen:
        gcloud.ssh(INSTANCE_NAME, **kwargs_for_ssh)
        assert expected_argument in mocked_popen.commands[0]


@mock.patch('time.sleep')
@mock.patch('common.gcloud.ssh')
def test_robust_begin_gcloud_ssh_fail(_, mocked_ssh):
    """Tests that ssh works as expected."""
    with pytest.raises(Exception) as exception:
        gcloud.robust_begin_gcloud_ssh(INSTANCE_NAME, ZONE)
        assert mocked_ssh.call_count == 10
        assert exception.value == 'Couldn\'t SSH to instance.'


@mock.patch('time.sleep')
@mock.patch('common.gcloud.ssh')
def test_robust_begin_gcloud_ssh_pass(mocked_ssh, _):
    """Tests robust_begin_gcloud_ssh works as intended on google cloud."""
    mocked_ssh.return_value = new_process.ProcessResult(0, None, False)
    gcloud.robust_begin_gcloud_ssh(INSTANCE_NAME, ZONE)
    mocked_ssh.assert_called_with('instance-a',
                                  command='echo ping',
                                  expect_zero=False,
                                  zone='zone-a')


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
            '--machine-type=n1-standard-96',
            '--boot-disk-size=4TB',
            '--boot-disk-type=pd-ssd',
        ]]

def _get_expected_create_runner_command(instance_type):
    return [
        'gcloud',
        'compute',
        'instances',
        'create',
        'instance-a',
        '--image-family=cos-stable',
        '--image-project=cos-cloud',
        '--zone=zone-a',
        '--scopes=cloud-platform',
        '--no-address',
        '--machine-type=%s' % instance_type,
        '--boot-disk-size=30GB',
        ]
@pytest.mark.parametrize(('preemptible_runners'),
                         [
                             None, False
                         ]) # yapf: disable
def test_create_instance_not_preemptible(preemptible_runners):
    """Tests create_instance doesn't specify preemptible when it isn't supposed
    to."""
    config = CONFIG.copy()
    if preemptible_runners is not None:
        config['preemptible_runners'] = preemptible_runners
    with test_utils.mock_popen_ctx_mgr(returncode=1) as mocked_popen:
        gcloud.create_instance(INSTANCE_NAME, gcloud.InstanceType.RUNNER,
                               config)
        assert mocked_popen.commands == [
            _get_expected_create_runner_command('n1-standard-1')
        ]

def test_create_instance_preemptible():
    """Tests create_instance doesn't specify preemptible when it isn't supposed
    to."""
    config = CONFIG.copy()
    config['preemptible_runners'] = True
    with test_utils.mock_popen_ctx_mgr(returncode=1) as mocked_popen:
        gcloud.create_instance(INSTANCE_NAME, gcloud.InstanceType.RUNNER,
                               config)
        assert mocked_popen.commands == [
            _get_expected_create_runner_command('n1-standard-1-preemptible')
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
    # -q is needed otherwise gcloud will prompt "Y/N?".
    zone = 'us-central1-a'
    expected_command = (['gcloud', 'compute', 'instances', 'delete', '-q'] +
                        instances + ['--zone', zone])
    gcloud.delete_instances(instances, zone)
    mocked_execute.assert_called_with(expected_command, expect_zero=False)


@mock.patch('common.new_process.execute')
def test_delete_instances_greater_than_batch_size(mocked_execute):
    """Test that delete_instances works as intended when instance count is more
  than batch size."""
    instances = ['instance-%d' % i for i in range(103)]
    mocked_execute.return_value = new_process.ProcessResult(0, '', False)
    # -q is needed otherwise gcloud will prompt "Y/N?".
    zone = 'us-central1-a'
    gcloud.delete_instances(instances, zone)
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
