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
#
"""Integration code for AFLplusplus fuzzer."""
import json
import os
import shutil
import subprocess

from fuzzers.afl import fuzzer as afl_fuzzer
from fuzzers import utils

def build(*args):  # pylint: disable=too-many-branches,too-many-statements
    """Build benchmark."""
    
    build_directory = os.environ['OUT']
    
    os.environ['CC'] = '/bulbasaur/afl_llvm_mode/afl-cc'
    os.environ['CXX'] = '/bulbasaur/afl_llvm_mode/afl-c++'
    # Generate an extra dictionary.
    os.environ['AFL_LLVM_DICT2FILE'] = build_directory + '/afl++.dict'
    os.environ['AFL_LLVM_DICT2FILE_NO_MAIN'] = '1'

    # LibFuzzer driver
    os.environ['FUZZER_LIB'] = '/libAFLDriver.a'

    # Some benchmarks like lcms. (see:
    # https://github.com/mm2/Little-CMS/commit/ab1093539b4287c233aca6a3cf53b234faceb792#diff-f0e6d05e72548974e852e8e55dffc4ccR212)
    # fail to compile if the compiler outputs things to stderr in unexpected
    # cases. Prevent these failures by using AFL_QUIET to stop afl-clang-fast
    # from writing AFL specific messages to stderr.

    src = os.getenv('SRC')
    work = os.getenv('WORK')

    with utils.restore_directory(src), utils.restore_directory(work):
        # Restore SRC to its initial state so we can build again without any
        # trouble. For some OSS-Fuzz projects, build_benchmark cannot be run
        # twice in the same directory without this.
        utils.build_benchmark()
    
    # build trace target
    trace_new_env = os.environ.copy()
    trace_new_env['USE_TRACE'] = '1'

    trace_build_directory = os.path.join(build_directory, 'trace')
    os.mkdir(trace_build_directory)
    trace_new_env['OUT'] = trace_build_directory
        
    fuzz_target = os.getenv('FUZZ_TARGET')
    if fuzz_target:
        trace_new_env['FUZZ_TARGET'] = os.path.join(trace_build_directory,
                                              os.path.basename(fuzz_target))
        
    print('Re-building benchmark for Trace fuzzing target')
    with utils.restore_directory(src), utils.restore_directory(work):
        utils.build_benchmark(env=trace_new_env)
            
    # build fast target
    new_env = os.environ.copy()
    new_env['USE_FAST'] = '1'
        
    fast_build_directory = os.path.join(build_directory, 'fast')
    os.mkdir(fast_build_directory)
    new_env['OUT'] = fast_build_directory
        
    fuzz_target = os.getenv('FUZZ_TARGET')
    if fuzz_target:
        new_env['FUZZ_TARGET'] = os.path.join(fast_build_directory,
                                              os.path.basename(fuzz_target))
            
    print('Re-building benchmark for Fast fuzzing target')
    utils.build_benchmark(env=new_env)

    dst_dir = os.path.join(build_directory, 'bulbasaur')  # build_directory = '/out'
    shutil.copytree('/bulbasaur', dst_dir)


# pylint: disable=too-many-arguments
def fuzz(input_corpus,
         output_corpus,
         target_binary,
         flags=tuple(),
         skip=False,
         no_cmplog=False):  # pylint: disable=too-many-arguments
    """Run fuzzer."""
    # Calculate CmpLog binary path from the instrumented target binary.
    
    target_binary_directory = os.path.dirname(target_binary)
    target_binary_name = os.path.basename(target_binary)
    
    fast_target_binary_directory = os.path.join(target_binary_directory, 'fast')
    fast_target_binary = os.path.join(fast_target_binary_directory, target_binary_name)
    
    trace_target_binary_directory = os.path.join(target_binary_directory, 'trace')
    trace_target_binary = os.path.join(trace_target_binary_directory, target_binary_name)

    afl_fuzzer.prepare_fuzz_environment(input_corpus)
    
    # Don't bind cpu.
    os.environ['DISABLE_BPFUZZ_BIND'] = '1'
    
    command = [
        './bulbasaur/target/release/fuzzer',
        '-i',
        input_corpus,
        '-o',
        os.path.join(output_corpus, 'output'),
        '-j',
        '1',
        '-x',
        './afl++.dict',
        '-f',
        target_binary,
        '-t',
        trace_target_binary,
    ]
    
    dictionary_path = utils.get_dictionary_path(target_binary)
    if dictionary_path:
        command.extend(['-x', dictionary_path])
        
    command += [
        '--',
        fast_target_binary,
    ]
    
    print('[run_bpfuzz] Running command: ' + ' '.join(command))
    output_stream = None
    subprocess.check_call(command, stdout=output_stream, stderr=output_stream)
