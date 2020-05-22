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
import glob
import multiprocessing
import os
import pathlib
import posixpath
import sys
import tarfile
import time
from typing import List, Set

import redis
import rq
from sqlalchemy import func
from sqlalchemy import orm

from common import benchmark_utils
from common import experiment_utils
from common import experiment_path as exp_path
from common import filesystem
from common import fuzzer_utils
from common import gsutil
from common import logs
from common import utils
from database import utils as db_utils
from database import models
from experiment.build import build_utils
from experiment import run_coverage
from experiment import scheduler
from third_party import sancov

logger = logs.Logger('measure_manager')  # pylint: disable=invalid-name

FAIL_WAIT_SECONDS = 30
POLL_RESULTS_WAIT_SECONDS = 5
SNAPSHOTS_BATCH_SAVE_SIZE = 100


def get_experiment_folders_dir():
    """Return experiment folders directory."""
    return exp_path.path('experiment-folders')


def remote_dir_exists(directory: pathlib.Path) -> bool:
    """Does |directory| exist in the CLOUD_EXPERIMENT_BUCKET."""
    return gsutil.ls(exp_path.gcs(directory), must_exist=False)[0] == 0


def measure_loop(experiment: str, max_total_time: int, redis_host: str):
    """Continuously measure trials for |experiment|."""
    db_utils.initialize()
    logs.initialize(default_extras={
        'component': 'dispatcher',
        'subcomponent': 'measurer',
    })
    with multiprocessing.Pool() as pool:
        set_up_coverage_binaries(pool, experiment)
    # Using Multiprocessing.Queue will fail with a complaint about
    # inheriting queue.
    redis_connection = redis.Redis(host=redis_host)
    q = rq.Queue(connection=redis_connection)
    while True:
        try:
            # Get whether all trials have ended before we measure to prevent
            # races.
            all_trials_ended = scheduler.all_trials_ended(experiment)
            if not measure_all_trials(experiment, max_total_time, q):
                # We didn't measure any trials.
                if all_trials_ended:
                    # There are no trials producing snapshots to measure.
                    # Given that we couldn't measure any snapshots, we won't
                    # be able to measure any the future, so break now.
                    break
        except Exception:  # pylint: disable=broad-except
            logger.error('Error occurred during measuring.')

            time.sleep(FAIL_WAIT_SECONDS)

    logger.info('Finished measuring.')


def get_job_timeout():
    """Returns the timeout for an rq job."""
    return experiment_utils.get_snapshot_seconds() + 2 * 60


def measure_all_trials(experiment: str, max_total_time: int, q) -> bool:  # pylint: disable=invalid-name
    """Get coverage data (with coverage runs) for all active trials. Note that
    this should not be called unless multiprocessing.set_start_method('spawn')
    was called first. Otherwise it will use fork which breaks logging."""
    logger.info('Measuring all trials.')

    experiment_folders_dir = get_experiment_folders_dir()
    if not remote_dir_exists(experiment_folders_dir):
        return True

    max_cycle = _time_to_cycle(max_total_time)
    unmeasured_snapshots = get_unmeasured_snapshots(experiment, max_cycle)

    if not unmeasured_snapshots:
        return False

    job_timeout = get_job_timeout()
    results = [
        q.enqueue(measure_worker.measure_trial_coverage,
                  unmeasured_snapshot,
                  job_timeout=job_timeout)
        for unmeasured_snapshot in unmeasured_snapshots
    ]

    # Poll the queue for snapshots and save them in batches until the pool is
    # done processing each unmeasured snapshot. Then save any remaining
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

        # Copy results because we want to mutate it while iterating through it.
        results_copy = results.copy()

        for result in results_copy:
            if not result.is_finished:
                # Note if we haven't finished all tasks so we can break out of
                # the outer (infinite) loop.
                all_finished = False
                continue

            if result.return_value is None:
                continue

            snapshots.append(result.return_value)
            results.remove(result)

        if len(snapshots) >= SNAPSHOTS_BATCH_SAVE_SIZE:
            save_snapshots()

        if all_finished:
            break

        # Sleep so we don't waste CPU cycles polling results constantly.
        time.sleep(POLL_RESULTS_WAIT_SECONDS)

    # If we have any snapshots left save them now.
    save_snapshots()

    logger.info('Done measuring all trials.')
    return snapshots_measured


