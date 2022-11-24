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

from fuzzers import utils
from fuzzers.afl import fuzzer as afl_fuzzer
from fuzzers.aflplusplus import fuzzer as aflplusplus_fuzzer


def get_symcc_build_dir(target_directory):
    """Return path to uninstrumented target directory."""
    return os.path.join(target_directory, 'uninstrumented')


def build():
    """Build an AFL version and SymCC version of the benchmark"""
    print('Step 1: Building with AFL')
    build_directory = os.environ['OUT']

    # Save the environment for use in SymCC
    new_env = os.environ.copy()

    # First build with AFL.
    src = os.getenv('SRC')
    work = os.getenv('WORK')
    with utils.restore_directory(src), utils.restore_directory(work):
        # Restore SRC to its initial state so we can build again without any
        # trouble. For some OSS-Fuzz projects, build_benchmark cannot be run
        # twice in the same directory without this.
        aflplusplus_fuzzer.build('tracepc')

    print('Step 2: Completed AFL build')
    # Copy over AFL artifacts needed by SymCC.
    shutil.copy('/afl/afl-fuzz', build_directory)
    shutil.copy('/afl/afl-showmap', build_directory)

    # Build the SymCC-instrumented target.
    print('Step 3: Building the benchmark with SymCC')
    symcc_build_dir = get_symcc_build_dir(os.environ['OUT'])
    os.mkdir(symcc_build_dir)

    # Set flags to ensure compilation with SymCC.
    new_env['CC'] = '/symcc/build/symcc'
    new_env['CXX'] = '/symcc/build/sym++'
    new_env['CXXFLAGS'] = new_env['CXXFLAGS'].replace('-stlib=libc++', '')
    new_env['CXXFLAGS'] += ' -ldl'
    new_env['FUZZER_LIB'] = '/libfuzzer-harness.o'
    new_env['OUT'] = symcc_build_dir

    new_env['CXXFLAGS'] += ' -fno-sanitize=all '
    new_env['CFLAGS'] += ' -fno-sanitize=all '

    # Setting this environment variable instructs SymCC to use the
    # libcxx library compiled with SymCC instrumentation.
    new_env['SYMCC_LIBCXX_PATH'] = '/libcxx_native_build'

    # Instructs SymCC to consider no symbolic inputs at runtime. This is needed
    # if, for example, some tests are run during compilation of the benchmark.
    new_env['SYMCC_NO_SYMBOLIC_INPUT'] = '1'

    # Build benchmark.
    utils.build_benchmark(env=new_env)

    # Copy over symcc artifacts and symbolic libc++.
    shutil.copy(
        '/symcc/build//SymRuntime-prefix/src/SymRuntime-build/libSymRuntime.so',
        symcc_build_dir)
    shutil.copy('/usr/lib/libz3.so', os.path.join(symcc_build_dir, 'libz3.so'))
    shutil.copy('/libcxx_native_build/lib/libc++.so.1', symcc_build_dir)
    shutil.copy('/libcxx_native_build/lib/libc++abi.so.1', symcc_build_dir)
    shutil.copy('/rust/bin/symcc_fuzzing_helper', symcc_build_dir)


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
    launch_afl_thread(input_corpus, output_corpus, target_binary, ['-S', 'afl'])
    time.sleep(5)
    launch_afl_thread(input_corpus, output_corpus, target_binary,
                      ['-S', 'afl-secondary'])
    time.sleep(5)

    # Start an instance of SymCC.
    # We need to ensure it uses the symbolic version of libc++.
    print('Starting the SymCC helper')
    new_environ = os.environ.copy()
    new_environ['LD_LIBRARY_PATH'] = symcc_workdir
    cmd = [
        os.path.join(symcc_workdir,
                     'symcc_fuzzing_helper'), '-o', output_corpus, '-a',
        'afl-secondary', '-n', 'symcc', '-m', '--', symcc_target_binary, '@@'
    ]
    with subprocess.Popen(cmd, env=new_environ):
        pass
