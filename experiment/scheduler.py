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
import pytz

from common import benchmark_utils
from common import experiment_utils
from common import fuzzer_config_utils
from common import gcloud
from common import gce
from common import logs
from common import retry
from common import utils
from common import yaml_utils
from database import models
from database import utils as db_utils

# Give the trial runner a little extra time to shut down and account for how
# long it can take to actually start running once an instance is started. 5
# minutes is an arbitrary amount of time.
GRACE_TIME_SECONDS = 5 * 60

FAIL_WAIT_SECONDS = 2 * 60  # !!!

logger = logs.Logger('scheduler')  # pylint: disable=invalid-name

RESOURCES_DIR = os.path.join(utils.ROOT_DIR, 'experiment', 'resources')

JINJA_ENV = jinja2.Environment(
    undefined=jinja2.StrictUndefined,
    loader=jinja2.FileSystemLoader(RESOURCES_DIR),
)

STARTED_TRIALS_FILTER = models.Trial.time_started.isnot(None)


def datetime_now() -> datetime.datetime:
    """Return datetime.datetime.utcnow(). This function is needed for
    mocking."""
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=pytz.UTC)


# TODO(metzman): Figure out what are the best practices for the functions which
# must return sqlalchemy.orm.Query. Importing it just for annotation might be
# confusing to readers. There may also be weird situations where it is
# acceptable to use a list or query (because of duck typing) but type hints
# prevents us unless handled intelligently.
def get_experiment_trials(experiment: str):
    """Returns a query of trials in |experiment|."""
    not_preempted_filter = models.Trial.preempted == False  # pylint: disable=singleton-comparison
    return _get_all_experiment_trials(experiment).filter(not_preempted_filter)


def get_pending_trials(experiment: str):
    """Returns trial entities from |experiment| that have not run yet."""
    return get_experiment_trials(experiment).filter(~STARTED_TRIALS_FILTER)


def get_running_trials(experiment: str):
    """Returns trial entities from |experiment| that have been marked started
    but not marked ended."""
    return get_experiment_trials(experiment).filter(
        models.Trial.time_ended.is_(None), STARTED_TRIALS_FILTER)


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


def delete_instances(instances, experiment_config):
    # Delete instances for expired trials.
    running_instances = gcloud.list_instances()
    instances_to_delete = [i for i in instances if i in running_instances]
    return gcloud.delete_instances(instances_to_delete,
                                   experiment_config['cloud_compute_zone'])


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

    if delete_instances(expired_instances, experiment_config):

        # If we failed to delete some instances, then don't update the status
        # of expired trials in database as we don't know which instances were
        # successfully deleted. Wait for next iteration of end_expired_trials.
        logger.error('Failed to delete instances after trial expiry.')
        return

    db_utils.bulk_save(trials_past_expiry)


def _get_all_experiment_trials(experiment: str):
    return db_utils.query(models.Trial).filter(
        models.Trial.experiment == experiment).order_by(models.Trial.id)


def _get_all_started_trials(experiment: str):
    return _get_all_experiment_trials(experiment).filter(STARTED_TRIALS_FILTER)


def get_last_trial_time_started(experiment: str):
    """Returns the time_started of the last trial that was started in
    |experiment|. This function cannot be called if there are any unstarted
    (e.g. pending trials). It will raise an assertion failure if there are any
    pending trials because it does not make sense to call this function before
    that time."""
    assert get_pending_trials(experiment).first() is None
    # Don't use get_experiment_trials because it already orders the results by
    # id.
    last_trial = db_utils.query(models.Trial).filter(
        models.Trial.experiment == experiment, STARTED_TRIALS_FILTER).order_by(
            models.Trial.time_started.desc()).first()
    return last_trial.time_started


def any_pending_trials(experiment):
    """Returns True if there are any pending trials."""
    return bool(get_pending_trials(experiment).first())


def any_running_trials(experiment):
    """Returns True if there are any running trials."""
    return bool(get_running_trials(experiment).first())


