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
import glob
import json
import os
import pathlib
import posixpath
import tarfile
import tempfile
import time
from typing import List, Set

from common import benchmark_utils
from common import experiment_utils
from common import experiment_path as exp_path
from common import filesystem
from common import fuzzer_utils
from common import filestore_utils
from common import logs
from common import utils
from database import models
from experiment.build import build_utils
from experiment.measurer import run_coverage
from third_party import sancov

logger = logs.Logger('measure_worker')  # pylint: disable=invalid-name

SnapshotMeasureRequest = collections.namedtuple(
    'SnapshotMeasureRequest', ['fuzzer', 'benchmark', 'trial_id', 'cycle'])


def initialize_logs():
    """Initialize logs. This must be called on process start."""
    logs.initialize(default_extras={
        'component': 'dispatcher',
        'subcomponent': 'measurer',
    })


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


class StateFile:
    """A class representing the state of measuring a particular trial on
    particular cycle. Objects of this class are backed by files stored in the
    bucket."""

    def __init__(self, name: str, state_dir: str, cycle: int):
        self.name = name
        self.state_dir = state_dir
        self.cycle = cycle
        self._prev_state = None

    def _get_bucket_cycle_state_file_path(self, cycle: int) -> str:
        """Get the state file path in the bucket."""
        state_file_name = experiment_utils.get_cycle_file_name(
            self.name, cycle) + '.json'
        state_file_path = os.path.join(self.state_dir, state_file_name)
        return exp_path.gcs(pathlib.Path(state_file_path))

    def _get_previous_cycle_state(self) -> list:
        """Returns the state from the previous cycle. Returns [] if |self.cycle|
        is 1."""
        if self.cycle == 1:
            return []

        previous_state_file_bucket_path = (
            self._get_bucket_cycle_state_file_path(self.cycle - 1))

        return json.loads(
            gsutil.cat(previous_state_file_bucket_path, expect_zero=False))

    def get_previous(self):
        """Returns the previous state."""
        if self._prev_state is None:
            self._prev_state = self._get_previous_cycle_state()

        return self._prev_state

    def set_current(self, state):
        """Sets the state for this cycle in the bucket."""
        state_file_bucket_path = self._get_bucket_cycle_state_file_path(
            self.cycle)
        with tempfile.NamedTemporaryFile(mode='w') as temp_file:
            temp_file.write(json.dumps(state))
            temp_file.flush()
            gsutil.cp(temp_file.name, state_file_bucket_path)


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
        self.sancov_dir = os.path.join(measurement_dir, 'sancovs')
        self.state_dir = os.path.join(measurement_dir, 'state')
        self.trial_dir = os.path.join(work_dir, 'experiment-folders',
                                      benchmark_fuzzer_trial_dir)

        # Used by the runner to signal that there won't be a corpus archive for
        # a cycle because the corpus hasn't changed since the last cycle.
        self.unchanged_cycles_path = os.path.join(self.trial_dir, 'results',
                                                  'unchanged-cycles')

    def initialize_measurement_dirs(self):
        """Initialize directories that will be needed for measuring
        coverage."""
        for directory in [self.corpus_dir, self.sancov_dir, self.crashes_dir]:
            filesystem.recreate_directory(directory)

    def run_cov_new_units(self):
        """Run the coverage binary on new units."""
        coverage_binary = get_coverage_binary(self.benchmark)
        crashing_units = run_coverage.do_coverage_run(coverage_binary,
                                                      self.corpus_dir,
                                                      self.sancov_dir,
                                                      self.crashes_dir)

        self.UNIT_BLACKLIST[self.benchmark] = (
            self.UNIT_BLACKLIST[self.benchmark].union(set(crashing_units)))

    def merge_new_pcs(self, cycle: int) -> List[str]:
        """Merge new pcs into and return the list of all covered pcs."""
        prev_pcs = self.get_prev_covered_pcs(cycle)
        covered_pcs_state = self.get_covered_pcs_state(cycle)
        sancov_files = glob.glob(os.path.join(self.sancov_dir, '*.sancov'))
        if not sancov_files:
            self.logger.error('No sancov files.')
            return list(prev_pcs)

        self.logger.info('Sancov files: %s.', str(sancov_files))
        new_pcs = set(sancov.GetPCs(sancov_files))
        all_pcs = sorted(prev_pcs.union(new_pcs))
        # Sort so that file doesn't change if PCs are unchanged.
        covered_pcs_state.set_current(all_pcs)
        return all_pcs

    def is_cycle_unchanged(self, cycle: int) -> bool:
        """Returns True if |cycle| is unchanged according to the
        unchanged-cycles file. This file is written to by the trial's runner."""

        def copy_unchanged_cycles_file():
            unchanged_cyles_gcs_path = exp_path.gcs(self.unchanged_cycles_path)
            result = filestore_utils.cp(unchanged_cyles_gcs_path,
                                        self.unchanged_cycles_path,
                                        expect_zero=False)
            return result.retcode == 0

        if not os.path.exists(self.unchanged_cycles_path):
            if not copy_unchanged_cycles_file():
                return False

        def get_unchanged_cycles():
            """Returns the list of unchanged cycles."""
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

    def get_covered_pcs_state(self, cycle: int) -> StateFile:
        """Returns the StateFile for covered-pcs of this |cycle|."""
        return StateFile('covered-pcs', self.state_dir, cycle)

    def get_prev_covered_pcs(self, cycle: int) -> Set[str]:
        """Returns the set of pcs covered in the previous cycle or an empty list
        if this is the first cycle."""
        return set(self.get_covered_pcs_state(cycle).get_previous())

    def get_measured_files_state(self, cycle) -> StateFile:
        """Returns the StateFile for measured-files of this cycle."""
        return StateFile('measured-files', self.state_dir, cycle)

    def get_prev_measured_files(self, cycle) -> Set[str]:
        """Returns the set of files measured in the previous cycle or an empty
        list if this is the first cycle."""
        measured_files_state = self.get_measured_files_state(cycle)
        return set(measured_files_state.get_previous())

    def extract_corpus(self, corpus_archive_path, cycle) -> bool:
        """Extract the corpus archive for this cycle if it exists."""
        if not os.path.exists(corpus_archive_path):
            self.logger.warning('Corpus not found: %s.', corpus_archive_path)
            return False

        prev_measured_units = self.get_prev_measured_files(cycle)
        crash_blacklist = self.UNIT_BLACKLIST[self.benchmark]
        unit_blacklist = prev_measured_units.union(crash_blacklist)

        extract_corpus(corpus_archive_path, unit_blacklist, self.corpus_dir)
        return True

    def archive_crashes(self, cycle):
        """Archive this cycle's crashes into cloud bucket."""
        if not os.listdir(self.crashes_dir):
            logs.info('No crashes found for cycle %d.', cycle)
            return

        logs.info('Archiving crashes for cycle %d.', cycle)
        crashes_archive_name = experiment_utils.get_crashes_archive_name(cycle)
        archive = os.path.join(os.path.dirname(self.crashes_dir),
                               crashes_archive_name)
        with tarfile.open(archive, 'w:gz') as tar:
            tar.add(self.crashes_dir,
                    arcname=os.path.basename(self.crashes_dir))
        bucket_path = exp_path.gcs(
            posixpath.join(self.trial_dir, 'crashes', crashes_archive_name))
        gsutil.cp(archive, bucket_path)
        os.remove(archive)

    def update_measured_files(self, cycle):
        """Updates the measured-files.txt file for this trial with
        files measured in this snapshot."""
        current_files = set(os.listdir(self.corpus_dir))
        previous_files = self.get_prev_measured_files(cycle)
        all_files = current_files.union(previous_files)

        measured_files_state = self.get_measured_files_state(cycle)
        measured_files_state.set_current(list(all_files))

        return all_files

    def update_state_for_unchanged_cycle(self, cycle):
        """Update the  covered-pcs and  measured-files state  files so  that the
        states for |cycle| are the same as |cycle - 1|."""
        state_files = [
            self.get_covered_pcs_state(cycle),
            StateFile('measured-files', self.state_dir, cycle)
        ]
        for state_file in state_files:
            prev_state = state_file.get_previous()
            state_file.set_current(prev_state)


