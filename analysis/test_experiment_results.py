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
"""Tests for experiment_results.py"""
from unittest import mock

from analysis import experiment_results
from analysis import test_data_utils


@mock.patch('common.benchmark_config.get_config', return_value={})
def test_linkify_fuzzer_names_in_ranking(_):
    """Tests turning fuzzer names into links."""
    experiment_df = test_data_utils.create_experiment_data()
    results = experiment_results.ExperimentResults(experiment_df,
                                                   coverage_dict=None,
                                                   output_directory=None,
                                                   plotter=None)
    ranking = results.rank_by_median_and_average_rank

    ranking = results.linkify_names(ranking)

    assert ranking.index[0] == (
        '<a href="https://github.com/google/fuzzbench/blob/'
        'master/fuzzers/afl">afl</a>')
