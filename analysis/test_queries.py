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

# pylint: disable=invalid-name,unused-argument
"""Tests for queries.py"""
import datetime

from analysis import queries
from database import models
from database import utils as db_utils


def test_add_nonprivate_experiments_for_merge_with_clobber(db):
    """Tests that add_nonprivate_experiments_for_merge_with_clobber doesn't
    include private experiments and returns the expected results in the correct
    order."""
    experiment_names = ['1', '2', '3']
    arbitrary_datetime = datetime.datetime(2020, 1, 1)
    db_utils.add_all([
        models.Experiment(name=name,
                          time_created=arbitrary_datetime,
                          private=False) for name in experiment_names
    ])
    db_utils.add_all([
        models.Experiment(name='private',
                          time_created=arbitrary_datetime,
                          private=True),
        models.Experiment(name='later-nonprivate',
                          time_created=arbitrary_datetime +
                          datetime.timedelta(days=1),
                          private=False),
        models.Experiment(name='nonprivate',
                          time_created=arbitrary_datetime,
                          private=False),
    ])
    expected_results = ['nonprivate', 'later-nonprivate', '1', '2', '3']
    results = queries.add_nonprivate_experiments_for_merge_with_clobber(
        experiment_names)
    assert results == expected_results
