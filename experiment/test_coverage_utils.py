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
import unittest
import os
import sys
from pyfakefs.fake_filesystem_unittest import TestCase

file_dir = os.path.dirname('coverage_utils.py')
sys.path.append(file_dir)

from experiment import coverage_utils

TEST_DATA_PATH = os.path.join(os.path.dirname(__file__), 'test_data')


def get_test_data_path(*subpaths):
    """Returns the path of |subpaths| relative to TEST_DATA_PATH."""
    return os.path.join(TEST_DATA_PATH, *subpaths)


def test_extract_covered_regions_from_summary_json(fs):
    """Tests that extract_covered_regions_from_summary_json returns the covered
    regions from summary json file."""
    code_regions = []
    summary_json_file = get_test_data_path('cov_summary.json')
    fs.add_real_file(summary_json_file, read_only=False)
    for region in coverage_utils.extract_covered_regions_from_summary_json(
            summary_json_file, 2):
        code_regions.append(region)
    print(code_regions)

    # TODO Instead of re-implementing the same method to construct the
    # covered_regions.json file, please test the implementation to construct
    # the covered_regions.json. Specifically, you could just test whether
    # it produces the following output or structure:
    
    #{"Coverage_Data": [
    #  {"region_arr": [7, 12, 12, 2, 0, 0, 0], "covered_trial_nums_hits": [[2, 1]], "uncovered_trial_nums": [], "num_unq_trial_covering": 1}, 
    #  {"region_arr": [11, 3, 12, 2, 0, 0, 0], "covered_trial_nums_hits": [], "uncovered_trial_nums": [2], "num_unq_trial_covering": 0}, 
    #  {"region_arr": [2, 37, 6, 2, 0, 0, 0], "covered_trial_nums_hits": [[2, 1]], "uncovered_trial_nums": [], "num_unq_trial_covering": 1}, 
    #  {"region_arr": [3, 24, 3, 30, 0, 0, 0], "covered_trial_nums_hits": [[2, 11]], "uncovered_trial_nums": [], "num_unq_trial_covering": 1}, 
    #  {"region_arr": [3, 32, 3, 35, 0, 0, 0], "covered_trial_nums_hits": [[2, 10]], "uncovered_trial_nums": [], "num_unq_trial_covering": 1}, 
    #  {"region_arr": [3, 37, 3, 48, 0, 0, 0], "covered_trial_nums_hits": [[2, 10]], "uncovered_trial_nums": [], "num_unq_trial_covering": 1}, 
    #  {"region_arr": [5, 3, 6, 2, 0, 0, 0], "covered_trial_nums_hits": [], "uncovered_trial_nums": [2], "num_unq_trial_covering": 0}, 
    #  {"region_arr": [1, 16, 1, 28, 1, 0, 0], "covered_trial_nums_hits": [[2, 10]], "uncovered_trial_nums": [], "num_unq_trial_covering": 1}, 
    #  {"region_arr": [1, 17, 1, 20, 1, 0, 0], "covered_trial_nums_hits": [[2, 10]], "uncovered_trial_nums": [], "num_unq_trial_covering": 1}, 
    #  {"region_arr": [1, 24, 1, 27, 1, 0, 0], "covered_trial_nums_hits": [[2, 1]], "uncovered_trial_nums": [], "num_unq_trial_covering": 1}]}

    # assertNotEqual(len(code_regions), 15, msg='did not pass assertion 1')


def check_if_duplicates(list_of_elems):
    """ Check if given list contains any duplicates """
    for elem in list_of_elems:
        if list_of_elems.count(elem) > 1:
            return True
    return False
