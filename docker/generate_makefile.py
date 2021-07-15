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

    run_types = ['run', 'debug', 'test-run', 'debug-builder']
    testcases_dir = os.path.join(BENCHMARK_DIR, benchmark, 'testcases')
    if os.path.exists(testcases_dir):
        run_types.append('repro-bugs')

    for run_type in run_types:
        if run_type == 'debug-builder':
            section += f'{run_type}-{fuzzer}-{benchmark}: '
            section += f'.{fuzzer}-{benchmark}-builder-debug\n'
        else:
            section += f'{run_type}-{fuzzer}-{benchmark}: '
            section += f'.{fuzzer}-{benchmark}-runner\n'

        section += f'\
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
\n'

        if run_type == 'test-run':
            section += '\t-e MAX_TOTAL_TIME=20 \\\n\t-e SNAPSHOT_PERIOD=10 \\\n'
        if run_type == 'debug-builder':
            section += '\t-e DEBUG_BUILDER=1 \\\n'
            section += '\t--entrypoint "/bin/bash" \\\n\t-it '
        elif run_type == 'debug':
            section += '\t--entrypoint "/bin/bash" \\\n\t-it '
        elif run_type == 'repro-bugs':
            section += f'\t-v {testcases_dir}:/testcases \\\n\t'
            section += '--entrypoint /bin/bash '
            section += os.path.join(BASE_TAG, image['tag'])
            section += ' -c "for f in /testcases/*; do '
            section += 'echo _________________________________________; '
            section += 'echo \\$$f:; '
            section += '\\$$OUT/\\$$FUZZ_TARGET -timeout=25 -rss_limit_mb=2560 '
            section += '\\$$f; done;" '
            section += '\n\n'
            continue
        elif run_type == 'run':
            section += '\t-it '
        else:
            section += '\t'

        if run_type != 'debug-builder':
            section += os.path.join(BASE_TAG, image['tag'])
        else:
            section += os.path.join(
                BASE_TAG, image['tag'].replace('runners/', 'builders/', 1))
        section += '\n\n'
    return section


def get_rules_for_image(name, image):
    """Returns makefile section for |image|."""
    if not ('base-' in name or 'dispatcher-' in name or name == 'worker'):
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

    # Print run, debug, test-run and debug-builder rules if image is a runner.
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
    """Generates the contents of the makefile and returns it."""
    fuzzers = fuzzer_utils.get_fuzzer_names()
    benchmarks = benchmark_utils.get_all_benchmarks()
    buildable_images = docker_images.get_images_to_build(fuzzers, benchmarks)

    makefile = 'export DOCKER_BUILDKIT := 1\n\n'

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
            makefile += (f'build-{fuzzer}-{benchmark}: ' +
                         f'.{fuzzer}-{benchmark}-{image_type}\n')
        makefile += '\n'

    # Print fuzzer-all benchmarks build targets.
    for fuzzer in fuzzers:
        all_build_targets = ' '.join(
            [f'build-{fuzzer}-{benchmark}' for benchmark in benchmarks])
        makefile += f'build-{fuzzer}-all: {all_build_targets}\n'
        all_test_run_targets = ' '.join(
            [f'test-run-{fuzzer}-{benchmark}' for benchmark in benchmarks])
        makefile += f'test-run-{fuzzer}-all: {all_test_run_targets}\n'

    # Print all targets build target.
    all_build_targets = ' '.join([f'build-{fuzzer}-all' for fuzzer in fuzzers])
    makefile += f'build-all: {all_build_targets}'
    return makefile


if __name__ == '__main__':
    sys.exit(main())
