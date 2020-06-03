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
"""Tests for measure_worker.py."""
import json
import os
import shutil
from unittest import mock

import pytest

from common import experiment_utils
from common import new_process
from database import models
from database import utils as db_utils
from experiment.build import build_utils
from experiment.measurer import measure_worker
from test_libs import utils as test_utils

TEST_DATA_PATH = os.path.join(os.path.dirname(__file__), 'test_data')

SNAPSHOT_LOGGER = measure_worker.logger

# Arbitrary values to use in tests.
FUZZER = 'fuzzer-a'
BENCHMARK = 'benchmark-a'
TRIAL_NUM = 12
FUZZERS = ['fuzzer-a', 'fuzzer-b']
BENCHMARKS = ['benchmark-1', 'benchmark-2']
NUM_TRIALS = 4
GIT_HASH = 'FAKE-GIT-HASH'

# pylint: disable=unused-argument,invalid-name


def get_test_data_path(*subpaths):
    """Returns the path of |subpaths| relative to TEST_DATA_PATH."""
    return os.path.join(TEST_DATA_PATH, *subpaths)


@pytest.fixture
def db_experiment(experiment_config, db):
    """A fixture that populates the database with an experiment entity with the
    name specified in the experiment_config fixture."""
    experiment = models.Experiment(name=experiment_config['experiment'])
    db_utils.add_all([experiment])
    # yield so that the experiment exists until the using function exits.
    yield


@pytest.mark.parametrize('new_pcs', [{'0x1', '0x2'}, set()])
@mock.patch('common.gsutil.cp')
@mock.patch(
    'experiment.measurer.measure_worker.SnapshotMeasurer.get_prev_covered_pcs')
def test_merge_new_pcs(mocked_get_prev_covered_pcs, mocked_cp, new_pcs, fs,
                       experiment):
    """Tests that merge_new_pcs merges new PCs, and updates the covered-pcs
    file."""
    # Have some previously covered PCs to make the test more realistic.
    prev_pcs = {'0x425221'}
    mocked_get_prev_covered_pcs.return_value = prev_pcs
    snapshot_measurer = measure_worker.SnapshotMeasurer(FUZZER, BENCHMARK,
                                                        TRIAL_NUM,
                                                        SNAPSHOT_LOGGER)
    fs.create_file(os.path.join(snapshot_measurer.sancov_dir, '1.sancov'))

    def mock_cp(*cat_arguments, **kwargs):
        src_name, dst_name = cat_arguments
        with open(src_name) as src_handle:
            assert json.loads(src_handle.read()) == list(
                sorted(new_pcs.union(prev_pcs)))

        assert dst_name == (
            'gs://experiment-data/test-experiment/measurement-folders/'
            'benchmark-a-fuzzer-a/trial-12/state/covered-pcs-0002.json')

    mocked_cp.side_effect = mock_cp

    with mock.patch('third_party.sancov.GetPCs') as mocked_GetPCs:
        mocked_GetPCs.return_value = new_pcs
        snapshot_measurer.merge_new_pcs(2)

    assert mocked_cp.call_count == 1


@mock.patch('experiment.measurer.measure_worker.set_up_coverage_binary')
@mock.patch('common.logs.error')
@mock.patch('experiment.measurer.measure_worker.initialize_logs')
@mock.patch('experiment.measurer.measure_worker.measure_snapshot_coverage')
def test_measure_trial_coverage(mocked_measure_snapshot_coverage, _, __, ___):
    """Tests that measure_trial_coverage works as expected."""
    min_cycle = 1
    measure_request = measure_worker.SnapshotMeasureRequest(
        FUZZER, BENCHMARK, TRIAL_NUM, min_cycle)
    measure_worker.measure_trial_coverage(measure_request)
    expected_calls = [mock.call(FUZZER, BENCHMARK, TRIAL_NUM, min_cycle)]
    assert mocked_measure_snapshot_coverage.call_args_list == expected_calls


def test_is_cycle_unchanged_doesnt_exist(experiment):
    """Test that is_cycle_unchanged can properly determine if a cycle is
    unchanged or not when it needs to copy the file for the first time."""
    snapshot_measurer = measure_worker.SnapshotMeasurer(FUZZER, BENCHMARK,
                                                        TRIAL_NUM,
                                                        SNAPSHOT_LOGGER)
    this_cycle = 1
    with test_utils.mock_popen_ctx_mgr(returncode=1):
        assert not snapshot_measurer.is_cycle_unchanged(this_cycle)


