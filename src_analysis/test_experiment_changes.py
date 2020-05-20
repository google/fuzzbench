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
# See the License for the specific language governing permissions and
# limitations under the License.
"""Tests for experiment_changes.py."""
import datetime
import os
from unittest import mock

import pytest

from database import models
from database import utils as db_utils
from src_analysis import experiment_changes
from src_analysis import diff_utils

# pylint: disable=invalid-name,unused-argument,redefined-outer-name

AFL_FUZZER_PY = os.path.abspath('fuzzers/afl/fuzzer.py')


@pytest.fixture
def db_experiment(db):
    """Fixture that creates a database populated the databse with an
    experiment."""
    experiment = models.Experiment()
    experiment.name = 'experiment'
    experiment.git_hash = 'hash'
    db_utils.add_all([experiment])
    return experiment


@mock.patch('src_analysis.diff_utils.get_changed_files',
            return_value=[AFL_FUZZER_PY])
def test_get_fuzzers_changed_since_last_afl(_, db_experiment):
    """Tests that get_fuzzers_changed_since_last returns the correct
    result when a fuzzer has changed."""
    changed_fuzzers = (experiment_changes.get_fuzzers_changed_since_last())
    assert 'afl' in changed_fuzzers
    assert 'fairfuzz' in changed_fuzzers


@mock.patch('src_analysis.diff_utils.get_changed_files', return_value=[])
def test_get_fuzzers_changed_since_last_no_changes(_, db_experiment):
    """Tests that get_fuzzers_changed_since_last returns the
    correct result when no fuzzer has changed."""
    assert not experiment_changes.get_fuzzers_changed_since_last()


@mock.patch('src_analysis.diff_utils.get_changed_files', return_value=[])
@mock.patch('common.logs.warning')
def test_get_fuzzers_changed_since_last_non_master_experiment(
        mocked_info, mocked_get_changed_files, db_experiment):
    """Tests that get_fuzzers_changed_since_last returns the
    correct result when the first experiment's git hash is not in branch"""
    # Set up a newer, out-of-branch experiment.
    out_of_branch_experiment = models.Experiment()
    out_of_branch_experiment.name = 'out-of-branch-experiment'
    out_of_branch_hash = 'out-of-branch-experiment-hash'
    out_of_branch_experiment.git_hash = out_of_branch_hash
    db_utils.add_all([out_of_branch_experiment])

    # Update the time of out_of_branch_experiment to come after db_experiment.
    out_of_branch_experiment.time_created = (db_experiment.time_created +
                                             datetime.timedelta(days=1))

    db_utils.add_all([out_of_branch_experiment])

    def get_changed_files(commit_hash):
        if commit_hash == 'out-of-branch-experiment-hash':
            raise diff_utils.DiffError(commit_hash)
        return AFL_FUZZER_PY

    mocked_get_changed_files.side_effect = get_changed_files

    assert not experiment_changes.get_fuzzers_changed_since_last()
    mocked_info.assert_called_with('Skipping %s. Commit is not in branch.',
                                   out_of_branch_hash)
    mocked_get_changed_files.assert_has_calls(
        [mock.call(out_of_branch_hash),
         mock.call('hash')])