class TrialInstanceManager:  # pylint: disable=too-many-instance-attributes
    """Manager for trial instances."""

    # Hard limit on the number of nonpreemptibles we will use. This bounds
    # costs.
    MAX_NONPREEMPTIBLES = 500
    # The maximum fraction of total trials in the experiment that can be done
    # using preemptibles. This helps bound the cost in unexpected situations.
    NONPREEMPTIBLES_FRACTION = 1 / 20
    MAX_FRACTION_FOR_NONPREEMPTIBLES = 1 / 4

    def __init__(self, num_trials, experiment_config):
        self.experiment_config = experiment_config
        self.num_trials = num_trials
        self.max_nonpreemptibles = min(
            math.ceil(self.num_trials * self.NONPREEMPTIBLES_FRACTION),
            self.MAX_NONPREEMPTIBLES)
        logger.info('Max nonpreemptibles: %d.', self.max_nonpreemptibles)
        self.max_preemptibles = self.num_trials * 2
        self.preemptible_window = 3 * experiment_config['max_total_time']
        self.preempted_trials = {}
        self._first_time_handling_preempted = None

        # !!! REGEX
        self.base_resource_url = (
            'https://www.googleapis.com/compute/v1/projects/{project}/zones/'
            '{zone}/instances/').format(
                project=experiment_config['cloud_project'],
                zone=experiment_config['cloud_compute_zone'])

        experiment = experiment_config['experiment']
        # Filter operations happening before the experiment started.
        self.last_preemptible_query = (db_utils.query(models.Experiment).filter(
            models.Experiment.name == experiment).one().time_created.replace(
                tzinfo=pytz.UTC))

    def get_time_handling_preempted(self):
        """Get the time since the last trial in the experiment started."""
        if self._first_time_handling_preempted is None:
            return 0
        # If we cached the last time started, use the cached value to
        # compute the elapsed time.
        return (datetime.datetime.utcnow() -
                self._first_time_handling_preempted)

    def can_start_preemptible(self, preemptible_starts):
        """Returns True if we can start a preemptible trial."""
        if not self.experiment_config.get('preemptible_runners'):
            return False

        if preemptible_starts > self.max_preemptibles:
            # Don't create more than the maximum number of preemptibles or else
            # costs can be infinite in the (highly unlikely) worst case
            # scenario.
            return False

        # if self.get_time_handling_preempted() > self.preemptible_window:
        #     # Don't keep creating preemptibles forever. Stop creating them after
        #     # a certain time period so that we can switch to nonpreemptibles or
        #     # terminate the experiment and let the user deal with the issue if
        #     # we can't run this experiment in a reasonable amount of time.
        #     return False

        # Otherwise, it's fine to create a preemptible instance.
        return True

    def get_preemptible_starts(self) -> int:
        """Returns the count of preemptible trials that have been started."""
        return _get_all_started_trials(
            self.experiment_config['experiment']).filter(
                models.Trial.preemptible == True).count()  # pylint: disable=singleton-comparison

    def get_nonpreemptible_starts(self) -> int:
        """Returns the count of nonpreemptible trials that have been started."""
        return _get_all_started_trials(
            self.experiment_config['experiment']).filter(
                models.Trial.preemptible == False).count()  # pylint: disable=singleton-comparison

    def can_start_nonpreemptible(self,
                                 nonpreemptible_starts,
                                 num_trials_to_run=None):
        """Returns True if we can start a nonpreemptible trial."""
        if not self.experiment_config.get('preemptible_runners'):
            return True

        if nonpreemptible_starts >= self.max_nonpreemptibles:
            # Don't exceed our maximum preemptibles.
            return False

        if num_trials_to_run is None:
            return True

        if (num_trials_to_run * self.MAX_FRACTION_FOR_NONPREEMPTIBLES >
                self.max_nonpreemptibles):
            # When we have trials left that can't be run on preemptibles, don't
            # naively allow nonpreemptible creation until we hit the limit.
            # Instead if we can't create enough nonpreemptibles to replace at
            # least 1/4 of the remaining trials, don't create nonpreemptibles at
            # all, the experiment can't be salvaged cheaply.
            return False

        # Supplement with nonpreemptibles if the experiment results are not so
        # messed up that doing so won't make the result useable.
        return True

    def _handle_preempted(self, trials):
        """Returns a tuple containing the list of trials that can be started on
        preemptibles and trials that can be started on nonpreemptibles."""
        replacements = []
        preemptible_starts = self.get_preemptible_starts()
        nonpreemptible_starts = self.get_nonpreemptible_starts()

        # This won't be 100% accurate but that doens't really matter.
        time_ended = datetime_now()
        num_to_restart = len(trials)
        for trial in trials:
            # Update the preempted trial.
            trial.preempted = True
            trial.time_ended = time_ended

            # Note that we must try to start each replacement trial as a
            # preemptible before trying nonpreemptible to minimize cost.
            if self.can_start_preemptible(preemptible_starts):
                # See if we can restart it as a preemptible.
                preemptible_starts += 1
                num_to_restart -= 1
                replacements.append(replace_trial(trial, True))
                continue

            if self.can_start_nonpreemptible(nonpreemptible_starts,
                                             num_to_restart):
                # If a trial can't be replaced with a preemptible see if we can
                # replace it with a nonpreemptible.
                nonpreemptible_starts += 1
                num_to_restart -= 1
                replacements.append(replace_trial(trial, False))
                continue

        return trials, replacements

    def _get_started_unfinished_instances(self):
        """Returns a dictionary of instance names to trials for trials were
        started but not finished according to the database."""
        experiment = self.experiment_config['experiment']
        running_trials = get_running_trials(experiment)
        return {
            experiment_utils.get_trial_instance_name(experiment, trial.id):
            trial for trial in running_trials
        }

    def _get_instance_from_preemption_operation(self, operation):
        """Returns the instance name from a preemption |operation|."""
        return operation['targetLink'][len(self.base_resource_url):]

    def get_preempted_trials(self):
        """Returns a list of preempted trials."""
        if not self.experiment_config.get('preemptible_runners'):
            # No preempted trials in a nonpreemptible experiment.
            assert not self.preempted_trials
            return []

        started_instances = self._get_started_unfinished_instances()
        query_time = datetime_now()

        preempted_instances = list(self._query_preempted_instances())
        trials = []
        for instance in preempted_instances:
            trial = started_instances.get(instance)
            if trial is None:
                # Preemption for this trial was probably handled already.
                logs.warning(
                    'instance: %s is preempted but is not running.',
                    instance)
                continue
            if trial.id in self.preempted_trials:
                # We already know this instance was preempted.
                continue
            self.preempted_trials[trial.id] = trial
            trials.append(trial)

        # Update this now when we know that we have succeded processing the
        # query. It's far worse if we update the query too early than if we
        # don't update the query at this point (which will only result in
        # redundant work.
        self.last_preemptible_query = query_time

        # Return all preempted instances, those we knew from before hand and
        # those we discovered in the query.
        return trials

    @retry.wrap(
        3, 2,
        'experiment.scheduler.TrialInstanceManager._query_preempted_instances')
    def _query_preempted_instances(self):
        project = self.experiment_config['cloud_project']
        zone = self.experiment_config['cloud_compute_zone']
        operations = gce.filter_by_end_time(self.last_preemptible_query,
                                            gce.get_operations(project, zone))
        instances = []
        for operation in gce.get_preemption_operations(operations):
            if operation is None:
                logs.error('Operation is None.')
                continue
            instances.append(
                self._get_instance_from_preemption_operation(operation))
        return instances

    def handle_preempted_trials(self):
        """Mark preempted trials as such in the db and add replacement trials to
        the db."""
        logger.info('Handling preempted.')
        if not self.experiment_config.get('preemptible_runners'):
            # Nothing to do here if not a preemptible experiment.
            return []

        if self._first_time_handling_preempted is None:
            self._first_time_handling_preempted = datetime_now()

        preempted_trials = self.get_preempted_trials()

        preempted_trials, replacements = self._handle_preempted(
            preempted_trials)

        experiment = self.experiment_config['experiment']
        instances = [
            experiment_utils.get_trial_instance_name(experiment, trial.id)
            for trial in preempted_trials
        ]
        logs.info('Deleting preempted instances: %s', instances)
        if instances and not delete_instances(instances,
                                              self.experiment_config):
            logs.error('Could not delete preempted instances: %s', instances)

        db_utils.add_all(preempted_trials + replacements)
        logger.info('Done handling preempted.')
        return replacements

    def more_to_schedule(self):
        """Returns True if there is nothping left to schedule."""
        experiment = self.experiment_config['experiment']
        if all_trials_ended(experiment):
            return False

        if any_running_trials(experiment):
            # If there are any running trials, they will need to be
            # scheduled/shutdown.
            return True

        if not any_pending_trials(experiment):
            return False

        if not self.experiment_config.get('preemptible_runners'):
            # There are more trials to run. In non-preemptible experiments, this
            # means we must continue scheduling.
            return True

        # In preemptible experiments, we only need to continue scheduling if we
        # can start more trials.
        preemptible_starts = self.get_preemptible_starts()
        if self.can_start_preemptible(preemptible_starts):
            return True

        nonpreemptible_starts = self.get_nonpreemptible_starts()
        return self.can_start_nonpreemptible(nonpreemptible_starts)


