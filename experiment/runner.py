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
"""Runs fuzzer for trial."""

from collections import namedtuple
import os
import posixpath
import shlex
import shutil
import subprocess
import sys
import tarfile
import threading
import time
import zipfile

from common import environment
from common import experiment_utils
from common import filesystem
from common import fuzzer_utils
from common import gsutil
from common import logs
from common import new_process
from common import retry
from common import utils

NUM_RETRIES = 3
RETRY_DELAY = 3

FUZZ_TARGET_DIR = '/out'

# This is an optimization to sync corpora only when it is needed. These files
# are temporary files generated during fuzzer runtime and are not related to
# the actual corpora.
EXCLUDE_PATHS = set([
    # AFL excludes.
    '.cur_input',
    '.state',
    'fuzz_bitmap',
    'fuzzer_stats',
    'plot_data',

    # QSYM excludes.
    'bitmap',
])

CORPUS_ELEMENT_BYTES_LIMIT = 1 * 1024 * 1024
SEED_CORPUS_ARCHIVE_SUFFIX = '_seed_corpus.zip'

File = namedtuple('File', ['path', 'modified_time', 'change_time'])


def _clean_seed_corpus(seed_corpus_dir):
    """Moves seed corpus files from sub-directories into the corpus directory
    root. Also, deletes any files that exceed the 1 MB limit."""
    if not os.path.exists(seed_corpus_dir):
        return

    failed_to_move_files = []
    for root, _, files in os.walk(seed_corpus_dir):
        for filename in files:
            file_path = os.path.join(root, filename)

            if os.path.getsize(file_path) > CORPUS_ELEMENT_BYTES_LIMIT:
                os.remove(file_path)
                logs.warning('Removed seed file %s as it exceeds 1 Mb limit.',
                             file_path)
                continue

            sha1sum = utils.file_hash(file_path)
            new_file_path = os.path.join(seed_corpus_dir, sha1sum)
            try:
                shutil.move(file_path, new_file_path)
            except OSError:
                failed_to_move_files.append((file_path, new_file_path))

    if failed_to_move_files:
        logs.error('Failed to move seed corpus files: %s', failed_to_move_files)


def _get_fuzzer_environment():
    """Returns environment to run the fuzzer in (outside virtualenv)."""
    env = os.environ.copy()

    path = env.get('PATH')
    if not path:
        return env

    path_parts = path.split(':')

    # |VIRTUALENV_DIR| is the virtualenv environment that runner.py is running
    # in. Fuzzer dependencies are installed in the system python environment,
    # so need to remove it from |PATH|.
    virtualenv_dir = env.get('VIRTUALENV_DIR')
    if not virtualenv_dir:
        return env

    path_parts_without_virtualenv = [
        p for p in path_parts if not p.startswith(virtualenv_dir)
    ]
    env['PATH'] = ':'.join(path_parts_without_virtualenv)
    return env


def get_clusterfuzz_seed_corpus_path(fuzz_target_path):
    """Returns the path of the clusterfuzz seed corpus archive if one exists.
    Otherwise returns None."""
    fuzz_target_without_extension = os.path.splitext(fuzz_target_path)[0]
    seed_corpus_path = (fuzz_target_without_extension +
                        SEED_CORPUS_ARCHIVE_SUFFIX)
    return seed_corpus_path if os.path.exists(seed_corpus_path) else None


def _unpack_clusterfuzz_seed_corpus(fuzz_target_path, corpus_directory):
    """If a clusterfuzz seed corpus archive is available, unpack it into the
    corpus directory if it exists. Copied from unpack_seed_corpus in
    engine_common.py in ClusterFuzz.
    """
    seed_corpus_archive_path = get_clusterfuzz_seed_corpus_path(
        fuzz_target_path)

    if not seed_corpus_archive_path:
        return

    with zipfile.ZipFile(seed_corpus_archive_path) as zip_file:
        # Unpack seed corpus recursively into the root of the main corpus
        # directory.
        idx = 0
        for seed_corpus_file in zip_file.infolist():
            if seed_corpus_file.filename.endswith('/'):
                # Ignore directories.
                continue

            # Allow callers to opt-out of unpacking large files.
            if seed_corpus_file.file_size > CORPUS_ELEMENT_BYTES_LIMIT:
                continue

            output_filename = '%016d' % idx
            output_file_path = os.path.join(corpus_directory, output_filename)
            zip_file.extract(seed_corpus_file, output_file_path)
            idx += 1

    logs.info('Unarchived %d files from seed corpus %s.', idx,
              seed_corpus_archive_path)


