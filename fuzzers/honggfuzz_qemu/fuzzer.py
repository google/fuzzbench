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
"""Integration code for Honggfuzz fuzzer."""

import os
import shutil
import subprocess

from fuzzers import utils


def build():
    """Build benchmark."""
    # honggfuzz doesn't need additional libraries when code is compiled
    # with hfuzz-clang(++)
    os.environ['CC'] = 'clang'
    os.environ['CXX'] = 'clang++'
    os.environ['FUZZER_LIB'] = '/libQEMU.a'

    utils.build_benchmark()

    print('[post_build] Copying honggfuzz to $OUT directory')
    # Copy over honggfuzz's main fuzzing binary.
    shutil.copy('/honggfuzz/honggfuzz', os.environ['OUT'])
    shutil.copy(
        '/honggfuzz/qemu_mode/honggfuzz-qemu/x86_64-linux-user/qemu-x86_64',
        os.environ['OUT'])


def fuzz(input_corpus, output_corpus, target_binary):
    """Run fuzzer."""
    # Seperate out corpus and crash directories as sub-directories of
    # |output_corpus| to avoid conflicts when corpus directory is reloaded.
    crashes_dir = os.path.join(output_corpus, 'crashes')
    output_corpus = os.path.join(output_corpus, 'corpus')
    os.makedirs(crashes_dir)
    os.makedirs(output_corpus)

    print('[fuzz] Running target with honggfuzz')
    command = [
        './honggfuzz',
        '--rlimit_rss',
        '2048',
        '--sanitizers_del_report=true',
        '--input',
        input_corpus,
        '--output',
        output_corpus,

        # Store crashes along with corpus for bug based benchmarking.
        '--crashdir',
        crashes_dir,
        '-s',
    ]
    dictionary_path = utils.get_dictionary_path(target_binary)
    if dictionary_path:
        command.extend(['--dict', dictionary_path])
    command.extend(['--', './qemu-x86_64', target_binary])

    print('[fuzz] Running command: ' + ' '.join(command))
    subprocess.check_call(command)
