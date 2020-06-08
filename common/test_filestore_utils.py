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

from common import filestore_utils

# TODO(zhichengcai): Figure out how we can test filestore_utils when using
# the local_filestore implementation.


def test_keyword_args():
    """Tests that keyword args, and in particular 'parallel' are handled
    correctly."""
    filestore_path = 'gs://fake_dir'

    with mock.patch('common.new_process.execute') as mocked_execute:
        filestore_utils.rm(filestore_path, recursive=True, parallel=True)
        mocked_execute.assert_called_with(
            ['gsutil', '-m', 'rm', '-r', filestore_path], expect_zero=True)

    with mock.patch('common.new_process.execute') as mocked_execute:
        filestore_utils.ls(filestore_path, must_exist=False)
        mocked_execute.assert_called_with(
            ['gsutil', 'ls', filestore_path], expect_zero=False)

    filestore_path2 = filestore_path + '2'

    with mock.patch('common.new_process.execute') as mocked_execute:
        filestore_utils.cp(filestore_path, filestore_path2, parallel=True)
        mocked_execute.assert_called_with(
            ['gsutil', '-m', 'cp', filestore_path, filestore_path2 ])

    with mock.patch('common.new_process.execute') as mocked_execute:
        filestore_utils.cp(filestore_path,  filestore_path2, write_to_stdout=False)
        mocked_execute.assert_called_with(
            ['gsutil', 'cp', filestore_path, filestore_path2],
            write_to_stdout=False)
