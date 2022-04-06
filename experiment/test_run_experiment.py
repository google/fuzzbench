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
"""Tests for run_experiment.py."""

import os
from unittest import mock
import unittest

import pytest

from experiment import run_experiment

BENCHMARKS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), os.pardir))

# pylint: disable=no-value-for-parameter


def test_validate_benchmarks_valid_benchmarks():
    """Tests that validate_benchmarks properly validates and parses a list of
    valid benchmarks."""
    # It won't raise an exception if everything is valid.
    run_experiment.validate_benchmarks(['freetype2-2017', 'libxml2-v2.9.2'])


def test_validate_benchmarks_invalid_benchmark():
    """Tests that validate_benchmarks does not validate invalid benchmarks."""
    with pytest.raises(run_experiment.ValidationError):
        run_experiment.validate_benchmarks('fake_benchmark')
    with pytest.raises(run_experiment.ValidationError):
        run_experiment.validate_benchmarks('common.sh')


class TestReadAndValdiateExperimentConfig(unittest.TestCase):
    """Tests for read_and_validate_experiment_config."""

    def setUp(self):
        self.config_filename = 'config'
        self.config = {
            'experiment_filestore': 'gs://bucket',
            'report_filestore': 'gs://web-bucket',
            'experiment': 'experiment-name',
            'docker_registry': 'gcr.io/fuzzbench',
            'cloud_project': 'fuzzbench',
            'cloud_compute_zone': 'us-central1-a',
            'trials': 10,
            'max_total_time': 1000,
        }

    @mock.patch('common.logs.error')
    def test_missing_required(self, mocked_error):
        """Tests that an error is logged when the config file is missing a
        required config parameter."""
        # All but trials.
        del self.config['trials']
        with mock.patch('common.yaml_utils.read') as mocked_read_yaml:
            mocked_read_yaml.return_value = self.config
            with pytest.raises(run_experiment.ValidationError):
                run_experiment.read_and_validate_experiment_config(
                    'config_file')
            mocked_error.assert_called_with('Config does not contain "%s".',
                                            'trials')

    @mock.patch('common.logs.error')
    def test_missing_required_cloud(self, mocked_error):
        """Tests that an error is logged when the config file is missing a
        required cloudconfig parameter."""
        # All but cloud_compute_zone.
        del self.config['cloud_compute_zone']
        with mock.patch('common.yaml_utils.read') as mocked_read_yaml:
            mocked_read_yaml.return_value = self.config
            with pytest.raises(run_experiment.ValidationError):
                run_experiment.read_and_validate_experiment_config(
                    'config_file')
            mocked_error.assert_called_with('Config does not contain "%s".',
                                            'cloud_compute_zone')

    def test_invalid_upper(self):
        """Tests that an error is logged when the config file has a config
        parameter that should be a lower case string but has some upper case
        chars."""
        self._test_invalid(
            'experiment_filestore', 'gs://EXPERIMENT',
            'Config parameter "%s" is "%s". It must be a lowercase string.')

    def test_invalid_string(self):
        """Tests that an error is logged when the config file has a config
        parameter that should be a string but is not."""
        self._test_invalid(
            'experiment_filestore', 1,
            'Config parameter "%s" is "%s". It must be a lowercase string.')

    def test_invalid_local_filestore(self):
        """Tests that an error is logged when the config file has a config
        parameter that should be a local filestore but is not."""
        self.config['local_experiment'] = True
        self.config['experiment_filestore'] = '/user/test/folder'
        self._test_invalid(
            'report_filestore', 'gs://wrong-here', 'Config parameter "%s" is '
            '"%s". Local experiments only support using Posix file systems as '
            'filestores.')

    def test_invalid_cloud_filestore(self):
        """Tests that an error is logged when the config file has a config
        parameter that should be a GCS bucket but is not."""
        self._test_invalid(
            'experiment_filestore', 'invalid', 'Config parameter "%s" is "%s". '
            'It must start with gs:// when running on Google Cloud.')

    @mock.patch('common.logs.error')
    def test_multiple_invalid(self, mocked_error):
        """Test that multiple errors are logged when multiple parameters are
        invalid."""
        self.config['experiment_filestore'] = 1
        self.config['report_filestore'] = None
        with mock.patch('common.yaml_utils.read') as mocked_read_yaml:
            mocked_read_yaml.return_value = self.config
            with pytest.raises(run_experiment.ValidationError):
                run_experiment.read_and_validate_experiment_config(
                    'config_file')
        mocked_error.assert_any_call(
            'Config parameter "%s" is "%s". It must be a lowercase string.',
            'experiment_filestore', str(self.config['experiment_filestore']))
        mocked_error.assert_any_call(
            'Config parameter "%s" is "%s". It must be a lowercase string.',
            'report_filestore', str(self.config['report_filestore']))

    @mock.patch('common.logs.error')
    def _test_invalid(self, param, value, expected_log_message, mocked_error):
        """Tests that |expected_log_message| is logged as an error when config
        |param| is |value| which is invalid."""
        # Don't parameterize this function, it would be too messsy.
        self.config[param] = value
        with mock.patch('common.yaml_utils.read') as mocked_read_yaml:
            mocked_read_yaml.return_value = self.config
            with pytest.raises(run_experiment.ValidationError):
                run_experiment.read_and_validate_experiment_config(
                    'config_file')
        mocked_error.assert_called_with(expected_log_message, param, str(value))

    @mock.patch('common.logs.error')
    def test_read_and_validate_experiment_config(self, _):
        """Tests that read_and_validat_experiment_config works as intended when
        config is valid."""
        with mock.patch('common.yaml_utils.read') as mocked_read_yaml:
            mocked_read_yaml.return_value = self.config
            assert (self.config == run_experiment.
                    read_and_validate_experiment_config('config_file'))


