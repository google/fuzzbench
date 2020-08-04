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

SCHEMA = {
    'avg_execs': float
}

def validate_fuzzer_stats(stats_json_str):
    stats = json.loads(stats_json_str)
    for key, value in stats:
        if key not in SCHEMA:
            raise ValueError(
                'Key {key} is not a valid stat key.'.format(key=key))
        expected_type = SCHMEA[key]
        if isinstance(value, expected_type):
            continue

        raise ValueError(
            ('Key {key} has value {value} which is type {type}.'
             'Expecting {expected_type}.').format(
                 key=key, value=value, type=type(value),
                 expected_type=expected_type))
