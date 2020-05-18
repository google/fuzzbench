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

from common import fuzzer_utils
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
    with pytest.raises(Exception):
        run_experiment.validate_benchmarks('fake_benchmark')
    with pytest.raises(Exception):
        run_experiment.validate_benchmarks('common.sh')


class TestReadAndValdiateExperimentConfig(unittest.TestCase):
    """Tests for read_and_validate_experiment_config."""

    def setUp(self):
        self.config_filename = 'config'
        self.config = {
            'cloud_experiment_bucket': 'gs://bucket',
            'cloud_web_bucket': 'gs://web-bucket',
            'experiment': 'experiment-name',
            'cloud_compute_zone': 'us-central1-a',
            'trials': 10,
            'max_total_time': 1000,
        }

    @mock.patch('common.logs.error')
    def test_missing_required(self, mocked_error):
        """Tests that an error is logged when the config file is missing a
        required config parameter."""
        # All but cloud_compute_zone.
        del self.config['cloud_compute_zone']
        with mock.patch('common.yaml_utils.read') as mocked_read_yaml:
            mocked_read_yaml.side_effect = lambda config_filename: self.config
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
            'cloud_experiment_bucket', 'gs://EXPERIMENT',
            'Config parameter "%s" is "%s". It must be a lowercase string.')

    def test_invalid_string(self):
        """Tests that an error is logged when the config file has a config
        parameter that should be a string but is not."""
        self._test_invalid(
            'cloud_experiment_bucket', 1,
            'Config parameter "%s" is "%s". It must be a lowercase string.')

    def test_invalid_bucket(self):
        """Tests that an error is logged when the config file has a config
        parameter that should be a GCS bucket but is not."""
        self._test_invalid(
            'cloud_experiment_bucket', 'invalid',
            'Config parameter "%s" is "%s". It must start with gs://.')

    @mock.patch('common.logs.error')
    def test_multiple_invalid(self, mocked_error):
        """Test that multiple errors are logged when multiple parameters are
        invalid."""
        self.config['cloud_experiment_bucket'] = 1
        self.config['cloud_web_bucket'] = None
        with mock.patch('common.yaml_utils.read') as mocked_read_yaml:
            mocked_read_yaml.side_effect = lambda config_filename: self.config
            with pytest.raises(run_experiment.ValidationError):
                run_experiment.read_and_validate_experiment_config(
                    'config_file')
        mocked_error.assert_any_call(
            'Config parameter "%s" is "%s". It must be a lowercase string.',
            'cloud_experiment_bucket',
            str(self.config['cloud_experiment_bucket']))
        mocked_error.assert_any_call(
            'Config parameter "%s" is "%s". It must be a lowercase string.',
            'cloud_web_bucket', str(self.config['cloud_web_bucket']))

    @mock.patch('common.logs.error')
    def _test_invalid(self, param, value, expected_log_message, mocked_error):
        """Tests that |expected_log_message| is logged as an error when config
        |param| is |value| which is invalid."""
        # Don't parameterize this function, it would be too messsy.
        self.config[param] = value
        with mock.patch('common.yaml_utils.read') as mocked_read_yaml:
            mocked_read_yaml.side_effect = lambda config_filename: self.config
            with pytest.raises(run_experiment.ValidationError):
                run_experiment.read_and_validate_experiment_config(
                    'config_file')
        mocked_error.assert_called_with(expected_log_message, param, str(value))

    @mock.patch('common.logs.error')
    def test_read_and_validate_experiment_config(self, _):
        """Tests that read_and_validat_experiment_config works as intended when
        config is valid."""
        with mock.patch('common.yaml_utils.read') as mocked_read_yaml:
            mocked_read_yaml.side_effect = lambda config_filename: self.config
            assert (self.config == run_experiment.
                    read_and_validate_experiment_config('config_file'))


def test_validate_fuzzer_config():
    """Tests that validate_fuzzer_config says that a valid fuzzer config name is
    valid and that an invalid one is not."""
    config = {'fuzzer': 'afl', 'name': 'name', 'fuzzer_environment': []}
    run_experiment.validate_fuzzer_config(config)

    with pytest.raises(Exception) as exception:
        config['fuzzer'] = 'afl:'
        run_experiment.validate_fuzzer_config(config)
    assert 'may only contain' in str(exception.value)

    with pytest.raises(Exception) as exception:
        config['fuzzer'] = 'not_exist'
        run_experiment.validate_fuzzer_config(config)
    assert 'does not exist' in str(exception.value)
    config['fuzzer'] = 'afl'

    with pytest.raises(Exception) as exception:
        config['invalid_key'] = 'invalid'
        run_experiment.validate_fuzzer_config(config)
    assert 'Invalid entry' in str(exception.value)
    del config['invalid_key']

    with pytest.raises(Exception) as exception:
        config['fuzzer_environment'] = {'a': 'b'}
        run_experiment.validate_fuzzer_config(config)
    assert 'must be a list' in str(exception.value)


def test_variant_configs_valid():
    """Ensure that all variant configs (variants.yaml files) are valid."""
    fuzzer_configs = fuzzer_utils.get_fuzzer_configs()
    for config in fuzzer_configs:
        run_experiment.validate_fuzzer_config(config)


def test_validate_fuzzer():
    """Tests that validate_fuzzer says that a valid fuzzer name is valid and
    that an invalid one is not."""
    run_experiment.validate_fuzzer('afl')

    with pytest.raises(Exception) as exception:
        run_experiment.validate_fuzzer('afl:')
    assert 'may only contain' in str(exception.value)

    with pytest.raises(Exception) as exception:
        run_experiment.validate_fuzzer('not_exist')
    assert 'does not exist' in str(exception.value)


def test_validate_experiment_name_valid():
    """Tests that validate_experiment_name says that a valid experiment_name is
    valid."""
    run_experiment.validate_experiment_name('experiment-1')


@pytest.mark.parametrize(('experiment_name',), [('a' * 100,), ('abc_',)])
def test_validate_experiment_name_invalid(experiment_name):
    """Tests that validate_fuzzer_config raises an exception when passed passed
    |experiment_name|, an invalid experiment name."""
    with pytest.raises(Exception) as exception:
        run_experiment.validate_experiment_name(experiment_name)
    assert 'is invalid. Must match' in str(exception.value)


def test_copy_resources_to_bucket():
    """Tests that copy_resources_to_bucket copies the correct resources."""
    config_dir = 'config'
    config = {
        'cloud_experiment_bucket': 'gs://gsutil-bucket',
        'experiment': 'experiment'
    }
    with mock.patch('common.gsutil.rsync') as mocked_rsync:
        with mock.patch('common.gsutil.cp') as mocked_cp:
            run_experiment.copy_resources_to_bucket(config_dir, config)
            mocked_cp.assert_called_once_with(
                'src.tar.gz',
                'gs://gsutil-bucket/experiment/input/',
                parallel=True)
            mocked_rsync.assert_called_once_with(
                'config',
                'gs://gsutil-bucket/experiment/input/config',
                parallel=True)
