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
from unittest import mock

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


@pytest.mark.parametrize(('benchmark_name',), [
    ('libPNG',),
    ('libpng!',),
])
def test_validate_name_invalid(benchmark_name):
    """Tests that validate_name returns False for am invalid benchmark name."""
    assert not benchmark_utils.validate_name(benchmark_name)


@pytest.mark.parametrize(('benchmark_name',), [('libpng',), ('libpng_1',),
                                               ('libpng-1',), ('libpng.1',)])
def test_validate_name_valid(benchmark_name):
    """Tests that validate_name returns True for a valid benchmark name."""
    assert benchmark_utils.validate_name(benchmark_name)


@mock.patch('common.benchmark_utils.get_type', return_value='other-type')
def test_validate_type_invalid(_):
    """Tests that validate_type returns False for an invalid type."""
    assert not benchmark_utils.validate_type('benchmark')


@pytest.mark.parametrize(('benchmark_type',), [
    ('code',),
    ('bug',),
])
def test_validate_type_valid(benchmark_type):
    """Tests that validate_type returns True for an valid type."""
    with mock.patch('common.benchmark_utils.get_type',
                    return_value=benchmark_type):
        assert benchmark_utils.validate_type('benchmark')


@mock.patch('common.benchmark_config.get_config', return_value={})
def test_get_default_type(_):
    """Tests that get_type returns the correct default value."""
    assert benchmark_utils.get_type('benchmark') == 'code'
