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
"""Integration code for NEUZZ fuzzer."""

import shutil
import subprocess
import time
import os

from fuzzers import utils
from fuzzers.afl import fuzzer as afl_fuzzer


def build():
    """Build fuzzer."""
    cflags = ['-O2', '-fno-omit-frame-pointer', '-fsanitize=address']

    utils.append_flags('CFLAGS', cflags)
    utils.append_flags('CXXFLAGS', cflags)

    os.environ['CC'] = '/afl/afl-clang'
    os.environ['CXX'] = '/afl/afl-clang++'
    os.environ['FUZZER_LIB'] = '/libNeuzz.a'

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


def fuzz(fuzz_config):
    """Run fuzzer."""
    input_corpus = fuzz_config['input_corpus']
    output_corpus = fuzz_config['output_corpus']
    target_binary = fuzz_config['target_binary']

    afl_fuzzer.prepare_fuzz_environment(input_corpus)

    # Neuzz requires AFL to produce seeds for one hour before kicking in.
    print('[run_fuzzer] Generating seeds with afl-fuzz')
    process = subprocess.Popen([
        './afl-fuzz', '-i', input_corpus, '-o', output_corpus, '-m', 'none',
        '--', target_binary, '@@'
    ])
    # Wait an hour.
    time.sleep(60 * 60)
    process.kill()

    afl_output_dir = os.path.join(output_corpus, 'queue')
    neuzz_input_dir = os.path.join(output_corpus, 'neuzz_in')
    # Treat afl's queue folder as the input for Neuzz.
    os.rename(afl_output_dir, neuzz_input_dir)

    print('[run_fuzzer] Running background machine learning process')
    subprocess.Popen([
        'python3', 'nn.py', '--enable-asan', '--output-folder', afl_output_dir,
        target_binary
    ])

    # Give time for tensorflow to initialize in the Python script and then
    # launch the Neuzz fuzzer program.
    time.sleep(60)
    print('[run_fuzzer] Running target with NEUZZ')
    subprocess.call([
        './neuzz', '-m', 'none', '-i', neuzz_input_dir, '-o', afl_output_dir,
        '-l', '7506', target_binary, '@@'
    ])
