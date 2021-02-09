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

from common import config_utils, yaml_utils
from experiment.build import docker_images


@pytest.fixture(scope='class')
def experiment_config():
    """Returns the default configuration for end-to-end testing."""
    return config_utils.validate_and_expand(
        yaml_utils.read('fuzzbench/test_e2e/end-to-end-test-config.yaml'))


@pytest.fixture(scope='class')
def redis_connection():
    """Returns the default redis server connection."""
    return redis.Redis(host='queue-server')


# pylint: disable=no-self-use,redefined-outer-name
@pytest.mark.skipif('E2E_INTEGRATION_TEST' not in os.environ,
                    reason='Not running end-to-end test.')
@pytest.mark.usefixtures('redis_connection', 'experiment_config')
class TestEndToEndRunResults:
    """Checks the result of a test experiment run."""

    def test_jobs_dependency(self, experiment_config, redis_connection):
        """Tests that jobs dependency preserves during working."""
        all_images = docker_images.get_images_to_build(
            experiment_config['fuzzers'], experiment_config['benchmarks'])
        jobs = {
            name: rq.job.Job.fetch(name, connection=redis_connection)
            for name in all_images
        }
        for name, image in all_images.items():
            if 'depends_on' in image:
                for dep in image['depends_on']:
                    assert jobs[dep].ended_at <= jobs[name].started_at

    def test_all_jobs_finished_successfully(self, experiment_config,
                                            redis_connection):
        """Tests all jobs finished successully."""
        all_images = docker_images.get_images_to_build(
            experiment_config['fuzzers'], experiment_config['benchmarks'])
        jobs = rq.job.Job.fetch_many(all_images.keys(),
                                     connection=redis_connection)
        for job in jobs:
            assert job.get_status() == 'finished'

    def test_measurement_jobs_were_started_before_trial_jobs_finished(self):
        """Fake test to be implemented later."""
        assert True

    def test_db_contains_experiment_results(self):
        """Fake test to be implemented later."""
        assert True

    def test_experiment_report_is_generated(self):
        """Fake test to be implemented later."""
        assert True
