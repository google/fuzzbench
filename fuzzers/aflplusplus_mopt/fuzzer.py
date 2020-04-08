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
"""Integration code for AFLplusplus fuzzer."""

import os

from fuzzers.afl import fuzzer as afl_fuzzer
from fuzzers.aflplusplus import fuzzer as aflplusplus_fuzzer

# OUT environment variable is the location of build directory (default is /out).


def build():
    """Build benchmark."""
    aflplusplus_fuzzer.build()


def fuzz(input_corpus, output_corpus, target_binary):
    """Run fuzzer."""
    # Calculate CmpLog binary path from the instrumented target binary.
    target_binary_directory = os.path.dirname(target_binary)
    cmplog_target_binary_directory = (
        aflplusplus_fuzzer.get_cmplog_build_directory(target_binary_directory))
    target_binary_name = os.path.basename(target_binary)
    cmplog_target_binary = os.path.join(cmplog_target_binary_directory,
                                        target_binary_name)

    afl_fuzzer.prepare_fuzz_environment(input_corpus)

    flags = ['-L0']  # afl++ MOpt activation at once.
    flags += ['-prare']  # rare branch scheduling.
    flags += ['-s123']  # fixed random seed.
    if os.path.exists(cmplog_target_binary):
        flags += ['-c', cmplog_target_binary]
    if 'ADDITIONAL_ARGS' in os.environ:
        flags += os.environ['ADDITIONAL_ARGS'].split(' ')

    afl_fuzzer.run_afl_fuzz(input_corpus,
                            output_corpus,
                            target_binary,
                            additional_flags=flags)
