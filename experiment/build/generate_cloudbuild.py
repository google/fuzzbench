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
"""Generates Cloud Build specification"""

import os

from experiment.build import docker_images

BASE_TAG = 'gcr.io/fuzzbench'
EXPERIMENT_TAG = "${_REPO}"
FUZZER_VAR = "${_FUZZER}"
BENCHMARK_VAR = "${_BENCHMARK}"
EXPERIMENT_VAR = "${_EXPERIMENT}"


def _identity(name):
    return name.replace(FUZZER_VAR, "fuzzer").replace(BENCHMARK_VAR,
                                                      "benchmark")


def coverage_steps():
    """Return gcb run steps for coverage."""
    steps = []
    step = {}
    step['name'] = 'gcr.io/cloud-builders/docker'
    step['args'] = ['run', '-v', '/workspace/out:/host-out']
    step['args'] += [
        os.path.join(EXPERIMENT_TAG, 'builders', 'coverage', BENCHMARK_VAR) +
        ':' + EXPERIMENT_VAR
    ]
    step['args'] += ['/bin/bash', '-c']
    step['args'] += [
        'cd /out; tar -czvf /host-out/coverage-build-' + BENCHMARK_VAR +
        '.tar.gz *'
    ]
    steps.append(step)
    step = {}
    step['name'] = 'gcr.io/cloud-builders/gsutil'
    step['args'] = ['-m', 'cp']
    step['args'] += [
        '/workspace/out/coverage-build-' + BENCHMARK_VAR + '.tar.gz'
    ]
    step['args'] += ['${_GCS_COVERAGE_BINARIES_DIR}/']
    steps.append(step)
    return steps


def create_cloud_build_spec(images_template, base=False):
    """Returns Cloud Build specification."""

    cloud_build_spec = {}
    cloud_build_spec['steps'] = []
    cloud_build_spec['images'] = []

    for name, image in images_template.items():
        step = {}
        step['id'] = _identity(name)
        step['env'] = ['DOCKER_BUILDKIT=1']
        step['name'] = 'gcr.io/cloud-builders/docker'
        step['args'] = ['build']
        step['args'] += [
            '--tag',
            os.path.join(BASE_TAG, image['tag']), '--tag',
            os.path.join(EXPERIMENT_TAG, image['tag']) + ':' + EXPERIMENT_VAR
        ]
        step['args'] += ['--cache-from']
        step['args'] += [os.path.join(EXPERIMENT_TAG, image['tag'])]
        step['args'] += ['--build-arg', 'BUILDKIT_INLINE_CACHE=1']
        if 'build_arg' in image:
            for build_arg in image['build_arg']:
                step['args'] += ['--build-arg', build_arg]
        if 'dockerfile' in image:
            step['args'] += ['--file', image['dockerfile']]
        step['args'] += [image['context']]
        if 'depends_on' in image:
            step['wait_for'] = []
            for dep in image['depends_on']:
                if 'base' in dep and not base:
                    continue
                step['wait_for'] += [_identity(dep)]
            if len(step['wait_for']) == 0:
                del step['wait_for']

        cloud_build_spec['images'].append(
            os.path.join(EXPERIMENT_TAG, image['tag']) + ':' + EXPERIMENT_VAR)
        cloud_build_spec['images'].append(
            os.path.join(EXPERIMENT_TAG, image['tag']))
        cloud_build_spec['steps'].append(step)

    if any('coverage' in _ for _ in images_template.keys()):
        cloud_build_spec['steps'] += coverage_steps()

    return cloud_build_spec


def _get_buildable_images():
    return docker_images.get_images_to_build([FUZZER_VAR], [BENCHMARK_VAR])


def generate_base_images_build_spec():
    """Returns build spec for base images."""
    buildable_images = _get_buildable_images()
    images_template = {}
    for name in buildable_images:
        if 'base' in name:
            images_template[name] = buildable_images[name]
    return create_cloud_build_spec(images_template, base=True)


def generate_benchmark_images_build_spec():
    """Returns build spec for standard benchmarks."""
    buildable_images = _get_buildable_images()
    images_template = {}
    for name in buildable_images:
        if any(_ in name for _ in ('base', 'coverage', 'dispatcher')):
            continue
        images_template[name] = buildable_images[name]
    return create_cloud_build_spec(images_template)


def generate_coverage_images_build_spec():
    """Returns build spec for OSS-Fuzz benchmarks."""
    buildable_images = _get_buildable_images()
    images_template = {}
    for name in buildable_images:
        if 'coverage' in name:
            images_template[name] = buildable_images[name]
    return create_cloud_build_spec(images_template)
