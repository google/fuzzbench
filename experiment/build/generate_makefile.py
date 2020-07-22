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

from experiment.build import docker_images
from common import yaml_utils
import argparse
import os

BASE_TAG = "gcr.io/fuzzbench"
BENCHMARKS_DIR = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, 'benchmarks')
FUZZERS_DIR = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, 'fuzzers')

RUN_TARGET_TEMPLATE = """
run-{fuzzer}-{benchmark}: {fuzzer}-{benchmark}-{oss_fuzz_string}runner
\tdocker run \\
\t--cpus=1 \\
\t--cap-add SYS_NICE \\
\t--cap-add SYS_PTRACE \\
\t-e FORCE_LOCAL=1 \\
\t-e FUZZ_OUTSIDE_EXPERIMENT=1 \\
\t-e TRIAL_ID=1 \\
\t-e FUZZER={fuzzer} \\
\t-e BENCHMARK={benchmark} \\{oss_fuzz_env_var}
\t-it {base_tag}/runners/{fuzzer}/{benchmark}

test-run-{fuzzer}-{benchmark}: {fuzzer}-{benchmark}-{oss_fuzz_string}runner
\tdocker run \\
\t--cap-add SYS_NICE \\
\t--cap-add SYS_PTRACE \\
\t-e FORCE_LOCAL=1 \\
\t-e FUZZ_OUTSIDE_EXPERIMENT=1 \\
\t-e TRIAL_ID=1 \\
\t-e FUZZER={fuzzer} \\
\t-e BENCHMARK={benchmark} \\{oss_fuzz_env_var}
\t-e MAX_TOTAL_TIME=20 \\
\t-e SNAPSHOT_PERIOD=10 \\
\t{base_tag}/runners/{fuzzer}/{benchmark}

debug-{fuzzer}-{benchmark}: {fuzzer}-{benchmark}-{oss_fuzz_string}runner
\tdocker run \\
\t--cpus=1 \\
\t--cap-add SYS_NICE \\
\t--cap-add SYS_PTRACE \\
\t-e FORCE_LOCAL=1 \\
\t-e FUZZ_OUTSIDE_EXPERIMENT=1 \\
\t-e TRIAL_ID=1 \\
\t-e FUZZER={fuzzer} \\
\t-e BENCHMARK={benchmark} \\{oss_fuzz_env_var}
\t--entrypoint "/bin/bash" \\
\t-it {base_tag}/runners/{fuzzer}/{benchmark}
"""


def print_makefile_run_template(fuzzers, benchmarks, oss_fuzz_benchmarks):
    # build fuzzer benchmark
    for fuzzer in fuzzers:
        image_type = "runner"
        if fuzzer == "coverage" or fuzzer == "coverage-source-based":
            image_type = "builder"
        for benchmark in benchmarks:
            print('build-{fuzzer}-{benchmark}: {fuzzer}-{benchmark}-{image_type}\n'.format(fuzzer=fuzzer, benchmark=benchmark, image_type=image_type))
        for benchmark in oss_fuzz_benchmarks:
            print('build-{fuzzer}-{benchmark}: {fuzzer}-{benchmark}-oss-fuzz-{image_type}\n'.format(fuzzer=fuzzer, benchmark=benchmark, image_type=image_type))
    
    print()
    for fuzzer in fuzzers:
        if fuzzer == "coverage" or fuzzer == "coverage-source-based":
            continue
        for benchmark in benchmarks:
            print(RUN_TARGET_TEMPLATE.format(
                    fuzzer=fuzzer, benchmark=benchmark, oss_fuzz_string="",
                    oss_fuzz_env_var="", base_tag="gcr.io/fuzzbench"
            ))
            print()
        for benchmark in oss_fuzz_benchmarks:
            print(RUN_TARGET_TEMPLATE.format(
                    fuzzer=fuzzer, benchmark=benchmark, oss_fuzz_string="oss-fuzz-",
                    oss_fuzz_env_var="\n\t-e FUZZ_TARGET=$(" + benchmark + "-fuzz-target) \\",
                    base_tag=BASE_TAG
            ))
            print()
    # print("endif\n")
    

def print_oss_fuzz_benchmark_definition(oss_fuzz_benchmarks):
    for benchmark in oss_fuzz_benchmarks:
        oss_fuzz_yaml = yaml_utils.read(os.path.join(BENCHMARKS_DIR, benchmark, 'oss-fuzz.yaml'))
        print(benchmark + '-project-name=' + oss_fuzz_yaml['project'])
        print(benchmark + '-fuzz-target=' + oss_fuzz_yaml['fuzz_target'])
        if not oss_fuzz_yaml['commit']:
            oss_fuzz_yaml['commit'] = ""
        print(benchmark + '-commit=' + oss_fuzz_yaml['commit'])
        print("{benchmark}-project-builder:".format(benchmark=benchmark))
        print('\tdocker build \\')
        print('\t--tag {base_tag}/builders/oss-fuzz/{benchmark} \\'.format(benchmark=benchmark, base_tag=BASE_TAG))
        print('\t--file benchmarks/{benchmark}/Dockerfile \\'.format(benchmark=benchmark))
        print('\t--cache-from {base_tag}/builders/oss-fuzz/{benchmark} \\'.format(benchmark=benchmark, base_tag=BASE_TAG))
        print('\t--build-arg BUILDKIT_INLINE_CACHE=1 \\')
        print('\tbenchmarks/{benchmark}'.format(benchmark=benchmark)) # Remove this
        # print('\tbenchmarks/{benchmark} && \\'.format(benchmark=benchmark))
        #print('\tdocker push {base_tag}/builders/oss-fuzz/{benchmark} \\'.format(benchmark=benchmark, base_tag=BASE_TAG))
        print()

