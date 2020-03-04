# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions andsss
# limitations under the License.
"""Tests for generate_report.py"""
import pandas as pd

from experiment import generate_report

def test_transform_for_progress_report_fuzzer_label():
    """Tests that transform_for_progress_report includes the
    experiment name in the fuzzer name"""
    input_df = pd.DataFrame({'experiment': ['experiment-a', 'experiment-b'],
                  'fuzzer': ['fuzzer-1', 'fuzzer-2']})
    transformed_df = generate_report.transform_for_progress_report(input_df)

    expected_fuzzers_df = pd.DataFrame({
                   'fuzzer':
                   ['fuzzer-1-experiment-a', 'fuzzer-2-experiment-b']})

    assert (transformed_df['fuzzer'] == expected_fuzzers_df['fuzzer']).all()
