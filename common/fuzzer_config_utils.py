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
"""Configuration helper functions."""

from common import experiment_path as exp_path
from common import yaml_utils


def get_dir():
    """Return config directory."""
    return exp_path.path('config')


def get_fuzzer_configs_dir():
    """Return fuzzer configs directory."""
    return exp_path.path('config', 'fuzzer-configs')


def get_fuzzer_name(fuzzer_config_filename: str) -> str:
    """Get the fuzzer specified in fuzzer_config_filename"""
    fuzzer_config = yaml_utils.read(get_fuzzer_configs_dir() /
                                    fuzzer_config_filename)

    # Multiple configurations of the same fuzzer are differentiated by their
    # assigned display names, but we default to the in the simple case.
    if 'name' in fuzzer_config:
        return fuzzer_config['name']
    return fuzzer_config['fuzzer']
