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
"""Module for building things for use in trials."""

import argparse
import itertools
from multiprocessing import pool as mp_pool
import os
import random
import subprocess
import sys
import time
from typing import Callable, List, Tuple

from common import benchmark_config
from common import benchmark_utils
from common import experiment_utils
from common import fuzzer_config
from common import fuzzer_utils
from common import filesystem
from common import utils
from common import logs

from experiment.build import build_utils

if not experiment_utils.is_local_experiment():
    import experiment.build.gcb_build as buildlib
else:
    import experiment.build.local_build as buildlib

# FIXME: Use 10 as default quota.
# Even though it says queueing happen, we end up exceeding limits on "get", so
# be conservative. Use 30 for now since this is limit for FuzzBench service.
DEFAULT_MAX_CONCURRENT_BUILDS = 30

# Build fail retries and wait interval.
NUM_BUILD_RETRIES = 3
BUILD_FAIL_WAIT = 5 * 60

BENCHMARKS_DIR = os.path.join(utils.ROOT_DIR, 'benchmarks')

logger = logs.Logger('builder')  # pylint: disable=invalid-name


def get_fuzzer_benchmark_pairs(fuzzers, benchmarks):
    """Return a tuple of (fuzzer, benchmark) pairs to build. Excludes
    unsupported fuzzers from each benchmark.
    """
    unsupported_fuzzer_benchmark_pairs = set()
    for fuzzer in fuzzers:
        config = fuzzer_config.get_config(fuzzer)
        unsupported_benchmarks = config.get('unsupported_benchmarks')
        if unsupported_benchmarks:
            unsupported_fuzzer_benchmark_pairs.update(
                itertools.product([fuzzer], unsupported_benchmarks))
        allowed_benchmarks = config.get('allowed_benchmarks')
        if allowed_benchmarks:
            for benchmark in benchmarks:
                if benchmark not in allowed_benchmarks:
                    unsupported_fuzzer_benchmark_pairs.add((fuzzer, benchmark))

        # Handle languages.
        fuzzer_languages = fuzzer_utils.get_languages(fuzzer)
        for benchmark in benchmarks:
            benchmark_language = benchmark_utils.get_language(benchmark)
            if benchmark_language not in fuzzer_languages:
                unsupported_fuzzer_benchmark_pairs.add((fuzzer, benchmark))

    for benchmark in benchmarks:
        config = benchmark_config.get_config(benchmark)
        unsupported_fuzzers = config.get('unsupported_fuzzers')
        if not unsupported_fuzzers:
            continue
        unsupported_fuzzer_benchmark_pairs.update(
            itertools.product(unsupported_fuzzers, [benchmark]))

    fuzzer_benchmark_pairs = list(itertools.product(fuzzers, benchmarks))
    return [
        i for i in fuzzer_benchmark_pairs
        if i not in unsupported_fuzzer_benchmark_pairs
    ]


def build_base_images() -> Tuple[int, str]:
    """Build base images."""
    return buildlib.build_base_images()


def build_measurer(benchmark: str) -> bool:
    """Do a coverage build for a benchmark."""
    try:
        logger.info('Building measurer for benchmark: %s.', benchmark)
        buildlib.build_coverage(benchmark)
        logs.info('Done building measurer for benchmark: %s.', benchmark)
        return True
    except Exception:  # pylint: disable=broad-except
        logger.error('Failed to build measurer for %s.', benchmark)
        return False


def build_all_measurers(
        benchmarks: List[str],
        num_concurrent_builds: int = DEFAULT_MAX_CONCURRENT_BUILDS
) -> List[str]:
    """Build measurers for each benchmark in |benchmarks| in parallel
    Returns a list of benchmarks built successfully."""
    logger.info('Building measurers.')
    filesystem.recreate_directory(build_utils.get_coverage_binaries_dir())
    build_measurer_args = [(benchmark,) for benchmark in benchmarks]
    successful_calls = retry_build_loop(build_measurer, build_measurer_args,
                                        num_concurrent_builds)
    logger.info('Done building measurers.')
    # Return list of benchmarks (like the list we were passed as an argument)
    # instead of returning a list of tuples each containing a benchmark.
    return [successful_call[0] for successful_call in successful_calls]


