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
"""Module for measuring snapshots from trial runners."""
import collections
import glob
import os
import pathlib
import posixpath
import tarfile
import time
from typing import List, Set

from common import benchmark_utils
from common import experiment_utils
from common import experiment_path as exp_path
from common import filesystem
from common import fuzzer_utils
from common import gsutil
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
        trial_name = 'trial-' + str(self.trial_num)
        self.benchmark_fuzzer_trial_dir = os.path.join(self.benchmark,
                                                       self.fuzzer, trial_name)
        work_dir = experiment_utils.get_work_dir()
        measurement_dir = os.path.join(work_dir, 'measurement-folders',
                                       self.benchmark_fuzzer_trial_dir)
        self.corpus_dir = os.path.join(measurement_dir, 'corpus')

        self.crashes_dir = os.path.join(measurement_dir, 'crashes')
        self.sancov_dir = os.path.join(measurement_dir, 'sancovs')
        self.report_dir = os.path.join(measurement_dir, 'reports')
        self.trial_dir = os.path.join(work_dir, 'experiment-folders',
                                      '%s-%s' % (benchmark, fuzzer), trial_name)

        # Stores the pcs that have been covered.
        self.covered_pcs_filename = os.path.join(self.report_dir,
                                                 'covered-pcs.txt')

        # Stores the files that have already been measured for a trial.
        self.measured_files_path = os.path.join(self.report_dir,
                                                'measured-files.txt')

        # Used by the runner to signal that there won't be a corpus archive for
        # a cycle because the corpus hasn't changed since the last cycle.
        self.unchanged_cycles_path = os.path.join(self.trial_dir, 'results',
                                                  'unchanged-cycles')

    def initialize_measurement_dirs(self):
        """Initialize directories that will be needed for measuring
        coverage."""
        for directory in [self.corpus_dir, self.sancov_dir, self.crashes_dir]:
            filesystem.recreate_directory(directory)
        filesystem.create_directory(self.report_dir)

    def run_cov_new_units(self):
        """Run the coverage binary on new units."""
        coverage_binary = get_coverage_binary(self.benchmark)
        crashing_units = run_coverage.do_coverage_run(coverage_binary,
                                                      self.corpus_dir,
                                                      self.sancov_dir,
                                                      self.crashes_dir)

        self.UNIT_BLACKLIST[self.benchmark] = (
            self.UNIT_BLACKLIST[self.benchmark].union(set(crashing_units)))

    def merge_new_pcs(self) -> List[str]:
        """Merge new pcs into |self.covered_pcs_filename| and return the list of
        all covered pcs."""

        # Create the covered pcs file if it doesn't exist yet.
        if not os.path.exists(self.covered_pcs_filename):
            filesystem.write(self.covered_pcs_filename, '')

        with open(self.covered_pcs_filename, 'r+') as file_handle:
            current_pcs = set(
                pc.strip() for pc in file_handle.readlines() if pc.strip())
            sancov_files = glob.glob(os.path.join(self.sancov_dir, '*.sancov'))
            if not sancov_files:
                self.logger.error('No sancov files.')
                return list(current_pcs)

            self.logger.info('Sancov files: %s.', str(sancov_files))
            new_pcs = set(sancov.GetPCs(sancov_files))
            all_pcs = sorted(list(current_pcs.union(new_pcs)))
            # Sort so that file doesn't change if PCs are unchanged.
            file_handle.seek(0)
            file_handle.write('\n'.join(all_pcs))
        return all_pcs

    def get_current_pcs(self) -> Set[str]:
        """Get the current pcs covered by a fuzzer."""
        with open(self.covered_pcs_filename) as file_handle:
            current_pcs = set(
                pc.strip() for pc in file_handle.readlines() if pc.strip())
        return current_pcs

    def is_cycle_unchanged(self, cycle: int) -> bool:
        """Returns True if |cycle| is unchanged according to the
        unchanged-cycles file. This file is written to by the trial's runner."""

        def copy_unchanged_cycles_file():
            result = gsutil.cp(exp_path.gcs(self.unchanged_cycles_path),
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
        gcs_path = exp_path.gcs(
            posixpath.join(self.trial_dir, 'crashes', crashes_archive_name))
        gsutil.cp(archive, gcs_path)
        os.remove(archive)

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


def measure_trial_coverage(measure_req) -> models.Snapshot:
    """Measure the coverage obtained by |trial_num| on |benchmark| using
    |fuzzer|."""
    initialize_logs()
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
        current_pcs = snapshot_measurer.get_current_pcs()
        return models.Snapshot(time=this_time,
                               trial_id=trial_num,
                               edges_covered=len(current_pcs))

    corpus_archive_dst = os.path.join(
        snapshot_measurer.trial_dir, 'corpus',
        experiment_utils.get_corpus_archive_name(cycle))
    corpus_archive_src = exp_path.gcs(corpus_archive_dst)

    corpus_archive_dir = os.path.dirname(corpus_archive_dst)
    if not os.path.exists(corpus_archive_dir):
        os.makedirs(corpus_archive_dir)
    if gsutil.cp(corpus_archive_src,
                 corpus_archive_dst,
                 expect_zero=False,
                 write_to_stdout=False)[0] != 0:
        snapshot_logger.warning('Corpus not found for cycle: %d.', cycle)
        return None

    snapshot_measurer.initialize_measurement_dirs()
    snapshot_measurer.extract_corpus(corpus_archive_dst)
    # Don't keep corpus archives around longer than they need to be.
    os.remove(corpus_archive_dst)

    # Get the coverage of the new corpus units.
    snapshot_measurer.run_cov_new_units()
    all_pcs = snapshot_measurer.merge_new_pcs()
    snapshot = models.Snapshot(time=this_time,
                               trial_id=trial_num,
                               edges_covered=len(all_pcs))

    # Record the new corpus files.
    snapshot_measurer.update_measured_files()

    # Archive crashes directory.
    snapshot_measurer.archive_crashes(cycle)

    measuring_time = round(time.time() - measuring_start_time, 2)
    snapshot_logger.info('Measured cycle: %d in %d seconds.', cycle,
                         measuring_time)
    return snapshot


def get_coverage_binary(benchmark: str) -> str:
    """Get the coverage binary for benchmark."""
    coverage_binaries_dir = build_utils.get_coverage_binaries_dir()
    fuzz_target = benchmark_utils.get_fuzz_target(benchmark)
    return fuzzer_utils.get_fuzz_target_binary(coverage_binaries_dir /
                                               benchmark,
                                               fuzz_target_name=fuzz_target)
