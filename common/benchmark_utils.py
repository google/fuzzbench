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

from common import experiment_utils
from common import fuzzer_utils
from common import logs
from common import oss_fuzz
from common import utils

VALID_BENCHMARK_REGEX = re.compile(r'^[A-Za-z0-9\._\-]+$')
BENCHMARKS_DIR = os.path.join(utils.ROOT_DIR, 'benchmarks')


def is_oss_fuzz(benchmark):
    """Returns True if |benchmark| is OSS-Fuzz-based project."""
    return os.path.isfile(oss_fuzz.get_config_file(benchmark))


def get_project(benchmark):
    """Returns the OSS-Fuzz project of |benchmark| if it is based on an
    OSS-Fuzz project, otherwise raises ValueError."""
    if is_oss_fuzz(benchmark):
        return oss_fuzz.get_config(benchmark)['project']
    raise ValueError('Can only get project on OSS-Fuzz benchmarks.')


def get_fuzz_target(benchmark):
    """Returns the fuzz target of |benchmark|"""
    if is_oss_fuzz(benchmark):
        return oss_fuzz.get_config(benchmark)['fuzz_target']
    return fuzzer_utils.DEFAULT_FUZZ_TARGET_NAME


def get_runner_image_url(benchmark, fuzzer, cloud_project):
    """Get the URL of the docker runner image for fuzzing the benchmark with
    fuzzer."""
    base_tag = experiment_utils.get_base_docker_tag(cloud_project)
    return '{base_tag}/runners/{fuzzer}/{benchmark}'.format(base_tag=base_tag,
                                                            fuzzer=fuzzer,
                                                            benchmark=benchmark)


def get_builder_image_url(benchmark, fuzzer, cloud_project):
    """Get the URL of the docker builder image for fuzzing the benchmark with
    fuzzer."""
    base_tag = experiment_utils.get_base_docker_tag(cloud_project)
    return '{base_tag}/builders/{fuzzer}/{benchmark}'.format(
        base_tag=base_tag, fuzzer=fuzzer, benchmark=benchmark)


def get_oss_fuzz_builder_hash(benchmark):
    """Get the specified hash of the OSS-Fuzz builder for the OSS-Fuzz project
    used by |benchmark|."""
    if is_oss_fuzz(benchmark):
        return oss_fuzz.get_config(benchmark)['oss_fuzz_builder_hash']
    raise ValueError('Can only get project on OSS-Fuzz benchmarks.')


def validate(benchmark):
    """Return True if |benchmark| is a valid fuzzbench fuzzer."""
    if VALID_BENCHMARK_REGEX.match(benchmark) is None:
        logs.error('%s does not conform to %s pattern.', benchmark,
                   VALID_BENCHMARK_REGEX.pattern)
        return False
    if benchmark in get_all_benchmarks():
        return True
    logs.error('%s must have a build.sh or oss-fuzz.yaml.', benchmark)
    return False


def get_oss_fuzz_benchmarks():
    """Returns the list of all OSS-Fuzz benchmarks."""
    return [
        benchmark for benchmark in get_all_benchmarks()
        if is_oss_fuzz(benchmark)
    ]


def get_all_benchmarks():
    """Returns the list of all benchmarks."""
    all_benchmarks = []
    for benchmark in os.listdir(BENCHMARKS_DIR):
        benchmark_path = os.path.join(BENCHMARKS_DIR, benchmark)
        if os.path.isfile(os.path.join(benchmark_path, 'oss-fuzz.yaml')):
            # Benchmark is an OSS-Fuzz benchmark.
            all_benchmarks.append(benchmark)
        elif os.path.isfile(os.path.join(benchmark_path, 'build.sh')):
            # Benchmark is a standard benchmark.
            all_benchmarks.append(benchmark)
    return all_benchmarks
