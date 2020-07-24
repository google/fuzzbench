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
"""Tests for benchmark_config.py"""
import os

from common import conftest
from common import benchmark_config
from common import utils

# pylint: disable=invalid-name,unused-argument

# TODO(metzman): Figure out how to mock lru_cache here.


def test_get_config_file():
    """Test that we can get the config file of a benchmark."""
    assert benchmark_config.get_config_file(
        conftest.OSS_FUZZ_BENCHMARK_NAME) == os.path.join(
            utils.ROOT_DIR, 'benchmarks', conftest.OSS_FUZZ_BENCHMARK_NAME,
            'benchmark.yaml')


def test_get_config(oss_fuzz_benchmark):
    """Test that we can get the configuration of a benchmark."""
    assert benchmark_config.get_config(conftest.OSS_FUZZ_BENCHMARK_NAME) == (
        conftest.OSS_FUZZ_BENCHMARK_CONFIG)
