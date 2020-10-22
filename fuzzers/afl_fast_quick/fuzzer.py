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
"""Integration code for AFL fuzzer."""

# This optimized afl++ variant should always be run together with
# "aflplusplus" to show the difference - a default configured afl++ vs.
# a hand-crafted optimized one. afl++ is configured not to enable the good
# stuff by default to be as close to vanilla afl as possible.
# But this means that the good stuff is hidden away in this benchmark
# otherwise.

import subprocess

from fuzzers import utils
from fuzzers.afl import fuzzer as afl_fuzzer


def build():  # pylint: disable=too-many-branches,too-many-statements
    """Build benchmark."""
    afl_fuzzer.build()

def run_afl_fuzz(input_corpus,
                 output_corpus,
                 target_binary,
                 additional_flags=None,
                 hide_output=False):
    """Run afl-fuzz."""
    # Spawn the afl fuzzing process.
    print('[run_afl_fuzz] Running target with afl-fuzz')
    command = [
        './afl-fuzz',
        '-i',
        input_corpus,
        '-o',
        output_corpus,
        # Use deterministic mode as it does best when we don't have
        # seeds which is often the case.
        '-d',
        # Use no memory limit as ASAN doesn't play nicely with one.
        '-m',
        'none',
        '-t',
        '10+', # Substantially reduced timeout. 
    ]
    if additional_flags:
        command.extend(additional_flags)
    dictionary_path = utils.get_dictionary_path(target_binary)
    if dictionary_path:
        command.extend(['-x', dictionary_path])
    command += [
        '--',
        target_binary,
        # Pass INT_MAX to afl the maximize the number of persistent loops it
        # performs.
        '2147483647'
    ]
    print('[run_afl_fuzz] Running command: ' + ' '.join(command))
    output_stream = subprocess.DEVNULL if hide_output else None
    subprocess.check_call(command, stdout=output_stream, stderr=output_stream)


def fuzz(input_corpus, output_corpus, target_binary):
    """Run afl-fuzz on target."""
    afl_fuzzer.prepare_fuzz_environment(input_corpus)

    run_afl_fuzz(input_corpus, output_corpus, target_binary)