def run_fuzzer(max_total_time, log_filename):
    """Runs the fuzzer using its script. Logs stdout and stderr of the fuzzer
    script to |log_filename| if provided."""
    input_corpus = environment.get('SEED_CORPUS_DIR')
    output_corpus = environment.get('OUTPUT_CORPUS_DIR')
    fuzz_target_name = environment.get('FUZZ_TARGET')
    target_binary = fuzzer_utils.get_fuzz_target_binary(FUZZ_TARGET_DIR,
                                                        fuzz_target_name)
    if not target_binary:
        logs.error('Fuzz target binary not found.')
        return

    _unpack_clusterfuzz_seed_corpus(target_binary, input_corpus)
    _clean_seed_corpus(input_corpus)

    if max_total_time is None:
        logs.warning('max_total_time is None. Fuzzing indefinitely.')

    runner_niceness = environment.get('RUNNER_NICENESS', 0)

    try:
        # Because the runner is launched at a higher priority,
        # set it back to the default(0) for fuzzing processes.
        command = [
            'nice', '-n',
            str(0 - runner_niceness), 'python3', '-u', '-c',
            ('import fuzzer; '
             'fuzzer.fuzz('
             "'{input_corpus}', '{output_corpus}', '{target_binary}')").format(
                 input_corpus=shlex.quote(input_corpus),
                 output_corpus=shlex.quote(output_corpus),
                 target_binary=shlex.quote(target_binary))
        ]
        # Write output to stdout if user is fuzzing from command line.
        # Otherwise, write output to the log file.
        if environment.get('FUZZ_OUTSIDE_EXPERIMENT'):
            new_process.execute(command,
                                timeout=max_total_time,
                                kill_children=True,
                                env=_get_fuzzer_environment())
        else:
            with open(log_filename, 'wb') as log_file:
                new_process.execute(command,
                                    timeout=max_total_time,
                                    output_file=log_file,
                                    kill_children=True,
                                    env=_get_fuzzer_environment())

    except subprocess.CalledProcessError:
        logs.error('Fuzz process returned nonzero.')


