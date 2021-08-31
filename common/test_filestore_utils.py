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
"""Tests for filestore_utils.py."""

from unittest import mock

import pytest

from common import filestore_utils
from common import new_process

LOCAL_DIR = '/dir'
LOCAL_DIR_2 = '/dir2'
GCS_DIR = 'gs://fake_dir'
GCS_DIR_2 = 'gs://fake_dir_2'


def test_using_local_filestore(fs, use_local_filestore):  # pylint: disable=invalid-name,unused-argument
    """Tests that local_filestore is used in local running settings."""
    fs.create_dir(LOCAL_DIR)
    fs.create_dir(LOCAL_DIR_2)

    with mock.patch('common.new_process.execute') as mocked_execute:
        filestore_utils.cp(LOCAL_DIR, LOCAL_DIR_2, recursive=True)
        assert 'gsutil' not in mocked_execute.call_args_list[0][0][0]

    with mock.patch('common.new_process.execute') as mocked_execute:
        filestore_utils.ls(LOCAL_DIR)
        assert 'gsutil' not in mocked_execute.call_args_list[0][0][0]

    with mock.patch('common.new_process.execute') as mocked_execute:
        filestore_utils.rm(LOCAL_DIR, recursive=True)
        assert 'gsutil' not in mocked_execute.call_args_list[0][0][0]

    with mock.patch('common.new_process.execute') as mocked_execute:
        filestore_utils.rsync(LOCAL_DIR, LOCAL_DIR_2, recursive=True)
        assert 'gsutil' not in mocked_execute.call_args_list[0][0][0]


def test_parallel_take_no_effects_locally(fs, use_local_filestore):  # pylint: disable=invalid-name,unused-argument
    """Tests that `parallel` argument takes no effect for local running no
    matter True or False."""
    fs.create_dir(LOCAL_DIR)
    fs.create_dir(LOCAL_DIR_2)

    with mock.patch('common.new_process.execute') as mocked_execute:
        filestore_utils.rsync(LOCAL_DIR, LOCAL_DIR_2, parallel=True)
        filestore_utils.rsync(LOCAL_DIR, LOCAL_DIR_2, parallel=False)
        call_args_list = mocked_execute.call_args_list
        assert call_args_list[0] == call_args_list[1]

    with mock.patch('common.new_process.execute') as mocked_execute:
        filestore_utils.cp(LOCAL_DIR,
                           LOCAL_DIR_2,
                           recursive=True,
                           parallel=True)
        filestore_utils.cp(LOCAL_DIR,
                           LOCAL_DIR_2,
                           recursive=True,
                           parallel=False)
        call_args_list = mocked_execute.call_args_list
        assert call_args_list[0] == call_args_list[1]

    with mock.patch('common.new_process.execute') as mocked_execute:
        filestore_utils.rm(LOCAL_DIR, recursive=True, parallel=True)
        filestore_utils.rm(LOCAL_DIR, recursive=True, parallel=False)
        call_args_list = mocked_execute.call_args_list
        assert call_args_list[0] == call_args_list[1]


def test_using_gsutil(use_gsutil):  # pylint: disable=unused-argument
    """Tests that gsutil is used in Google Cloud running settings."""

    with mock.patch('common.new_process.execute') as mocked_execute:
        filestore_utils.cp(GCS_DIR, GCS_DIR_2, recursive=True)
        assert 'gsutil' in mocked_execute.call_args_list[0][0][0]

    with mock.patch('common.new_process.execute') as mocked_execute:
        filestore_utils.ls(GCS_DIR)
        assert 'gsutil' in mocked_execute.call_args_list[0][0][0]

    with mock.patch('common.new_process.execute') as mocked_execute:
        filestore_utils.rm(GCS_DIR, recursive=True)
        assert 'gsutil' in mocked_execute.call_args_list[0][0][0]

    with mock.patch('common.new_process.execute') as mocked_execute:
        filestore_utils.rsync(GCS_DIR, GCS_DIR_2, recursive=True)
        assert 'gsutil' in mocked_execute.call_args_list[0][0][0]


def test_keyword_args(use_gsutil):  # pylint: disable=unused-argument
    """Tests that keyword args, and in particular 'parallel' are handled
    correctly."""

    with mock.patch('common.new_process.execute') as mocked_execute:
        filestore_utils.rm(GCS_DIR_2, recursive=True, parallel=True)
        mocked_execute.assert_called_with(
            ['gsutil', '-m', 'rm', '-r', GCS_DIR_2], expect_zero=True)

    with mock.patch('common.new_process.execute') as mocked_execute:
        mocked_execute.return_value = new_process.ProcessResult(0, '', '')
        filestore_utils.ls(GCS_DIR_2)
        mocked_execute.assert_called_with(['gsutil', 'ls', GCS_DIR_2],
                                          expect_zero=True)

    with mock.patch('common.new_process.execute') as mocked_execute:
        filestore_utils.cp(GCS_DIR, GCS_DIR_2, parallel=True)
        mocked_execute.assert_called_with(
            ['gsutil', '-m', 'cp', GCS_DIR, GCS_DIR_2], expect_zero=True)


def test_gsutil_parallel_on(fs, use_gsutil):  # pylint: disable=invalid-name,unused-argument
    """Tests that `parallel` is passed to gsutil execution."""
    with mock.patch('common.gsutil.gsutil_command') as mocked_gsutil_command:
        filestore_utils.rsync(GCS_DIR, GCS_DIR_2, parallel=True)
        test_args_list = mocked_gsutil_command.call_args_list
        assert 'parallel' in test_args_list[0][1]
        assert test_args_list[0][1]['parallel'] is True


@pytest.mark.parametrize(('filestore_path', 'expected_result'),
                         [('gs://filestore', True), ('/filestore', False),
                          ('C:\\Windows\\filestore', False)])
def test_is_gcs_filestore_path(filestore_path, expected_result):
    """Tests that is_gcs_filestore_path returns the correct result for different
    filestore paths."""
    assert (filestore_utils.is_gcs_filestore_path(filestore_path) ==
            expected_result)


@pytest.mark.parametrize(
    ('filestore_path', 'expected_result'),
    [('gs://filestore', 'https://storage.googleapis.com/filestore'),
     ('/filestore', '/filestore'),
     ('C:\\Windows\\filestore', 'C:\\Windows\\filestore')])
def test_get_user_accessible_path(filestore_path, expected_result):
    """Tests that get_user_accessible_path returns the correct result for
    different filestore paths."""
    assert filestore_utils.get_user_facing_path(
        filestore_path) == expected_result
