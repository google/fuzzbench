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
"""Tests for runner.py."""

import os
import pathlib
import posixpath
from unittest import mock

import pytest

from common import benchmark_config
from common import filestore_utils
from common import new_process
from experiment import runner
from test_libs import utils as test_utils

# pylint: disable=invalid-name,unused-argument,redefined-outer-name


@mock.patch('subprocess.Popen.communicate')
def test_run_fuzzer_log_file(mocked_communicate, fs, environ):
    """Test that run_fuzzer invokes the fuzzer defined run_fuzzer function as
    expected."""
    mocked_communicate.return_value = ('', 0)
    max_total_time = 1
    log_filename = '/log.txt'
    os.environ['MAX_TOTAL_TIME'] = str(max_total_time)
    os.environ['SEED_CORPUS_DIR'] = '/out/seeds'
    os.environ['OUTPUT_CORPUS_DIR'] = '/out/corpus'
    os.environ['FUZZ_TARGET'] = '/out/fuzz-target'
    os.environ['RUNNER_NICENESS'] = '-5'
    os.environ['FUZZER'] = 'afl'
    os.environ['BENCHMARK'] = 'freetype2-2017'
    fs.add_real_directory(benchmark_config.BENCHMARKS_DIR)
    fs.create_file('/out/fuzz-target')

    with test_utils.mock_popen_ctx_mgr() as mocked_popen:
        runner.run_fuzzer(max_total_time, log_filename)
        assert mocked_popen.commands == [[
            'nice', '-n', '5', 'python3', '-u', '-c',
            'from fuzzers.afl import fuzzer; '
            'fuzzer.fuzz("/out/seeds", "/out/corpus", "/out/fuzz-target")'
        ]]
    assert os.path.exists(log_filename)


MAX_TOTAL_TIME = 100
EXPERIMENT_FILESTORE = 'gs://bucket'
BENCHMARK = 'benchmark-1'
EXPERIMENT = 'experiment-name'
TRIAL_NUM = 1
FUZZER = 'fuzzer_a'


class FuzzerAModule:
    """A fake fuzzer.py module that impolements get_stats."""
    DEFAULT_STATS = '{"execs_per_sec":20.0}'

    @staticmethod
    def get_stats(output_directory, log_filename):
        """Returns a stats string."""
        return FuzzerAModule.DEFAULT_STATS


@pytest.fixture
def fuzzer_module():
    """Fixture that makes sure record_stats uses a fake fuzzer module."""
    with mock.patch('experiment.runner.get_fuzzer_module',
                    return_value=FuzzerAModule):
        yield


@pytest.fixture
def trial_runner(fs, environ):
    """Fixture that creates a TrialRunner object."""
    os.environ.update({
        'BENCHMARK': BENCHMARK,
        'EXPERIMENT': EXPERIMENT,
        'TRIAL_ID': str(TRIAL_NUM),
        'FUZZER': FUZZER,
        'EXPERIMENT_FILESTORE': EXPERIMENT_FILESTORE,
        'MAX_TOTAL_TIME': str(MAX_TOTAL_TIME),
        'OUTPUT_CORPUS_DIR': '/out/corpus',
    })

    with mock.patch('common.filestore_utils.rm'):
        trial_runner = runner.TrialRunner()
    trial_runner.initialize_directories()
    yield trial_runner


def test_record_stats(trial_runner, fuzzer_module):
    """Tests that record_stats records stats to a JSON file."""
    cycle = 1337
    trial_runner.cycle = cycle

    stats_file = os.path.join(trial_runner.results_dir, f'stats-{cycle}.json')
    trial_runner.record_stats()
    with open(stats_file, encoding='utf-8') as file_handle:
        stats_file_contents = file_handle.read()

    assert stats_file_contents == FuzzerAModule.DEFAULT_STATS


def test_record_stats_unsupported(trial_runner):
    """Tests that record_stats works as intended when fuzzer_module doesn't
    support get_stats."""
    cycle = 1338
    trial_runner.cycle = cycle

    class FuzzerAModuleNoGetStats:
        """Fake fuzzer.py module that doesn't implement get_stats."""

    with mock.patch('experiment.runner.get_fuzzer_module',
                    return_value=FuzzerAModuleNoGetStats):
        trial_runner.record_stats()

    stats_file = os.path.join(trial_runner.results_dir, f'stats-{cycle}.json')
    assert not os.path.exists(stats_file)


