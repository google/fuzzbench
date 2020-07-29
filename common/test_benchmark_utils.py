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
"""Tests for benchmark_utils.py"""
import pytest

from common import benchmark_utils
from common import conftest

# pylint: disable=invalid-name,unused-argument

DOCKER_REGISTRY = 'gcr.io/fuzzbench'

OTHER_BENCHMARK = 'benchmark'


def test_get_fuzz_target(oss_fuzz_benchmark):
    """Test that we can get the docker name of a benchmark."""
    assert (benchmark_utils.get_fuzz_target(conftest.OSS_FUZZ_BENCHMARK_NAME) ==
            conftest.OSS_FUZZ_BENCHMARK_CONFIG['fuzz_target'])


@pytest.mark.parametrize(
    'benchmark,expected_url',
    [(conftest.OSS_FUZZ_BENCHMARK_NAME,
      'gcr.io/fuzzbench/runners/fuzzer/oss-fuzz-benchmark:experiment'),
     (OTHER_BENCHMARK, 'gcr.io/fuzzbench/runners/fuzzer/benchmark:experiment')])
def test_get_runner_image_url(benchmark, expected_url, oss_fuzz_benchmark):
    """Test that we can get the runner image url of a benchmark."""
    assert benchmark_utils.get_runner_image_url('experiment', benchmark,
                                                'fuzzer',
                                                DOCKER_REGISTRY) == expected_url
