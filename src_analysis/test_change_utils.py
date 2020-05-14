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
"""Tests for change_utils.py."""
import os
from unittest import mock

import pytest

from common import fuzzer_utils
from common import utils
from database import models
from database import utils as db_utils
from src_analysis import change_utils
from src_analysis import diff_utils

# pylint: disable=invalid-name,unused-argument,redefined-outer-name

AFL_FUZZER_PY = os.path.abspath('fuzzers/afl/fuzzer.py')


def test_get_changed_fuzzers_for_ci():
    """Tests that get_changed_fuzzers_for_ci returns all fuzzers when a file
    that affects all fuzzer build was changed."""
    changed_fuzzers = change_utils.get_changed_fuzzers_for_ci(
        [os.path.join(utils.ROOT_DIR, 'docker', 'build.mk')])
    assert changed_fuzzers == fuzzer_utils.get_fuzzer_names()


@pytest.fixture
def db_experiment(db):
    """Fixture that creates a database populated the databse with an
    experiment."""
    experiment = models.Experiment()
    experiment.name = 'experiment'
    experiment.git_hash = 'hash'
    db_utils.add_all([experiment])


@mock.patch('src_analysis.diff_utils.get_changed_files',
            return_value=[AFL_FUZZER_PY])
def test_get_changed_fuzzers_since_last_experiment_afl(_, db_experiment):
    """Tests that get_changed_fuzzers_since_last_experiment returns the correct
    result when a fuzzer has changed."""
    changed_fuzzers = change_utils.get_changed_fuzzers_since_last_experiment()
    assert 'afl' in changed_fuzzers
    assert 'fairfuzz' in changed_fuzzers


@mock.patch('src_analysis.diff_utils.get_changed_files', return_value=[])
def test_get_changed_fuzzers_since_last_experiment_no_changes(_, db_experiment):
    """Tests that get_changed_fuzzers_since_last_experiment returns the
    correct result when no fuzzer has changed."""
    assert not change_utils.get_changed_fuzzers_since_last_experiment()


@mock.patch('src_analysis.diff_utils.get_changed_files', return_value=[])
def test_get_changed_fuzzers_since_last_experiment_non_master_experiment(
        mocked_get_changed_files, db_experiment):
    """Tests that get_changed_fuzzers_since_last_experiment returns the
    correct result when the first experiment's git hash is not in master"""
    # Set up a newer, out-of-tree experiment.
    out_of_tree_experiment = models.Experiment()
    out_of_tree_experiment.name = 'experiment2'
    out_of_tree_experiment.git_hash = 'hash2'
    db_utils.add_all([out_of_tree_experiment])

    def get_changed_files(commit_hash):
        if commit_hash == 'hash2':
            raise diff_utils.DiffError(commit_hash)
        return AFL_FUZZER_PY

    mocked_get_changed_files.side_effect = get_changed_files

    assert not change_utils.get_changed_fuzzers_since_last_experiment()
