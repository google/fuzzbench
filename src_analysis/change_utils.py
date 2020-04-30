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
"""Utilities for finding changed code, particularly fuzzers and benchmarks."""
from typing import List

from src_analysis import benchmark_dependencies
from src_analysis import fuzzer_dependencies
# !!! Kill module?


def get_changed_fuzzers(changed_files: List[str] = None) -> List[str]:
    """Returns a list of fuzzers that have changed functionality based
    on the files that have changed in |changed_files|."""
    # TODO(metzman): Handle case where docker/... or make changes.
    changed_fuzzers = fuzzer_dependencies.get_files_dependent_fuzzers(
        changed_files)
    return changed_fuzzers


def get_changed_benchmarks(changed_files: List[str] = None) -> List[str]:
    """Returns a list of benchmarks that have changed functionality based
    on the files that have changed in |changed_files|."""
    changed_benchmarks = benchmark_dependencies.get_files_dependent_benchmarks(
        changed_files)
    return changed_benchmarks
