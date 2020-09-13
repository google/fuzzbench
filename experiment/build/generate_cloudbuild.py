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

from common import yaml_utils
from common import experiment_utils
from common import experiment_path as exp_path
from common.utils import ROOT_DIR
from experiment.build import build_utils

DOCKER_IMAGE = 'docker:19.03.12'
PROJECT_DOCKER_REGISTRY = 'gcr.io/fuzzbench'


def get_experiment_tag_for_image(image_specs, tag_by_experiment=True):
    """Returns the registry with the experiment tag for given image."""
    tag = posixpath.join(experiment_utils.get_base_docker_tag(),
                         image_specs['tag'])
    if tag_by_experiment:
        tag += ':' + experiment_utils.get_experiment_name()
    return tag


def coverage_steps(benchmark):
    """Returns GCB run steps for coverage builds."""
    coverage_binaries_dir = exp_path.filestore(
        build_utils.get_coverage_binaries_dir())
    steps = [{
        'name':
            DOCKER_IMAGE,
        'args': [
            'run', '-v', '/workspace/out:/host-out',
            posixpath.join(experiment_utils.get_base_docker_tag(), 'builders',
                           'coverage', benchmark) + ':' +
            experiment_utils.get_experiment_name(), '/bin/bash', '-c',
            'cd /out; tar -czvf /host-out/coverage-build-' + benchmark +
            '.tar.gz * /src /work'
        ]
    }]
    step = {'name': 'gcr.io/cloud-builders/gsutil'}
    step['args'] = [
        '-m', 'cp', '/workspace/out/coverage-build-' + benchmark + '.tar.gz',
        coverage_binaries_dir + '/'
    ]
    steps.append(step)
    return steps


def create_cloud_build_spec(image_templates,
                            benchmark='',
                            build_base_images=False):
    """Generates Cloud Build specification.

    Args:
      image_templates: Image types and their properties.
      benchmark: Name of benchmark (required for coverage builds only).
      build_base_images: True if building only base images.

    Returns:
      GCB build steps.
    """
    cloud_build_spec = {'steps': [], 'images': []}

    if build_base_images:
        cloud_build_spec['steps'].append({
            # Workaround for bug https://github.com/moby/moby/issues/40262.
            'id': 'pull-ubuntu-xenial',
            'env': 'DOCKER_BUILDKIT=1',
            'name': DOCKER_IMAGE,
            'args': ['pull', 'ubuntu:xenial'],
        })

    for image_name, image_specs in image_templates.items():
        step = {
            'id': image_name,
            'env': 'DOCKER_BUILDKIT=1',
            'name': DOCKER_IMAGE,
        }
        step['args'] = [
            'build', '--tag',
            posixpath.join(PROJECT_DOCKER_REGISTRY,
                           image_specs['tag']), '--tag',
            get_experiment_tag_for_image(image_specs), '--cache-from',
            get_experiment_tag_for_image(image_specs, tag_by_experiment=False),
            '--build-arg', 'BUILDKIT_INLINE_CACHE=1'
        ]
        for build_arg in image_specs.get('build_arg', []):
            step['args'] += ['--build-arg', build_arg]

        step['args'] += [
            '--file', image_specs['dockerfile'], image_specs['context']
        ]
        step['wait_for'] = []
        for dependency in image_specs.get('depends_on', []):
            # Base images are built before creating fuzzer benchmark builds,
            # so it's not required to wait for them to build.
            if 'base' in dependency and not build_base_images:
                continue
            step['wait_for'] += [dependency]

        cloud_build_spec['steps'].append(step)
        cloud_build_spec['images'].append(
            get_experiment_tag_for_image(image_specs))
        cloud_build_spec['images'].append(
            get_experiment_tag_for_image(image_specs, tag_by_experiment=False))

    if any(image_specs['type'] in 'coverage'
           for _, image_specs in image_templates.items()):
        cloud_build_spec['steps'] += coverage_steps(benchmark)

    return cloud_build_spec


def main():
    """Write base-images build spec when run from command line."""
    image_templates = yaml_utils.read(
        os.path.join(ROOT_DIR, 'docker', 'image_types.yaml'))
    base_images_spec = create_cloud_build_spec(
        {'base-image': image_templates['base-image']}, build_base_images=True)
    base_images_spec_file = os.path.join(ROOT_DIR, 'docker', 'gcb',
                                         'base-images.yaml')
    yaml_utils.write(base_images_spec_file, base_images_spec)


if __name__ == '__main__':
    main()
