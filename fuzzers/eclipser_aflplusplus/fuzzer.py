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

from fuzzers.aflplusplus import fuzzer as aflplusplus_fuzzer


def get_uninstrumented_outdir(target_directory):
    """Return path to uninstrumented target directory."""
    return os.path.join(target_directory, 'uninstrumented')


def build():
    """Build benchmark."""

    # Backup the environment.
    orig_env = os.environ.copy()
    #src = os.getenv('SRC')
    #work = os.getenv('WORK')
    build_directory = os.getenv('OUT')
    fuzz_target = os.getenv('FUZZ_TARGET')

    # First, build an uninstrumented binary for Eclipser.
    aflplusplus_fuzzer.build('qemu', 'eclipser')
    eclipser_dir = get_uninstrumented_outdir(build_directory)
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
    aflplusplus_fuzzer.fuzz(input_corpus,
                            output_corpus,
                            target_binary,
                            flags=(['-S', 'afl-worker']))


def fuzz(input_corpus, output_corpus, target_binary):
    """Run fuzzer."""

    # Calculate uninstrumented binary path from the instrumented target binary.
    target_binary_directory = os.path.dirname(target_binary)
    uninstrumented_target_binary_directory = (
        get_uninstrumented_outdir(target_binary_directory))
    target_binary_name = os.path.basename(target_binary)
    uninstrumented_target_binary = os.path.join(
        uninstrumented_target_binary_directory, target_binary_name)
    if not os.path.isdir(input_corpus):
        raise Exception('invalid input directory')

    afl_args = (input_corpus, output_corpus, target_binary)
    eclipser_args = (input_corpus, output_corpus, uninstrumented_target_binary)
    # Do not launch AFL master instance for now, to reduce memory usage and
    # align with the vanilla AFL.
    os.environ['AFL_DISABLE_TRIM'] = '1'
    print('[fuzz] Running AFL worker')
    afl_worker_thread = threading.Thread(target=afl_worker, args=afl_args)
    afl_worker_thread.start()
    print('[fuzz] Running Eclipser')
    eclipser_thread = threading.Thread(target=eclipser, args=eclipser_args)
    eclipser_thread.start()
    print('[fuzz] Now waiting for threads to finish...')
    afl_worker_thread.join()
    eclipser_thread.join()
