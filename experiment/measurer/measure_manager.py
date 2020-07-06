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
from typing import Dict, List, Set

import rq.job
from sqlalchemy import func
from sqlalchemy import orm

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
    manager = MeasureJobManager(experiment_config, queue)
    while True:
        try:
            # Get whether all trials have ended before we measure to prevent
            # races.
            all_trials_ended = scheduler.all_trials_ended(experiment)
            if not measure_all_trials(manager):
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
    # Be generous with amount of time.
    return experiment_utils.get_snapshot_seconds() * 1.5


class MeasureJobManager:
    """Class that creates measure jobs."""

    def __init__(self, experiment_config: dict, rq_queue):
        self.config = experiment_config
        self.queue = rq_queue
        self.job_timeout = get_job_timeout()

        # Dictionary containing a mapping of trial ids to values for trials
        # where we shouldn't measure the "next" unmeasured cycle in the db.
        # This is used when trials shouldn't be measured anymore or a certain
        # cycle should be skipped for a given trial. The values in this
        # dictionary are either the cycle that should be measured instead, or
        # None if the trial shouldn't be measured at all.
        self.special_handling_dict: Dict[int, int] = {}

    def enqueue_measure_jobs_for_unmeasured(self) -> Set[int]:
        """Get snapshots we need to measure from the db and enqueue jobs to
        measure them. Returns these jobs"""
        experiment = self.config['experiment']
        max_total_time = self.config['max_total_time']
        max_cycle = _time_to_cycle(max_total_time)
        unmeasured_snapshots = get_unmeasured_snapshots(experiment, max_cycle)
        logger.info('Enqueuing measure: %d jobs.', len(unmeasured_snapshots))
        jobs = self.enqueue_measure_jobs(unmeasured_snapshots)
        logger.info('Done enqueuing jobs.')
        return {job.id for job in jobs}

    def enqueue_measure_jobs(
            self, measure_reqs: List[measure_worker.SnapshotMeasureRequest]):
        """Adds jobs to perform each measurement request in measure_reqs to the
        queue, and returns them."""
        jobs = []
        for measure_req in measure_reqs:
            job = self.enqueue_measure_job(measure_req)
            if job is None:
                continue

            jobs.append(job)
        return jobs

    def enqueue_measure_job(self,
                            measure_req: measure_worker.SnapshotMeasureRequest):
        """Enqueues a job to measure as requested by measure_req, doing any
        special handling for particular trials if needed. Returns this job."""
        measure_req = self.replace_request_if_needed(measure_req)
        if measure_req is None:
            return None
        return self.queue.enqueue(measure_worker.measure_trial_coverage,
                                  measure_req,
                                  job_timeout=self.job_timeout,
                                  result_ttl=self.job_timeout,
                                  ttl=self.job_timeout)

    def replace_request_if_needed(
            self, measure_req: measure_worker.SnapshotMeasureRequest
    ) -> measure_worker.SnapshotMeasureRequest:
        """Returns a SnapshotMeasureRequest. When the request doesn't need
        special handling (i.e. most cases), returns |measure_req|. Otherwise
        returns None if the trial shouldn't be measured anymore or returns a
        measure request for a later cycle if needed."""
        if measure_req.trial_id not in self.special_handling_dict:
            return measure_req
        cycle_to_measure_instead = (
            self.special_handling_dict[measure_req.trial_id])

        if cycle_to_measure_instead is None:
            # This means the trial shouldn't be measured anymore.
            logger.info(
                'Not queuing request for trial: %d, cycle: %d. '
                'Trial has nothing more to measure', measure_req.trial_id,
                measure_req.cycle)
            return None

        logger.info(
            'Queuing request to measure cycle: %d instead of %d '
            'for trial: %d.', measure_req.cycle, cycle_to_measure_instead,
            measure_req.trial_id)

        return get_request_for_later_cycle(measure_req,
                                           cycle_to_measure_instead)

    def enqueue_next_measure_job(
            self, unmeasured_snapshot: measure_worker.SnapshotMeasureRequest):
        """Adds a job to measure the next snapshot after |unmeasured_snapshot|
        to the queue and returns the job."""
        # Don't schedule another job when the cycle we just measured was the
        # last one in the trial.
        max_total_time = self.config['max_total_time']
        if _time_to_cycle(max_total_time) == unmeasured_snapshot.cycle:
            return None

        next_unmeasured_snapshot = measure_worker.SnapshotMeasureRequest(
            unmeasured_snapshot.fuzzer, unmeasured_snapshot.benchmark,
            unmeasured_snapshot.trial_id, unmeasured_snapshot.cycle + 1)
        return self.enqueue_measure_job(next_unmeasured_snapshot)

    def run_scheduler(self):
        """Runs the worker scheduler on the queue to scale up or down the worker
        instance group."""
        # TODO(metzman): Move this to scheduler or it's own process. It's here
        # for now because the scheduler quits too early.
        schedule_measure_workers.schedule(self.config, self.queue)

    def get_jobs(self, job_ids):
        """Fetches the jobs corresponding that have the ids specified by
        |job_ids| from the queue and returns them."""
        return rq.job.Job.fetch_many(job_ids, self.queue.connection)

    def handle_finished_job(self, job):
        """Enqueues another job to measure the trial after |job| completes if
        needed and does book keeping to ensure the right jobs are scheduled."""
        measure_resp = job.return_value
        measure_req = job.args[0]

        if measure_resp.snapshot is None:
            # Do special handling for jobs that finished but were not
            # successful.
            next_job = self.handle_unsuccessful_finished_job(job)
            return measure_resp.snapshot, next_job

        if measure_req.trial_id in self.special_handling_dict:
            # Otherwise the job was successful, but if it was specially handled
            # last time, remove it from the special_handling_dict since it won't
            # need special handling again.
            del self.special_handling_dict[measure_req.trial_id]

        # Schedule a job to measure the next cycle since this cycle one was
        # measured successfully.
        next_job = self.enqueue_next_measure_job(measure_req)
        return measure_resp.snapshot, next_job

    def handle_unsuccessful_finished_job(self, job):
        """Handles jobs that completed but were not able to measure the snapshot
        requested. In most cases this means rescheduling the job to measure the
        snapshot again. The first of the other cases is when the cycle can't be
        measured but a later one can. In that case, which happens when the the
        fuzzer freezes the instance it runs on and the runner misses its chance
        to take a snapshot on some cycles, this method schedules a job for the
        next possible snapshot to measured. In the second of these other cases,
        no other snapshot is possible to measure and the trial has finished. In
        that case, no job is scheduled and this method ensures that no measuring
        job is scheduled for the trial ever again. This is because when the
        trial has finished, it won't produce any new snapshots, so there will
        never be anything more to measure for that snapshot."""
        measure_resp = job.return_value
        assert measure_resp.snapshot is None
        measure_req = job.args[0]
        if measure_resp.next_cycle is not None:
            # Measurement was unsuccessful but when queueing another job for
            # this trial, we should try measuring a later cycle.

            # If we skipped measuring snapshot N and try to measure N+X, we
            # shouldn't have to skip measuring N+X again.
            assert measure_req.trial_id not in self.special_handling_dict

            self.special_handling_dict[
                measure_req.trial_id] = measure_resp.next_cycle
            return self.enqueue_next_measure_job(measure_req)

        if trial_ended(measure_req.trial_id):
            # Measurement was unsuccessful and will never be successful again
            # for this trial, don't measure this trial again.
            self.special_handling_dict[measure_req.trial_id] = None
            return None

        # Measurement was unsuccessful but this trial's cycle should just be
        # measured again.
        # TODO(metzman): Schedule this later so we don't waste time trying to
        # measure it again immediately.
        return self.enqueue_measure_job(measure_req)


