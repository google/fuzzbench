# Copyright 2024 Google LLC
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
"""Tests for utils.py"""

from common import utils


def test_get_retry_delay():
    """"Tests if get delay is working as expected"""
    delay = 3
    backoff = 2

    first_try = 1
    first_try_delay = utils.get_retry_delay(first_try, delay, backoff)
    # Backoff should have no effect on first try
    assert first_try_delay == delay

    second_try = 2
    second_try_delay = utils.get_retry_delay(second_try, delay, backoff)
    assert second_try_delay == delay * backoff
