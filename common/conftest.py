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
"""A pytest conftest.py file that defines fixtures"""
import os
import yaml

import pytest

from common import utils

# pylint: disable=invalid-name

OSS_FUZZ_BENCHMARK_CONFIG = {
    'fuzz_target':
        'my_fuzzer',
    'project':
        'oss-fuzz-project',
    'oss_fuzz_builder_hash':
        '9dcbb741050312af58acb50e3a590aa446b1e57bb35125507bd5c637c07a1aea',  # pylint: disable=line-too-long
}

OSS_FUZZ_BENCHMARK_NAME = 'oss-fuzz-benchmark'


@pytest.fixture
def oss_fuzz_benchmark(fs):
    """Fixutre that makes an OSS-Fuzz benchmark with OSS_FUZZ_BENCHMARK_CONFIG
    as its config."""
    benchmark_config_contents = yaml.dump(OSS_FUZZ_BENCHMARK_CONFIG)
    benchmark_config_file = os.path.join(utils.ROOT_DIR, 'benchmarks',
                                         OSS_FUZZ_BENCHMARK_NAME,
                                         'benchmark.yaml')
    fs.create_file(benchmark_config_file, contents=benchmark_config_contents)
    return OSS_FUZZ_BENCHMARK_NAME
