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