def split_successes_and_failures(inputs: List,
                                 results: List[bool]) -> Tuple[List, List]:
    """Returns a tuple where the left side is a list of every input[idx] where
    results[idx] is True and the right side is a list of every input[idx] where
    results[idx] is False."""
    assert len(inputs) == len(results)
    successes = []
    failures = []
    for idx, _input in enumerate(inputs):
        if results[idx]:
            successes.append(_input)
        else:
            failures.append(_input)
    return successes, failures


def retry_build_loop(build_func: Callable, inputs: List[Tuple],
                     num_concurrent_builds: int) -> List:
    """Calls |build_func| in parallel on |inputs|. Repeat on failures up to
    |NUM_BUILD_RETRIES| times. Returns the list of inputs that |build_func| was
    called successfully on."""
    successes = []
    logs.info('Concurrent builds: %d.', num_concurrent_builds)
    with mp_pool.ThreadPool(num_concurrent_builds) as pool:
        for _ in range(NUM_BUILD_RETRIES):
            logs.info('Building using (%s): %s', build_func, inputs)
            results = pool.starmap(build_func, inputs)
            curr_successes, curr_failures = split_successes_and_failures(
                inputs, results)

            logs.info('Build successes: %s', curr_successes)
            successes.extend(curr_successes)
            if not curr_failures:
                break

            logs.error('Build failures: %s', curr_failures)
            inputs = curr_failures
            sleep_interval = random.uniform(1, BUILD_FAIL_WAIT)
            logs.info('Sleeping for %d secs before retrying.', sleep_interval)
            time.sleep(sleep_interval)

    return successes


def build_fuzzer_benchmark(fuzzer: str, benchmark: str) -> bool:
    """Wrapper around buildlib.build_fuzzer_benchmark that logs and catches
    exceptions. buildlib.build_fuzzer_benchmark builds an image for |fuzzer|
    to fuzz |benchmark|."""
    logger.info('Building benchmark: %s, fuzzer: %s.', benchmark, fuzzer)
    try:
        buildlib.build_fuzzer_benchmark(fuzzer, benchmark)
    except subprocess.CalledProcessError:
        logger.error('Failed to build benchmark: %s, fuzzer: %s.', benchmark,
                     fuzzer)
        return False
    logs.info('Done building benchmark: %s, fuzzer: %s.', benchmark, fuzzer)
    return True


def build_all_fuzzer_benchmarks(
        fuzzers: List[str],
        benchmarks: List[str],
        num_concurrent_builds: int = DEFAULT_MAX_CONCURRENT_BUILDS
) -> List[str]:
    """Build fuzzer,benchmark images for all pairs of |fuzzers| and |benchmarks|
    in parallel. Returns a list of fuzzer,benchmark pairs that built
    successfully."""
    logger.info('Building all fuzzer benchmarks.')
    build_fuzzer_benchmark_args = get_fuzzer_benchmark_pairs(
        fuzzers, benchmarks)

    # TODO(metzman): Use an asynchronous unordered map variant to schedule
    # eagerly.
    successful_calls = retry_build_loop(build_fuzzer_benchmark,
                                        build_fuzzer_benchmark_args,
                                        num_concurrent_builds)
    logger.info('Done building fuzzer benchmarks.')
    return successful_calls


def main():
    """Build fuzzer, benchmark pairs on Google Cloud Build."""
    parser = argparse.ArgumentParser(
        description='Build fuzzer, benchmark pairs on Google Cloud Build.')

    parser.add_argument('-b',
                        '--benchmarks',
                        help='Benchmark names.',
                        nargs='+',
                        required=True)

    parser.add_argument('-f',
                        '--fuzzers',
                        help='Fuzzer names.',
                        nargs='+',
                        required=True)

    parser.add_argument('-n',
                        '--num-concurrent-builds',
                        help='Max concurrent builds allowed.',
                        type=int,
                        default=DEFAULT_MAX_CONCURRENT_BUILDS,
                        required=False)

    logs.initialize()
    args = parser.parse_args()

    build_all_fuzzer_benchmarks(args.fuzzers, args.benchmarks,
                                args.num_concurrent_builds)

    return 0


if __name__ == '__main__':
    sys.exit(main())
