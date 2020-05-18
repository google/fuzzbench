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
"""Code for starting and ending trials."""
import datetime
import math
import multiprocessing
import os
import shlex
import sys
import random
import time

import jinja2
import sqlalchemy

from common import benchmark_utils
from common import experiment_utils
from common import fuzzer_config_utils
from common import gcloud
from common import gce
from common import logs
from common import utils
from common import yaml_utils
from database import models
from database import utils as db_utils

# Give the trial runner a little extra time to shut down and account for how
# long it can take to actually start running once an instance is started. 5
# minutes is an arbitrary amount of time.
GRACE_TIME_SECONDS = 5 * 60

FAIL_WAIT_SECONDS = 10 * 60

logger = logs.Logger('scheduler')  # pylint: disable=invalid-name

RESOURCES_DIR = os.path.join(utils.ROOT_DIR, 'experiment', 'resources')

JINJA_ENV = jinja2.Environment(
    undefined=jinja2.StrictUndefined,
    loader=jinja2.FileSystemLoader(RESOURCES_DIR),
)


def datetime_now() -> datetime.datetime:
    """Return datetime.datetime.utcnow(). This function is needed for
    mocking."""
    return datetime.datetime.now(datetime.timezone.utc)


# TODO(metzman): Figure out what are the best practices for the functions which
# must return sqlalchemy.orm.Query. Importing it just for annotation might be
# confusing to readers. There may also be weird situations where it is
# acceptable to use a list or query (because of duck typing) but type hints
# prevents us unless handled intelligently.
def get_experiment_trials(experiment: str):
    """Returns a query of trials in |experiment|."""
    return db_utils.query(models.Trial).filter(
        models.Trial.experiment == experiment).order_by(models.Trial.id)


def get_pending_trials(experiment: str):
    """Returns trial entities from |experiment| that have not run yet."""
    return get_experiment_trials(experiment).filter(
        models.Trial.time_started.is_(None))


def get_running_trials(experiment: str):
    """Returns trial entities from |experiment| that have been marked started
    but not marked ended."""
    return get_experiment_trials(experiment).filter(
        models.Trial.time_ended.is_(None),
        models.Trial.time_started.isnot(None))


def get_expired_trials(experiment: str, max_total_time: int):
    """Returns trial entities from |experiment| that have not ended and were
    started more than |max_total_time| + |GRACE_TIME_SECONDS| ago."""
    earliest_nonexpired_dt = datetime_now() - datetime.timedelta(
        seconds=max_total_time + GRACE_TIME_SECONDS)

    return get_experiment_trials(experiment).filter(
        models.Trial.time_started <= earliest_nonexpired_dt).filter(
            models.Trial.time_ended.is_(None))


def all_trials_ended(experiment: str) -> bool:
    """Return a bool if there are any trials in |experiment| that have not
    started."""
    return not get_experiment_trials(experiment).filter(
        models.Trial.time_ended.is_(None)).all()


def end_expired_trials(experiment_config: dict):
    """Get all expired trials, end them and return them."""
    trials_past_expiry = get_expired_trials(experiment_config['experiment'],
                                            experiment_config['max_total_time'])
    expired_instances = []
    current_dt = datetime_now()
    for trial in trials_past_expiry:
        expired_instances.append(
            experiment_utils.get_trial_instance_name(
                experiment_config['experiment'], trial.id))
        trial.time_ended = current_dt

    # Bail out here because trials_past_expiry will be truthy until evaluated.
    if not expired_instances:
        return

    # Delete instances for expired trials.
    running_instances = gcloud.list_instances()
    instances_to_delete = [
        i for i in expired_instances if i in running_instances
    ]
    if instances_to_delete and not gcloud.delete_instances(
            instances_to_delete, experiment_config['cloud_compute_zone']):
        # If we failed to delete some instances, then don't update the status
        # of expired trials in database as we don't know which instances were
        # successfully deleted. Wait for next iteration of end_expired_trials.
        logger.error('Failed to delete instances after trial expiry.')
        return

    db_utils.bulk_save(trials_past_expiry)


