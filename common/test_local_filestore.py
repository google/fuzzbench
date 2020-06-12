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

import subprocess
import pytest

from common import local_filestore


def test_local_filestore_rm(tmp_path):
    """Tests local_filestore.rm works as expected."""
    file_path = str(tmp_path) + '/file'
    data = 'hello'
    with open(file_path, 'w') as file_handle:
        file_handle.write(data)
    local_filestore.rm(file_path)
    with pytest.raises(FileNotFoundError):
        assert open(file_path)


def test_local_filestore_ls(tmp_path):
    """Tests local_filestore.ls |must_exist| take effects."""
    file_path = str(tmp_path) + '/non_exist_file'
    with pytest.raises(subprocess.CalledProcessError):
        assert local_filestore.ls(file_path)


def test_local_filestore_cp(tmp_path):
    """Tests local_filestore.cp works as expected."""
    source = str(tmp_path) + '/source'
    data = 'hello'
    with open(source, 'w') as file_handle:
        file_handle.write(data)
    destination = str(tmp_path) + '/destination'
    local_filestore.cp(source, destination)
    with open(destination) as file_handle:
        assert file_handle.read() == data


SRC = '/src'
DST = '/dst'


def test_rsync_dir_to_dir(fs):  #pylint: disable=invalid-name
    """Tests that rsync works as intended."""
    fs.create_dir(SRC)
    fs.create_dir(DST)
    with mock.patch('common.new_process.execute') as mocked_execute:
        local_filestore.rsync(SRC, DST)
    mocked_execute.assert_called_with(
        ['rsync', '--delete', '-r', '/src/', '/dst'], expect_zero=True)


def test_rsync_options(fs):  #pylint: disable=invalid-name
    """Tests that rsync works as intended when supplied a options
    argument."""
    fs.create_dir(SRC)
    fs.create_dir(DST)
    flag = '-flag'
    with mock.patch('common.new_process.execute') as mocked_execute:
        local_filestore.rsync(SRC, DST, options=[flag])
    assert flag in mocked_execute.call_args_list[0][0][0]


@pytest.mark.parametrize(('kwarg_for_rsync', 'flag'), [('delete', '--delete'),
                                                       ('recursive', '-r')])
def test_rsync_no_flag(kwarg_for_rsync, flag, fs):  #pylint: disable=invalid-name
    """Tests that rsync works as intended when caller specifies not
    to use specific flags."""
    fs.create_dir(SRC)
    fs.create_dir(DST)
    kwargs_for_rsync = {}
    kwargs_for_rsync[kwarg_for_rsync] = False
    with mock.patch('common.new_process.execute') as mocked_execute:
        local_filestore.rsync(SRC, DST, **kwargs_for_rsync)
    assert flag not in mocked_execute.call_args_list[0][0][0]
