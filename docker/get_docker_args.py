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
"""Helper script to get docker arguments for local building."""

import os
import sys
import yaml

FUZZERS_DIR = os.path.join(os.path.dirname(__file__), os.path.pardir, 'fuzzers')


def print_build_arguments(variants, variant_name):
    """Print the build arguments for the variant named |variant_name|."""
    for variant in variants:
        if variant['name'] != variant_name:
            continue
        if 'build_arguments' in variant:
            print(' '.join(variant['build_arguments']))
        return


def main(argv):
    """Script main function."""
    if 'VARIANT_NAME' not in os.environ:
        return

    variants_path = os.path.join(FUZZERS_DIR, argv[1], 'variants.yaml')
    if not os.path.exists(variants_path):
        return

    with open(variants_path) as file_handle:
        config = yaml.load(file_handle, yaml.SafeLoader)
        assert 'variants' in config
        print_build_arguments(config['variants'], os.environ['VARIANT_NAME'])


if __name__ == '__main__':
    main(sys.argv)
