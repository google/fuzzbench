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

import yaml

from experiment import reporter
from test_libs import utils as test_utils

# pylint: disable=unused-argument,invalid-name


def test_output_report_filestore(fs, experiment):
    """Test that output_report writes the report and rsyncs it to the report
    filestore."""
    config_filepath = os.path.join(os.path.dirname(__file__), '..', 'service',
                                   'core-fuzzers.yaml')
    fs.add_real_file(config_filepath)

    # Get the config.
    config_filepath = os.path.join(os.path.dirname(__file__), 'test_data',
                                   'experiment-config.yaml')
    fs.add_real_file(config_filepath)

    with open(config_filepath) as file_handle:
        experiment_config = yaml.load(file_handle, yaml.SafeLoader)

    with test_utils.mock_popen_ctx_mgr() as mocked_popen:
        with mock.patch('analysis.generate_report.generate_report'
                       ) as mocked_generate_report:
            reporter.output_report(experiment_config)
            reports_dir = os.path.join(os.environ['WORK'], 'reports')
            assert mocked_popen.commands == [[
                'gsutil', '-h', 'Cache-Control:public,max-age=0,no-transform',
                'rsync', '-d', '-r', reports_dir,
                'gs://web-reports/test-experiment'
            ]]
            experiment_name = os.environ['EXPERIMENT']
            mocked_generate_report.assert_called_with(
                [experiment_name],
                reports_dir,
                report_name=experiment_name,
                fuzzers=[
                    'afl', 'afl_qemu', 'aflfast', 'aflplusplus',
                    'aflplusplus_optimal', 'aflplusplus_qemu', 'aflsmart',
                    'eclipser', 'entropic', 'fairfuzz', 'fuzzer-a', 'fuzzer-b',
                    'honggfuzz', 'honggfuzz_qemu', 'lafintel', 'libfuzzer',
                    'manul', 'mopt'
                ],
                in_progress=False,
                merge_with_clobber_nonprivate=False,
                coverage_report=False)
