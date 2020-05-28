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
"""Tests for local_utils.py."""

from unittest import mock

import pytest

from common import local_utils
from test_libs import utils as test_utils


def test_local_utils_command():
    """Tests local_utils_command works as expected."""
    arguments = ['hello']
    with test_utils.mock_popen_ctx_mgr() as mocked_popen:
        local_utils.local_utils_command(arguments)
    assert mocked_popen.commands == [arguments]


class Testlocal_utilsRsync:
    """Tests for local_utils_command works as expected."""
    SRC = '/src'
    DST = '/dst'

    def test_rsync(self):
        """Tests that rsync works as intended."""
        with mock.patch(
                'common.local_utils.local_utils_command') as mocked_local_utils_command:
            local_utils.rsync(self.SRC, self.DST)
        mocked_local_utils_command.assert_called_with(
            ['rsync', '-d', '-r', '/src', '/dst'])

    def test_local_utils_options(self):
        """Tests that rsync works as intended when supplied a local_utils_options
        argument."""
        flag = '-flag'
        with mock.patch(
                'common.local_utils.local_utils_command') as mocked_local_utils_command:
            local_utils.rsync(self.SRC, self.DST, local_utils_options=[flag])
        assert flag == mocked_local_utils_command.call_args_list[0][0][0][0]

    def test_options(self):
        """Tests that rsync works as intended when supplied a local_utils_options
        argument."""
        flag = '-flag'
        with mock.patch(
                'common.local_utils.local_utils_command') as mocked_local_utils_command:
            local_utils.rsync(self.SRC, self.DST, options=[flag])
        assert flag in mocked_local_utils_command.call_args_list[0][0][0]

    @pytest.mark.parametrize(('kwarg_for_rsync', 'flag'), [('delete', '-d'),
                                                           ('recursive', '-r')])
    def test_no_flag(self, kwarg_for_rsync, flag):
        """Tests that rsync works as intended when caller specifies not
        to use specific flags."""
        kwargs_for_rsync = {}
        kwargs_for_rsync[kwarg_for_rsync] = False
        with mock.patch(
                'common.local_utils.local_utils_command') as mocked_local_utils_command:
            local_utils.rsync(self.SRC, self.DST, **kwargs_for_rsync)
        assert flag not in mocked_local_utils_command.call_args_list[0][0][0]
