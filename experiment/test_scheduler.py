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
from multiprocessing.pool import ThreadPool
import os
import time
from unittest import mock

import pytest

from common import experiment_utils
from common import gcloud
from common import new_process
from database import models
from database import utils as db_utils
from experiment import scheduler

FUZZER = 'fuzzer'
BENCHMARK = 'bench'
ARBITRARY_DATETIME = datetime.datetime(2020, 1, 1)

# pylint: disable=invalid-name,unused-argument,redefined-outer-name,too-many-arguments,no-value-for-parameter,protected-access


def get_other_experiment_name(experiment_config):
    """Returns the name of an experiment different from the one in
    |experiment_config|."""
    return experiment_config['experiment'] + 'other'


def create_experiments(experiment_config):
    """Create the experiment experiment entity for the experiment in
    |experiment_config| and create another one and save the results to the
    db."""
    other_experiment_name = get_other_experiment_name(experiment_config)
    db_utils.add_all([
        models.Experiment(name=experiment_config['experiment']),
        models.Experiment(name=other_experiment_name)
    ])


@pytest.fixture
def pending_trials(db, experiment_config):
    """Adds trials to the database and returns pending trials."""
    create_experiments(experiment_config)

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
    other_experiment_name = get_other_experiment_name(experiment_config)
    other_trials = [
        create_trial(other_experiment_name),
        create_trial(experiment_config['experiment'], ARBITRARY_DATETIME),
        create_trial(experiment_config['experiment'], ARBITRARY_DATETIME)
    ]
    db_utils.add_all(other_trials + our_pending_trials)
    our_trial_ids = [trial.id for trial in our_pending_trials]
    with db_utils.session_scope() as session:
        return session.query(models.Trial).filter(
            models.Trial.id.in_(our_trial_ids))


@pytest.mark.parametrize(
    'benchmark,expected_image,expected_target',
    [('benchmark1',
      'gcr.io/fuzzbench/runners/fuzzer-a/benchmark1:test-experiment',
      'fuzz-target'),
     ('bloaty_fuzz_target',
      'gcr.io/fuzzbench/runners/fuzzer-a/bloaty_fuzz_target:test-experiment',
      'fuzz_target')])
def test_create_trial_instance(benchmark, expected_image, expected_target,
                               experiment_config):
    """Test that create_trial_instance invokes create_instance
    and creates a startup script for the instance, as we expect it to."""
    expected_startup_script = '''# Start docker.

# Hack because container-optmized-os doesn't support writing to /home/root.
# docker-credential-gcr needs to write to a dotfile in $HOME.
export HOME=/home/chronos
mkdir -p $HOME
docker-credential-gcr configure-docker -include-artifact-registry

while ! docker pull {docker_image_url}
do
  echo 'Error pulling image, retrying...'
done

docker run \\
--privileged --cpus=1 --rm \\
\\
-e INSTANCE_NAME=r-test-experiment-9 \\
-e FUZZER=fuzzer-a \\
-e BENCHMARK={benchmark} \\
-e EXPERIMENT=test-experiment \\
-e TRIAL_ID=9 \\
-e MAX_TOTAL_TIME=86400 \\
-e SNAPSHOT_PERIOD=900 \\
-e NO_SEEDS=False \\
-e NO_DICTIONARIES=False \\
-e OSS_FUZZ_CORPUS=False \\
-e CUSTOM_SEED_CORPUS_DIR=None \\
-e DOCKER_REGISTRY=gcr.io/fuzzbench -e CLOUD_PROJECT=fuzzbench -e CLOUD_COMPUTE_ZONE=us-central1-a \\
-e EXPERIMENT_FILESTORE=gs://experiment-data \\
-e REPORT_FILESTORE=gs://web-reports \\
-e FUZZ_TARGET={oss_fuzz_target} \\
-e LOCAL_EXPERIMENT=False \\
--name=runner-container \\
--cap-add SYS_NICE --cap-add SYS_PTRACE \\
--security-opt seccomp=unconfined \\
{docker_image_url} 2>&1 | tee /tmp/runner-log.txt'''
    with mock.patch('common.benchmark_utils.get_fuzz_target',
                    return_value=expected_target):
        _test_create_trial_instance(benchmark, expected_image, expected_target,
                                    expected_startup_script, experiment_config,
                                    True)


