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
"""Integration code for mua_fuzzer_bench measurer builds."""

import os
import subprocess

from fuzzers import utils

MUA_RECORDING_DB = '/mua_build/execs.sqlite'


def build():
    """Build benchmark."""
    benchmark = os.getenv('BENCHMARK')

    cflags = [
        # '-fprofile-instr-generate', '-fcoverage-mapping', '-gline-tables-only'
        '-fPIE',
    ]
    if benchmark == 're2_fuzzer':
        cflags = [
            '',
        ]
    utils.append_flags('CFLAGS', cflags)
    utils.append_flags('CXXFLAGS', cflags)

    os.environ['CC'] = 'gclang-wrap'
    os.environ['CXX'] = 'gclang++-wrap'
    os.environ['LLVM_COMPILER_PATH'] = '/usr/lib/llvm-15/bin/'
    os.environ['MUA_RECORDING_DB'] = MUA_RECORDING_DB
    os.environ['llvmBinPath'] = '/usr/local/bin/'

    # build FUZZER_LIB
    #subprocess.check_call(['clang++', '-c',
    #'/mutator/dockerfiles/programs/common/main.cc', '-o',
    #'/usr/lib/libFuzzingEngineMutation.a'])
    #os.environ['FUZZER_LIB'] = '/usr/lib/libFuzzingEngineMutation.a'

    os.environ['FUZZER_LIB'] = '/mutator/dockerfiles/programs/common/main.cc'

    if os.path.exists(MUA_RECORDING_DB):
        os.unlink(MUA_RECORDING_DB)

    build_script = os.path.join(os.environ['SRC'], 'build.sh')
    print(f'build_script: {build_script}')

    fuzzer = os.getenv('FUZZER')
    print(f'Building benchmark {benchmark} with fuzzer {fuzzer}')

    utils.build_benchmark()

    subprocess.check_call(['/mutator/fuzzbench_build.sh'])
