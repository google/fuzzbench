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
"""Helper functions for using the local_filestore."""

import os

from common import new_process
from common import filesystem


def cp(  # pylint: disable=invalid-name
        source,
        destination,
        recursive=False,
        expect_zero=True,
        parallel=False):  # pylint: disable=unused-argument
    """Executes "cp" command from |source| to |destination|."""
    # Create intermediate folders for `cp` command to behave like `gsutil.cp`.
    filesystem.create_directory(os.path.dirname(destination))

    command = ['cp']
    if recursive:
        command.append('-r')
    command.extend([source, destination])
    return new_process.execute(command, expect_zero=expect_zero)


def ls(path, must_exist=True):  # pylint: disable=invalid-name
    """Executes "ls" command for |path|. If |must_exist| is True then it can
    raise subprocess.CalledProcessError."""
    # Add '-1' (i.e., number one) to behave like `gsutil.ls` (i.e., one filename
    # per line).
    command = ['ls', '-1', path]
    process_result = new_process.execute(command, expect_zero=must_exist)
    return process_result


def rm(  # pylint: disable=invalid-name
        path,
        recursive=True,
        force=False,
        parallel=False):  # pylint: disable=unused-argument
    """Executes "rm" command for |path| and returns the result. Uses -r
    if |recursive|. If |force|, then uses -f and will not except if return code
    is nonzero."""
    command = ['rm', path]
    if recursive:
        command.insert(1, '-r')
    if force:
        command.insert(1, '-f')
    return new_process.execute(command, expect_zero=True)


def rsync(  # pylint: disable=too-many-arguments
        source,
        destination,
        delete=True,
        recursive=True,
        gsutil_options=None,  # pylint: disable=unused-argument
        options=None,
        parallel=False):  # pylint: disable=unused-argument
    """Does local_filestore rsync from |source| to |destination| using useful
    defaults that can be overriden."""
    # Add check to behave like `gsutil.rsync`.
    assert os.path.isdir(source), 'filestore_utils.rsync: source should be dir.'

    # Create intermediate folders for `rsync` command to behave like
    # `gsutil.rsync`.
    filesystem.create_directory(destination)

    command = ['rsync']
    if delete:
        command.append('--delete')
    if recursive:
        command.append('-r')
    if options is not None:
        command.extend(options)
    # Add '/' at the end of `source` to behave like `gsutil.rsync`.
    if source[-1] != '/':
        source = source + '/'
    command.extend([source, destination])
    return new_process.execute(command, expect_zero=True)


def cat(file_path, expect_zero=True):
    """Does cat on |file_path| and returns the result."""
    command = ['cat', file_path]
    return new_process.execute(command, expect_zero=expect_zero)
