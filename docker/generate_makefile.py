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
"""Simple generator for local Makefile rules."""

import os
import sys

from common import yaml_utils
from common import benchmark_utils
from common import fuzzer_utils
from experiment.build import docker_images

BASE_TAG = "gcr.io/fuzzbench"
BENCHMARK_DIR = benchmark_utils.BENCHMARKS_DIR


def _get_benchmark_fuzz_target(benchmarks):
    """Returns benchmark variables from benchmark.yaml files."""
    variables = ''
    for benchmark in benchmarks:
        benchmark_vars = yaml_utils.read(
            os.path.join(BENCHMARK_DIR, benchmark, 'benchmark.yaml'))
        variables += (benchmark + '-fuzz-target=' +
                      benchmark_vars['fuzz_target'] + '\n')
        variables += '\n'
    return variables


def _get_makefile_run_template(image):
    fuzzer = image['fuzzer']
    benchmark = image['benchmark']
    section = ''

    for run_type in ('run', 'debug', 'test-run'):
        section += (
            f'{run_type}-{fuzzer}-{benchmark}: .{fuzzer}-{benchmark}-runner')

        section += '\
\tdocker run \\\n\
\t--cpus=1 \\\n\
\t--cap-add SYS_NICE \\\n\
\t--cap-add SYS_PTRACE \\\n\
\t-e FUZZ_OUTSIDE_EXPERIMENT=1 \\\n\
\t-e FORCE_LOCAL=1 \\\n\
\t-e TRIAL_ID=1 \\\n\
\t-e FUZZER={fuzzer} \\\n\
\t-e BENCHMARK={benchmark} \\\n\
\t-e FUZZ_TARGET=$({benchmark}-fuzz-target) \\\
\n'.format(fuzzer=fuzzer, benchmark=benchmark)

        if run_type == 'test-run':
            section += '\t-e MAX_TOTAL_TIME=20 \\\n\t-e SNAPSHOT_PERIOD=10 \\\n'
        if run_type == 'debug':
            section += '\t--entrypoint "/bin/bash" \\\n\t-it '
        elif run_type == 'run':
            section += '\t-it '
        else:
            section += '\t'

        section += os.path.join(BASE_TAG, image['tag'])
        section += '\n\n'
    return section


def get_rules_for_image(name, image):
    """Returns makefile section for |image|."""
    if not ('base-' in name or 'dispatcher-' in name):
        section = '.'
    else:
        section = ''
    section += name + ':'
    if 'depends_on' in image:
        for dep in image['depends_on']:
            if 'base' in dep:
                section += ' ' + dep
            else:
                section += ' .' + dep
    section += '\n'
    if 'base-' in name:
        section += '\tdocker pull ubuntu:xenial\n'
    section += '\tdocker build \\\n'
    section += '\t--tag ' + os.path.join(BASE_TAG, image['tag']) + ' \\\n'
    section += '\t--build-arg BUILDKIT_INLINE_CACHE=1 \\\n'
    section += ('\t--cache-from ' + os.path.join(BASE_TAG, image['tag']) +
                ' \\\n')

    if 'build_arg' in image:
        for arg in image['build_arg']:
            section += '\t--build-arg ' + arg + ' \\\n'
    if 'dockerfile' in image:
        section += '\t--file ' + image['dockerfile'] + ' \\\n'
    section += '\t' + image['context'] + '\n'
    section += '\n'

    # Print run, debug, test-run rules if image is a runner.
    if 'runner' in name and not ('intermediate' in name or 'base' in name):
        section += _get_makefile_run_template(image)
    return section


def main():
    """Writes Makefile with docker image build rules to sys.argv[1]."""
    if len(sys.argv) != 2:
        print(f'Usage: {sys.argv[0]} <makefile>')
        return 1
    makefile_path = sys.argv[1]
    makefile_contents = generate_makefile()
    with open(makefile_path, 'w') as file_handle:
        file_handle.write(makefile_contents)
    return 0

def generate_makefile():
    fuzzers = fuzzer_utils.get_fuzzer_names()
    benchmarks = benchmark_utils.get_all_benchmarks()
    buildable_images = docker_images.get_images_to_build(fuzzers, benchmarks)

    makefile = 'export DOCKER_BUILDKIT := 1\n'

    # Print oss-fuzz benchmarks property variables.
    makefile += _get_benchmark_fuzz_target(benchmarks)

    for name, image in buildable_images.items():
        makefile += get_rules_for_image(name, image)

    # Print build targets for all fuzzer-benchmark pairs (including coverage).
    fuzzers.append('coverage')
    for fuzzer in fuzzers:
        image_type = 'runner'
        if 'coverage' in fuzzer:
            image_type = 'builder'
        for benchmark in benchmarks:
            makefile += ('build-{fuzzer}-{benchmark}: ' +
                         '.{fuzzer}-{benchmark}-{image_type}\n').format(
                             fuzzer=fuzzer,
                             benchmark=benchmark,
                             image_type=image_type)
        makefile += '\n'

    # Print fuzzer-all benchmarks build targets.
    for fuzzer in fuzzers:
        all_build_targets = ' '.join([
            'build-{0}-{1}'.format(fuzzer, benchmark)
            for benchmark in benchmarks
        ])
        makefile += 'build-{fuzzer}-all: {all_targets}\n'.format(
            fuzzer=fuzzer, all_targets=all_build_targets)
        all_test_run_targets = ' '.join([
            'test-run-{0}-{1}'.format(fuzzer, benchmark)
            for benchmark in benchmarks
        ])
        makefile += 'test-run-{fuzzer}-all: {all_targets}\n'.format(
            fuzzer=fuzzer, all_targets=all_test_run_targets)

    # Print all targets build target.
    all_build_targets = ' '.join(
        ['build-{0}-all'.format(name) for name in fuzzers])
    makefile += 'build-all: {all_targets}'.format(all_targets=all_build_targets)
    return makefile


if __name__ == '__main__':
    sys.exit(main())
