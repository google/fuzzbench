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
import subprocess
import tarfile
import tempfile
import time
from typing import List, Set

from common import benchmark_utils
from common import experiment_path as exp_path
from common import experiment_utils
from common import filesystem
from common import filestore_utils
from common import fuzzer_utils
from common import logs
from common import utils
from database import models
from experiment.build import build_utils
from experiment.measurer import run_coverage
from third_party import sancov

logger = logs.Logger('measure_worker')  # pylint: disable=invalid-name

SnapshotMeasureRequest = collections.namedtuple(
    'SnapshotMeasureRequest', ['fuzzer', 'benchmark', 'trial_id', 'cycle'])

SnapshotMeasureResponse = collections.namedtuple(
    'SnapshotMeasureResponse', ['snapshot', 'has_more'])


def initialize_logs():
    """Initialize logs. This must be called on process start."""
    logs.initialize(
        default_extras={
            'component': 'worker',
            'subcomponent': 'measurer',
            'experiment': experiment_utils.get_experiment_name()
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

        try:
            result = filestore_utils.cat(previous_state_file_bucket_path)
        except subprocess.CalledProcessError:
            return []

        return json.loads(result.output)

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
            filestore_utils.cp(temp_file.name, state_file_bucket_path)


def get_unchanged_cycles(fuzzer, benchmark, trial_num):
    trial_dir = experiment_utils.get_trial_dir(
        fuzzer, benchmark, trial_num)
    unchanged_cycles_filestore_path = posixpath.join(trial_dir, 'results',
                                                     'unchanged-cycles')
    with tempfile.TemporaryDirectory() as temp_dir:
        unchanged_cycles_path = os.path.join(temp_dir, 'unchanged-cycles')
        cp_result = filestore_utils.cp(
            unchanged_cycles_filestore_path, unchanged_cycles_path, must_exist=False)
        if cp_result.retcode != 0:
            logger.info('Unable to copy temporary unchanged-cycles.')
            return []

        return [int(cycle) for cycle in
                filesystem.read(unchanged_cycles_path).splitlines()]


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
        unchanged_cycles = get_unchanged_cycles(
            self.fuzzer, self.benchmark, self.trial_num)
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
        filestore_utils.cp(archive, bucket_path)
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
            self.get_measured_files_state(cycle),
            StateFile('measured-files', self.state_dir, cycle)
        ]
        for state_file in state_files:
            prev_state = state_file.get_previous()
            state_file.set_current(prev_state)

    def has_more(self, cycle, max_cycle):
        if cycle == max_cycle:
            return False


def measure_trial_coverage(measure_req) -> models.Snapshot:
    """Measure the coverage obtained by |trial_num| on |benchmark| using
    |fuzzer|."""
    initialize_logs()

    try:
        set_up_coverage_binary(measure_req.benchmark)
        logger.debug('Measuring trial: %d.', measure_req.trial_id)
        measure_response = measure_snapshot_coverage(measure_req)
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
    return measure_response


def copy_cycle_corpus_archive(self, cycle):
    corpus_archive_dst = os.path.join(
        self.trial_dir, 'corpus',
        experiment_utils.get_corpus_archive_name(cycle))
    corpus_archive_src = exp_path.gcs(corpus_archive_dst)

    corpus_archive_dir = os.path.dirname(corpus_archive_dst)
    if not os.path.exists(corpus_archive_dir):
        os.makedirs(corpus_archive_dir)

    try:
        filestore_utils.cp(corpus_archive_src, corpus_archive_dst)
    except subprocess.CalledProcessError:
        # No extra state to save.
        return None

    return corpus_archive_dst


def _initiailize_snapshot_logger(measure_req):
    snapshot_logger = logs.Logger('measurer',
                                  default_extras={
                                      'fuzzer': measure_req.fuzzer,
                                      'benchmark': meaure_req.benchmark,
                                      'trial_id': str(measure_req.trial_num),
                                      'cycle': str(measure_req.cycle),
                                  })
    return snapshot_logger


def measure_unchanged_cycle(measure_req, snapshot_measurer):
    snapshot_measurer.update_state_for_unchanged_cycle(measure_req.cycle)
    covered_pcs = snapshot_measurer.get_prev_covered_pcs(measure_req.cycle)
    return create_measure_response(measure_req, len(covered_pcs))


def measure_snapshot_coverage(measure_req) -> models.Snapshot:
    """Measure coverage of the snapshot for |cycle| for |trial_num| of |fuzzer|
    and |benchmark|."""
    snapshot_logger = _initialize_snapshot_logger(measure_req)
    snapshot_logger.info('Measuring cycle: %d.', measure_req.cycle)
    snapshot_measurer = SnapshotMeasurer(measure_req.fuzzer, measure_req.benchmark, meaure_req.trial_num,
                                         snapshot_logger)

    response = _measure_snapshot_coverage(snapshot_measurer, measure_req)
    measuring_time = round(time.time() - measuring_start_time, 2)
    snapshot_logger.info(
        'Responding to measure request took %d seconds.', measuring_time)
    return response


def _measure_snapshot_coverage(snapshot_measurer, measure_req) -> SnapshotMeasureResponse:
    if snapshot_measurer.is_cycle_unchanged(measure_req.cycle):
        return measure_unchanged_cycle(measure_req, snapshot_measurer)

    corpus_archive_path = copy_cycle_corpus_archive(measure_req.cycle)
    if corpus_archive_path:
        # Get the coverage of the new corpus units.
        return measure_cycle_units(
            snapshot_measurer, measure_req, corpus_archive_path)

    snapshot_measurer.logger.info('Could not copy corpus for cycle: %d.',
                                  measure_req.cycle)

    next_measure_req = find_next_snapshot_to_measure(measure_req)
    if not next_measure_req:
        return create_unable_to_measure_response()
    update_states_for_next_req(next_measure_req)
    return _measure_snapshot_coverage(snapshot_measurer, measure_req)


def update_states_for_next_req(snapshot_measurer, next_measure_req):



CORPUS_ARCHIVE_CYCLE_REGEX = re.compile('.*corpus-archive-(\d{4}).tar.gz$')

def get_corpus_archive_cycle_num(archive):
    return CORPUS_ARCHIVE_CYCLE_REGEX.match(archive)


def get_cycles_with_corpus_archives(fuzzer, benchmark, trial_num):
    trial_dir = experiment_utils.get_trial_dir(
        fuzzer, benchmark, trial_num)
    archives = filestore_utils.ls(trial_dir).output.splitlines()
    matches = [get_corpus_archive_cycle_num(archive) for archive in archives]
    cycles = [int(match.groups(1)[0]) for match in matches]
    return cycles


def find_next_snapshot_to_measure(measure_req):
    if measure_req.cycle == 1:
        return None
    # Get all cycles that are possible to measure. This means cycles that are
    # reported as unchanged or those that have a corpus archive.
    all_cycles = get_unchanged_cycles(
        measure_req.fuzzer, measure_req.benchmark, measure_req.trial_num)
    archived_cycles = get_cycles_with_corpus_archives(
        measure_req.fuzzer, measure_req.benchmark, measure_req.trial_num)
    all_cycles.extend(archived_cycles)

    # Get cycles that are worth measuring. Since we wouldn't have a measure_req
    # for cycle N unless N-1 was measured or N=1 this means a cycle where N > 1.
    # To deal with the very remote possibility of race conditions, include N=1
    # in eligible cycles.
    eligible_cycles = [cycle for cycle in all_cycles
                       if cycle <= measure_req.cycle]
    if not eligible_cycles:
        return None

    # Return a request for the next snapshot we want to measure, aka the minimum
    # of eligible ones.
    next_cycle = min(eligible_cycles)
    next_req = SnapshotMeasureRequest(
        measure_req.fuzzer, measure_req.benchmark, measure_req.trial_num,
        next_cycle)
    return next_req


def create_unable_to_measure_response():
    return create_measure_response(
        measure_req=None, num_edges=0, has_more=False)


def create_measure_response(measure_req, num_edges, has_more=True):
    if not has_more:
        return SnapshotMeasureResponse(None, False)

    cycle_time = measure_req.cycle * experiment_utils.get_snapshot_seconds()
    snapshot = models.Snapshot(time=cycle_time,
                               trial_id=trial_num,
                               edges_covered=len(cycle_pcs))
    return SnapshotMeasureResponse(snapshot, True)

def measure_cycle_units(snapshot_measurer, measure_req, corpus_archive_path):
    # Prepare to get coverage of new units.
    snapshot_measurer.initialize_measurement_dirs()
    snapshot_measurer.extract_corpus(corpus_archive_path, measure_req.cycle)
    # Don't keep corpus archives around longer than they need to be.
    os.remove(corpus_archive_path)

    snapshot_measurer.run_cov_new_units()
    cycle_pcs = snapshot_measurer.merge_new_pcs(measure_req.cycle)
    # Record the new corpus files.
    snapshot_measurer.update_measured_files(measure_req.cycle)

    # Archive crashes directory.
    snapshot_measurer.archive_crashes(measure_req.cycle)
    return create_measure_response(measure_req, len(cycle_pcs))


def set_up_coverage_binary(benchmark):
    """Set up coverage binaries for |benchmark|."""
    # TODO(metzman): Should we worry about disk space on workers?
    initialize_logs()
    coverage_binaries_dir = build_utils.get_coverage_binaries_dir()
    benchmark_coverage_binary_dir = coverage_binaries_dir / benchmark
    if os.path.exists(benchmark_coverage_binary_dir):
        return

    filesystem.create_directory(benchmark_coverage_binary_dir)
    archive_name = 'coverage-build-%s.tar.gz' % benchmark
    cloud_bucket_archive_path = exp_path.gcs(coverage_binaries_dir /
                                             archive_name)
    filestore_utils.cp(cloud_bucket_archive_path,
                       str(benchmark_coverage_binary_dir))
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
