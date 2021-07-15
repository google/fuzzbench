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
"""Integration code for Fuzzolic fuzzer. Note that starting from v2.0, Fuzzolic
relies on AFL to perform random-based fuzzing."""

import shutil
import subprocess
import os
import threading
import time

from fuzzers import utils
from fuzzers.afl import fuzzer as afl_fuzzer


def get_uninstrumented_outdir(target_directory):
    """Return path to uninstrumented target directory."""
    return os.path.join(target_directory, 'uninstrumented')


def build():
    """Build benchmark."""

    # Backup the environment.
    new_env = os.environ.copy()
    src = os.getenv('SRC')
    work = os.getenv('WORK')
    out = os.getenv('OUT')

    # First, build an instrumented binary for AFL.
    os.environ['CC'] = '/out/AFLplusplus/afl-clang-fast'
    os.environ['CXX'] = '/out/AFLplusplus/afl-clang-fast++'
    os.environ['FUZZER_LIB'] = '/libAFLDriver.a'
    os.environ['AFL_PATH'] = '/out/AFLplusplus/'
    os.environ['AFL_LLVM_DICT2FILE'] = out + '/afl++.dict'
    #afl_fuzzer.prepare_build_environment()
    with utils.restore_directory(src), utils.restore_directory(work):
        # Restore SRC to its initial state so we can build again without any
        # trouble. For some OSS-Fuzz projects, build_benchmark cannot be run
        # twice in the same directory without this.
        utils.build_benchmark()
    print('[build] Copying afl-fuzz to $OUT directory')
    shutil.copy('/out/AFLplusplus/afl-fuzz', os.environ['OUT'])

    # Next, build an uninstrumented binary for Fuzzolic.
    new_env['CC'] = 'clang'
    new_env['CXX'] = 'clang++'
    new_env['FUZZER_LIB'] = '/libStandaloneFuzzTarget.a'
    # Ensure to compile with NO_SANITIZER_COMPAT* flags even for bug benchmarks,
    # as QEMU is incompatible with sanitizers. Also, Fuzzolic prefers clean and
    # unoptimized binaries. We leave fast random fuzzing as AFL's job.
    new_env['CFLAGS'] = ' '.join(utils.NO_SANITIZER_COMPAT_CFLAGS)
    cxxflags = [utils.LIBCPLUSPLUS_FLAG] + utils.NO_SANITIZER_COMPAT_CFLAGS
    new_env['CXXFLAGS'] = ' '.join(cxxflags)
    uninstrumented_outdir = get_uninstrumented_outdir(os.environ['OUT'])
    os.mkdir(uninstrumented_outdir)
    new_env['OUT'] = uninstrumented_outdir
    fuzz_target = os.getenv('FUZZ_TARGET')
    if fuzz_target:
        targ_name = os.path.basename(fuzz_target)
        new_env['FUZZ_TARGET'] = os.path.join(uninstrumented_outdir, targ_name)
    print('[build] Re-building benchmark for uninstrumented fuzzing target')
    with utils.restore_directory(src), utils.restore_directory(work):
        utils.build_benchmark(env=new_env)


def fuzzolic(input_corpus, output_corpus, target_binary):
    """Run Fuzzolic."""
    # We will use output_corpus as a directory where AFL and Fuzzolic sync their
    # test cases with each other. For Fuzzolic, we should explicitly specify an
    # output directory under this sync directory.
    if input_corpus:
        fuzzolic_out = os.path.join(output_corpus, "fuzzolic_output")
    afl_out = os.path.join(output_corpus, "afl-worker")
    afl_queue = os.path.join(afl_out, "queue")
    command = [
        '/out/fuzzolic/fuzzolic/fuzzolic.py',
        '-p',  # optimistic solving
        '-r',  # address reasoning
        '-l',  # symbolic libc models
        '-t',  # timeout
        '90000',
        '-a',
        afl_out,
        '-i',
        afl_queue,
        '-o',
        fuzzolic_out,
        '--',
        target_binary,
    ]
    print('[fuzzolic] Running Fuzzolic with command: ' + ' '.join(command))
    subprocess.Popen(command)


def afl_worker(input_corpus, output_corpus, target_binary):
    """Run AFL worker instance."""
    print('[afl_worker] Run AFL worker')
    #dictionary_path = utils.get_dictionary_path(target_binary)
    #if dictionary_path:
    #    command += (['-x', dictionary_path])
    afl_fuzzer.run_afl_fuzz(input_corpus, output_corpus, target_binary,
                            ['-S', 'afl-worker'], True)


def fuzz(input_corpus, output_corpus, target_binary):
    """Run fuzzer."""
    #utils.create_seed_file_for_empty_corpus(input_corpus)
    afl_fuzzer.prepare_fuzz_environment(input_corpus)

    print('[fuzz] Running AFL worker')
    os.environ['AFL_DISABLE_TRIM'] = "1"
    afl_args = (input_corpus, output_corpus, target_binary)
    afl_worker_thread = threading.Thread(target=afl_worker, args=afl_args)
    afl_worker_thread.start()
    time.sleep(5)

    print('[fuzz] Running Fuzzolic')
    target_binary_directory = os.path.dirname(target_binary)
    uninstrumented_target_binary_directory = (
        get_uninstrumented_outdir(target_binary_directory))
    target_binary_name = os.path.basename(target_binary)
    uninstrumented_target_binary = os.path.join(
        uninstrumented_target_binary_directory, target_binary_name)
    fuzzolic_args = (input_corpus, output_corpus, uninstrumented_target_binary)
    fuzzolic_thread = threading.Thread(target=fuzzolic, args=fuzzolic_args)
    fuzzolic_thread.start()

    print('[fuzz] Now waiting for threads to finish...')
    afl_worker_thread.join()
    fuzzolic_thread.join()
