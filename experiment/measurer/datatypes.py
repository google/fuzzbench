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
"""Module for common data types and helping functions shared under the measurer
module."""
import collections
import json

SnapshotMeasureRequest = collections.namedtuple(
    'SnapshotMeasureRequest', ['fuzzer', 'benchmark', 'trial_id', 'cycle'])

RetryRequest = collections.namedtuple(
    'RetryRequest', ['fuzzer', 'benchmark', 'trial_id', 'cycle'])


def from_dict_to_snapshot_retry_request(values: dict):
    """Converts a dict into a RetryRequest named tuple."""
    return RetryRequest(values['fuzzer'], values['benchmark'],
                        values['trial_id'], values['cycle'])


def from_dict_to_snapshot_measure_request(values: dict):
    """Converts a dict into a SnapshotMeasureRequest named tuple."""
    return SnapshotMeasureRequest(values['fuzzer'], values['benchmark'],
                                  values['trial_id'], values['cycle'])


def from_snapshot_measure_request_to_bytes(
        snapshot_measure_request: SnapshotMeasureRequest) -> bytes:
    """Takes a snapshot measure request and transform it into bytes, so
    it can be published in a pub sub queue."""
    return json.dumps(snapshot_measure_request._asdict()).encode('utf-8')


def from_retry_request_to_bytes(retry_request: RetryRequest) -> bytes:
    """Takes a snapshot retry request and transform it into bytes, so
    it can be published in a pub sub queue."""
    return json.dumps(retry_request._asdict()).encode('utf-8')
