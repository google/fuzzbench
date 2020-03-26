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

import collections
import shutil
import subprocess
import os
import tempfile

from fuzzers import utils

# OUT environment variable is the location of build directory (default is /out).

# Fuzz each fuzzer for 1 hour before rotating.
SECONDS_PER_FUZZER = 3600


def prepare_build_environment():
    """Set environment variables used to build AFL-based fuzzers."""
    utils.set_no_sanitizer_compilation_flags()

    cflags = ['-O3', '-fsanitize-coverage=trace-pc-guard']
    utils.append_flags('CFLAGS', cflags)
    utils.append_flags('CXXFLAGS', cflags)

    os.environ['CC'] = 'clang'
    os.environ['CXX'] = 'clang++'
    os.environ['FUZZER_LIB'] = '/libAFL.a'


def build():
    """Build benchmark with AFL."""
    prepare_build_environment()

    utils.build_benchmark()

    print('[post_build] Copying afl-fuzz to $OUT directory')
    # Copy out the afl-fuzz binary as a build artifact.
    shutil.copy('/afl/afl-fuzz', os.path.join(os.environ['OUT'], 'afl'))
    shutil.copy('/aflpp/afl-fuzz', os.path.join(os.environ['OUT'], 'aflpp'))
    shutil.copy('/aflsmart/afl-fuzz', os.path.join(os.environ['OUT'],
                                                   'aflsmart'))
    shutil.copy('/fair/afl-fuzz', os.path.join(os.environ['OUT'], 'fair'))
    shutil.copy('/mopt/afl-fuzz', os.path.join(os.environ['OUT'], 'mopt'))


def prepare_fuzz_environment(input_corpus):
    """Prepare to fuzz with AFL or another AFL-based fuzzer."""
    # Tell AFL to not use its terminal UI so we get usable logs.
    os.environ['AFL_NO_UI'] = '1'
    # Skip AFL's CPU frequency check (fails on Docker).
    os.environ['AFL_SKIP_CPUFREQ'] = '1'
    # No need to bind affinity to one core, Docker enforces 1 core usage.
    os.environ['AFL_NO_AFFINITY'] = '1'
    # AFL will abort on startup if the core pattern sends notifications to
    # external programs. We don't care about this.
    os.environ['AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES'] = '1'

    # AFL needs at least one non-empty seed to start.
    if len(os.listdir(input_corpus)) == 0:
        with open(os.path.join(input_corpus, 'default_seed'),
                  'w') as file_handle:
            file_handle.write('hi')


# pylint: disable=too-many-arguments
def run_afl_fuzz(fuzzer_name,
                 input_corpus,
                 output_corpus,
                 target_binary,
                 timeout,
                 additional_flags=None,
                 hide_output=False):
    """Run afl-fuzz."""
    # Spawn the afl fuzzing process.
    # FIXME: Currently AFL will exit if it encounters a crashing input in seed
    # corpus (usually timeouts). Add a way to skip/delete such inputs and
    # re-run AFL. This currently happens with a seed in wpantund benchmark.
    print('[run_fuzzer] Running target with afl-fuzz')
    command = [
        os.path.join('.', fuzzer_name),
        '-i',
        input_corpus,
        '-o',
        output_corpus,
        # Use deterministic mode as it does best when we don't have
        # seeds which is often the case.
        '-d',
        # Use no memory limit as ASAN doesn't play nicely with one.
        '-m',
        'none'
    ]
    if additional_flags:
        command.extend(additional_flags)
    command += [
        '--',
        target_binary,
        # Pass INT_MAX to afl the maximize the number of persistent loops it
        # performs.
        '2147483647'
    ]
    output_stream = subprocess.DEVNULL if hide_output else None
    subprocess.call(command,
                    stdout=output_stream,
                    stderr=output_stream,
                    timeout=timeout)


def fuzz(input_corpus, output_corpus, target_binary):
    """Run afl-fuzz on target."""
    prepare_fuzz_environment(input_corpus)
    fuzzer_queue = collections.deque(
        ['fair', 'mopt', 'afl', 'aflpp', 'aflsmart'], maxlen=5)

    tmp_dir = tempfile.TemporaryDirectory()
    next_fuzzer_input_corpus = os.path.join(str(tmp_dir), 'input_corpus')
    shutil.copytree(input_corpus, next_fuzzer_input_corpus)
    while True:
        fuzzer_name = fuzzer_queue[0]
        try:
            fuzzer_output_dir = os.path.join(output_corpus, fuzzer_name)
            run_afl_fuzz(fuzzer_name, next_fuzzer_input_corpus,
                         fuzzer_output_dir, target_binary, SECONDS_PER_FUZZER)
        except subprocess.TimeoutExpired:
            tmp_dir.cleanup()
            fuzzer_queue.rotate(1)
            next_fuzzer_name = fuzzer_name
            print('Switching to fuzzer to {0}.'.format(next_fuzzer_name))
            tmp_dir = tempfile.TemporaryDirectory()
            next_fuzzer_input_corpus = os.path.join(str(tmp_dir),
                                                    'input_corpus')
            shutil.copytree(os.path.join(fuzzer_output_dir, 'queue'),
                            next_fuzzer_input_corpus)
