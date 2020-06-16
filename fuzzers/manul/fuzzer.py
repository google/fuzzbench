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
"""Manul Integration"""
import os
import subprocess
import shutil
from fuzzers import utils
from fuzzers.afl import fuzzer as afl_fuzzer


def build():
    """Build benchmark and copy fuzzer to $OUT."""
    afl_fuzzer.prepare_build_environment()
    utils.build_benchmark()
    # Move manul base to /out.
    shutil.move('/manul', os.environ['OUT'])


def fuzz(input_corpus, output_corpus, target_binary):
    """Run fuzzer.

    Arguments:
      input_corpus: Directory containing the initial seed corpus for
                    the benchmark.
      output_corpus: Output directory to place the newly generated corpus
                     from fuzzer run.
      target_binary: Absolute path to the fuzz target binary.
    """
    afl_fuzzer.prepare_fuzz_environment(input_corpus)
    # Run fuzzer on the benchmark.
    manul_directory = os.path.join(os.environ['OUT'], 'manul')
    command = ([
        'python3', 'manul.py', '-i', input_corpus, '-o', output_corpus, '-c',
        os.path.join(manul_directory, 'manul_lin.config'), target_binary + ' @@'
    ])
    subprocess.check_call(command, cwd=manul_directory)
