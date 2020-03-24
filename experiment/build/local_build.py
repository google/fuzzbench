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
import posixpath
from typing import Tuple

from common import benchmark_utils
from common import environment
from common import experiment_path as exp_path
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
    return new_process.execute(command, cwd=utils.ROOT_DIR)


def build_base_images() -> Tuple[int, str]:
    """Build base images on GCB."""
    return make('base-runner', 'base-builder')


def build_coverage(benchmark):
    """Build coverage image for benchmark on GCB."""
    image_name = 'build-coverage-{}'.format(benchmark)
    result = make(image_name)
    if result.retcode:
        return result
    local_copy_coverage_binaries(benchmark)
    return result


def local_copy_coverage_binaries(benchmark):
    """Copy coverage binaries in a local experiment."""
    shared_volume = os.environ['SHARED_VOLUME']

    shared_coverage_binaries_volume = os.path.join(shared_volume,
                                                   'coverage-binaries')

    # Use try-except to avoid a race by checking if it exists before
    # creating it.
    try:
        os.mkdir(shared_coverage_binaries_volume)
    except FileExistsError:
        pass

    mount_arg = '{0}:{0}'.format(shared_volume)
    runner_image_url = benchmark_utils.get_runner_image_url(
        benchmark, 'coverage', environment.get('CLOUD_PROJECT'))
    if benchmark_utils.is_oss_fuzz(benchmark):
        runner_image_url = runner_image_url.replace('runners', 'builders')
    docker_name = benchmark_utils.get_docker_name(benchmark)
    coverage_build_archive = 'coverage-build-{}.tar.gz'.format(docker_name)
    coverage_build_archive_shared_volume_path = os.path.join(
        shared_coverage_binaries_volume, coverage_build_archive)
    command = 'cd /out; tar -czvf {} *'.format(
        coverage_build_archive_shared_volume_path)
    new_process.execute([
        'docker', 'run', '-v', mount_arg, runner_image_url, '/bin/bash', '-c',
        command
    ])
    coverage_binaries_dir = build_utils.get_coverage_binaries_dir()
    coverage_build_archive_gcs_path = posixpath.join(
        exp_path.gcs(coverage_binaries_dir), coverage_build_archive)

    return gsutil.cp(coverage_build_archive_shared_volume_path,
                     coverage_build_archive_gcs_path)


def build_fuzzer_benchmark(fuzzer: str, benchmark: str) -> bool:
    """Builds |benchmark| for |fuzzer|."""
    image_name = 'build-{}-{}'.format(fuzzer, benchmark)
    make(image_name)
    return False
