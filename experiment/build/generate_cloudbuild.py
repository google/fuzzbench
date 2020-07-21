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

import argparse
import json
import yaml

from experiment.build import docker_images


# TODO: Add unit test for this.
def create_cloud_build_spec(buildable_images, docker_registry):
    """Returns Cloud Build specificatiion."""

    cloud_build_spec = {}
    cloud_build_spec['steps'] = []
    cloud_build_spec['images'] = []

    for name, image in buildable_images.items():
        step = {}
        step['id'] = name
        step['name'] = 'gcr.io/cloud-builders/docker'
        step['args'] = []
        step['args'] += ['--tag', image['tag']]
        step['args'] += ['--cache-from', docker_registry + image['tag']]
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
                step['wait_for'] += [dep]
        cloud_build_spec['images'].append(name)
        cloud_build_spec['steps'].append(step)

    return cloud_build_spec


def main():
    """Generates Cloud Build specification."""
    parser = argparse.ArgumentParser(description='GCB spec generator.')
    parser.add_argument('-r',
                        '--docker-registry',
                        default='gcr.io/fuzzbench/',
                        help='Docker registry to use.')
    args = parser.parse_args()

    # TODO: Create fuzzer/benchmark list dynamically.
    fuzzers = ['afl', 'libfuzzer']
    benchmarks = ['libxml', 'libpng']
    buildable_images = docker_images.get_images_to_build(fuzzers, benchmarks)
    cloud_build_spec = create_cloud_build_spec(buildable_images,
                                               args.docker_registry)
    # Build spec can be yaml or json, use whichever:
    # https://cloud.google.com/cloud-build/docs/configuring-builds/create-basic-configuration
    print(yaml.dump(cloud_build_spec))
    print(json.dumps(cloud_build_spec))


if __name__ == '__main__':
    main()
