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
import sys
import random
import time
from typing import List, Dict

import jinja2

from common import benchmark_utils
from common import experiment_utils
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

FAIL_WAIT_SECONDS = 10 * 60

logger = logs.Logger('scheduler')  # pylint: disable=invalid-name

RESOURCES_DIR = os.path.join(utils.ROOT_DIR, 'experiment', 'resources')

JINJA_ENV = jinja2.Environment(
    undefined=jinja2.StrictUndefined,
    loader=jinja2.FileSystemLoader(RESOURCES_DIR),
)

STARTED_TRIALS_FILTER = models.Trial.time_started.isnot(None)

NUM_RETRIES = 3
RETRY_WAIT_SECONDS = 3


def datetime_now() -> datetime.datetime:
    """Return datetime.datetime.utcnow(). This function is needed for
    mocking."""
    return datetime.datetime.now(
        datetime.timezone.utc).replace(tzinfo=datetime.timezone.utc)


# TODO(metzman): Figure out what are the best practices for the functions which
# must return sqlalchemy.orm.Query. Importing it just for annotation might be
# confusing to readers. There may also be weird situations where it is
# acceptable to use a list or query (because of duck typing) but type hints
# prevents us unless handled intelligently.
def get_nonpreempted_trials(experiment: str):
    """Returns a query of trials in |experiment|."""
    not_preempted_filter = models.Trial.preempted == False  # pylint: disable=singleton-comparison
    return get_experiment_trials(experiment).filter(not_preempted_filter)


def get_pending_trials(experiment: str):
    """Returns trial entities from |experiment| that have not run yet."""
    return get_nonpreempted_trials(experiment).filter(~STARTED_TRIALS_FILTER)


def get_running_trials(experiment: str):
    """Returns trial entities from |experiment| that have been marked started
    but not marked ended."""
    return get_nonpreempted_trials(experiment).filter(
        models.Trial.time_ended.is_(None), STARTED_TRIALS_FILTER)


def get_expired_trials(experiment: str, max_total_time: int):
    """Returns trial entities from |experiment| that have not ended and were
    started more than |max_total_time| + |GRACE_TIME_SECONDS| ago."""
    earliest_nonexpired_dt = datetime_now() - datetime.timedelta(
        seconds=max_total_time + GRACE_TIME_SECONDS)

    return get_nonpreempted_trials(experiment).filter(
        models.Trial.time_started <= earliest_nonexpired_dt).filter(
            models.Trial.time_ended.is_(None))


def all_trials_ended(experiment: str) -> bool:
    """Return a bool if there are any trials in |experiment| that have not
    started."""
    return not get_experiment_trials(experiment).filter(
        models.Trial.time_ended.is_(None)).all()


def delete_instances(instances, experiment_config):
    """Deletes |instances|."""
    cloud_project = experiment_config['cloud_project']
    cloud_compute_zone = experiment_config['cloud_compute_zone']
    instances_to_delete = [
        i for i in gce.get_instances(cloud_project, cloud_compute_zone)
        if i in instances
    ]
    return gcloud.delete_instances(instances_to_delete,
                                   experiment_config['cloud_compute_zone'])


def end_expired_trials(experiment_config: dict, core_allocation: dict):
    """Get all expired trials, end them and return them."""
    trials_past_expiry = get_expired_trials(experiment_config['experiment'],
                                            experiment_config['max_total_time'])
    expired_instances = []
    expired_trial_ids = []
    current_dt = datetime_now()
    for trial in trials_past_expiry:
        trial_id = trial.id
        expired_instances.append(
            experiment_utils.get_trial_instance_name(
                experiment_config['experiment'], trial_id))
        expired_trial_ids.append(trial_id)
        trial.time_ended = current_dt

    # Bail out here because trials_past_expiry will be truthy until evaluated.
    if not expired_instances:
        return

    if core_allocation is not None:
        for cpuset, trial_id in core_allocation.items():
            if trial_id in expired_trial_ids:
                core_allocation[cpuset] = None

    if not experiment_utils.is_local_experiment() and not delete_instances(
            expired_instances, experiment_config):
        # If we failed to delete some instances, then don't update the status
        # of expired trials in database as we don't know which instances were
        # successfully deleted. Wait for next iteration of end_expired_trials.
        logger.error('Failed to delete instances after trial expiry.')
        return

    db_utils.bulk_save(trials_past_expiry)


