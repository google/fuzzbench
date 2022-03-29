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
"""Module for building things on Google Cloud Build for use in trials."""

import subprocess
import tempfile
from typing import Dict

from common import logs
from common import new_process
from common import utils
from common import yaml_utils
from experiment.build import build_utils
from experiment.build import docker_images
from experiment.build import generate_cloudbuild

CONFIG_DIR = 'config'

# Maximum time to wait for a GCB config to finish build.
GCB_BUILD_TIMEOUT = 4 * 60 * 60  # 4 hours.

# High cpu and memory configuration, matches OSS-Fuzz.
GCB_MACHINE_TYPE = 'n1-highcpu-32'

logger = logs.Logger('builder')  # pylint: disable=invalid-name


def _get_buildable_images(fuzzer=None, benchmark=None):
    return docker_images.get_images_to_build([fuzzer], [benchmark])


def build_base_images():
    """Build base images on GCB."""
    buildable_images = _get_buildable_images()
    image_templates = {
        image: buildable_images[image] for image in ['base-image', 'worker']
    }
    config = generate_cloudbuild.create_cloudbuild_spec(image_templates,
                                                        build_base_images=True)
    _build(config, 'base-images')


def build_coverage(benchmark):
    """Build coverage image for benchmark on GCB."""
    buildable_images = _get_buildable_images(benchmark=benchmark)
    image_templates = {
        image_name: image_specs
        for image_name, image_specs in buildable_images.items()
        if (image_name == (benchmark + '-project-builder') or
            image_specs['type'] == 'coverage')
    }
    config = generate_cloudbuild.create_cloudbuild_spec(image_templates,
                                                        benchmark=benchmark)
    config_name = 'benchmark-{benchmark}-coverage'.format(benchmark=benchmark)
    _build(config, config_name)


def _build(
        config: Dict,
        config_name: str,
        timeout_seconds: int = GCB_BUILD_TIMEOUT) -> new_process.ProcessResult:
    """Submit build to GCB."""
    with tempfile.NamedTemporaryFile() as config_file:
        yaml_utils.write(config_file.name, config)
        logger.debug('Using build configuration: %s' % config)

        config_arg = '--config=%s' % config_file.name
        machine_type_arg = '--machine-type=%s' % GCB_MACHINE_TYPE

        # Use "s" suffix to denote seconds.
        timeout_arg = '--timeout=%ds' % timeout_seconds

        command = [
            'gcloud',
            'builds',
            'submit',
            str(utils.ROOT_DIR),
            config_arg,
            timeout_arg,
            machine_type_arg,
        ]

        # Don't write to stdout to make concurrent building faster. Otherwise
        # writing becomes the bottleneck.
        result = new_process.execute(command,
                                     write_to_stdout=False,
                                     kill_children=True,
                                     timeout=timeout_seconds,
                                     expect_zero=False)
        # TODO(metzman): Refactor code so that local_build stores logs as well.
        build_utils.store_build_logs(config_name, result)
        if result.retcode != 0:
            raise subprocess.CalledProcessError(result.retcode, command)
    return result


def build_fuzzer_benchmark(fuzzer: str, benchmark: str):
    """Builds |benchmark| for |fuzzer|."""
    image_templates = {}
    buildable_images = _get_buildable_images(fuzzer=fuzzer, benchmark=benchmark)
    for image_name, image_specs in buildable_images.items():
        if image_specs['type'] in ('base', 'coverage', 'dispatcher'):
            continue
        image_templates[image_name] = image_specs
    config = generate_cloudbuild.create_cloudbuild_spec(image_templates)
    config_name = 'benchmark-{benchmark}-fuzzer-{fuzzer}'.format(
        benchmark=benchmark, fuzzer=fuzzer)

    _build(config, config_name)
