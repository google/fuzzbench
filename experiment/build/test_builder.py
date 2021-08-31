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
"""Tests for builder.py."""

import os
import sys
from unittest import mock

import pytest

from common import utils
from experiment.build import builder

SRC_ROOT = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir)

COVERAGE_TOOLS = {'coverage', 'coverage_source_based'}

# pylint: disable=invalid-name,unused-argument,redefined-outer-name


def get_regular_benchmarks():
    """Get all non-blocklisted, non-OSS-Fuzz benchmarks."""
    return get_benchmarks_or_fuzzers('benchmarks', 'build.sh', blocklist=set())


def get_oss_fuzz_benchmarks():
    """Get all non-blocklisted OSS-Fuzz benchmarks."""
    return get_benchmarks_or_fuzzers('benchmarks',
                                     'benchmark.yaml',
                                     blocklist=set())


def get_fuzzers():
    """Get all non-blocklisted fuzzers."""
    return get_benchmarks_or_fuzzers('fuzzers', 'fuzzer.py', COVERAGE_TOOLS)


def get_benchmarks_or_fuzzers(benchmarks_or_fuzzers_directory, filename,
                              blocklist):
    """Get all fuzzers or benchmarks from |benchmarks_or_fuzzers_directory| that
    are not in |blocklist|. Assume something is a fuzzer or benchmark if it is a
    directory and
    |benchmarks_or_fuzzers_directory|/$FUZZER_OR_BENCHMARK_NAME/|filename|
    exists."""
    parent_directory_path = os.path.join(SRC_ROOT,
                                         benchmarks_or_fuzzers_directory)
    return [
        directory for directory in os.listdir(parent_directory_path)
        if (directory not in blocklist and os.path.exists(
            os.path.join(parent_directory_path, directory, filename)))
    ]


@pytest.mark.skipif(sys.version_info.minor > 7,
                    reason='Test can stop responding on versions greater than '
                    '3.7')
@mock.patch('experiment.build.builder.build_measurer')
@mock.patch('time.sleep')
@pytest.mark.parametrize('build_measurer_return_value', [True, False])
def test_build_all_measurers(_, mocked_build_measurer,
                             build_measurer_return_value, experiment, fs):
    """Tests that build_all_measurers works as intendend when build_measurer
    calls fail."""
    fs.add_real_directory(utils.ROOT_DIR)
    mocked_build_measurer.return_value = build_measurer_return_value
    benchmarks = get_regular_benchmarks()
    result = builder.build_all_measurers(benchmarks)
    if build_measurer_return_value:
        assert result == benchmarks
    else:
        assert not result


@pytest.fixture
def builder_integration(experiment):
    """Fixture for builder.py integration tests that uses an experiment fixture
    and makes the number of build retries saner by default."""
    num_retries = int(os.getenv('TEST_NUM_BUILD_RETRIES', '1'))
    with mock.patch('experiment.build.builder.NUM_BUILD_RETRIES', num_retries):
        yield


# pylint: disable=no-self-use
@pytest.mark.skipif(
    not os.getenv('TEST_INTEGRATION_ALL'),
    reason='Tests take too long and can interfere with real '
    'experiments. Find some way of opting-in and isolating the tests.')
class TestIntegrationBuild:
    """Integration tests for building."""

    def test_integration_build_all_fuzzer_benchmarks(self, builder_integration):
        """Test that build_all_fuzzer_benchmarks can build measurers on GCB."""
        benchmarks = get_regular_benchmarks()
        fuzzers = get_fuzzers()
        _test_build_fuzzers_benchmarks(fuzzers, benchmarks)

    def test_integration_build_oss_fuzz_projects(self, builder_integration):
        """Test that build_all_measurers can build OSS-Fuzz projects on
        GCB."""
        fuzzers = get_fuzzers()
        benchmarks = get_oss_fuzz_benchmarks()
        _test_build_fuzzers_benchmarks(fuzzers, benchmarks)

    def test_integration_build_all_measurers(self, builder_integration):
        """Test that build_all_measurers can build measurers on GCB."""
        benchmarks = get_regular_benchmarks()
        _test_build_measurers_benchmarks(benchmarks)

    def test_integration_build_oss_fuzz_project_measurers(
            self, builder_integration):
        """Test that build_all_measurers can build measurers for OSS-Fuzz
        projects on GCB."""
        benchmarks = get_oss_fuzz_benchmarks()
        _test_build_measurers_benchmarks(benchmarks)


