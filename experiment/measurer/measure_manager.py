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
# limitations under the License. for now
"""Module for managing measurement of snapshots from trial runners."""
import collections
import multiprocessing
import pathlib
import sys
import time
from typing import List

from sqlalchemy import func
from sqlalchemy import orm
import rq.job

from common import experiment_path as exp_path
from common import experiment_utils
from common import filestore_utils
from common import logs
from common import yaml_utils
from database import utils as db_utils
from database import models
from experiment.measurer import measure_worker
from experiment import scheduler
from experiment import schedule_measure_workers

logger = logs.Logger('measure_manager')  # pylint: disable=invalid-name

FAIL_WAIT_SECONDS = 30
POLL_RESULTS_WAIT_SECONDS = 5
SNAPSHOTS_BATCH_SAVE_SIZE = 50


def get_experiment_folders_dir():
    """Return experiment folders directory."""
    return exp_path.path('experiment-folders')


def exists_in_experiment_filestore(path: pathlib.Path) -> bool:
    """Returns True if |path| exists in the experiment_filestore."""
    return filestore_utils.ls(exp_path.gcs(path), must_exist=False).retcode == 0


def measure_loop(experiment_config: dict):
    """Continuously measure trials for |experiment|."""
    db_utils.initialize()
    experiment = experiment_config['experiment']
    initialize_logs(experiment)
    queue = schedule_measure_workers.initialize(experiment_config)
    while True:
        try:
            # Get whether all trials have ended before we measure to prevent
            # races.
            all_trials_ended = scheduler.all_trials_ended(experiment)
            if not measure_all_trials(experiment_config, queue):
                # We didn't measure any trials.
                if all_trials_ended:
                    # There are no trials producing snapshots to measure.
                    # Given that we couldn't measure any snapshots, we won't
                    # be able to measure any the future, so stop now.
                    break
        except Exception:  # pylint: disable=broad-except
            logger.error('Error occurred during measuring.')

            time.sleep(FAIL_WAIT_SECONDS)

    schedule_measure_workers.teardown(experiment_config)
    logger.info('Finished measuring.')


def get_job_timeout():
    """Returns the timeout for an rq job."""
    return experiment_utils.get_snapshot_seconds() + 2 * 60


def enqueue_measure_jobs_for_unmeasured(experiment_config: dict, queue):
    """Get snapshots we need to measure from the db and add them to the queue so
    that they can be measured."""
    experiment = experiment_config['experiment']
    max_total_time = experiment_config['max_total_time']
    max_cycle = _time_to_cycle(max_total_time)
    logger.info('Enqueuing measure jobs.')
    unmeasured_snapshots = get_unmeasured_snapshots(experiment, max_cycle)
    jobs = enqueue_measure_jobs(unmeasured_snapshots, queue)
    logger.info('Done enqueuing jobs.')
    return jobs


def enqueue_measure_jobs(unmeasured_snapshots, queue):
    """Add jobs to measure each snapshot in |unmeasured_snapshots| to |queue|
    and returns them."""
    job_timeout = get_job_timeout()
    jobs = [
        queue.enqueue(measure_worker.measure_trial_coverage,
                      unmeasured_snapshot,
                      job_timeout=job_timeout,
                      result_ttl=job_timeout,
                      ttl=job_timeout)
        for unmeasured_snapshot in unmeasured_snapshots
    ]
    return jobs


def enqueue_next_measure_job(unmeasured_snapshot, experiment_config, queue):
    """Adds a job to measure the next snapshot after |unmeasured_snapshot| to
    |queue| and returns the job."""
    if _time_to_cycle(
            experiment_config['max_total_time']) == unmeasured_snapshot.cycle:
        return None
    next_unmeasured_snapshot = measure_worker.SnapshotMeasureRequest(
        unmeasured_snapshot.fuzzer, unmeasured_snapshot.benchmark,
        unmeasured_snapshot.trial_id, unmeasured_snapshot.cycle + 1)
    job = enqueue_measure_jobs([next_unmeasured_snapshot], queue)[0]
    return job


def ready_to_measure():
    """Returns True if we are ready to start measuring."""
    experiment_folders_dir = get_experiment_folders_dir()
    return exists_in_experiment_filestore(experiment_folders_dir)


