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
"""Generates Makefile containing docker image targets."""

import os
from experiment.build import docker_images
from common import yaml_utils

BASE_TAG = "gcr.io/fuzzbench"
BENCHMARK_DIR = os.path.join(os.path.dirname(__file__), os.pardir, 'benchmarks')

RUN_TEMPLATE = """
{run_type}-{fuzzer}-{benchmark}: .{fuzzer}-{benchmark}-runner
\tdocker run \\
\t--cpus=1 \\
\t--cap-add SYS_NICE \\
\t--cap-add SYS_PTRACE \\
\t-e FUZZ_OUTSIDE_EXPERIMENT=1 \\
\t-e FORCE_LOCAL=1 \\
\t-e TRIAL_ID=1 \\
\t-e FUZZER={fuzzer} \\
\t-e BENCHMARK={benchmark} \\"""


def print_benchmark_definition(benchmarks):
    """Prints benchmark variables from benchmark.yaml files."""
    for benchmark in benchmarks:
        benchmark_vars = yaml_utils.read(
            os.path.join(BENCHMARK_DIR, benchmark, 'benchmark.yaml'))
        print(benchmark + '-fuzz-target=' + benchmark_vars['fuzz_target'])
        if not 'commit' in benchmark_vars.keys():
            benchmark_vars['commit'] = ""
        if not benchmark_vars['commit']:
            benchmark_vars['commit'] = ""
        print(benchmark + '-commit=' + benchmark_vars['commit'])
        print()


def _print_makefile_build_template(name, image):
    if not ('base' in name or 'dispatcher' in name):
        print('.', end='')
    print(name + ':', end='')
    if 'depends_on' in image:
        for dep in image['depends_on']:
            if 'base' in dep:
                print(' ' + dep, end='')
            else:
                print(' .' + dep, end='')
    print()
    print('\tdocker build \\')
    print('\t--tag ' + BASE_TAG + '/' + image['tag'] + ' \\')
    print('\t--build-arg BUILDKIT_INLINE_CACHE=1 \\')
    print('\t--cache-from ' + BASE_TAG + '/' + image['tag'] + ' \\')
    if name == 'base-builder':
        print('\t--cache-from ' + 'gcr.io/oss-fuzz-base/base-clang \\')
    if 'build_arg' in image:
        for arg in image['build_arg']:
            print('\t--build-arg ' + arg + ' \\')
    if 'dockerfile' in image:
        print('\t--file ' + image['dockerfile'] + ' \\')
    print('\t' + image['context'])
    print()


def _print_makefile_run_template(image):
    fuzzer, benchmark = image['tag'].split('/')[1:]

    for run_type in ('run', 'debug', 'test-run'):
        print(
            RUN_TEMPLATE.format(run_type=run_type,
                                benchmark=benchmark,
                                fuzzer=fuzzer))
        print('\t-e FUZZ_TARGET=$({benchmark}-fuzz-target) \\'.format(
            benchmark=benchmark))
        if run_type == 'test-run':
            print('\t-e MAX_TOTAL_TIME=20 \\\n\t-e SNAPSHOT_PERIOD=10 \\')
        if run_type == 'debug':
            print('\t-entrypoint "/bin/bash" \\\n\t-it ', end='')
        else:
            print('\t', end='')
        print(BASE_TAG + '/' + image['tag'])
        print()


def print_makefile(name, image):
    """Print makefile section for given image to stdout."""
    _print_makefile_build_template(name, image)
    if 'runner' in name and not ('intermediate' in name or 'base' in name):
        _print_makefile_run_template(image)


def main():
    """Generates Makefile with docker image build rules."""
    fuzzers, benchmarks = docker_images.get_fuzzers_and_benchmarks()
    buildable_images = docker_images.get_images_to_build(fuzzers, benchmarks)

    print('export DOCKER_BUILDKIT := 1')

    # Print oss-fuzz benchmarks property variables.
    print_benchmark_definition(benchmarks)

    for name, image in buildable_images.items():
        print_makefile(name, image)

    # Print build targets for all fuzzer-benchmark pairs.
    for fuzzer in fuzzers:
        image_type = "runner"
        if fuzzer in ('coverage', 'coverage_source_based'):
            image_type = "builder"
        for benchmark in benchmarks:
            print(('build-{fuzzer}-{benchmark}: ' +
                   '.{fuzzer}-{benchmark}-{image_type}\n').format(
                       fuzzer=fuzzer,
                       benchmark=benchmark,
                       image_type=image_type))
        print()

    # Print fuzzer-all benchmarks build targets.
    for fuzzer in fuzzers:
        all_build_targets = ' '.join([
            'build-{0}-{1}'.format(fuzzer, benchmark)
            for benchmark in benchmarks
        ])
        print('build-{fuzzer}-all: {all_targets}'.format(
            fuzzer=fuzzer, all_targets=all_build_targets))

    # Print all targets build target.
    all_build_targets = ' '.join(
        ['build-{0}-all'.format(name) for name in fuzzers])
    print('build-all: {all_targets}'.format(all_targets=all_build_targets))


if __name__ == '__main__':
    main()
