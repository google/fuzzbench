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

import os
import subprocess
from unittest import mock

import pytest

from common import local_filestore


def test_rm(tmp_path):
    """Tests rm works as expected."""
    file_path = tmp_path / 'file'
    data = 'hello'
    with open(file_path, 'w') as file_handle:
        file_handle.write(data)
    local_filestore.rm(str(file_path))
    assert not os.path.exists(file_path)


def test_ls(tmp_path):
    """Tests ls will raise an exception while |must_exist| is
    True if the file doesn't exist ."""
    file_path = tmp_path / 'non_exist_file'
    with pytest.raises(subprocess.CalledProcessError):
        local_filestore.ls(str(file_path))


def test_ls_non_must_exist(tmp_path):
    """Tests ls won't raise an exception while |must_exist| is
    False if the file doesn't exist ."""
    file_path = tmp_path / 'non_exist_file'
    local_filestore.ls(str(file_path), must_exist=False)


def test_ls_one_file_per_line(tmp_path):
    """Tests ls will list files as one per line."""
    dir_path = tmp_path
    file1 = dir_path / 'file1'
    file2 = dir_path / 'file2'
    with open(file1, 'w+'):
        pass
    with open(file2, 'w+'):
        pass
    assert local_filestore.ls(str(dir_path)).output == 'file1\nfile2\n'


def test_cp(tmp_path):
    """Tests cp works as expected."""
    source = tmp_path / 'source'
    data = 'hello'
    with open(source, 'w') as file_handle:
        file_handle.write(data)
    destination = tmp_path / 'destination'
    local_filestore.cp(str(source), str(destination))
    with open(destination) as file_handle:
        assert file_handle.read() == data


def test_cp_nonexistent_dest(tmp_path):
    """Tests cp will create intermediate folders for destination."""
    source_dir = tmp_path / 'source'
    source_dir.mkdir()
    source_file = source_dir / 'file1'
    cp_dest_dir = tmp_path / 'cp_test' / 'intermediate' / 'cp_dest'
    with open(source_file, 'w'):
        pass

    # Should run without exceptions.
    local_filestore.cp(str(source_dir), str(cp_dest_dir), recursive=True)


def test_rsync_nonexistent_dest(tmp_path):
    """Tests cp will create intermediate folders for destination."""
    source_dir = tmp_path / 'source'
    source_dir.mkdir()
    source_file = source_dir / 'file1'
    rsync_dest_dir = tmp_path / 'rsync_test' / 'intermediate' / 'rsync_dest'
    with open(source_file, 'w'):
        pass

    # Should run without exceptions.
    local_filestore.rsync(str(source_dir), str(rsync_dest_dir))


SRC = '/src'
DST = '/dst'


def test_rsync_dir_to_dir(fs):  # pylint: disable=invalid-name
    """Tests that rsync works as intended."""
    fs.create_dir(SRC)
    fs.create_dir(DST)
    with mock.patch('common.new_process.execute') as mocked_execute:
        local_filestore.rsync(SRC, DST)
    mocked_execute.assert_called_with(
        ['rsync', '--delete', '-r', '/src/', '/dst'], expect_zero=True)


def test_rsync_options(fs):  # pylint: disable=invalid-name
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
def test_rsync_no_flag(kwarg_for_rsync, flag, fs):  # pylint: disable=invalid-name
    """Tests that rsync works as intended when caller specifies not
    to use specific flags."""
    fs.create_dir(SRC)
    fs.create_dir(DST)
    kwargs_for_rsync = {}
    kwargs_for_rsync[kwarg_for_rsync] = False
    with mock.patch('common.new_process.execute') as mocked_execute:
        local_filestore.rsync(SRC, DST, **kwargs_for_rsync)
    assert flag not in mocked_execute.call_args_list[0][0][0]