def measure_all_trials(experiment_config: dict, queue) -> bool:  # pylint: disable=too-many-branches,too-many-statements
    """Get coverage data (with coverage runs) for all active trials. Note that
    this should not be called unless multiprocessing.set_start_method('spawn')
    was called first. Otherwise it will use fork which breaks logging."""
    logger.info('Measuring all trials.')

    if not ready_to_measure():
        return True

    jobs = enqueue_measure_jobs_for_unmeasured(experiment_config, queue)
    if not jobs:
        # If we didn't enqueue any jobs, then there is nothing to measure.
        return False

    initial_jobs = {job.id: job for job in jobs}

    # TODO(metzman): Move this to scheduler or it's own process. It's here for
    # now because the scheduler quits too early.
    schedule_measure_workers.schedule(experiment_config, queue)

    # Poll the queue for snapshots and save them in batches until the workers
    # are done processing each unmeasured snapshot. Then save any remaining
    # snapshots.
    snapshots = []
    snapshots_measured = False

    def save_snapshots():
        """Saves measured snapshots if there were any, resets |snapshots| to an
        empty list and records the fact that snapshots have been measured."""
        if not snapshots:
            return

        db_utils.bulk_save(snapshots)
        snapshots.clear()
        nonlocal snapshots_measured
        snapshots_measured = True

    while True:
        all_finished = True
        job_ids = initial_jobs.keys()
        jobs = rq.job.Job.fetch_many(job_ids, queue.connection)

        logger.info('len(results): %d', len(jobs))
        for job in jobs:
            if job is None:
                logger.info('job is None, %s', all(j is None for j in jobs))
                initial_jobs = {}
                break
            status = job.get_status(refresh=False)
            if status is None:
                logger.info('%s returned None', job.get_call_string())
                del initial_jobs[job.id]
                continue

            if status == rq.job.JobStatus.FAILED:  # pylint: disable=no-member
                del initial_jobs[job.id]
                continue

            if status != rq.job.JobStatus.FINISHED:  # pylint: disable=no-member
                # Note if we haven't finished all tasks so we can break out of
                # the outer (infinite) loop.
                all_finished = False
                continue

            del initial_jobs[job.id]
            if job.return_value is None:
                continue

            snapshot = job.return_value
            snapshots.append(snapshot)
            next_job = enqueue_next_measure_job(job.args[0], experiment_config,
                                                queue)
            if next_job is None:
                continue
            initial_jobs[next_job.id] = next_job

        if len(snapshots) >= SNAPSHOTS_BATCH_SAVE_SIZE:
            save_snapshots()

        if all_finished:
            break

        # Sleep so we don't waste CPU cycles polling results constantly.
        time.sleep(POLL_RESULTS_WAIT_SECONDS)

    # If we have any snapshots left save them now.
    save_snapshots()

    logger.info('Done measuring all trials.')
    schedule_measure_workers.schedule(experiment_config, queue)
    return snapshots_measured


def _time_to_cycle(time_in_seconds: float) -> int:
    """Converts |time_in_seconds| to the corresponding cycle and returns it."""
    return time_in_seconds // experiment_utils.get_snapshot_seconds()


def _query_ids_of_measured_trials(experiment: str):
    """Returns a query of the ids of trials in |experiment| that have measured
    snapshots."""
    trials_and_snapshots_query = db_utils.query(models.Snapshot).options(
        orm.joinedload('trial'))
    experiment_trials_filter = models.Snapshot.trial.has(experiment=experiment,
                                                         preempted=False)
    experiment_trials_and_snapshots_query = trials_and_snapshots_query.filter(
        experiment_trials_filter)
    experiment_snapshot_trial_ids_query = (
        experiment_trials_and_snapshots_query.with_entities(
            models.Snapshot.trial_id))
    return experiment_snapshot_trial_ids_query.distinct()


def _query_unmeasured_trials(experiment: str):
    """Returns a query of trials in |experiment| that have not been measured."""
    trial_query = db_utils.query(models.Trial)
    ids_of_trials_with_snapshots = _query_ids_of_measured_trials(experiment)
    no_snapshots_filter = ~models.Trial.id.in_(ids_of_trials_with_snapshots)
    started_trials_filter = ~models.Trial.time_started.is_(None)
    nonpreempted_trials_filter = ~models.Trial.preempted
    experiment_trials_filter = models.Trial.experiment == experiment
    return trial_query.filter(experiment_trials_filter, no_snapshots_filter,
                              started_trials_filter, nonpreempted_trials_filter)