def get_last_trial_time_started(experiment: str):
    """Returns the time_started of the last trial that was started in
    |experiment|. This function cannot be called if there are any unstarted
    (e.g. pending trials). It will raise an assertion failure if there are any
    pending trials because it does not make sense to call this function before
    that time."""
    assert get_pending_trials(experiment).first() is None
    last_trial = get_experiment_trials(experiment).order_by(
        sqlalchemy.desc(models.Trial.time_started)).limit(1)
    return last_trial.time_started


class TrialInstanceManager:  # pylint: disable=too-many-instance-attributes
    """Manager for trial instances."""

    def __init__(self, num_trials, experiment_config):
        self.experiment_config = experiment_config
        self.num_trials = num_trials
        self.max_nonpreemptibles = min(math.ceil(self.num_trials / 20), 500)
        self.nonpreemptible_starts = 0
        self.max_preemptibles = self.num_trials * 2
        self.preemptible_window = 3 * experiment_config['max_total_time']
        self.preemptible_starts = 0
        self.preempted_trials = {}
        experiment = experiment_config['experiment']

        self._last_trial_time_started = None

        # Filter operations happening before the experiment started.
        self.last_preemptible_query = (db_utils.query(models.Experiment).filter(
            models.Experiment.name == experiment).one().time_created)

    def get_time_since_last_trial_start(self):
        """Get the time since the last trial in the experiment started."""
        if self._last_trial_time_started is not None:
            return datetime.datetime.utcnow() - self._last_trial_time_started

        pending_trials = get_pending_trials(
            self.experiment_config['experiment'])

        if pending_trials.first():
            # The last trial hasn't started.
            return 0

        self._last_trial_time_started = get_last_trial_time_started(
            self.experiment_config['experiment'])
        return datetime.datetime.utcnow() - self._last_trial_time_started

    def can_start_preemptible(self, preemptible_starts=None):
        """Returns True if we can start a preemptible trial."""
        if preemptible_starts is None:
            preemptible_starts = self.preemptible_starts

        if preemptible_starts > self.max_preemptibles:
            # Don't create more than the maximum number of preemptibles or else
            # costs can be infinite in the (highly unlikely) worst case
            # scenario.
            return False

        if self.get_time_since_last_trial_start() > self.preemptible_window:
            # Don't keep creating preemptibles forever. Stop creating them after
            # a certain time period so that we can switch to nonpreemptibles or
            # terminate the experiment and let the user deal with the issue if
            # we can't run this experiment in a reasonable amount of time.
            return False

        # Otherwise, it's fine to create a preemptible instance.
        return True

    def can_start_nonpreemptible(self,
                                 num_trials_to_run,
                                 nonpreemptible_starts=None):
        """Returns True if we can start a nonpreemptible trial."""
        if not self.experiment_config['preemptible_runners']:
            return True
        if nonpreemptible_starts is None:
            nonpreemptible_starts = self.nonpreemptible_starts
        if nonpreemptible_starts >= self.max_nonpreemptibles:
            # Don't exceed our maximum preemptibles.
            return False

        if num_trials_to_run / 4 <= self.max_nonpreemptibles:
            return True
        # Don't supplement with nonpreemptibles if the experiment results are so
        # messed up that doing won't make the result useable.
        return False

    def get_restartable_trials(self):
        """Returns a tuple containing the list of trials that can be started on
        preemptibles and trials that can be started on nonpreemptibles."""
        start_as_preemptible = []
        preemptible_starts = self.preemptible_starts

        start_as_nonpreemptible = []
        nonpreemptible_starts = self.nonpreemptible_starts

        trials = list(self.get_preempted_trials())
        num_trials = len(trials)
        for trial in trials:
            if self.can_start_preemptible(preemptible_starts):
                preemptible_starts += 1
                start_as_preemptible.append(trial)
                continue

            if self.can_start_nonpreemptible(num_trials, nonpreemptible_starts):
                nonpreemptible_starts += 1
                start_as_nonpreemptible.append(trial)

        return preemptible_starts, nonpreemptible_starts

    def get_preempted_trials(self):
        """Returns a list of preempted trials."""
        if not self.experiment_config['preemptible_runners']:
            return
        # TODO(metzman): Use time so that we aren't requerying the same trials
        for trial in self.preempted_trials.values():
            yield trial
        new_last_query = datetime.datetime.utcnow()
        project = self.experiment_config['project']
        zone = self.experiment_config['zone']
        operations = gce.filter_by_end_time(self.last_preemptible_query,
                                            gce.get_operations(project, zone))
        preemption_operations = list(gce.get_preemption_operations(operations))
        self.last_preemptible_query = new_last_query
        base_str = 'https://www.googleapis.com/compute/v1/projects/{project}/zones/{zone}/instances/'.format(
            project=project, zone=zone)
        experiment = self.experiment_config['experiment']
        running_trials = get_running_trials(experiment)
        running_instances = {
            experiment_utils.get_trial_instance_name(experiment, trial.id):
            trial for trial in running_trials
        }
        for operation in preemption_operations:
            instance = operation['targetLink'][len(base_str):]
            trial = running_instances.get(instance)
            if trial is None:
                continue
            if trial.id in self.preempted_trials:
                continue
            self.preempted_trials[trial.id] = trial
            yield trial

    def record_restarted_trials(self, restarted_as_preemptibles,
                                restarted_as_nonpreemptibles):
        """Record that certain trials were restarted. Trials that are restarted
        on preemptibles should be passed in |restarted_as_preemptibles| while
        trials that are restarted as nonpreemptibles should be passed in
        |restarted_as_nonpreemptibles|."""
        for trial in restarted_as_preemptibles:
            del self.preempted_trials[trial.id]
            self.preemptible_starts += 1

        for trial in restarted_as_nonpreemptibles:
            del self.preempted_trials[trial.id]
            self.nonpreemptible_starts += 1

    def more_to_schedule(self):
        """Returns True if there is nothing left to schedule."""
        experiment = self.experiment_config['experiment']
        if all_trials_ended(experiment):
            return False

        # We can always schedule trials for the first time, so if there are any
        # unstarted trials we know there are more to schedule and that they
        # won't go over the limits our heuristics set when using
        # preemptible_runners.
        if get_pending_trials(experiment).first() is not None:
            return True

        if (self.experiment_config.get('preemptible_runners') and
                get_running_trials(experiment).first()):
            # If there are any running trials, they will need to be scheduled.
            return True

        restart_as_preemptibles, restart_as_nonpreemptibles = (
            self.get_restartable_trials())

        return bool(restart_as_preemptibles) or bool(restart_as_nonpreemptibles)