def _time_to_cycle(time_in_seconds: float) -> int:
    """Converts |time_in_seconds| to the corresponding cycle and returns it."""
    return time_in_seconds // experiment_utils.get_snapshot_seconds()


def _query_ids_of_measured_trials(experiment: str):
    """Returns a query of the ids of trials in |experiment| that have measured
    snapshots."""
    trials_and_snapshots_query = db_utils.query(models.Snapshot).options(
        orm.joinedload('trial'))
    experiment_trials_filter = models.Snapshot.trial.has(experiment=experiment)
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
    experiment_trials_filter = models.Trial.experiment == experiment
    return trial_query.filter(experiment_trials_filter, no_snapshots_filter,
                              started_trials_filter)


def _get_unmeasured_first_snapshots(experiment: str
                                   ) -> List[measure_worker.SnapshotMeasureRequest]:
    """Returns a list of unmeasured SnapshotMeasureRequests that are the first
    snapshot for their trial. The trials are trials in |experiment|."""
    trials_without_snapshots = _query_unmeasured_trials(experiment)
    return [
        measure_worker.SnapshotMeasureRequest(
            trial.fuzzer, trial.benchmark, trial.id,
            1) for trial in trials_without_snapshots
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


def _get_unmeasured_next_snapshots(experiment: str, max_cycle: int
                                  ) -> List[measure_worker.SnapshotMeasureRequest]:
    """Returns a list of the latest unmeasured measurer.SnapshotMeasureRequests
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


def set_up_coverage_binaries(pool, experiment):
    """Set up coverage binaries for all benchmarks in |experiment|."""
    benchmarks = [
        trial.benchmark for trial in db_utils.query(models.Trial).distinct(
            models.Trial.benchmark).filter(
                models.Trial.experiment == experiment)
    ]
    coverage_binaries_dir = build_utils.get_coverage_binaries_dir()
    if not os.path.exists(coverage_binaries_dir):
        os.makedirs(coverage_binaries_dir)
    pool.map(set_up_coverage_binary, benchmarks)


def set_up_coverage_binary(benchmark):
    """Set up coverage binaries for |benchmark|."""
    initialize_logs()
    coverage_binaries_dir = build_utils.get_coverage_binaries_dir()
    benchmark_coverage_binary_dir = coverage_binaries_dir / benchmark
    if not os.path.exists(benchmark_coverage_binary_dir):
        os.mkdir(benchmark_coverage_binary_dir)
    archive_name = 'coverage-build-%s.tar.gz' % benchmark
    cloud_bucket_archive_path = exp_path.gcs(coverage_binaries_dir /
                                             archive_name)
    gsutil.cp(cloud_bucket_archive_path,
              str(benchmark_coverage_binary_dir),
              write_to_stdout=False)
    archive_path = benchmark_coverage_binary_dir / archive_name
    tar = tarfile.open(archive_path, 'r:gz')
    tar.extractall(benchmark_coverage_binary_dir)
    os.remove(archive_path)


def get_coverage_binary(benchmark: str) -> str:
    """Get the coverage binary for benchmark."""
    coverage_binaries_dir = build_utils.get_coverage_binaries_dir()
    fuzz_target = benchmark_utils.get_fuzz_target(benchmark)
    return fuzzer_utils.get_fuzz_target_binary(coverage_binaries_dir /
                                               benchmark,
                                               fuzz_target_name=fuzz_target)


def initialize_logs():
    """Initialize logs. This must be called on process start."""
    logs.initialize(default_extras={
        'component': 'dispatcher',
        'subcomponent': 'measurer',
    })


def main():
    """Measure the experiment."""
    initialize_logs()
    multiprocessing.set_start_method('spawn')

    experiment_name = experiment_utils.get_experiment_name()

    try:
        measure_loop(experiment_name, int(sys.argv[1]), sys.argv[2])
    except Exception as error:
        logs.error('Error conducting experiment.')
        raise error


if __name__ == '__main__':
    sys.exit(main())
