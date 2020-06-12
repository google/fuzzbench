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
from common import new_process

# TODO(zhichengcai): Figure out how we can test filestore_utils when using
# the local_filestore implementation.


class TestLocalFilestore:
    """Tests for switching on local_filestore."""
    FILESTORE = '/experiment_data'
    DIR1 = '/dir1'
    DIR2 = '/dir2'

    def test_local_filestore_on(self, use_local_filestore):  # pylint: disable=unused-argument
        """Tests that local_filestore switches on correctly."""
        with mock.patch('common.new_process.execute') as mocked_execute:
            filestore_utils.cp(self.DIR1, self.DIR2, recursive=True)
            assert 'gsutil' not in mocked_execute.call_args_list[0][0][0]


class TestGsutil():
    """Tests for switching on gsutil."""
    FILESTORE = 'gs://experiment-data'
    LOCAL_DIR = '/dir'
    GSUTIL_DIR = 'gs://fake_dir'

    def test_gsutil_on(self, fs, use_gsutil):  # pylint: disable=invalid-name,unused-argument
        """Tests that gsutil switches on correctly."""

        with mock.patch('common.new_process.execute') as mocked_execute:
            fs.create_dir(self.LOCAL_DIR)
            filestore_utils.cp(self.LOCAL_DIR, self.GSUTIL_DIR, recursive=True)
            mocked_execute.assert_called_with(
                ['gsutil', 'cp', '-r', self.LOCAL_DIR, self.GSUTIL_DIR],
                expect_zero=True)

    def test_keyword_args(self, use_gsutil):  # pylint: disable=unused-argument
        """Tests that keyword args, and in particular 'parallel' are handled
        correctly."""

        with mock.patch('common.new_process.execute') as mocked_execute:
            filestore_utils.rm(self.FILESTORE, recursive=True, parallel=True)
            mocked_execute.assert_called_with(
                ['gsutil', '-m', 'rm', '-r', self.FILESTORE], expect_zero=True)

        with mock.patch('common.new_process.execute') as mocked_execute:
            mocked_execute.return_value = new_process.ProcessResult(0, '', '')
            filestore_utils.ls(self.FILESTORE)
            mocked_execute.assert_called_with(['gsutil', 'ls', self.FILESTORE],
                                              expect_zero=True)

        with mock.patch('common.new_process.execute') as mocked_execute:
            filestore_utils.cp(self.GSUTIL_DIR, self.FILESTORE, parallel=True)
            mocked_execute.assert_called_with(
                ['gsutil', '-m', 'cp', self.GSUTIL_DIR, self.FILESTORE],
                expect_zero=True)

    def test_gsutil_parallel_on(self, fs, use_gsutil):  # pylint: disable=invalid-name,unused-argument
        """Tests that `parallel` is passed to gsutil execution."""
        with mock.patch(
                'common.gsutil.gsutil_command') as mocked_gsutil_command:
            filestore_utils.rsync(self.GSUTIL_DIR,
                                  self.FILESTORE,
                                  parallel=True)
            test_args_list = mocked_gsutil_command.call_args_list
            assert 'parallel' in test_args_list[0][1]
            assert test_args_list[0][1]['parallel'] is True
