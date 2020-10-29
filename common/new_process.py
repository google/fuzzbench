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
"""Helpers for creating new processes."""
import collections
import os
import signal
import subprocess
import threading
from typing import List

from common import logs

LOG_LIMIT_FIELD = 10 * 1024  # 10 KB.


class WrappedPopen:
    """A simple wrapper class around subprocess.Popen."""

    def __init__(self, process: subprocess.Popen):
        self.process = process
        self.timed_out = False


def _kill_process_group(process_group_id: int):
    """Kill the processes with the group id |process_group_id|."""
    try:
        os.killpg(process_group_id, signal.SIGKILL)
    except ProcessLookupError:
        pass


def _end_process(wrapped_process: WrappedPopen, kill_children: bool):
    """Sends SIGKILL to |process| and kills child processes if
    |kill_children|."""
    try:
        process_group_id = os.getpgid(wrapped_process.process.pid)
    except ProcessLookupError:
        process_group_id = None

    wrapped_process.process.kill()
    wrapped_process.timed_out = True
    if kill_children and process_group_id is not None:
        _kill_process_group(process_group_id)


def _start_kill_thread(process: WrappedPopen, kill_children: bool,
                       timeout: int) -> threading.Timer:
    """Starts a thread to start killing |process| if it doesn't die before
    |timeout| seconds have elapsed."""
    # TODO(metzman): Figure out if we should kill descendant processes.
    timer = threading.Timer(timeout, _end_process, [process, kill_children])
    timer.start()
    return timer


ProcessResult = collections.namedtuple('ProcessResult',
                                       ['retcode', 'output', 'timed_out'])


def execute(  # pylint: disable=too-many-locals,too-many-branches
        command: List[str],
        *args,
        expect_zero: bool = True,
        timeout: int = None,
        write_to_stdout=False,
        # If not set, will default to PIPE.
        output_file=None,
        # Not True by default because we can't always set group on processes.
        kill_children: bool = False,
        **kwargs) -> ProcessResult:
    """Execute |command| and return the returncode and the output"""
    if write_to_stdout:
        # Don't set stdout, it's default value None, causes it to be set to
        # stdout.
        assert output_file is None
    elif not output_file:
        output_file = subprocess.PIPE

    kwargs['stdout'] = output_file
    kwargs['stderr'] = subprocess.STDOUT
    if kill_children:
        kwargs['preexec_fn'] = os.setsid

    process = subprocess.Popen(command, *args, **kwargs)
    process_group_id = os.getpgid(process.pid)

    wrapped_process = WrappedPopen(process)
    if timeout is not None:
        kill_thread = _start_kill_thread(wrapped_process, kill_children,
                                         timeout)
    output, _ = process.communicate()

    if timeout is not None:
        kill_thread.cancel()
    elif kill_children:
        # elif because the kill_thread will kill children if needed.
        _kill_process_group(process_group_id)

    retcode = process.returncode

    command_log_str = ' '.join(command)[:LOG_LIMIT_FIELD]
    log_message = 'Executed command: "%s" returned: %d.'

    if output is not None:
        output = output.decode('utf-8', errors='ignore')
        output_for_log = output[-LOG_LIMIT_FIELD:]
        log_extras = {'output': output_for_log}
    else:
        log_extras = None

    if expect_zero and retcode != 0 and not wrapped_process.timed_out:
        logs.error(log_message, command_log_str, retcode, extras=log_extras)
        raise subprocess.CalledProcessError(retcode, command)

    logs.debug(log_message, command_log_str, retcode, extras=log_extras)
    return ProcessResult(retcode, output, wrapped_process.timed_out)