def get_experiment_trials(experiment: str):
    """Returns a query for trials in |experiment| ordered by id."""
    with db_utils.session_scope() as session:
        return session.query(models.Trial).filter(
            models.Trial.experiment == experiment).order_by(models.Trial.id)


def get_started_trials(experiment: str):
    """Returns a query for trials in |experiment| that have been started."""
    return get_experiment_trials(experiment).filter(STARTED_TRIALS_FILTER)


def get_last_trial_time_started(experiment: str):
    """Returns the time_started of the last trial that was started in
    |experiment|. This function cannot be called if there are any unstarted
    (e.g. pending trials). It will raise an assertion failure if there are any
    pending trials because it does not make sense to call this function before
    that time."""
    assert get_pending_trials(experiment).first() is None
    # Don't use get_experiment_trials because it already orders the results by
    # id.
    with db_utils.session_scope() as session:
        last_trial = session.query(models.Trial).filter(
            models.Trial.experiment == experiment,
            STARTED_TRIALS_FILTER).order_by(
                models.Trial.time_started.desc()).first()
        return last_trial.time_started


def any_pending_trials(experiment):
    """Returns True if there are any pending trials in |experiment|."""
    return bool(get_pending_trials(experiment).first())


def any_running_trials(experiment):
    """Returns True if there are any running trials in |experiment|."""
    return bool(get_running_trials(experiment).first())


