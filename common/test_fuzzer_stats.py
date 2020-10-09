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
"""Tests for fuzzer_stats.py."""
import pytest

from common import fuzzer_stats


def test_validate_valid_fuzzer_stats():
    """Tests that validate_fuzzer_stats doesn't throw an exception for a valid
    stats string."""
    fuzzer_stats.validate_fuzzer_stats('{"execs_per_sec": 20.2}')


def test_validate_nondict_fuzzer_stats():
    """Tests that validate_fuzzer_stats throws an exception when given a json
    string not containing an object (dict)."""
    with pytest.raises(ValueError, match='20.2 is not a dict.'):
        fuzzer_stats.validate_fuzzer_stats('20.2')


def test_validate_invalid_key_fuzzer_stats():
    """Tests that validate_fuzzer_stats throws an exception when given a json
    string with an invalid key."""
    with pytest.raises(ValueError,
                       match='Key fake_key is not a valid stat key.'):
        fuzzer_stats.validate_fuzzer_stats('{"fake_key": 20.2}')


def test_validate_wrong_type_fuzzer_stats():
    """Tests that validate_fuzzer_stats throws an exception when given a json
    string with a value with an incorrect type."""
    match = ('Key "execs_per_sec" has value "20.2" which is type: '
             '"<class \'str\'>". Expected type: "<class \'float\'>".')
    with pytest.raises(ValueError, match=match):
        fuzzer_stats.validate_fuzzer_stats('{"execs_per_sec": "20.2"}')
