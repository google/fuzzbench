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
"""Tests for measure_manager.py."""
import os
import datetime
from unittest import mock
import queue

import pytest

from common import new_process
from database import models
from database import utils as db_utils
from experiment.measurer import measure_manager

MAX_TOTAL_TIME = 100
ARBITRARY_DATETIME = datetime.datetime(2020, 1, 1)
EXPERIMENT_NAME = 'experiment'
FUZZER = 'fuzzer'
BENCHMARK = 'benchmark'

# pylint: disable=unused-argument,invalid-name


@mock.patch('common.filestore_utils.ls')
@mock.patch(
    'experiment.measurer.measure_manager.MeasureJobManager.run_scheduler')
def test_measure_all_trials_not_ready(mocked_run_scheduler, mocked_ls,
                                      experiment, experiment_config, db):
    """Test running measure_all_trials before it can start measuring."""
    mocked_ls.return_value = new_process.ProcessResult(1, '', False)
    manager = measure_manager.MeasureJobManager(experiment_config, queue)
    assert measure_manager.measure_all_trials(manager)
    assert not mocked_run_scheduler.called


@mock.patch('common.new_process.execute')
@mock.patch('common.filesystem.directories_have_same_files')
@pytest.mark.skip(reason="See crbug.com/1012329")
def test_measure_all_trials_no_more(mocked_directories_have_same_files,
                                    mocked_execute, experiment_config):
    """Test measure_all_trials does what is intended when the experiment is
    done."""
    mocked_directories_have_same_files.return_value = True
    mocked_execute.return_value = new_process.ProcessResult(0, '', False)
    manager = measure_manager.MeasureJobManager(experiment_config, queue)
    assert not measure_manager.measure_all_trials(manager)


@mock.patch('experiment.schedule_measure_workers.teardown')
@mock.patch('experiment.schedule_measure_workers.initialize')
@mock.patch('experiment.scheduler.all_trials_ended')
@mock.patch('experiment.measurer.measure_manager.measure_all_trials')
def test_measure_loop_end(mocked_measure_all_trials, mocked_all_trials_ended, _,
                          __, experiment_config):
    """Tests that measure_loop stops when there is nothing left to measure."""
    call_count = 0

    def mock_measure_all_trials(*args, **kwargs):
        # Do the assertions here so that there will be an assert fail on failure
        # instead of an infinite loop.
        nonlocal call_count
        assert call_count == 0
        call_count += 1
        return False

    mocked_measure_all_trials.side_effect = mock_measure_all_trials
    mocked_all_trials_ended.return_value = True
    measure_manager.measure_loop(experiment_config)
    # If everything went well, we should get to this point without any exception
    # failures.


@mock.patch('common.new_process.execute')
def test_path_exists_in_experiment_filestore(mocked_execute, environ):
    """Tests that path_exists_in_experiment_filestore calls gsutil properly."""
    work_dir = '/work'
    os.environ['WORK'] = work_dir
    os.environ['EXPERIMENT_FILESTORE'] = 'gs://cloud-bucket'
    os.environ['EXPERIMENT'] = 'example-experiment'
    measure_manager.exists_in_experiment_filestore(work_dir)
    mocked_execute.assert_called_with(
        ['gsutil', 'ls', 'gs://cloud-bucket/example-experiment'],
        expect_zero=False)


def test_trial_ended(db):
    """Tests that trial_ended returns the correct value for a trial that has
    ended and that it returns the correct value for a trial that has not
    ended."""
    db_utils.add_all([models.Experiment(name=EXPERIMENT_NAME)])
    ended_trial = models.Trial(experiment=EXPERIMENT_NAME,
                               benchmark=BENCHMARK,
                               fuzzer=FUZZER,
                               time_started=ARBITRARY_DATETIME,
                               time_ended=ARBITRARY_DATETIME)

    not_ended_trial = models.Trial(experiment=EXPERIMENT_NAME,
                                   benchmark=BENCHMARK,
                                   fuzzer=FUZZER,
                                   time_started=ARBITRARY_DATETIME)
    db_utils.add_all([ended_trial, not_ended_trial])
    assert measure_manager.trial_ended(ended_trial.id)
    assert not measure_manager.trial_ended(not_ended_trial.id)
