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
"""Integration code for AFL fuzzer."""

import os
import shutil
import subprocess
import time
import threading

from fuzzers import utils
from fuzzers.afl import fuzzer as afl

WARMUP = 60 * 60


def prepare_build_environment():
    """Set environment variables used to build targets for AFL-based
    fuzzers."""
    utils.set_compilation_flags()
    os.environ['CC'] = '/afl/afl-clang'
    os.environ['CXX'] = '/afl/afl-clang++'
    os.environ['FUZZER_LIB'] = '/libNeuzz.a'


def build():
    """Build benchmark."""
    prepare_build_environment()
    utils.build_benchmark()
    output_directory = os.environ['OUT']
    # Copy out the afl-fuzz binary as a build artifact.
    print('[post_build] Copying afl-fuzz to $OUT directory')
    shutil.copy('/afl/afl-fuzz', output_directory)
    # Neuzz also requires afl-showmap.
    print('[post_build] Copying afl-showmap to $OUT directory')
    shutil.copy('/afl/afl-showmap', output_directory)
    # Copy the Neuzz fuzzer itself.
    print('[post_build] Copy neuzz fuzzer.')
    shutil.copy('/neuzz/neuzz', output_directory)
    shutil.copy('/neuzz/nn.py', output_directory)


def kill_afl(output_stream=subprocess.DEVNULL):
    """kill afl-fuzz process."""
    print('Warmed up!')
    # Can't avoid this because 'run_afl_fuzz' doesn't return a handle to
    # 'afl-fuzz' process so that we can kill it with subprocess.terminate()
    subprocess.call(['pkill', '-f', 'afl-fuzz'],
                    stdout=output_stream,
                    stderr=output_stream)


def run_neuzz(input_corpus,
              output_corpus,
              target_binary,
              additional_flags=None,
              hide_output=False):
    """Run neuzz"""
    # Spawn the afl fuzzing process for warmup
    output_stream = subprocess.DEVNULL if hide_output else None
    threading.Timer(20, kill_afl, [output_stream]).start()
    afl.run_afl_fuzz(input_corpus, output_corpus, target_binary,
                     additional_flags, hide_output)
    # After warming up, copy the 'queue' to use for neuzz input
    print('[run_neuzz] Warmed up!')
    command = [
        'cp', '-RT', f'{output_corpus}/queue/', f'{input_corpus}_neuzzin/'
    ]
    print('[run_neuzz] Running command: ' + ' '.join(command))

    subprocess.check_call(command, stdout=output_stream, stderr=output_stream)

    afl_output_dir = os.path.join(output_corpus, 'queue')
    neuzz_input_dir = os.path.join(output_corpus, 'neuzz_in')
    # Treat afl's queue folder as the input for Neuzz.
    os.rename(afl_output_dir, neuzz_input_dir)

    # Spinning up the neural network
    command = [
        'python2', './nn.py', '--output-folder', afl_output_dir, target_binary
    ]
    print('[run_neuzz] Running command: ' + ' '.join(command))
    with subprocess.Popen(command, stdout=output_stream, stderr=output_stream):
        pass
    time.sleep(40)
    target_rel_path = os.path.relpath(target_binary, os.getcwd())
    # Spinning up neuzz
    command = [
        './neuzz', '-m', 'none', '-i', neuzz_input_dir, '-o', afl_output_dir,
        target_rel_path, '@@'
    ]
    print('[run_neuzz] Running command: ' + ' '.join(command))
    with subprocess.Popen(command, stdout=output_stream,
                          stderr=output_stream) as neuzz_proc:
        neuzz_proc.wait()


def fuzz(input_corpus, output_corpus, target_binary):
    """Run afl-fuzz on target."""
    afl.prepare_fuzz_environment(input_corpus)
    run_neuzz(input_corpus, output_corpus, target_binary)
