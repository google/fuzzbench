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
"""Tests for benchmark_dependencies.py."""
import os

from common import benchmark_utils
from src_analysis import benchmark_dependencies

OSS_FUZZ_BENCHMARK = 'curl_curl_fuzzer_http'
STANDARD_BENCHMARK = 'libpng-1.2.56'
OSS_FUZZ_YAML_PATH = os.path.join(benchmark_utils.BENCHMARKS_DIR,
                                  OSS_FUZZ_BENCHMARK, 'oss-fuzz.yaml')
STANDARD_BUILD_SH_PATH = os.path.join(benchmark_utils.BENCHMARKS_DIR,
                                      STANDARD_BENCHMARK, 'build.sh')


def test_is_subpath_of_benchmark():
    """Tests that is_subpath_of_benchmark returns True for subpaths of a
    benchmark and returns False for other paths."""
    assert benchmark_dependencies.is_subpath_of_benchmark(
        OSS_FUZZ_YAML_PATH, OSS_FUZZ_BENCHMARK)
    assert not benchmark_dependencies.is_subpath_of_benchmark(
        STANDARD_BUILD_SH_PATH, OSS_FUZZ_BENCHMARK)


def test_get_files_dependent_benchmarks():
    """Tests that get_files_dependent_benchmarks returns the benchmarks that are
    dependent on the files passed to it."""
    fake_build_sh_path = os.path.join(benchmark_utils.BENCHMARKS_DIR, 'fake',
                                      'build.sh')
    changed_files = [
        STANDARD_BUILD_SH_PATH, OSS_FUZZ_YAML_PATH, fake_build_sh_path
    ]
    dependent_benchmarks = (
        benchmark_dependencies.get_files_dependent_benchmarks(changed_files))

    assert sorted(dependent_benchmarks) == sorted(
        [STANDARD_BENCHMARK, OSS_FUZZ_BENCHMARK])

    dependent_benchmarks = (
        benchmark_dependencies.get_files_dependent_benchmarks(
            [fake_build_sh_path]))

    assert dependent_benchmarks == []
