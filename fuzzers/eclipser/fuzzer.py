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
"""Integration code for Eclipser fuzzer. Note that starting from v2.0, Eclipser
relies on AFL to perform random-based fuzzing."""

import shutil
import subprocess
import os
import threading

from fuzzers import utils
from fuzzers.afl import fuzzer as afl_fuzzer


def get_uninstrumented_outdir(target_directory):
    """Return path to uninstrumented target directory."""
    return os.path.join(target_directory, 'uninstrumented')


def build():
    """Build benchmark."""

    # Backup the environment.
    new_env = os.environ.copy()

    # First, build an instrumented binary for AFL.
    afl_fuzzer.prepare_build_environment()
    src = os.getenv('SRC')
    work = os.getenv('WORK')
    with utils.restore_directory(src), utils.restore_directory(work):
        # Restore SRC to its initial state so we can build again without any
        # trouble. For some OSS-Fuzz projects, build_benchmark cannot be run
        # twice in the same directory without this.
        utils.build_benchmark()
    print('[build] Copying afl-fuzz to $OUT directory')
    shutil.copy('/afl/afl-fuzz', os.environ['OUT'])

    # Next, build an uninstrumented binary for Eclipser.
    new_env['CC'] = 'clang'
    new_env['CXX'] = 'clang++'
    new_env['FUZZER_LIB'] = '/libStandaloneFuzzTarget.a'
    # Ensure to compile with NO_SANITIZER_COMPAT* flags even for bug benchmarks,
    # as QEMU is incompatible with sanitizers. Also, Eclipser prefers clean and
    # unoptimized binaries. We leave fast random fuzzing as AFL's job.
    new_env['CFLAGS'] = ' '.join(utils.NO_SANITIZER_COMPAT_CFLAGS)
    cxxflags = [utils.LIBCPLUSPLUS_FLAG] + utils.NO_SANITIZER_COMPAT_CFLAGS
    new_env['CXXFLAGS'] = ' '.join(cxxflags)
    uninstrumented_outdir = get_uninstrumented_outdir(os.environ['OUT'])
    os.mkdir(uninstrumented_outdir)
    new_env['OUT'] = uninstrumented_outdir
    fuzz_target = os.getenv('FUZZ_TARGET')
    if fuzz_target:
        targ_name = os.path.basename(fuzz_target)
        new_env['FUZZ_TARGET'] = os.path.join(uninstrumented_outdir, targ_name)
    print('[build] Re-building benchmark for uninstrumented fuzzing target')
    utils.build_benchmark(env=new_env)


def eclipser(input_corpus, output_corpus, target_binary):
    """Run Eclipser."""
    # We will use output_corpus as a directory where AFL and Eclipser sync their
    # test cases with each other. For Eclipser, we should explicitly specify an
    # output directory under this sync directory.
    eclipser_out = os.path.join(output_corpus, 'eclipser_output')
    command = [
        'dotnet',
        '/Eclipser/build/Eclipser.dll',
        '-p',
        target_binary,
        '-s',
        output_corpus,
        '-o',
        eclipser_out,
        '--arg',  # Specifies the command-line of the program.
        'foo',
        '-f',  # Specifies the path of file input to fuzz.
        'foo',
        '-v',  # Controls the verbosity.
        '2',
        '--exectimeout',
        '5000',
    ]
    if os.listdir(input_corpus):  # Specify inputs only if any seed exists.
        command += ['-i', input_corpus]
    print('[eclipser] Run Eclipser with command: ' + ' '.join(command))
    with subprocess.Popen(command):
        pass


def afl_worker(input_corpus, output_corpus, target_binary):
    """Run AFL worker instance."""
    print('[afl_worker] Run AFL worker')
    afl_fuzzer.run_afl_fuzz(input_corpus, output_corpus, target_binary,
                            ['-S', 'afl-worker'], True)


def fuzz(input_corpus, output_corpus, target_binary):
    """Run fuzzer."""

    # Calculate uninstrumented binary path from the instrumented target binary.
    target_binary_directory = os.path.dirname(target_binary)
    uninstrumented_target_binary_directory = (
        get_uninstrumented_outdir(target_binary_directory))
    target_binary_name = os.path.basename(target_binary)
    uninstrumented_target_binary = os.path.join(
        uninstrumented_target_binary_directory, target_binary_name)

    afl_fuzzer.prepare_fuzz_environment(input_corpus)
    afl_args = (input_corpus, output_corpus, target_binary)
    eclipser_args = (input_corpus, output_corpus, uninstrumented_target_binary)
    # Do not launch AFL master instance for now, to reduce memory usage and
    # align with the vanilla AFL.
    print('[fuzz] Running AFL worker')
    afl_worker_thread = threading.Thread(target=afl_worker, args=afl_args)
    afl_worker_thread.start()
    print('[fuzz] Running Eclipser')
    eclipser_thread = threading.Thread(target=eclipser, args=eclipser_args)
    eclipser_thread.start()
    print('[fuzz] Now waiting for threads to finish...')
    afl_worker_thread.join()
    eclipser_thread.join()
