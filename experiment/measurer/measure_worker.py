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
import re
import tarfile
import tempfile
import time
from typing import Optional, List, Set

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

logger = None

SnapshotMeasureRequest = collections.namedtuple(
    'SnapshotMeasureRequest', ['fuzzer', 'benchmark', 'trial_id', 'cycle'])

SnapshotMeasureResponse = collections.namedtuple('SnapshotMeasureResponse',
                                                 ['snapshot', 'next_cycle'])

MEASURED_FILES_STATE_NAME = 'measured-files'
COVERED_PCS_STATE_NAME = 'covered-pcs'

CORPUS_ARCHIVE_CYCLE_REGEX = re.compile(r'.*\/corpus-archive-(\d{4})\.tar\.gz$')


def _initialize_logger(measure_req: SnapshotMeasureRequest):
    """Initialize logs. This must be called on process start."""
    logs.initialize(
        default_extras={
            'component': 'worker',
            'subcomponent': 'measurer',
            'experiment': experiment_utils.get_experiment_name(),
            'fuzzer': measure_req.fuzzer,
            'benchmark': measure_req.benchmark,
            'trial_id': str(measure_req.trial_id),
            'cycle': str(measure_req.cycle),
        })

    return logs.Logger('measure_worker')


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
        return exp_path.filestore(pathlib.Path(state_file_path))

    def _get_previous_cycle_state(self) -> list:
        """Returns the state from the previous cycle. Returns [] if |self.cycle|
        is 1."""
        if self.cycle == 1:
            return []

        previous_state_file_bucket_path = (
            self._get_bucket_cycle_state_file_path(self.cycle - 1))

        result = filestore_utils.cat(previous_state_file_bucket_path,
                                     expect_zero=False)
        if result.retcode != 0:
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


def get_unchanged_cycles(fuzzer: str, benchmark: str,
                         trial_id: int) -> List[int]:
    """Returns a list of unchanged cycles for |fuzzer|, |benchmark|, and
    |trial_id| or an empty list if there is no unchanged-cycles file for
    |trial_id|."""
    trial_dir = get_trial_work_dir(fuzzer, benchmark, trial_id)
    unchanged_cycles_filestore_path = exp_path.filestore(
        posixpath.join(trial_dir, 'results', 'unchanged-cycles'))
    with tempfile.TemporaryDirectory() as temp_dir:
        unchanged_cycles_path = os.path.join(temp_dir, 'unchanged-cycles')
        cp_result = filestore_utils.cp(unchanged_cycles_filestore_path,
                                       unchanged_cycles_path,
                                       expect_zero=False)
        if cp_result.retcode != 0:
            return []

        return [
            int(cycle)
            for cycle in filesystem.read(unchanged_cycles_path).splitlines()
        ]


def get_trial_work_dir(fuzzer: str, benchmark: str, trial_id: int):
    """Get the path to the trial directory in WORK."""
    work_dir = experiment_utils.get_work_dir()
    benchmark_fuzzer_trial_dir = experiment_utils.get_trial_dir(
        fuzzer, benchmark, trial_id)
    trial_dir = os.path.join(work_dir, 'experiment-folders',
                             benchmark_fuzzer_trial_dir)
    return trial_dir