class TrialRunner:  # pylint: disable=too-many-instance-attributes
    """Class for running a trial."""

    def __init__(self):
        benchmark_fuzzer_directory = '%s-%s' % (environment.get(
            'BENCHMARK'), environment.get('FUZZER_VARIANT_NAME'))
        if not environment.get('FUZZ_OUTSIDE_EXPERIMENT'):
            bucket = environment.get('CLOUD_EXPERIMENT_BUCKET')
            experiment_name = environment.get('EXPERIMENT')
            trial = 'trial-%d' % environment.get('TRIAL_ID')
            self.gcs_sync_dir = posixpath.join(bucket, experiment_name,
                                               'experiment-folders',
                                               benchmark_fuzzer_directory,
                                               trial)
            # Clean the directory before we use it.
            gsutil.rm(self.gcs_sync_dir, force=True)
        else:
            self.gcs_sync_dir = None

        self.cycle = 1
        self.corpus_dir = 'corpus'
        self.corpus_archives_dir = 'corpus-archives'
        self.results_dir = 'results'
        self.unchanged_cycles_path = os.path.join(self.results_dir,
                                                  'unchanged-cycles')
        self.last_sync_time = None
        self.corpus_dir_contents = set()

    def initialize_directories(self):
        """Initialize directories needed for the trial."""
        directories = [
            self.corpus_dir,
            self.corpus_archives_dir,
            self.results_dir,
        ]

        for directory in directories:
            filesystem.recreate_directory(directory)

    def conduct_trial(self):
        """Conduct the benchmarking trial."""
        self.initialize_directories()
        log_file = os.path.join(self.results_dir, 'fuzzer-log.txt')

        logs.info('Starting trial.')

        max_total_time = environment.get('MAX_TOTAL_TIME')
        args = (max_total_time, log_file)
        fuzz_thread = threading.Thread(target=run_fuzzer, args=args)
        fuzz_thread.start()

        if environment.get('FUZZ_OUTSIDE_EXPERIMENT'):
            # Hack so that the fuzz_thread has some time to fail if something is
            # wrong. Without this we will sleep for a long time before checking
            # if the fuzz thread is alive.
            time.sleep(5)

        while fuzz_thread.is_alive():
            self.sleep_until_next_sync()
            self.do_sync()
            self.cycle += 1

        logs.info('Doing final sync.')
        self.do_sync(final_sync=True)
        fuzz_thread.join()

    def sleep_until_next_sync(self):
        """Sleep until it is time to do the next sync."""
        if self.last_sync_time is not None:
            next_sync_time = (self.last_sync_time +
                              experiment_utils.SNAPSHOT_PERIOD)
            sleep_time = next_sync_time - time.time()
            if sleep_time < 0:
                # Log error if a sync has taken longer than SNAPSHOT_PERIOD and
                # messed up our time synchronization.
                logs.warning('Sleep time on cycle %d is %d', self.cycle,
                             sleep_time)
                sleep_time = 0
        else:
            sleep_time = experiment_utils.SNAPSHOT_PERIOD
        logs.debug('Sleeping for %d seconds.', sleep_time)
        time.sleep(sleep_time)
        # last_sync_time is recorded before the sync so that each sync happens
        # roughly SNAPSHOT_PERIOD after each other.
        self.last_sync_time = time.time()

    def _set_corpus_dir_contents(self):
        """Set |self.corpus_dir_contents| to the current contents of
        |self.corpus_dir|. Don't include files or directories excluded by
        |EXCLUDE_PATHS|."""
        self.corpus_dir_contents = set()
        corpus_dir = os.path.abspath(self.corpus_dir)
        for root, _, files in os.walk(corpus_dir):
            # Check if root is excluded.
            relpath = os.path.relpath(root, corpus_dir)
            if _is_path_excluded(relpath):
                continue

            for filename in files:
                # Check if filename is excluded first.
                if _is_path_excluded(filename):
                    continue

                file_path = os.path.join(root, filename)
                stat_info = os.stat(file_path)
                last_modified_time = stat_info.st_mtime
                # Warning: ctime means creation time on Win and may not work as
                # expected.
                last_changed_time = stat_info.st_ctime
                file_tuple = File(file_path, last_modified_time,
                                  last_changed_time)
                self.corpus_dir_contents.add(file_tuple)

    def is_corpus_dir_same(self):
        """Sets |self.corpus_dir_contents| to the current contents and returns
        True if it is the same as the previous contents."""
        logs.debug('Checking if corpus dir is the same.')
        prev_contents = self.corpus_dir_contents.copy()
        self._set_corpus_dir_contents()
        return prev_contents == self.corpus_dir_contents

    def do_sync(self, final_sync=False):
        """Save corpus archives and results to GCS."""
        try:
            if not final_sync and self.is_corpus_dir_same():
                logs.debug('Cycle: %d unchanged.', self.cycle)
                filesystem.append(self.unchanged_cycles_path, str(self.cycle))
            else:
                logs.debug('Cycle: %d changed.', self.cycle)
                self.archive_and_save_corpus()

            self.save_results()
            logs.debug('Finished sync.')
        except Exception:  # pylint: disable=broad-except
            logs.error('Failed to sync cycle: %d.', self.cycle)

    def archive_corpus(self):
        """Archive this cycle's corpus."""
        archive = os.path.join(
            self.corpus_archives_dir,
            experiment_utils.get_corpus_archive_name(self.cycle))

        directories = [self.corpus_dir]
        if self.cycle == 1:
            # Some fuzzers like eclipser and LibFuzzer don't actually copy the
            # seed/input corpus to the output corpus (which AFL does do), this
            # results in their coverage being undercounted.
            seed_corpus = environment.get('SEED_CORPUS_DIR')
            directories.append(seed_corpus)

        archive_directories(directories, archive)
        return archive

    def save_corpus_archive(self, archive):
        """Save corpus |archive| to GCS and delete when done."""
        if not self.gcs_sync_dir:
            return

        basename = os.path.basename(archive)
        gcs_path = posixpath.join(self.gcs_sync_dir, self.corpus_dir, basename)

        # Don't use parallel to avoid stability issues.
        gsutil.cp(archive, gcs_path, parallel=False)

        # Delete corpus archive so disk doesn't fill up.
        os.remove(archive)

    @retry.wrap(NUM_RETRIES, RETRY_DELAY,
                'experiment.runner.TrialRunner.archive_and_save_corpus')
    def archive_and_save_corpus(self):
        """Archive and save the current corpus to GCS."""
        archive = self.archive_corpus()
        self.save_corpus_archive(archive)

    @retry.wrap(NUM_RETRIES, RETRY_DELAY,
                'experiment.runner.TrialRunner.save_results')
    def save_results(self):
        """Save the results directory to GCS."""
        if not self.gcs_sync_dir:
            return
        # Copy results directory before rsyncing it so that we don't get an
        # exception from uploading a file that changes in size. Files can change
        # in size because the log file containing the fuzzer's output is in this
        # directory and can be written to by the fuzzer at any time.
        results_copy = filesystem.make_dir_copy(self.results_dir)

        # Don't use parallel because it causes stability issues
        # (crbug.com/1053309).
        gsutil.rsync(results_copy,
                     posixpath.join(self.gcs_sync_dir, self.results_dir),
                     parallel=False)


