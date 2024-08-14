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
from unittest import mock
import multiprocessing
import pytest

from database.models import Snapshot
from experiment.measurer import measure_worker
import experiment.measurer.datatypes as measurer_datatypes


@pytest.fixture
def local_measure_worker():
    """Fixture for instantiating a local measure worker object."""
    request_queue = multiprocessing.Queue()
    response_queue = multiprocessing.Queue()
    region_coverage = False
    config = {
        'request_queue': request_queue,
        'response_queue': response_queue,
        'region_coverage': region_coverage
    }
    return measure_worker.LocalMeasureWorker(config)


@pytest.fixture
@mock.patch('google.cloud.pubsub_v1.PublisherClient')
@mock.patch('google.cloud.pubsub_v1.SubscriberClient')
def gcloud_measure_worker(_mock_subscriber_client, _mock_publisher_client):
    """Fixture for instantiating a google cloud measure worker object, with
    mocked subscriber and publisher clients, and mocked subscription creation"""
    config = {
        'region_coverage': False,
        'project_id': 'fuzzbench-test',
        'request_queue_topic_id': 'request_queue_topic_id',
        'response_queue_topic_id': 'response_queue_topic_id',
        'experiment': 'test',
    }
    return measure_worker.GoogleCloudMeasureWorker(config)


def test_process_measured_snapshot_as_serialized_snapshot(
        gcloud_measure_worker):  # pylint: disable=redefined-outer-name
    """Tests if process_measured_snapshot_result is serializing snapshot when
    called by a google cloud measure worker."""
    request = measurer_datatypes.SnapshotMeasureRequest('fuzzer', 'benchmark',
                                                        1, 0)
    snapshot = Snapshot(trial_id=1)
    result, _retry = gcloud_measure_worker.process_measured_snapshot_result(  # pylint: disable=line-too-long
        snapshot, request)
    assert isinstance(result, bytes)


def test_process_measured_snapshot_as_retry_request(local_measure_worker):  # pylint: disable=redefined-outer-name
    """"Tests the scenario where measure_snapshot is None, so task needs to be
    retried."""
    request = measurer_datatypes.SnapshotMeasureRequest('fuzzer', 'benchmark',
                                                        1, 0)
    snapshot = None
    result, _retry = local_measure_worker.process_measured_snapshot_result(
        snapshot, request)
    assert isinstance(result, measurer_datatypes.RetryRequest)


def test_process_measured_snapshot_as_snapshot(local_measure_worker):  # pylint: disable=redefined-outer-name
    """"Tests the scenario where measure_snapshot is not None, so snapshot is
    returned."""
    request = measurer_datatypes.SnapshotMeasureRequest('fuzzer', 'benchmark',
                                                        1, 0)
    snapshot = Snapshot(trial_id=1)
    result, _retry = local_measure_worker.process_measured_snapshot_result(
        snapshot, request)
    assert isinstance(result, Snapshot)


def test_put_snapshot_in_response_queue(local_measure_worker):  # pylint: disable=redefined-outer-name
    """Tests if result is being put in response queue as expected."""
    request = measurer_datatypes.SnapshotMeasureRequest('fuzzer', 'benchmark',
                                                        1, 0)
    snapshot = Snapshot(trial_id=1)
    result, retry = local_measure_worker.process_measured_snapshot_result(
        snapshot, request)
    local_measure_worker.put_result_in_response_queue(result, retry)
    assert local_measure_worker.response_queue.qsize() == 1


def test_get_task_from_request_queue_gcloud_worker_calls_acknowledge(
        gcloud_measure_worker):  # pylint: disable=redefined-outer-name
    """a"""
    pull_return = mock.MagicMock()
    received_message = mock.MagicMock()
    received_message.ack_id = 0

    # Since we are simulating getting an object from the queue, this object will
    # come serialized in bytes format
    unserialized_data = measurer_datatypes.SnapshotMeasureRequest(
        'fuzzer', 'benchmark', 1748392, 0)
    serialized_data = measurer_datatypes.from_snapshot_measure_request_to_bytes(
        unserialized_data)
    received_message.message.data = serialized_data

    # Mocking the pull method to return the serialized message
    pull_return.received_messages = [received_message]
    gcloud_measure_worker.subscriber_client.pull.return_value = pull_return

    _result = gcloud_measure_worker.get_task_from_request_queue()
    gcloud_measure_worker.subscriber_client.acknowledge.assert_called_once()


def test_get_task_from_request_queue_gcloud_worker(gcloud_measure_worker):  # pylint: disable=redefined-outer-name
    """a"""
    pull_return = mock.MagicMock()
    received_message = mock.MagicMock()
    received_message.ack_id = 0

    # Since we are simulating getting an object from the queue, this object will
    # come serialized in bytes format
    unserialized_data = measurer_datatypes.SnapshotMeasureRequest(
        'fuzzer', 'benchmark', 1748392, 0)
    serialized_data = measurer_datatypes.from_snapshot_measure_request_to_bytes(
        unserialized_data)
    received_message.message.data = serialized_data

    # Mocking the pull method to return the serialized message
    pull_return.received_messages = [received_message]
    gcloud_measure_worker.subscriber_client.pull.return_value = pull_return

    result = gcloud_measure_worker.get_task_from_request_queue()
    assert isinstance(result, measurer_datatypes.SnapshotMeasureRequest)
