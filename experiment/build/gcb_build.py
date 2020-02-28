#!/usr/bin/env python3
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
import subprocess
from typing import Dict, Tuple

from common import benchmark_utils
from common import environment
from common import experiment_path as exp_path
from common import experiment_utils
from common import gsutil
from common import logs
from common import new_process
from common import utils
from experiment.build import build_utils

# Maximum time to wait for a GCB config to finish build.
GCB_BUILD_TIMEOUT = 2 * 60 * 60  # 2 hours.

# High cpu configuration for faster builds.
GCB_MACHINE_TYPE = 'n1-highcpu-8'

logger = logs.Logger('builder')  # pylint: disable=invalid-name


def make(*args):
    """Invoke |make| with |args| and return the result."""
    assert args
    command = ['make'] + list(args)
    return new_process.execute(command)


def build_base_images() -> Tuple[int, str]:
    """Build base images on GCB."""
    if utils.is_local_experiment():
        return make('base-runner', 'base-builder')
    return _build(get_build_config_file('base-images.yaml'), 'base-images')


def build_coverage(benchmark):
    """Build coverage image for benchmark on GCB."""
    if benchmark_utils.is_oss_fuzz(benchmark):
        build_oss_fuzz_project_coverage(benchmark)
    else:
        build_benchmark_coverage(benchmark)


def local_copy_coverage_binaries(benchmark):
    """Copy coverage binaries in a local experiment."""
    coverage_binaries_dir = build_utils.get_coverage_binaries_dir()
    mount_arg = '{}:/host-out'.format(coverage_binaries_dir)
    runner_image_url = benchmark_utils.get_runner_image_url(
        benchmark, 'coverage', environment.get('CLOUD_PROJECT'))
    if benchmark_utils.is_oss_fuzz(benchmark):
        runner_image_url = runner_image_url.replace('runners', 'builders')
    docker_name = benchmark_utils.get_docker_name(benchmark)
    coverage_build_archive = 'coverage-build-{}.tar.gz'.format(docker_name)
    command = 'cd /out; tar -czvf /host-out/{} *'.format(coverage_build_archive)
    new_process.execute([
        'docker', 'run', '-v', mount_arg, runner_image_url, '/bin/bash', '-c',
        command
    ])
    coverage_build_archive_path = os.path.join(coverage_binaries_dir,
                                               coverage_build_archive)
    return gsutil.cp(coverage_build_archive_path,
                     exp_path.gcs(coverage_build_archive_path))


def build_benchmark_coverage(benchmark: str) -> Tuple[int, str]:
    """Build a coverage build of |benchmark| on GCB."""
    if utils.is_local_experiment():
        image_name = 'coverage-{}-oss-fuzz-builder'.format(benchmark)
        result = make(image_name)
        if result.retcode:
            return result
        local_copy_coverage_binaries(benchmark)
        return result

    coverage_binaries_dir = exp_path.gcs(
        build_utils.get_coverage_binaries_dir())
    substitutions = {
        '_GCS_COVERAGE_BINARIES_DIR': coverage_binaries_dir,
        '_BENCHMARK': benchmark,
    }
    config_file = get_build_config_file('coverage.yaml')
    config_name = 'benchmark-{benchmark}-coverage'.format(benchmark=benchmark)
    return _build(config_file, config_name, substitutions)


def build_oss_fuzz_project_fuzzer(benchmark: str,
                                  fuzzer: str) -> Tuple[int, str]:
    """Build a |benchmark|, |fuzzer| runner image on GCB."""
    project = benchmark_utils.get_project(benchmark)
    oss_fuzz_builder_hash = benchmark_utils.get_oss_fuzz_builder_hash(benchmark)
    substitutions = {
        '_OSS_FUZZ_PROJECT': project,
        '_FUZZER': fuzzer,
        '_OSS_FUZZ_BUILDER_HASH': oss_fuzz_builder_hash,
    }
    config_file = get_build_config_file('oss-fuzz-fuzzer.yaml')
    config_name = 'oss-fuzz-{project}-fuzzer-{fuzzer}-hash-{hash}'.format(
        project=project, fuzzer=fuzzer, hash=oss_fuzz_builder_hash)

    return _build(config_file, config_name, substitutions)


def build_benchmark_fuzzer(benchmark: str, fuzzer: str) -> Tuple[int, str]:
    """Build a |benchmark|, |fuzzer| runner image on GCB."""
    # See link for why substitutions must begin with an underscore:
    # https://cloud.google.com/cloud-build/docs/configuring-builds/substitute-variable-values#using_user-defined_substitutions
    substitutions = {
        '_BENCHMARK': benchmark,
        '_FUZZER': fuzzer,
    }
    config_file = get_build_config_file('fuzzer.yaml')
    config_name = 'benchmark-{benchmark}-fuzzer-{fuzzer}'.format(
        benchmark=benchmark, fuzzer=fuzzer)
    return _build(config_file, config_name, substitutions)


def build_oss_fuzz_project_coverage(benchmark: str) -> Tuple[int, str]:
    """Build a coverage build of OSS-Fuzz-based benchmark |benchmark| on GCB."""
    if utils.is_local_experiment():
        image_name = 'coverage-{}-oss-fuzz-builder'.format(benchmark)
        result = make(image_name)
        if result.retcode:
            return result
        local_copy_coverage_binaries(benchmark)
        return result

    project = benchmark_utils.get_project(benchmark)
    oss_fuzz_builder_hash = benchmark_utils.get_oss_fuzz_builder_hash(benchmark)
    coverage_binaries_dir = exp_path.gcs(
        build_utils.get_coverage_binaries_dir())
    substitutions = {
        '_GCS_COVERAGE_BINARIES_DIR': coverage_binaries_dir,
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


def build_fuzzer_benchmark(fuzzer: str, benchmark: str) -> bool:
    """Builds |benchmark| for |fuzzer|."""
    logger.info('Building benchmark: %s, fuzzer: %s.', benchmark, fuzzer)
    try:
        if utils.is_local_experiment():
            image_name = 'build-{}-{}'.format(fuzzer, benchmark)
            make(image_name)
        elif benchmark_utils.is_oss_fuzz(benchmark):
            build_oss_fuzz_project_fuzzer(benchmark, fuzzer)
        else:
            build_benchmark_fuzzer(benchmark, fuzzer)
    except subprocess.CalledProcessError:
        logger.error('Failed to build benchmark: %s, fuzzer: %s.', benchmark,
                     fuzzer)
        return False
    logs.info('Done building benchmark: %s, fuzzer: %s.', benchmark, fuzzer)
    return True


def get_build_config_file(filename: str) -> str:
    """Return the path of the GCB build config file |filename|."""
    return os.path.join(utils.ROOT_DIR, 'experiment', 'gcb', filename)
