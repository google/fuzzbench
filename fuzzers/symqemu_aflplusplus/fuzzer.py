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
''' Uses the SymCC-AFL hybrid from SymCC. '''

import os
import time
import shutil
import threading
import subprocess

from fuzzers.afl import fuzzer as afl_fuzzer
from fuzzers.aflplusplus import fuzzer as aflplusplus_fuzzer


def get_symcc_build_dir(target_directory):
    """Return path to uninstrumented target directory."""
    return os.path.join(target_directory, 'uninstrumented')


def build():
    """Build an AFL version and SymCC version of the benchmark"""

    # Backup the environment.
    orig_env = os.environ.copy()
    #src = os.getenv('SRC')
    #work = os.getenv('WORK')
    build_directory = os.getenv('OUT')
    fuzz_target = os.getenv('FUZZ_TARGET')

    # First, build an uninstrumented binary for Eclipser.
    aflplusplus_fuzzer.build('qemu', 'eclipser')
    eclipser_dir = get_symcc_build_dir(build_directory)
    os.mkdir(eclipser_dir)
    fuzz_binary = build_directory + '/' + fuzz_target
    shutil.copy(fuzz_binary, eclipser_dir)
    if os.path.isdir(build_directory + '/seeds'):
        shutil.rmtree(build_directory + '/seeds')

    # Second, build an instrumented binary for AFL++.
    os.environ = orig_env
    aflplusplus_fuzzer.build('tracepc')
    print('[build] Copying afl-fuzz to $OUT directory')

    # Copy afl-fuzz
    shutil.copy('/afl/afl-fuzz', build_directory)
    shutil.copy('/afl/afl-showmap', build_directory)
    shutil.copy('/rust/bin/symcc_fuzzing_helper', eclipser_dir)

    symcc_build_dir = get_symcc_build_dir(os.environ['OUT'])

    # Copy over symcc artifacts and symbolic libc++.
    shutil.copy(
        '/symcc/build//SymRuntime-prefix/src/SymRuntime-build/libSymRuntime.so',
        symcc_build_dir)
    shutil.copy('/usr/lib/libz3.so', os.path.join(symcc_build_dir, 'libz3.so'))
    shutil.copy('/rust/bin/symcc_fuzzing_helper', symcc_build_dir)
    shutil.copy('/symqemu/build/x86_64-linux-user/symqemu-x86_64',
                symcc_build_dir)


def launch_afl_thread(input_corpus, output_corpus, target_binary,
                      additional_flags):
    """ Simple wrapper for running AFL. """
    afl_thread = threading.Thread(target=afl_fuzzer.run_afl_fuzz,
                                  args=(input_corpus, output_corpus,
                                        target_binary, additional_flags))
    afl_thread.start()
    return afl_thread


def fuzz(input_corpus, output_corpus, target_binary):
    """
    Launches a master and a secondary instance of AFL, as well as
    the symcc helper.
    """
    target_binary_dir = os.path.dirname(target_binary)
    symcc_workdir = get_symcc_build_dir(target_binary_dir)
    target_binary_name = os.path.basename(target_binary)
    symcc_target_binary = os.path.join(symcc_workdir, target_binary_name)

    os.environ['AFL_DISABLE_TRIM'] = '1'

    # Start a master and secondary instance of AFL.
    # We need both because of the way SymCC works.
    print('[run_fuzzer] Running AFL for SymCC')
    afl_fuzzer.prepare_fuzz_environment(input_corpus)
    launch_afl_thread(input_corpus, output_corpus, target_binary,
                      ['-S', 'afl-secondary'])
    time.sleep(5)

    # Start an instance of SymCC.
    # We need to ensure it uses the symbolic version of libc++.
    symqemu_target = os.path.join(symcc_workdir, 'symqemu-x86_64')
    if os.path.isfile(symqemu_target):
        print('Found symqemu target')
    else:
        print('Did not find symqemu target')

    print('Starting the SymCC helper')
    new_environ = os.environ.copy()
    new_environ['LD_LIBRARY_PATH'] = symcc_workdir
    cmd = [
        os.path.join(symcc_workdir, 'symcc_fuzzing_helper'), '-o',
        output_corpus, '-a', 'afl-secondary', '-n', 'symqemu', '-m', '--',
        symqemu_target, symcc_target_binary, '@@'
    ]
    print(f'Running command: {" ".join(cmd)}')
    with subprocess.Popen(cmd, env=new_environ):
        pass