def restart_preempted_trials(trial_instance_manager, pool):
    """Restarts preempted trials based on heuristics for saving money
    while still producing complete results quickly."""
    restart_as_preemptibles, restart_as_nonpreemptibles = (
        trial_instance_manager.get_restartable_trials())

    # Delete preempted trials.
    experiment_config = trial_instance_manager.experiment_config
    experiment_name = experiment_config['experiment']
    trial_instance_names = [
        trial.get_trial_instance_name(experiment_name, trial.id)
        for trial in restart_as_nonpreemptibles + restart_as_preemptibles
    ]
    zone = experiment_config['zone']
    success = gcloud.delete_instances(trial_instance_names, zone)
    if not success:
        # !!! Return two? (error status being the new)
        return []  # !!! IF WE FAIL ONCE DELETING DO WE PERMANENTLY FAIL?

    # Restart nonpreemptibles.
    experiment_config = trial_instance_manager.experiment_config
    restarted_preemptibles = start_trials(restart_as_preemptibles,
                                          experiment_config,
                                          pool,
                                          preemptible=True)

    # Update manager.
    trial_instance_manager.record_restarted_trials(restarted_preemptibles, [])

    if not restart_as_nonpreemptibles:
        return restarted_preemptibles

    restarted_nonpreemptibles = start_trials(restart_as_nonpreemptibles,
                                             experiment_config,
                                             pool,
                                             preemptible=False)
    # Update manager.
    trial_instance_manager.record_restarted_trials([],
                                                   restarted_nonpreemptibles)
    return restarted_preemptibles + restarted_nonpreemptibles


