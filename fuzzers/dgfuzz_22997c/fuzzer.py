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
"""Integration code for a LibAFL-based fuzzer."""

import os
import sys
import subprocess
from pathlib import Path

from fuzzers import utils


def prepare_fuzz_environment(input_corpus):
    """Prepare to fuzz with a LibAFL-based fuzzer."""
    os.environ['ASAN_OPTIONS'] = 'abort_on_error=1:detect_leaks=0:'\
                                 'malloc_context_size=0:symbolize=0:'\
                                 'allocator_may_return_null=1:'\
                                 'detect_odr_violation=0:handle_segv=0:'\
                                 'handle_sigbus=0:handle_abort=0:'\
                                 'handle_sigfpe=0:handle_sigill=0'
    os.environ['UBSAN_OPTIONS'] =  'abort_on_error=1:'\
                                   'allocator_release_to_os_interval_ms=500:'\
                                   'handle_abort=0:handle_segv=0:'\
                                   'handle_sigbus=0:handle_sigfpe=0:'\
                                   'handle_sigill=0:print_stacktrace=0:'\
                                   'symbolize=0:symbolize_inline_frames=0'
    # Create at least one non-empty seed to start.
    utils.create_seed_file_for_empty_corpus(input_corpus)


def build_dfsan():
    """Build benchmark with dfsan."""
    new_env = os.environ.copy()
    new_env['CC'] = ('/dgfuzz/fuzzers/fuzzbench_dataflow_guided/afl-cc/'
                     'afl-clang-dgfuzz')
    new_env['CXX'] = ('/dgfuzz/fuzzers/fuzzbench_dataflow_guided/afl-cc/'
                      'afl-clang-dgfuzz++')

    new_env['ASAN_OPTIONS'] = 'abort_on_error=0:allocator_may_return_null=1'
    new_env['UBSAN_OPTIONS'] = 'abort_on_error=0'
    new_env['DFSAN_OPTIONS'] = 'strict_data_dependencies=0'
    new_env['AFL_QUIET'] = '1'

    new_env['FUZZER_LIB'] = '/libAFLDriver.a'

    build_directory = new_env['OUT']
    dfsan_build_directory = os.path.join(build_directory, 'dfsan')
    os.mkdir(dfsan_build_directory)
    new_env['OUT'] = dfsan_build_directory

    cfg_file = os.path.join(build_directory, 'aflpp_cfg.bin')
    new_env['AFL_LLVM_CFG_FILE'] = cfg_file
    new_env['AFL_LLVM_FIRST_BUILD'] = '1'
    if os.path.isfile(cfg_file):
        os.remove(cfg_file)
    Path(cfg_file).touch()

    mod_offsets_file = os.path.join(
            build_directory, 'module_cfg_offsets.txt')
    new_env['AFL_LLVM_MODULE_OFFSETS_FILE'] = mod_offsets_file
    Path(mod_offsets_file).touch()
    os.chmod(mod_offsets_file, 0o666)

    src = os.getenv('SRC')
    work = os.getenv('WORK')

    with utils.restore_directory(src), utils.restore_directory(work):
        # Restore SRC to its initial state so we can build again without any
        # trouble. For some OSS-Fuzz projects, build_benchmark cannot be run
        # twice in the same directory without this.
        utils.build_benchmark(env=new_env)

    fuzz_target = os.getenv('FUZZ_TARGET')
    exec_path = os.path.join(dfsan_build_directory, fuzz_target)
    new_path = os.path.join(dfsan_build_directory, fuzz_target + '_dfsan')
    os.rename(exec_path, new_path)


def build():
    """Build benchmark."""

    # first build it with DFSan enabled
    build_dfsan()

    os.environ['CC'] = ('/dgfuzz/fuzzers/fuzzbench_dataflow_guided/target/'
                        'release-fuzzbench/libafl_cc')
    os.environ['CXX'] = ('/dgfuzz/fuzzers/fuzzbench_dataflow_guided/target/'
                         'release-fuzzbench/libafl_cxx')

    os.environ['ASAN_OPTIONS'] = 'abort_on_error=0:allocator_may_return_null=1'
    os.environ['UBSAN_OPTIONS'] = 'abort_on_error=0'

    cflags = ['--libafl']
    utils.append_flags('CFLAGS', cflags)
    utils.append_flags('CXXFLAGS', cflags)
    utils.append_flags('LDFLAGS', cflags)

    os.environ['FUZZER_LIB'] = '/stub_rt.a'
    build_directory = os.environ['OUT']
    cfg_file = os.path.join(build_directory, 'libafl_cfg.bin')
    os.environ['AFL_LLVM_CFG_FILE'] = cfg_file
    if os.path.isfile(cfg_file):
        os.remove(cfg_file)
    Path(cfg_file).touch()
    os.environ['AFL_LLVM_MODULE_OFFSETS_FILE'] = os.path.join(
            build_directory, 'module_cfg_offsets.txt')
    utils.build_benchmark()


def fuzz(input_corpus, output_corpus, target_binary):
    """Run fuzzer."""
    prepare_fuzz_environment(input_corpus)
    dictionary_path = utils.get_dictionary_path(target_binary)
    command = [target_binary]
    if dictionary_path:
        command += (['-x', dictionary_path])

    # Add the control flow graph file
    build_directory = os.environ['OUT']
    cfg_file = os.path.join(build_directory, 'libafl_cfg.bin')
    if os.path.exists(cfg_file):
        command += (['-c', cfg_file])
        dfsan_cfg_file = os.path.join(build_directory, 'aflpp_cfg.bin')
        command += (['-a', dfsan_cfg_file])
    else:
        sys.exit(1)

    # get the dfsan binary
    dfsan_build_directory = os.path.join(build_directory, 'dfsan')
    fuzz_target = os.getenv('FUZZ_TARGET')
    dfsan_fuzz_target = os.path.join(dfsan_build_directory,
                                     fuzz_target + '_dfsan')
    command += (['-d', dfsan_fuzz_target])

    # Add the input and output corpus
    command += (['-o', output_corpus, '-i', input_corpus])
    fuzzer_env = os.environ.copy()
    fuzzer_env['LD_PRELOAD'] = '/usr/lib/x86_64-linux-gnu/libjemalloc.so.2'
    print(command)
    subprocess.check_call(command, cwd=os.environ['OUT'], env=fuzzer_env)