def _get_unmeasured_first_snapshots(
        experiment: str) -> List[measure_worker.SnapshotMeasureRequest]:
    """Returns a list of unmeasured SnapshotMeasureRequests that are the first
    snapshot for their trial. The trials are trials in |experiment|."""
    trials_without_snapshots = _query_unmeasured_trials(experiment)
    return [
        measure_worker.SnapshotMeasureRequest(trial.fuzzer, trial.benchmark,
                                              trial.id, 1)
        for trial in trials_without_snapshots
    ]


SnapshotWithTime = collections.namedtuple(
    'SnapshotWithTime', ['fuzzer', 'benchmark', 'trial_id', 'time'])


def _query_measured_latest_snapshots(experiment: str):
    """Returns a generator of a SnapshotWithTime representing a snapshot that is
    the first snapshot for their trial. The trials are trials in
    |experiment|."""
    latest_time_column = func.max(models.Snapshot.time)
    # The order of these columns must correspond to the fields in
    # SnapshotWithTime.
    columns = (models.Trial.fuzzer, models.Trial.benchmark,
               models.Snapshot.trial_id, latest_time_column)
    experiment_filter = models.Snapshot.trial.has(experiment=experiment)
    group_by_columns = (models.Snapshot.trial_id, models.Trial.benchmark,
                        models.Trial.fuzzer)
    snapshots_query = db_utils.query(*columns).join(
        models.Trial).filter(experiment_filter).group_by(*group_by_columns)
    return (SnapshotWithTime(*snapshot) for snapshot in snapshots_query)


def _get_unmeasured_next_snapshots(
        experiment: str,
        max_cycle: int) -> List[measure_worker.SnapshotMeasureRequest]:
    """Returns a list of the latest unmeasured SnapshotMeasureRequests
    of trials in |experiment| that have been measured at least once in
    |experiment|. |max_total_time| is used to determine if a trial has another
    snapshot left."""
    # Measure the latest snapshot of every trial that hasn't been measured
    # yet.
    latest_snapshot_query = _query_measured_latest_snapshots(experiment)
    next_snapshots = []
    for snapshot in latest_snapshot_query:
        snapshot_time = snapshot.time
        cycle = _time_to_cycle(snapshot_time)
        next_cycle = cycle + 1
        if next_cycle > max_cycle:
            continue

        snapshot_with_cycle = measure_worker.SnapshotMeasureRequest(
            snapshot.fuzzer, snapshot.benchmark, snapshot.trial_id, next_cycle)
        next_snapshots.append(snapshot_with_cycle)
    return next_snapshots


def get_unmeasured_snapshots(experiment: str, max_cycle: int
                            ) -> List[measure_worker.SnapshotMeasureRequest]:
    """Returns a list of SnapshotMeasureRequests that need to be measured
    (assuming they have been saved already)."""
    # Measure the first snapshot of every started trial without any measured
    # snapshots.
    unmeasured_first_snapshots = _get_unmeasured_first_snapshots(experiment)

    unmeasured_latest_snapshots = _get_unmeasured_next_snapshots(
        experiment, max_cycle)

    # Measure the latest unmeasured snapshot of every other trial.
    return unmeasured_first_snapshots + unmeasured_latest_snapshots


def initialize_logs(experiment_name):
    """Initialize logs. This must be called on process start."""
    logs.initialize(
        default_extras={
            'component': 'dispatcher',
            'subcomponent': 'measurer',
            'experiment': experiment_name,
        })


def main():
    """Measure the experiment."""
    multiprocessing.set_start_method('spawn')

    experiment_name = experiment_utils.get_experiment_name()
    initialize_logs(experiment_name)
    experiment_config = yaml_utils.read(sys.argv[1])
    try:
        measure_loop(experiment_config)
    except Exception as error:
        logger.error('Error conducting experiment.')
        raise error


if __name__ == '__main__':
    sys.exit(main())
