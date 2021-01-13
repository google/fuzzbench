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
"""Utilities used in testing."""

import contextlib
from unittest import mock


@contextlib.contextmanager
def mock_popen_ctx_mgr(*args, **kwargs):
    """Returns a mocked Popen context manager."""
    with mock.patch('subprocess.Popen',
                    create_mock_popen(*args, **kwargs)) as mocked_popen:
        yield mocked_popen


def create_mock_popen(
        output=bytes('', 'utf-8'), err=bytes('', 'utf-8'), returncode=0):
    """Creates a mock subprocess.Popen."""

    class MockPopen:
        """Mock subprocess.Popen."""
        commands = []
        testcases_written = []

        # pylint: disable=unused-argument
        def __init__(self, command, *args, **kwargs):
            """Inits the MockPopen."""
            stdout = kwargs.pop('stdout', None)
            self.command = command
            self.commands.append(command)
            self.stdout = None
            self.stderr = None
            self.returncode = returncode
            if hasattr(stdout, 'write'):
                self.stdout = stdout
            self.pid = 1

        def communicate(self, input_data=None):  # pylint: disable=unused-argument
            """Mock subprocess.Popen.communicate."""
            if self.stdout:
                self.stdout.write(output)

            if self.stderr:
                self.stderr.write(err)

            return output, err

        def poll(self, input_data=None):  # pylint: disable=unused-argument
            """Mock subprocess.Popen.poll."""
            return self.returncode

        def wait(self, timeout=None):  # pylint: disable=unused-argument
            """Mock subprocess.Popen.wait."""
            return self.poll()

    return MockPopen


class MockPool:
    """Mock version of multiprocessing.Pool."""

    def __init__(self, *args, **kwargs):  # pylint: disable=unused-argument
        """Initialize a mock version of multiprocessing.Pool."""
        self.func_calls = []

    def starmap(self, func, iterable, chunksize=1):  # pylint: disable=unused-argument
        """Mock of multiprocessing.Pool.starmap."""
        for item in iterable:
            self.func_calls.append(item)
        return []

    def map(self, func, iterable, chunksize=1):  # pylint: disable=unused-argument
        """Mock of multiprocessing.Pool.starmap."""
        for item in iterable:
            self.func_calls.append(item)
        return []

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        pass