@pytest.mark.parametrize(('stats_data',), [('1',), ('{1:2}',),
                                           ('{"execs_per_sec": None}',)])
def test_record_stats_invalid(stats_data, trial_runner, fuzzer_module):
    """Tests that record_stats works as intended when fuzzer_module.get_stats
    exceptions."""
    cycle = 1337
    trial_runner.cycle = cycle

    class FuzzerAModuleCustomGetStats:
        """Fake fuzzer.py that implements get_stats."""

        @staticmethod
        def get_stats(output_directory, log_filename):
            """Fake get_stats method that returns stats_data."""
            return stats_data

    with mock.patch('experiment.runner.get_fuzzer_module',
                    return_value=FuzzerAModuleCustomGetStats):
        with mock.patch('common.logs.error') as mocked_log_error:
            trial_runner.record_stats()

    stats_file = os.path.join(trial_runner.results_dir, f'stats-{cycle}.json')
    assert not os.path.exists(stats_file)
    mocked_log_error.assert_called_with('Stats are invalid.')


@mock.patch('common.logs.error')
def test_record_stats_exception(mocked_log_error, trial_runner, fuzzer_module):
    """Tests that record_stats works as intended when fuzzer_module.get_stats
    exceptions."""
    cycle = 1337
    trial_runner.cycle = cycle

    class FuzzerAModuleGetStatsException:
        """Fake fuzzer.py module that exceptions when get_stats is called."""

        @staticmethod
        def get_stats(output_directory, log_filename):
            """Fake get_stats method that exceptions when called."""
            raise Exception()

    with mock.patch('experiment.runner.get_fuzzer_module',
                    return_value=FuzzerAModuleGetStatsException):
        trial_runner.record_stats()

    stats_file = os.path.join(trial_runner.results_dir, f'stats-{cycle}.json')
    assert not os.path.exists(stats_file)
    mocked_log_error.assert_called_with(
        'Call to %s failed.', FuzzerAModuleGetStatsException.get_stats)


def test_trial_runner(trial_runner):
    """Tests that TrialRunner gets initialized as it is supposed to."""
    assert trial_runner.gcs_sync_dir == (
        'gs://bucket/experiment-name/'
        'experiment-folders/benchmark-1-fuzzer_a/trial-1')

    assert trial_runner.cycle == 0


@mock.patch('common.logs.log')
def test_save_corpus_archive(_, trial_runner, fs):
    """Test that save_corpus_archive calls gsutil rsync on the corpus-archives
    directory."""
    archive_name = 'x.tar.gz'
    fs.create_file(archive_name, contents='')
    with test_utils.mock_popen_ctx_mgr() as mocked_popen:
        trial_runner.save_corpus_archive(archive_name)
        assert mocked_popen.commands == [[
            'gsutil', 'cp', archive_name,
            posixpath.join(
                'gs://bucket/experiment-name/experiment-folders/'
                'benchmark-1-fuzzer_a/trial-1/corpus', archive_name)
        ]]
    assert not os.path.exists(archive_name)


@mock.patch('common.logs.log')
def test_archive_corpus_name_correct(_, trial_runner):
    """Test that archive_corpus archives a corpus with the correct name."""
    trial_runner.cycle = 1337
    trial_runner.archive_corpus()
    assert str(trial_runner.cycle) in os.listdir(
        trial_runner.corpus_archives_dir)[0]


@mock.patch('common.logs.debug')
def test_do_sync_unchanged(mocked_debug, trial_runner, fuzzer_module):
    """Test that do_sync records if there was no corpus change since last
    cycle."""
    trial_runner.cycle = 1337
    with test_utils.mock_popen_ctx_mgr() as mocked_popen:
        trial_runner.do_sync()
        assert mocked_popen.commands == [
            [
                'gsutil', 'cp', '/corpus-archives/corpus-archive-1337.tar.gz',
                ('gs://bucket/experiment-name/experiment-folders/'
                 'benchmark-1-fuzzer_a/trial-1/corpus/'
                 'corpus-archive-1337.tar.gz')
            ],
            [
                'gsutil', 'rsync', '-d', '-r', '/results-copy',
                ('gs://bucket/experiment-name/experiment-folders/'
                 'benchmark-1-fuzzer_a/trial-1/results')
            ]
        ]
    assert not os.listdir(trial_runner.corpus_archives_dir)  # !!! make it work


