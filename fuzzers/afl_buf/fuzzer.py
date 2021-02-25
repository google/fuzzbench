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
"""Integration code for AFL fuzzer."""

import os
import shutil

from fuzzers import utils
from fuzzers.afl import fuzzer as afl_fuzzer


def prepare_build_environment():
    """Set environment variables used to build targets for AFL-based
    fuzzers."""
    os.environ['CC'] = '/afl/afl-clang-fast'
    os.environ['CXX'] = '/afl/afl-clang-fast++'
    os.environ['FUZZER_LIB'] = '/libAFL.a'
    os.environ['AFL_QUIET'] = '1'
    # Buf waypoint
    os.environ['WAYPOINTS'] = 'buf'


def build():
    """Build benchmark."""
    prepare_build_environment()

    utils.build_benchmark()

    print('[post_build] Copying afl-fuzz to $OUT directory')
    # Copy out the afl-fuzz binary as a build artifact.
    shutil.copy('/afl/afl-fuzz', os.environ['OUT'])


def fuzz(input_corpus, output_corpus, target_binary):
    """Run afl-fuzz on target."""
    afl_fuzzer.prepare_fuzz_environment(input_corpus)

    afl_fuzzer.run_afl_fuzz(input_corpus,
                            output_corpus,
                            target_binary,
                            additional_flags=['-p'])
