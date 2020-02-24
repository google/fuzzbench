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
"""Tests for dispatcher.py."""
import os
from unittest import mock

import pytest
import yaml

from common import fuzzer_config_utils
from database import models
from database import utils as db_utils
from experiment import dispatcher
from test_libs import utils as test_utils

TEST_DATA_PATH = os.path.join(os.path.dirname(__file__), 'test_data')
SANCOV_DIR = '/sancov'

# pylint: disable=invalid-name,redefined-outer-name,unused-argument


def get_test_data_path(*subpaths):
    """Returns the path of |subpaths| relative to TEST_DATA_PATH."""
    return os.path.join(TEST_DATA_PATH, *subpaths)


FUZZERS = ['fuzzer-a', 'fuzzer-b']


def mock_split_successes_and_failures(inputs, results):
    """Mocked version of split_successes_and_failures. Returns inputs, [] as if
    there was a corresponding True value in |results| for every value in
    |inputs|."""
    return inputs, []


@pytest.fixture
@mock.patch('multiprocessing.pool.ThreadPool', test_utils.MockPool)
@mock.patch('experiment.builder.split_successes_and_failures',
            mock_split_successes_and_failures)
def dispatcher_experiment(fs, db, experiment):
    """Creates a dispatcher.Experiment object."""
    experiment_config_filepath = get_test_data_path('experiment-config.yaml')
    fs.add_real_file(experiment_config_filepath)
    for fuzzer in FUZZERS:
        fs.create_file(os.path.join(
            fuzzer_config_utils.get_fuzzer_configs_dir(), fuzzer),
                       contents=yaml.dump({'fuzzer': fuzzer}))
    return dispatcher.Experiment(experiment_config_filepath)


@mock.patch('multiprocessing.pool.ThreadPool', test_utils.MockPool)
def test_experiment(dispatcher_experiment):
    """Tests creating an Experiment object."""
    assert dispatcher_experiment.benchmarks == ['benchmark-1', 'benchmark-2']
    assert dispatcher_experiment.fuzzers == FUZZERS
    assert (
        dispatcher_experiment.web_bucket == 'gs://web-reports/test-experiment')
    db_experiments = db_utils.query(models.Experiment).all()
    assert len(db_experiments) == 1
    db_experiment = db_experiments[0]
    assert db_experiment.name == os.environ['EXPERIMENT']
    trials = db_utils.query(models.Trial).all()
    fuzzer_and_benchmarks = [(trial.benchmark, trial.fuzzer) for trial in trials
                            ]
    assert fuzzer_and_benchmarks == ([('benchmark-1', 'fuzzer-a'),
                                      ('benchmark-1', 'fuzzer-b')] *
                                     4) + [('benchmark-2', 'fuzzer-a'),
                                           ('benchmark-2', 'fuzzer-b')] * 4
