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
"""Tests for generate_makefile.py."""

from docker import generate_makefile


def test_get_rules_for_image():
    """Tests result of a makefile generation for an image."""

    name = 'afl-zlib-builder-intermediate'
    image = {
        'tag': 'builders/afl/zlib-intermediate',
        'context': 'fuzzers/afl',
        'dockerfile': 'fuzzers/afl/builder.Dockerfile',
        'depends_on': ['zlib-project-builder'],
        'build_arg': ['parent_image=gcr.io/fuzzbench/builders/benchmark/zlib']
    }

    rules_for_image = generate_makefile.get_rules_for_image(name, image)
    assert rules_for_image == (
        '.afl-zlib-builder-intermediate: .zlib-project-builder\n'
        '\tdocker build \\\n'
        '\t--tag gcr.io/fuzzbench/builders/afl/zlib-intermediate \\\n'
        '\t--build-arg BUILDKIT_INLINE_CACHE=1 \\\n'
        '\t--cache-from gcr.io/fuzzbench/builders/afl/zlib-intermediate \\\n'
        '\t--build-arg parent_image=gcr.io/fuzzbench/builders/benchmark/zlib \\'
        '\n'
        '\t--file fuzzers/afl/builder.Dockerfile \\\n'
        '\tfuzzers/afl\n'
        '\n')


def test_get_rules_for_runner_image():
    """Tests result of a makefile generation for a runner image."""

    name = 'afl-zlib-runner'
    image = {
        'tag': 'runners/afl/zlib',
        'fuzzer': 'afl',
        'benchmark': 'zlib',
        'context': '.',
        'dockerfile': 'docker/benchmark-runner/Dockerfile',
        'build_arg': ['fuzzer=afl', 'benchmark=zlib'],
        'depends_on': ['afl-zlib-builder', 'afl-zlib-intermediate-runner']
    }
    rules_for_image = generate_makefile.get_rules_for_image(name, image)
    assert rules_for_image == (
        '.afl-zlib-runner: .afl-zlib-builder .afl-zlib-intermediate-runner\n'
        '\tdocker build \\\n'
        '\t--tag gcr.io/fuzzbench/runners/afl/zlib \\\n'
        '\t--build-arg BUILDKIT_INLINE_CACHE=1 \\\n'
        '\t--cache-from gcr.io/fuzzbench/runners/afl/zlib \\\n'
        '\t--build-arg fuzzer=afl \\\n'
        '\t--build-arg benchmark=zlib \\\n'
        '\t--file docker/benchmark-runner/Dockerfile \\\n'
        '\t.\n\n'
        'run-afl-zlib: .afl-zlib-runner\n' + ('\
\tdocker run \\\n\
\t--cpus=1 \\\n\
\t--cap-add SYS_NICE \\\n\
\t--cap-add SYS_PTRACE \\\n\
\t-e FUZZ_OUTSIDE_EXPERIMENT=1 \\\n\
\t-e FORCE_LOCAL=1 \\\n\
\t-e TRIAL_ID=1 \\\n\
\t-e FUZZER=afl \\\n\
\t-e BENCHMARK=zlib \\\n\
\t-e FUZZ_TARGET=$(zlib-fuzz-target) \\\
\n') + '\t-it gcr.io/fuzzbench/runners/afl/zlib\n\n'
        'debug-afl-zlib: .afl-zlib-runner\n' + ('\
\tdocker run \\\n\
\t--cpus=1 \\\n\
\t--cap-add SYS_NICE \\\n\
\t--cap-add SYS_PTRACE \\\n\
\t-e FUZZ_OUTSIDE_EXPERIMENT=1 \\\n\
\t-e FORCE_LOCAL=1 \\\n\
\t-e TRIAL_ID=1 \\\n\
\t-e FUZZER=afl \\\n\
\t-e BENCHMARK=zlib \\\n\
\t-e FUZZ_TARGET=$(zlib-fuzz-target) \\\
\n') + '\t--entrypoint "/bin/bash" \\\n\t-it gcr.io/fuzzbench/runners/afl/zlib'
        '\n\n'
        'test-run-afl-zlib: .afl-zlib-runner\n' + ('\
\tdocker run \\\n\
\t--cpus=1 \\\n\
\t--cap-add SYS_NICE \\\n\
\t--cap-add SYS_PTRACE \\\n\
\t-e FUZZ_OUTSIDE_EXPERIMENT=1 \\\n\
\t-e FORCE_LOCAL=1 \\\n\
\t-e TRIAL_ID=1 \\\n\
\t-e FUZZER=afl \\\n\
\t-e BENCHMARK=zlib \\\n\
\t-e FUZZ_TARGET=$(zlib-fuzz-target) \\\
\n') + '\t-e MAX_TOTAL_TIME=20 \\\n\t-e SNAPSHOT_PERIOD=10 \\\n'
        '\tgcr.io/fuzzbench/runners/afl/zlib'
        '\n\n'
        'debug-builder-afl-zlib: .afl-zlib-builder-debug\n' + ('\
\tdocker run \\\n\
\t--cpus=1 \\\n\
\t--cap-add SYS_NICE \\\n\
\t--cap-add SYS_PTRACE \\\n\
\t-e FUZZ_OUTSIDE_EXPERIMENT=1 \\\n\
\t-e FORCE_LOCAL=1 \\\n\
\t-e TRIAL_ID=1 \\\n\
\t-e FUZZER=afl \\\n\
\t-e BENCHMARK=zlib \\\n\
\t-e FUZZ_TARGET=$(zlib-fuzz-target) \\\n\
\t-e DEBUG_BUILDER=1 \\\n\
\t--entrypoint "/bin/bash" \\\
\n') + '\t-it gcr.io/fuzzbench/builders/afl/zlib\n\n')
