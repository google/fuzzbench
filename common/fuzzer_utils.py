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
"""Fuzzer helpers."""

import importlib
import os
import re
from typing import Optional

from common import logs
from common import utils

DEFAULT_FUZZ_TARGET_NAME = 'fuzz-target'
FUZZ_TARGET_SEARCH_STRING = b'LLVMFuzzerTestOneInput'
VALID_FUZZER_REGEX = re.compile(r'^[A-Za-z0-9_]+$')
FUZZERS_DIR = os.path.join(utils.ROOT_DIR, 'fuzzers')


class FuzzerDirectory:
    """Class representing a fuzzer directory in fuzzers/."""

    def __init__(self, name):
        # TOOD(metzman): Use this class to represent fuzzers in general.
        # For example, replace the dict format we use for variants with this.
        self.name = name

    @property
    def directory(self):
        """Returns the path to the directory in fuzzers/."""
        return os.path.join(FUZZERS_DIR, self.name)

    @property
    def fuzzer_py(self):
        """Returns the path to the fuzzer.py file in fuzzer directory."""
        return os.path.join(self.directory, 'fuzzer.py')

    @property
    def runner_dockerfile(self):
        """Returns the path to the runner.Dockerfile file in fuzzer
        directory."""
        return os.path.join(self.directory, 'runner.Dockerfile')

    @property
    def builder_dockerfile(self):
        """Returns the path to the builder.Dockerfile file in fuzzer
        directory."""
        return os.path.join(self.directory, 'builder.Dockerfile')

    @property
    def variants_yaml(self):
        """Returns the path to the variants.yaml file in fuzzer directory."""
        return os.path.join(self.directory, 'variants.yaml')

    @property
    def dockerfiles(self):
        """Returns a list of paths to the runner and builder dockerfiles in the
        fuzzer directory."""
        return [self.runner_dockerfile, self.builder_dockerfile]


def get_fuzz_target_binary(search_directory: str,
                           fuzz_target_name: str) -> Optional[str]:
    """Return target binary path."""
    if fuzz_target_name:
        fuzz_target_binary = os.path.join(search_directory, fuzz_target_name)
        if os.path.exists(fuzz_target_binary):
            return fuzz_target_binary
        return None

    default_fuzz_target_binary = os.path.join(search_directory,
                                              DEFAULT_FUZZ_TARGET_NAME)
    if os.path.exists(default_fuzz_target_binary):
        return default_fuzz_target_binary

    for root, _, files in os.walk(search_directory):
        if root == 'uninstrumented':
            continue
        for filename in files:
            if filename.endswith('-uninstrumented'):
                # Skip uninstrumented binaries (e.g. with QSYM).
                continue

            file_path = os.path.join(root, filename)
            with open(file_path, 'rb') as file_handle:
                if FUZZ_TARGET_SEARCH_STRING in file_handle.read():
                    return file_path

    return None


def validate(fuzzer):
    """Return True if |fuzzer| is a valid fuzzbench fuzzer."""
    # Although importing probably allows a subset of what the regex allows, use
    # the regex anyway to be safe. The regex is enforcing that the fuzzer is a
    # valid path for GCS or a linux system.
    if VALID_FUZZER_REGEX.match(fuzzer) is None:
        logs.error('%s does not conform to %s pattern.', fuzzer,
                   VALID_FUZZER_REGEX.pattern)
        return False

    # Try importing the fuzzer module.
    module_name = 'fuzzers.{}.fuzzer'.format(fuzzer)
    try:
        importlib.import_module(module_name)
        return True
    except Exception as error:  # pylint: disable=broad-except
        logs.error('Encountered "%s" while trying to import %s.', error,
                   module_name)
        return False


def get_fuzzer_from_config(fuzzer_config: dict) -> str:
    """Returns the fuzzer of |fuzzer_config| for a non-variant fuzzer or returns
    the name for a fuzzer variant."""
    return fuzzer_config.get('name', fuzzer_config['fuzzer'])


def get_fuzzer_names():
    """Returns a list of names of all fuzzers."""
    return [get_fuzzer_from_config(config) for config in get_fuzzer_configs()]


def get_fuzzer_configs(fuzzers=None):
    """Returns the list of all fuzzer and variant configurations."""
    # Import it here to avoid yaml dependency in runner.
    # pylint: disable=import-outside-toplevel
    from common import yaml_utils

    fuzzers_dir = os.path.join(utils.ROOT_DIR, 'fuzzers')
    fuzzer_configs = []
    names = set()
    for fuzzer in os.listdir(fuzzers_dir):
        if not os.path.isfile(os.path.join(fuzzers_dir, fuzzer, 'fuzzer.py')):
            continue
        if fuzzer == 'coverage':
            continue

        if not fuzzers or fuzzer in fuzzers:
            # Auto-generate the default configuration for each underlying
            # fuzzer.
            fuzzer_configs.append({'fuzzer': fuzzer})

        variant_config_path = os.path.join(fuzzers_dir, fuzzer, 'variants.yaml')
        if not os.path.isfile(variant_config_path):
            continue

        variant_config = yaml_utils.read(variant_config_path)
        assert 'variants' in variant_config, (
            'Missing "variants" section of {}'.format(variant_config_path))
        for variant in variant_config['variants']:
            if not fuzzers or variant['name'] in fuzzers:
                assert 'name' in variant, (
                    'Missing name attribute for fuzzer variant in {}'.format(
                        variant_config_path))
                variant['fuzzer'] = fuzzer
                fuzzer_configs.append(variant)

            name = variant['name'] if 'name' in variant else variant['fuzzer']
            assert name not in names, (
                'Multiple fuzzers/variants have the same name: ' + name)
            names.add(name)

    return fuzzer_configs
