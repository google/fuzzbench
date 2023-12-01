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
"""Integration code for a LibAFL fuzzer with an AFL++ forkserver."""

import os
import shutil
import subprocess

from fuzzers import utils
from fuzzers.aflplusplus import fuzzer as aflplusplus_fuzzer
from fuzzers.libafl import fuzzer as libafl_fuzzer


def build():
    """Build benchmark."""
    # Build the target with AFL++
    aflplusplus_fuzzer.build('tracepc', 'cmplog', 'dict2file')

    # Copy to fuzzer to OUT
    build_directory = os.environ['OUT']
    fuzzer = '/libafl/fuzzers/fuzzbench_forkserver/' \
              'target/release-fuzzbench/fuzzbench_forkserver'
    shutil.copy(fuzzer, build_directory)


def fuzz(input_corpus, output_corpus, target_binary):
    """Run fuzzer."""
    # Calculate CmpLog binary path from the instrumented target binary.
    target_binary_directory = os.path.dirname(target_binary)
    cmplog_target_binary_directory = \
        aflplusplus_fuzzer.get_cmplog_build_directory(target_binary_directory)
    target_binary_name = os.path.basename(target_binary)
    cmplog_target_binary = os.path.join(cmplog_target_binary_directory,
                                        target_binary_name)

    # Setup env vars
    libafl_fuzzer.prepare_fuzz_environment(input_corpus)

    # Merge dictionaries
    dictionary_path = utils.get_dictionary_path(target_binary)
    if os.path.exists('./afl++.dict'):
        if dictionary_path:
            with open('./afl++.dict', encoding='utf-8') as dictfile:
                autodict = dictfile.read()
            with open(dictionary_path, 'a', encoding='utf-8') as dictfile:
                dictfile.write(autodict)
        else:
            dictionary_path = './afl++.dict'

    # Run the fuzzer
    command = ['./fuzzbench_forkserver', '-c', cmplog_target_binary]
    if dictionary_path:
        command += (['-x', dictionary_path])
    command += (['-o', output_corpus, '-i', input_corpus, target_binary])
    print(command)
    subprocess.check_call(command)
