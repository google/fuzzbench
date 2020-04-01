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
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import zipfile

from common import benchmark_utils
from common import filesystem
from common import fuzzer_utils as common_fuzzer_utils
from common import oss_fuzz
from common import utils
from fuzzers import utils as fuzzer_utils

BUILD_ARCHIVE_EXTENSION = '.tar.gz'
COVERAGE_BUILD_PREFIX = 'coverage-build-'
LEN_COVERAGE_BUILD_PREFIX = len(COVERAGE_BUILD_PREFIX)

GUARDS_REGEX = re.compile(rb'INFO:.*\((?P<num_guards>\d+) guards\).*')

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
    real_benchmarks = os.listdir(benchmarks_dir)
    if benchmark in real_benchmarks:
        return benchmark

    for real_benchmark in real_benchmarks:
        if not os.path.isdir(os.path.join(benchmarks_dir, real_benchmark)):
            continue

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

    with zipfile.ZipFile(zip_file_name) as zip_file:
        return len([
            filename for filename in zip_file.namelist()
            if not filename.endswith('/')
        ])


def count_standard_seeds(seeds_dir):
    """Count the number of seeds for a standard benchmark."""
    return len([p for p in Path(seeds_dir).glob('**/*') if p.is_file()])


def get_seed_count(benchmark_path, fuzz_target_path):
    """Count the number of seeds for a benchmark."""
    standard_seeds_dir = os.path.join(benchmark_path, 'seeds')
    if os.path.exists(standard_seeds_dir):
        return count_standard_seeds(standard_seeds_dir)
    return count_oss_fuzz_seeds(fuzz_target_path)


def get_num_guards(fuzz_target_path):
    """Returns the number of guards in |fuzz_target_path|."""
    result = subprocess.run([fuzz_target_path, '-runs=0'],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            check=True)
    output = result.stdout
    match = GUARDS_REGEX.search(output)
    assert match, 'Couldn\'t determine guards for ' + fuzz_target_path
    return int(match.groupdict()['num_guards'])


def get_binary_size_mb(fuzz_target_path):
    """Returns the size of |fuzz_target_path| in MB, rounded to two
    decimal places."""
    size = os.path.getsize(fuzz_target_path)
    return round(size / ONE_MB, 2)


def get_fuzz_target(benchmark, benchmark_path):
    """Returns the fuzz target and its path for |benchmark|."""
    if benchmark_utils.is_oss_fuzz(benchmark):
        fuzz_target = oss_fuzz.get_config(benchmark)['fuzz_target']
    else:
        fuzz_target = common_fuzzer_utils.DEFAULT_FUZZ_TARGET_NAME

    fuzz_target_path = common_fuzzer_utils.get_fuzz_target_binary(
        benchmark_path, fuzz_target)
    assert fuzz_target_path, 'Couldn\'t find fuzz target for ' + benchmark

    return fuzz_target, fuzz_target_path


def get_benchmark_info(build_path):
    """Get BenchmarkInfo for the benchmark in |build_path|."""
    basename = os.path.basename(build_path)
    benchmark = basename[len(COVERAGE_BUILD_PREFIX
                            ):-len(BUILD_ARCHIVE_EXTENSION)]
    benchmark = get_real_benchmark_name(benchmark)
    parent_dir = os.path.dirname(build_path)
    benchmark_path = os.path.join(parent_dir, benchmark)

    filesystem.create_directory(benchmark_path)

    with tarfile.open(build_path) as tar_file:
        tar_file.extractall(benchmark_path)

    fuzz_target, fuzz_target_path = get_fuzz_target(benchmark, benchmark_path)
    has_dictionary = bool(fuzzer_utils.get_dictionary_path(fuzz_target_path))

    seeds = get_seed_count(benchmark_path, fuzz_target_path)
    num_guards = get_num_guards(fuzz_target_path)
    size = get_binary_size_mb(fuzz_target_path)
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
