# Copyright 2022 Google LLC
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
"""Tools for using oss-fuzz."""
import functools
import os

from common import utils
from common import yaml_utils

FUZZERS_DIR = os.path.join(utils.ROOT_DIR, 'fuzzers')


def get_config_file(fuzzer):
    """Returns the path to the config for a fuzzer."""
    return os.path.join(FUZZERS_DIR, fuzzer, 'fuzzer.yaml')


@functools.lru_cache(maxsize=None)
def get_config(fuzzer):
    """Returns a dictionary containing the config for a fuzzer."""
    config_file = get_config_file(fuzzer)
    if os.path.exists(config_file):
        return yaml_utils.read(config_file)
    return {}
