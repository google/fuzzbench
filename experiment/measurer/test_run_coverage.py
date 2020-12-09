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
"""Tests for run_crashes.py."""

# pylint: disable=no-self-use

import os
from unittest import mock
import glob

import pytest

from experiment.measurer import run_coverage

TEST_DATA_PATH = os.path.join(os.path.dirname(__file__), 'test_data',
                              'test_run_coverage')


def _get_test_data_dir(directory):
    """Return the path of |TEST_DATA_PATH|/|directory|."""
    return os.path.join(TEST_DATA_PATH, directory)


def _make_crashes_dir(parent_path):
    """Makes a crashes dir in |parent_path| and returns it."""
    crashes_dir = os.path.join(str(parent_path), 'crashes')
    os.mkdir(crashes_dir)
    return crashes_dir


def _make_coverage_dir(parent_path):
    """Makes a profraw dir in |parent_path| and returns it."""
    coverage_dir = os.path.join(str(parent_path), 'coverage')
    os.mkdir(coverage_dir)
    return coverage_dir


def _assert_profraw_files(coverage_dir):
    """Ensure |coverage_dir| has profraw files."""
    pattern = coverage_dir
    if not pattern.endswith('/'):
        pattern += '/'
    pattern += '*.profraw'
    assert glob.glob(pattern)


@pytest.mark.skipif(not os.getenv('FUZZBENCH_TEST_INTEGRATION'),
                    reason='Not running integration tests.')
class TestIntegrationRunCoverage:
    """Integration tests for run_coverage.py"""

    COVERAGE_BINARY_PATH = os.path.join(TEST_DATA_PATH, 'fuzz-target-clang-cov')

    def test_integration_do_coverage_run_crash(self, tmp_path):
        """Test that do_coverage_run returns crashing inputs."""
        units = _get_test_data_dir('crash-corpus')
        coverage_dir = _make_coverage_dir(tmp_path)
        profraw_file = os.path.join(coverage_dir, 'test_crash.profraw')
        crashes_dir = _make_crashes_dir(tmp_path)
        crashing_units = run_coverage.do_coverage_run(self.COVERAGE_BINARY_PATH,
                                                      units, profraw_file,
                                                      crashes_dir)

        # Ensure the crashing units are returned.
        assert crashing_units == ['86f7e437faa5a7fce15d1ddcb9eaeaea377667b8']
        _assert_profraw_files(coverage_dir)

    def test_integration_do_coverage_run_no_crash(self, tmp_path):
        """Test that do_coverage_run doesn't return crashing inputs when there
        are none."""
        units = _get_test_data_dir('corpus')
        coverage_dir = _make_coverage_dir(tmp_path)
        profraw_file = os.path.join(coverage_dir, 'test_no_crash.profraw')
        crashes_dir = _make_crashes_dir(tmp_path)
        crashing_units = run_coverage.do_coverage_run(self.COVERAGE_BINARY_PATH,
                                                      units, profraw_file,
                                                      crashes_dir)

        # Ensure no crashing unit is returned.
        assert not crashing_units
        _assert_profraw_files(coverage_dir)

    @mock.patch('common.logs.error')
    @mock.patch('experiment.measurer.run_coverage.MAX_TOTAL_TIME', 0)
    def test_integration_do_coverage_run_max_total_timeout(
            self, mocked_log_error, tmp_path):
        """Test that do_coverage_run respects max total time."""
        units = _get_test_data_dir('timeout-corpus')
        coverage_dir = _make_coverage_dir(tmp_path)
        profraw_file = os.path.join(coverage_dir, 'test_max_time.profraw')
        crashes_dir = _make_crashes_dir(tmp_path)
        crashing_units = run_coverage.do_coverage_run(self.COVERAGE_BINARY_PATH,
                                                      units, profraw_file,
                                                      crashes_dir)

        assert mocked_log_error.call_count
        # Ensure no crashing unit is returned.
        assert not crashing_units
