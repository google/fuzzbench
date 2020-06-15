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
"""Tests for new_process.py"""
import os
import time
from unittest import mock

from common import new_process

TEST_DATA_PATH = os.path.join(os.path.dirname(__file__), 'test_data')

# pylint: disable=protected-access,invalid-name,unused-argument


def test_end_process():
    """Tests that _end_process terminates the process and then tries to wait
    before killing it."""
    mock_popen = mock.Mock()
    mock_popen.pid = 1
    mock_popen.poll.return_value = None
    mock_popen.terminate.return_value = None
    mock_popen.kill.return_value = None
    new_process._end_process(new_process.WrappedPopen(mock_popen), False)
    mock_popen.kill.assert_called()


class TestIntegrationExecute:
    """Integration tests for execute."""

    COMMAND = ['python3', os.path.join(TEST_DATA_PATH, 'printer.py')]

    def test_timeout(self):
        """Test that the timeout parameter works as intended."""
        start_time = time.time()
        result = new_process.execute(self.COMMAND, timeout=.1)
        end_time = time.time()
        assert end_time - start_time < 5
        # Give it a lot of slack to account for differences on people's macines.
        assert result.retcode != 0

    @mock.patch('common.logs.info')
    def test_output_file(self, mocked_info, tmp_path):
        """Test that execute handles the output_file argument as intended."""
        output_file_path = tmp_path / 'output'
        with open(output_file_path, 'w') as output_file:
            new_process.execute(self.COMMAND,
                                timeout=1,
                                output_file=output_file,
                                expect_zero=False)

        with open(output_file_path, 'r') as output_file:
            assert output_file.read() == 'Hello, World!\n'
