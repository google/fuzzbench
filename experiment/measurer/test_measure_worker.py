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
"""Tests for measure_worker.py."""
import multiprocessing
import pytest

from database.models import Snapshot
from experiment.measurer import measure_worker
import experiment.measurer.datatypes as measurer_datatypes


@pytest.fixture
def local_measure_worker():
    """Fixture for instantiating a local measure worker object"""
    request_queue = multiprocessing.Queue()
    response_queue = multiprocessing.Queue()
    region_coverage = False
    config = {
        'request_queue': request_queue,
        'response_queue': response_queue,
        'region_coverage': region_coverage
    }
    return measure_worker.LocalMeasureWorker(config)


def test_put_snapshot_in_response_queue(local_measure_worker):  # pylint: disable=redefined-outer-name
    """Tests the scenario where measure_snapshot is not None, so snapshot is put
    in response_queue"""
    request = measurer_datatypes.SnapshotMeasureRequest('fuzzer', 'benchmark',
                                                        1, 0)
    snapshot = Snapshot(trial_id=1)
    local_measure_worker.put_result_in_response_queue(snapshot, request)
    response_queue = local_measure_worker.response_queue
    assert response_queue.qsize() == 1
    assert isinstance(response_queue.get(), Snapshot)


def test_put_retry_in_response_queue(local_measure_worker):  # pylint: disable=redefined-outer-name
    """Tests the scenario where measure_snapshot is None, so task needs to be
    retried"""
    request = measurer_datatypes.RetryRequest('fuzzer', 'benchmark', 1, 0)
    snapshot = None
    local_measure_worker.put_result_in_response_queue(snapshot, request)
    response_queue = local_measure_worker.response_queue
    assert response_queue.qsize() == 1
    assert isinstance(response_queue.get(), measurer_datatypes.RetryRequest)