class SnapshotMeasurer:  # pylint: disable=too-many-instance-attributes
    """Class used for storing details needed to measure coverage of a particular
    trial."""

    UNIT_BLACKLIST = collections.defaultdict(set)

    def __init__(self, fuzzer: str, benchmark: str, trial_id: int):
        self.fuzzer = fuzzer
        self.benchmark = benchmark
        self.trial_id = trial_id
        benchmark_fuzzer_trial_dir = experiment_utils.get_trial_dir(
            fuzzer, benchmark, trial_id)
        work_dir = experiment_utils.get_work_dir()
        measurement_dir = os.path.join(work_dir, 'measurement-folders',
                                       benchmark_fuzzer_trial_dir)
        self.corpus_dir = os.path.join(measurement_dir, 'corpus')

        self.crashes_dir = os.path.join(measurement_dir, 'crashes')
        self.sancov_dir = os.path.join(measurement_dir, 'sancovs')
        self.state_dir = os.path.join(measurement_dir, 'state')
        self.trial_dir = get_trial_work_dir(fuzzer, benchmark, trial_id)

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

    def save_measured_files_state(self, cycle):
        """Saves the measured-files StateFile for this cycle with files
        measured in this cycle and previous ones."""
        current_files = set(os.listdir(self.corpus_dir))
        previous_files = self.get_prev_measured_files(cycle)
        all_files = current_files.union(previous_files)

        measured_files_state = self.get_measured_files_state(cycle)
        measured_files_state.set_current(list(all_files))

        return all_files

    def save_covered_pcs_state(self, cycle: int,
                               expect_sancovs: bool = True) -> List[str]:
        """Merge new pcs into the previously covered pcs. Update the state to
        reflect this and return the list of all covered pcs."""
        prev_pcs = self.get_prev_covered_pcs(cycle)
        sancov_files = glob.glob(os.path.join(self.sancov_dir, '*.sancov'))
        if sancov_files:
            new_pcs = set(sancov.GetPCs(sancov_files))
        else:
            if expect_sancovs:
                logger.error('No sancov files.')
            new_pcs = set()

        # Sort so that file doesn't change if PCs are unchanged.
        all_pcs = sorted(prev_pcs.union(new_pcs))
        covered_pcs_state = self.get_covered_pcs_state(cycle)
        covered_pcs_state.set_current(all_pcs)
        return all_pcs

    def is_cycle_unchanged(self, cycle: int) -> bool:
        """Returns True if |cycle| is unchanged according to the
        unchanged-cycles file. This file is written to by the trial's runner."""
        unchanged_cycles = get_unchanged_cycles(self.fuzzer, self.benchmark,
                                                self.trial_id)
        return cycle in unchanged_cycles

    def get_covered_pcs_state(self, cycle: int) -> StateFile:
        """Returns the StateFile for covered-pcs of this |cycle|."""
        return StateFile(COVERED_PCS_STATE_NAME, self.state_dir, cycle)

    def get_prev_covered_pcs(self, cycle: int) -> Set[str]:
        """Returns the set of pcs covered in the previous cycle or an empty list
        if this is the first cycle."""
        return set(self.get_covered_pcs_state(cycle).get_previous())

    def get_measured_files_state(self, cycle) -> StateFile:
        """Returns the StateFile for measured-files of this cycle."""
        return StateFile(MEASURED_FILES_STATE_NAME, self.state_dir, cycle)

    def get_prev_measured_files(self, cycle) -> Set[str]:
        """Returns the set of files measured in the previous cycle or an empty
        list if this is the first cycle."""
        measured_files_state = self.get_measured_files_state(cycle)
        return set(measured_files_state.get_previous())

    def extract_corpus(self, corpus_archive_path, cycle) -> bool:
        """Extract the corpus archive for this cycle if it exists."""
        prev_measured_units = self.get_prev_measured_files(cycle)
        crash_blacklist = self.UNIT_BLACKLIST[self.benchmark]
        unit_blacklist = prev_measured_units.union(crash_blacklist)

        extract_corpus(corpus_archive_path, unit_blacklist, self.corpus_dir)
        return True

    def archive_crashes(self, cycle):
        """Archive this cycle's crashes into cloud bucket."""
        if not os.listdir(self.crashes_dir):
            return

        crashes_archive_name = experiment_utils.get_crashes_archive_name(cycle)
        archive = os.path.join(os.path.dirname(self.crashes_dir),
                               crashes_archive_name)
        with tarfile.open(archive, 'w:gz') as tar:
            tar.add(self.crashes_dir,
                    arcname=os.path.basename(self.crashes_dir))
        bucket_path = exp_path.filestore(
            posixpath.join(self.trial_dir, 'crashes', crashes_archive_name))
        filestore_utils.cp(archive, bucket_path)
        os.remove(archive)

    def get_cycle_corpus(self, cycle):
        """Extracts the corpus for |cycle|. Returns True on success."""
        corpus_archive_dst = os.path.join(
            self.trial_dir, 'corpus',
            experiment_utils.get_corpus_archive_name(cycle))
        corpus_archive_src = exp_path.filestore(corpus_archive_dst)

        corpus_archive_dir = os.path.dirname(corpus_archive_dst)
        if not os.path.exists(corpus_archive_dir):
            os.makedirs(corpus_archive_dir)

        cp_result = filestore_utils.cp(corpus_archive_src,
                                       corpus_archive_dst,
                                       expect_zero=False)
        if cp_result.retcode != 0:
            logger.debug('Could not copy archive for cycle.')
            return False

        self.extract_corpus(corpus_archive_dst, cycle)
        # Don't keep corpus archives around longer than they need to be.
        os.remove(corpus_archive_dst)
        return True

    def save_state(self, cycle, cycle_changed):
        """Save state for |cycle| and return the edges covered by the cycle."""
        self.archive_crashes(cycle)
        self.save_measured_files_state(cycle)
        cycle_edges = self.save_covered_pcs_state(cycle,
                                                  expect_sancovs=cycle_changed)
        return cycle_edges


