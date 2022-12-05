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
"""Integration code for centipede fuzzer."""

import os
import yaml

from fuzzers.centipede import fuzzer


def build():
    """Build benchmark."""
    fuzzer.build()


def fuzz(input_corpus, output_corpus, target_binary):
    """Run fuzzer. Wrapper that uses the defaults when calling run_fuzzer."""
    with open('/focus_map.yaml', 'r', encoding='utf-8') as focus_file:
        focus_map = yaml.safe_load(focus_file)
    benchmark = os.getenv('BENCHMARK', None)
    if benchmark not in focus_map:
        return
    focus_list = focus_map[benchmark]
    focus_filter = ','.join(focus_list)
    fuzzer.run_fuzzer(input_corpus,
                      output_corpus,
                      target_binary,
                      extra_flags=[f'--function_filter={focus_filter}'])
