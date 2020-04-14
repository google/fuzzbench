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
import threading
import subprocess

from fuzzers import utils

from fuzzers.afl import fuzzer as afl_fuzzer


def prepare_build_environment():
    """Set environment variables used to build benchmark."""

    # Update compiler flags for clang-3.8
    # -lstdc++
    cflags = ['-fPIC']
    cppflags = cflags + ['-I/usr/local/include/c++/v1/', '-stdlib=libc++', '-std=c++11']
    utils.append_flags('CFLAGS', cflags)
    utils.append_flags('CXXFLAGS', cppflags)
   
    # Setup aflcc compiler
    os.environ['LLVM_CONFIG'] = 'llvm-config-3.8'
    os.environ['CC'] = '/afl/aflc-gclang'
    os.environ['CXX'] = '/afl/aflc-gclang++'
    os.environ['FUZZER_LIB'] = '/libAFL.a -L/ -lAflccMock -lpthread'


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
    cppflags = ' '.join(['-I/usr/local/include/c++/v1/', '-stdlib=libc++', '-std=c++11'])
    ldflags = ' '.join(['-lpthread', '-lm', ' -lz'])

    # the original afl binary
    print('[post_build] Generating original afl build')
    os.environ['AFL_COVERAGE_TYPE'] = 'ORIGINAL'
    os.environ['AFL_CONVERT_COMPARISON_TYPE'] = 'NONE'
    os.environ['AFL_DICT_TYPE'] = 'NORMAL'
    bin1_cmd = "{compiler} {flags} -O3 {target}.bc -o {target}-original {ldflags}".format(compiler='/afl/aflc-clang-fast++', flags=cppflags, target=fuzz_target, ldflags=ldflags)
    if 0 != os.system(bin1_cmd):
        raise ValueError("command '{command}' failed".format(command=bin1_cmd))

    # the normalized build with optimized dictionary
    print('[post_build] Generating normalized-none-opt')
    os.environ['AFL_COVERAGE_TYPE'] = 'ORIGINAL'
    os.environ['AFL_CONVERT_COMPARISON_TYPE'] = 'NONE'
    os.environ['AFL_DICT_TYPE'] = 'OPTIMIZED'
    bin2_cmd = "{compiler} {flags} {target}.bc -o {target}-normalized-none-opt {ldflags}".format(compiler='/afl/aflc-clang-fast++', flags=cppflags, target=fuzz_target, ldflags=ldflags)
    if 0 != os.system(bin2_cmd):
        raise ValueError("command '{command}' failed".format(command=bin2_cmd))

    # the no-collision split-condition optimized dictionary
    print('[post_build] Generating no-collision-all-opt build')
    os.environ['AFL_COVERAGE_TYPE'] = 'NO_COLLISION'
    os.environ['AFL_CONVERT_COMPARISON_TYPE'] = 'ALL'
    os.environ['AFL_DICT_TYPE'] = 'OPTIMIZED'
    bin3_cmd = "{compiler} {flags} {target}.bc -o {target}-no-collision-all-opt {ldflags}".format(compiler='/afl/aflc-clang-fast++', flags=cppflags, target=fuzz_target, ldflags=ldflags)
    if 0 != os.system(bin3_cmd):
        raise ValueError("command '{command}' failed".format(command=bin3_cmd))

    print('[post_build] Copying afl-fuzz to $OUT directory')
    # Copy out the afl-fuzz binary as a build artifact.
    shutil.copy('/afl/afl-fuzz', os.environ['OUT'])


def run_fuzz(input_corpus,
                 output_corpus,
                 target_binary,
                 additional_flags=None,
                 hide_output=False):
    """Run afl-fuzz."""
    # Spawn the afl fuzzing process.
    # FIXME: Currently AFL will exit if it encounters a crashing input in seed
    # corpus (usually timeouts). Add a way to skip/delete such inputs and
    # re-run AFL.
    print('[run_fuzzer] Running target with afl-fuzz')
    command = [
        './afl-fuzz',
        '-i',
        input_corpus,
        '-o',
        output_corpus,
        # Use no memory limit as ASAN doesn't play nicely with one.
        '-m',
        'none'
    ]
    if additional_flags:
        command.extend(additional_flags)
    dictionary_path = utils.get_dictionary_path(target_binary)
    if dictionary_path:
        command.extend(['-x', dictionary_path])
    command += [
        '--',
        target_binary,
        # Pass INT_MAX to afl the maximize the number of persistent loops it
        # performs.
        '2147483647'
    ]
    print('[run_fuzzer] Running command: ' + ' '.join(command))
    output_stream = subprocess.DEVNULL if hide_output else None
    subprocess.call(command, stdout=output_stream, stderr=output_stream)


def fuzz(input_corpus, output_corpus, target_binary):
    """Run fuzzer."""
    afl_fuzzer.prepare_fuzz_environment(input_corpus)

    # Note: dictionary automatically added by run_afl_fuzz
    print('[run_fuzzer] Running AFL for original binary')
    afl_fuzz_thread1 = threading.Thread(target=run_fuzz,
                                       args=(input_corpus, output_corpus,
                                             "{target}-original".format(target=target_binary), 
                                             ['-S', 'afl-slave-original']))
    afl_fuzz_thread1.start()

    print('[run_fuzzer] Running AFL for normalized and optimized dictionary')
    afl_fuzz_thread2 = threading.Thread(target=run_fuzz,
                                       args=(input_corpus, output_corpus,
                                             "{target}-normalized-none-opt".format(target=target_binary), 
                                             ['-S', 'afl-slave-normalized-opt']))
    afl_fuzz_thread2.start()

    print('[run_fuzzer] Running AFL for FBSP and optimized dictionary')
    run_fuzz(input_corpus,
                        output_corpus,
                        "{target}-no-collision-all-opt".format(target=target_binary), 
                        ['-S', 'afl-slave-no-collision-all-opt'],
                        hide_output=False)
