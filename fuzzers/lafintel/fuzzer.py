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
    # In php benchmark, there is a call to __builtin_cpu_supports("ssse3")
    # (see https://github.com/php/php-src/blob/master/Zend/zend_cpuinfo.h).
    # It is not supported by clang-3.8, so we define the MACRO below
    # to replace any __builtin_cpu_supports() with 0, i.e., not supported
    cflags = ['-fPIC']
    if 'php' in os.environ['BENCHMARK']:
        cflags += ['-D__builtin_cpu_supports\\(x\\)=0']
    cppflags = cflags + ['-I/usr/local/include/c++/v1/', '-std=c++11']
    utils.append_flags('CFLAGS', cflags)
    utils.append_flags('CXXFLAGS', cppflags)

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


def fuzz(input_corpus, output_corpus, target_binary):
    """Run fuzzer."""
    afl_fuzzer.fuzz(input_corpus, output_corpus, target_binary)
