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
"""Integration code for libFuzzer fuzzer."""

import subprocess
import os

from fuzzers import utils
from fuzzers.libfuzzer import fuzzer as libfuzzer_fuzzer


def build():
    """Build benchmark."""
    # With LibFuzzer we use -fsanitize=fuzzer-no-link for build CFLAGS and then
    # /usr/lib/libFuzzer.a as the FUZZER_LIB for the main fuzzing binary. This
    # allows us to link against a version of LibFuzzer that we specify.
    cflags = ['-fsanitize=fuzzer-no-link', '-fno-sanitize-coverage=trace-cmp']
    utils.append_flags('CFLAGS', cflags)
    utils.append_flags('CXXFLAGS', cflags)

    os.environ['CC'] = 'clang'
    os.environ['CXX'] = 'clang++'
    os.environ['FUZZER_LIB'] = '/usr/lib/libFuzzer.a'

    utils.build_benchmark()


def fuzz(input_corpus, output_corpus, target_binary):
    """Run fuzzer. Wrapper that uses the defaults when calling
    run_fuzzer."""
    libfuzzer_fuzzer.fuzz(input_corpus, output_corpus, target_binary)
