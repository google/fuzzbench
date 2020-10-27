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
"""Tests for generate_cloudbuild.py."""
import os

from experiment.build import generate_cloudbuild

# pylint: disable=unused-argument


def test_generate_cloudbuild_spec_build_base_image(experiment):
    """Tests generation of cloud build configuration yaml for the base image."""
    image_templates = {
        'base-image': {
            'dockerfile': 'docker/base-image/Dockerfile',
            'context': 'docker/base-image',
            'tag': 'base-image',
            'type': 'base'
        }
    }
    generated_spec = generate_cloudbuild.create_cloudbuild_spec(
        image_templates, build_base_images=True)

    expected_spec = {
        'steps': [{
            'id': 'pull-ubuntu-xenial',
            'env': ['DOCKER_BUILDKIT=1'],
            'name': 'docker:19.03.12',
            'args': ['pull', 'ubuntu:xenial']
        }, {
            'id': 'base-image',
            'env': ['DOCKER_BUILDKIT=1'],
            'name': 'docker:19.03.12',
            'args': [
                'build', '--tag', 'gcr.io/fuzzbench/base-image:test-experiment',
                '--tag', 'gcr.io/fuzzbench/base-image', '--tag',
                'gcr.io/fuzzbench/base-image', '--cache-from',
                'gcr.io/fuzzbench/base-image', '--build-arg',
                'BUILDKIT_INLINE_CACHE=1', '--file',
                'docker/base-image/Dockerfile', 'docker/base-image'
            ],
            'wait_for': []
        }],
        'images': [
            'gcr.io/fuzzbench/base-image:test-experiment',
            'gcr.io/fuzzbench/base-image'
        ]
    }

    assert generated_spec == expected_spec


def test_generate_cloudbuild_spec_other_registry(experiment):
    """Tests generation of cloud build configuration yaml for the base image
    when a registry other than gcr.io/fuzzbench is specified.
    """
    os.environ['DOCKER_REGISTRY'] = 'gcr.io/not-fuzzbench'
    image_templates = {
        'base-image': {
            'dockerfile': 'docker/base-image/Dockerfile',
            'context': 'docker/base-image',
            'tag': 'base-image',
            'type': 'base'
        }
    }
    generated_spec = generate_cloudbuild.create_cloudbuild_spec(
        image_templates, build_base_images=True)

    expected_spec = {
        'steps': [{
            'id': 'pull-ubuntu-xenial',
            'env': ['DOCKER_BUILDKIT=1'],
            'name': 'docker:19.03.12',
            'args': ['pull', 'ubuntu:xenial']
        }, {
            'id': 'base-image',
            'env': ['DOCKER_BUILDKIT=1'],
            'name': 'docker:19.03.12',
            'args': [
                'build', '--tag', 'gcr.io/not-fuzzbench/base-image'
                ':test-experiment', '--tag', 'gcr.io/fuzzbench/base-image',
                '--tag', 'gcr.io/not-fuzzbench/base-image', '--cache-from',
                'gcr.io/not-fuzzbench/base-image', '--build-arg',
                'BUILDKIT_INLINE_CACHE=1', '--file',
                'docker/base-image/Dockerfile', 'docker/base-image'
            ],
            'wait_for': []
        }],
        'images': [
            'gcr.io/not-fuzzbench/base-image:test-experiment',
            'gcr.io/not-fuzzbench/base-image'
        ]
    }

    assert generated_spec == expected_spec


def test_generate_cloudbuild_spec_build_fuzzer_benchmark(experiment):
    """Tests generation of cloud build configuration yaml for a fuzzer-benchmark
    build."""
    image_templates = {
        'afl-zlib-builder-intermediate': {
            'build_arg': [
                'parent_image=gcr.io/fuzzbench/builders/benchmark/zlib'
            ],
            'depends_on': ['zlib-project-builder'],
            'dockerfile': 'fuzzers/afl/builder.Dockerfile',
            'context': 'fuzzers/afl',
            'tag': 'builders/afl/zlib-intermediate',
            'type': 'builder'
        }
    }

    generated_spec = generate_cloudbuild.create_cloudbuild_spec(image_templates)

    expected_spec = {
        'steps': [{
            'id': 'afl-zlib-builder-intermediate',
            'env': ['DOCKER_BUILDKIT=1'],
            'name': 'docker:19.03.12',
            'args': [
                'build', '--tag',
                'gcr.io/fuzzbench/builders/afl/zlib-intermediate'
                ':test-experiment', '--tag',
                'gcr.io/fuzzbench/builders/afl/zlib-intermediate', '--tag',
                'gcr.io/fuzzbench/builders/afl/zlib-intermediate',
                '--cache-from',
                'gcr.io/fuzzbench/builders/afl/zlib-intermediate',
                '--build-arg', 'BUILDKIT_INLINE_CACHE=1', '--build-arg',
                'parent_image=gcr.io/fuzzbench/builders/benchmark/zlib',
                '--file', 'fuzzers/afl/builder.Dockerfile', 'fuzzers/afl'
            ],
            'wait_for': ['zlib-project-builder']
        }],
        'images': [
            'gcr.io/fuzzbench/builders/afl/zlib-intermediate:test-experiment',
            'gcr.io/fuzzbench/builders/afl/zlib-intermediate'
        ]
    }
    assert generated_spec == expected_spec


