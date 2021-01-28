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
"""Integration code for symqemu fuzzer. Note that symqemu
relies on AFL to perform random-based fuzzing."""

import shutil
import subprocess
import os
import threading
import time

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

    # First, build an uninstrumented binary for symqemu.
    aflplusplus_fuzzer.build("qemu", "eclipser")
    symqemu_dir = get_uninstrumented_outdir(build_directory)
    os.mkdir(symqemu_dir)
    fuzz_binary = build_directory + '/' + fuzz_target
    shutil.copy(fuzz_binary, symqemu_dir)
    if os.path.isdir(build_directory + '/seeds'):
        shutil.rmtree(build_directory + '/seeds')

    # Second, build an instrumented binary for AFL++.
    os.environ = orig_env
    aflplusplus_fuzzer.build("tracepc")
    print('[build] Copying afl-fuzz to $OUT directory')

    # Copy afl-fuzz
    shutil.copy('/afl/afl-fuzz', build_directory)


def symqemu(input_corpus, output_corpus, target_binary):
    """Run symqemu."""
    # We will use output_corpus as a directory where AFL and symqemu sync their
    # test cases with each other. For symqemu, we should explicitly specify an
    # output directory under this sync directory.
    command = [
        '/symcc/symcc_fuzzing_helper',
        '-Q',
        '-o',
        output_corpus,
        '-a',
        'afl-worker',
        '-n',
        'symqemu',
        '-S',
        '0',
        '--',
        '/symcc/symqemu-x86_64',
        target_binary,
    ]
    print('[symqemu] Run symqemu with command: ' + ' '.join(command))
    subprocess.Popen(command)


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
        raise Exception("invalid input directory")

    afl_args = (input_corpus, output_corpus, target_binary)
    print('[fuzz] Running AFL worker')
    afl_worker_thread = threading.Thread(target=afl_worker, args=afl_args)
    afl_worker_thread.start()
    symqemu_args = (input_corpus, output_corpus, uninstrumented_target_binary)
    # ensure afl++ is running before we start symqemu
    time.sleep(10)
    print('[fuzz] Running symqemu')
    symqemu_thread = threading.Thread(target=symqemu, args=symqemu_args)
    symqemu_thread.start()
    print('[fuzz] Now waiting for threads to finish...')
    afl_worker_thread.join()
    symqemu_thread.join()
