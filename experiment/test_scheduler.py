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
# See the License for the specific language governing permissions andsss
# limitations under the License.
"""Tests for scheduler.py"""
import datetime
from unittest import mock
from multiprocessing.pool import ThreadPool

import pytest

from common import gcloud
from common import new_process
from database import models
from database import utils as db_utils
from experiment import scheduler

FUZZER = 'fuzzer'
BENCHMARK = 'bench'

# pylint: disable=invalid-name,unused-argument,redefined-outer-name


@pytest.fixture
def pending_trials(db, experiment_config):
    """Adds trials to the database and returns pending trials."""
    other_experiment_name = experiment_config['experiment'] + 'other'
    db_utils.add_all([
        models.Experiment(name=experiment_config['experiment']),
        models.Experiment(name=other_experiment_name)
    ])

    def create_trial(experiment, time_started=None, time_ended=None):
        """Creates a database trial."""
        return models.Trial(experiment=experiment,
                            benchmark=BENCHMARK,
                            fuzzer=FUZZER,
                            time_started=time_started,
                            time_ended=time_ended)

    our_pending_trials = [
        create_trial(experiment_config['experiment']),
        create_trial(experiment_config['experiment'])
    ]
    other_trials = [
        create_trial(other_experiment_name),
        create_trial(experiment_config['experiment'], datetime.datetime.now()),
        create_trial(experiment_config['experiment'], datetime.datetime.now())
    ]
    db_utils.add_all(other_trials + our_pending_trials)
    our_trial_ids = [trial.id for trial in our_pending_trials]
    return db_utils.query(models.Trial).filter(
        models.Trial.id.in_(our_trial_ids))


@pytest.mark.parametrize(
    'benchmark,expected_image,expected_target',
    [('benchmark1', 'gcr.io/fuzzbench/runners/fuzzer-a/benchmark1',
      'fuzz-target'),
     ('bloaty_fuzz_target', 'gcr.io/fuzzbench/oss-fuzz/runners/fuzzer-a/bloaty',
      'fuzz_target')])
@mock.patch('common.gcloud.create_instance')
@mock.patch('common.fuzzer_config_utils.get_by_variant_name')
def test_create_trial_instance(  # pylint: disable=too-many-arguments
        mocked_get_by_variant_name, mocked_create_instance, benchmark,
        expected_image, expected_target, experiment_config):
    """Test that create_trial_instance invokes create_instance
    and creates a startup script for the instance, as we expect it to."""
    instance_name = 'instance1'
    fuzzer_param = 'variant'
    trial = 9
    mocked_create_instance.side_effect = lambda *args, **kwargs: None
    mocked_get_by_variant_name.return_value = {
        'fuzzer': 'fuzzer-a',
        'variant_name': 'variant',
        'env': {
            'C1': 'custom',
            'C2': 'custom2'
        },
    }
    scheduler.create_trial_instance(benchmark, fuzzer_param, trial,
                                    experiment_config)
    instance_name = 'r-test-experiment-9'
    expected_startup_script_path = '/tmp/%s-start-docker.sh' % instance_name

    mocked_create_instance.assert_called_with(
        instance_name,
        gcloud.InstanceType.RUNNER,
        experiment_config,
        startup_script=expected_startup_script_path)
    expected_format_string = '''#!/bin/bash
echo 0 > /proc/sys/kernel/yama/ptrace_scope
echo core >/proc/sys/kernel/core_pattern

while ! docker pull {docker_image_url}
do
  echo 'Error pulling image, retrying...'
done

docker run --privileged --cpuset-cpus=0 --rm \
-e INSTANCE_NAME=r-test-experiment-9 \
-e FUZZER=fuzzer-a -e BENCHMARK={benchmark} -e FUZZER_VARIANT_NAME=variant \
-e EXPERIMENT=test-experiment -e TRIAL_ID=9 -e MAX_TOTAL_TIME=86400 \
-e CLOUD_PROJECT=fuzzbench -e CLOUD_COMPUTE_ZONE=us-central1-a \
-e CLOUD_EXPERIMENT_BUCKET=gs://experiment-data \
-e FUZZ_TARGET={oss_fuzz_target} -e C1=custom -e C2=custom2 \
--cap-add SYS_NICE --cap-add SYS_PTRACE --name=runner-container \
{docker_image_url} 2>&1 | tee /tmp/runner-log.txt'''

    with open(expected_startup_script_path) as file_handle:
        assert file_handle.read() == expected_format_string.format(
            benchmark=benchmark,
            oss_fuzz_target=expected_target,
            docker_image_url=expected_image)


@mock.patch('common.gcloud.create_instance')
@mock.patch('common.fuzzer_config_utils.get_by_variant_name')
def test_start_trials_not_started(mocked_get_by_variant_name,
                                  mocked_create_instance, pending_trials,
                                  experiment_config):
    """Test that start_trials returns an empty list nothing when all trials fail
    to be created/started."""
    mocked_create_instance.return_value = False
    mocked_get_by_variant_name.return_value = {'fuzzer': 'test_fuzzer'}
    with ThreadPool() as pool:
        result = scheduler.start_trials(pending_trials, experiment_config, pool)
    assert result == []


@mock.patch('common.new_process.execute')
@mock.patch('common.fuzzer_config_utils.get_by_variant_name')
@mock.patch('experiment.scheduler.datetime_now')
def test_schedule(mocked_datetime_now, mocked_get_by_variant_name,
                  mocked_execute, pending_trials, experiment_config):
    """Tests that schedule() ends expired trials and starts new ones as
    needed."""
    mocked_execute.return_value = new_process.ProcessResult(0, '', False)
    mocked_get_by_variant_name.return_value = {'fuzzer': 'test_fuzzer'}
    datetimes_first_experiments_started = [
        trial.time_started for trial in db_utils.query(models.Trial).filter(
            models.Trial.experiment == experiment_config['experiment']).filter(
                models.Trial.time_started.isnot(None))
    ]

    mocked_datetime_now.return_value = (
        max(datetimes_first_experiments_started) +
        datetime.timedelta(seconds=(experiment_config['max_total_time'] +
                                    scheduler.GRACE_TIME_SECONDS * 2)))

    with ThreadPool() as pool:
        scheduler.schedule(experiment_config, pool)
    assert db_utils.query(models.Trial).filter(
        models.Trial.time_started.in_(
            datetimes_first_experiments_started)).all() == (db_utils.query(
                models.Trial).filter(models.Trial.time_ended.isnot(None)).all())

    assert pending_trials.filter(
        models.Trial.time_started.isnot(None)).all() == pending_trials.all()
