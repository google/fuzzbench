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
"""Integration code for Collabtive Fuzzer Framework."""

import os
import shutil
import subprocess

from fuzzers import utils
from fuzzers.afl import fuzzer as afl_fuzzer


def get_honggfuzz_target_dir(output_directory):
    """Return path to Honggfuzz's target directory."""
    return os.path.join(output_directory, 'honggfuzz')


def honggfuzz_build():
    """Build benchmark."""
    new_env = os.environ.copy()

    new_env['CC'] = '/honggfuzz/hfuzz_cc/hfuzz-clang'
    new_env['CXX'] = '/honggfuzz/hfuzz_cc/hfuzz-clang++'
    new_env['FUZZER_LIB'] = '/honggfuzz/empty_lib.o'

    utils.build_benchmark(env=new_env)

    print('[post_build] Copying honggfuzz to $OUT directory')
    # Copy over honggfuzz's main fuzzing binary.
    shutil.copy('/honggfuzz/honggfuzz', os.environ['OUT'])
             

def build_honggfuzz():
    """Build benchmark with Honggfuzz."""
    print('Building with Honggfuzz')
    out_dir = os.environ['OUT']
    honggfuzz_target_dir = get_honggfuzz_target_dir(os.environ['OUT'])
    os.environ['OUT'] = honggfuzz_target_dir
    src = os.getenv('SRC')
    work = os.getenv('WORK')
    with utils.restore_directory(src), utils.restore_directory(work):
        # Restore SRC to its initial state so we can build again without any
        # trouble. For some OSS-Fuzz projects, build_benchmark cannot be run
        # twice in the same directory without this.
        honggfuzz_build()
    os.environ['OUT'] = out_dir

def prepare_build_environment():
    """Prepare build environment."""
    honggfuzz_target_dir = get_honggfuzz_target_dir(os.environ['OUT'])

    os.makedirs(honggfuzz_target_dir, exist_ok=True)

def build():
    """Build benchmark."""
    prepare_build_environment()
    new_env = os.environ.copy()
    cflags = ['-fsanitize=fuzzer-no-link']
    utils.append_flags('CFLAGS', cflags, env=new_env)
    utils.append_flags('CXXFLAGS', cflags, env=new_env)
    src = new_env.get('SRC')
    work = new_env.get('WORK')
    new_env['CC'] = 'clang'
    new_env['CXX'] = 'clang++'
    new_env['FUZZER_LIB'] = '/usr/lib/libHCFUZZER.a'
    with utils.restore_directory(src), utils.restore_directory(work):
        utils.build_benchmark(env=new_env)

    build_honggfuzz()
   

def fuzz(input_corpus, output_corpus, target_binary):
    """Run fuzzer. Wrapper that uses the defaults when calling
    run_fuzzer."""
    run_fuzzer(input_corpus,
               output_corpus,
               target_binary,
               extra_flags=['-keep_seed=0', '-cross_over_uniform_dist=1'])


def run_fuzzer(input_corpus, output_corpus, target_binary, extra_flags=None):
    """Run fuzzer."""
    if extra_flags is None:
        extra_flags = []

    # Seperate out corpus and crash directories as sub-directories of
    # |output_corpus| to avoid conflicts when corpus directory is reloaded.
    crashes_dir = os.path.join(output_corpus, 'crashes')
    output_corpus = os.path.join(output_corpus, 'corpus')
    os.makedirs(crashes_dir)
    os.makedirs(output_corpus)

    #prepare_fuzz_environment(input_corpus)
    afl_fuzzer.prepare_fuzz_environment(input_corpus)
    binary = os.path.basename(target_binary)

    os.environ['AFL_IGNORE_UNKNOWN_ENVS'] = '1'
    os.environ['AFL_FAST_CAL'] = '1'
    os.environ['AFL_NO_WARN_INSTABILITY'] = '1'

    flags = [
        '-print_final_stats=1',
        # `close_fd_mask` to prevent too much logging output from the target.
        '-close_fd_mask=3',
        # Run in fork mode to allow ignoring ooms, timeouts, crashes and
        # continue fuzzing indefinitely.
        f'-target_program={binary}',
        '-fuzzers=honggfuzz',
        '-fork=1',
        '-fork_job_budget_coe=2',
        '-fork_num_seeds=3',
        '-fork_max_job_time=600',
        '-ignore_ooms=1',
        '-ignore_timeouts=1',
        '-ignore_crashes=1',

        # Don't use LSAN's leak detection. Other fuzzers won't be using it and
        # using it will cause libFuzzer to find "crashes" no one cares about.
        '-detect_leaks=0',

        # Store crashes along with corpus for bug based benchmarking.
        f'-artifact_prefix={crashes_dir}/',
    ]
    flags += extra_flags
  
    if 'ADDITIONAL_ARGS' in os.environ:
        flags += os.environ['ADDITIONAL_ARGS'].split(' ')
    dictionary_path = utils.get_dictionary_path(target_binary)
    if dictionary_path:
        flags.append('-dict=' + dictionary_path)
 
    command = [target_binary] + flags + [output_corpus, input_corpus]
    print('[run_fuzzer] Running command: ' + ' '.join(command))
    subprocess.check_call(command)
