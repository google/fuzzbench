# Copyright 2024 Google LLC
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
"""Tests for methods under models.py."""
import pytest

from database import models

@pytest.fixture()
def snapshot():
    """Simple pytest fixture to return a model snapshot."""
    return models.Snapshot(trial_id=1)

def assert_dicts_equal_ignoring_order(dict1, dict2):
    """Helping function to check if two dictionaries have the same keys, and
    same values for each key, ignoring the keys order."""
    assert set(dict1.keys()) == set(dict2.keys())
    for key in dict1:
        assert dict1[key] == dict2[key]

def test_snapshot_to_bytes(snapshot):  # pylint: disable=redefined-outer-name
    """Tests if a snapshot model is being successfully converted to bytes
    format."""
    snapshot_as_bytes = snapshot.to_bytes()
    assert isinstance(snapshot_as_bytes, bytes)

def test_snapshot_as_dict(snapshot):  # pylint: disable=redefined-outer-name
    """Tests if a snapshot model is being successfully converted to a
    dictionary."""
    snapshot_as_dict = snapshot.as_dict()
    expected_dict = {'edges_covered': None, 'fuzzer_stats': None, 'time': None,
                     'trial_id': 1}
    assert_dicts_equal_ignoring_order(snapshot_as_dict, expected_dict)
    