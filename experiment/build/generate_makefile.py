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
"""Generates Makefile containing docker image targets."""

import argparse

from experiment.build import docker_images


# TODO: Add unit test for this.
def print_makefile(buildable_images, docker_registry):
    """Prints the generated makefile to stdout."""
    print('export DOCKER_BUILDKIT := 1')

    for name, image in buildable_images.items():
        print(name + ':', end='')
        if 'depends_on' in image:
            for dep in image['depends_on']:
                print(' ' + dep, end='')
        print()
        print('\tdocker build \\')
        print('    --tag ' + image['tag'] + ' \\')
        print('    --cache-from ' + docker_registry + image['tag'] + ' \\')
        if 'build_arg' in image:
            for arg in image['build_arg']:
                print('    --build-arg ' + arg + ' \\')
        if 'dockerfile' in image:
            print('    --file ' + image['dockerfile'] + ' \\')
        print('    ' + image['context'])
        print()


def main():
    """Generates Makefile with docker image build rules."""
    parser = argparse.ArgumentParser(description='GCB spec generator.')
    parser.add_argument('-r',
                        '--docker-registry',
                        default='gcr.io/fuzzbench/',
                        help='Docker registry to use as cache.')
    args = parser.parse_args()

    # TODO: Create fuzzer/benchmark list dynamically.
    fuzzers = ['afl', 'libfuzzer']
    benchmarks = ['libxml', 'libpng']
    buildable_images = docker_images.get_images_to_build(fuzzers, benchmarks)
    print_makefile(buildable_images, args.docker_registry)


if __name__ == '__main__':
    main()
