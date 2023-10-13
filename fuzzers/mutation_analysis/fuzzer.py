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
    prepare()


def prepare():
    # executed when benchmark is already present, but no fuzzer selected
    subprocess.check_call(['/bin/mua_build_benchmark'])
    subprocess.check_call(['cd /mutator && gradle build'])
    subprocess.check_call(['ldconfig /mutator/build/install/LLVM_Mutation_Tool/lib/ '])
    subprocess.check_call(['pipx run hatch run src/mua_fuzzer_benchmark/eval.py locator_local --config-path /tmp/config.json --result-path /tmp/test/'])
    #subprocess.check_call([''])
    #subprocess.check_call([''])

     # build tooling
    # load libs
     #build location executables


    # fuzzer_build # runs fuzzer.py build
# mua_build_benchmark # builds bitcode to /out/filename.bc and config to /tmp/config

# cd /mutator && gradle build #baut tooling
# ldconfig /mutator/build/install/LLVM_Mutation_Tool/lib/ 
# pipx run hatch run src/mua_fuzzer_benchmark/eval.py locator_local --config-path /tmp/config.json --result-path /tmp/test/ # stores infos in /tmp/test


# /tmp/test/progs/xml/xml.locator /benchmark.yaml #create a list of all possible mutations
# cd /mutator && python locator_signal_to_mutation_list.py --trigger-signal-dir /tmp/trigger_signal/ --prog xml --out /tmp/mualist.json && cat /tmp/mualist.json
# cd /mutator && MUT_NUM_CPUS=24 pipx run hatch run src/mua_fuzzer_benchmark/eval.py locator_mutants_local --result-path /tmp/mutants_$(date +"%Y%m%d_%H%M%S") --statsdb /tmp/test/stats.db --mutation-list /tmp/mualist.json
