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

from unittest.mock import call
from unittest.mock import patch

from docker import generate_makefile


@patch('builtins.print')
def test_print_makefile_build(mocked_print):
    """Tests result of a makefile generation for an image."""

    name = 'afl-zlib-builder-intermediate'
    image = {
        'tag': 'builders/afl/zlib-intermediate',
        'context': 'fuzzers/afl',
        'dockerfile': 'fuzzers/afl/builder.Dockerfile',
        'depends_on': ['zlib-project-builder'],
        'build_arg': ['parent_image=gcr.io/fuzzbench/builders/benchmark/zlib']
    }

    generate_makefile.print_rules_for_image(name, image)
    assert mocked_print.mock_calls == [
        call('.', end=''),
        call('afl-zlib-builder-intermediate:', end=''),
        call(' .zlib-project-builder', end=''),
        call(),
        call('\tdocker build \\'),
        call('\t--tag gcr.io/fuzzbench/builders/afl/zlib-intermediate \\'),
        call('\t--build-arg BUILDKIT_INLINE_CACHE=1 \\'),
        call('\t--cache-from gcr.io/fuzzbench/builders/afl/zlib-intermediate \\'
            ),
        call('\t--build-arg parent_image=gcr.io/' +
             'fuzzbench/builders/benchmark/zlib \\'),
        call('\t--file fuzzers/afl/builder.Dockerfile \\'),
        call('\tfuzzers/afl'),
        call()
    ]


@patch('builtins.print')
def test_print_makefile_runner_image(mocked_print):
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

    generate_makefile.print_rules_for_image(name, image)

    assert mocked_print.mock_calls == [
        call('.', end=''),
        call('afl-zlib-runner:', end=''),
        call(' .afl-zlib-builder', end=''),
        call(' .afl-zlib-intermediate-runner', end=''),
        call(),
        call('\tdocker build \\'),
        call('\t--tag gcr.io/fuzzbench/runners/afl/zlib \\'),
        call('\t--build-arg BUILDKIT_INLINE_CACHE=1 \\'),
        call('\t--cache-from gcr.io/fuzzbench/runners/afl/zlib \\'),
        call('\t--build-arg fuzzer=afl \\'),
        call('\t--build-arg benchmark=zlib \\'),
        call('\t--file docker/benchmark-runner/Dockerfile \\'),
        call('\t.'),
        call(),
        call('run-afl-zlib: .afl-zlib-runner'),
        call('\
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
'),
        call('\t', end=''),
        call('gcr.io/fuzzbench/runners/afl/zlib'),
        call(),
        call('debug-afl-zlib: .afl-zlib-runner'),
        call('\
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
'),
        call('\t--entrypoint "/bin/bash" \\\n\t-it ', end=''),
        call('gcr.io/fuzzbench/runners/afl/zlib'),
        call(),
        call('test-run-afl-zlib: .afl-zlib-runner'),
        call('\
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
'),
        call('\t-e MAX_TOTAL_TIME=20 \\\n\t-e SNAPSHOT_PERIOD=10 \\'),
        call('\t-it ', end=''),
        call('gcr.io/fuzzbench/runners/afl/zlib'),
        call()
    ]
