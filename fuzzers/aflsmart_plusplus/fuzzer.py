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
"""Integration code for AFLSmart++ fuzzer."""

import os
import shutil
import glob

from fuzzers.afl import fuzzer as afl_fuzzer


def build():
    """Build benchmark."""
    afl_fuzzer.build()

    # Copy Peach binaries to OUT
    shutil.copytree('/afl/peach-3.0.202-source/output/linux_x86_64_debug/bin',
                    os.environ['OUT'] + '/peach-3.0.202')

    # Copy supported input models
    for file in glob.glob('/afl/input_models/*.xml'):
        print(file)
        shutil.copy(file, os.environ['OUT'])


def fuzz(input_corpus, output_corpus, target_binary):
    """Run afl-fuzz on target."""
    afl_fuzzer.prepare_fuzz_environment(input_corpus)
    os.environ['PATH'] += os.pathsep + '/out/peach-3.0.202/'

    input_model = 'all_composite.xml'

    additional_flags = [
        # Enable stacked mutations
        '-h',
        # Enable structure-aware fuzzing
        '-w',
        'peach',
        # Select input model
        '-g',
        input_model,
        # Choose FAVOR chunk type selection algo
        '-s',
        '2',
        # Reduce the chance of doing "destructive" mutations
        '-D',
        '50',
    ]

    afl_fuzzer.run_afl_fuzz(input_corpus, output_corpus, target_binary,
                            additional_flags)
