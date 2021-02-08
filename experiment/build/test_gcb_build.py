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
"""Tests for builder.py."""

import subprocess
from unittest import mock

import pytest

from common import new_process
from experiment.build import gcb_build

# pylint: disable=protected-access

FAIL_RESULT = new_process.ProcessResult(1, '', False)


@mock.patch('common.new_process.execute', return_value=FAIL_RESULT)
@mock.patch('experiment.build.build_utils.store_build_logs')
def test_build_error(mocked_store_build_logs, _):
    """Tests that on error, _build raises subprocess.CalledProcessError and
    calls store_build_logs."""
    config_name = 'config'
    with pytest.raises(subprocess.CalledProcessError):
        gcb_build._build({}, config_name)
    mocked_store_build_logs.assert_called_with(config_name, FAIL_RESULT)


SUCCESS_RESULT = new_process.ProcessResult(0, '', False)


@mock.patch('common.new_process.execute', return_value=SUCCESS_RESULT)
@mock.patch('experiment.build.build_utils.store_build_logs')
def test_build_success_store_logs(mocked_store_build_logs, _):
    """Tests that on success _buiild stores build logs."""
    config_name = 'config'
    gcb_build._build({}, config_name)
    mocked_store_build_logs.assert_called_with(config_name, SUCCESS_RESULT)
