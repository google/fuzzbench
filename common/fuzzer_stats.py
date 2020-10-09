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
"""Module for dealing with self reported fuzzer stats."""

import json

SCHEMA = {'execs_per_sec': float}


def validate_fuzzer_stats(stats_json_str):
    """Validate that |stats_json_str| is a json representation of valid fuzzer
    stats. Raises an exception if it is not, otherwise returns successfully."""
    stats = json.loads(stats_json_str)

    if not isinstance(stats, dict):
        raise ValueError(f'{stats} is not a dict.')

    for key, value in stats.items():
        if key not in SCHEMA:
            raise ValueError(f'Key {key} is not a valid stat key.')
        expected_type = SCHEMA[key]
        if isinstance(value, expected_type):
            continue

        raise ValueError(
            f'Key "{key}" has value "{value}" which is type: "{type(value)}"' +
            f'. Expected type: "{expected_type}".')