@pytest.mark.skip(reason='This should fail now because we don\'t tag images by '
                  'experiment in local experiments')
@pytest.mark.parametrize(
    'benchmark,expected_image,expected_target',
    [('benchmark1', 'gcr.io/fuzzbench/runners/fuzzer-a/benchmark1',
      'fuzz-target'),
     ('bloaty_fuzz_target',
      'gcr.io/fuzzbench/runners/fuzzer-a/bloaty_fuzz_target', 'fuzz_target')])
def test_create_trial_instance_local_experiment(benchmark, expected_image,
                                                expected_target,
                                                local_experiment_config,
                                                environ):
    """Test that create_trial_instance invokes create_instance and creates a
    startup script for the instance, as we expect it to when running a
    local_experiment."""
    os.environ['LOCAL_EXPERIMENT'] = str(True)
    expected_startup_script = '''# Start docker.


docker run \\
--privileged --cpus=1 --rm \\
\\
-e INSTANCE_NAME=r-test-experiment-9 \\
-e FUZZER=fuzzer-a \\
-e BENCHMARK={benchmark} \\
-e EXPERIMENT=test-experiment \\
-e TRIAL_ID=9 \\
-e MAX_TOTAL_TIME=86400 \\
-e DOCKER_REGISTRY=gcr.io/fuzzbench \\
-e EXPERIMENT_FILESTORE=/tmp/experiment-data -v /tmp/experiment-data:/tmp/experiment-data \\
-e REPORT_FILESTORE=/tmp/web-reports -v /tmp/web-reports:/tmp/web-reports \\
-e FUZZ_TARGET={oss_fuzz_target} \\
-e LOCAL_EXPERIMENT=True \\
\\
--cap-add SYS_NICE --cap-add SYS_PTRACE \\
--security-opt seccomp=unconfined \\
{docker_image_url} 2>&1 | tee /tmp/runner-log.txt'''
    _test_create_trial_instance(benchmark, expected_image, expected_target,
                                expected_startup_script,
                                local_experiment_config, False)


@mock.patch('common.gcloud.create_instance')
def _test_create_trial_instance(  # pylint: disable=too-many-locals
        benchmark, expected_image, expected_target, expected_startup_script,
        experiment_config, preemptible, mocked_create_instance):
    """Test that create_trial_instance invokes create_instance
    and creates a startup script for the instance, as we expect it to."""
    instance_name = 'instance1'
    fuzzer_param = 'fuzzer-a'
    trial = 9
    mocked_create_instance.side_effect = lambda *args, **kwargs: None
    scheduler.create_trial_instance(fuzzer_param, benchmark, trial,
                                    experiment_config, preemptible)
    instance_name = 'r-test-experiment-9'
    expected_startup_script_path = '/tmp/%s-start-docker.sh' % instance_name

    mocked_create_instance.assert_called_with(
        instance_name,
        gcloud.InstanceType.RUNNER,
        experiment_config,
        startup_script=expected_startup_script_path,
        preemptible=preemptible)

    with open(expected_startup_script_path) as file_handle:
        content = file_handle.read()
        check_from = '# Start docker.'
        assert check_from in content
        script_for_docker = content[content.find(check_from):]
        assert script_for_docker == expected_startup_script.format(
            benchmark=benchmark,
            oss_fuzz_target=expected_target,
            docker_image_url=expected_image)


@mock.patch('common.gcloud.create_instance')
@mock.patch('common.benchmark_utils.get_fuzz_target',
            return_value='fuzz-target')
def test_start_trials_not_started(mocked_create_instance, pending_trials,
                                  experiment_config):
    """Test that start_trials returns an empty list nothing when all trials fail
    to be created/started."""
    mocked_create_instance.return_value = False
    with ThreadPool() as pool:
        result = scheduler.start_trials(pending_trials, experiment_config, pool)
    assert result == []


@mock.patch('common.new_process.execute')
@mock.patch('experiment.scheduler.datetime_now')
@mock.patch('common.benchmark_utils.get_fuzz_target',
            return_value='fuzz-target')
