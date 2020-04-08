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

    # Update compiler flags for clang-3.8
    cflags = ['-fPIC']
    cppflags = cflags + ['-I/usr/local/include/c++/v1/', '-stdlib=libc++', '-std=c++11']
    utils.append_flags('CFLAGS', cflags)
    utils.append_flags('CXXFLAGS', cppflags)
   
    # Setup aflcc compiler
    os.environ['LLVM_CONFIG'] = 'llvm-config-3.8'
    os.environ['CC'] = '/afl/aflc-gclang'
    os.environ['CXX'] = '/afl/aflc-gclang++'
    os.environ['FUZZER_LIB'] = '/libAFL.a -L / -lAflccMock'


def build():
    """Build benchmark."""
    prepare_build_environment()

    utils.build_benchmark()

    print('[post_build] Extracting .bc file')
    out_dir = os.environ['OUT']
    fuzz_target = os.path.join(out_dir, 'fuzz-target')
    getbc_cmd = "/afl/aflc-get-bc {target}".format(target=fuzz_target)
    if 0 != os.system(getbc_cmd):
        raise ValueError("get-bc failed")

    # create the different build types
    os.environ['AFL_BUILD_TYPE'] = 'FUZZING'

    # the original afl binary
    print('[post_build] Generating original afl build')
    os.environ['AFL_COVERAGE_TYPE'] = 'ORIGINAL'
    os.environ['AFL_CONVERT_COMPARISON_TYPE'] = 'NONE'
    os.environ['AFL_DICT_TYPE'] = 'NORMAL'
    bin1_cmd = "{compiler} -O3 {target}.bc -o {target}-original".format(compiler='/afl/aflc-clang-fast++', target=fuzz_target)
    if 0 != os.system(bin1_cmd):
        raise ValueError("command '{command}' failed".format(command=bin1_cmd))

    # the normalized build with optimized dictionary
    print('[post_build] Generating normalized-none-opt')
    os.environ['AFL_COVERAGE_TYPE'] = 'ORIGINAL'
    os.environ['AFL_CONVERT_COMPARISON_TYPE'] = 'NONE'
    os.environ['AFL_DICT_TYPE'] = 'OPTIMIZED'
    bin2_cmd = "{compiler} {target}.bc -o {target}-normalized-none-opt".format(compiler='/afl/aflc-clang-fast++', target=fuzz_target)
    if 0 != os.system(bin2_cmd):
        raise ValueError("command '{command}' failed".format(command=bin2_cmd))

    # the no-collision split-condition optimized dictionary
    print('[post_build] Generating no-collision-all-opt build')
    os.environ['AFL_COVERAGE_TYPE'] = 'NO_COLLISION'
    os.environ['AFL_CONVERT_COMPARISON_TYPE'] = 'ALL'
    os.environ['AFL_DICT_TYPE'] = 'OPTIMIZED'
    bin3_cmd = "{compiler} {target}.bc -o {target}-no-collision-all-opt".format(compiler='/afl/aflc-clang-fast++', target=fuzz_target)
    if 0 != os.system(bin3_cmd):
        raise ValueError("command '{command}' failed".format(command=bin3_cmd))

    print('[post_build] Copying afl-fuzz to $OUT directory')
    # Copy out the afl-fuzz binary as a build artifact.
    shutil.copy('/afl/afl-fuzz', os.environ['OUT'])


def fuzz(input_corpus, output_corpus, target_binary):
    """Run fuzzer."""
    afl_fuzzer.prepare_fuzz_environment(input_corpus)

    # print('[run_fuzzer] Running AFL for binary1')
    # afl_fuzz_thread = threading.Thread(target=afl_fuzzer.run_afl_fuzz,
    #                                    args=(input_corpus, output_corpus,
    #                                          target_binary, ['-S',
    #                                                          'afl-slave']))
    # afl_fuzz_thread.start()
