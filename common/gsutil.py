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
"""Helper functions for using the gsutil tool."""

from common import new_process


def gsutil_command(arguments, expect_zero=True, parallel=False):
    """Executes a gsutil command with |arguments| and returns the result. If
    |parallel| is True then "-m" is added to the gsutil command so that gsutil
    can use multiple processes to complete the command. If |expect_zero| is True
    and the command fails then this function will raise a
    subprocess.CalledError."""
    command = ['gsutil']
    if parallel:
        command.append('-m')
    return new_process.execute(command + arguments, expect_zero=expect_zero)


def cp(source, destination, recursive=False, expect_zero=True, parallel=False):  # pylint: disable=invalid-name
    """Executes gsutil's "cp" command to copy |source| to |destination|. Uses -r
    if |recursive|. If |expect_zero| is True and the command fails then this
    function will raise a subprocess.CalledError."""
    command = ['cp']
    if recursive:
        command.append('-r')
    command.extend([source, destination])

    return gsutil_command(command, expect_zero=expect_zero, parallel=parallel)


def ls(path, must_exist=True):  # pylint: disable=invalid-name
    """Executes gsutil's "ls" command on |path|. If |must_exist| is True and the
    command fails then this function will raise a subprocess.CalledError."""
    command = ['ls', path]
    process_result = gsutil_command(command, expect_zero=must_exist)
    return process_result


def rm(path, recursive=True, force=False, parallel=False):  # pylint: disable=invalid-name
    """Executes gsutil's rm command on |path| and returns the result.
    Uses -r if |recursive|. If |force|, then uses -f and will not except if
    return code is nonzero."""
    command = ['rm', path]
    if recursive:
        command.insert(1, '-r')
    if force:
        command.insert(1, '-f')

    # Set expect_zero=False because "gsutil rm -f" returns nonzero on failure
    # unlike the local version of rm.
    return gsutil_command(command, expect_zero=(not force), parallel=parallel)


def rsync(  # pylint: disable=too-many-arguments
        source,
        destination,
        delete=True,
        recursive=True,
        gsutil_options=None,
        options=None,
        parallel=False):
    """Does gsutil rsync from |source| to |destination| using useful defaults
    that can be overriden. Prepends any |gsutil_options| before the rsync
    subcommand if provided."""
    command = [] if gsutil_options is None else gsutil_options
    command.append('rsync')
    if delete:
        command.append('-d')
    if recursive:
        command.append('-r')
    if options is not None:
        command.extend(options)
    command.extend([source, destination])
    return gsutil_command(command, parallel=parallel)


def cat(file_path, expect_zero=True):
    """Does gsutil cat on |file_path| and returns the result."""
    command = ['cat', file_path]
    # TODO(metzman): Consider replacing this technique with cp to temp file
    # and a local `cat`. The problem with this technique is stderr output
    # from gsutil can be included.
    return gsutil_command(command, expect_zero=expect_zero)
