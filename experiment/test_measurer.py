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
"""Tests for measurer.py."""

import datetime
import os
import shutil
from unittest import mock
import queue

import pytest

from common import experiment_utils
from common import new_process
from database import models
from database import utils as db_utils
from experiment.build import build_utils
from experiment import dispatcher
from experiment import measurer
from experiment import scheduler
from test_libs import utils as test_utils

TEST_DATA_PATH = os.path.join(os.path.dirname(__file__), 'test_data')

# Arbitrary values to use in tests.
FUZZER = 'fuzzer-a'
BENCHMARK = 'benchmark-a'
TRIAL_NUM = 12
FUZZERS = ['fuzzer-a', 'fuzzer-b']
BENCHMARKS = ['benchmark-1', 'benchmark-2']
NUM_TRIALS = 4
MAX_TOTAL_TIME = 100
GIT_HASH = 'FAKE-GIT-HASH'

SNAPSHOT_LOGGER = measurer.logger

# pylint: disable=unused-argument,invalid-name,redefined-outer-name,protected-access


@pytest.mark.parametrize('new_pcs', [['0x1', '0x2'], []])
def test_merge_new_pcs(new_pcs, fs, experiment):
    """Tests that merge_new_pcs merges new PCs, and updates the covered-pcs
    file."""
    snapshot_measurer = measurer.SnapshotMeasurer(FUZZER, BENCHMARK, TRIAL_NUM,
                                                  SNAPSHOT_LOGGER)

    covered_pcs_filename = get_test_data_path('covered-pcs.txt')
    fs.add_real_file(covered_pcs_filename, read_only=False)
    snapshot_measurer.sancov_dir = os.path.dirname(covered_pcs_filename)
    snapshot_measurer.covered_pcs_filename = covered_pcs_filename

    with open(covered_pcs_filename) as file_handle:
        initial_contents = file_handle.read()

    fs.create_file(os.path.join(snapshot_measurer.sancov_dir, '1.sancov'),
                   contents='')
    with mock.patch('third_party.sancov.GetPCs') as mocked_GetPCs:
        mocked_GetPCs.return_value = new_pcs
        snapshot_measurer.merge_new_pcs()
    with open(covered_pcs_filename) as file_handle:
        new_contents = file_handle.read()
    assert new_contents == (''.join(pc + '\n' for pc in new_pcs) +
                            initial_contents)


@mock.patch('common.logs.error')
@mock.patch('experiment.measurer.initialize_logs')
@mock.patch('multiprocessing.Queue')
@mock.patch('experiment.measurer.measure_snapshot_coverage')
def test_measure_trial_coverage(mocked_measure_snapshot_coverage, mocked_queue,
                                _, __):
    """Tests that measure_trial_coverage works as expected."""
    min_cycle = 1
    max_cycle = 10
    measure_request = measurer.SnapshotMeasureRequest(FUZZER, BENCHMARK,
                                                      TRIAL_NUM, min_cycle)
    measurer.measure_trial_coverage(measure_request, max_cycle, mocked_queue())
    expected_calls = [
        mock.call(FUZZER, BENCHMARK, TRIAL_NUM, cycle)
        for cycle in range(min_cycle, max_cycle + 1)
    ]
    assert mocked_measure_snapshot_coverage.call_args_list == expected_calls


@mock.patch('common.gsutil.ls')
@mock.patch('common.gsutil.rsync')
def test_measure_all_trials_not_ready(mocked_rsync, mocked_ls, experiment):
    """Test running measure_all_trials before it is ready works as intended."""
    mocked_ls.return_value = ([], 1)
    assert measurer.measure_all_trials(experiment_utils.get_experiment_name(),
                                       MAX_TOTAL_TIME, test_utils.MockPool(),
                                       queue.Queue())
    assert not mocked_rsync.called


NEW_UNIT = 'new'
OLD_UNIT = 'old'


@pytest.mark.skip(
    reason="Figure out how to test this with the async snapshot save loop.")
@mock.patch('common.new_process.execute')
@mock.patch('multiprocessing.Manager')
@mock.patch('multiprocessing.pool')
def test_measure_all_trials(_, __, mocked_execute, db, fs):
    """Tests that measure_all_trials does what is intended under normal
    conditions."""
    mocked_execute.return_value = new_process.ProcessResult(0, '', False)

    dispatcher._initialize_experiment_in_db(
        experiment_utils.get_experiment_name(), GIT_HASH, BENCHMARKS, FUZZERS,
        NUM_TRIALS)
    trials = scheduler.get_pending_trials(
        experiment_utils.get_experiment_name()).all()
    for trial in trials:
        trial.time_started = datetime.datetime.utcnow()
    db_utils.add_all(trials)

    fs.create_file(measurer.get_experiment_folders_dir() / NEW_UNIT)
    mock_pool = test_utils.MockPool()

    assert measurer.measure_all_trials(experiment_utils.get_experiment_name(),
                                       MAX_TOTAL_TIME, mock_pool, queue.Queue())

    actual_ids = [call[2] for call in mock_pool.func_calls]
    # 4 (trials) * 2 (fuzzers) * 2 (benchmarks)
    assert sorted(actual_ids) == list(range(1, 17))


