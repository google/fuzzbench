# Copyright 2022 Google LLC
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

    # First, build an instrumented binary for AFL.
    os.environ['CC'] = '/out/AFLplusplus/afl-clang-fast'
    os.environ['CXX'] = '/out/AFLplusplus/afl-clang-fast++'
    os.environ['FUZZER_LIB'] = '/libAFLDriver.a'
    os.environ['AFL_PATH'] = '/out/AFLplusplus/'
    #afl_fuzzer.prepare_build_environment()
    src = os.getenv('SRC')
    work = os.getenv('WORK')
    with utils.restore_directory(src), utils.restore_directory(work):
        # Restore SRC to its initial state so we can build again without any
        # trouble. For some OSS-Fuzz projects, build_benchmark cannot be run
        # twice in the same directory without this.
        utils.build_benchmark()
    print('[build] Copying afl-fuzz to $OUT directory')
    shutil.copy('/out/AFLplusplus/afl-fuzz', os.environ['OUT'])


def fuzz(input_corpus, output_corpus, target_binary):
    """Run fuzzer."""
    #utils.create_seed_file_for_empty_corpus(input_corpus)
    afl_fuzzer.prepare_fuzz_environment(input_corpus)
    os.environ['AFL_DISABLE_TRIM'] = "1"

    # Main instance
    print('[fuzz] Running main AFL worker')
    afl_main_thread = threading.Thread(target=afl_fuzzer.run_afl_fuzz,
                                       args=(input_corpus, output_corpus,
                                             target_binary, ['-M', 'afl-main']))
    afl_main_thread.start()
    time.sleep(5)

    # Secondary instance
    print('[fuzz] Running secondary AFL worker')
    afl_secondary_thread = threading.Thread(target=afl_fuzzer.run_afl_fuzz,
                                            args=(input_corpus, output_corpus,
                                                  target_binary,
                                                  ['-S',
                                                   'afl-secondary'], True))
    afl_secondary_thread.start()

    print('[fuzz] Now waiting for threads to finish...')
    afl_main_thread.join()
    afl_secondary_thread.join()