@mock.patch('common.gsutil.cp')
@mock.patch('common.filesystem.read')
def test_is_cycle_unchanged_first_copy(mocked_read, mocked_cp, experiment):
    """Test that is_cycle_unchanged can properly determine if a cycle is
    unchanged or not when it needs to copy the file for the first time."""
    snapshot_measurer = measure_worker.SnapshotMeasurer(FUZZER, BENCHMARK,
                                                        TRIAL_NUM,
                                                        SNAPSHOT_LOGGER)
    this_cycle = 100
    unchanged_cycles_file_contents = (
        '\n'.join([str(num) for num in range(10)] + [str(this_cycle)]))
    mocked_read.return_value = unchanged_cycles_file_contents
    mocked_cp.return_value = new_process.ProcessResult(0, '', False)

    assert snapshot_measurer.is_cycle_unchanged(this_cycle)
    assert not snapshot_measurer.is_cycle_unchanged(this_cycle + 1)


def test_is_cycle_unchanged_update(fs, experiment):
    """Test that is_cycle_unchanged can properly determine that a
    cycle has changed when it has the file but needs to update it."""
    snapshot_measurer = measure_worker.SnapshotMeasurer(FUZZER, BENCHMARK,
                                                        TRIAL_NUM,
                                                        SNAPSHOT_LOGGER)

    this_cycle = 100
    initial_unchanged_cycles_file_contents = (
        '\n'.join([str(num) for num in range(10)] + [str(this_cycle)]))
    fs.create_file(snapshot_measurer.unchanged_cycles_path,
                   contents=initial_unchanged_cycles_file_contents)

    next_cycle = this_cycle + 1
    unchanged_cycles_file_contents = (initial_unchanged_cycles_file_contents +
                                      '\n' + str(next_cycle))
    assert snapshot_measurer.is_cycle_unchanged(this_cycle)
    with mock.patch('common.gsutil.cp') as mocked_cp:
        with mock.patch('common.filesystem.read') as mocked_read:
            mocked_cp.return_value = new_process.ProcessResult(0, '', False)
            mocked_read.return_value = unchanged_cycles_file_contents
            assert snapshot_measurer.is_cycle_unchanged(next_cycle)


@mock.patch('common.gsutil.cp')
def test_is_cycle_unchanged_skip_cp(mocked_cp, fs, experiment):
    """Check that is_cycle_unchanged doesn't call gsutil.cp unnecessarily."""
    snapshot_measurer = measure_worker.SnapshotMeasurer(FUZZER, BENCHMARK,
                                                        TRIAL_NUM,
                                                        SNAPSHOT_LOGGER)
    this_cycle = 100
    initial_unchanged_cycles_file_contents = (
        '\n'.join([str(num) for num in range(10)] + [str(this_cycle + 1)]))
    fs.create_file(snapshot_measurer.unchanged_cycles_path,
                   contents=initial_unchanged_cycles_file_contents)
    assert not snapshot_measurer.is_cycle_unchanged(this_cycle)
    mocked_cp.assert_not_called()


@mock.patch('common.gsutil.cp')
def test_is_cycle_unchanged_no_file(mocked_cp, fs, experiment):
    """Test that is_cycle_unchanged returns False when there is no
    unchanged-cycles file."""
    # Make sure we log if there is no unchanged-cycles file.
    snapshot_measurer = measure_worker.SnapshotMeasurer(FUZZER, BENCHMARK,
                                                        TRIAL_NUM,
                                                        SNAPSHOT_LOGGER)
    mocked_cp.return_value = new_process.ProcessResult(1, '', False)
    assert not snapshot_measurer.is_cycle_unchanged(0)


@mock.patch('common.new_process.execute')
def test_run_cov_new_units(mocked_execute, fs, environ):
    """Tests that run_cov_new_units does a coverage run as we expect."""
    os.environ = {
        'WORK': '/work',
        'CLOUD_EXPERIMENT_BUCKET': 'gs://bucket',
        'EXPERIMENT': 'experiment',
    }
    mocked_execute.return_value = new_process.ProcessResult(0, '', False)
    snapshot_measurer = measure_worker.SnapshotMeasurer(FUZZER, BENCHMARK,
                                                        TRIAL_NUM,
                                                        SNAPSHOT_LOGGER)
    snapshot_measurer.initialize_measurement_dirs()
    new_units = ['new1', 'new2']
    for unit in new_units:
        fs.create_file(os.path.join(snapshot_measurer.corpus_dir, unit))
    fuzz_target_path = '/work/coverage-binaries/benchmark-a/fuzz-target'
    fs.create_file(fuzz_target_path)

    snapshot_measurer.run_cov_new_units()
    assert len(mocked_execute.call_args_list) == 1  # Called once
    args = mocked_execute.call_args_list[0]
    command_arg = args[0][0]
    assert command_arg[0] == fuzz_target_path
    expected = {
        'cwd': '/work/coverage-binaries/benchmark-a',
        'env': {
            'UBSAN_OPTIONS': ('coverage_dir='
                              '/work/measurement-folders/benchmark-a-fuzzer-a'
                              '/trial-12/sancovs'),
            'WORK': '/work',
            'CLOUD_EXPERIMENT_BUCKET': 'gs://bucket',
            'EXPERIMENT': 'experiment',
        },
        'expect_zero': False,
    }
    args = args[1]
    for arg, value in expected.items():
        assert args[arg] == value


