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
"""Integration code for AFLcc fuzzer."""

import threading

from fuzzers.aflcc import fuzzer as aflcc_fuzzer


def build():
    """Build benchmark."""
    aflcc_fuzzer.build()


def fuzz(input_corpus, output_corpus, target_binary):
    """Run fuzzer."""
    aflcc_fuzzer.prepare_fuzz_environment(input_corpus)

    # Note: dictionary automatically added by run_fuzzer().

    # Don't use a dictionary for original afl.
    print('[fuzz] Running AFL for original binary')
    afl_fuzz_thread1 = threading.Thread(
        target=aflcc_fuzzer.run_fuzzer,
        args=(input_corpus, output_corpus,
              '{target}-original'.format(target=target_binary),
              ['-S', 'slave-original']))
    afl_fuzz_thread1.start()

    print('[run_fuzzer] Running AFL for normalized and optimized dictionary')
    afl_fuzz_thread2 = threading.Thread(
        target=aflcc_fuzzer.run_fuzzer,
        args=(input_corpus, output_corpus,
              '{target}-normalized-none-nopt'.format(target=target_binary),
              ['-S', 'slave-normalized-nopt']))
    afl_fuzz_thread2.start()

    print('[run_fuzzer] Running AFL for FBSP and optimized dictionary')
    aflcc_fuzzer.run_fuzzer(
        input_corpus,
        output_corpus,
        '{target}-no-collision-all-opt'.format(target=target_binary),
        ['-S', 'slave-no-collision-all-opt'],
        hide_output=False)