@mock.patch('common.new_process.execute')
def test_do_sync_changed(mocked_execute, fs, trial_runner, fuzzer_module):
    """Test that do_sync archives and saves a corpus if it changed from the
    previous one."""
    mocked_execute.return_value = new_process.ProcessResult(0, '', False)
    corpus_file_name = 'corpus-file'
    fs.create_file(os.path.join(trial_runner.output_corpus, corpus_file_name))
    trial_runner.cycle = 1337
    trial_runner.do_sync()
    assert mocked_execute.call_args_list == [
        mock.call([
            'gsutil', 'cp', '/corpus-archives/corpus-archive-1337.tar.gz',
            ('gs://bucket/experiment-name/experiment-folders/'
             'benchmark-1-fuzzer_a/trial-1/corpus/'
             'corpus-archive-1337.tar.gz')
        ],
                  expect_zero=True),
        mock.call([
            'gsutil', 'rsync', '-d', '-r', '/results-copy',
            ('gs://bucket/experiment-name/experiment-folders/'
             'benchmark-1-fuzzer_a/trial-1/results')
        ],
                  expect_zero=True)
    ]
    # Archives should get deleted after syncing.
    archives = os.listdir(trial_runner.corpus_archives_dir)
    assert len(archives) == 0


class TestIntegrationRunner:
    """Integration tests for the runner."""

    @pytest.mark.skipif(not os.environ.get('TEST_EXPERIMENT_FILESTORE'),
                        reason='TEST_EXPERIMENT_FILESTORE is not set, '
                        'skipping integration test.')
    @mock.patch('common.logs.error')
    def test_integration_runner(self, mocked_error, tmp_path, environ):
        # pylint: disable=too-many-locals
        """Test that runner can run libFuzzer and saves snapshots to GCS."""
        # Switch cwd so that fuzzers don't create tons of files in the repo.
        os.chdir(tmp_path)

        # Set env variables that would be set by the Dockerfile.
        file_directory = pathlib.Path(__file__).parent

        root_dir = file_directory.parent
        os.environ['ROOT_DIR'] = str(root_dir)

        seed_corpus_dir = tmp_path / 'seeds'
        os.mkdir(seed_corpus_dir)
        os.environ['SEED_CORPUS_DIR'] = str(seed_corpus_dir)

        output_corpus_dir = tmp_path / 'corpus'
        os.mkdir(output_corpus_dir)
        os.environ['OUTPUT_CORPUS_DIR'] = str(output_corpus_dir)

        fuzzer = 'libfuzzer'
        fuzzer_parent_path = root_dir / 'fuzzers' / fuzzer

        benchmark = 'MultipleConstraintsOnSmallInputTest'
        test_experiment_bucket = os.environ['TEST_EXPERIMENT_FILESTORE']
        experiment = 'integration-test-experiment'
        gcs_directory = posixpath.join(test_experiment_bucket, experiment,
                                       'experiment-folders',
                                       f'{benchmark}-{fuzzer}', 'trial-1')
        filestore_utils.rm(gcs_directory, force=True)
        # Add fuzzer directory to make it easy to run fuzzer.py in local
        # configuration.
        os.environ['PYTHONPATH'] = ':'.join(
            [str(root_dir), str(fuzzer_parent_path)])

        # Set env variables that would set by the scheduler.
        os.environ['FUZZER'] = fuzzer
        os.environ['BENCHMARK'] = benchmark
        os.environ['EXPERIMENT_FILESTORE'] = test_experiment_bucket
        os.environ['EXPERIMENT'] = experiment

        os.environ['TRIAL_ID'] = str(TRIAL_NUM)

        max_total_time = 10
        os.environ['MAX_TOTAL_TIME'] = str(max_total_time)

        target_binary_path = (file_directory / 'test_data' / 'test_runner' /
                              benchmark)
        with mock.patch('common.fuzzer_utils.get_fuzz_target_binary',
                        return_value=str(target_binary_path)):
            with mock.patch('common.experiment_utils.get_snapshot_seconds',
                            return_value=max_total_time / 10):
                runner.main()

        gcs_corpus_directory = posixpath.join(gcs_directory, 'corpus')
        snapshots = filestore_utils.ls(gcs_corpus_directory)

        assert len(snapshots) >= 2

        # Check that the archives are deleted after being copied to GCS.
        assert not os.path.exists(
            tmp_path / 'corpus-archives' / 'corpus-archive-0001.tar.gz')

        local_gcs_corpus_dir_copy = tmp_path / 'gcs_corpus_dir'
        os.mkdir(local_gcs_corpus_dir_copy)
        filestore_utils.cp(posixpath.join(gcs_corpus_directory, '*'),
                           str(local_gcs_corpus_dir_copy),
                           recursive=True,
                           parallel=True)
        archive_size = os.path.getsize(local_gcs_corpus_dir_copy /
                                       'corpus-archive-0001.tar.gz')

        assert archive_size > 500

        assert len(os.listdir(output_corpus_dir)) > 5
        mocked_error.assert_not_called()


