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
"""Utilities for finding changed components, particularly fuzzers and
benchmarks."""
import os
from typing import List

from common import utils
from common import filesystem
from common import fuzzer_utils
from src_analysis import benchmark_dependencies
from src_analysis import fuzzer_dependencies

# This will mean changes to OSS-Fuzz Dockerfiles cause standard benchmarks to be
# built and vice versa. But until we map the relationship between dockerfiles in
# python, ignore this for simplicity.
CI_FILES = set([
    os.path.join(utils.ROOT_DIR, 'Makefile'),
    os.path.join(utils.ROOT_DIR, '.github', 'workflows',
                 'build_and_test_run_fuzzer_benchmarks.py')
] + filesystem.list_files(os.path.join(utils.ROOT_DIR, 'docker')))


def get_absolute_paths(file_paths):
    """Returns the list of absolute paths to each path in file_paths."""
    return [os.path.abspath(file_path) for file_path in file_paths]


def get_changed_fuzzers(changed_files: List[str] = None) -> List[str]:
    """Returns a list of fuzzers that have changed functionality based
    on the files that have changed in |changed_files|."""
    changed_files = get_absolute_paths(changed_files)
    changed_fuzzers = fuzzer_dependencies.get_files_dependent_fuzzers(
        changed_files)
    return changed_fuzzers


def get_changed_fuzzers_for_ci(changed_files: List[str] = None) -> List[str]:
    """Returns a list of fuzzers that have changed functionality based
    on the files that have changed in |changed_files|.
    Unlike get_changed_fuzzers this function considers changes that affect
    building or running fuzzers in CI."""
    changed_files = get_absolute_paths(changed_files)
    if any(changed_file in CI_FILES for changed_file in changed_files):
        # If any of changed files are in CI_FILES.
        return fuzzer_utils.get_fuzzer_names()
    return get_changed_fuzzers(changed_files)


def get_changed_benchmarks(changed_files: List[str] = None) -> List[str]:
    """Returns a list of benchmarks that have changed functionality based
    on the files that have changed in |changed_files|."""
    changed_files = get_absolute_paths(changed_files)
    changed_benchmarks = benchmark_dependencies.get_files_dependent_benchmarks(
        changed_files)
    return changed_benchmarks
