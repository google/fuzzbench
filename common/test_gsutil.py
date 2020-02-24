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
"""Tests for gsutil.py."""

from unittest import mock

import pytest

from common import gsutil
from test_libs import utils as test_utils


def test_gsutil_command():
    """Tests gsutil_command works as expected."""
    arguments = ['hello']
    with test_utils.mock_popen_ctx_mgr() as mocked_popen:
        gsutil.gsutil_command(arguments)
    assert mocked_popen.commands == [['gsutil', '-m'] + arguments]


class TestGsutilRsync:
    """Tests for gsutil_command works as expected."""
    SRC = '/src'
    DST = 'gs://dst'

    def test_rsync(self):
        """Tests that rsync works as intended."""
        with mock.patch(
                'common.gsutil.gsutil_command') as mocked_gsutil_command:
            gsutil.rsync(self.SRC, self.DST)
        mocked_gsutil_command.assert_called_with(
            ['rsync', '-d', '-r', '/src', 'gs://dst'])

    def test_gsutil_options(self):
        """Tests that rsync works as intended when supplied a gsutil_options
        argument."""
        flag = '-flag'
        with mock.patch(
                'common.gsutil.gsutil_command') as mocked_gsutil_command:
            gsutil.rsync(self.SRC, self.DST, gsutil_options=[flag])
        assert flag == mocked_gsutil_command.call_args_list[0][0][0][0]

    def test_options(self):
        """Tests that rsync works as intended when supplied a gsutil_options
        argument."""
        flag = '-flag'
        with mock.patch(
                'common.gsutil.gsutil_command') as mocked_gsutil_command:
            gsutil.rsync(self.SRC, self.DST, options=[flag])
        assert flag in mocked_gsutil_command.call_args_list[0][0][0]

    @pytest.mark.parametrize(('kwarg_for_rsync', 'flag'), [('delete', '-d'),
                                                           ('recursive', '-r')])
    def test_no_flag(self, kwarg_for_rsync, flag):
        """Tests that rsync works as intended when caller specifies not
        to use specific flags."""
        kwargs_for_rsync = {}
        kwargs_for_rsync[kwarg_for_rsync] = False
        with mock.patch(
                'common.gsutil.gsutil_command') as mocked_gsutil_command:
            gsutil.rsync(self.SRC, self.DST, **kwargs_for_rsync)
        assert flag not in mocked_gsutil_command.call_args_list[0][0][0]
