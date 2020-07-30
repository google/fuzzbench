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
"""Generate Makefile test."""

import io
import sys

from docker import generate_makefile


def test_print_makefile_build():
    """Tests result of a makefile generation for an image."""

    name = 'afl-zlib-builder-intermediate'
    image = {
        'tag': 'builders/afl/zlib-intermediate',
        'context': 'fuzzers/afl',
        'dockerfile': 'fuzzers/afl/builder.Dockerfile',
        'depends_on': ['zlib-project-builder'],
        'build_arg': ['parent_image=gcr.io/fuzzbench/builders/benchmark/zlib']
    }

    generated_makefile_truth = """\
.afl-zlib-builder-intermediate: .zlib-project-builder
\tdocker build \\
\t--tag gcr.io/fuzzbench/builders/afl/zlib-intermediate \\
\t--build-arg BUILDKIT_INLINE_CACHE=1 \\
\t--cache-from gcr.io/fuzzbench/builders/afl/zlib-intermediate \\
\t--build-arg parent_image=gcr.io/fuzzbench/builders/benchmark/zlib \\
\t--file fuzzers/afl/builder.Dockerfile \\
\tfuzzers/afl

"""

    stdout = sys.stdout
    print_output = io.StringIO()
    sys.stdout = print_output

    generate_makefile.print_rules_for_image(name, image)
    result = print_output.getvalue()
    sys.stdout = stdout

    assert result == generated_makefile_truth


def test_print_makefile_runner_image():
    """Tests result of a makefile generation for a runner image."""

    name = 'afl-zlib-runner'
    image = {
        'tag': 'runners/afl/zlib',
        'context': '.',
        'dockerfile': 'docker/benchmark-runner/Dockerfile',
        'build_arg': ['fuzzer=afl', 'benchmark=zlib'],
        'depends_on': ['afl-zlib-builder', 'afl-zlib-intermediate-runner']
    }

    generated_makefile_truth = """\
.afl-zlib-runner: .afl-zlib-builder .afl-zlib-intermediate-runner
\tdocker build \\
\t--tag gcr.io/fuzzbench/runners/afl/zlib \\
\t--build-arg BUILDKIT_INLINE_CACHE=1 \\
\t--cache-from gcr.io/fuzzbench/runners/afl/zlib \\
\t--build-arg fuzzer=afl \\
\t--build-arg benchmark=zlib \\
\t--file docker/benchmark-runner/Dockerfile \\
\t.

run-afl-zlib: .afl-zlib-runner
\tdocker run \\
\t--cpus=1 \\
\t--cap-add SYS_NICE \\
\t--cap-add SYS_PTRACE \\
\t-e FUZZ_OUTSIDE_EXPERIMENT=1 \\
\t-e FORCE_LOCAL=1 \\
\t-e TRIAL_ID=1 \\
\t-e FUZZER=afl \\
\t-e BENCHMARK=zlib \\
\t-e FUZZ_TARGET=$(zlib-fuzz-target) \\
\tgcr.io/fuzzbench/runners/afl/zlib

debug-afl-zlib: .afl-zlib-runner
\tdocker run \\
\t--cpus=1 \\
\t--cap-add SYS_NICE \\
\t--cap-add SYS_PTRACE \\
\t-e FUZZ_OUTSIDE_EXPERIMENT=1 \\
\t-e FORCE_LOCAL=1 \\
\t-e TRIAL_ID=1 \\
\t-e FUZZER=afl \\
\t-e BENCHMARK=zlib \\
\t-e FUZZ_TARGET=$(zlib-fuzz-target) \\
\t-entrypoint "/bin/bash" \\
\t-it gcr.io/fuzzbench/runners/afl/zlib

test-run-afl-zlib: .afl-zlib-runner
\tdocker run \\
\t--cpus=1 \\
\t--cap-add SYS_NICE \\
\t--cap-add SYS_PTRACE \\
\t-e FUZZ_OUTSIDE_EXPERIMENT=1 \\
\t-e FORCE_LOCAL=1 \\
\t-e TRIAL_ID=1 \\
\t-e FUZZER=afl \\
\t-e BENCHMARK=zlib \\
\t-e FUZZ_TARGET=$(zlib-fuzz-target) \\
\t-e MAX_TOTAL_TIME=20 \\
\t-e SNAPSHOT_PERIOD=10 \\
\tgcr.io/fuzzbench/runners/afl/zlib

"""

    stdout = sys.stdout
    print_output = io.StringIO()
    sys.stdout = print_output

    generate_makefile.print_rules_for_image(name, image)
    result = print_output.getvalue()
    sys.stdout = stdout

    assert result == generated_makefile_truth