def remote_dir_exists(directory: pathlib.Path) -> bool:
    """Does |directory| exist in the CLOUD_EXPERIMENT_BUCKET."""
    return gsutil.ls(exp_path.gcs(directory), must_exist=False)[0] == 0


def measure_trial_coverage(measure_req) -> models.Snapshot:
    """Measure the coverage obtained by |trial_num| on |benchmark| using
    |fuzzer|."""
    initialize_logs()
    set_up_coverage_binary(measure_req.benchmark)
    logger.debug('Measuring trial: %d.', measure_req.trial_id)

    try:
        snapshot = measure_snapshot_coverage(measure_req.fuzzer,
                                             measure_req.benchmark,
                                             measure_req.trial_id,
                                             measure_req.cycle)
    except Exception:  # pylint: disable=broad-except
        logger.error('Error measuring cycle.',
                     extras={
                         'fuzzer': measure_req.fuzzer,
                         'benchmark': measure_req.benchmark,
                         'trial_id': str(measure_req.trial_id),
                         'cycle': str(measure_req.cycle),
                     })
        return None
    logger.debug('Done measuring trial: %d.', measure_req.trial_id)
    # TODO(metzman): Figure out if we want to allow measuring of more than one
    # snapshot per requests.
    return snapshot


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
        snapshot_measurer.update_state_for_unchanged_cycle(cycle)
        covered_pcs = snapshot_measurer.get_prev_covered_pcs(cycle)
        return models.Snapshot(time=this_time,
                               trial_id=trial_num,
                               edges_covered=len(covered_pcs))

    corpus_archive_dst = os.path.join(
        snapshot_measurer.trial_dir, 'corpus',
        experiment_utils.get_corpus_archive_name(cycle))
    corpus_archive_src = exp_path.gcs(corpus_archive_dst)

    corpus_archive_dir = os.path.dirname(corpus_archive_dst)
    if not os.path.exists(corpus_archive_dir):
        os.makedirs(corpus_archive_dir)
    if filestore_utils.cp(corpus_archive_src,
                          corpus_archive_dst,
                          expect_zero=False,
                          write_to_stdout=False)[0] != 0:
        snapshot_logger.warning('Corpus not found for cycle: %d.', cycle)
        # No extra state to save.
        return None

    snapshot_measurer.initialize_measurement_dirs()
    snapshot_measurer.extract_corpus(corpus_archive_dst, cycle)
    # Don't keep corpus archives around longer than they need to be.
    os.remove(corpus_archive_dst)

    # Get the coverage of the new corpus units.
    snapshot_measurer.run_cov_new_units()
    all_pcs = snapshot_measurer.merge_new_pcs(cycle)
    snapshot = models.Snapshot(time=this_time,
                               trial_id=trial_num,
                               edges_covered=len(all_pcs))

    # Record the new corpus files.
    snapshot_measurer.update_measured_files(cycle)

    # Archive crashes directory.
    snapshot_measurer.archive_crashes(cycle)

    measuring_time = round(time.time() - measuring_start_time, 2)
    snapshot_logger.info('Measured cycle: %d in %d seconds.', cycle,
                         measuring_time)
    return snapshot