def create_measure_response(measure_req, cycle_pcs):
    """Returns a SnapshotMeasureResponse for |measure_req.cycle| containing
    |cycle_pcs|."""
    cycle_time = measure_req.cycle * experiment_utils.get_snapshot_seconds()
    snapshot = models.Snapshot(time=cycle_time,
                               trial_id=measure_req.trial_id,
                               edges_covered=len(cycle_pcs))
    return SnapshotMeasureResponse(snapshot, None)


def measure_snapshot_coverage(measure_req: SnapshotMeasureRequest
                             ) -> Optional[SnapshotMeasureResponse]:
    """Try to do the measurement asked for by |measure_req| and return a
    response indictating the result of the measurement."""
    # Set up things for logging.
    logger.info('Measuring cycle: %d.', measure_req.cycle)
    measuring_start_time = time.time()

    snapshot_measurer = SnapshotMeasurer(measure_req.fuzzer,
                                         measure_req.benchmark,
                                         measure_req.trial_id)
    snapshot_measurer.initialize_measurement_dirs()
    # If the double negative is confusing, think of this condition "if cycle is
    # not static" where a cycle is "static" if it is the same as the previous.
    cycle_changed = not snapshot_measurer.is_cycle_unchanged(measure_req.cycle)

    if cycle_changed:
        # Try to measure the new units if the cycle changed from last time.
        if not snapshot_measurer.get_cycle_corpus(measure_req.cycle):

            # If we can't get the corpus, then we can't measure this cycle now.
            logger.info('Cannot measure cycle now.')
            return None
        snapshot_measurer.run_cov_new_units()

    # Get the results of the measurement, the edges and the crashes.
    cycle_edges = snapshot_measurer.save_state(measure_req.cycle, cycle_changed)
    response = create_measure_response(measure_req, cycle_edges)

    # Log that we are done.
    measuring_time = round(time.time() - measuring_start_time, 2)
    logger.info('Measuring cycle: %d took %d seconds.', measure_req.cycle,
                measuring_time)

    return response


def measure_trial_coverage(measure_req: SnapshotMeasureRequest
                          ) -> SnapshotMeasureResponse:
    """Measure the coverage obtained by |trial_id| on |benchmark| using
    |fuzzer|."""
    # TODO(metzman): Figure out if we want to allow measuring of more than
    # one snapshot per requests.
    global logger
    logger = _initialize_logger(measure_req)
    try:
        set_up_coverage_binary(measure_req.benchmark)
        measure_resp = measure_snapshot_coverage(measure_req)
        if measure_resp:
            return measure_resp
    except Exception:  # pylint: disable=broad-except
        logger.error('Error measuring cycle.',
                     extras={
                         'fuzzer': measure_req.fuzzer,
                         'benchmark': measure_req.benchmark,
                         'trial_id': str(measure_req.trial_id),
                         'cycle': str(measure_req.cycle),
                     })
    return handle_failed_measure(measure_req)


def get_trial_corpus_filestore_path(measure_req: SnapshotMeasureRequest) -> str:
    """Returns the filestore path where corpus archives are stored for the trial
    specified by measure_req."""
    trial_bucket_dir = experiment_utils.get_trial_bucket_dir(
        measure_req.fuzzer, measure_req.benchmark, measure_req.trial_id)
    return posixpath.join(trial_bucket_dir, 'corpus')


