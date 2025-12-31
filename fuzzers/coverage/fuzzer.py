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
"""Integration code for clang source-based coverage builds."""

import os
import subprocess

from fuzzers import utils


def build():
    """Build benchmark."""
    cflags = [
        '-fprofile-instr-generate', '-fcoverage-mapping', '-gline-tables-only', '-fcoverage-mcdc'
    ]
    utils.append_flags('CFLAGS', cflags)
    utils.append_flags('CXXFLAGS', cflags)

    os.environ['CC'] = 'clang-19'
    os.environ['CXX'] = 'clang++-19'
    os.environ['FUZZER_LIB'] = '/usr/lib/libFuzzer.a'

    utils.build_benchmark()

def fuzz(input_corpus, output_corpus, target_binary):
    """Run fuzzer. Wrapper that uses the defaults when calling
    run_fuzzer."""
    
    command = [target_binary, input_corpus]
    print('[run_fuzzer] Running command: ' + ' '.join(command))
    subprocess.check_call(command)