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
"""Module for finding dependencies of benchmarks, and benchmarks that are
dependent on given files."""
import os

from common import benchmark_utils


def is_subpath_of_benchmark(path, benchmark):
    """Returns True if |path| is a subpath of |benchmark|."""
    benchmark_path = os.path.join(benchmark_utils.BENCHMARKS_DIR, benchmark)
    common_path = os.path.commonpath([path, benchmark_path])
    return common_path == benchmark_path


def get_files_dependent_benchmarks(dependency_files):
    """Returns the list of benchmarks that are dependent on any file in
    |dependency_files|."""
    dependent_benchmarks = []
    benchmarks = benchmark_utils.get_all_benchmarks()
    for dependency_file in dependency_files:
        for benchmark in benchmarks:

            if not is_subpath_of_benchmark(dependency_file, benchmark):
                # Benchmarks can only depend on files in their directory.
                continue

            dependent_benchmarks.append(benchmark)

    return dependent_benchmarks
