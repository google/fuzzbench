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

from common import logs
from common import new_process

logger = logs.Logger('gsutil')


def gsutil_command(arguments, parallel=False, **kwargs):
    """Executes a gsutil command with |arguments| and returns the result."""
    command = ['gsutil']
    if parallel:
        command.append('-m')
    return new_process.execute(command + arguments, **kwargs)


def cp(*cp_arguments, parallel=False, expect_zero=True):  # pylint: disable=invalid-name
    """Executes gsutil's "cp" command with |cp_arguments| and returns the
    returncode and the output."""
    command = ['cp']
    command.extend(cp_arguments)
    return gsutil_command(command, parallel=parallel, expect_zero=expect_zero)


def ls(*ls_arguments, expect_zero=True):  # pylint: disable=invalid-name
    """Executes gsutil's "ls" command with |ls_arguments| and returns the result
    and the returncode. Does not except on nonzero return code if not
    |must_exist|."""
    command = ['ls'] + list(ls_arguments)
    result = gsutil_command(command, expect_zero=expect_zero)
    retcode = result.retcode  # pytype: disable=attribute-error
    output = result.output.splitlines()  # pytype: disable=attribute-error
    return retcode, output


def rm(*rm_arguments, recursive=True, force=False, parallel=False):  # pylint: disable=invalid-name
    """Executes gsutil's rm command with |rm_arguments| and returns the result.
    Uses -r if |recursive|. If |force|, then uses -f and will not except if
    return code is nonzero."""
    command = ['rm'] + list(rm_arguments)[:]
    if recursive:
        command.insert(1, '-r')
    if force:
        command.insert(1, '-f')
    return gsutil_command(command, expect_zero=(not force), parallel=parallel)


def rsync(  # pylint: disable=too-many-arguments
        source,
        destination,
        delete=True,
        recursive=True,
        gsutil_options=None,
        options=None,
        parallel=False):
    """Does gsutil rsync from |source| to |destination| using sane defaults that
    can be overriden. Prepends any |gsutil_options| before the rsync subcommand
    if provided."""
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
