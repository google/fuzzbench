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

from common import yaml_utils
from experiment.build import docker_images

BASE_TAG = 'gcr.io/fuzzbench-test'
EXPERIMENT_TAG = "${_REPO}"
BENCHMARK_VAR = "${_BENCHMARK}"
EXPERIMENT_VAR = "${_EXPERIMENT}"


def _identity(name):
    return name.replace("${_FUZZER}", "fuzzer").replace("${_BENCHMARK}",
                                                        "benchmark")


def coverage_steps():
    """Return gcb run steps for coverage."""
    steps = []
    step = {}
    step['name'] = 'gcr.io/cloud-builders/docker'
    step['args'] = ['run', '-v', '/workspace/out:/host-out']
    step['args'] += [
        EXPERIMENT_TAG + '/builders/coverage/' + BENCHMARK_VAR + ':' +
        EXPERIMENT_VAR
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


# TODO(Tanq16): Add unit test for this.
def create_cloud_build_spec(images_template, coverage=False, base=False):
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
        step['args'] += ['--tag', BASE_TAG + '/' + image['tag']]
        step['args'] += ['--tag']
        step['args'] += [
            EXPERIMENT_TAG + '/' + image['tag'] + ':' + EXPERIMENT_VAR
        ]
        step['args'] += ['--cache-from']
        step['args'] += [EXPERIMENT_TAG + '/' + image['tag']]
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
                step['wait_for'] += ['-']
                del step['wait_for']
        image_built = EXPERIMENT_TAG + '/' + image['tag'] + ':' + EXPERIMENT_VAR
        cloud_build_spec['images'].append(image_built)
        cloud_build_spec['steps'].append(step)

    if coverage:
        cloud_build_spec['steps'] += coverage_steps()

    return cloud_build_spec


def generate_base_images(buildable_images, base=True):
    """Returns build spec for base images."""
    base_images_template = {}
    for name in buildable_images:
        if 'base' in name:
            base_images_template[name] = buildable_images[name]
    return create_cloud_build_spec(base_images_template, base=base)


def generate_benchmark_images(buildable_images, coverage=False):
    """Returns build spec for standard benchmarks."""
    benchmark_images_template = {}
    for name in buildable_images:
        if any(_ in name for _ in ('base', 'oss-fuzz')):
            continue
        if coverage and 'runner' in name:
            continue
        benchmark_images_template[name] = buildable_images[name]
    return create_cloud_build_spec(benchmark_images_template, coverage=coverage)


def generate_oss_fuzz_benchmark_images(buildable_images, coverage=False):
    """Returns build spec for OSS-Fuzz benchmarks."""
    oss_fuzz_benchmark_images_template = {}
    for name in buildable_images:
        if coverage and 'runner' in name:
            continue
        if 'oss-fuzz' in name:
            oss_fuzz_benchmark_images_template[name] = buildable_images[name]
    return create_cloud_build_spec(oss_fuzz_benchmark_images_template,
                                   coverage=coverage)


def write_spec(filename, data):
    """Write build spec to specified file."""
    file_path = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir,
                             'docker', 'gcb', filename)
    if not os.path.exists(os.path.dirname(file_path)):
        os.makedirs(os.path.dirname(file_path))
    yaml_utils.write(file_path, data)


def generate_gcb_build_spec():
    """Generates Cloud Build specification."""

    buildable_images = docker_images.get_images_to_build_gcb()
    buildable_images_coverage = docker_images.get_images_to_build_gcb(
        coverage=True)

    write_spec('base-images.yaml', generate_base_images(buildable_images))
    write_spec('fuzzer.yaml', generate_benchmark_images(buildable_images))
    write_spec(
        'coverage.yaml',
        generate_benchmark_images(buildable_images_coverage, coverage=True))
    write_spec('oss-fuzz-fuzzer.yaml',
               generate_oss_fuzz_benchmark_images(buildable_images))
    write_spec(
        'oss-fuzz-coverage.yaml',
        generate_oss_fuzz_benchmark_images(buildable_images_coverage,
                                           coverage=True))
