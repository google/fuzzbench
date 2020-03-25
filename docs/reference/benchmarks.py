# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Code for generating the table in benchmarks.md."""

import collections
import multiprocessing
import os
import re
import subprocess
import sys
import tarfile
import zipfile

from common import benchmark_utils
from common import fuzzer_utils
from common import utils
from common import oss_fuzz

BUILD_ARCHIVE_EXTENSION = '.tar.gz'
LEN_BUILD_ARCHIVE_EXTENSION = len(BUILD_ARCHIVE_EXTENSION)
COVERAGE_BUILD_PREFIX = 'coverage-build-'
LEN_COVERAGE_BUILD_PREFIX = len(BUILD_ARCHIVE_EXTENSION)

GUARDS_REGEX = re.compile(r'INFO:.*\((?P<num_guards>\d+) guards\).*')

ONE_MB = 1024**2

BENCHMARK_INFO_FIELDS = ['benchmark', 'target', 'dict', 'seeds', 'guards', 'MB']
BenchmarkInfo = collections.namedtuple('BenchmarkInfo', BENCHMARK_INFO_FIELDS)


def get_benchmark_infos(builds_dir):
    """Get BenchmarkInfo for each benchmark that has a build in
    builds_dir."""
    build_paths = [
        os.path.join(builds_dir, path)
        for path in os.listdir(builds_dir)
        if path.endswith(BUILD_ARCHIVE_EXTENSION)
    ]
    pool = multiprocessing.Pool()
    return pool.map(get_benchmark_info, build_paths)


def get_real_benchmark_name(benchmark):
    """The method we use to infer benchmark names from coverage builds
    doesn't quite work because the project name is used in OSS-Fuzz
    builds instead. This function figures out the actual benchmark based on
    the project name."""
    benchmarks_dir = os.path.join(utils.ROOT_DIR, 'benchmarks')
    real_benchmarks = [
        real_benchmark for real_benchmark in os.listdir(benchmarks_dir)
        if os.path.isdir(os.path.join(benchmarks_dir, real_benchmark))
    ]
    if benchmark in real_benchmarks:
        return benchmark
    for real_benchmark in real_benchmarks:
        if not benchmark_utils.is_oss_fuzz(real_benchmark):
            continue
        config = oss_fuzz.get_config(real_benchmark)
        if config['project'] == benchmark:
            return real_benchmark
    return None


def count_oss_fuzz_seeds(fuzz_target_path):
    """Count the number of seeds in the OSS-Fuzz seed archive for
    |fuzze_target_path|."""
    zip_file_name = fuzz_target_path + '_seed_corpus.zip'
    if not os.path.exists(zip_file_name):
        return 0
    seeds = 0
    with zipfile.ZipFile(zip_file_name) as zip_file:
        for info in zip_file.infolist():
            if info.filename.endswith('/'):
                continue
            seeds += 1
    return seeds


def count_standard_seeds(seeds_path):
    """Count the number of seeds for a standard benchmark."""
    seeds = 0
    for _, _, files in os.walk(seeds_path):
        seeds += len(files)
    return seeds


def get_seed_count(benchmark_path, fuzz_target_path):
    """Count the number of seeds for a benchmark."""
    standard_seeds_path = os.path.join(benchmark_path, 'seeds')
    if os.path.exists(standard_seeds_path):
        count_standard_seeds(standard_seeds_path)
    else:
        seeds = count_oss_fuzz_seeds(fuzz_target_path)
    return seeds


def get_benchmark_info(build_path):
    """Get BenchmarkInfo for the benchmark in |build_path|."""
    basename = os.path.basename(build_path)
    benchmark = basename[LEN_COVERAGE_BUILD_PREFIX:-LEN_BUILD_ARCHIVE_EXTENSION]
    benchmark = get_real_benchmark_name(benchmark)
    parent_dir = os.path.dirname(build_path)
    benchmark_path = os.path.join(parent_dir, benchmark)

    try:
        os.mkdir(benchmark_path)
    except FileExistsError:
        pass  # So that function is idempotent.

    with tarfile.open(build_path) as tar_file:
        tar_file.extractall(benchmark_path)

    if benchmark_utils.is_oss_fuzz(benchmark):
        fuzz_target = oss_fuzz.get_config(benchmark)['fuzz_target']
    else:
        fuzz_target = fuzzer_utils.DEFAULT_FUZZ_TARGET_NAME

    fuzz_target_path = fuzzer_utils.get_fuzz_target_binary(
        benchmark_path, fuzz_target)
    assert fuzz_target_path, benchmark

    has_dictionary = os.path.exists(fuzz_target_path + '.dict')

    seeds = get_seed_count(benchmark_path, fuzz_target_path)

    result = subprocess.run([fuzz_target_path, '-runs=0'],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            check=True)

    output = result.stdout.decode()
    search = GUARDS_REGEX.search(output)
    assert search, benchmark
    num_guards = int(search.groupdict()['num_guards'])

    size = os.path.getsize(fuzz_target_path)
    size = round(size / ONE_MB, 2)
    return BenchmarkInfo(benchmark, fuzz_target, has_dictionary, seeds,
                         num_guards, size)


def infos_to_markdown_table(benchmark_infos):
    """Conver a list of BenchmarkInfos into a markdown table and
    return the result."""
    markdown = ''
    for benchmark_info in sorted(benchmark_infos,
                                 key=lambda info: info.benchmark):
        markdown += '|{}|{}|{}|{}|{}|{}|\n'.format(*benchmark_info)
    return markdown


def main():
    """Print a markdown table with important data on each
    benchmark."""
    if len(sys.argv) != 2:
        print('Usage {} <coverage_builds_directory>'.format(sys.argv[0]))
        return 1
    coverage_builds_dir = sys.argv[1]
    infos = get_benchmark_infos(coverage_builds_dir)
    print(infos_to_markdown_table(infos))
    print(BENCHMARK_INFO_FIELDS)
    return 0


if __name__ == '__main__':
    sys.exit(main())
