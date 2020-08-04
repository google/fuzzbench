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

import tempfile
from typing import Dict

from common import experiment_path as exp_path
from common import experiment_utils
from common import logs
from common import new_process
from common import utils
from common import yaml_utils
from experiment.build import build_utils
from experiment.build import docker_images
from experiment.build import generate_cloudbuild

BUILDER_STEP_IDS = [
    'build-fuzzer-builder',
    'build-fuzzer-benchmark-builder',
    'build-fuzzer-benchmark-builder-intermediate',
]
CONFIG_DIR = 'config'

# Maximum time to wait for a GCB config to finish build.
GCB_BUILD_TIMEOUT = 4 * 60 * 60  # 4 hours.

# High cpu configuration for faster builds.
GCB_MACHINE_TYPE = 'n1-highcpu-8'

logger = logs.Logger('builder')  # pylint: disable=invalid-name


def _get_buildable_images(fuzzer=None, benchmark=None):
    return docker_images.get_images_to_build([fuzzer], [benchmark])


def build_base_images():
    """Build base images on GCB."""
    image_templates = {'base-image': _get_buildable_images()['base-image']}
    config = generate_cloudbuild.create_cloud_build_spec(image_templates,
                                                         build_base_images=True)
    _build(config, 'base-images')


def build_coverage(benchmark):
    """Build coverage image for benchmark on GCB."""
    coverage_binaries_dir = exp_path.filestore(
        build_utils.get_coverage_binaries_dir())
    substitutions = {'_GCS_COVERAGE_BINARIES_DIR': coverage_binaries_dir}
    buildable_images = _get_buildable_images(benchmark=benchmark)
    image_templates = {
        image_name: image_spec
        for image_name, image_spec in buildable_images.items()
        if 'coverage' in image_name
    }
    config = generate_cloudbuild.create_cloud_build_spec(image_templates,
                                                         benchmark=benchmark)
    config_name = 'benchmark-{benchmark}-coverage'.format(benchmark=benchmark)
    _build(config, config_name, substitutions)


def _build(config: Dict,
           config_name: str,
           substitutions: Dict[str, str] = None,
           timeout_seconds: int = GCB_BUILD_TIMEOUT
          ) -> new_process.ProcessResult:
    """Build each of |args| on gcb."""
    with tempfile.NamedTemporaryFile() as config_file:
        yaml_utils.write(config_file.name, config)
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

        if substitutions is None:
            substitutions = {}

        assert '_REPO' not in substitutions
        substitutions['_REPO'] = experiment_utils.get_base_docker_tag()

        assert '_EXPERIMENT' not in substitutions
        substitutions['_EXPERIMENT'] = experiment_utils.get_experiment_name()

        substitutions = [
            '%s=%s' % (key, value) for key, value in substitutions.items()
        ]
        substitutions = ','.join(substitutions)
        command.append('--substitutions=%s' % substitutions)

        # Don't write to stdout to make concurrent building faster. Otherwise
        # writing becomes the bottleneck.
        result = new_process.execute(command,
                                     write_to_stdout=False,
                                     kill_children=True,
                                     timeout=timeout_seconds)
        build_utils.store_build_logs(config_name, result)
    return result


def build_fuzzer_benchmark(fuzzer: str, benchmark: str):
    """Builds |benchmark| for |fuzzer|."""
    image_templates = {}
    buildable_images = _get_buildable_images(fuzzer=fuzzer, benchmark=benchmark)
    for image_name in buildable_images:
        if any(image_type in image_name
               for image_type in ('base', 'coverage', 'dispatcher')):
            continue
        image_templates[image_name] = buildable_images[image_name]
    config = generate_cloudbuild.create_cloud_build_spec(image_templates)
    config_name = 'benchmark-{benchmark}-fuzzer-{fuzzer}'.format(
        benchmark=benchmark, fuzzer=fuzzer)

    _build(config, config_name)