def replace_trial(trial, preemptible):
    """Returns a new trial to replace |trial|. The trial is preemptible if
    |preemptible|. Sets trial.replacement to the replacement trial."""
    replacement = models.Trial(fuzzer=trial.fuzzer,
                               benchmark=trial.benchmark,
                               experiment=trial.experiment,
                               preemptible=preemptible)
    trial.replacement = replacement.id
    return replacement


def schedule(experiment_config: dict, pool):
    """Gets all pending trials for the current experiment and then schedules
    those that are possible."""
    logger.info('Finding trials to schedule.')

    # End expired trials
    end_expired_trials(experiment_config)

    # Start pending trials.
    pending_trials = list(get_pending_trials(experiment_config['experiment']))
    started_trials = start_trials(pending_trials, experiment_config, pool)
    return started_trials


def schedule_loop(experiment_config: dict):
    """Continuously run the scheduler until there is nothing left to schedule.
    Note that this should not be called unless
    multiprocessing.set_start_method('spawn') was called first. Otherwise it
    will use fork to create the Pool which breaks logging."""
    # Create the thread pool once and reuse it to avoid leaking threads and
    # other issues.
    logger.info('Starting scheduler')
    num_trials = len(
        get_experiment_trials(experiment_config['experiment']).all())
    trial_instance_manager = TrialInstanceManager(num_trials, experiment_config)
    experiment = experiment_config['experiment']
    with multiprocessing.Pool() as pool:
        handle_preempted = False
        while trial_instance_manager.more_to_schedule():
            try:

                if not handle_preempted and not any_pending_trials(experiment):
                    # Only start handling preempted instances once every initial
                    # trial runs once.
                    handle_preempted = True

                schedule(experiment_config, pool)
                if handle_preempted:
                    trial_instance_manager.handle_preempted_trials()
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


