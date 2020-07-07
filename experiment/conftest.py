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
"""A pytest conftest.py file that defines fixtures."""
import os

import pytest
import yaml


@pytest.fixture
def experiment_config():
    """Fixture that returns the loaded yaml configuration
    test_data/experiment-config.yaml."""
    config_filepath = os.path.join(os.path.dirname(__file__), 'test_data',
                                   'experiment-config.yaml')

    with open(config_filepath) as file_handle:
        return yaml.load(file_handle, yaml.SafeLoader)


@pytest.fixture
def local_experiment_config():
    """Fixture that returns the loaded yaml configuration
    test_data/local_experiment-config.yaml."""
    config_filepath = os.path.join(os.path.dirname(__file__), 'test_data',
                                   'local-experiment-config.yaml')

    with open(config_filepath) as file_handle:
        return yaml.load(file_handle, yaml.SafeLoader)
