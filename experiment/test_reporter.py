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

from experiment import reporter
from test_libs import utils as test_utils

# pylint: disable=unused-argument,invalid-name


def test_output_report_bucket(fs, experiment):
    """Test that output_report writes the report and rsyncs it to the web
    bucket."""
    web_bucket = 'gs://web-bucket/experiment'
    with test_utils.mock_popen_ctx_mgr() as mocked_popen:
        with mock.patch('analysis.generate_report.generate_report'
                       ) as mocked_generate_report:
            reporter.output_report(web_bucket)
            reports_dir = os.path.join(os.environ['WORK'], 'reports')
            assert mocked_popen.commands == [[
                'gsutil', '-h', 'Cache-Control:public,max-age=0,no-transform',
                'rsync', '-P', '-d', '-r', reports_dir,
                'gs://web-bucket/experiment'
            ]]
            mocked_generate_report.assert_called_with(
                [os.environ['EXPERIMENT']], reports_dir, in_progress=False)
