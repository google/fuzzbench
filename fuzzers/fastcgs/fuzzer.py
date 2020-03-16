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
"""Integration code for AFLplusplus fuzzer."""

import os
import shutil

from fuzzers.afl import fuzzer as afl_fuzzer
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

    os.environ['CC'] = '/afl/afl-clang-fast'
    os.environ['CXX'] = '/afl/afl-clang-fast++'
    os.environ['FUZZER_LIB'] = '/libAFLDriver.a'

    # Some benchmarks like lcms
    # (see: https://github.com/mm2/Little-CMS/commit/ab1093539b4287c233aca6a3cf53b234faceb792#diff-f0e6d05e72548974e852e8e55dffc4ccR212)
    # fail to compile if the compiler outputs things to stderr in unexpected
    # cases. Prevent these failures by using AFL_QUIET to stop afl-clang-fast
    # from writing AFL specific messages to stderr.
    os.environ['AFL_QUIET'] = '1'

    utils.build_benchmark()
    shutil.copy('/afl/afl-fuzz', os.environ['OUT'])


def fuzz(input_corpus, output_corpus, target_binary):
    """Run fuzzer."""
    afl_fuzzer.prepare_fuzz_environment(input_corpus)

    afl_fuzzer.run_afl_fuzz(
        input_corpus,
        output_corpus,
        target_binary,
        additional_flags=[
            # Enable AFLFast's power schedules with default exponential
            # schedule.
            '-p',
            'fast',
            # Enable Mopt mutator with pacemaker fuzzing mode at first. This
            # is also recommended in a short-time scale evaluation.
            '-L',
            '0',
        ])
