# Copyright 2021 Google LLC
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
''' Uses the SymSan-AFL hybrid from SymSan. '''

import shutil
import os
import subprocess
import threading

from fuzzers.afl import fuzzer as afl_fuzzer
from fuzzers.aflplusplus import fuzzer as aflplusplus_fuzzer

# Helper library that contains important functions for building.
from fuzzers import utils


def is_benchmark(name):
    """Check the benchmark under built."""
    benchmark = os.getenv('BENCHMARK', None)
    return benchmark is not None and name in benchmark


def get_symsan_build_dir(target_directory):
    """Return path to CmpLog target directory."""
    return os.path.join(target_directory, 'symsantrack')


def get_symsan_build_fast_dir(target_directory):
    """Return path to CmpLog target directory."""
    return os.path.join(target_directory, 'symsanfast')


#def is_benchmark(name):
#    benchmark = os.getenv('BENCHMARK', None)
#    return benchmark is not None and name in benchmark


def get_cmplog_build_directory(target_directory):
    """Return path to CmpLog target directory."""
    return os.path.join(target_directory, 'cmplog')


def build_symsan_fast(build_directory, src, work):
    """Build symsan fast binaries."""
    symsan_build_fast_directory = get_symsan_build_fast_dir(build_directory)
    os.mkdir(symsan_build_fast_directory)

    new_env = os.environ.copy()
    new_env['CC'] = '/symsan/build/bin/ko-clang'
    new_env['CXX'] = '/symsan/build/bin/ko-clang++'
    new_env['KO_CC'] = 'clang-12'
    new_env['KO_CXX'] = 'clang++-12'
    new_env['CXXFLAGS'] = '-stdlib=libc++'
    new_env['KO_USE_NATIVE_LIBCXX'] = '1'
    new_env['CFLAGS'] = ''
    #new_env['CXXFLAGS'] = new_env['CXXFLAGS'].replace("-stlib=libc++", "")
    new_env['FUZZER_LIB'] = '/libfuzzer-harness-fast.o'
    new_env['OUT'] = symsan_build_fast_directory
    new_env['KO_DONT_OPTIMIZE'] = '1'

    if is_benchmark('curl_curl_fuzzer_http'):
        new_env['SANITIZER'] = 'memory'

    fuzz_target = os.getenv('FUZZ_TARGET')
    if fuzz_target:
        new_env['FUZZ_TARGET'] = os.path.join(symsan_build_fast_directory,
                                              os.path.basename(fuzz_target))

    with utils.restore_directory(src), utils.restore_directory(work):
        utils.build_benchmark(env=new_env)


def build_symsan(build_directory, src, work):
    """Build symsan track binaries."""
    symsan_build_directory = get_symsan_build_dir(build_directory)
    os.mkdir(symsan_build_directory)
    new_env = os.environ.copy()
    new_env['CC'] = '/symsan/build/bin/ko-clang'
    new_env['CXX'] = '/symsan/build/bin/ko-clang++'
    new_env['KO_CC'] = 'clang-12'
    new_env['KO_CXX'] = 'clang++-12'
    #new_env['CXXFLAGS'] = new_env['CXXFLAGS'].replace("-stlib=libc++", "")
    new_env['CXXFLAGS'] = ''
    new_env['CFLAGS'] = ''
    new_env['FUZZER_LIB'] = '/libfuzzer-harness.o'
    new_env['OUT'] = symsan_build_directory
    new_env['KO_DONT_OPTIMIZE'] = '1'
    new_env['USE_TRACK'] = '1'
    new_env['KO_USE_FASTGEN'] = '1'
    if is_benchmark('curl_curl_fuzzer_http'):
        new_env['SANITIZER'] = 'memory'

        # For CmpLog build, set the OUT and FUZZ_TARGET environment
        # variable to point to the new CmpLog build directory.
    fuzz_target = os.getenv('FUZZ_TARGET')
    if fuzz_target:
        new_env['FUZZ_TARGET'] = os.path.join(symsan_build_directory,
                                              os.path.basename(fuzz_target))

    with utils.restore_directory(src), utils.restore_directory(work):
        utils.build_benchmark(env=new_env)