class TrialInstanceManager:  # pylint: disable=too-many-instance-attributes
    """Manager for trial instances.
    Public methods of this are safe to call in preemptible and nonpreemptible
    experiments alike though the main purpose of this class is to manage
    preempted trials.
    This class object should be created at the start of scheduling and the
    handle_preempted_trials method should be called in the scheduling loop.
    See the docstring for handle_preempted_trials for how it works.
    """
    # Hard limit on the number of nonpreemptibles we will use. This bounds
    # costs.
    MAX_NONPREEMPTIBLES = 500

    # The maximum fraction of total trials in the experiment that can be done
    # using nonpreemptibles. This helps bound the cost in unexpected situations.
    NONPREEMPTIBLES_FRACTION = 1 / 10

    # How long can we keep trying preemptibles before we have to switch to a
    # nonpreemptibles or stopping the experiment.
    PREEMPTIBLE_WINDOW_MULTIPLIER = 1

    def __init__(self, num_trials, experiment_config):
        self.experiment_config = experiment_config
        self.num_trials = num_trials

        # Bound for the number of nonpreemptibles we can start if the experiment
        # specified preemptible_runners.
        self.max_nonpreemptibles = min(
            math.ceil(self.num_trials * self.NONPREEMPTIBLES_FRACTION),
            self.MAX_NONPREEMPTIBLES)
        logger.info('Max nonpreemptibles: %d.', self.max_nonpreemptibles)

        # Attributes for preemptible retry window. The preemptible retry window
        # is a time period that starts when the last initial trial is started.
        # It determines how long we can retry preempted trials using
        # preemptibles. This bounds the length of time an experiment lasts.
        self.preemptible_window = (experiment_config['max_total_time'] *
                                   self.PREEMPTIBLE_WINDOW_MULTIPLIER)
        self._initial_trials = list(
            get_experiment_trials(experiment_config['experiment']))
        self._max_time_started = None

        self.preempted_trials = {}
        self.preemptible_starts_futile = False

        # Filter operations happening before the experiment started.
        with db_utils.session_scope() as session:
            self.last_preemptible_query = (session.query(
                models.Experiment).filter(
                    models.Experiment.name == experiment_config['experiment']
                ).one().time_created.replace(tzinfo=datetime.timezone.utc))

    def _get_max_time_started(self):
        """Returns the last time_started of the self._initial_trials. Returns
        None if any initial trials haven't been started yet. This is needed so
        that the preemptible retry window starts from the end of the last
        initial trial to be started."""
        if self._max_time_started is not None:
            return self._max_time_started

        max_time_started = None
        for trial in self._initial_trials:
            time_started = trial.time_started
            if time_started is None:
                # An initial trial has never been started. Therefore the max
                # time started doesn't exist and the window hasn't started.
                return None

            if max_time_started is None:
                max_time_started = time_started
                continue

            max_time_started = max(time_started, max_time_started)

        assert max_time_started is not None
        max_time_started = max_time_started.replace(
            tzinfo=datetime.timezone.utc)
        self._max_time_started = max_time_started
        return max_time_started

    def preemptible_window_passed(self) -> bool:
        """Returns True if the preemptible window has passed."""
        max_time_started = self._get_max_time_started()
        if max_time_started is None:
            return False

        preemptible_window_end_time = max_time_started + datetime.timedelta(
            seconds=self.preemptible_window)

        return datetime_now() > preemptible_window_end_time

    def can_start_preemptible(self) -> bool:
        """Returns True if we can start a preemptible trial.
        |preemptible_starts| is the number of preemptibles we've already
        started."""
        if not self.experiment_config.get('preemptible_runners'):
            # This code shouldn't be executed in a non preemptible experiment.
            # But just in case it is, it's not OK to create a preemptible trial
            # in a non-preemptible experiment.
            return False

        if self.preemptible_window_passed():
            # Don't keep creating preemptible instances forever. Don't create
            # them if the experiment has already taken a certain amount of time
            # longer than the equivalent nonpreemptible experiment.
            # *NOTE*: preemptible_window_passed is slightly broken. When
            # the measurer uses this method it may produce slightly different
            # results than the scheduler because the initial trials may be
            # different. This is unlikely to happen in the real world. It is
            # probably benign as well because the measurer may think the window
            # end is slightly later than the scheduler. The effect of this will
            # simply be that the measurer may measure for slightly longer than
            # needed.
            return False

        # Otherwise, it's fine to create a preemptible instance.
        return True

    def can_start_nonpreemptible(self, nonpreemptible_starts: int) -> bool:
        """Returns True if we can start a nonpreemptible trial."""
        if not self.experiment_config.get('preemptible_runners'):
            # This code shouldn't be executed in a preemptible experiment.
            # But just in case it is, it's not always OK to a non-preemptible
            # trial in a non-preemptible experiment.
            return True

        if nonpreemptible_starts >= self.max_nonpreemptibles:
            # Don't exceed the maximum number of nonpreemptibles.
            return False

        # Supplement with nonpreemptibles if the experiment results are not so
        # messed up that doing so won't make the result useable.
        return True

    def get_nonpreemptible_starts(self) -> int:
        """Returns the count of nonpreemptible trials that have been started."""
        return get_started_trials(self.experiment_config['experiment']).filter(
            models.Trial.preemptible.is_(False)).count()

    def _get_preempted_replacements(self,
                                    preempted_trials) -> List[models.Trial]:
        """Returns a list containing a replacement trial for each trial that can
        be replaced in |preempted_trials|."""
        replacements = []
        nonpreemptible_starts = self.get_nonpreemptible_starts()

        # The time_ended won't be 100% accurate but that doesn't matter.
        time_ended = datetime_now()

        for trial in preempted_trials:
            # Update the preempted trial.
            trial.preempted = True
            trial.time_ended = time_ended

            # We try to start each replacement trial as a preemptible before
            # trying nonpreemptible to minimize cost.
            if self.can_start_preemptible():
                # See if we can replace with a preemptible.
                replacements.append(replace_trial(trial, preemptible=True))
                continue

            if self.can_start_nonpreemptible(nonpreemptible_starts):
                # If a trial can't be replaced with a preemptible see if we can
                # replace it with a nonpreemptible.
                nonpreemptible_starts += 1
                replacements.append(replace_trial(trial, preemptible=False))
                continue

        return replacements

    def _get_started_unfinished_instances(self) -> Dict[str, models.Trial]:
        """Returns a dictionary of instance names to trials for trials were
        started but not finished according to the database."""
        experiment = self.experiment_config['experiment']
        running_trials = get_running_trials(experiment)
        return {
            experiment_utils.get_trial_instance_name(experiment, trial.id):
            trial for trial in running_trials
        }

    def get_preempted_trials(self) -> List[models.Trial]:
        """Returns a list of trials that were preempted."""
        if not self.experiment_config.get('preemptible_runners'):
            # No preempted trials in a nonpreemptible experiment.
            assert not self.preempted_trials
            return []

        started_instances = self._get_started_unfinished_instances()
        query_time = datetime_now()

        preempted_instances = self._get_preempted_instances_with_retries()
        trials = []
        for instance in preempted_instances:
            trial = started_instances.get(instance)
            if trial is None:
                # Preemption for this trial was probably handled already.
                logs.warning('Instance: %s is preempted but is not running.',
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
        # redundant work).
        self.last_preemptible_query = query_time

        # Return all preempted instances, those we knew from beforehand and
        # those we discovered in the query.
        return trials

    @retry.wrap(NUM_RETRIES, RETRY_WAIT_SECONDS,
                'experiment.scheduler.TrialInstanceManager.'
                '_get_preempted_instances_with_retries')
    def _get_preempted_instances_with_retries(self):
        project = self.experiment_config['cloud_project']
        zone = self.experiment_config['cloud_compute_zone']
        return list(gce.get_preempted_instances(project, zone))

    def handle_preempted_trials(self):
        """Handle preempted trials by marking them as preempted and creating
        replacement trials when appropriate.
        This is the algorithm used by handle_preempted_trials:

        1. Query the GCE API to find trials that were preempted since our last
        query (or the start of the experiment on our first query.

        2. For every preempted trial, ensure that it was not handled before and
        if it wasn't then mark the trials as finished and preempted and create
        replacement trials if appropriate.

        This is how it is determined whether a preempted trial should be
        replaced and what it should be replaced with:

        1. First we see if we can replace it with a preemptible instance. We
        will replace it with a preemptible instance if:

          a. We haven't created more than double the number of preemptible trial
          instances than the number of trial this experiment would take if it
          were using non-preemptibles ("target_trials") . This bounds the cost
          of our preemptible usage to <2X cost of using preemptibles naively
          If preemptibles are 20% cost of non-preemptibles, then <40% the cost
          of a non-preemptible experiment.

          b. We haven't spent longer than 3X the duration of time the
          experiment would take if using nonpreemptibles. This bounds the
          duration of the experiment to 4X the length of the nonpreemptible
          experiment.

        2. If we can't create a preemptible replacement, we replace it with a
        nonpreemptible if:

          a. We haven't created more than target_trials/20 nonpreemptibles
          already. This bounds the cost of the nonpreemptibles to 5% of the cost
          of a 100% nonpreemptible experiment.

          b. (TODO): Using preemptibles will actually help the results of this
          experiment. If we can't create any preemptible instances but we need
          to replace target_trials number of instances, replacing the tiny
          fraction of them with preemptibles will give you a 5% complete
          experiment. This is a hard issue to solve, because we restart
          trials as they are preempted so we may not determine it is futile to
          use nonpreemptibles until the last nonpreemptible above our limit is
          reached.

        3. TODO: There are other cases where we probably shouldn't replace
        trials that we haven't implemented, but would like to such as:

          a. If a trial is preempted very close to the end of its budgeted time.
          In that case it's probably fine if the comparison on the benchmark
          happens at 22:45 instead of 23:00.

          b. If a trial is the only trial for the fuzzer-benchmark that was
          preempted. In that case, not replacing the trial will save time and
          not hurt results much.

        The impact of this algorithm is that:

        1. The cost of a preemptible experiment, in the worst case scenario is
        45% of a nonpreemptible experiment. On average we find they will be
        ~30% the cost of a nonpreemptible experiment.

        2. Time of an experiment will be 4X the length of a nonpreemptible
        experiment in the worst case scenario. This is fine however because most
        of the experiment will finish earlier, only a few trials that won't
        change results very much will trickle in at the end.

        3. Experiments are guaranteed to terminate but results won't necessarily
        be complete if the preemption rate is pathologically high. This is
        acceptable because a human should intervene in these edge cases.
        """
        logger.info('Handling preempted.')
        if not self.experiment_config.get('preemptible_runners'):
            # Nothing to do here if not a preemptible experiment.
            return []

        preempted_trials = self.get_preempted_trials()
        if not preempted_trials:
            logs.info('No preempteds to handle.')
            return []

        replacements = self._get_preempted_replacements(preempted_trials)
        experiment = self.experiment_config['experiment']
        instances = [
            experiment_utils.get_trial_instance_name(experiment, trial.id)
            for trial in preempted_trials
        ]

        logs.info('Deleting preempted instances: %s', instances)
        if not delete_instances(instances, self.experiment_config):
            logs.error('Could not delete preempted instances: %s', instances)

        db_utils.add_all(preempted_trials + replacements)
        logger.info('Done handling preempted.')
        return replacements


def replace_trial(trial, preemptible):
    """Returns a new trial to replace |trial|. The trial is preemptible if
    |preemptible|. Sets trial.replacement to the replacement trial."""
    replacement = models.Trial(fuzzer=trial.fuzzer,
                               benchmark=trial.benchmark,
                               experiment=trial.experiment,
                               preemptible=preemptible)
    trial.replacement = replacement.id
    return replacement


def schedule(experiment_config: dict, pool, core_allocation=None):
    """Gets all pending trials for the current experiment and then schedules
    those that are possible."""
    logger.info('Finding trials to schedule.')

    # End expired trials
    end_expired_trials(experiment_config, core_allocation)

    # Start pending trials.
    pending_trials = list(get_pending_trials(experiment_config['experiment']))
    started_trials = start_trials(pending_trials, experiment_config, pool,
                                  core_allocation)
    return started_trials


def schedule_loop(experiment_config: dict):
    """Continuously run the scheduler until there is nothing left to schedule.
    Note that this should not be called unless
    multiprocessing.set_start_method('spawn') was called first. Otherwise it
    will use fork to create the Pool which breaks logging."""
    # Create the thread pool once and reuse it to avoid leaking threads and
    # other issues.
    logger.info('Starting scheduler.')
    num_trials = len(
        get_experiment_trials(experiment_config['experiment']).all())
    local_experiment = experiment_utils.is_local_experiment()
    pool_args = ()
    core_allocation = None
    runners_cpus = experiment_config['runners_cpus']
    if runners_cpus is not None:
        if local_experiment:
            runner_num_cpu_cores = experiment_config['runner_num_cpu_cores']
            processes = runners_cpus // runner_num_cpu_cores
            logger.info('Scheduling runners from core 0 to %d.' %
                        (runner_num_cpu_cores * processes - 1))
            core_allocation = {}
            for cpu in range(0, runner_num_cpu_cores * processes,
                             runner_num_cpu_cores):
                core_allocation['%d-%d' %
                                (cpu, cpu + runner_num_cpu_cores - 1)] = None
            pool_args = (processes,)
        else:
            pool_args = (runners_cpus,)

    if not local_experiment:
        gce.initialize()
        trial_instance_manager = TrialInstanceManager(num_trials,
                                                      experiment_config)

    experiment = experiment_config['experiment']
    with multiprocessing.Pool(*pool_args) as pool:
        handle_preempted = False
        while not all_trials_ended(experiment):
            try:
                if (not local_experiment and not handle_preempted and
                        not any_pending_trials(experiment)):
                    # This ensures that:
                    # 1. handle_preempted will not becomes True when running
                    #    locally.
                    # 2. Only start handling preempted instances once every
                    #    initial trial was started.
                    handle_preempted = True

                schedule(experiment_config, pool, core_allocation)
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


def update_started_trials(trial_proxies, trial_id_mapping, core_allocation):
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

        if core_allocation is not None:
            core_allocation[proxy.cpuset] = proxy.id

        started_trials.append(trial)
    if started_trials:
        db_utils.add_all(started_trials)
    return started_trials


def start_trials(trials, experiment_config: dict, pool, core_allocation=None):
    """Start all |trials| that are possible to start. Marks the ones that were
    started as started."""
    logger.info('Starting trials.')
    trial_id_mapping = {trial.id: trial for trial in trials}

    # Shuffle trials so that we don't create trials for the same fuzzer
    # benchmark close to one another. This *may* make the preemption rate more
    # evenly distributed across fuzzer benchmarks which will help if we don't
    # end up completing the target number of trials. A more rigourous approach
    # where we increase the distance in between trials for the same
    # fuzzer-benchmark might be useful.
    shuffled_trials = list(trial_id_mapping.values())
    random.shuffle(shuffled_trials)

    free_cpusets = [
        cpuset for cpuset, trial_id in core_allocation.items()
        if trial_id is None
    ] if core_allocation is not None else None

    start_trial_args = []
    for index, trial in enumerate(shuffled_trials):
        if free_cpusets is not None and index >= len(free_cpusets):
            break

        start_trial_args += [
            (TrialProxy(trial), experiment_config,
             free_cpusets[index] if free_cpusets is not None else None)
        ]

    started_trial_proxies = pool.starmap(_start_trial, start_trial_args)
    started_trials = update_started_trials(started_trial_proxies,
                                           trial_id_mapping, core_allocation)
    logger.info(f'Started {len(started_trials)} trials.')
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
        self.cpuset = None


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


def _start_trial(trial: TrialProxy, experiment_config: dict, cpuset=None):
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
                                    experiment_config, trial.preemptible,
                                    cpuset)
    if started:
        trial.time_started = datetime_now()
        trial.cpuset = cpuset
        return trial
    logger.info('Trial: %d not started.', trial.id)
    return None


