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
"""Yaml helpers."""
import yaml


def read(yaml_filename):
    """Reads and loads yaml file specified by |yaml_filename|."""
    with open(yaml_filename) as file_handle:
        return yaml.load(file_handle, yaml.SafeLoader)


def write(yaml_filename, data):
    """Writes |data| to a new yaml file at |yaml_filename|."""
    with open(yaml_filename, 'w') as file_handle:
        return yaml.dump(data, file_handle)