def build():  # pylint: disable=too-many-branches,too-many-statements
    """Build benchmark."""
    # BUILD_MODES is not already supported by fuzzbench, meanwhile we provide
    # a default configuration.

    src = os.getenv('SRC')
    work = os.getenv('WORK')
    build_directory = os.environ['OUT']

    with utils.restore_directory(src), utils.restore_directory(work):
        build_symsan(build_directory, src, work)
        build_symsan_fast(build_directory, src, work)
        aflplusplus_fuzzer.build('tracepc', 'cmplog', 'dict2file')

    shutil.copy('/symsan/target/release/fastgen', os.environ['OUT'])


def check_skip_det_compatible(additional_flags):
    """ Checks if additional flags are compatible with '-d' option"""
    # AFL refuses to take in '-d' with '-M' or '-S' options for parallel mode.
    # (cf. https://github.com/google/AFL/blob/8da80951/afl-fuzz.c#L7477)
    if '-M' in additional_flags or '-S' in additional_flags:
        return False
    return True


def launch_afl_thread(input_corpus, output_corpus, target_binary,
                      additional_flags):
    """ Simple wrapper for running AFL. """
    afl_thread = threading.Thread(target=afl_fuzzer.run_afl_fuzz,
                                  args=(input_corpus, output_corpus,
                                        target_binary, additional_flags))
    afl_thread.start()
    return afl_thread


def fuzz(input_corpus, output_corpus, target_binary, flags=tuple(), skip=False):
    """Run fuzzer."""
    # Calculate CmpLog binary path from the instrumented target binary.
    target_binary_directory = os.path.dirname(target_binary)
    cmplog_target_binary_directory = (
        get_cmplog_build_directory(target_binary_directory))
    target_binary_name = os.path.basename(target_binary)
    cmplog_target_binary = os.path.join(cmplog_target_binary_directory,
                                        target_binary_name)

    target_binary_name = os.path.basename(target_binary)

    symsantrack_binary = os.path.join(
        get_symsan_build_dir(target_binary_directory), target_binary_name)
    symsanfast_binary = os.path.join(
        get_symsan_build_fast_dir(target_binary_directory), target_binary_name)

    afl_fuzzer.prepare_fuzz_environment(input_corpus)
    # decomment this to enable libdislocator.
    # os.environ['AFL_ALIGNED_ALLOC'] = '1' # align malloc to max_align_t
    # os.environ['AFL_PRELOAD'] = '/afl/libdislocator.so'

    flags = list(flags)

    if os.path.exists('./afl++.dict'):
        flags += ['-x', './afl++.dict']
    # Move the following to skip for upcoming _double tests:
    if os.path.exists(cmplog_target_binary):
        flags += ['-c', cmplog_target_binary]

    if not skip:
        if not flags or not flags[0] == '-Q' and '-p' not in flags:
            flags += ['-p', 'fast']
        if ((not flags or (not '-l' in flags and not '-R' in flags)) and
                os.path.exists(cmplog_target_binary)):
            flags += ['-l', '2']
        os.environ['AFL_DISABLE_TRIM'] = '1'
        if 'ADDITIONAL_ARGS' in os.environ:
            flags += os.environ['ADDITIONAL_ARGS'].split(' ')
    print('target binary is ' + target_binary)
    #run fastgen
    fastgen_cmd = [
        '/bin/bash', '-ex', '/out/fuz.sh', symsantrack_binary, symsanfast_binary
    ]
    fastgen_restart_cmd = [
        '/bin/bash', '-ex', '/out/fres.sh', symsantrack_binary,
        symsanfast_binary
    ]

    launch_afl_thread(input_corpus,
                      output_corpus,
                      target_binary,
                      additional_flags=flags)

    with subprocess.Popen(fastgen_cmd, stdout=None, stderr=None) as ori:
        ori.wait()

    while True:
        with subprocess.Popen(fastgen_restart_cmd, stdout=None,
                              stderr=None) as res:
            res.wait()
