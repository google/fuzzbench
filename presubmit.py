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

import yaml

from common import benchmark_utils
from common import fuzzer_utils
from common import filesystem
from common import logs
from common import yaml_utils
from service import automatic_run_experiment
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
THIRD_PARTY_DIR_NAME = 'third_party'
_IGNORE_DIRECTORIES = [
    os.path.join(_SRC_ROOT, 'database', 'alembic'),
    os.path.join(_SRC_ROOT, 'benchmarks'),
]

BASE_PYTEST_COMMAND = ['python3', '-m', 'pytest', '-vv']

NON_DEFAULT_CHECKS = {
    'test_changed_integrations',
}


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


def is_fuzzer_tested_in_ci(fuzzer: str) -> bool:
    """Returns True if |fuzzer| is in the list of fuzzers tested in
    fuzzers.yml."""
    yaml_filepath = _SRC_ROOT / '.github' / 'workflows' / 'fuzzers.yml'
    yaml_contents = yaml_utils.read(yaml_filepath)
    fuzzer_list = yaml_contents['jobs']['build']['strategy']['matrix']['fuzzer']
    is_tested = fuzzer in fuzzer_list
    if not is_tested:
        print(f'{fuzzer} is not included in fuzzer list in {yaml_filepath}.')
    return is_tested


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

        if fuzzer != 'coverage' and not is_fuzzer_tested_in_ci(fuzzer):
            self.invalid_fuzzers.add(fuzzer)
            return False

        if fuzzer_utils.validate(fuzzer):
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


def lint(_: List[Path]) -> bool:
    """Run python's linter on all python code. Return False if it fails
    linting."""

    to_check = [
        'analysis',
        'common',
        'database',
        'docker',
        'experiment',
        'fuzzbench',
        'fuzzers',
        'service',
        'src_analysis',
        'test_libs',
        '.github/workflows/build_and_test_run_fuzzer_benchmarks.py',
        'presubmit.py',
    ]

    command = ['python3', '-m', 'pylint', '-j', '0']
    command.extend(to_check)
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
    success = returncode == 0
    if not success:
        print('Code is not formatted correctly, please run \'make format\'')
    return success


def validate_experiment_requests(paths: List[Path]):
    """Returns False if service/experiment-requests.yaml it is in |paths| and is
    not valid."""
    if Path(automatic_run_experiment.REQUESTED_EXPERIMENTS_PATH) not in paths:
        return True

    try:
        experiment_requests = yaml_utils.read(
            automatic_run_experiment.REQUESTED_EXPERIMENTS_PATH)
    except yaml.parser.ParserError:
        print('Error parsing %s.' %
              automatic_run_experiment.REQUESTED_EXPERIMENTS_PATH)
        return False

    # Only validate the latest request.
    result = automatic_run_experiment.validate_experiment_requests(
        experiment_requests[:1])

    if not result:
        print('%s is not valid.' %
              automatic_run_experiment.REQUESTED_EXPERIMENTS_PATH)

    return result


def is_path_ignored(path: Path) -> bool:
    """Returns True if |path| is a subpath of an ignored directory or is a
    third_party directory."""
    for ignore_directory in _IGNORE_DIRECTORIES:
        if filesystem.is_subpath(ignore_directory, path):
            return True

    # Third party directories can be anywhere.
    path_parts = str(path).split(os.sep)
    if any(path_part == THIRD_PARTY_DIR_NAME for path_part in path_parts):
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

        if is_path_ignored(path):
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
    return [path for path in paths if not is_path_ignored(path)]


def pytest(_) -> bool:
    """Run all unittests using pytest."""
    returncode = subprocess.run(BASE_PYTEST_COMMAND, check=False).returncode
    return returncode == 0


def validate_fuzzers_and_benchmarks(file_paths: List[Path]):
    """Validate fuzzers and benchmarks."""
    fuzzer_and_benchmark_validator = FuzzerAndBenchmarkValidator()
    path_valid_statuses = [
        fuzzer_and_benchmark_validator.validate(path) for path in file_paths
    ]
    return all(path_valid_statuses)


def do_default_checks(file_paths: List[Path], checks) -> bool:
    """Do default presubmit checks and return False if any presubmit check
    fails."""
    failed_checks = []
    for check_name, check in checks:
        if check_name in NON_DEFAULT_CHECKS:
            continue

        if not check(file_paths):
            print('ERROR: %s failed, see errors above.' % check_name)
            failed_checks.append(check_name)

    if failed_checks:
        print('Failed checks: %s' % ' '.join(failed_checks))
        return False

    return True


def bool_to_returncode(success: bool) -> int:
    """Return 0 if |success|. Otherwise return 1."""
    if success:
        print('Success.')
        return 0

    print('Failed.')
    return 1


def get_args(command_check_mapping):
    """Get arguments passed to program."""
    parser = argparse.ArgumentParser(
        description='Presubmit script for fuzzbench.')
    parser.add_argument(
        'command',
        choices=dict(command_check_mapping).keys(),
        nargs='?',
        help='The presubmit check to run. Defaults to most of them.')
    parser.add_argument('--all-files',
                        action='store_true',
                        help='Run presubmit check(s) on all files',
                        default=False)
    parser.add_argument('-v', '--verbose', action='store_true', default=False)

    return parser.parse_args()


def initialize_logs(verbose: bool):
    """Initialize logging."""
    if not verbose:
        logs.initialize()
    else:
        logs.initialize(log_level=logging.DEBUG)


def get_relevant_files(all_files: bool) -> List[Path]:
    """Get the files that should be checked."""
    if not all_files:
        relevant_files = [Path(path) for path in diff_utils.get_changed_files()]
    else:
        relevant_files = get_all_files()

    return filter_ignored_files(relevant_files)


def do_single_check(command: str, relevant_files: List[Path],
                    command_check_mapping) -> bool:
    """Do a single check requested by a command."""
    check = dict(command_check_mapping)[command]
    if command == 'format':
        success = check(relevant_files, False)
    else:
        success = check(relevant_files)
    if not success:
        print('ERROR: %s failed, see errors above.' % check.__name__)

    return success


def main() -> int:
    """Check that this branch conforms to the standards of fuzzbench."""

    # Use list of tuples so order is preserved.
    command_check_mapping = [
        ('licensecheck', license_check),
        ('format', yapf),
        ('lint', lint),
        ('typecheck', pytype),
        ('test', pytest),
        ('validate_fuzzers_and_benchmarks', validate_fuzzers_and_benchmarks),
        ('validate_experiment_requests', validate_experiment_requests),
        ('test_changed_integrations', test_changed_integrations),
    ]

    args = get_args(command_check_mapping)

    os.chdir(_SRC_ROOT)

    initialize_logs(args.verbose)

    relevant_files = get_relevant_files(args.all_files)

    logs.debug('Running presubmit check(s) on: %s',
               ' '.join(str(path) for path in relevant_files))

    if not args.command:
        # Do default checks.
        success = do_default_checks(relevant_files, command_check_mapping)
        return bool_to_returncode(success)

    success = do_single_check(args.command, relevant_files,
                              command_check_mapping)
    return bool_to_returncode(success)


if __name__ == '__main__':
    sys.exit(main())
