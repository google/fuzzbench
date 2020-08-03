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
import posixpath

from experiment.build import docker_images
from common import yaml_utils
from common.utils import ROOT_DIR

BASE_TAG = 'gcr.io/fuzzbench'
EXPERIMENT_REPO = '${_REPO}'
EXPERIMENT_VAR = '${_EXPERIMENT}'


def get_experiment_tag_for_image(image, experiment=True):
    """Returns the registry with the experiment tag for given image."""
    if not experiment:
        return posixpath.join(BASE_TAG, image['tag']) + ':test-experiment'
    return posixpath.join(EXPERIMENT_REPO, image['tag']) + ':' + EXPERIMENT_VAR


def coverage_steps(benchmark):
    """Returns GCB run steps for coverage builds."""
    steps = [{
        'name':
            'gcr.io/cloud-builders/docker',
        'args': [
            'run', '-v', '/workspace/out:/host-out',
            posixpath.join(EXPERIMENT_REPO, 'builders', 'coverage', benchmark) +
            ':' + EXPERIMENT_VAR, '/bin/bash', '-c',
            'cd /out; tar -czvf /host-out/coverage-build-' + benchmark +
            '.tar.gz *'
        ]
    }]
    step = {'name': 'gcr.io/cloud-builders/gsutil'}
    step['args'] = [
        '-m', 'cp', '/workspace/out/coverage-build-' + benchmark + '.tar.gz',
        '${_GCS_COVERAGE_BINARIES_DIR}/'
    ]
    steps.append(step)
    return steps


def create_cloud_build_spec(image_templates,
                            benchmark=None,
                            experiment=True,
                            build_base_images=False):
    """Generates Cloud Build specification.

    Args:
      image_templates: Image types and their properties.
      benchmark: Name of benchmark (required for coverage builds only).
      build_base_images: True if building only base images.

    Returns:
      GCB build steps.
    """
    cloud_build_spec = {}
    cloud_build_spec['steps'] = []
    cloud_build_spec['images'] = []

    for name, image_specs in image_templates.items():
        step = {
            'id': name,
            'env': 'DOCKER_BUILDKIT=1',
            'name': 'gcr.io/cloud-builders/docker'
        }
        step['args'] = [
            'build', '--tag',
            posixpath.join(BASE_TAG, image_specs['tag']), '--tag',
            get_experiment_tag_for_image(image_specs,
                                         experiment), '--cache-from',
            get_experiment_tag_for_image(image_specs, experiment),
            '--build-arg', 'BUILDKIT_INLINE_CACHE=1'
        ]
        for build_arg in image_specs.get('build_arg', []):
            step['args'] += ['--build-arg', build_arg]
        if 'dockerfile' in image_specs:
            step['args'] += ['--file', image_specs['dockerfile']]
        step['args'] += [image_specs['path']]
        step['wait_for'] = []
        for dep in image_specs.get('depends_on', []):
            # Base images are built before creating fuzzer benchmark builds,
            # so it's not required to wait for them to build.
            if 'base' in dep and not build_base_images:
                continue
            step['wait_for'] += [dep]

        cloud_build_spec['steps'].append(step)
        cloud_build_spec['images'].append(
            get_experiment_tag_for_image(image_specs, experiment))
        cloud_build_spec['images'].append(
            get_experiment_tag_for_image(image_specs, experiment).split(':')[0])

    if any('coverage' in image_name for image_name in image_templates.keys()):
        cloud_build_spec['steps'] += coverage_steps(benchmark)

    return cloud_build_spec


def _get_buildable_images(fuzzers, benchmarks):
    return docker_images.get_images_to_build(fuzzers, benchmarks)


def generate_base_images_build_spec(experiment=True):
    """Returns build spec for base images."""
    buildable_images = _get_buildable_images([''], [''])
    image_templates = {'base-image': buildable_images['base-image']}
    return create_cloud_build_spec(image_templates,
                                   build_base_images=True,
                                   experiment=experiment)


def generate_benchmark_build_spec(fuzzers, benchmarks):
    """Returns build spec for fuzzer-benchmark builds."""
    buildable_images = _get_buildable_images(fuzzers, benchmarks)
    image_templates = {}
    for name in buildable_images:
        if any(image_type in name
               for image_type in ('base', 'coverage', 'dispatcher')):
            continue
        image_templates[name] = buildable_images[name]
    return create_cloud_build_spec(image_templates)


def generate_coverage_build_spec(fuzzers, benchmarks):
    """Returns build spec for coverage builds."""
    buildable_images = _get_buildable_images(fuzzers, benchmarks)
    image_templates = {
        name: image
        for name, image in buildable_images.items()
        if 'coverage' in name
    }
    return create_cloud_build_spec(image_templates, benchmark=benchmarks[0])


def main():
    """Write base-images build spec when run from command line."""
    base_images_spec = generate_base_images_build_spec(experiment=False)
    base_images_spec_file = os.path.join(ROOT_DIR, 'docker', 'base-images.yaml')
    yaml_utils.write(base_images_spec_file, base_images_spec)


if __name__ == "__main__":
    main()