def trial_ended(trial_id: int) -> bool:
    """Is the trial with the id |trial_id| finished?"""
    # TODO(metzman): Optimize this to not do so many queries.
    trial = db_utils.query(
        models.Trial).filter(models.Trial.id == trial_id).one()
    return trial.time_ended is not None


def get_request_for_later_cycle(
        initial_measure_req: measure_worker.SnapshotMeasureRequest,
        cycle: int) -> measure_worker.SnapshotMeasureRequest:
    """Returns a measure_worker.SnapshotMeasureRequest that contains all of the
    same attributes as |initial_measure_req| except the cycle is |cycle|. Cycle
    should greater than or equal to |measure_req.cycle|."""
    assert cycle >= initial_measure_req.cycle
    return measure_worker.SnapshotMeasureRequest(initial_measure_req.fuzzer,
                                                 initial_measure_req.benchmark,
                                                 initial_measure_req.trial_id,
                                                 cycle)


def ready_to_measure():
    """Returns True if we are ready to start measuring."""
    experiment_folders_dir = get_experiment_folders_dir()
    return exists_in_experiment_filestore(experiment_folders_dir)


def measure_all_trials(manager: MeasureJobManager) -> bool:
    """Get coverage data (with coverage runs) for all active trials. Note that
    this should not be called unless multiprocessing.set_start_method('spawn')
    was called first. Otherwise it will use fork which breaks logging."""
    logger.info('Measuring all trials.')

    if not ready_to_measure():
        return True

    job_ids = manager.enqueue_measure_jobs_for_unmeasured()
    if not job_ids:
        # If we didn't enqueue any jobs, then there is nothing to measure.
        return False

    manager.run_scheduler()

    # Poll the queue for snapshots and save them in batches, for each snapshot
    # that was measured, schedule another task to measure the next snapshot for
    # that trial. Do this until there are no more tasks and then save any
    # remaining snapshots.
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
        for job_id, job in list(zip(job_ids, manager.get_jobs(job_ids))):
            if job is None:
                logger.error('Job is None')
                job_ids.remove(job_id)
                continue

            status = job.get_status(refresh=False)
            if status is None:
                logger.error('%s returned None', job.get_call_string())
                job_ids.remove(job_id)
                continue

            if status == rq.job.JobStatus.FAILED:  # pylint: disable=no-member
                job_ids.remove(job_id)
                continue

            if status != rq.job.JobStatus.FINISHED:  # pylint: disable=no-member
                # Note if we haven't finished all tasks so we can break out of
                # the outer (infinite) loop.
                continue

            job_ids.remove(job_id)
            snapshot, next_job = manager.handle_finished_job(job)

            if next_job is not None:
                job_ids.add(next_job.id)

            if snapshot is not None:
                snapshots.append(snapshot)

        if len(snapshots) >= SNAPSHOTS_BATCH_SAVE_SIZE:
            save_snapshots()

        if not job_ids:
            save_snapshots()
            job_ids = manager.enqueue_measure_jobs_for_unmeasured()

        if not job_ids:
            break

        # Sleep so we don't waste CPU cycles polling results constantly.
        time.sleep(POLL_RESULTS_WAIT_SECONDS)

    # If we have any snapshots left save them now.
    save_snapshots()

    logger.info('Done measuring all trials.')
    manager.run_scheduler()
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
