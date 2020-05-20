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

from common import gcloud
from common import new_process
from database import models
from database import utils as db_utils
from experiment import scheduler

FUZZER = 'fuzzer'
BENCHMARK = 'bench'

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
        create_trial(experiment_config['experiment'], datetime.datetime.now()),
        create_trial(experiment_config['experiment'], datetime.datetime.now())
    ]
    db_utils.add_all(other_trials + our_pending_trials)
    our_trial_ids = [trial.id for trial in our_pending_trials]
    return db_utils.query(models.Trial).filter(
        models.Trial.id.in_(our_trial_ids))


@pytest.mark.parametrize(
    'benchmark,expected_image,expected_target',
    [('benchmark1', 'gcr.io/fuzzbench/runners/variant/benchmark1',
      'fuzz-target'),
     ('bloaty_fuzz_target',
      'gcr.io/fuzzbench/runners/variant/bloaty_fuzz_target', 'fuzz_target')])
def test_create_trial_instance(benchmark, expected_image, expected_target,
                               experiment_config):
    """Test that create_trial_instance invokes create_instance
    and creates a startup script for the instance, as we expect it to."""
    expected_startup_script = '''## Start docker.

while ! docker pull {docker_image_url}
do
  echo 'Error pulling image, retrying...'
done

docker run \\
--privileged --cpus=1 --rm \\
-e INSTANCE_NAME=r-test-experiment-9 \\
-e FUZZER=variant \\
-e BENCHMARK={benchmark} \\
-e EXPERIMENT=test-experiment \\
-e TRIAL_ID=9 \\
-e MAX_TOTAL_TIME=86400 \\
-e CLOUD_PROJECT=fuzzbench \\
-e CLOUD_COMPUTE_ZONE=us-central1-a \\
-e CLOUD_EXPERIMENT_BUCKET=gs://experiment-data \\
-e FUZZ_TARGET={oss_fuzz_target} \\
-e C1=custom -e C2=custom2 --name=runner-container \\
--cap-add SYS_NICE --cap-add SYS_PTRACE \\
{docker_image_url} 2>&1 | tee /tmp/runner-log.txt'''
    _test_create_trial_instance(benchmark, expected_image, expected_target,
                                expected_startup_script, experiment_config,
                                True)


@pytest.mark.parametrize(
    'benchmark,expected_image,expected_target',
    [('benchmark1', 'gcr.io/fuzzbench/runners/variant/benchmark1',
      'fuzz-target'),
     ('bloaty_fuzz_target',
      'gcr.io/fuzzbench/runners/variant/bloaty_fuzz_target', 'fuzz_target')])
def test_create_trial_instance_local_experiment(benchmark, expected_image,
                                                expected_target,
                                                experiment_config, environ):
    """Test that create_trial_instance invokes create_instance and creates a
    startup script for the instance, as we expect it to when running a
    local_experiment."""
    os.environ['LOCAL_EXPERIMENT'] = str(True)
    os.environ['HOST_GCLOUD_CONFIG'] = '~/.config/gcloud'
    expected_startup_script = '''## Start docker.


docker run -v ~/.config/gcloud:/root/.config/gcloud \\
--privileged --cpus=1 --rm \\
-e INSTANCE_NAME=r-test-experiment-9 \\
-e FUZZER=variant \\
-e BENCHMARK={benchmark} \\
-e EXPERIMENT=test-experiment \\
-e TRIAL_ID=9 \\
-e MAX_TOTAL_TIME=86400 \\
-e CLOUD_PROJECT=fuzzbench \\
-e CLOUD_COMPUTE_ZONE=us-central1-a \\
-e CLOUD_EXPERIMENT_BUCKET=gs://experiment-data \\
-e FUZZ_TARGET={oss_fuzz_target} \\
-e C1=custom -e C2=custom2 \\
--cap-add SYS_NICE --cap-add SYS_PTRACE \\
{docker_image_url} 2>&1 | tee /tmp/runner-log.txt'''
    _test_create_trial_instance(benchmark, expected_image, expected_target,
                                expected_startup_script, experiment_config,
                                False)


