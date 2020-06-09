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
"""Tests for local_filestore.py."""

from unittest import mock

import pytest

from common import local_filestore
from test_libs import utils as test_utils


def test_local_filestore_command():
    """Tests local_filestore_command works as expected."""
    arguments = ['hello']
    with test_utils.mock_popen_ctx_mgr() as mocked_popen:
        local_filestore.local_filestore_command(arguments)
    assert mocked_popen.commands == [arguments]


class TestLocalUtilsRsync:
    """Tests for local_filestore_command works as expected."""
    SRC = '/src'
    DST = '/dst'

    @mock.patch('os.path.isdir')
    def test_rsync_file_to_dir(self, mock_isdir):
        """Tests that rsync works as intended."""
        with mock.patch('common.local_filestore.local_filestore_command'
                       ) as mocked_local_filestore_command:
            mock_isdir.return_value = False
            local_filestore.rsync(self.SRC, self.DST)
        mocked_local_filestore_command.assert_called_with(
            ['rsync', '--delete', '-r', '/src', '/dst'])

    @mock.patch('os.path.isdir')
    def test_rsync_dir_to_dir(self, mock_isdir):
        """Tests that rsync works as intended."""
        with mock.patch('common.local_filestore.local_filestore_command'
                       ) as mocked_local_filestore_command:
            mock_isdir.return_value = True
            local_filestore.rsync(self.SRC, self.DST)
        mocked_local_filestore_command.assert_called_with(
            ['rsync', '--delete', '-r', '/src/', '/dst'])

    def test_options(self):
        """Tests that rsync works as intended when supplied a options
        argument."""
        flag = '-flag'
        with mock.patch('common.local_filestore.local_filestore_command'
                       ) as mocked_local_filestore_command:
            local_filestore.rsync(self.SRC, self.DST, options=[flag])
        assert flag in mocked_local_filestore_command.call_args_list[0][0][0]

    @pytest.mark.parametrize(('kwarg_for_rsync', 'flag'),
                             [('delete', '--delete'), ('recursive', '-r')])
    def test_no_flag(self, kwarg_for_rsync, flag):
        """Tests that rsync works as intended when caller specifies not
        to use specific flags."""
        kwargs_for_rsync = {}
        kwargs_for_rsync[kwarg_for_rsync] = False
        with mock.patch('common.local_filestore.local_filestore_command'
                       ) as mocked_local_filestore_command:
            local_filestore.rsync(self.SRC, self.DST, **kwargs_for_rsync)
        test_call_args_list = mocked_local_filestore_command.call_args_list
        assert flag not in test_call_args_list[0][0][0]