@mock.patch('multiprocessing.pool.ThreadPool', test_utils.MockPool)
@mock.patch('common.new_process.execute')
@mock.patch('common.filesystem.directories_have_same_files')
@pytest.mark.skip(reason="See crbug.com/1012329")
def test_measure_all_trials_no_more(mocked_directories_have_same_files,
                                    mocked_execute):
    """Test measure_all_trials does what is intended when the experiment is
    done."""
    mocked_directories_have_same_files.return_value = True
    mocked_execute.return_value = new_process.ProcessResult(0, '', False)
    mock_pool = test_utils.MockPool()
    assert not measurer.measure_all_trials(
        experiment_utils.get_experiment_name(), MAX_TOTAL_TIME, mock_pool,
        queue.Queue())


def test_is_cycle_unchanged_doesnt_exist(experiment):
    """Test that is_cycle_unchanged can properly determine if a cycle is
    unchanged or not when it needs to copy the file for the first time."""
    snapshot_measurer = measurer.SnapshotMeasurer(FUZZER, BENCHMARK, TRIAL_NUM,
                                                  SNAPSHOT_LOGGER)
    this_cycle = 1
    with test_utils.mock_popen_ctx_mgr(returncode=1):
        assert not snapshot_measurer.is_cycle_unchanged(this_cycle)


@mock.patch('common.gsutil.cp')
@mock.patch('common.filesystem.read')
def test_is_cycle_unchanged_first_copy(mocked_read, mocked_cp, experiment):
    """Test that is_cycle_unchanged can properly determine if a cycle is
    unchanged or not when it needs to copy the file for the first time."""
    snapshot_measurer = measurer.SnapshotMeasurer(FUZZER, BENCHMARK, TRIAL_NUM,
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
    snapshot_measurer = measurer.SnapshotMeasurer(FUZZER, BENCHMARK, TRIAL_NUM,
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
    snapshot_measurer = measurer.SnapshotMeasurer(FUZZER, BENCHMARK, TRIAL_NUM,
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
    snapshot_measurer = measurer.SnapshotMeasurer(FUZZER, BENCHMARK, TRIAL_NUM,
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
    snapshot_measurer = measurer.SnapshotMeasurer(FUZZER, BENCHMARK, TRIAL_NUM,
                                                  SNAPSHOT_LOGGER)
    snapshot_measurer.initialize_measurement_dirs()
    shared_units = ['shared1', 'shared2']
    fs.create_file(snapshot_measurer.measured_files_path,
                   contents='\n'.join(shared_units))
    for unit in shared_units:
        fs.create_file(os.path.join(snapshot_measurer.corpus_dir, unit))

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
                              '/work/measurement-folders/benchmark-a/fuzzer-a'
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


def get_test_data_path(*subpaths):
    """Returns the path of |subpaths| relative to TEST_DATA_PATH."""
    return os.path.join(TEST_DATA_PATH, *subpaths)


# pylint: disable=no-self-use


class TestIntegrationMeasurement:
    """Integration tests for measurement."""

    # TODO(metzman): Get this test working everywhere by using docker or a more
    # portable binary.
    @pytest.mark.skipif(not os.getenv('FUZZBENCH_TEST_INTEGRATION'),
                        reason='Not running integration tests.')
    @mock.patch('experiment.measurer.SnapshotMeasurer.is_cycle_unchanged')
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

        snapshot_measurer = measurer.SnapshotMeasurer(trial.fuzzer,
                                                      trial.benchmark, trial.id,
                                                      SNAPSHOT_LOGGER)

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
            snapshot = measurer.measure_snapshot_coverage(
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
    measurer.extract_corpus(archive_path, set(), tmp_path)
    expected_corpus_files = {
        '5ea57dfc9631f35beecb5016c4f1366eb6faa810',
        '2f1507c3229c5a1f8b619a542a8e03ccdbb3c29c',
        'b6ccc20641188445fa30c8485a826a69ac4c6b60'
    }
    assert expected_corpus_files.issubset(set(os.listdir(tmp_path)))


@mock.patch('experiment.scheduler.all_trials_ended')
@mock.patch('experiment.measurer.set_up_coverage_binaries')
@mock.patch('experiment.measurer.measure_all_trials')
@mock.patch('multiprocessing.Manager')
@mock.patch('multiprocessing.pool')
def test_measure_loop_end(_, mocked_manager, mocked_measure_all_trials, __,
                          mocked_all_trials_ended):
    """Tests that measure_loop stops when there is nothing left to measure."""
    call_count = 0

    def mock_measure_all_trials(*args, **kwargs):
        # Do the assertions here so that there will be an assert fail on failure
        # instead of an infinite loop.
        nonlocal call_count
        assert call_count == 0
        call_count += 1
        return False

    mocked_measure_all_trials.side_effect = mock_measure_all_trials
    mocked_all_trials_ended.return_value = True
    measurer.measure_loop('', 0)
    # If everything went well, we should get to this point without any exception
    # failures.