def archive_directories(directories, archive_path):
    """Create a tar.gz file named |archive_path| containing the contents of each
    directory in |directories|."""
    with tarfile.open(archive_path, 'w:gz') as tar:
        for directory in directories:
            tar_directory(directory, tar)


def tar_directory(directory, tar):
    """Add the contents of |directory| to |tar|. Note that this should not
    exception just because files and directories are being deleted from
    |directory| while this function is being executed."""
    directory = os.path.abspath(directory)
    directory_name = os.path.basename(directory)
    for root, _, files in os.walk(directory):
        for filename in files:
            file_path = os.path.join(root, filename)
            arcname = os.path.join(directory_name,
                                   os.path.relpath(file_path, directory))
            try:
                tar.add(file_path, arcname=arcname)
            except (FileNotFoundError, OSError):
                # We will get these errors if files or directories are being
                # deleted from |directory| as we archive it. Don't bother
                # rescanning the directory, new files will be archived in the
                # next sync.
                pass
            except Exception:  # pylint: disable=broad-except
                logs.error('Unexpected exception occurred when archiving.')


def _is_path_excluded(path):
    """Is any part of |path| in |EXCLUDE_PATHS|."""
    path_parts = path.split(os.sep)
    for part in path_parts:
        if not part:
            continue
        if part in EXCLUDE_PATHS:
            return True
    return False


def experiment_main():
    """Do a trial as part of an experiment."""
    logs.info('Doing trial as part of experiment.')
    try:
        runner = TrialRunner()
        runner.conduct_trial()
    except Exception as error:  # pylint: disable=broad-except
        logs.error('Error doing trial.')
        raise error


def main():
    """Do an experiment on a development machine or on a GCP runner instance."""
    logs.initialize(
        default_extras={
            'benchmark': environment.get('BENCHMARK'),
            'component': 'runner',
            'fuzzer': environment.get('FUZZER'),
            'trial_id': str(environment.get('TRIAL_ID')),
        })
    experiment_main()
    return 0


if __name__ == '__main__':
    sys.exit(main())
