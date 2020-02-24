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
import queue
import signal
import subprocess
import sys
import threading
import time

from typing import List, Tuple

from common import logs

LOG_LIMIT_FIELD = 10 * 1024  # 10 KB.


def _enqueue_file_lines(process: subprocess.Popen,
                        out_queue: queue.Queue,
                        dead_read_seconds: int = 1):
    """Read a line from |process.stdout| and put it on the |queue|."""
    process_end_time = None

    while True:
        if (process_end_time and
                time.time() - process_end_time > dead_read_seconds):
            break

        if process.poll() and process_end_time is None:
            process_end_time = time.time()

        try:
            line = process.stdout.readline()
        except ValueError:
            break
        out_queue.put(line)
        if not line:
            break


def _start_enqueue_thread(process: subprocess.Popen
                         ) -> Tuple[queue.Queue, threading.Thread]:
    """Start a thread that calls _enqueue_file_lines. Return the queue and
    thread."""
    out_queue = queue.Queue()
    thread = threading.Thread(target=_enqueue_file_lines,
                              args=(process, out_queue))
    thread.start()
    return out_queue, thread


def _mirror_output(process: subprocess.Popen, output_files: List) -> str:
    """Mirror output from |process|'s stdout to |output_files| and return the
    output."""
    lines = []
    out_queue, thread = _start_enqueue_thread(process)

    while True:
        # See if we can get a line from the queue.
        try:
            # TODO(metzman): Handle cases where the process does not have utf-8
            # encoded output.
            line = out_queue.get_nowait().decode('utf-8', errors='ignore')
        except queue.Empty:
            if not thread.is_alive():
                break
            continue
        if not line:
            if not thread.is_alive():
                break
            continue
        # If we did get a line, add it to our list and write it to the
        # output_files.
        lines.append(line)
        for output_file in output_files[:]:
            try:
                output_file.write(line)
                output_file.flush()
            except ValueError:
                logs.error('Could not write to output_file: %s.', output_file)
                output_files.remove(output_file)
    thread.join()
    return ''.join(lines)


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
        output_files=None,
        timeout: int = None,
        write_to_stdout: bool = True,
        # Not True by default because we can't always set group on processes.
        kill_children: bool = False,
        **kwargs) -> ProcessResult:
    """Execute |command| and return the returncode and the output"""
    if output_files is None:
        output_files = []
    else:
        output_files = output_files[:]
    if write_to_stdout:
        output_files.append(sys.stdout)
    if output_files:
        kwargs['bufsize'] = 1
        kwargs['close_fds'] = 'posix' in sys.builtin_module_names

    kwargs['stdout'] = subprocess.PIPE
    kwargs['stderr'] = subprocess.STDOUT
    if kill_children:
        kwargs['preexec_fn'] = os.setsid

    process = subprocess.Popen(command, *args, **kwargs)
    process_group_id = os.getpgid(process.pid)

    kill_thread = None
    wrapped_process = WrappedPopen(process)
    if timeout is not None:
        kill_thread = _start_kill_thread(wrapped_process, kill_children,
                                         timeout)
    if output_files:
        output = _mirror_output(process, output_files)
    else:
        output, _ = process.communicate()
        output = output.decode('utf-8', errors='ignore')
    process.wait()
    if kill_thread:
        kill_thread.cancel()
    elif kill_children:
        _kill_process_group(process_group_id)
    retcode = process.returncode

    log_message = ('Executed command: "{command}" returned: {retcode}.'.format(
        command=(' '.join(command))[:LOG_LIMIT_FIELD], retcode=retcode))
    output_for_log = output[-LOG_LIMIT_FIELD:]
    log_extras = {'output': output_for_log}

    if expect_zero and retcode != 0 and not wrapped_process.timed_out:
        logs.error(log_message, extras=log_extras)
        raise subprocess.CalledProcessError(retcode, command)

    logs.debug(log_message, extras=log_extras)
    return ProcessResult(retcode, output, wrapped_process.timed_out)
