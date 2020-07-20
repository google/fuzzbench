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
"""Checks the result of a test experiment run. Note that this is not a
standalone unit test module, but used as part of our end-to-end integration
test."""

import os

import pytest

import redis
import rq
from rq.job import Job


# pylint: disable=no-self-use
@pytest.mark.skipif('E2E_INTEGRATION_TEST' not in os.environ,
                    reason='Not running end-to-end test.')
class TestEndToEndRunResults:
    """Checks the result of a test experiment run."""

    def test_all_jobs_finished_sucessfully(self):
        """Fake test to be implemented later."""
        assert True

    def test_measurement_jobs_were_started_before_trial_jobs_finished(self):
        """Fake test to be implemented later."""
        assert True

    def test_db_contains_experiment_results(self):
        """Fake test to be implemented later."""
        assert True

    def test_experiment_report_is_generated(self):
        """Fake test to be implemented later."""
        assert True
