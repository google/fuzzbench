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
"""Tests for coverage_utils.py"""
import os

from experiment.measurer import coverage_utils

TEST_DATA_PATH = os.path.join(os.path.dirname(__file__), 'test_data')


def get_test_data_path(*subpaths):
    """Returns the path of |subpaths| relative to TEST_DATA_PATH."""
    return os.path.join(TEST_DATA_PATH, *subpaths)


def test_extract_covered_branches_from_summary_json(fs):
    """Tests that extract_covered_branches_from_summary_json returns the covered
    branches from summary json file."""
    summary_json_file = get_test_data_path('cov_summary.json')
    fs.add_real_file(summary_json_file, read_only=False)
    covered_branches = coverage_utils. \
    extract_covered_branches_from_summary_json(
        summary_json_file)
    assert len(covered_branches) == 9
