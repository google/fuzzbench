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
"""Tests for reporter.py."""

import os

from unittest import mock
import pytest

from common import yaml_utils
from experiment import reporter
from test_libs import utils as test_utils

# pylint: disable=unused-argument,invalid-name


def _setup_experiment_files(fs):
    """Set up experiment config and core-fuzzers files and return experiment
    config yaml."""
    fs.add_real_file(reporter.CORE_FUZZERS_YAML)

    config_filepath = os.path.join(os.path.dirname(__file__), 'test_data',
                                   'experiment-config.yaml')
    fs.add_real_file(config_filepath)
    experiment_config = yaml_utils.read(config_filepath)

    return experiment_config


@pytest.mark.parametrize(
    ('experiment_fuzzers', 'expected_merged_fuzzers', 'expected_report_url'),
    [  # Tests the following usecases:
        # If fuzzer variants are provided, then we merge them with the core
        # fuzzers and put them in the |experimental| sub-directory.
        (['fuzzer-a', 'fuzzer-b'
         ], set(['fuzzer-a', 'fuzzer-b'] + reporter.get_core_fuzzers()),
         'gs://web-reports/experimental/test-experiment'),
        # If we provide the core fuzzers (e.g. in an official experiment),
        # then they show up in the root reports directory.
        (reporter.get_core_fuzzers(), set(
            reporter.get_core_fuzzers()), 'gs://web-reports/test-experiment'),
        # If we provide a subset of the core fuzzers, then they are merged with
        # the other core fuzzers from older experiments and still show up in
        # the root reports directory.
        (reporter.get_core_fuzzers()[:2], set(
            reporter.get_core_fuzzers()), 'gs://web-reports/test-experiment')
    ])
def test_output_report_filestore(experiment_fuzzers, expected_merged_fuzzers,
                                 expected_report_url, fs, experiment):
    """Test that output_report writes the report and rsyncs it to the report
    filestore."""
    experiment_config = _setup_experiment_files(fs)
    experiment_config['fuzzers'] = experiment_fuzzers

    with test_utils.mock_popen_ctx_mgr() as mocked_popen:
        with mock.patch('analysis.generate_report.generate_report'
                       ) as mocked_generate_report:
            reporter.output_report(experiment_config)
            reports_dir = os.path.join(os.environ['WORK'], 'reports')
            assert mocked_popen.commands == [[
                'gsutil', '-h', 'Cache-Control:public,max-age=0,no-transform',
                'rsync', '-r', reports_dir, expected_report_url
            ]]
            experiment_name = os.environ['EXPERIMENT']
            mocked_generate_report.assert_called_with(
                [experiment_name],
                reports_dir,
                report_name=experiment_name,
                fuzzers=expected_merged_fuzzers,
                in_progress=False,
                merge_with_clobber_nonprivate=False,
                coverage_report=False)
