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

import shutil
import os

from fuzzers import utils

from fuzzers.afl import fuzzer as afl_fuzzer


def prepare_build_environment():
    """Set environment variables used to build benchmark."""
    utils.set_no_sanitizer_compilation_flags()
    # TODO(metzman): Figure out why -pthread needs to come after
    # -std=libc++ and why -std=libc++ is not needed. This hack isn't
    # such a problem unless it affects other users (presubmably it
    # won't because their compilers are newer.
    CFLAGS = ' '.join([
    '-pthread', '-Wl,--no-as-needed', '-Wl,-ldl', '-Wl,-lm',
    '-Wno-unused-command-line-argument', '-O3', '-stdlib=libc++'
    ])
    os.environ['CFLAGS'] = CFLAGS
    os.environ['CXXFLAGS'] = CFLAGS
    print(os.environ['CFLAGS'])

    # Enable LAF-INTEL changes
    os.environ['LAF_SPLIT_SWITCHES'] = '1'
    os.environ['LAF_TRANSFORM_COMPARES'] = '1'
    os.environ['LAF_SPLIT_COMPARES'] = '1'
    os.environ['AFL_CC'] = 'clang-3.8'
    os.environ['AFL_CXX'] = 'clang++-3.8'

    os.environ['CC'] = '/afl/afl-clang-fast'
    os.environ['CXX'] = '/afl/afl-clang-fast++'
    os.environ['FUZZER_LIB'] = '/libAFL.a'

def build():
    """Build benchmark."""
    prepare_build_environment()

    utils.build_benchmark()

    print('[post_build] Copying afl-fuzz to $OUT directory')
    # Copy out the afl-fuzz binary as a build artifact.
    shutil.copy('/afl/afl-fuzz', os.environ['OUT'])


def fuzz(fuzz_config):
    """Run fuzzer."""
    afl_fuzzer.fuzz(fuzz_config)