# pylint: disable=no-self-use


class TestIntegrationMeasurement:
    """Integration tests for measurement."""

    # TODO(metzman): Get this test working everywhere by using docker or a more
    # portable binary.
    @pytest.mark.skipif(not os.getenv('FUZZBENCH_TEST_INTEGRATION'),
                        reason='Not running integration tests.')
    @mock.patch(
        'experiment.measurer.measure_worker.SnapshotMeasurer.is_cycle_unchanged'
    )
    def test_measure_snapshot_coverage(  # pylint: disable=too-many-locals
            self, mocked_is_cycle_unchanged, db, experiment, tmp_path):
        """Integration test for measure_snapshot_coverage."""
        # WORK is set by experiment to a directory that only makes sense in a
        # fakefs.
        os.environ['WORK'] = str(tmp_path)
        mocked_is_cycle_unchanged.return_value = False
        # Set up the coverage binary.
        benchmark = 'freetype2-2017'
        coverage_binary_src = get_test_data_path(
            'test_measure_snapshot_coverage', benchmark + '-coverage')
        benchmark_cov_binary_dir = os.path.join(
            build_utils.get_coverage_binaries_dir(), benchmark)

        os.makedirs(benchmark_cov_binary_dir)
        coverage_binary_dst_dir = os.path.join(benchmark_cov_binary_dir,
                                               'fuzz-target')

        shutil.copy(coverage_binary_src, coverage_binary_dst_dir)

        # Set up entities in database so that the snapshot can be created.
        experiment = models.Experiment(name=os.environ['EXPERIMENT'])
        db_utils.add_all([experiment])
        trial = models.Trial(fuzzer=FUZZER,
                             benchmark=benchmark,
                             experiment=os.environ['EXPERIMENT'])
        db_utils.add_all([trial])

        snapshot_measurer = measure_worker.SnapshotMeasurer(
            trial.fuzzer, trial.benchmark, trial.id, SNAPSHOT_LOGGER)

        # Set up the snapshot archive.
        cycle = 1
        archive = get_test_data_path('test_measure_snapshot_coverage',
                                     'corpus-archive-%04d.tar.gz' % cycle)
        corpus_dir = os.path.join(snapshot_measurer.trial_dir, 'corpus')
        os.makedirs(corpus_dir)
        shutil.copy(archive, corpus_dir)

        with mock.patch('common.gsutil.cp') as mocked_cp:
            mocked_cp.return_value = new_process.ProcessResult(0, '', False)
            # TODO(metzman): Create a system for using actual buckets in
            # integration tests.
            snapshot = measure_worker.measure_snapshot_coverage(
                snapshot_measurer.fuzzer, snapshot_measurer.benchmark,
                snapshot_measurer.trial_num, cycle)
        assert snapshot
        assert snapshot.time == cycle * experiment_utils.get_snapshot_seconds()
        assert snapshot.edges_covered == 3798


@pytest.mark.parametrize('archive_name',
                         ['libfuzzer-corpus.tgz', 'afl-corpus.tgz'])
def test_extract_corpus(archive_name, tmp_path):
    """"Tests that extract_corpus unpacks a corpus as we expect."""
    archive_path = get_test_data_path(archive_name)
    measure_worker.extract_corpus(archive_path, set(), tmp_path)
    expected_corpus_files = {
        '5ea57dfc9631f35beecb5016c4f1366eb6faa810',
        '2f1507c3229c5a1f8b619a542a8e03ccdbb3c29c',
        'b6ccc20641188445fa30c8485a826a69ac4c6b60'
    }
    assert expected_corpus_files.issubset(set(os.listdir(tmp_path)))