def schedule(experiment_config: dict,
             trial_instance_manager: TrialInstanceManager, pool):
    """Gets all pending trials for the current experiment and then schedules
    those that are possible."""
    logger.info('Finding trials to schedule.')

    # End expired trials
    end_expired_trials(experiment_config)

    # Start pending trials.
    experiment = experiment_config['experiment']
    pending_trials = list(get_pending_trials(experiment))
    preemptible = experiment_config.get('preemptible_runners')

    started_trials = start_trials(pending_trials,
                                  experiment_config,
                                  pool,
                                  preemptible=preemptible)
    if len(started_trials) != pending_trials:
        # Don't restart trials until we have started all trials for the first
        # time. This will prevent us from reaching the limit on preemptibles for
        # the experiment by restarting images and preventing others from getting
        # a chance to run at all.
        return

    restart_preempted_trials(trial_instance_manager, pool)


def schedule_loop(experiment_config: dict):
    """Continuously run the scheduler until there is nothing left to schedule.
    Note that this should not be called unless
    multiprocessing.set_start_method('spawn') was called first. Otherwise it
    will use fork to create the Pool which breaks logging."""
    # Create the thread pool once and reuse it to avoid leaking threads and
    # other issues.
    with multiprocessing.Pool() as pool:
        num_trials = len(get_experiment_trials(experiment_config['experiment']))
        trial_instance_manager = TrialInstanceManager(num_trials,
                                                      experiment_config)
        while trial_instance_manager.more_to_schedule():
            try:
                schedule(experiment_config, trial_instance_manager, pool)
            except Exception:  # pylint: disable=broad-except
                logger.error('Error occurred during scheduling.')

            # Either
            # - We had an unexpected exception OR
            # - We have not been able to start trials and still have some
            #   remaining. This can happen when we run out of instance quota.
            # In these cases, sleep before retrying again.
            time.sleep(FAIL_WAIT_SECONDS)

    logger.info('Finished scheduling.')


def update_started_trials(trial_proxies, trial_id_mapping):
    """Update started trials in |trial_id_mapping| with results from
    |trial_proxies| and save the updated trials."""
    # Map proxies back to trials and mark trials as started when proxies were
    # marked as such.
    started_trials = []
    for proxy in trial_proxies:
        if not proxy:
            continue
        trial = trial_id_mapping[proxy.id]
        trial.time_started = proxy.time_started
        started_trials.append(trial)
    if started_trials:
        db_utils.add_all(started_trials)
    return started_trials


def start_trials(trials, experiment_config: dict, pool, preemptible: bool):
    """Start all |trials| that are possible to start. Marks the ones that were
    started as started."""
    logger.info('Starting trials.')
    trial_id_mapping = {trial.id: trial for trial in trials}

    # Shuffle trials so that we don't create trials for the same fuzzer
    # benchmark close to one another. This *may* make the preemption rate more
    # evenly distributed across fuzzer benchmarks which will help if we don't
    # end up completing the target number of trials. A more rigourous approach
    # where we guarantee this may be useful.
    shuffled_trials = list(trial_id_mapping.values())
    random.shuffle(shuffled_trials)

    start_trial_args = [(TrialProxy(trial), experiment_config, preemptible)
                        for trial in shuffled_trials]
    started_trial_proxies = pool.starmap(_start_trial, start_trial_args)

    started_trials = update_started_trials(started_trial_proxies,
                                           trial_id_mapping)
    return started_trials


class TrialProxy:
    """A proxy object for a model.Trial. TrialProxy's allow these fields to be
    set and retreived without making any database calls."""

    def __init__(self, trial):
        self.id = trial.id  # pylint: disable=invalid-name
        self.fuzzer = trial.fuzzer
        self.benchmark = trial.benchmark
        self.time_started = trial.time_started
        self.time_ended = trial.time_ended


def _initialize_logs(experiment):
    """Initialize logs. This must be called on process start."""
    logs.initialize(default_extras={
        'experiment': experiment,
        'component': 'dispatcher'
    })


