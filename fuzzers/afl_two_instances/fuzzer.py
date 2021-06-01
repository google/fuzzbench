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
"""Integration code for two AFL instances. This one is useful 
   since some hybrid fuzzers rely on multiple processes, e.g.
   one for AFL and one for concolic execution, and thus potentially
   claim more total CPU power than a single AFL process. Examples
   of this include SymCC and Eclipser.
   This integration is to have a fairer comparison between such 
   integrations."""

import time
import threading

from fuzzers.afl import fuzzer as afl_fuzzer


def build():
    """Build benchmark."""
    afl_fuzzer.build()


def fuzz(input_corpus, output_corpus, target_binary):
    """Run fuzzer."""
    afl_fuzzer.prepare_fuzz_environment(input_corpus)

    # Master instance
    afl_master_thread = threading.Thread(target=afl_fuzzer.run_afl_fuzz,
                                         args=(input_corpus, output_corpus,
                                               target_binary,
                                               ['-M', 'afl-master']))
    afl_master_thread.start()
    time.sleep(5)
    # Secondary instance
    afl_secondary_thread = threading.Thread(target=afl_fuzzer.run_afl_fuzz,
                                            args=(input_corpus, output_corpus,
                                                  target_binary,
                                                  ['-S', 'afl-secondary']))
    afl_secondary_thread.start()