def _test_build_measurers_benchmarks(benchmarks):
    """Asserts that measurers for each benchmark in |benchmarks| can build."""
    assert benchmarks == builder.build_all_measurers(benchmarks)


def _test_build_fuzzers_benchmarks(fuzzers, benchmarks):
    """Asserts that each pair of fuzzer in |fuzzers| and benchmark in
    |benchmarks| can build."""
    all_pairs = builder.get_fuzzer_benchmark_pairs(fuzzers, benchmarks)
    assert builder.build_all_fuzzer_benchmarks(fuzzers, benchmarks) == all_pairs


def get_all_benchmarks():
    """Returns all benchmarks."""
    return get_oss_fuzz_benchmarks() + get_regular_benchmarks()


def get_specified_fuzzers():
    """Returns fuzzers as specified in the environment."""
    fuzzers = os.environ['TEST_BUILD_CHANGED_FUZZERS'].split(' ')
    return fuzzers


def get_specified_benchmarks():
    """Returns benchmarks as specified in the environment."""
    fuzzers = os.environ['TEST_BUILD_CHANGED_BENCHMARKS'].split(' ')
    return fuzzers


# TODO(metzman): Fix failures caused by copying logs to GCS.
class TestBuildChangedBenchmarksOrFuzzers:
    """Integration tests for integrations of changed fuzzers or benchmarks.
    Needs TEST_BUILD_CHANGED_BENCHMARKS or TEST_BUILD_CHANGED_FUZZERS to run."""

    @pytest.mark.skipif(not os.getenv('TEST_BUILD_CHANGED_FUZZERS'),
                        reason='''Nothing to test if no fuzzers specified.''')
    def test_build_changed_fuzzers(self, builder_integration):
        """Tests that the specified fuzzers can build with all benchmarks."""
        fuzzers = get_specified_fuzzers()
        benchmarks = get_all_benchmarks()
        _test_build_fuzzers_benchmarks(fuzzers, benchmarks)

    @pytest.mark.skipif(not os.getenv('TEST_BUILD_CHANGED_BENCHMARKS'),
                        reason='''Nothing to test if no benchmarks
                        specified.''')
    def test_build_changed_benchmarks(self, builder_integration):
        """Tests that the specified benchmarks can build with all fuzzers."""
        fuzzers = get_fuzzers()
        benchmarks = get_specified_benchmarks()
        _test_build_fuzzers_benchmarks(fuzzers, benchmarks)

    @pytest.mark.skipif(not os.getenv('TEST_BUILD_CHANGED_BENCHMARKS'),
                        reason='''Nothing to test if no benchmarks
                        specified.''')
    def test_build_measurers_benchmarks(self, builder_integration):
        """Tests that either the specified fuzzers or benchmarks can build."""
        benchmarks = get_specified_benchmarks()
        _test_build_measurers_benchmarks(benchmarks)


def mock_get_benchmark_config(benchmark):
    """Mocked version of common.benchmark_config.get_config."""
    if benchmark == 'benchmark1':
        return {
            'unsupported_fuzzers': ['fuzzer2'],
        }
    if benchmark == 'benchmark2':
        return {
            'unsupported_fuzzers': ['fuzzer2', 'fuzzer3'],
        }
    return {}


@mock.patch('common.benchmark_config.get_config', mock_get_benchmark_config)
def test_get_fuzzer_benchmark_pairs():
    """Tests builder.get_fuzzer_benchmark_pairs."""
    assert builder.get_fuzzer_benchmark_pairs(
        ['fuzzer1', 'fuzzer2', 'fuzzer3'],
        ['benchmark1', 'benchmark2', 'benchmark3']) == [
            ('fuzzer1', 'benchmark1'), ('fuzzer1', 'benchmark2'),
            ('fuzzer1', 'benchmark3'), ('fuzzer2', 'benchmark3'),
            ('fuzzer3', 'benchmark1'), ('fuzzer3', 'benchmark3')
        ]
