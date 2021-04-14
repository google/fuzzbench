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
import itertools
import os
from unittest import mock

import pytest

from database import models
from database import utils as db_utils
from experiment import dispatcher
from test_libs import utils as test_utils

TEST_DATA_PATH = os.path.join(os.path.dirname(__file__), 'test_data')

# pylint: disable=invalid-name,redefined-outer-name,unused-argument,protected-access


def get_test_data_path(*subpaths):
    """Returns the path of |subpaths| relative to TEST_DATA_PATH."""
    return os.path.join(TEST_DATA_PATH, *subpaths)


def mock_split_successes_and_failures(inputs, results):
    """Mocked version of split_successes_and_failures. Returns inputs, [] as if
    there was a corresponding True value in |results| for every value in
    |inputs|."""
    return inputs, []


@pytest.fixture
@mock.patch('multiprocessing.pool.ThreadPool', test_utils.MockPool)
@mock.patch('experiment.build.builder.split_successes_and_failures',
            mock_split_successes_and_failures)
def dispatcher_experiment(fs, db, experiment):
    """Creates a dispatcher.Experiment object."""
    fs.create_dir(os.environ['WORK'])
    experiment_config_filepath = get_test_data_path('experiment-config.yaml')
    fs.add_real_file(experiment_config_filepath)
    return dispatcher.Experiment(experiment_config_filepath)


@mock.patch('multiprocessing.pool.ThreadPool', test_utils.MockPool)
def test_experiment(dispatcher_experiment):
    """Tests creating an Experiment object."""
    assert dispatcher_experiment.benchmarks == ['benchmark-1', 'benchmark-2']
    assert dispatcher_experiment.fuzzers == ['fuzzer-a', 'fuzzer-b']


def test_initialize_experiment_in_db(dispatcher_experiment):
    """Tests that _initialize_experiment_in_db adds the right things to the
    database."""
    trials_args = itertools.product(dispatcher_experiment.benchmarks,
                                    range(dispatcher_experiment.num_trials),
                                    dispatcher_experiment.fuzzers)
    trials = [
        models.Trial(fuzzer=fuzzer,
                     experiment=dispatcher_experiment.experiment_name,
                     benchmark=benchmark)
        for benchmark, _, fuzzer in trials_args
    ]
    dispatcher._initialize_experiment_in_db(dispatcher_experiment.config)
    dispatcher._initialize_trials_in_db(trials)

    with db_utils.session_scope() as session:
        db_experiments = session.query(models.Experiment).all()
        assert len(db_experiments) == 1
        db_experiment = db_experiments[0]
        assert db_experiment.name == os.environ['EXPERIMENT']
        trials = session.query(models.Trial).all()
        fuzzer_and_benchmarks = [
            (trial.benchmark, trial.fuzzer) for trial in trials
        ]
    assert fuzzer_and_benchmarks == ([('benchmark-1', 'fuzzer-a'),
                                      ('benchmark-1', 'fuzzer-b')] *
                                     4) + [('benchmark-2', 'fuzzer-a'),
                                           ('benchmark-2', 'fuzzer-b')] * 4


@mock.patch('experiment.build.builder.build_base_images', side_effect=Exception)
def test_build_images_for_trials_base_images_fail(dispatcher_experiment):
    """Tests that build_for_trial raises an exception when base images can't be
    built. This is important because the experiment should not proceed."""
    with pytest.raises(Exception):
        dispatcher.build_images_for_trials(dispatcher_experiment.fuzzers,
                                           dispatcher_experiment.benchmarks,
                                           dispatcher_experiment.num_trials,
                                           dispatcher_experiment.preemptible)


