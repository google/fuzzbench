#!/usr/bin/env python3
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
"""Module for measuring snapshots from trial runners."""

import collections
import multiprocessing
import os
import pathlib
import posixpath
import sys
import tarfile
import time
from typing import List, Set
import queue
import json

from sqlalchemy import func
from sqlalchemy import orm

from common import benchmark_utils
from common import experiment_utils
from common import experiment_path as exp_path
from common import filesystem
from common import fuzzer_utils
from common import filestore_utils
from common import logs
from common import utils
from common import new_process
from database import utils as db_utils
from database import models
from experiment.build import build_utils
from experiment import run_coverage
from experiment import scheduler

logger = logs.Logger('measurer')  # pylint: disable=invalid-name

SnapshotMeasureRequest = collections.namedtuple(
    'SnapshotMeasureRequest', ['fuzzer', 'benchmark', 'trial_id', 'cycle'])

NUM_RETRIES = 3
RETRY_DELAY = 3
FAIL_WAIT_SECONDS = 30
SNAPSHOT_QUEUE_GET_TIMEOUT = 1
SNAPSHOTS_BATCH_SAVE_SIZE = 100


def get_experiment_folders_dir():
    """Return experiment folders directory."""
    return exp_path.path('experiment-folders')


def exists_in_experiment_filestore(path: pathlib.Path) -> bool:
    """Returns True if |path| exists in the experiment_filestore."""
    return filestore_utils.ls(exp_path.filestore(path),
                              must_exist=False).retcode == 0


def measure_loop(experiment: str, max_total_time: int):
    """Continuously measure trials for |experiment|."""
    logs.initialize(default_extras={
        'component': 'dispatcher',
        'subcomponent': 'measurer',
    })
    logs.info('Start measure_loop.')

    with multiprocessing.Pool() as pool, multiprocessing.Manager() as manager:
        set_up_coverage_binaries(pool, experiment)
        # Using Multiprocessing.Queue will fail with a complaint about
        # inheriting queue.
        q = manager.Queue()  # pytype: disable=attribute-error
        while True:
            try:
                # Get whether all trials have ended before we measure to prevent
                # races.
                all_trials_ended = scheduler.all_trials_ended(experiment)

                if not measure_all_trials(experiment, max_total_time, pool, q):
                    # We didn't measure any trials.
                    if all_trials_ended:
                        # There are no trials producing snapshots to measure.
                        # Given that we couldn't measure any snapshots, we won't
                        # be able to measure any the future, so stop now.
                        break
            except Exception:  # pylint: disable=broad-except
                logger.error('Error occurred during measuring.')

            time.sleep(FAIL_WAIT_SECONDS)

    logger.info('Finished measuring.')


def measure_all_trials(experiment: str, max_total_time: int, pool, q) -> bool:  # pylint: disable=invalid-name
    """Get coverage data (with coverage runs) for all active trials. Note that
    this should not be called unless multiprocessing.set_start_method('spawn')
    was called first. Otherwise it will use fork which breaks logging."""
    logger.info('Measuring all trials.')

    experiment_folders_dir = get_experiment_folders_dir()
    if not exists_in_experiment_filestore(experiment_folders_dir):
        return True

    max_cycle = _time_to_cycle(max_total_time)
    unmeasured_snapshots = get_unmeasured_snapshots(experiment, max_cycle)

    if not unmeasured_snapshots:
        return False

    measure_trial_coverage_args = [
        (unmeasured_snapshot, max_cycle, q)
        for unmeasured_snapshot in unmeasured_snapshots
    ]

    result = pool.starmap_async(measure_trial_coverage,
                                measure_trial_coverage_args)

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
        try:
            snapshot = q.get(timeout=SNAPSHOT_QUEUE_GET_TIMEOUT)
            snapshots.append(snapshot)
        except queue.Empty:
            if result.ready():
                # If "ready" that means pool has finished calling on each
                # unmeasured_snapshot. Since it is finished and the queue is
                # empty, we can stop checking the queue for more snapshots.
                logger.debug(
                    'Finished call to map with measure_trial_coverage.')
                break

            if len(snapshots) >= SNAPSHOTS_BATCH_SAVE_SIZE * .75:
                # Save a smaller batch size if we can make an educated guess
                # that we will have to wait for the next snapshot.
                save_snapshots()
                continue

        if len(snapshots) >= SNAPSHOTS_BATCH_SAVE_SIZE and not result.ready():
            save_snapshots()

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