@mock.patch('common.gcloud.create_instance')
@mock.patch('common.fuzzer_config_utils.get_by_variant_name')
def _test_create_trial_instance(  # pylint: disable=too-many-locals
        benchmark, expected_image, expected_target, expected_startup_script,
        experiment_config, preemptible, mocked_get_by_variant_name,
        mocked_create_instance):
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
        check_from = '## Start docker.'
        assert check_from in content
        script_for_docker = content[content.find(check_from):]
        assert script_for_docker == expected_startup_script.format(
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
        result = scheduler.start_trials(pending_trials,
                                        experiment_config,
                                        pool,
                                        preemptible=True)
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
    experiment = experiment_config['experiment']
    datetimes_first_experiments_started = [
        trial.time_started for trial in db_utils.query(models.Trial).filter(
            models.Trial.experiment == experiment).filter(
                models.Trial.time_started.isnot(None))
    ]

    mocked_datetime_now.return_value = (
        max(datetimes_first_experiments_started) +
        datetime.timedelta(seconds=(experiment_config['max_total_time'] +
                                    scheduler.GRACE_TIME_SECONDS * 2)))

    num_trials = db_utils.query(
        models.Trial).filter(models.Trial.experiment == experiment).count()
    trial_instance_manager = scheduler.TrialInstanceManager(
        num_trials, experiment_config)
    with ThreadPool() as pool:
        scheduler.schedule(experiment_config, trial_instance_manager, pool)
    assert db_utils.query(models.Trial).filter(
        models.Trial.time_started.in_(
            datetimes_first_experiments_started)).all() == (db_utils.query(
                models.Trial).filter(models.Trial.time_ended.isnot(None)).all())

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


DEFAULT_NUM_TRIALS = 100


def get_trial_instance_manager(experiment_config):
    """Returns an instance of TrialInstanceManager for |experiment_config|."""
    if not db_utils.query(models.Experiment).filter(
            models.Experiment.name == experiment_config['experiment']).first():
        create_experiments(experiment_config)

    return scheduler.TrialInstanceManager(DEFAULT_NUM_TRIALS, experiment_config)


def test_get_time_since_last_trial_start_cached(db, experiment_config):
    """Tests that get_time_since_last_trial_start uses the cached value we give
    it."""
    experiment = experiment_config['experiment']
    db_utils.add_all([
        models.Experiment(name=experiment),
    ])
    trial_instance_manager = scheduler.TrialInstanceManager(
        1, experiment_config)
    one_day_ago = datetime.timedelta(days=1)
    yesterday = datetime.datetime.utcnow() - one_day_ago
    trial_instance_manager._last_trial_time_started = yesterday
    assert (trial_instance_manager.get_time_since_last_trial_start() >=
            one_day_ago)


def test_get_time_since_last_trial_start_pending_trials(pending_trials,
                                                        preempt_exp_conf):
    """Tests that get_time_since_last_trial_start returns 0 when there are still
    pending trials."""
    trial_instance_manager = get_trial_instance_manager(preempt_exp_conf)
    assert trial_instance_manager.get_time_since_last_trial_start() == 0
    assert trial_instance_manager._last_trial_time_started is None


def test_get_time_since_last_trial_start_no_pending(db, experiment_config):
    """Tests that get_time_since_last_trial_start returns the right result when
    there are no pending trials."""
    experiment = experiment_config['experiment']
    db_utils.add_all([
        models.Experiment(name=experiment),
    ])
    trial1 = models.Trial(experiment=experiment,
                          benchmark=BENCHMARK,
                          fuzzer=FUZZER)
    trial1.time_started = datetime.datetime.fromtimestamp(
        time.mktime(time.gmtime(0)))
    db_utils.add_all([trial1])
    trial_instance_manager = scheduler.TrialInstanceManager(
        1, experiment_config)
    # !!! mock utcnow
    assert trial_instance_manager._last_trial_time_started is None
    result = trial_instance_manager.get_time_since_last_trial_start()
    assert trial_instance_manager._last_trial_time_started is not None
    assert (trial_instance_manager.get_time_since_last_trial_start().days ==
            result.days)


# @pytest.mark.parametrize(
#     'preemptibles,nonpreemptibles',
#     [([], []), ([1], [0, 2])])
# def test_record_restarted_trials(preemptibles, nonpreemptibles, experiment_config, pending_trials):
#     trial_instance_manager = scheduler.TrialInstanceManager(
#         1, experiment_config)
#     fake_trial_entity = None
#     trial_instance_manager.preempted_trials = {trial_id: fake_trial_entity
#                                                for trial_id in range(3)}
#     trial_instance_manager.record_restarted_trials(
#         preemptibles, nonpreemptibles)
#     assert len(preemptibles) == trial_instance_manager.preemptible_starts
#     assert len(nonpreemptibles) == trial_instance_manager.nonpreemptible_starts
#     both_starts = set(preemptibles + nonpreemptibles)
#     expected_preempted_trials = {trial_id: fake_trial_entity for trial_id in range(3) if trial_id not in both_starts}
#     assert expected_preempted_trials == trial_instance_manager.preempted_trials


def test_can_start_nonpreemptible_not_preemptible_runners(preempt_exp_conf):
    """Tests that test_can_start_nonpreemptible returns True when
    'preemptible_runners' is not set to True in the experiment_config."""
    trial_instance_manager = get_trial_instance_manager(preempt_exp_conf)
    trial_instance_manager.experiment_config['preemptible_runners'] = False
    assert trial_instance_manager.can_start_nonpreemptible(100)


def test_can_start_nonpreemptible_above_max(preempt_exp_conf):
    """Tests that test_can_start_nonpreemptible returns True when
    'preemptible_runners' is not set to True in the experiment_config."""
    trial_instance_manager = get_trial_instance_manager(preempt_exp_conf)
    trials_left_to_run = 1
    assert not trial_instance_manager.can_start_nonpreemptible(
        trials_left_to_run, trial_instance_manager.max_nonpreemptibles)

    trial_instance_manager.nonpreemptible_starts = (
        trial_instance_manager.max_nonpreemptibles)
    assert not trial_instance_manager.can_start_nonpreemptible(
        trials_left_to_run)


def test_can_start_nonpreemptible_too_many_left(preempt_exp_conf):
    """Tests that we don't start using nonpreemptibles when there is so much
    left to run that using nonpreemptibles won't salvage the experiment."""
    trial_instance_manager = get_trial_instance_manager(preempt_exp_conf)
    trials_left_to_run = (
        trial_instance_manager.max_nonpreemptibles /
        trial_instance_manager.MAX_FRACTION_FOR_NONPREEMPTIBLES) + 1
    assert not trial_instance_manager.can_start_nonpreemptible(
        trials_left_to_run)


def test_can_start_nonpreemptible(preempt_exp_conf):
    """Tests that we can start a nonpreemptible under the right conditions."""
    trial_instance_manager = get_trial_instance_manager(preempt_exp_conf)
    trials_left_to_run = (
        trial_instance_manager.max_nonpreemptibles /
        trial_instance_manager.MAX_FRACTION_FOR_NONPREEMPTIBLES)
    nonpreemptible_starts = trial_instance_manager.max_nonpreemptibles - 1
    assert trial_instance_manager.can_start_nonpreemptible(
        trials_left_to_run, nonpreemptible_starts)


def test_can_start_preemptible_not_preemptible_runners(preempt_exp_conf):
    """Tests that test_can_start_preemptible returns False when
    'preemptible_runners' is not set to True in the experiment_config."""
    trial_instance_manager = get_trial_instance_manager(preempt_exp_conf)
    trial_instance_manager.experiment_config['preemptible_runners'] = False
    assert not trial_instance_manager.can_start_preemptible(100)


def test_can_start_preemptible_over_max_num(preempt_exp_conf):
    """Tests that we bound the number of preemptible trials we start."""
    trial_instance_manager = get_trial_instance_manager(preempt_exp_conf)
    preemptible_starts = trial_instance_manager.max_preemptibles + 1
    assert not trial_instance_manager.can_start_preemptible(preemptible_starts)
    trial_instance_manager.preemptible_starts = preemptible_starts
    assert not trial_instance_manager.can_start_preemptible()


@mock.patch(
    'experiment.scheduler.TrialInstanceManager.get_time_since_last_trial_start')
def test_can_start_preemptible_over_max_time(
        mocked_get_time_since_last_trial_start, preempt_exp_conf):
    """Tests that we bound the number of preemptible trials we start."""
    trial_instance_manager = get_trial_instance_manager(preempt_exp_conf)
    preemptible_starts = trial_instance_manager.max_preemptibles - 1
    one_day = datetime.timedelta(days=1).total_seconds()
    mocked_get_time_since_last_trial_start.return_value = (
        trial_instance_manager.preemptible_window + one_day)
    assert not trial_instance_manager.can_start_preemptible(preemptible_starts)
    assert mocked_get_time_since_last_trial_start.call_count == 1


def test_can_start_preemptible(preempt_exp_conf, pending_trials):
    """Tests that we can start a preemptible instance when expected."""
    trial_instance_manager = get_trial_instance_manager(preempt_exp_conf)
    preemptible_starts = 0
    assert trial_instance_manager.can_start_preemptible(preemptible_starts)


@mock.patch('experiment.scheduler.all_trials_ended', return_value=True)
def test_more_to_schedule_all_trials_ended(_, preempt_exp_conf, pending_trials):
    """Tests TrialInstanceManager.more_to_schedule returns False when there is
    more to schedule."""
    trial_instance_manager = get_trial_instance_manager(preempt_exp_conf)
    assert not trial_instance_manager.more_to_schedule()


@mock.patch('experiment.scheduler.all_trials_ended', return_value=False)
def test_more_to_schedule_pending_trials(_, experiment_config, pending_trials):
    """Tests TrialInstanceManager.more_to_schedule returns True when there are
    are trials that have never been started in a nonpreemptible_experiment"""
    trial_instance_manager = get_trial_instance_manager(experiment_config)
    assert trial_instance_manager.more_to_schedule()


@mock.patch('experiment.scheduler.get_running_trials', return_value=False)
@mock.patch('experiment.scheduler.all_trials_ended', return_value=False)
def test_more_to_schedule_running_trials_preemptible(_,
                                                     mocked_get_running_trials,
                                                     preempt_exp_conf):
    """Tests TrialInstanceManager.more_to_schedule returns True when there are
    all trials have been started but not all have ended in a nonpreemptible
    experiment."""
    trial_instance_manager = get_trial_instance_manager(preempt_exp_conf)
    trial = models.Trial(experiment=preempt_exp_conf['experiment'],
                         benchmark=BENCHMARK,
                         fuzzer=FUZZER,
                         time_started=datetime.datetime.utcnow(),
                         time_ended=None)
    db_utils.add_all([trial])

    def get_running_trials(_):
        return db_utils.query(models.Trial).filter(models.Trial.id == trial.id)

    mocked_get_running_trials.side_effect = get_running_trials

    assert trial_instance_manager.more_to_schedule()
    assert mocked_get_running_trials.call_count == 1


@pytest.mark.parametrize('return_value', [([], [None]), ([None], [])])
@mock.patch('experiment.scheduler.TrialInstanceManager.get_restartable_trials')
@mock.patch('experiment.scheduler.all_trials_ended', return_value=False)
def test_more_to_schedule_running_trials_restart(_,
                                                 mocked_get_restartable_trials,
                                                 return_value,
                                                 preempt_exp_conf):
    """Tests TrialInstanceManager.more_to_schedule returns True when there are
    all trials trials to restart."""
    trial_instance_manager = get_trial_instance_manager(preempt_exp_conf)
    mocked_get_restartable_trials.return_value = return_value
    assert trial_instance_manager.more_to_schedule()


@mock.patch('experiment.scheduler.TrialInstanceManager.get_restartable_trials')
@mock.patch('experiment.scheduler.all_trials_ended', return_value=False)
def test_more_to_schedule_running_trials_no_restart(
        _, mocked_get_restartable_trials, preempt_exp_conf):
    """Tests TrialInstanceManager.more_to_schedule returns False when there are
    no trials to restart."""
    trial_instance_manager = get_trial_instance_manager(preempt_exp_conf)
    mocked_get_restartable_trials.return_value = ([], [])
    assert not trial_instance_manager.more_to_schedule()