@mock.patch('common.gce._get_instance_items', return_value=[])
def test_schedule(_, __, mocked_datetime_now, mocked_execute, pending_trials,
                  experiment_config):
    """Tests that schedule() ends expired trials and starts new ones as
    needed."""
    mocked_execute.return_value = new_process.ProcessResult(0, '', False)
    experiment = experiment_config['experiment']
    with db_utils.session_scope() as session:
        datetimes_first_experiments_started = [
            trial.time_started for trial in session.query(models.Trial).filter(
                models.Trial.experiment == experiment).filter(
                    models.Trial.time_started.isnot(None))
        ]

    mocked_datetime_now.return_value = (
        max(datetimes_first_experiments_started) +
        datetime.timedelta(seconds=(experiment_config['max_total_time'] +
                                    scheduler.GRACE_TIME_SECONDS * 2)))

    with ThreadPool() as pool:
        scheduler.schedule(experiment_config, pool)
    with db_utils.session_scope() as session:
        assert session.query(models.Trial).filter(
            models.Trial.time_started.in_(
                datetimes_first_experiments_started)).all() == (session.query(
                    models.Trial).filter(
                        models.Trial.time_ended.isnot(None)).all())

    assert pending_trials.filter(
        models.Trial.time_started.isnot(None)).all() == pending_trials.all()


def test_get_last_trial_time_started(db, experiment_config):
    """Tests that get_last_trial_time_started returns the time_started of the
    last trial to be started."""
    experiment = experiment_config['experiment']
    db_utils.add_all([
        models.Experiment(name=experiment),
    ])
    trial1 = models.Trial(experiment=experiment,
                          benchmark=BENCHMARK,
                          fuzzer=FUZZER)
    trial2 = models.Trial(experiment=experiment,
                          benchmark=BENCHMARK,
                          fuzzer=FUZZER)
    first_time = datetime.datetime.fromtimestamp(time.mktime(time.gmtime(0)))
    trial1.time_started = first_time
    last_time_started = first_time + datetime.timedelta(days=1)
    trial2.time_started = last_time_started
    trials = [trial1, trial2]
    db_utils.add_all(trials)

    assert scheduler.get_last_trial_time_started(
        experiment) == last_time_started


def test_get_last_trial_time_started_called_early(db, experiment_config):
    """Tests that get_last_trial_time_started raises an exception if called
    while there are still pending trials."""
    experiment = experiment_config['experiment']
    db_utils.add_all([
        models.Experiment(name=experiment),
    ])
    trial1 = models.Trial(experiment=experiment,
                          benchmark=BENCHMARK,
                          fuzzer=FUZZER)
    trial2 = models.Trial(experiment=experiment,
                          benchmark=BENCHMARK,
                          fuzzer=FUZZER)
    first_time = datetime.datetime.fromtimestamp(time.mktime(time.gmtime(0)))
    trial1.time_started = first_time
    trials = [trial1, trial2]
    db_utils.add_all(trials)
    with pytest.raises(AssertionError):
        scheduler.get_last_trial_time_started(experiment)


@pytest.fixture
def preempt_exp_conf(experiment_config, db):
    """Fixture that returns an |experiment_config| where preemptible_runners is
    True. Implicitly depnds on db fixture because most users of this fixture
    need it."""
    experiment_config['preemptible_runners'] = True
    return experiment_config


def get_trial_instance_manager(experiment_config: dict):
    """Returns an instance of TrialInstanceManager for |experiment_config|."""
    with db_utils.session_scope() as session:
        experiment_exists = bool(
            session.query(models.Experiment).filter(
                models.Experiment.name ==
                experiment_config['experiment']).first())

    if not experiment_exists:
        create_experiments(experiment_config)

    default_num_trials = 100
    return scheduler.TrialInstanceManager(default_num_trials, experiment_config)


def test_can_start_nonpreemptible_not_preemptible_runners(preempt_exp_conf):
    """Tests that test_can_start_nonpreemptible returns True when
    'preemptible_runners' is not set to True in the experiment_config."""
    trial_instance_manager = get_trial_instance_manager(preempt_exp_conf)
    trial_instance_manager.experiment_config['preemptible_runners'] = False
    assert trial_instance_manager.can_start_nonpreemptible(100000)


