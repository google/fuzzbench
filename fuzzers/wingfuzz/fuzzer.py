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
"""Integration code for Wingfuzz fuzzer."""

import os

from fuzzers import utils
from fuzzers.libfuzzer import fuzzer as libfuzzer_fuzzer


def build():
    """Build benchmark."""
    cflags = [
        '-fsanitize=fuzzer-no-link',
        '-fno-sanitize-coverage=trace-cmp',
        '-fno-legacy-pass-manager',
        '-fpass-plugin=/LoadCmpTracer.so',
        # Hack: support non-standard build scripts ignoring LDFLAGS
        '-w',
        '-Wl,/WeakSym.o'
    ]
    utils.append_flags('CFLAGS', cflags)
    utils.append_flags('CXXFLAGS', cflags)

    os.environ['CC'] = 'clang'
    os.environ['CXX'] = 'clang++'
    os.environ['FUZZER_LIB'] = '/libWingfuzz.a'

    utils.build_benchmark()


def fuzz(input_corpus, output_corpus, target_binary):
    """Run fuzzer."""
    libfuzzer_fuzzer.run_fuzzer(input_corpus,
                                output_corpus,
                                target_binary,
                                extra_flags=[
                                    '-fork=0', '-keep_seed=1',
                                    '-jobs=2147483647', '-workers=1',
                                    '-reload=0'
                                ])
