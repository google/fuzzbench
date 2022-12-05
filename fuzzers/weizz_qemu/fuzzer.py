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
"""Integration code for weizz fuzzer."""

import os
import shutil
import subprocess

from fuzzers import utils


def build():
    """Build benchmark."""
    os.environ['CC'] = 'clang'
    os.environ['CXX'] = 'clang++'
    os.environ['FUZZER_LIB'] = '/libQEMU.a'
    # QEMU doesn't like ASan
    cflags = filter(lambda flag: not flag.startswith('-fsanitize=address'),
                    os.environ['CFLAGS'].split())
    cxxflags = filter(lambda flag: not flag.startswith('-fsanitize=address'),
                      os.environ['CXXFLAGS'].split())
    os.environ['CFLAGS'] = ' '.join(cflags)
    os.environ['CXXFLAGS'] = ' '.join(cxxflags)

    utils.build_benchmark()

    # Copy over weizz's binaries.
    shutil.copy('/weizz/weizz', os.environ['OUT'])
    shutil.copy('/weizz/weizz-qemu', os.environ['OUT'])


def fuzz(input_corpus, output_corpus, target_binary):
    """Run fuzzer."""
    # FIXME: Share code with afl.fuzz.
    os.environ['WEIZZ_NO_UI'] = '1'
    os.environ['WEIZZ_SKIP_CPUFREQ'] = '1'
    os.environ['WEIZZ_NO_AFFINITY'] = '1'
    os.environ['WEIZZ_I_DONT_CARE_ABOUT_MISSING_CRASHES'] = '1'
    os.environ['WEIZZ_CTX_SENSITIVE'] = '1'
    os.environ['WEIZZ_SKIP_CRASHES'] = '1'
    os.environ['WEIZZ_SHUFFLE_QUEUE'] = '1'

    # Weizz needs at least one non-empty seed to start.
    utils.create_seed_file_for_empty_corpus(input_corpus)

    command = [
        './weizz',
        '-d',  # No deterministic mutation.
        '-w',  # Enable smart mode, high-order mutate tagged inputs.
        '-h',  # Stacking mode, alternate smart and AFL mutations.
        '-Q',  # Qemu mode.
        '-L',  # Size bounds to disable getdeps for a testcase.
        '8k',  # Size bounds set to 8kb.
        '-m',  # No memory limits
        'none',
        '-i',
        input_corpus,
        '-o',
        output_corpus,
        '-t',
        '1000+',  # Use same default 1 sec timeout, but add '+' to skip hangs.
    ]
    dictionary_path = utils.get_dictionary_path(target_binary)
    if dictionary_path:
        command.extend(['-x', dictionary_path])
    command.extend(['--', target_binary])

    os.system('ulimit -s 16384')

    print('[weizz] Running command: ' + ' '.join(command))
    subprocess.check_call(command)
