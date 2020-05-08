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

from common import fuzzer_utils
from common import utils
from src_analysis import change_utils


def test_get_changed_fuzzers_for_ci():
    """Tests that get_changed_fuzzers_for_ci returns all fuzzers when a file
    that affects all fuzzer build was changed."""
    changed_fuzzers = change_utils.get_changed_fuzzers_for_ci(
        [os.path.join(utils.ROOT_DIR, 'docker', 'build.mk')])
    assert changed_fuzzers == fuzzer_utils.get_fuzzer_names()