def test_clean_seed_corpus_no_seeds(fs):
    """Test that seed corpus files are deleted if NO_SEEDS is set in the
    environment to 'True'."""
    seed_corpus_dir = '/seeds'
    fs.create_dir(seed_corpus_dir)
    seed_file = os.path.join(seed_corpus_dir, 'a')
    fs.create_file(seed_file, contents='abc')
    runner._clean_seed_corpus(seed_corpus_dir)  # pylint: disable=protected-access
    assert not os.path.exists(seed_file)
    assert os.path.exists(seed_corpus_dir)


def test_clean_seed_corpus(fs):
    """Test that seed corpus files are moved to root directory and deletes files
    exceeding 1 MB limit."""
    seed_corpus_dir = '/seeds'
    fs.create_dir(seed_corpus_dir)

    fs.create_file(os.path.join(seed_corpus_dir, 'a', 'abc'), contents='abc')
    fs.create_file(os.path.join(seed_corpus_dir, 'def'), contents='def')
    fs.create_file(os.path.join(seed_corpus_dir, 'efg'), contents='a' * 1048577)

    runner._clean_seed_corpus(seed_corpus_dir)  # pylint: disable=protected-access

    assert not os.path.exists(os.path.join(seed_corpus_dir, 'a', 'abc'))
    assert not os.path.exists(os.path.join(seed_corpus_dir, 'def'))
    assert not os.path.exists(os.path.join(seed_corpus_dir, 'efg'))
    assert len(os.listdir(seed_corpus_dir)) == 3  # Directory 'a' and two files.

    with open(os.path.join(seed_corpus_dir,
                           'a9993e364706816aba3e25717850c26c9cd0d89d'),
              encoding='utf-8') as file_handle:
        assert file_handle.read() == 'abc'
    with open(os.path.join(seed_corpus_dir,
                           '589c22335a381f122d129225f5c0ba3056ed5811'),
              encoding='utf-8') as file_handle:
        assert file_handle.read() == 'def'


def _assert_elements_equal(l1, l2):
    """Assert that the elements of |l1| and |l2| are equal. Modifies |l1|
    and |l2| by sorting them."""
    assert list(sorted(l1)) == list(sorted(l2))


class TestUnpackClusterFuzzSeedCorpusIfNeeded:
    """Tests for _unpack_clusterfuzz_seed_corpus."""
    CORPUS_DIRECTORY = '/corpus'

    def _unpack_clusterfuzz_seed_corpus(self, fuzz_target_path):
        return runner._unpack_clusterfuzz_seed_corpus(  # pylint: disable=protected-access
            fuzz_target_path, self.CORPUS_DIRECTORY)

    def _list_corpus_dir(self):
        return os.listdir(self.CORPUS_DIRECTORY)

    def test_no_seed_corpus(self, fs):
        """Test that unpack_clusterfuzz_seed_corpus does nothing when there is
        no seed corpus."""
        fs.create_dir(self.CORPUS_DIRECTORY)
        self._unpack_clusterfuzz_seed_corpus('/fuzz-target')
        _assert_elements_equal([], self._list_corpus_dir())

    def test_unpack_clusterfuzz_seed_corpus(self, fs):
        """Tests unpack_clusterfuzz_seed_corpus can unpack a seed corpus."""
        fs.create_dir(self.CORPUS_DIRECTORY)
        fuzz_target_directory = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'test_data',
            'test_runner')
        seed_corpus_path = os.path.join(fuzz_target_directory,
                                        'fuzz-target_seed_corpus.zip')
        fs.add_real_file(seed_corpus_path)
        fuzz_target_path = os.path.join(os.path.dirname(seed_corpus_path),
                                        'fuzz-target')
        fs.create_file(fuzz_target_path)
        self._unpack_clusterfuzz_seed_corpus(fuzz_target_path)
        expected_dir_contents = [
            '0000000000000000', '0000000000000001', '0000000000000002'
        ]
        _assert_elements_equal(expected_dir_contents, self._list_corpus_dir())
