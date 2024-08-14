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
"""Tests for datatypes.py."""
import experiment.measurer.datatypes as measurer_datatypes

def test_from_dict_to_snapshot_retry_request():
    """Tests if a dictionary is being properly converted to a RetryRequest named
    tuple object."""
    dictionary = {'fuzzer': 'test-fuzzer', 'benchmark': 'test-benchmark',
                  'trial_id': 1, 'cycle': 0}
    result = measurer_datatypes.from_dict_to_snapshot_retry_request(dictionary)
    expected_retry_request = measurer_datatypes.RetryRequest('test-fuzzer',
                                                             'test-benchmark',
                                                             1, 0)
    assert result == expected_retry_request

def test_from_dict_to_snapshot_measure_request():
    """Tests if a dictionary is being properly converted to a
    SnapshotMeasureRequest named tuple object."""
    dictionary = {'fuzzer': 'test-fuzzer', 'benchmark': 'test-benchmark',
                  'trial_id': 1, 'cycle': 0}
    result = measurer_datatypes.from_dict_to_snapshot_measure_request(
        dictionary)
    expected_tuple = measurer_datatypes.SnapshotMeasureRequest('test-fuzzer',
                                                               'test-benchmark',
                                                                 1, 0)
    assert result == expected_tuple

def test_from_snapshot_measure_request_to_bytes():
    """Tests if a SnapshotMeasureRequest named tuple object is being
    successfully converted to bytes format."""
    snapshot_measure_request = measurer_datatypes.SnapshotMeasureRequest(
        'test-fuzzer', 'test-benchmark', 1, 0)
    req_as_bytes = measurer_datatypes.from_snapshot_measure_request_to_bytes(
        snapshot_measure_request)
    assert isinstance(req_as_bytes, bytes)

def test_from_snapshot_retry_request_to_bytes():
    """Tests if a RetryRequest named tuple object is being successfully
    converted to bytes format."""
    snapshot_retry_request = measurer_datatypes.RetryRequest('test-fuzzer',
                                                             'test-benchmark',
                                                             1, 0)
    snapshot_as_bytes = measurer_datatypes.from_retry_request_to_bytes(
        snapshot_retry_request)
    assert isinstance(snapshot_as_bytes, bytes)
