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

# OUT environment variable is the location of build directory (default is /out).


def build():
    """Build fuzzer."""
    cflags = [
        '-O2',
        '-fno-omit-frame-pointer',
        '-gline-tables-only',
        '-fsanitize=address',
    ]
    utils.append_flags('CFLAGS', cflags)
    utils.append_flags('CXXFLAGS', cflags)

    # honggfuzz doesn't need additional libraries when code is compiled
    # with hfuzz-clang(++)
    os.environ['CC'] = '/honggfuzz/hfuzz_cc/hfuzz-clang'
    os.environ['CXX'] = '/honggfuzz/hfuzz_cc/hfuzz-clang++'
    os.environ['FUZZER_LIB'] = '/honggfuzz/empty_lib.o'

    utils.build_benchmark()

    print('[post_build] Copying honggfuzz to $OUT directory')
    # Copy over honggfuzz's main fuzzing binary.
    shutil.copy('/honggfuzz/honggfuzz', os.environ['OUT'])


def fuzz(input_corpus, output_corpus, target_binary):
    """Run fuzzer."""
    # Honggfuzz needs the output directory to exist.
    if not os.path.exists(output_corpus):
        os.makedirs(output_corpus)

    print('[run_fuzzer] Running target with honggfuzz')
    subprocess.call([
        './honggfuzz', '--sanitizers', '--persistent', '--input', input_corpus,
        '--output', output_corpus, '--', target_binary
    ])
