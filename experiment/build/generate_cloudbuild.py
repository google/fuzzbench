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

from common import experiment_path as exp_path
from common import experiment_utils
from common import yaml_utils
from common.utils import ROOT_DIR
from experiment.build import build_utils

DOCKER_IMAGE = 'docker:19.03.12'
STANDARD_DOCKER_REGISTRY = 'gcr.io/fuzzbench'


def _get_image_tag(image_specs,
                   tag_by_experiment=False,
                   use_standard_registry=False):
    """Returns an image tag for |image_specs|. Uses an experiment-specific tag
    if |tag_by_experiment|. The registry is determined by the env var
    DOCKER_REGISTRY or is |STANDARD_DOCKER_REGISTRY| if |use_standard_registry|
    is True. Note that "tag" in this file generally refers to "name:tag".
    """
    if use_standard_registry:
        registry = STANDARD_DOCKER_REGISTRY
    else:
        registry = get_docker_registry()

    tag = posixpath.join(registry, image_specs['tag'])
    if tag_by_experiment:
        tag += ':' + experiment_utils.get_experiment_name()
    return tag


def _get_gcb_image_tag(image_specs):
    """Returns an image tag for |image_specs| that can be used by other steps in
    GCB. This tag is needed because the docker images in FuzzBench inherit from
    "gcr.io/fuzzbench/$PARENT" but the other tags for an image can't include
    gcr.io/fuzzbench because they are used to name images that are actually
    pushed to a registry, and not everyone can push to gcr.io/fuzzbench.
    This tag should not actually be pushed since again not everyone can push to
    gcr.io/fuzzbench.
    """
    return _get_image_tag(image_specs, use_standard_registry=True)


def _get_experiment_image_tag(image_specs):
    """Returns an image tag for |image_specs| that is experiment-specific and
    can be used to get images built for a specific experiment. This is needed by
    the runners which need to pull images built for a specific experiment.
    Otherwise, if multiple experiments are running concurrently, the runners can
    pull images built for another experiment.
    """
    # This tag will be used by images other than runner. However, it is only
    # actually needed for the runner images. Doing it for the other images may
    # help with debugging, but is primarily done to avoid compilcating the build
    # code.
    return _get_image_tag(image_specs, tag_by_experiment=True)


def _get_cachable_image_tag(image_specs):
    """Returns an image tag for |image_specs| that is cachable. By cachable, we
    mean the images can both be pushed to the registry and be pulled from the
    registry in a subsequent build. This means that the tag will use the
    registry specified by this experiment and will not use an experiment
    specific-tag (so that builds in other experiments can cache from this tag).
    """
    return _get_image_tag(image_specs)


def coverage_steps(benchmark):
    """Returns GCB run steps for coverage builds."""
    coverage_binaries_dir = exp_path.filestore(
        build_utils.get_coverage_binaries_dir())
    steps = [{
        'name':
            DOCKER_IMAGE,
        'args': [
            'run',
            '-v',
            '/workspace/out:/host-out',
            # TODO(metzman): Get rid of this and use one source of truth
            # for tags.
            posixpath.join(get_docker_registry(), 'builders', 'coverage',
                           benchmark) + ':' +
            experiment_utils.get_experiment_name(),
            '/bin/bash',
            '-c',
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


def get_docker_registry():
    """Returns the docker registry for this experiment."""
    return os.environ['DOCKER_REGISTRY']


def create_cloudbuild_spec(image_templates,
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
    cloudbuild_spec = {'steps': [], 'images': []}

    # Workaround for bug https://github.com/moby/moby/issues/40262.
    # This is only needed for base-image as it inherits from ubuntu:xenial.
    if build_base_images:
        cloudbuild_spec['steps'].append({
            'id': 'pull-ubuntu-xenial',
            'env': ['DOCKER_BUILDKIT=1'],
            'name': DOCKER_IMAGE,
            'args': ['pull', 'ubuntu:xenial'],
        })

    for image_name, image_specs in image_templates.items():
        step = {
            'id': image_name,
            'env': ['DOCKER_BUILDKIT=1'],
            'name': DOCKER_IMAGE,
        }
        step['args'] = [
            'build', '--tag',
            _get_experiment_image_tag(image_specs), '--tag',
            _get_gcb_image_tag(image_specs), '--tag',
            _get_cachable_image_tag(image_specs), '--cache-from',
            _get_cachable_image_tag(image_specs), '--build-arg',
            'BUILDKIT_INLINE_CACHE=1'
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

        cloudbuild_spec['steps'].append(step)
        cloudbuild_spec['images'].append(_get_experiment_image_tag(image_specs))
        cloudbuild_spec['images'].append(_get_cachable_image_tag(image_specs))

    if any(image_specs['type'] in 'coverage'
           for _, image_specs in image_templates.items()):
        cloudbuild_spec['steps'] += coverage_steps(benchmark)

    return cloudbuild_spec


def main():
    """Write base-images build spec when run from command line."""
    image_templates = yaml_utils.read(
        os.path.join(ROOT_DIR, 'docker', 'image_types.yaml'))
    base_images_spec = create_cloudbuild_spec(
        {'base-image': image_templates['base-image']}, build_base_images=True)
    base_images_spec_file = os.path.join(ROOT_DIR, 'docker', 'gcb',
                                         'base-images.yaml')
    yaml_utils.write(base_images_spec_file, base_images_spec)


if __name__ == '__main__':
    main()
