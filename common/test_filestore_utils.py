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


class TestLocalFileStoreOn:
    """Tests for switching on local_filestore."""
    FILESTORE = '/fake_filestore'
    DIR1 = '/dir1'
    DIR2 = '/dir2'

    def _switch_on_local_filestore(self, fs, environ):  #pylint: disable=invalid-name
        # Create local filestore usage environment.
        fs.create_dir(self.FILESTORE)
        fs.create_dir(self.DIR1)
        fs.create_dir(self.DIR2)
        environ['EXPERIMENT_FILESTORE'] = self.FILESTORE

    @pytest.fixture
    def test_local_filestore_on(self, fs, environ):  #pylint: disable=invalid-name
        """Tests that local_filestore switches on correctly."""
        self._switch_on_local_filestore(fs, environ)

        with mock.patch('common.new_process.execute') as mocked_execute:
            filestore_utils.cp(self.DIR1, self.DIR2, recursive=True)
            mocked_execute.assert_called_with(
                ['cp', '-r', self.DIR1, self.DIR2], expect_zero=True)


class TestGsutilOn():
    """Tests for switching on gsutil."""
    FILESTORE = 'gs://fake_filestore'
    LOCAL_DIR = '/dir'
    GSUTIL_DIR = 'gs://fake_dir'

    def _switch_on_gsutil(self, environ):  #pylint: disable=invalid-name
        # Create gsutil usage environment.
        environ['EXPERIMENT_FILESTORE'] = self.FILESTORE

    @pytest.fixture
    def test_gsutil_on(self, fs, environ):  #pylint: disable=invalid-name
        """Tests that gsutil switches on correctly."""
        self._switch_on_gsutil(environ)

        with mock.patch('common.new_process.execute') as mocked_execute:
            fs.create_dir(self.LOCAL_DIR)
            filestore_utils.cp(self.LOCAL_DIR, self.GSUTIL_DIR, recursive=True)
            mocked_execute.assert_called_with(
                ['gsutil', 'cp', '-r', self.LOCAL_DIR, self.GSUTIL_DIR],
                expect_zero=True)

    @pytest.fixture
    def test_keyword_args(self, environ):
        """Tests that keyword args, and in particular 'parallel' are handled
        correctly."""
        self._switch_on_gsutil(environ)

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
