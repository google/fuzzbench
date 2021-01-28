# Copyright 2021 Google LLC
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
"""Integration code for SymQEMU."""

import shutil
import subprocess
import os
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

    os.environ['FUZZER_LIB'] = '/libAFL.a'

    src = os.getenv('SRC')
    work = os.getenv('WORK')
    with utils.restore_directory(src), utils.restore_directory(work):
        # Restore SRC to its initial state so we can build again without any
        # trouble. For some OSS-Fuzz projects, build_benchmark cannot be run
        # twice in the same directory without this.
        utils.build_benchmark()

    # SymQEMU requires an uninstrumented build as well.
    new_env = os.environ.copy()
    cflags = utils.NO_SANITIZER_COMPAT_CFLAGS[:]
    cflags.append(utils.DEFAULT_OPTIMIZATION_LEVEL)
    os.environ['CFLAGS'] = ' '.join(cflags)
    cxxflags = cflags.append(utils.LIBCPLUSPLUS_FLAG)
    os.environ['CXXFLAGS'] = ' '.join(cxxflags)

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
    # SymQEMU also requires afl-showmap.
    print('[post_build] Copying afl-showmap to $OUT directory')
    shutil.copy('/afl/afl-showmap', build_directory)
    # Copy SymQEMU and its dependencies.
    print('[post_build] Copying libz3 to $OUT directory')
    shutil.copy('/z3/lib/libz3.so.4.8', build_directory)
    print('[post_build] Copying libSymRuntime to $OUT directory')
    shutil.copy(
        '/symcc/build/SymRuntime-prefix/src/SymRuntime-build/libSymRuntime.so',
        build_directory)
    print('[post_build] Copying SymQEMU to $OUT directory')
    shutil.copy('/symqemu/build/x86_64-linux-user/symqemu-x86_64',
                build_directory)
    print('[post_build] Copying fuzzing helper to $OUT directory')
    shutil.copy('/root/.cargo/bin/symcc_fuzzing_helper', build_directory)


def run_afl_fuzz(input_corpus, output_corpus, target_binary):
    """Run afl-fuzz in distributed mode."""
    # Spawn the afl fuzzing process.
    # FIXME: Currently AFL will exit if it encounters a crashing input in seed
    # corpus (usually timeouts). Add a way to skip/delete such inputs and
    # re-run AFL.
    print('[run_fuzzer] Running target with afl-fuzz')
    command = [
        './afl-fuzz',
        '-i',
        input_corpus,
        '-o',
        output_corpus,
        # Use no memory limit as ASAN doesn't play nicely with one.
        '-m',
        'none',
        '-S',
        'afl'
    ]
    dictionary_path = utils.get_dictionary_path(target_binary)
    if dictionary_path:
        command.extend(['-x', dictionary_path])
    command += [
        '--',
        target_binary,
        # Pass INT_MAX to afl the maximize the number of persistent loops it
        # performs.
        '2147483647'
    ]
    print('[run_fuzzer] Running command: ' + ' '.join(command))
    subprocess.check_call(command)


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

    print('[run_fuzzer] Running AFL for SymQEMU')
    afl_fuzz_thread = threading.Thread(target=run_afl_fuzz,
                                       args=(input_corpus, output_corpus,
                                             target_binary))
    afl_fuzz_thread.start()

    # Wait till AFL initializes (i.e. fuzzer_stats file exists) before
    # launching SymQEMU.
    print('[run_fuzzer] Waiting for AFL to finish initialization')
    afl_stats_file = os.path.join(output_corpus, 'afl', 'fuzzer_stats')
    while True:
        if os.path.exists(afl_stats_file):
            break
        time.sleep(5)

    print('[run_fuzzer] Running SymQEMU')
    new_env = os.environ.copy()
    new_env['LD_LIBRARY_PATH'] = target_binary_directory
    subprocess.check_call([
        './symcc_fuzzing_helper', '-a', 'afl', '-o', output_corpus, '-n',
        'symqemu', '--', './symqemu-x86_64', uninstrumented_target_binary
    ],
                          env=new_env)
