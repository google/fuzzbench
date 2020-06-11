#!/usr/bin/env python3
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
"""Presubmit script for fuzzbench."""
# pylint: disable=wrong-import-position
import os

# Many users need this if they are using a Google Cloud instance for development
# or if their system has a weird setup that makes FuzzBench think it is running
# on Google Cloud. It's unlikely that setting this will mess anything up so set
# it.
# TODO(metzman): Make local the default setting and propagate 'NOT_LOCAL' to all
# production environments so we don't need to worry about this any more.
os.environ['FORCE_LOCAL'] = '1'

import argparse
import logging
from pathlib import Path
import subprocess
import sys
from typing import List, Optional

from common import benchmark_utils
from common import fuzzer_utils
from common import filesystem
from common import logs
from src_analysis import change_utils
from src_analysis import diff_utils

_LICENSE_CHECK_FILENAMES = ['Dockerfile']
_LICENSE_CHECK_EXTENSIONS = [
    '.bash',
    '.c',
    '.cc',
    '.cpp',
    '.css',
    '.h',
    '.htm',
    '.html',
    '.js',
    '.proto',
    '.py',
    '.sh',
]
_LICENSE_CHECK_STRING = 'http://www.apache.org/licenses/LICENSE-2.0'

_SRC_ROOT = Path(__file__).absolute().parent
_IGNORE_DIRECTORIES = [
    os.path.join(_SRC_ROOT, 'database', 'alembic'),
    os.path.join(_SRC_ROOT, 'third_party'),
]

BASE_PYTEST_COMMAND = ['python3', '-m', 'pytest', '-vv']


def get_containing_subdir(path: Path, parent_path: Path) -> Optional[str]:
    """Return the subdirectory of |parent_path| that contains |path|.
    Return None if |path| is not in |parent_path|."""
    parts = path.relative_to(_SRC_ROOT).parts
    if parts[0] != parent_path.name:
        return None
    containing_subdir = _SRC_ROOT / parts[0] / parts[1]
    if not containing_subdir.is_dir():
        # Can only be a fuzzer or benchmark if it is a directory.
        return None
    return containing_subdir.name


def get_fuzzer(path: Path) -> Optional[str]:
    """Return the name of the fuzzer |path| is part of, or return None if it is
    not part of a fuzzer."""
    return get_containing_subdir(path, _SRC_ROOT / 'fuzzers')


def get_benchmark(path: Path) -> Optional[str]:
    """Return the name of the benchmark |path| is part of, or return None if it
    is not part of a benchmark."""
    return get_containing_subdir(path, _SRC_ROOT / 'benchmarks')


class FuzzerAndBenchmarkValidator:
    """Class that validates the names of fuzzers and benchmarks."""

    def __init__(self):
        self.invalid_fuzzers = set()
        self.invalid_benchmarks = set()

    def validate_fuzzer(self, path: Path):
        """Return True if |path| is part of a valid fuzzer. Otherwise return
        False and print an error."""
        fuzzer = get_fuzzer(path)

        if fuzzer is None:
            return True

        if fuzzer in self.invalid_fuzzers:
            # We know this is invalid and have already complained about it.
            return False

        valid = fuzzer_utils.validate(fuzzer)
        if valid:
            return True

        self.invalid_fuzzers.add(fuzzer)

        print(fuzzer, 'is not valid.')
        return False

    def validate_benchmark(self, path: Path):
        """Return True if |path| is part of a valid benchmark. Otherwise return
        False and print an error."""
        benchmark = get_benchmark(path)

        if benchmark is None:
            return True

        if benchmark in self.invalid_benchmarks:
            # We know this is invalid and have already complained about it.
            return False

        valid = benchmark_utils.validate(benchmark)
        if valid:
            return True

        self.invalid_benchmarks.add(benchmark)

        print(benchmark, 'is not valid.')
        return False

    def validate(self, file_path: Path) -> bool:
        """If |file_path| is in an invalid fuzzer or benchmark then return
        False. If the fuzzer or benchmark is not in |self.invalid_dirs|, then
        print an error message and it to |self.invalid_dirs|."""
        return (self.validate_fuzzer(file_path) and
                self.validate_benchmark(file_path))


def is_python(path: Path) -> bool:
    """Returns True if |path| ends in .py."""
    return path.suffix == '.py'


MIGRATIONS_PATH = os.path.join(_SRC_ROOT, 'database', 'alembic', 'versions')


def filter_migrations(paths):
    """Filter out migration scripts."""
    # TODO(metzman): Filter out all alembic scripts.
    return [
        path for path in paths if not os.path.dirname(path) == MIGRATIONS_PATH
    ]


def test_changed_integrations(paths: List[Path]):
    """Runs tests that build changed fuzzers with all benchmarks and changed
    benchmarks with measurer and all fuzzers. Not enabled by default since it
    requires GCB."""
    benchmarks = change_utils.get_changed_benchmarks(
        [str(path) for path in paths])
    fuzzers = change_utils.get_changed_fuzzers([str(path) for path in paths])

    if not benchmarks and not fuzzers:
        return True

    pytest_command = BASE_PYTEST_COMMAND + [
        '-k', 'TestBuildChangedBenchmarksOrFuzzers'
    ]

    env = os.environ.copy()
    if benchmarks:
        env = os.environ.copy()
        env['TEST_BUILD_CHANGED_BENCHMARKS'] = ' '.join(benchmarks)

    if fuzzers:
        env['TEST_BUILD_CHANGED_FUZZERS'] = ' '.join(fuzzers)

    retcode = subprocess.run(pytest_command, check=False, env=env).returncode
    return retcode == 0


