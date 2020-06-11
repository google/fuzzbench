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
"""Helper functions for using the local_filestore tool."""

import os

from common import new_process


def local_filestore_command(arguments, expect_zero=True):
    """Executes a local command with |arguments| and returns the result."""
    return new_process.execute(arguments, expect_zero=expect_zero)


def cp(  # pylint: disable=invalid-name
        source,
        destination,
        recursive=False,
        parallel=False):  # pylint: disable=unused-argument
    """Executes "cp" command with |cp_arguments|."""
    # Create intermediate folders for `cp` command to behave like `gsutil.cp`.
    for file_or_dir_path in [source, destination]:
        dirpath = os.path.dirname(os.path.abspath(file_or_dir_path))
        if not os.path.exists(dirpath):
            os.makedirs(dirpath)

    command = ['cp']
    if recursive:
        command.append('-r')
    command.extend([source, destination])
    return local_filestore_command(command)


def ls(path, must_exist=True):  # pylint: disable=invalid-name
    """Executes "ls" command for |path|. If |must_exist| is True then it can
    raise subprocess.CalledProcessError."""
    # Add '-l' to behave like `gsutil.ls`.
    command = ['ls', '-l', path]
    process_result = local_filestore_command(command, expect_zero=must_exist)
    return process_result


def rm(  # pylint: disable=invalid-name
        path,
        recursive=True,
        force=False,
        parallel=False):  # pylint: disable=unused-argument
    """Executes "rm" command with |rm_arguments| and returns the result. Uses -r
    if |recursive|. If |force|, then uses -f and will not except if return code
    is nonzero."""
    command = ['rm', path]
    if recursive:
        command.insert(1, '-r')
    if force:
        command.insert(1, '-f')
    return local_filestore_command(command)


def rsync(  # pylint: disable=too-many-arguments
        source,
        destination,
        delete=True,
        recursive=True,
        # TODO: Need to remove from filestore_utils.
        gsutil_options=None,  # pylint: disable=unused-argument
        options=None,
        parallel=False):  # pylint: disable=unused-argument
    """Does local_filestore rsync from |source| to |destination| using sane
    defaults that can be overriden."""
    # Add check to behave like `gsutil.rsync`.
    assert os.path.isdir(source), 'filestore.rsync: source should be a dir'
    command = []
    command.append('rsync')
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
    return local_filestore_command(command)
