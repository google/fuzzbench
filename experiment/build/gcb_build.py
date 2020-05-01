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

import os
from typing import Dict, Tuple

from common import benchmark_utils
from common import experiment_path as exp_path
from common import experiment_utils
from common import filesystem
from common import fuzzer_config_utils
from common import logs
from common import new_process
from common import utils
from common import yaml_utils
from experiment.build import build_utils

BUILDER_STEP_IDS = [
    'build-fuzzer-builder',
    'build-fuzzer-benchmark-builder',
    'build-fuzzer-benchmark-builder-intermediate',
]
CONFIG_DIR = 'config'

# Maximum time to wait for a GCB config to finish build.
GCB_BUILD_TIMEOUT = 2 * 60 * 60  # 2 hours.

# High cpu configuration for faster builds.
GCB_MACHINE_TYPE = 'n1-highcpu-8'

logger = logs.Logger('builder')  # pylint: disable=invalid-name


def build_base_images() -> Tuple[int, str]:
    """Build base images on GCB."""
    return _build(get_build_config_file('base-images.yaml'), 'base-images')


def build_coverage(benchmark):
    """Build coverage image for benchmark on GCB."""
    if benchmark_utils.is_oss_fuzz(benchmark):
        _build_oss_fuzz_project_coverage(benchmark)
    else:
        _build_benchmark_coverage(benchmark)


def _build_benchmark_coverage(benchmark: str) -> Tuple[int, str]:
    """Build a coverage build of |benchmark| on GCB."""
    coverage_binaries_dir = exp_path.gcs(
        build_utils.get_coverage_binaries_dir())
    substitutions = {
        '_GCS_COVERAGE_BINARIES_DIR': coverage_binaries_dir,
        '_BENCHMARK': benchmark,
    }
    config_file = get_build_config_file('coverage.yaml')
    config_name = 'benchmark-{benchmark}-coverage'.format(benchmark=benchmark)
    return _build(config_file, config_name, substitutions)


def _add_build_arguments_to_config(base: str, fuzzer: str) -> str:
    """If there are fuzzer-specific arguments, make a config file with them."""
    fuzzer_config = fuzzer_config_utils.get_by_variant_name(fuzzer)
    if 'build_arguments' not in fuzzer_config:
        return base

    # TODO(mbarbella): Rather than rewrite yaml files, use the GCB API.
    args = fuzzer_config['build_arguments']
    config = yaml_utils.read(base)
    for step in config['steps']:
        if 'id' in step and step['id'] in BUILDER_STEP_IDS:
            # Append additional flags before the final argument.
            step['args'] = step['args'][:-1] + args + [step['args'][-1]]

    new_config_path = os.path.join(CONFIG_DIR, 'builds', fuzzer + '.yaml')
    filesystem.create_directory(os.path.dirname(new_config_path))
    yaml_utils.write(new_config_path, config)
    return new_config_path


def _build_oss_fuzz_project_fuzzer(benchmark: str,
                                   fuzzer: str) -> Tuple[int, str]:
    """Build a |benchmark|, |fuzzer| runner image on GCB."""
    underlying_fuzzer = fuzzer_config_utils.get_by_variant_name(
        fuzzer)['fuzzer']
    project = benchmark_utils.get_project(benchmark)
    oss_fuzz_builder_hash = benchmark_utils.get_oss_fuzz_builder_hash(benchmark)
    substitutions = {
        '_OSS_FUZZ_PROJECT': project,
        '_BENCHMARK': benchmark,
        '_FUZZER': fuzzer,
        '_UNDERLYING_FUZZER': underlying_fuzzer,
        '_OSS_FUZZ_BUILDER_HASH': oss_fuzz_builder_hash,
    }
    config_file = _add_build_arguments_to_config(
        get_build_config_file('oss-fuzz-fuzzer.yaml'), fuzzer)
    config_name = 'oss-fuzz-{project}-fuzzer-{fuzzer}-hash-{hash}'.format(
        project=project, fuzzer=fuzzer, hash=oss_fuzz_builder_hash)

    return _build(config_file, config_name, substitutions)


def _build_benchmark_fuzzer(benchmark: str, fuzzer: str) -> Tuple[int, str]:
    """Build a |benchmark|, |fuzzer| runner image on GCB."""
    underlying_fuzzer = fuzzer_config_utils.get_by_variant_name(
        fuzzer)['fuzzer']
    # See link for why substitutions must begin with an underscore:
    # https://cloud.google.com/cloud-build/docs/configuring-builds/substitute-variable-values#using_user-defined_substitutions
    substitutions = {
        '_BENCHMARK': benchmark,
        '_FUZZER': fuzzer,
        '_UNDERLYING_FUZZER': underlying_fuzzer,
    }
    config_file = _add_build_arguments_to_config(
        get_build_config_file('fuzzer.yaml'), fuzzer)
    config_name = 'benchmark-{benchmark}-fuzzer-{fuzzer}'.format(
        benchmark=benchmark, fuzzer=fuzzer)
    return _build(config_file, config_name, substitutions)


def _build_oss_fuzz_project_coverage(benchmark: str) -> Tuple[int, str]:
    """Build a coverage build of OSS-Fuzz-based benchmark |benchmark| on GCB."""
    project = benchmark_utils.get_project(benchmark)
    oss_fuzz_builder_hash = benchmark_utils.get_oss_fuzz_builder_hash(benchmark)
    coverage_binaries_dir = exp_path.gcs(
        build_utils.get_coverage_binaries_dir())
    substitutions = {
        '_GCS_COVERAGE_BINARIES_DIR': coverage_binaries_dir,
        '_BENCHMARK': benchmark,
        '_OSS_FUZZ_PROJECT': project,
        '_OSS_FUZZ_BUILDER_HASH': oss_fuzz_builder_hash,
    }
    config_file = get_build_config_file('oss-fuzz-coverage.yaml')
    config_name = 'oss-fuzz-{project}-coverage-hash-{hash}'.format(
        project=project, hash=oss_fuzz_builder_hash)
    return _build(config_file, config_name, substitutions)


def _build(config_file: str,
           config_name: str,
           substitutions: Dict[str, str] = None,
           timeout_seconds: int = GCB_BUILD_TIMEOUT) -> Tuple[int, str]:
    """Build each of |args| on gcb."""
    config_arg = '--config=%s' % config_file
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


def get_build_config_file(filename: str) -> str:
    """Return the path of the GCB build config file |filename|."""
    return os.path.join(utils.ROOT_DIR, 'docker', 'gcb', filename)


def build_fuzzer_benchmark(fuzzer: str, benchmark: str) -> bool:
    """Builds |benchmark| for |fuzzer|."""
    if benchmark_utils.is_oss_fuzz(benchmark):
        _build_oss_fuzz_project_fuzzer(benchmark, fuzzer)
    else:
        _build_benchmark_fuzzer(benchmark, fuzzer)