def get_fuzzers_and_benchmarks():
    fuzzers = []
    benchmarks = []
    oss_fuzz_benchmarks = []

    for benchmark in os.listdir(BENCHMARKS_DIR):
        benchmark_path = os.path.join(BENCHMARKS_DIR, benchmark)
        if not os.path.isdir(benchmark_path):
            continue
        if os.path.exists(os.path.join(benchmark_path, 'oss-fuzz.yaml')):
            oss_fuzz_benchmarks.append(benchmark)
        elif os.path.exists(os.path.join(benchmark_path, 'build.sh')):
            benchmarks.append(benchmark)

    for fuzzer in os.listdir(FUZZERS_DIR):
        fuzzer_dir = os.path.join(FUZZERS_DIR, fuzzer)
        if not os.path.isdir(fuzzer_dir):
            continue
        fuzzers.append(fuzzer)

    return fuzzers, benchmarks, oss_fuzz_benchmarks


# TODO(Tanq16): Add unit test for this.
def print_makefile(name, image):
    """Prints the generated makefile to stdout."""
    print(name + ':', end='')
    if 'depends_on' in image:
        for dep in image['depends_on']:
            print(' ' + dep, end='')
    print()
    print('\tdocker build \\')
    print('\t--tag ' + image['tag'] + ' \\')
    print('\t--build-arg BUILDKIT_INLINE_CACHE=1 \\')
    if 'build_arg' in image:
        for arg in image['build_arg']:
            print('\t--build-arg ' + arg + ' \\')
    if 'dockerfile' in image:
        print('\t--file ' + image['dockerfile'] + ' \\')
    print('\t--cache-from ' + BASE_TAG + '/' + image['tag'] + ' \\')
    print('\t' + image['context']) # + ' && \\')
    #print('\tdocker push ' + BASE_TAG + '/' + image['tag'])
    print()


def main():
    """Generates Makefile with docker image build rules."""
    # parser = argparse.ArgumentParser(
    #     description='Makefile build rule generator.')
    # parser.add_argument('-r',
    #                     '--docker-registry',
    #                     default='gcr.io/fuzzbench',
    #                     help='Docker registry to use as cache.')
    # args = parser.parse_args()
    # BASE_TAG = args.docker_registry

    fuzzers, benchmarks, oss_fuzz_benchmarks = get_fuzzers_and_benchmarks()

    buildable_images = docker_images.get_images_to_build(fuzzers, benchmarks)
    buildable_images_oss_fuzz = docker_images.get_images_to_build(fuzzers, oss_fuzz_benchmarks, oss_fuzz=True, skip_base=True)
    all_benchmarks = benchmarks + oss_fuzz_benchmarks
    
    # Remove coverage runners.
    for benchmark in benchmarks:
        del buildable_images['coverage-{benchmark}-intermediate-runner'.format(benchmark=benchmark)]
        del buildable_images['coverage-{benchmark}-runner'.format(benchmark=benchmark)]
        # del buildable_images['coverage_source_based-{benchmark}-intermediate-runner'.format(benchmark=benchmark)]
        # del buildable_images['coverage_source_based-{benchmark}-runner'.format(benchmark=benchmark)]
    for benchmark in oss_fuzz_benchmarks:
        del buildable_images_oss_fuzz['coverage-{benchmark}-oss-fuzz-intermediate-runner'.format(benchmark=benchmark)]
        del buildable_images_oss_fuzz['coverage-{benchmark}-oss-fuzz-runner'.format(benchmark=benchmark)]
        # del buildable_images['coverage_source_based-{benchmark}-oss-fuzz-intermediate-runner'.format(benchmark=benchmark)]
        # del buildable_images['coverage_source_based-{benchmark}-oss-fuzz-runner'.format(benchmark=benchmark)]

    print('export DOCKER_BUILDKIT := 1')
    # print('cache_from = $(if ${RUNNING_ON_CI},--cache-from {fuzzer},)')
    print_oss_fuzz_benchmark_definition(oss_fuzz_benchmarks)
    
    for name, image in buildable_images.items():
        print_makefile(name, image)
    for name, image in buildable_images_oss_fuzz.items():
        print_makefile(name, image)

    print_makefile_run_template(fuzzers, benchmarks, oss_fuzz_benchmarks)

    for fuzzer in fuzzers:
        all_build_targets = ' '.join([
            'build-{0}-{1}'.format(fuzzer, benchmark)
            for benchmark in all_benchmarks
        ])
        print('build-{fuzzer}-all: {all_targets}'.format(
            fuzzer=fuzzer, all_targets=all_build_targets))
    
    all_build_targets = ' '.join(
        ['build-{0}-all'.format(name) for name in fuzzers])
    print('build-all: {all_targets}'.format(all_targets=all_build_targets))
    

if __name__ == '__main__':
    main()
