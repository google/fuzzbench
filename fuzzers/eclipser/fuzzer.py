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
"""Integration code for Eclipser fuzzer."""

import os
import subprocess
import time
from multiprocessing import Process

from fuzzers import utils


def build():
    """Build fuzzer."""
    # QEMU does not work with sanitizers, so skip -fsanitize=. See
    # https://github.com/SoftSec-KAIST/Eclipser/issues/5
    utils.set_no_sanitizer_compilation_flags()
    cflags = [
        '-O2',
        '-fno-omit-frame-pointer',
    ]
    utils.append_flags('CFLAGS', cflags)
    utils.append_flags('CXXFLAGS', cflags)

    os.environ['CC'] = 'clang'
    os.environ['CXX'] = 'clang++'
    os.environ['FUZZER_LIB'] = '/libStandaloneFuzzTarget.a'

    utils.build_benchmark()


def fuzz(input_corpus, output_corpus, target_binary):
    """Run fuzzer."""
    # Create an encoded temp corpus directory.
    encoded_temp_corpus = os.path.join(os.path.dirname(input_corpus),
                                       'temp-corpus')
    if not os.path.exists(encoded_temp_corpus):
        os.mkdir(encoded_temp_corpus)

    print('[run_fuzzer] Running target with Eclipser')
    command = [
        'dotnet',
        '/Eclipser/build/Eclipser.dll',
        'fuzz',
        '-p',
        target_binary,
        '-t',
        '1048576',  # FIXME: Find the max value allowed here.
        '-o',
        encoded_temp_corpus,
        '--src',
        'file',
        '--initarg',
        'foo',  # Specifies how command line argument is passed, just a file.
        '-f',
        'foo',
        '--maxfilelen',
        # Default is too low (8 bytes), match experiment config at:
        # https://github.com/SoftSec-KAIST/Eclipser-Artifact/blob/6aadf02eeadb0416bd4c5edeafc8627bc24ebc82/docker-scripts/experiment-scripts/package-exp/run_eclipser.sh#L25
        '1048576',
        # Default is low (0.5 sec), recommended to use higher:
        # https://github.com/google/fuzzbench/issues/70#issuecomment-596060572
        '--exectimeout',
        '2000',
    ]
    if os.listdir(input_corpus):  # Important, otherwise Eclipser crashes.
        command += ['-i', input_corpus]
    subprocess.Popen(command)

    process = Process(target=copy_corpus_directory,
                      args=(
                          encoded_temp_corpus,
                          output_corpus,
                      ))
    process.start()


def copy_corpus_directory(encoded_temp_corpus, output_corpus):
    """Copies corpus periodically from encoded corpus directory into output
  directory."""
    while True:
        # Wait for initial fuzzer initialization, and after every copy.
        time.sleep(120)

        subprocess.call([
            'dotnet',
            '/Eclipser/build/Eclipser.dll',
            'decode',
            '-i',
            os.path.join(encoded_temp_corpus, 'testcase'),
            '-o',
            output_corpus,
        ])
