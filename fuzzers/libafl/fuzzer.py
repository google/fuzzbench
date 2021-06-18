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
import subprocess

from fuzzers import utils


def prepare_fuzz_environment(input_corpus):
    """Prepare to fuzz with a LibAFL-based fuzzer."""
    # Create at least one non-empty seed to start.
    utils.create_seed_file_for_empty_corpus(input_corpus)


def build():  # pylint: disable=too-many-branches,too-many-statements
    """Build benchmark."""
    os.environ['CC'] = '/libafl/fuzzers/fuzzbench/target/release/libafl_cc'
    os.environ['CXX'] = '/libafl/fuzzers/fuzzbench/target/release/libafl_cxx'
    os.environ['FUZZER_LIB'] = '/emptylib.a'
    utils.build_benchmark()


def fuzz(input_corpus, output_corpus, target_binary):
    """Run fuzzer."""
    prepare_fuzz_environment(input_corpus)
    dictionary_path = utils.get_dictionary_path(target_binary)
    command = [target_binary]
    if dictionary_path:
        command += (['-x', dictionary_path])
    command += ([output_corpus, input_corpus])
    print(command)
    subprocess.check_call(command, cwd=os.environ['OUT'])
