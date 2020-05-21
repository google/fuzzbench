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

import shutil
import subprocess
import os

from fuzzers import utils

# OUT environment variable is the location of build directory (default is /out).


def prepare_build_environment():
    """Set environment variables used to build targets for AFL-based
    fuzzers."""
    cflags = ['-fsanitize-coverage=trace-pc-guard']
    utils.append_flags('CFLAGS', cflags)
    utils.append_flags('CXXFLAGS', cflags)

    os.environ['CC'] = 'clang'
    os.environ['CXX'] = 'clang++'
    os.environ['FUZZER_LIB'] = '/libAFL.a'


def build():
    """Build benchmark."""
    prepare_build_environment()

    utils.build_benchmark()

    print('[post_build] Copying Ankou to $OUT directory')
    # Copy out the Ankou binary as a build artifact.
    shutil.copy('/Ankou', os.environ['OUT'])


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


def run_ankou_fuzz(input_corpus,
                   output_corpus,
                   target_binary,
                   additional_flags=None,
                   hide_output=False):
    """Run Ankou."""
    print('[run_fuzzer] Running target with Ankou')
    command = [
        './Ankou', '-app', target_binary, '-i', input_corpus, '-o',
        output_corpus
    ]
    if additional_flags:
        command.extend(additional_flags)
    #dictionary_path = utils.get_dictionary_path(target_binary)
    #if dictionary_path:
    #    command.extend(['-dict', dictionary_path])

    print('[run_fuzzer] Running command: ' + ' '.join(command))
    output_stream = subprocess.DEVNULL if hide_output else None
    subprocess.check_call(command, stdout=output_stream, stderr=output_stream)


def fuzz(input_corpus, output_corpus, target_binary):
    """Run Ankou on target."""
    prepare_fuzz_environment(input_corpus)

    run_ankou_fuzz(input_corpus, output_corpus, target_binary)
