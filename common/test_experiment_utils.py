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
"""Tests for experiment_utils.py."""

from common import experiment_utils


def test_get_dispatcher_instance_name():
    """Tests that get_dispatcher_instance_name returns the expected result."""
    assert experiment_utils.get_dispatcher_instance_name(
        'experiment-a') == 'd-experiment-a'


def test_get_trial_instance_name():
    """Tests that get_trial_instance_name returns the expected result."""
    assert experiment_utils.get_trial_instance_name('experiment-a',
                                                    9) == 'r-experiment-a-9'


def test_get_corpus_archive_name():
    """Tests that get_corpus_archive_name returns the expected result."""
    assert (experiment_utils.get_corpus_archive_name(9) ==
            'corpus-archive-0009.tar.gz')