def test_validate_fuzzer():
    """Tests that validate_fuzzer says that a valid fuzzer name is valid and
    that an invalid one is not."""
    run_experiment.validate_fuzzer('afl')

    with pytest.raises(run_experiment.ValidationError) as exception:
        run_experiment.validate_fuzzer('afl:')
    assert 'is invalid' in str(exception.value)

    with pytest.raises(run_experiment.ValidationError) as exception:
        run_experiment.validate_fuzzer('not_exist')
    assert 'is invalid' in str(exception.value)


def test_validate_experiment_name_valid():
    """Tests that validate_experiment_name says that a valid experiment_name is
    valid."""
    run_experiment.validate_experiment_name('experiment-1')


@pytest.mark.parametrize(('experiment_name',), [('a' * 100,), ('abc_',)])
def test_validate_experiment_name_invalid(experiment_name):
    """Tests that validate_experiment_name raises an exception when passed an
    an invalid experiment name."""
    with pytest.raises(run_experiment.ValidationError) as exception:
        run_experiment.validate_experiment_name(experiment_name)
    assert 'is invalid. Must match' in str(exception.value)


# This test takes up to a minute to complete.
@pytest.mark.slow
def test_copy_resources_to_bucket(tmp_path):
    """Tests that copy_resources_to_bucket copies the correct resources."""
    # Do this so that Ctrl-C doesn't pollute the repo.
    cwd = os.getcwd()
    os.chdir(tmp_path)

    config_dir = 'config'
    config = {
        'experiment_filestore': 'gs://gsutil-bucket',
        'experiment': 'experiment',
        'benchmarks': ['libxslt_xpath'],
        'oss_fuzz_corpus': True,
        'custom_seed_corpus_dir': None,
    }
    try:
        with mock.patch('common.filestore_utils.cp') as mocked_filestore_cp:
            with mock.patch(
                    'common.filestore_utils.rsync') as mocked_filestore_rsync:
                with mock.patch('common.gsutil.cp') as mocked_gsutil_cp:
                    run_experiment.copy_resources_to_bucket(config_dir, config)
                    mocked_filestore_cp.assert_called_once_with(
                        'src.tar.gz',
                        'gs://gsutil-bucket/experiment/input/',
                        parallel=True)
                    mocked_filestore_rsync.assert_called_once_with(
                        'config',
                        'gs://gsutil-bucket/experiment/input/config',
                        parallel=True)
                    mocked_gsutil_cp.assert_called_once_with(
                        'gs://libxslt-backup.clusterfuzz-external.appspot.com/'
                        'corpus/libFuzzer/libxslt_xpath/public.zip',
                        'gs://gsutil-bucket/experiment/oss_fuzz_corpora/'
                        'libxslt_xpath.zip',
                        expect_zero=False,
                        parallel=True)
    finally:
        os.chdir(cwd)
