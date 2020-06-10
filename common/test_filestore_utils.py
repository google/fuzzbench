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

# TODO(zhichengcai): Figure out how we can test filestore_utils when using
# the local_filestore implementation.


@pytest.fixture
def test_local_filestore(fs, environ):  #pylint: disable=invalid-name
    """Tests that keyword args, and in particular 'parallel' are handled
    correctly."""
    # Create cloud filestore usage environment.
    filestore_path = '/fake_dir'
    fs.create_dir(filestore_path)
    fs.create_dir('/dir1')
    fs.create_dir('/dir2')
    environ['EXPERIMENT_FILESTORE'] = filestore_path
    with mock.patch('common.new_process.execute') as mocked_execute:
        filestore_utils.cp('/dir1', '/dir2', recursive=True)
        mocked_execute.assert_called_with(['cp', '-r', '/dir1', '/dir2'],
                                          expect_zero=True)


@pytest.fixture
def test_keyword_args(environ):
    """Tests that keyword args, and in particular 'parallel' are handled
    correctly."""
    # Create cloud filestore usage environment.
    filestore_path = 'gs://fake_dir'
    environ['EXPERIMENT_FILESTORE'] = filestore_path

    with mock.patch('common.new_process.execute') as mocked_execute:
        filestore_utils.rm(filestore_path, recursive=True, parallel=True)
        mocked_execute.assert_called_with(
            ['gsutil', '-m', 'rm', '-r', filestore_path], expect_zero=True)

    with mock.patch('common.new_process.execute') as mocked_execute:
        mocked_execute.return_value = new_process.ProcessResult(0, '', '')
        filestore_utils.ls(filestore_path)
        mocked_execute.assert_called_with(['gsutil', 'ls', filestore_path],
                                          expect_zero=True)

    filestore_path2 = filestore_path + '2'

    with mock.patch('common.new_process.execute') as mocked_execute:
        filestore_utils.cp(filestore_path, filestore_path2, parallel=True)
        mocked_execute.assert_called_with(
            ['gsutil', '-m', 'cp', filestore_path, filestore_path2],
            expect_zero=True)