@mock.patch('experiment.build.builder.build_base_images')
def test_build_images_for_trials_build_success(_, dispatcher_experiment):
    """Tests that build_for_trial returns all trials we expect to run in an
    experiment when builds are successful."""
    fuzzer_benchmarks = list(
        itertools.product(dispatcher_experiment.fuzzers,
                          dispatcher_experiment.benchmarks))
    with mock.patch('experiment.build.builder.build_all_measurers',
                    return_value=dispatcher_experiment.benchmarks):
        with mock.patch('experiment.build.builder.build_all_fuzzer_benchmarks',
                        return_value=fuzzer_benchmarks):
            trials = dispatcher.build_images_for_trials(
                dispatcher_experiment.fuzzers, dispatcher_experiment.benchmarks,
                dispatcher_experiment.num_trials,
                dispatcher_experiment.preemptible)
    trial_fuzzer_benchmarks = [
        (trial.fuzzer, trial.benchmark) for trial in trials
    ]
    expected_trial_fuzzer_benchmarks = [
        fuzzer_benchmark for fuzzer_benchmark in fuzzer_benchmarks
        for _ in range(dispatcher_experiment.num_trials)
    ]
    assert (sorted(expected_trial_fuzzer_benchmarks) == sorted(
        trial_fuzzer_benchmarks))


@mock.patch('experiment.build.builder.build_base_images')
def test_build_images_for_trials_benchmark_fail(_, dispatcher_experiment):
    """Tests that build_for_trial doesn't return trials or try to build fuzzers
    for a benchmark whose coverage build failed."""
    successful_benchmark = 'benchmark-1'

    def mocked_build_all_fuzzer_benchmarks(fuzzers, benchmarks):
        assert benchmarks == [successful_benchmark]
        return list(itertools.product(fuzzers, benchmarks))

    with mock.patch('experiment.build.builder.build_all_measurers',
                    return_value=[successful_benchmark]):
        with mock.patch('experiment.build.builder.build_all_fuzzer_benchmarks',
                        side_effect=mocked_build_all_fuzzer_benchmarks):
            # Check this test so that we know we are actually testing behavior
            # when benchmarks fail.
            assert len(set(dispatcher_experiment.benchmarks)) > 1
            trials = dispatcher.build_images_for_trials(
                dispatcher_experiment.fuzzers, dispatcher_experiment.benchmarks,
                dispatcher_experiment.num_trials,
                dispatcher_experiment.preemptible)
    for trial in trials:
        assert trial.benchmark == successful_benchmark


@mock.patch('experiment.build.builder.build_base_images')
def test_build_images_for_trials_fuzzer_fail(_, dispatcher_experiment):
    """Tests that build_for_trial doesn't return trials a fuzzer whose build
    failed on a benchmark."""
    successful_fuzzer = 'fuzzer-a'
    fail_fuzzer = 'fuzzer-b'
    fuzzers = [successful_fuzzer, fail_fuzzer]
    successful_benchmark_for_fail_fuzzer = 'benchmark-1'
    fail_benchmark_for_fail_fuzzer = 'benchmark-2'
    benchmarks = [
        successful_benchmark_for_fail_fuzzer, fail_benchmark_for_fail_fuzzer
    ]
    successful_builds = [(successful_fuzzer, fail_benchmark_for_fail_fuzzer),
                         (successful_fuzzer,
                          successful_benchmark_for_fail_fuzzer),
                         (fail_fuzzer, successful_benchmark_for_fail_fuzzer)]
    num_trials = 10

    def mocked_build_all_fuzzer_benchmarks(fuzzers, benchmarks):
        # Sanity check this test so that we know we are actually testing
        # behavior when fuzzers fail.
        assert sorted(fuzzers) == sorted([successful_fuzzer, fail_fuzzer])
        assert successful_benchmark_for_fail_fuzzer in benchmarks
        return successful_builds

    with mock.patch('experiment.build.builder.build_all_measurers',
                    return_value=benchmarks):
        with mock.patch('experiment.build.builder.build_all_fuzzer_benchmarks',
                        side_effect=mocked_build_all_fuzzer_benchmarks):
            trials = dispatcher.build_images_for_trials(fuzzers, benchmarks,
                                                        num_trials, False)

    trial_fuzzer_benchmarks = [
        (trial.fuzzer, trial.benchmark) for trial in trials
    ]
    expected_trial_fuzzer_benchmarks = [
        fuzzer_benchmark for fuzzer_benchmark in successful_builds
        for _ in range(num_trials)
    ]
    assert (sorted(expected_trial_fuzzer_benchmarks) == sorted(
        trial_fuzzer_benchmarks))
