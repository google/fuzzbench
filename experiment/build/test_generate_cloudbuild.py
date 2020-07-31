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

from experiment.build import generate_cloudbuild


def test_print_cloud_build_spec():
    """Tests result of a makefile generation for an image."""

    image = {
        '${_FUZZER}-${_BENCHMARK}-builder-intermediate': {
            'tag':
                'builders/${_FUZZER}/${_BENCHMARK}-intermediate',
            'context':
                'fuzzers/${_FUZZER}',
            'dockerfile':
                'fuzzers/${_FUZZER}/builder.Dockerfile',
            'depends_on': ['${_BENCHMARK}-project-builder'],
            'build_arg': [
                'parent_image=gcr.io/fuzzbench/' +
                'builders/benchmark/${_BENCHMARK}'
            ]
        }
    }

    generated_spec = generate_cloudbuild.create_cloud_build_spec(image)

    expected_spec = {
        'steps': [{
            'id': 'fuzzer-benchmark-builder-intermediate',
            'env': ['DOCKER_BUILDKIT=1'],
            'name': 'gcr.io/cloud-builders/docker',
            'args': [
                'build', '--tag',
                'gcr.io/fuzzbench/builders/${_FUZZER}/${_BENCHMARK}-' +
                'intermediate', '--tag',
                '${_REPO}/builders/${_FUZZER}/${_BENCHMARK}-' +
                'intermediate:${_EXPERIMENT}', '--cache-from',
                '${_REPO}/builders/${_FUZZER}/${_BENCHMARK}-intermediate',
                '--build-arg', 'BUILDKIT_INLINE_CACHE=1', '--build-arg',
                'parent_image=gcr.io/fuzzbench/' +
                'builders/benchmark/${_BENCHMARK}', '--file',
                'fuzzers/${_FUZZER}/builder.Dockerfile', 'fuzzers/${_FUZZER}'
            ],
            'wait_for': ['benchmark-project-builder']
        }],
        'images': [
            '${_REPO}/builders/${_FUZZER}/${_BENCHMARK}-intermediate' +
            ':${_EXPERIMENT}',
            '${_REPO}/builders/${_FUZZER}/${_BENCHMARK}-intermediate'
        ]
    }

    assert generated_spec == expected_spec
