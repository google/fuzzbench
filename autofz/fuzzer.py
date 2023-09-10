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
"""Integration code for Honggfuzz fuzzer."""

import os
import shutil
import subprocess

from fuzzers import utils


def build():
    """Build benchmark."""
    os.environ['CC'] = 'clang'
    os.environ['CXX'] = 'clang++'

    utils.build_benchmark()

    shutil.copy('.', os.environ['OUT'])


def fuzz(input_corpus, output_corpus, target_binary):
    """Run fuzzer."""
    print('[fuzz] Running target with ')
    command = [
        'autofz',
        '-f',
        'all',
        '-t',
        target_binary,
        '-i',
        input_corpus,
        '-o',
        output_corpus,
    ]
    
    subprocess.check_call(command)

