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
"""Code for dealing with benchmarks."""
import enum
import os
import re

import yaml

from common import environment
from common import logs
from common import benchmark_config
from common import utils

# Must be valid in a docker tag.
VALID_BENCHMARK_REGEX = re.compile(r'^[a-z0-9\._\-]+$')
BENCHMARKS_DIR = os.path.join(utils.ROOT_DIR, 'benchmarks')


class BenchmarkType(str, enum.Enum):
    """Benchmark type."""
    CODE = 'code'
    BUG = 'bug'


# pytype: disable=missing-parameter
BENCHMARK_TYPE_STRS = {benchmark_type.value for benchmark_type in BenchmarkType}
# pytype: enable=missing-parameter


def get_fuzz_target(benchmark):
    """Returns the fuzz target of |benchmark|"""
    return benchmark_config.get_config(benchmark)['fuzz_target']


def get_project(benchmark):
    """Returns the project of |benchmark|"""
    return benchmark_config.get_config(benchmark)['project']


def get_type(benchmark):
    """Returns the type of |benchmark|"""
    return benchmark_config.get_config(benchmark).get('type',
                                                      BenchmarkType.CODE.value)


def is_oss_fuzz_benchmark(benchmark):
    """Returns if benchmark is a OSS-Fuzz benchmark."""
    return bool(benchmark_config.get_config(benchmark).get('commit_date'))


def get_runner_image_url(experiment, benchmark, fuzzer, docker_registry):
    """Get the URL of the docker runner image for fuzzing the benchmark with
    fuzzer."""
    tag = 'latest' if environment.get('LOCAL_EXPERIMENT') else experiment
    return '{docker_registry}/runners/{fuzzer}/{benchmark}:{tag}'.format(
        docker_registry=docker_registry,
        fuzzer=fuzzer,
        benchmark=benchmark,
        tag=tag)


def get_builder_image_url(benchmark, fuzzer, docker_registry):
    """Get the URL of the docker builder image for fuzzing the benchmark with
    fuzzer."""
    return '{docker_registry}/builders/{fuzzer}/{benchmark}'.format(
        docker_registry=docker_registry, fuzzer=fuzzer, benchmark=benchmark)


def validate_name(benchmark):
    """Returns True if |benchmark| is a valid fuzzbench benchmark name."""
    if VALID_BENCHMARK_REGEX.match(benchmark) is None:
        logs.error('%s does not conform to %s pattern.', benchmark,
                   VALID_BENCHMARK_REGEX.pattern)
        return False
    return True


def validate_type(benchmark):
    """Returns True if |benchmark| has a valid type."""
    benchmark_type = get_type(benchmark)
    if benchmark_type not in BENCHMARK_TYPE_STRS:
        logs.error('%s has an invalid benchmark type %s, must be one of %s',
                   benchmark, benchmark_type, BENCHMARK_TYPE_STRS)
        return False
    return True


def validate(benchmark):
    """Returns True if |benchmark| is a valid fuzzbench benchmark."""
    if not validate_name(benchmark):
        return False

    if benchmark not in get_all_benchmarks():
        logs.error('%s must have a benchmark.yaml.', benchmark)
        return False

    # Validate config file can be parsed.
    try:
        get_fuzz_target(benchmark)
    except yaml.parser.ParserError:
        logs.error('%s must have a valid benchmark.yaml file. Failed to parse.',
                   benchmark)
        return False
    except KeyError:
        logs.error('%s\'s benchmark.yaml does not define "fuzz_target".',
                   benchmark)
        return False

    # Validate type.
    return validate_type(benchmark)


def get_all_benchmarks():
    """Returns the list of all benchmarks."""
    all_benchmarks = []
    for benchmark in os.listdir(BENCHMARKS_DIR):
        benchmark_path = os.path.join(BENCHMARKS_DIR, benchmark)
        if os.path.isfile(os.path.join(benchmark_path, 'benchmark.yaml')):
            all_benchmarks.append(benchmark)
    return sorted(all_benchmarks)


def get_coverage_benchmarks():
    """Returns the list of all coverage benchmarks."""
    return (get_oss_fuzz_coverage_benchmarks() +
            get_standard_coverage_benchmarks())


def get_oss_fuzz_coverage_benchmarks():
    """Returns the list of OSS-Fuzz coverage benchmarks."""
    return [
        benchmark for benchmark in get_all_benchmarks()
        if is_oss_fuzz_benchmark(benchmark) and
        get_type(benchmark) == BenchmarkType.CODE.value
    ]


def get_standard_coverage_benchmarks():
    """Returns the list of standard coverage benchmarks."""
    return [
        benchmark for benchmark in get_all_benchmarks()
        if not is_oss_fuzz_benchmark(benchmark) and
        get_type(benchmark) == BenchmarkType.CODE.value
    ]


def get_bug_benchmarks():
    """Returns the list of standard bug benchmarks."""
    return [
        benchmark for benchmark in get_all_benchmarks()
        if get_type(benchmark) == BenchmarkType.BUG.value
    ]


def is_cpp(benchmark):
    """Returns True if |benchmark| is written in C/C++."""
    return get_language(benchmark) == 'c++'


def exclude_non_cpp(benchmarks):
    """Returns |benchmarks| with only benchmarks written in C/C++."""
    return [benchmark for benchmark in benchmarks if is_cpp(benchmark)]


def get_language(benchmark):
    """Returns the prorgamming language the benchmark was written in."""
    config = benchmark_config.get_config(benchmark)
    return config.get('language', 'c++')
