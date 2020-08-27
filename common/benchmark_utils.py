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
import os
import re

from common import environment
from common import logs
from common import benchmark_config
from common import utils

# Must be valid in a docker tag.
VALID_BENCHMARK_REGEX = re.compile(r'^[a-z0-9\._\-]+$')
BENCHMARKS_DIR = os.path.join(utils.ROOT_DIR, 'benchmarks')


def get_project(benchmark):
    """Returns the OSS-Fuzz project of |benchmark| if it is based on an
    OSS-Fuzz project, otherwise raises ValueError."""
    return benchmark_config.get_config(benchmark)['project']


def get_fuzz_target(benchmark):
    """Returns the fuzz target of |benchmark|"""
    return benchmark_config.get_config(benchmark)['fuzz_target']


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


def validate(benchmark):
    """Return True if |benchmark| is a valid fuzzbench fuzzer."""
    if VALID_BENCHMARK_REGEX.match(benchmark) is None:
        logs.error('%s does not conform to %s pattern.', benchmark,
                   VALID_BENCHMARK_REGEX.pattern)
        return False
    if benchmark in get_all_benchmarks():
        return True
    logs.error('%s must have a benchmark.yaml.', benchmark)
    return False


def get_all_benchmarks():
    """Returns the list of all benchmarks."""
    all_benchmarks = []
    for benchmark in os.listdir(BENCHMARKS_DIR):
        benchmark_path = os.path.join(BENCHMARKS_DIR, benchmark)
        if os.path.isfile(os.path.join(benchmark_path, 'benchmark.yaml')):
            all_benchmarks.append(benchmark)
    return all_benchmarks
