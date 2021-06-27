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
"""Integration code for Eclipser fuzzer. Note that starting from v2.0, Eclipser
relies on AFL to perform random-based fuzzing."""

import os
import shutil
import threading

from fuzzers.aflplusplus import fuzzer as aflplusplus_fuzzer


def get_uninstrumented_outdir(target_directory):
    """Return path to uninstrumented target directory."""
    return os.path.join(target_directory, 'uninstrumented')


def build():
    """Build benchmark."""
    build_directory = os.getenv('OUT')
    fuzz_target = os.getenv('FUZZ_TARGET')

    # First, build an uninstrumented binary.
    aflplusplus_fuzzer.build("qemu", "eclipser")
    qemu_dir = get_uninstrumented_outdir(build_directory)
    os.mkdir(qemu_dir)
    fuzz_binary = build_directory + '/' + fuzz_target
    shutil.copy(fuzz_binary, qemu_dir)
    if os.path.isdir(build_directory + '/seeds'):
        shutil.rmtree(build_directory + '/seeds')

    aflplusplus_fuzzer.build("tracepc")
    shutil.copy('/afl/afl-fuzz', build_directory)


def afl_worker1(input_corpus, output_corpus, target_binary):
    """Run AFL worker instance."""
    print('[afl_worker] Run AFL worker1')
    aflplusplus_fuzzer.fuzz(input_corpus,
                            output_corpus,
                            target_binary,
                            flags=(['-S', 'afl-worker1']),
                            no_cmplog=True)


def afl_worker2(input_corpus, output_corpus, target_binary):
    """Run AFL worker instance."""
    print('[afl_worker] Run AFL worker2')
    aflplusplus_fuzzer.fuzz(input_corpus,
                            output_corpus,
                            target_binary,
                            flags=(['-S', 'afl-worker2', '-Q', '-c0']),
                            skip=True,
                            no_cmplog=True)


def fuzz(input_corpus, output_corpus, target_binary):
    """Run fuzzer."""

    if not os.path.isdir(input_corpus):
        raise Exception("invalid input directory")
    afl_args = (input_corpus, output_corpus, target_binary)
    print('[fuzz] Running AFL worker 1')
    afl_worker_thread = threading.Thread(target=afl_worker1, args=afl_args)
    afl_worker_thread.start()
    print('[fuzz] Running AFL workser 2')
    target_binary_directory = os.path.dirname(target_binary)
    uninstrumented_target_binary_directory = (
        get_uninstrumented_outdir(target_binary_directory))
    target_binary_name = os.path.basename(target_binary)
    uninstrumented_target_binary = os.path.join(
        uninstrumented_target_binary_directory, target_binary_name)
    afl_args = (input_corpus, output_corpus, uninstrumented_target_binary)
    eclipser_thread = threading.Thread(target=afl_worker2, args=afl_args)
    eclipser_thread.start()
    print('[fuzz] Now waiting for threads to finish...')
    afl_worker_thread.join()
    eclipser_thread.join()
