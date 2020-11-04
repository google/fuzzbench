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
"""Tests for run_coverage.py."""

# pylint: disable=no-self-use

import os

import pytest

from experiment.measurer import run_crashes

TEST_DATA_PATH = os.path.join(os.path.dirname(__file__), 'test_data',
                              'test_run_crashes')


@pytest.mark.skipif(not os.getenv('FUZZBENCH_TEST_INTEGRATION'),
                    reason='Not running integration tests.')
class TestIntegrationRunCoverage:
    """Integration tests for run_crashes.py"""

    APP_BINARY_PATH = os.path.join(TEST_DATA_PATH, 'fuzz-target')

    def test_integration_do_coverage_run_crash(self):
        """Test that do_coverage_run returns crashing inputs."""
        llvm_tools_path = os.path.abspath(
            os.path.join(TEST_DATA_PATH, '..', 'llvm_tools'))
        os.environ["PATH"] = llvm_tools_path + os.pathsep + os.environ["PATH"]

        crashes_dir = os.path.join(TEST_DATA_PATH, 'crash-corpus')
        crashes = run_crashes.do_crashes_run(self.APP_BINARY_PATH, crashes_dir)

        expected_crash_key = 'Abrt:fuzz_target.c\n'
        assert len(crashes) == 1
        assert expected_crash_key in crashes
        assert crashes[expected_crash_key]['crash_testcase'] == 'crash'
        assert crashes[expected_crash_key]['crash_type'] == 'Abrt'
        assert crashes[expected_crash_key]['crash_address']
        assert crashes[expected_crash_key]['crash_state'] == 'fuzz_target.c\n'
        assert ('ERROR: AddressSanitizer: ABRT on unknown address'
                in crashes[expected_crash_key]['crash_stacktrace'])