# Restarting preemptibles gives us another 24h (upto). It resets the counter.
# https://cloud.google.com/compute/docs/instances/preemptible#preemption_selection


def _start_trial(trial: TrialProxy, experiment_config: dict, preemptible: bool):
    """Start a trial if possible. Mark the trial as started if it was and then
    return the Trial. Otherwise return None."""
    # TODO(metzman): Add support for early exit (trial_creation_failed) that was
    # removed when this started using multiprocessing.
    # Also, support batched saves of trials (with a queue, like measurer uses)
    # so that measuring a schedule doesn't require waiting until the map call
    # that calls this function completely terminates.
    _initialize_logs(experiment_config['experiment'])
    logger.info('Start trial %d.', trial.id)
    started = create_trial_instance(trial.benchmark, trial.fuzzer, trial.id,
                                    experiment_config, preemptible)
    if started:
        trial.time_started = datetime_now()
        return trial
    logger.info('Trial: %d not started.', trial.id)
    return None


def render_startup_script_template(instance_name: str, benchmark: str,
                                   fuzzer: str, trial_id: int,
                                   experiment_config: dict):
    """Render the startup script using the template and the parameters
    provided and return the result."""
    fuzzer_config = fuzzer_config_utils.get_by_variant_name(fuzzer)
    docker_image_url = benchmark_utils.get_runner_image_url(
        benchmark, fuzzer, experiment_config['cloud_project'])
    fuzz_target = benchmark_utils.get_fuzz_target(benchmark)

    # Convert additional environment variables from configuration to arguments
    # that will be passed to docker.
    additional_env = ''
    if 'env' in fuzzer_config:
        additional_env = ' '.join([
            '-e {k}={v}'.format(k=k, v=shlex.quote(v))
            for k, v in fuzzer_config['env'].items()
        ])

    local_experiment = experiment_utils.is_local_experiment()
    template = JINJA_ENV.get_template('runner-startup-script-template.sh')
    kwargs = {
        'instance_name': instance_name,
        'benchmark': benchmark,
        'experiment': experiment_config['experiment'],
        'fuzzer': fuzzer,
        'trial_id': trial_id,
        'max_total_time': experiment_config['max_total_time'],
        'cloud_project': experiment_config['cloud_project'],
        'cloud_compute_zone': experiment_config['cloud_compute_zone'],
        'cloud_experiment_bucket': experiment_config['cloud_experiment_bucket'],
        'fuzz_target': fuzz_target,
        'docker_image_url': docker_image_url,
        'additional_env': additional_env,
        'local_experiment': local_experiment
    }
    if local_experiment:
        kwargs['host_gcloud_config'] = os.environ['HOST_GCLOUD_CONFIG']

    return template.render(**kwargs)


def create_trial_instance(fuzzer: str, benchmark: str, trial_id: int,
                          experiment_config: dict, preemptible: bool) -> bool:
    """Create or start a trial instance for a specific
    trial_id,fuzzer,benchmark."""
    instance_name = experiment_utils.get_trial_instance_name(
        experiment_config['experiment'], trial_id)
    startup_script = render_startup_script_template(instance_name, benchmark,
                                                    fuzzer, trial_id,
                                                    experiment_config)
    startup_script_path = '/tmp/%s-start-docker.sh' % instance_name
    with open(startup_script_path, 'w') as file_handle:
        file_handle.write(startup_script)

    return gcloud.create_instance(instance_name,
                                  gcloud.InstanceType.RUNNER,
                                  experiment_config,
                                  startup_script=startup_script_path,
                                  preemptible=preemptible)


def main():
    """Main function for running scheduler independently."""
    logs.initialize(default_extras={'component': 'dispatcher'})

    if len(sys.argv) != 2:
        print('Usage: {} <experiment_config.yaml>'.format(sys.argv[0]))
        return 1

    experiment_config = yaml_utils.read(sys.argv[1])
    schedule_loop(experiment_config)

    return 0


if __name__ == '__main__':
    sys.exit(main())