def test_generate_cloudbuild_spec_build_benchmark_coverage(experiment):
    """Tests generation of cloud build configuration yaml for a benchmark
    coverage build."""
    image_templates = {
        'zlib-project-builder': {
            'dockerfile': 'benchmarks/zlib/Dockerfile',
            'context': 'benchmarks/zlib',
            'tag': 'builders/benchmark/zlib',
            'type': 'builder'
        },
        'coverage-zlib-builder-intermediate': {
            'build_arg': [
                'parent_image=gcr.io/fuzzbench/builders/benchmark/zlib'
            ],
            'depends_on': ['zlib-project-builder'],
            'dockerfile': 'fuzzers/coverage/builder.Dockerfile',
            'context': 'fuzzers/coverage',
            'tag': 'builders/coverage/zlib-intermediate',
            'type': 'coverage'
        },
        'coverage-zlib-builder': {
            'build_arg': [
                'benchmark=zlib', 'fuzzer=coverage',
                'parent_image=gcr.io/fuzzbench/builders/coverage/'
                'zlib-intermediate'
            ],
            'depends_on': ['coverage-zlib-builder-intermediate'],
            'dockerfile': 'docker/benchmark-builder/Dockerfile',
            'context': '.',
            'tag': 'builders/coverage/zlib',
            'type': 'coverage'
        }
    }

    generated_spec = generate_cloudbuild.create_cloudbuild_spec(
        image_templates, benchmark='zlib')

    expected_spec = {
        'steps': [{
            'id': 'zlib-project-builder',
            'env': ['DOCKER_BUILDKIT=1'],
            'name': 'docker:19.03.12',
            'args': [
                'build', '--tag',
                'gcr.io/fuzzbench/builders/benchmark/zlib:test-experiment',
                '--tag', 'gcr.io/fuzzbench/builders/benchmark/zlib', '--tag',
                'gcr.io/fuzzbench/builders/benchmark/zlib', '--cache-from',
                'gcr.io/fuzzbench/builders/benchmark/zlib', '--build-arg',
                'BUILDKIT_INLINE_CACHE=1', '--file',
                'benchmarks/zlib/Dockerfile', 'benchmarks/zlib'
            ],
            'wait_for': []
        }, {
            'id': 'coverage-zlib-builder-intermediate',
            'env': ['DOCKER_BUILDKIT=1'],
            'name': 'docker:19.03.12',
            'args': [
                'build', '--tag',
                'gcr.io/fuzzbench/builders/coverage/zlib-intermediate:'
                'test-experiment', '--tag',
                'gcr.io/fuzzbench/builders/coverage/zlib-intermediate', '--tag',
                'gcr.io/fuzzbench/builders/coverage/zlib-intermediate',
                '--cache-from',
                'gcr.io/fuzzbench/builders/coverage/zlib-intermediate',
                '--build-arg', 'BUILDKIT_INLINE_CACHE=1', '--build-arg',
                'parent_image=gcr.io/fuzzbench/builders/benchmark/zlib',
                '--file', 'fuzzers/coverage/builder.Dockerfile',
                'fuzzers/coverage'
            ],
            'wait_for': ['zlib-project-builder']
        }, {
            'id': 'coverage-zlib-builder',
            'env': ['DOCKER_BUILDKIT=1'],
            'name': 'docker:19.03.12',
            'args': [
                'build', '--tag',
                'gcr.io/fuzzbench/builders/coverage/zlib:test-experiment',
                '--tag', 'gcr.io/fuzzbench/builders/coverage/zlib', '--tag',
                'gcr.io/fuzzbench/builders/coverage/zlib', '--cache-from',
                'gcr.io/fuzzbench/builders/coverage/zlib', '--build-arg',
                'BUILDKIT_INLINE_CACHE=1', '--build-arg', 'benchmark=zlib',
                '--build-arg', 'fuzzer=coverage', '--build-arg',
                'parent_image=gcr.io/fuzzbench/builders/coverage/'
                'zlib-intermediate', '--file',
                'docker/benchmark-builder/Dockerfile', '.'
            ],
            'wait_for': ['coverage-zlib-builder-intermediate']
        }, {
            'name':
                'docker:19.03.12',
            'args': [
                'run', '-v', '/workspace/out:/host-out',
                'gcr.io/fuzzbench/builders/coverage/zlib:test-experiment',
                '/bin/bash', '-c',
                'cd /out; tar -czvf /host-out/coverage-build-zlib.tar.gz * '
                '/src /work'
            ]
        }, {
            'name':
                'gcr.io/cloud-builders/gsutil',
            'args': [
                '-m', 'cp', '/workspace/out/coverage-build-zlib.tar.gz',
                'gs://experiment-data/test-experiment/coverage-binaries/'
            ]
        }],
        'images': [
            'gcr.io/fuzzbench/builders/benchmark/zlib:test-experiment',
            'gcr.io/fuzzbench/builders/benchmark/zlib',
            'gcr.io/fuzzbench/builders/coverage/zlib-intermediate'
            ':test-experiment',
            'gcr.io/fuzzbench/builders/coverage/zlib-intermediate',
            'gcr.io/fuzzbench/builders/coverage/zlib:test-experiment',
            'gcr.io/fuzzbench/builders/coverage/zlib'
        ]
    }

    assert generated_spec == expected_spec
