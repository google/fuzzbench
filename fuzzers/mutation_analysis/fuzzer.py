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

MUA_RECORDING_DB = '/tmp/execs.sqlite'


def build():
    # """Build benchmark."""
    cflags = [
        # '-fprofile-instr-generate', '-fcoverage-mapping', '-gline-tables-only'
        '-fPIE',
    ]
    utils.append_flags('CFLAGS', cflags)
    utils.append_flags('CXXFLAGS', cflags)

    os.environ['CC'] = 'gclang-wrap'
    os.environ['CXX'] = 'gclang++-wrap'
    os.environ['LLVM_COMPILER_PATH'] = '/usr/lib/llvm-15/bin/' 
    os.environ['FUZZER_LIB'] = '/mutator/dockerfiles/programs/common/main.cc'
    os.environ['MUA_RECORDING_DB'] = MUA_RECORDING_DB
    os.environ['llvmBinPath'] = '/usr/local/bin/'

    if os.path.exists(MUA_RECORDING_DB):
        os.unlink(MUA_RECORDING_DB)

    # fuzzer_lib = env['FUZZER_LIB']
    # env['LIB_FUZZING_ENGINE'] = fuzzer_lib
    # if os.path.exists(fuzzer_lib):
    #     # Make /usr/lib/libFuzzingEngine.a point to our library for OSS-Fuzz
    #     # so we can build projects that are using -lFuzzingEngine.
    #     shutil.copy(fuzzer_lib, OSS_FUZZ_LIB_FUZZING_ENGINE_PATH)

    build_script = os.path.join(os.environ['SRC'], 'build.sh')
    print(f"build_script: {build_script}")

    benchmark = os.getenv('BENCHMARK')
    fuzzer = os.getenv('FUZZER')
    print(f'Building benchmark {benchmark} with fuzzer {fuzzer}')

    os.system("touch /test.txt")

    utils.build_benchmark()

    # subprocess.check_call(['/bin/mua_build_benchmark'])
