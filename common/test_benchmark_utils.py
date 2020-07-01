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


@pytest.mark.parametrize('benchmark,expected_result',
                         [(conftest.OSS_FUZZ_BENCHMARK_NAME, True),
                          (OTHER_BENCHMARK, False)])
def test_is_oss_fuzz(benchmark, expected_result, oss_fuzz_benchmark):
    """Test that we can distinguish OSS-Fuzz benchmarks from non-OSS-Fuzz
    benchmarks."""
    assert benchmark_utils.is_oss_fuzz(benchmark) == expected_result


def test_get_project_oss_fuzz_benchmark(oss_fuzz_benchmark):
    """Test that we can get the project of an OSS-Fuzz benchmark."""
    assert benchmark_utils.get_project(
        oss_fuzz_benchmark) == conftest.OSS_FUZZ_BENCHMARK_CONFIG['project']


def test_get_project_non_oss_fuzz_benchmark():
    """Test that we can't get the project of a non-OSS-Fuzz benchmark."""
    with pytest.raises(ValueError):
        benchmark_utils.get_project(OTHER_BENCHMARK)


@pytest.mark.parametrize('benchmark,expected_fuzz_target',
                         [(conftest.OSS_FUZZ_BENCHMARK_NAME,
                           conftest.OSS_FUZZ_BENCHMARK_CONFIG['fuzz_target']),
                          (OTHER_BENCHMARK, 'fuzz-target')])
def test_get_fuzz_target(benchmark, expected_fuzz_target, oss_fuzz_benchmark):
    """Test that we can get the docker name of a benchmark."""
    assert benchmark_utils.get_fuzz_target(benchmark) == expected_fuzz_target


@pytest.mark.parametrize(
    'benchmark,expected_url',
    [(conftest.OSS_FUZZ_BENCHMARK_NAME,
      'gcr.io/fuzzbench/runners/fuzzer/oss-fuzz-benchmark'),
     (OTHER_BENCHMARK, 'gcr.io/fuzzbench/runners/fuzzer/benchmark')])
def test_get_runner_image_url(benchmark, expected_url, oss_fuzz_benchmark):
    """Test that we can get the runner image url of a benchmark."""
    assert benchmark_utils.get_runner_image_url(benchmark, 'fuzzer',
                                                DOCKER_REGISTRY) == expected_url


def test_get_builder_hash_oss_fuzz_benchmark(oss_fuzz_benchmark):
    """Test that we can get the oss_fuzz_builder_hash of an OSS-Fuzz
    benchmark."""
    assert benchmark_utils.get_oss_fuzz_builder_hash(
        oss_fuzz_benchmark
    ) == conftest.OSS_FUZZ_BENCHMARK_CONFIG['oss_fuzz_builder_hash']


def test_get_builder_hash_non_oss_fuzz_benchmark():
    """Test that we can't get the oss_fuzz_builder_hash of a non-OSS-Fuzz
    benchmark."""
    with pytest.raises(ValueError):
        benchmark_utils.get_oss_fuzz_builder_hash(OTHER_BENCHMARK)
