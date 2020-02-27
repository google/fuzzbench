# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Integration code for QSYM fuzzer."""

import contextlib
import shutil
import subprocess
import os
import tempfile
import threading
import time

from fuzzers import utils
from fuzzers.afl import fuzzer as afl_fuzzer

# FUZZ_TARGET environment variable is location of the fuzz target (default is
# /out/fuzz-target).
# OUT environment variable is the location of build directory (default is /out).


def get_uninstrumented_build_directory(target_directory):
    """Return path to uninstrumented target directory."""
    return os.path.join(target_directory, 'uninstrumented')


def build():
    """Build fuzzer."""
    afl_fuzzer.prepare_build_environment()

    # Override AFL's FUZZER_LIB with QSYM's.
    os.environ['FUZZER_LIB'] = '/libQSYM.a'

    src = os.getenv('SRC')
    work = os.getenv('WORK')
    with restore_directory(src), restore_directory(work):
        # Restore SRC to its initial state so we can build again without any
        # trouble. For some OSS-Fuzz projects, build_benchmark cannot be run
        # twice in the same directory without this.
        utils.build_benchmark()

    # QSYM requires an uninstrumented build as well.
    new_env = os.environ.copy()
    utils.set_no_sanitizer_compilation_flags(new_env)
    cflags = ['-O2', '-fno-omit-frame-pointer', '-gline-tables-only']
    utils.append_flags('CFLAGS', cflags, new_env)
    utils.append_flags('CXXFLAGS', cflags, new_env)

    # For uninstrumented build, set the OUT and FUZZ_TARGET environment
    # variable to point to the new uninstrumented build directory.
    build_directory = os.environ['OUT']
    uninstrumented_build_directory = get_uninstrumented_build_directory(
        build_directory)
    os.mkdir(uninstrumented_build_directory)
    new_env['OUT'] = uninstrumented_build_directory
    fuzz_target = os.getenv('FUZZ_TARGET')
    if fuzz_target:
        new_env['FUZZ_TARGET'] = os.path.join(uninstrumented_build_directory,
                                              os.path.basename(fuzz_target))

    print('Re-building benchmark for uninstrumented fuzzing target')
    utils.build_benchmark(env=new_env)

    print('[post_build] Copying afl-fuzz to $OUT directory')
    # Copy out the afl-fuzz binary as a build artifact.
    shutil.copy('/afl/afl-fuzz', build_directory)
    # QSYM also requires afl-showmap.
    print('[post_build] Copying afl-showmap to $OUT directory')
    shutil.copy('/afl/afl-showmap', build_directory)


def fuzz(input_corpus, output_corpus, target_binary):
    """Run fuzzer."""
    # Calculate uninstrumented binary path from the instrumented target binary.
    target_binary_directory = os.path.dirname(target_binary)
    uninstrumented_target_binary_directory = (
        get_uninstrumented_build_directory(target_binary_directory))
    target_binary_name = os.path.basename(target_binary)
    uninstrumented_target_binary = os.path.join(
        uninstrumented_target_binary_directory, target_binary_name)

    afl_fuzzer.prepare_fuzz_environment(input_corpus)

    print('[run_fuzzer] Running AFL for QSYM')
    afl_fuzz_thread = threading.Thread(target=afl_fuzzer.run_afl_fuzz,
                                       args=(input_corpus, output_corpus,
                                             target_binary, ['-S',
                                                             'afl-slave']))
    afl_fuzz_thread.start()

    # Wait till AFL initializes (i.e. fuzzer_stats file exists) before
    # launching QSYM.
    print('[run_fuzzer] Waiting for AFL to finish initialization')
    afl_stats_file = os.path.join(output_corpus, 'afl-slave', 'fuzzer_stats')
    while True:
        if os.path.exists(afl_stats_file):
            break
        time.sleep(5)

    print('[run_fuzzer] Running QSYM')
    subprocess.Popen([
        './qsym/bin/run_qsym_afl.py', '-a', 'afl-slave', '-o', output_corpus,
        '-n', 'qsym', '--', uninstrumented_target_binary
    ])


@contextlib.contextmanager
def restore_directory(directory):
    """Helper contextmanager that when created saves a backup of |directory| and
    when closed/exited replaces |directory| with the backup.

    Example usage:

    directory = 'my-directory'
    with restore_directory(directory):
       shutil.rmtree(directory)
    # At this point directory is in the same state where it was before we
    # deleted it.
    """
    # TODO(metzman): Figure out if this is worth it, so far it only allows QSYM
    # to compile bloaty.
    if not directory:
        # Don't do anything if directory is None.
        yield
        return
    # Save cwd so that if it gets deleted we can just switch into the restored
    # version without code that runs after us running into issues.
    initial_cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as temp_dir:
        backup = os.path.join(temp_dir, os.path.basename(directory))
        shutil.copytree(directory, backup)
        yield
        shutil.rmtree(directory)
        shutil.move(backup, directory)
        try:
            os.getcwd()
        except FileNotFoundError:
            os.chdir(initial_cwd)
