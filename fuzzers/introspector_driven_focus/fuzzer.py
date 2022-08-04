# Copyright 2022 Google LLC
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
"""Integration code for libFuzzer fuzzer."""

import yaml

from fuzzers.libfuzzer import fuzzer

def build():
    """Build benchmark."""
    fuzzer.build()


def fuzz(input_corpus, output_corpus, target_binary):
    """Run fuzzer. Wrapper that uses the defaults when calling
    run_fuzzer."""

    with open("focus_list.yaml", 'r') as focus_file:
        focus_functions = yaml.load(focus_file)
    # For now just use the first function, later will for multiple functions
    focus_func = focus_functions['functions'][0]
    fuzzer.run_fuzzer(input_corpus,
               output_corpus,
               target_binary,
               extra_flags=['-keep_seed=1', '-cross_over_uniform_dist=1',
                            f'-focus_function={focus_func}'])
