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

# This optimized afl++ variant should always be run together with
# "aflplusplus" to show the difference - a default configured afl++ vs.
# a hand-crafted optimized one. afl++ is configured not to enable the good
# stuff by default to be as close to vanilla afl as possible.
# But this means that the good stuff is hidden away in this benchmark
# otherwise.

import os
import subprocess

from fuzzers.aflplusplus import fuzzer as aflplusplus_fuzzer
from fuzzers.afl import fuzzer as afl_fuzzer
from fuzzers import utils


def build():  # pylint: disable=too-many-branches,too-many-statements
    """Build benchmark."""
    aflplusplus_fuzzer.build()

def get_cmplog_build_directory(target_directory):
    """Return path to CmpLog target directory."""
    return os.path.join(target_directory, 'cmplog')

def check_skip_det_compatible(additional_flags):
    """ Checks if additional flags are compatible with '-d' option"""
    # AFL refuses to take in '-d' with '-M' or '-S' options for parallel mode.
    # (cf. https://github.com/google/AFL/blob/8da80951/afl-fuzz.c#L7477)
    if '-M' in additional_flags or '-S' in additional_flags:
        return False
    return True

def fuzz(input_corpus, output_corpus, target_binary):
    """Run fuzzer."""
    os.environ['AFL_SKIP_CRASHES'] = "1"
    # Calculate CmpLog binary path from the instrumented target binary.
    target_binary_directory = os.path.dirname(target_binary)
    cmplog_target_binary_directory = (
        get_cmplog_build_directory(target_binary_directory))
    target_binary_name = os.path.basename(target_binary)
    cmplog_target_binary = os.path.join(cmplog_target_binary_directory,
                                        target_binary_name)

    afl_fuzzer.prepare_fuzz_environment(input_corpus)
    # decomment this to enable libdislocator.
    # os.environ['AFL_ALIGNED_ALLOC'] = '1' # align malloc to max_align_t
    # os.environ['AFL_PRELOAD'] = '/afl/libdislocator.so'

    flags = list()

    if os.path.exists('./afl++.dict'):
        flags += ['-x', './afl++.dict']

    # Move the following to skip for upcoming _double tests:
    if os.path.exists(cmplog_target_binary):
        flags += ['-c', cmplog_target_binary]

    os.environ['AFL_DISABLE_TRIM'] = "1"
    # os.environ['AFL_FAST_CAL'] = '1'
    os.environ['AFL_CMPLOG_ONLY_NEW'] = '1'
    if 'ADDITIONAL_ARGS' in os.environ:
        flags += os.environ['ADDITIONAL_ARGS'].split(' ')

    os.environ['AFL_FAST_CAL'] = '1'

    afl_command = [
        './afl-fuzz',
        '-i',
        input_corpus,
        '-o',
        output_corpus,
        # Use no memory limit as ASAN doesn't play nicely with one.
        '-m',
        'none',
        '-t',
        '1000+',  # Use same default 1 sec timeout, but add '+' to skip hangs.
    ]
    # Use '-d' to skip deterministic mode, as long as it it compatible with
    # flags.
    if not flags or check_skip_det_compatible(flags):
        afl_command.append('-d')
    if flags:
        afl_command.extend(flags)
    dictionary_path = utils.get_dictionary_path(target_binary)
    if dictionary_path:
        afl_command.extend(['-x', dictionary_path])
    afl_command += [
        '--',
        target_binary,
        # Pass INT_MAX to afl the maximize the number of persistent loops it
        # performs.
        '2147483647'
    ]

    command = [
        'muttfuzz',
        '"',
    ]
    command += afl_command

    command += [
        '"',
        target_binary,
        '--initial_fuzz_cmd',
        '"',
    ]

    command+=afl_command

    command += [
        '"',
        '--initial_budget',
        '1800',
        '--budget',
        '86400',
        '--post_mutant_cmd',
        '"cp fuzz_target/crashes.*/id* fuzz_target/queue/; rm -rf fuzz_target/crashes.*"'
    ]

    print('[run_afl_fuzz] Running target with afl-fuzz')
    print(command)

    #subprocess.check_call(command)