def _get_unmeasured_first_snapshots(experiment: str
                                   ) -> List[SnapshotMeasureRequest]:
    """Returns a list of unmeasured SnapshotMeasureRequests that are the first
    snapshot for their trial. The trials are trials in |experiment|."""
    trials_without_snapshots = _query_unmeasured_trials(experiment)
    return [
        SnapshotMeasureRequest(trial.fuzzer, trial.benchmark, trial.id, 1)
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


def _get_unmeasured_next_snapshots(experiment: str, max_cycle: int
                                  ) -> List[SnapshotMeasureRequest]:
    """Returns a list of the latest unmeasured SnapshotMeasureRequests of
    trials in |experiment| that have been measured at least once in
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

        snapshot_with_cycle = SnapshotMeasureRequest(snapshot.fuzzer,
                                                     snapshot.benchmark,
                                                     snapshot.trial_id,
                                                     next_cycle)
        next_snapshots.append(snapshot_with_cycle)
    return next_snapshots


def get_unmeasured_snapshots(experiment: str,
                             max_cycle: int) -> List[SnapshotMeasureRequest]:
    """Returns a list of SnapshotMeasureRequests that need to be measured
    (assuming they have been saved already)."""
    # Measure the first snapshot of every started trial without any measured
    # snapshots.
    unmeasured_first_snapshots = _get_unmeasured_first_snapshots(experiment)

    unmeasured_latest_snapshots = _get_unmeasured_next_snapshots(
        experiment, max_cycle)

    # Measure the latest unmeasured snapshot of every other trial.
    return unmeasured_first_snapshots + unmeasured_latest_snapshots


def extract_corpus(corpus_archive: str, sha_blacklist: Set[str],
                   output_directory: str):
    """Extract a corpus from |corpus_archive| to |output_directory|."""
    pathlib.Path(output_directory).mkdir(exist_ok=True)
    tar = tarfile.open(corpus_archive, 'r:gz')
    for member in tar.getmembers():

        if not member.isfile():
            # We don't care about directory structure. So skip if not a file.
            continue

        member_file_handle = tar.extractfile(member)
        if not member_file_handle:
            logger.info('Failed to get handle to %s', member)
            continue

        member_contents = member_file_handle.read()
        filename = utils.string_hash(member_contents)
        if filename in sha_blacklist:
            continue

        file_path = os.path.join(output_directory, filename)

        if os.path.exists(file_path):
            # Don't write out duplicates in the archive.
            continue

        filesystem.write(file_path, member_contents, 'wb')


class SnapshotMeasurer:  # pylint: disable=too-many-instance-attributes
    """Class used for storing details needed to measure coverage of a particular
    trial."""

    UNIT_BLACKLIST = collections.defaultdict(set)

    def __init__(self, fuzzer: str, benchmark: str, trial_num: int,
                 trial_logger: logs.Logger):
        self.fuzzer = fuzzer
        self.benchmark = benchmark
        self.trial_num = trial_num
        self.logger = trial_logger
        benchmark_fuzzer_trial_dir = experiment_utils.get_trial_dir(
            fuzzer, benchmark, trial_num)
        work_dir = experiment_utils.get_work_dir()
        measurement_dir = os.path.join(work_dir, 'measurement-folders',
                                       benchmark_fuzzer_trial_dir)
        self.corpus_dir = os.path.join(measurement_dir, 'corpus')

        self.crashes_dir = os.path.join(measurement_dir, 'crashes')
        self.coverage_dir = os.path.join(measurement_dir, 'coverage')
        self.report_dir = os.path.join(measurement_dir, 'reports')
        self.trial_dir = os.path.join(work_dir, 'experiment-folders',
                                      benchmark_fuzzer_trial_dir)

        # Stores the files that have already been measured for a trial.
        self.measured_files_path = os.path.join(self.report_dir,
                                                'measured-files.txt')

        # Used by the runner to signal that there won't be a corpus archive for
        # a cycle because the corpus hasn't changed since the last cycle.
        self.unchanged_cycles_path = os.path.join(self.trial_dir, 'results',
                                                  'unchanged-cycles')

        # Store the profraw file containing coverage data for each cycle.
        self.profraw_file = os.path.join(self.coverage_dir, 'data.profraw')

        # Store the profdata file for the current trial.
        self.profdata_file = os.path.join(self.report_dir, 'data.profdata')

        # Store the coverage information in json form.
        self.cov_summary_file = os.path.join(self.report_dir,
                                             'cov_summary.json')

    def initialize_measurement_dirs(self):
        """Initialize directories that will be needed for measuring
        coverage."""
        for directory in [self.corpus_dir, self.coverage_dir, self.crashes_dir]:
            filesystem.recreate_directory(directory)
        filesystem.create_directory(self.report_dir)

    def run_cov_new_units(self):
        """Run the coverage binary on new units."""
        coverage_binary = get_coverage_binary(self.benchmark)
        crashing_units = run_coverage.do_coverage_run(coverage_binary,
                                                      self.corpus_dir,
                                                      self.profraw_file,
                                                      self.crashes_dir)

        self.UNIT_BLACKLIST[self.benchmark] = (
            self.UNIT_BLACKLIST[self.benchmark].union(set(crashing_units)))

    def get_current_coverage(self) -> int:
        """Get the current number of lines covered."""
        if not os.path.exists(self.cov_summary_file):
            self.logger.warning('No coverage summary json file found.')
            return 0
        try:
            with open(self.cov_summary_file) as summary:
                # Using the last line to skip the warning in bloaty
                coverage_info = json.loads(summary.readlines()[-1])
                coverage_data = coverage_info["data"][0]
                summary_data = coverage_data["totals"]
                regions_coverage_data = summary_data["regions"]
                regions_covered = regions_coverage_data["covered"]
                return regions_covered
        except Exception:  # pylint: disable=broad-except
            self.logger.error('Coverage summary json file defective.')
            return 0

    def generate_profdata(self, cycle: int):
        """Generate .profdata file from .profraw file."""
        if os.path.isfile(self.profdata_file):
            # If coverage profdata exists, then merge it with
            # existing available data.
            files_to_merge = [self.profraw_file, self.profdata_file]
        else:
            files_to_merge = [self.profraw_file]
        command = ['llvm-profdata', 'merge', '-sparse'
                  ] + files_to_merge + ['-o', self.profdata_file]
        result = new_process.execute(command)

        if result.retcode != 0:
            self.logger.error(
                'Coverage profdata generation failed for cycle: %d.', cycle)

    def generate_summary(self, cycle: int):
        """Transform the .profdata file into json form."""
        coverage_binary = get_coverage_binary(self.benchmark)
        command = [
            'llvm-cov', 'export', '-format=text', '-summary-only',
            coverage_binary,
            '-instr-profile=%s' % self.profdata_file
        ]
        with open(self.cov_summary_file, 'w') as output_file:
            result = new_process.execute(command, output_file=output_file)
        if result.retcode != 0:
            self.logger.error(
                'Coverage summary json file generation failed for \
                    cycle: %d.', cycle)

    def is_cycle_unchanged(self, cycle: int) -> bool:
        """Returns True if |cycle| is unchanged according to the
        unchanged-cycles file. This file is written to by the trial's runner."""

        def copy_unchanged_cycles_file():
            unchanged_cycles_filestore_path = exp_path.filestore(
                self.unchanged_cycles_path)
            result = filestore_utils.cp(unchanged_cycles_filestore_path,
                                        self.unchanged_cycles_path,
                                        expect_zero=False)
            return result.retcode == 0

        if not os.path.exists(self.unchanged_cycles_path):
            if not copy_unchanged_cycles_file():
                return False

        def get_unchanged_cycles():
            return [
                int(cycle) for cycle in filesystem.read(
                    self.unchanged_cycles_path).splitlines()
            ]

        unchanged_cycles = get_unchanged_cycles()
        if cycle in unchanged_cycles:
            return True

        if cycle < max(unchanged_cycles):
            # If the last/max unchanged cycle is greater than |cycle| then we
            # don't need to copy the file again.
            return False

        if not copy_unchanged_cycles_file():
            return False

        unchanged_cycles = get_unchanged_cycles()
        return cycle in unchanged_cycles

    def extract_corpus(self, corpus_archive_path) -> bool:
        """Extract the corpus archive for this cycle if it exists."""
        if not os.path.exists(corpus_archive_path):
            self.logger.warning('Corpus not found: %s.', corpus_archive_path)
            return False

        already_measured_units = self.get_measured_files()
        crash_blacklist = self.UNIT_BLACKLIST[self.benchmark]
        unit_blacklist = already_measured_units.union(crash_blacklist)

        extract_corpus(corpus_archive_path, unit_blacklist, self.corpus_dir)
        return True

    def archive_crashes(self, cycle):
        """Archive this cycle's crashes into filestore."""
        if not os.listdir(self.crashes_dir):
            logs.info('No crashes found for cycle %d.', cycle)
            return

        logs.info('Archiving crashes for cycle %d.', cycle)
        crashes_archive_name = experiment_utils.get_crashes_archive_name(cycle)
        archive_path = os.path.join(os.path.dirname(self.crashes_dir),
                                    crashes_archive_name)
        with tarfile.open(archive_path, 'w:gz') as tar:
            tar.add(self.crashes_dir,
                    arcname=os.path.basename(self.crashes_dir))
        archive_filestore_path = exp_path.filestore(
            posixpath.join(self.trial_dir, 'crashes', crashes_archive_name))
        filestore_utils.cp(archive_path, archive_filestore_path)
        os.remove(archive_path)

    def update_measured_files(self):
        """Updates the measured-files.txt file for this trial with
        files measured in this snapshot."""
        current_files = set(os.listdir(self.corpus_dir))
        already_measured = self.get_measured_files()
        filesystem.write(self.measured_files_path,
                         '\n'.join(current_files.union(already_measured)))

    def get_measured_files(self):
        """Returns a the set of files that have been measured for this
        snapshot's trials."""
        if not os.path.exists(self.measured_files_path):
            return set()
        return set(filesystem.read(self.measured_files_path).splitlines())


def measure_trial_coverage(  # pylint: disable=invalid-name
        measure_req, max_cycle: int,
        q: multiprocessing.Queue) -> models.Snapshot:
    """Measure the coverage obtained by |trial_num| on |benchmark| using
    |fuzzer|."""
    initialize_logs()
    logger.debug('Measuring trial: %d.', measure_req.trial_id)
    min_cycle = measure_req.cycle
    # Add 1 to ensure we measure the last cycle.
    for cycle in range(min_cycle, max_cycle + 1):
        try:
            snapshot = measure_snapshot_coverage(measure_req.fuzzer,
                                                 measure_req.benchmark,
                                                 measure_req.trial_id, cycle)
            if not snapshot:
                break
            q.put(snapshot)
        except Exception:  # pylint: disable=broad-except
            logger.error('Error measuring cycle.',
                         extras={
                             'fuzzer': measure_req.fuzzer,
                             'benchmark': measure_req.benchmark,
                             'trial_id': str(measure_req.trial_id),
                             'cycle': str(cycle),
                         })
    logger.debug('Done measuring trial: %d.', measure_req.trial_id)


def measure_snapshot_coverage(fuzzer: str, benchmark: str, trial_num: int,
                              cycle: int) -> models.Snapshot:
    """Measure coverage of the snapshot for |cycle| for |trial_num| of |fuzzer|
    and |benchmark|."""
    snapshot_logger = logs.Logger('measurer',
                                  default_extras={
                                      'fuzzer': fuzzer,
                                      'benchmark': benchmark,
                                      'trial_id': str(trial_num),
                                      'cycle': str(cycle),
                                  })
    snapshot_measurer = SnapshotMeasurer(fuzzer, benchmark, trial_num,
                                         snapshot_logger)

    measuring_start_time = time.time()
    snapshot_logger.info('Measuring cycle: %d.', cycle)
    this_time = cycle * experiment_utils.get_snapshot_seconds()
    if snapshot_measurer.is_cycle_unchanged(cycle):
        snapshot_logger.info('Cycle: %d is unchanged.', cycle)
        regions_covered = snapshot_measurer.get_current_coverage()
        return models.Snapshot(time=this_time,
                               trial_id=trial_num,
                               edges_covered=regions_covered)

    corpus_archive_dst = os.path.join(
        snapshot_measurer.trial_dir, 'corpus',
        experiment_utils.get_corpus_archive_name(cycle))
    corpus_archive_src = exp_path.filestore(corpus_archive_dst)

    corpus_archive_dir = os.path.dirname(corpus_archive_dst)
    if not os.path.exists(corpus_archive_dir):
        os.makedirs(corpus_archive_dir)

    if filestore_utils.cp(corpus_archive_src,
                          corpus_archive_dst,
                          expect_zero=False).retcode:
        snapshot_logger.warning('Corpus not found for cycle: %d.', cycle)
        return None

    snapshot_measurer.initialize_measurement_dirs()
    snapshot_measurer.extract_corpus(corpus_archive_dst)
    # Don't keep corpus archives around longer than they need to be.
    os.remove(corpus_archive_dst)

    # Run coverage on the new corpus units.
    snapshot_measurer.run_cov_new_units()

    # Generate profdata and transform it into json form.
    snapshot_measurer.generate_profdata(cycle)
    snapshot_measurer.generate_summary(cycle)

    # Get the coverage of the new corpus units.
    regions_covered = snapshot_measurer.get_current_coverage()
    snapshot = models.Snapshot(time=this_time,
                               trial_id=trial_num,
                               edges_covered=regions_covered)

    # Record the new corpus files.
    snapshot_measurer.update_measured_files()

    # Archive crashes directory.
    snapshot_measurer.archive_crashes(cycle)
    measuring_time = round(time.time() - measuring_start_time, 2)
    snapshot_logger.info('Measured cycle: %d in %f seconds.', cycle,
                         measuring_time)
    return snapshot


def set_up_coverage_binaries(pool, experiment):
    """Set up coverage binaries for all benchmarks in |experiment|."""
    # Use set comprehension to select distinct benchmarks.
    benchmarks = [
        benchmark_tuple[0]
        for benchmark_tuple in db_utils.query(models.Trial.benchmark).distinct(
        ).filter(models.Trial.experiment == experiment)
    ]

    coverage_binaries_dir = build_utils.get_coverage_binaries_dir()
    filesystem.create_directory(coverage_binaries_dir)
    pool.map(set_up_coverage_binary, benchmarks)


def set_up_coverage_binary(benchmark):
    """Set up coverage binaries for |benchmark|."""
    initialize_logs()
    coverage_binaries_dir = build_utils.get_coverage_binaries_dir()
    benchmark_coverage_binary_dir = coverage_binaries_dir / benchmark
    filesystem.create_directory(benchmark_coverage_binary_dir)
    archive_name = 'coverage-build-%s.tar.gz' % benchmark
    archive_filestore_path = exp_path.filestore(coverage_binaries_dir /
                                                archive_name)
    filestore_utils.cp(archive_filestore_path,
                       str(benchmark_coverage_binary_dir))
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
        measure_loop(experiment_name, int(sys.argv[1]))
    except Exception as error:
        logs.error('Error conducting experiment.')
        raise error


if __name__ == '__main__':
    sys.exit(main())