def test_can_start_nonpreemptible_above_max(preempt_exp_conf):
    """Tests that test_can_start_nonpreemptible returns True when we are above
    the maximum allowed for nonpreemptibles (and 'preemptible_runners' is not
    set to True in the experiment_config)."""
    trial_instance_manager = get_trial_instance_manager(preempt_exp_conf)
    assert not trial_instance_manager.can_start_nonpreemptible(
        trial_instance_manager.max_nonpreemptibles)


def test_can_start_nonpreemptible(preempt_exp_conf):
    """Tests that we can start a nonpreemptible under the right conditions."""
    trial_instance_manager = get_trial_instance_manager(preempt_exp_conf)
    assert trial_instance_manager.can_start_nonpreemptible(
        trial_instance_manager.max_nonpreemptibles - 1)


def test_can_start_preemptible_not_preemptible_runners(preempt_exp_conf):
    """Tests that test_can_start_preemptible returns False when
    'preemptible_runners' is not set to True in the experiment_config."""
    trial_instance_manager = get_trial_instance_manager(preempt_exp_conf)
    trial_instance_manager.experiment_config['preemptible_runners'] = False
    assert not trial_instance_manager.can_start_preemptible()


def test_can_start_preemptible(preempt_exp_conf, pending_trials):
    """Tests that we can start a preemptible instance when expected."""
    trial_instance_manager = get_trial_instance_manager(preempt_exp_conf)
    assert trial_instance_manager.can_start_preemptible()


def test_get_preempted_trials_nonpreemptible(experiment_config, db):
    """Tests that TrialInstanceManager.get_preempted_trials returns no trials
    for a nonpreemptible experiment."""
    trial_instance_manager = get_trial_instance_manager(experiment_config)
    assert trial_instance_manager.get_preempted_trials() == []


@mock.patch('common.gce._get_instance_items', return_value=[])
def test_get_preempted_trials_stale_preempted(_, preempt_exp_conf):
    """Tests that TrialInstanceManager.get_preempted_trials doesn't return
    trials that we already know were preempted."""
    trial_instance_manager = get_trial_instance_manager(preempt_exp_conf)
    trial = models.Trial(experiment=preempt_exp_conf['experiment'],
                         fuzzer=FUZZER,
                         benchmark=BENCHMARK)
    db_utils.add_all([trial])
    instance_name = experiment_utils.get_trial_instance_name(
        preempt_exp_conf['experiment'], trial.id)
    trial_instance_manager.preempted_trials = {instance_name: trial}
    with mock.patch(
            'experiment.scheduler.TrialInstanceManager.'
            '_get_started_unfinished_instances',
            return_value=[instance_name]):
        assert trial_instance_manager.get_preempted_trials() == []


def _get_preempted_instance_item(trial_id, exp_conf):
    instance_name = experiment_utils.get_trial_instance_name(
        exp_conf['experiment'], trial_id)
    return {
        'id': '1',
        'name': instance_name,
        'status': 'TERMINATED',
        'scheduling': {
            'preemptible': True,
        }
    }


@mock.patch('common.gce._get_instance_items')
def test_get_preempted_trials_new_preempted(mocked_get_instance_items,
                                            preempt_exp_conf):
    """Tests that TrialInstanceManager.get_preempted_trials returns trials that
    new preempted trials we don't know about until we query for them and not
    trials that we already knew were preempted."""
    trial_instance_manager = get_trial_instance_manager(preempt_exp_conf)

    # Create trials.
    experiment = preempt_exp_conf['experiment']
    time_started = ARBITRARY_DATETIME
    known_preempted = models.Trial(experiment=experiment,
                                   fuzzer=FUZZER,
                                   benchmark=BENCHMARK,
                                   time_started=time_started)
    unknown_preempted = models.Trial(experiment=experiment,
                                     fuzzer=FUZZER,
                                     benchmark=BENCHMARK,
                                     time_started=time_started)
    trials = [known_preempted, unknown_preempted]
    db_utils.add_all(trials)
    mocked_get_instance_items.return_value = [
        _get_preempted_instance_item(trial.id, preempt_exp_conf)
        for trial in trials
    ]

    trial_instance_manager.preempted_trials = {
        known_preempted.id: known_preempted
    }
    result = trial_instance_manager.get_preempted_trials()
    expected_result = [unknown_preempted]
    assert result == expected_result