def get_cycles_with_corpus_archives(measure_req: SnapshotMeasureRequest
                                   ) -> List[int]:
    """Returns a list of cycles for this trial with corpus archives."""
    archives_path = get_trial_corpus_filestore_path(measure_req)
    ls_result = filestore_utils.ls(archives_path, must_exist=False)
    if ls_result.retcode != 0:
        return []
    archives = ls_result.output.splitlines()
    matches = [
        CORPUS_ARCHIVE_CYCLE_REGEX.match(archive) for archive in archives
    ]
    return [int(match.groups(1)[0]) for match in matches if match is not None]


def handle_failed_measure(measure_req: SnapshotMeasureRequest
                         ) -> SnapshotMeasureResponse:
    """This function deals with the case when a request to measure a given cycle
    (|measure_req.cycle|), cannot be completed (because it is not reported as
    unchanged and there isn't a corpus archive for this cycle). In most cases,
    the request has come too early and the this function returns a
    SnapshotMeasureResponse indicating that the request can be tried again.
    However, in some cases, a fuzzer will freeze the machine it is running on
    and cycle M might not be measurable but cycle N (where N > M) is measurable
    (because the snapshotting code in the runner didn't get to run until N has
    finished). When that is the case this function returns a reponse that
    indicates M should be measured next (and that measuring N should not be
    retried) and does any necessary setup for state files so that M can be
    measured (using update_states_for_skipped_cycles)."""
    # Get all cycles that are possible to measure. This means cycles that are
    # reported as unchanged or those that have a corpus archive.
    all_cycles = get_unchanged_cycles(measure_req.fuzzer, measure_req.benchmark,
                                      measure_req.trial_id)
    archived_cycles = get_cycles_with_corpus_archives(measure_req)
    all_cycles.extend(archived_cycles)

    # Get cycles that are worth measuring. Since we wouldn't have a measure_req
    # for cycle N unless N-1 was measured or N=1 this means a cycle where N > 1.
    # To deal with the very remote possibility of race conditions, include N=1
    # in eligible cycles.
    eligible_cycles = [
        cycle for cycle in all_cycles if cycle >= measure_req.cycle
    ]

    def create_response(next_cycle):
        return SnapshotMeasureResponse(None, next_cycle)

    if not eligible_cycles:
        return create_response(None)

    # Return a request for the next snapshot we want to measure, aka the minimum
    # of eligible ones.
    next_cycle = min(eligible_cycles)
    update_states_for_skipped_cycles(measure_req, next_cycle)
    return create_response(next_cycle)


def update_states_for_skipped_cycles(measure_req: SnapshotMeasureRequest,
                                     next_cycle: int):
    """This function is called when |measure_req.cycle| cannot be measured
    (because it is not unchanged and there is no corpus-archive) but
    |next_cycle| can be (because there is one of these things for |next_cycle|).
    An invariant of this system is that if there is a measure request for
    |measure_req.cycle| then |measure_req.cycle-1| was measured. Therefore, this
    function updates the states of the cycles in between |measure_req.cycle| and
    |next_cycle-1| so that next_cycle can be measured using the state from
    |next_cycle-1|."""
    assert measure_req.cycle >= 2
    state_dict = {}

    def update_cycle_states(cycle, temp_dir):
        """Update the states for |cycle| with the states in |state_dict|."""
        for state_name, last_state in state_dict.items():
            cycle_state = StateFile(state_name, temp_dir, cycle)
            cycle_state.set_current(last_state)

    with tempfile.TemporaryDirectory() as temp_dir:
        # Get the last states saved.
        for state_name in [MEASURED_FILES_STATE_NAME, COVERED_PCS_STATE_NAME]:
            state_dict[state_name] = StateFile(
                state_name, temp_dir, measure_req.cycle).get_previous()

        # Set all the states until next_cycle to the last ones we have.
        for cycle in range(measure_req.cycle, next_cycle):
            update_cycle_states(cycle, temp_dir)


def set_up_coverage_binary(benchmark: str):
    """Set up coverage binaries for |benchmark|."""
    # TODO(metzman): Should we worry about disk space on workers?
    coverage_binaries_dir = build_utils.get_coverage_binaries_dir()
    benchmark_coverage_binary_dir = coverage_binaries_dir / benchmark
    if os.path.exists(benchmark_coverage_binary_dir):
        return

    filesystem.create_directory(benchmark_coverage_binary_dir)
    archive_name = 'coverage-build-%s.tar.gz' % benchmark
    cloud_bucket_archive_path = exp_path.filestore(coverage_binaries_dir /
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