def lint(paths: List[Path]) -> bool:
    """Run python's linter on |paths| if it is a python file. Return False if it
    fails linting."""
    paths = [path for path in paths if is_python(path)]
    paths = filter_migrations(paths)
    if not paths:
        return True

    command = ['python3', '-m', 'pylint', '-j', '0']
    command.extend(paths)
    returncode = subprocess.run(command, check=False).returncode
    return returncode == 0


def pytype(paths: List[Path]) -> bool:
    """Run pytype on |path| if it is a python file. Return False if it fails
    type checking."""
    paths = [path for path in paths if is_python(path)]
    if not paths:
        return True

    base_command = ['python3', '-m', 'pytype']
    success = True

    # TODO(metzman): Change this to the parallel pytype when the path issue is
    # solved.
    for path in paths:
        command = base_command[:]
        command.append(path)
        returncode = subprocess.run(command, check=False).returncode
        if returncode != 0:
            success = False
    return success


def yapf(paths: List[Path], validate: bool = True) -> bool:
    """Do yapf on |path| if it is Python file. Only validates format if
    |validate| otherwise, formats the file. Returns False if validation
    or formatting fails."""
    paths = [path for path in paths if is_python(path)]
    if not paths:
        return True

    validate_argument = '-d' if validate else '-i'
    command = ['yapf', validate_argument, '-p']
    command.extend(paths)
    returncode = subprocess.run(command, check=False).returncode
    return returncode == 0


def is_path_in_ignore_directory(path: Path) -> bool:
    """Returns True if |path| is a subpath of an ignored directory."""
    for ignore_directory in _IGNORE_DIRECTORIES:
        if filesystem.is_subpath(ignore_directory, path):
            return True
    return False


def license_check(paths: List[Path]) -> bool:
    """Validate license header."""
    if not paths:
        return True

    success = True
    for path in paths:
        filename = os.path.basename(path)
        extension = os.path.splitext(path)[1]
        if (filename not in _LICENSE_CHECK_FILENAMES and
                extension not in _LICENSE_CHECK_EXTENSIONS):
            continue

        if is_path_in_ignore_directory(path):
            continue

        with open(path) as file_handle:
            if _LICENSE_CHECK_STRING not in file_handle.read():
                print('Missing license header in file %s.' % str(path))
                success = False

    return success


def get_all_files() -> List[Path]:
    """Returns a list of absolute paths of files in this repo."""
    get_all_files_command = ['git', 'ls-files']
    output = subprocess.check_output(
        get_all_files_command).decode().splitlines()
    return [Path(path).absolute() for path in output if Path(path).is_file()]


def filter_ignored_files(paths: List[Path]) -> List[Path]:
    """Returns a list of absolute paths of files in this repo that can be
    checked statically."""
    return [path for path in paths if not is_path_in_ignore_directory(path)]


def do_tests() -> bool:
    """Run all unittests."""
    returncode = subprocess.run(BASE_PYTEST_COMMAND, check=False).returncode
    return returncode == 0


def do_checks(file_paths: List[Path]) -> bool:
    """Return False if any presubmit check fails."""
    success = True

    fuzzer_and_benchmark_validator = FuzzerAndBenchmarkValidator()
    path_valid_statuses = [
        fuzzer_and_benchmark_validator.validate(path) for path in file_paths
    ]
    if not all(path_valid_statuses):
        success = False

    for check in [license_check, yapf, lint, pytype]:
        if not check(file_paths):
            print('ERROR: %s failed, see errors above.' % check.__name__)
            success = False

    if not do_tests():
        success = False

    return success


def bool_to_returncode(success: bool) -> int:
    """Return 0 if |success|. Otherwise return 1."""
    if success:
        print('Success.')
        return 0

    print('Failed.')
    return 1


def main() -> int:
    """Check that this branch conforms to the standards of fuzzbench."""
    parser = argparse.ArgumentParser(
        description='Presubmit script for fuzzbench.')
    choices = [
        'format', 'lint', 'typecheck', 'licensecheck',
        'test_changed_integrations'
    ]
    parser.add_argument(
        'command',
        choices=choices,
        nargs='?',
        help='The presubmit check to run. Defaults to all of them')
    parser.add_argument('--all-files',
                        action='store_true',
                        help='Run presubmit check(s) on all files',
                        default=False)
    parser.add_argument('-v', '--verbose', action='store_true', default=False)

    args = parser.parse_args()

    os.chdir(_SRC_ROOT)

    if not args.verbose:
        logs.initialize()
    else:
        logs.initialize(log_level=logging.DEBUG)

    if not args.all_files:
        relevant_files = [Path(path) for path in diff_utils.get_changed_files()]
    else:
        relevant_files = get_all_files()

    relevant_files = filter_ignored_files(relevant_files)

    logs.debug('Running presubmit check(s) on: %s',
               ' '.join(str(path) for path in relevant_files))

    if not args.command:
        success = do_checks(relevant_files)
        return bool_to_returncode(success)

    command_check_mapping = {
        'format': yapf,
        'lint': lint,
        'typecheck': pytype,
        'test_changed_integrations': test_changed_integrations
    }

    check = command_check_mapping[args.command]
    if args.command == 'format':
        success = check(relevant_files, False)
    else:
        success = check(relevant_files)
    if not success:
        print('ERROR: %s failed, see errors above.' % check.__name__)
    return bool_to_returncode(success)


if __name__ == '__main__':
    sys.exit(main())