def set_up_coverage_binary(benchmark):
    """Set up coverage binaries for |benchmark|."""
    # TODO(metzman): Should we worry about disk space on workers?
    initialize_logs()
    coverage_binaries_dir = build_utils.get_coverage_binaries_dir()
    benchmark_coverage_binary_dir = coverage_binaries_dir / benchmark
    if os.path.exists(benchmark_coverage_binary_dir):
        return

    os.mkdir(benchmark_coverage_binary_dir)
    archive_name = 'coverage-build-%s.tar.gz' % benchmark
    cloud_bucket_archive_path = exp_path.gcs(coverage_binaries_dir /
                                             archive_name)
    gsutil.cp(cloud_bucket_archive_path,
              str(benchmark_coverage_binary_dir),
              write_to_stdout=False)
    archive_path = benchmark_coverage_binary_dir / archive_name
    with tarfile.open(archive_path, 'r:gz') as tar:
        tar.extractall(benchmark_coverage_binary_dir)
    os.remove(archive_path)


def get_coverage_binary(benchmark: str) -> str:
    """Get the coverage binary for benchmark."""
    coverage_binaries_dir = build_utils.get_coverage_binaries_dir()
    fuzz_target = benchmark_utils.get_fuzz_target(benchmark)
    return fuzzer_utils.get_fuzz_target_binary(coverage_binaries_dir /
                                               benchmark,
                                               fuzz_target_name=fuzz_target)
