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
"""Docker images tests."""

from experiment.build import docker_images


def test_images_to_build_list():
    """Tests that the expected set of images is returned by
    images_to_build()."""
    fuzzers = ['afl', 'libfuzzer']
    benchmarks = ['libxml', 'libpng']
    all_images = docker_images.get_images_to_build(fuzzers, benchmarks)
    assert set(all_images.keys()) == set([
        'base-image', 'worker', 'dispatcher-image', 'libxml-project-builder',
        'libpng-project-builder', 'afl-libxml-builder-intermediate',
        'afl-libxml-intermediate-runner', 'afl-libxml-builder',
        'afl-libxml-builder-debug', 'coverage-libxml-builder',
        'afl-libpng-builder', 'afl-libpng-builder-debug',
        'afl-libpng-intermediate-runner', 'afl-libpng-builder-intermediate',
        'afl-libpng-runner', 'libfuzzer-libxml-builder-intermediate',
        'libfuzzer-libxml-builder', 'libfuzzer-libxml-builder-debug',
        'libfuzzer-libpng-builder-intermediate',
        'libfuzzer-libxml-intermediate-runner', 'libfuzzer-libxml-runner',
        'libfuzzer-libpng-builder', 'libfuzzer-libpng-builder-debug',
        'libfuzzer-libpng-intermediate-runner', 'libfuzzer-libpng-runner',
        'coverage-libxml-builder-intermediate', 'coverage-libpng-builder',
        'coverage-libxml-builder-intermediate', 'afl-libxml-runner',
        'coverage-libpng-builder-intermediate'
    ])


def test_dependencies_exist():
    """Tests that if an image has a dependency, then the dependency exist among
    the images."""
    fuzzers = ['afl', 'libfuzzer']
    benchmarks = ['libxml', 'libpng']
    all_images = docker_images.get_images_to_build(fuzzers, benchmarks)

    for image in all_images.values():
        if 'depends_on' in image:
            for dep in image['depends_on']:
                assert dep in all_images
