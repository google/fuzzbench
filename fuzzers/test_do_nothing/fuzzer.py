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

import os
import time

from fuzzers import utils
SECONDS = 1
MINUTES = 60 * SECONDS
HOURS = 60 * MINUTES
DAYS = 24 * HOURS

def build_vanilla(build_out, src, work):
    new_env = os.environ.copy()
    new_env['OUT'] = build_out
    new_env['FUZZER_LIB'] = '/out/aflpp_driver.o'

    with utils.restore_directory(src), utils.restore_directory(work):
        utils.build_benchmark(env=new_env)

def build():
    """Build benchmark."""
    src = os.getenv('SRC')
    work = os.getenv('WORK')
    build_directory = os.getenv('OUT')

    build_vanilla(build_directory, src, work)

def fuzz(input_corpus, output_corpus, target_binary):
    while True:
        print("Fuzzing...")
        print("Sleeping...")
        time.sleep(1 * MINUTES)
