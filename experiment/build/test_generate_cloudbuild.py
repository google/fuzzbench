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

from unittest.mock import patch 

from experiment.build import generate_cloudbuild


@patch.dict(os.environ, {
    'CLOUD_PROJECT': 'fuzzbench',
    'EXPERIMENT': 'test-experiment'
})
def test_generate_cloud_build_spec():
    """Tests result of a makefile generation for an image."""

    image = {
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

    generated_spec = generate_cloudbuild.create_cloud_build_spec(image)

    expected_spec = {
        'steps': [{
            'id': 'afl-zlib-builder-intermediate',
            'env': 'DOCKER_BUILDKIT=1',
            'name': 'gcr.io/cloud-builders/docker',
            'args': [
                'build', '--tag',
                'gcr.io/fuzzbench/builders/afl/zlib-intermediate', '--tag',
                'gcr.io/fuzzbench/builders/afl/zlib-intermediate'
                ':test-experiment', '--cache-from',
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
