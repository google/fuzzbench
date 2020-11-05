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
"""Tests for gce.py."""
from unittest import mock

from common import gce

PROJECT = 'my-cloud-project'
ZONE = 'my-compute-zone'
INSTANCE_GROUP = 'my-instance-group'
INSTANCE_TEMPLATE_URL = 'resource/my-instance-group'
EXPERIMENT = 'my-experiment'


@mock.patch('common.gce.get_instance_group_managers')
def test_delete_instance_group(mocked_get_instance_group_managers):
    """Tests that delete_instance_group uses the GCE API correctly."""
    mock_managers = mock.Mock()
    mocked_get_instance_group_managers.return_value = mock_managers
    gce.delete_instance_group(INSTANCE_GROUP, PROJECT, ZONE)
    assert mock_managers.delete.call_args_list == [
        mock.call(instanceGroupManager=INSTANCE_GROUP,
                  project=PROJECT,
                  zone=ZONE)
    ]


@mock.patch('common.gce.get_instance_group_managers')
def test_resize_instance_group(mocked_get_instance_group_managers):
    """Tests that resize_instance_group uses the GCE API correctly."""
    size = 10
    mock_managers = mock.Mock()
    mocked_get_instance_group_managers.return_value = mock_managers
    gce.resize_instance_group(size, INSTANCE_GROUP, PROJECT, ZONE)
    assert mock_managers.resize.call_args_list == [
        mock.call(instanceGroupManager=INSTANCE_GROUP,
                  size=size,
                  project=PROJECT,
                  zone=ZONE)
    ]


@mock.patch('common.gce.get_instance_group_managers')
def test_create_instance_group(mocked_get_instance_group_managers):
    """Tests that create_instance_group uses the GCE API correctly."""
    mock_managers = mock.Mock()
    mocked_get_instance_group_managers.return_value = mock_managers
    base_instance_name = 'm-' + EXPERIMENT
    gce.create_instance_group(INSTANCE_GROUP, INSTANCE_TEMPLATE_URL,
                              base_instance_name, PROJECT, ZONE)
    body = {
        'baseInstanceName': 'm-' + EXPERIMENT,
        'targetSize': 1,
        'name': INSTANCE_GROUP,
        'instanceTemplate': INSTANCE_TEMPLATE_URL,
    }
    assert mock_managers.insert.call_args_list == [
        mock.call(body=body, project=PROJECT, zone=ZONE)
    ]


@mock.patch('common.gce.get_instance_group_managers')
def test_get_instance_group_size(mocked_get_instance_group_managers):
    """Tests that get_instance_group_size uses the GCE API correctly and returns
    the right value."""
    mock_managers = mock.Mock()
    mocked_get_instance_group_managers.return_value = mock_managers
    mock_req = mock.Mock()
    mock_managers.get.return_value = mock_req
    size = 1
    mock_req.execute.return_value = {'targetSize': size}
    result = gce.get_instance_group_size(INSTANCE_GROUP, PROJECT, ZONE)
    assert mock_managers.get.call_args_list == [
        mock.call(instanceGroupManager=INSTANCE_GROUP,
                  project=PROJECT,
                  zone=ZONE)
    ]
    assert result == size