def start_trials(trials, experiment_config: dict, pool):
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

    start_trial_args = [
        (TrialProxy(trial), experiment_config) for trial in shuffled_trials
    ]
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
        self.preemptible = trial.preemptible


def _initialize_logs(experiment):
    """Initialize logs. This must be called on process start."""
    logs.initialize(
        default_extras={
            'experiment': experiment,
            'component': 'dispatcher',
            'subcomponent': 'scheduler'
        })


# Restarting preemptibles gives us another 24h (upto). It resets the counter.
# https://cloud.google.com/compute/docs/instances/preemptible#preemption_selection


def _start_trial(trial: TrialProxy, experiment_config: dict):
    """Start a trial if possible. Mark the trial as started if it was and then
    return the Trial. Otherwise return None."""
    # TODO(metzman): Add support for early exit (trial_creation_failed) that was
    # removed when this started using multiprocessing.
    # Also, support batched saves of trials (with a queue, like measurer uses)
    # so that measuring a schedule doesn't require waiting until the map call
    # that calls this function completely terminates.
    _initialize_logs(experiment_config['experiment'])
    logger.info('Start trial %d.', trial.id)
    started = create_trial_instance(trial.fuzzer, trial.benchmark, trial.id,
                                    experiment_config, trial.preemptible)
    if started:
        trial.time_started = datetime_now()
        return trial
    logger.info('Trial: %d not started.', trial.id)
    return None


def render_startup_script_template(instance_name: str, fuzzer: str,
                                   benchmark: str, trial_id: int,
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
    startup_script = render_startup_script_template(instance_name, fuzzer,
                                                    benchmark, trial_id,
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
    logs.initialize(default_extras={
        'component': 'local', #!!!
        'subcomponent': 'scheduler'
    })

    if len(sys.argv) != 2:
        print('Usage: {} <experiment_config.yaml>'.format(sys.argv[0]))
        return 1

    experiment_config = yaml_utils.read(sys.argv[1])
    schedule_loop(experiment_config)

    return 0


if __name__ == '__main__':
    sys.exit(main())
