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
"""Integration code for ankou fuzzer."""

import shutil
import subprocess
import os

from fuzzers import utils
from fuzzers.afl import fuzzer as afl_fuzzer

# OUT environment variable is the location of build directory (default is /out).


def build():
    """Build benchmark."""
    afl_fuzzer.prepare_build_environment()

    utils.build_benchmark()

    print('[post_build] Copying Ankou to $OUT directory')
    # Copy out the Ankou binary as a build artifact.
    shutil.copy('/Ankou', os.environ['OUT'])


def fuzz(input_corpus, output_corpus, target_binary):
    """Run Ankou on target."""
    afl_fuzzer.prepare_fuzz_environment(input_corpus)

    print('[run_fuzzer] Running target with Ankou')
    command = [
        './Ankou', '-app', target_binary, '-i', input_corpus, '-o',
        output_corpus
    ]
    dictionary_path = utils.get_dictionary_path(target_binary)
    if dictionary_path:
        command.extend(['-dict', dictionary_path])

    print('[run_fuzzer] Running command: ' + ' '.join(command))
    subprocess.check_call(command)