def render_startup_script_template(  # pylint: disable=too-many-arguments
        instance_name: str,
        fuzzer: str,
        benchmark: str,
        trial_id: int,
        experiment_config: dict,
        cpuset=None):
    """Render the startup script using the template and the parameters
    provided and return the result."""
    experiment = experiment_config['experiment']
    docker_image_url = benchmark_utils.get_runner_image_url(
        experiment, benchmark, fuzzer, experiment_config['docker_registry'])
    fuzz_target = benchmark_utils.get_fuzz_target(benchmark)

    local_experiment = experiment_utils.is_local_experiment()
    template = JINJA_ENV.get_template('runner-startup-script-template.sh')
    kwargs = {
        'instance_name': instance_name,
        'benchmark': benchmark,
        'experiment': experiment,
        'fuzzer': fuzzer,
        'trial_id': trial_id,
        'max_total_time': experiment_config['max_total_time'],
        'snapshot_period': experiment_config['snapshot_period'],
        'experiment_filestore': experiment_config['experiment_filestore'],
        'report_filestore': experiment_config['report_filestore'],
        'fuzz_target': fuzz_target,
        'docker_image_url': docker_image_url,
        'docker_registry': experiment_config['docker_registry'],
        'local_experiment': local_experiment,
        'no_seeds': experiment_config['no_seeds'],
        'no_dictionaries': experiment_config['no_dictionaries'],
        'oss_fuzz_corpus': experiment_config['oss_fuzz_corpus'],
        'num_cpu_cores': experiment_config['runner_num_cpu_cores'],
        'cpuset': cpuset,
        'custom_seed_corpus_dir': experiment_config['custom_seed_corpus_dir'],
    }

    if not local_experiment:
        kwargs['cloud_compute_zone'] = experiment_config['cloud_compute_zone']
        kwargs['cloud_project'] = experiment_config['cloud_project']

    return template.render(**kwargs)


def create_trial_instance(  # pylint: disable=too-many-arguments
        fuzzer: str,
        benchmark: str,
        trial_id: int,
        experiment_config: dict,
        preemptible: bool,
        cpuset=None) -> bool:
    """Create or start a trial instance for a specific
    trial_id,fuzzer,benchmark."""
    instance_name = experiment_utils.get_trial_instance_name(
        experiment_config['experiment'], trial_id)
    startup_script = render_startup_script_template(instance_name, fuzzer,
                                                    benchmark, trial_id,
                                                    experiment_config, cpuset)
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
        'component': 'dispatcher',
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
