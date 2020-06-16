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
import posixpath

from common import gce


def test_get_instance_from_preempted_operation():
    """Tests that _get_instance_from_preemption_operation returns the correct
    value."""
    expected_instance = 'r-my-experiment-100'
    base_target_link = 'www.myresourceurl/'
    target_link = posixpath.join(base_target_link, expected_instance)
    operation = {'targetLink': target_link}
    instance = gce.get_instance_from_preempted_operation(
        operation, base_target_link)

    assert instance == expected_instance
