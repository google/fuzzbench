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
"""Helper functions for using the local_utils tool."""

import os

from common import logs
from common import new_process
#from common import experiment_utils

logger = logs.Logger('local_utils')


def local_utils_command(arguments, *args, **kwargs):
    """Executes a local_utils command with |arguments| and returns the result.
    """
    return new_process.execute(arguments, *args, **kwargs)


def cp(*cp_arguments, **kwargs):  # pylint: disable=invalid-name
    """Executes local_utils's "cp" command with |cp_arguments| and returns the
    returncode and the output."""
    # prepare for cp command
    for file_or_dir_path in cp_arguments:
        dirpath = os.path.dirname(os.path.abspath(file_or_dir_path))
        if not os.path.exists(dirpath):
            os.makedirs(dirpath)

    command = ['cp']
    command.extend(cp_arguments)
    return local_utils_command(command, **kwargs)


def ls(*ls_arguments, must_exist=True, **kwargs):  # pylint: disable=invalid-name
    """Executes local_utils's "ls" command with |ls_arguments| and returns the
    result and the returncode. Does not except on nonzero return code if not
    |must_exist|."""
    command = ['ls'] + list(ls_arguments)
    # Don't use parallel as it probably doesn't help at all.
    result = local_utils_command(command, expect_zero=must_exist, **kwargs)
    retcode = result.retcode  # pytype: disable=attribute-error
    output = result.output.splitlines()  # pytype: disable=attribute-error
    return retcode, output


def rm(  # pylint: disable=invalid-name
        *rm_arguments,
        recursive=True,
        force=False,
        **kwargs):
    """Executes local_utils's rm command with |rm_arguments| and returns the
    result. Uses -r if |recursive|. If |force|, then uses -f and will not except
    if return code is nonzero."""
    command = ['rm'] + list(rm_arguments)[:]
    if recursive:
        command.insert(1, '-r')
    if force:
        command.insert(1, '-f')
    return local_utils_command(command, expect_zero=(not force), **kwargs)


def rsync(  # pylint: disable=too-many-arguments
        source,
        destination,
        delete=True,
        recursive=True,
        options=None,
        **kwargs):
    """Does local_utils rsync from |source| to |destination| using sane defaults
    that can be overriden. Prepends any |local_utils_options| before the rsync
    subcommand if provided."""
    command = []
    command.append('rsync')
    if delete:
        command.append('--delete')
    if recursive:
        command.append('-r')
    if options is not None:
        command.extend(options)
    command.extend([source + '/', destination])
    return local_utils_command(command, **kwargs)
