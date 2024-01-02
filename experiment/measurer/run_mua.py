# Copyright 2023 Google LLC
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
"""Module for mutation testing measurer functionality."""

import os
from pathlib import Path
import shlex
import subprocess
import time
from common import logs
from common import benchmark_utils
from common import experiment_utils
from common import new_process
from common import environment
from experiment.build import build_utils
from experiment.exec_id import read_exec_id

logger = logs.Logger()

MUTATION_ANALYSIS_IMAGE_NAME = 'mutation_analysis'

GOOGLE_CLOUD_MUA_MAPPED_DIR = '/etc/mua_out/'

EXEC_ID = None


def get_container_name(benchmark):
    """Return the container name for the given benchmark."""
    return f'mutation_analysis_{benchmark}_container'


def get_host_mua_out_dir():
    """Return the host directory where mua_out is mapped."""
    if experiment_utils.is_local_experiment():
        return Path(os.environ.get('HOST_MUA_OUT_DIR',
                                   '/tmp/mua_out')).absolute()
    return Path(GOOGLE_CLOUD_MUA_MAPPED_DIR)


def get_dispatcher_mua_out_dir():
    """Return the dispatcher directory where mua_out is mapped to."""
    return Path('/mua_out/')


def stop_mua_container(benchmark):
    """Stop the mua container for the benchmark."""
    container_name = get_container_name(benchmark)
    try:
        new_process.execute(['docker', 'rm', '-f', container_name])
    except subprocess.CalledProcessError:
        pass


def run_mua_container(benchmark):
    """Run commands on mua container to prepare it"""
    experiment_name = experiment_utils.get_experiment_name()
    host_mua_out_dir = get_host_mua_out_dir()
    shared_mua_binaries_dir = host_mua_out_dir / experiment_name
    docker_mua_binaries_dir = f'/mapped/{experiment_name}'
    mount_arg = f'{shared_mua_binaries_dir}:{docker_mua_binaries_dir}'
    os.makedirs(shared_mua_binaries_dir, exist_ok=True)

    builder_image_url = benchmark_utils.get_builder_image_url(
        benchmark, MUTATION_ANALYSIS_IMAGE_NAME,
        environment.get('DOCKER_REGISTRY'))

    container_name = get_container_name(benchmark)

    host_mua_mapped_dir = os.environ.get('HOST_MUA_MAPPED_DIR')

    mua_run_cmd = [
        'docker', 'run', '--init', '-it', '--detach', '--name', container_name,
        '-v', mount_arg, *([] if host_mua_mapped_dir is None else
                           ['-v', f'{host_mua_mapped_dir}:/mapped_dir']),
        builder_image_url, '/bin/bash', '-c', 'sleep infinity'
    ]

    mua_run_res = new_process.execute(mua_run_cmd, expect_zero=False)
    if mua_run_res.retcode != 0:
        if 'Conflict. The container name' in mua_run_res.output:
            logger.debug('mua container already running')
            return
        logger.error('could not run mua container:\n' +
                     f'command: {mua_run_cmd}\n' +
                     f'returncode: {mua_run_res.retcode}\n' +
                     f'timed_out: {mua_run_res.timed_out}\n' +
                     f'{mua_run_res.output}')
        raise Exception('Could not run mua container.')


def mua_container_is_running(benchmark):
    """Return true if the mua container is started."""
    container_name = get_container_name(benchmark)
    try:
        res = new_process.execute(
            ['docker', 'inspect', '-f', '{{.State.Running}}', container_name],
            expect_zero=False)
        if res.retcode != 0:
            return False
        if res.output.strip() == 'true':
            return True
        return False
    except subprocess.CalledProcessError:
        return False


def ensure_mua_container_running(benchmark):
    """Start the mutation analysis container for the benchmark."""
    if mua_container_is_running(benchmark):
        return

    # find correct container and start it
    container_name = get_container_name(benchmark)

    docker_start_command = ['docker', 'start', container_name]
    res = new_process.execute(docker_start_command, expect_zero=False)
    if res.retcode != 0:
        logger.info('Could not start mua container, using run instead.')
        run_mua_container(benchmark)


def copy_mua_stats_db(benchmark, mua_results_dir):
    """Copy the stats db from the container to the mua results dir."""
    # Wait a bit if the container was just started
    for _ in range(10):
        if mua_container_is_running(benchmark):
            break
        logger.debug('Waiting for mua container to start.')
        time.sleep(1)

    container_name = get_container_name(benchmark)
    corpus_run_stats_db = mua_results_dir / 'stats.sqlite'

    if not corpus_run_stats_db.is_file():
        logger.info(
            f'Copying stats db from container to: {corpus_run_stats_db}')

        copy_stats_db_command = [
            'docker', 'cp', f'{container_name}:/mua_build/build/stats.db',
            str(corpus_run_stats_db)
        ]
        logger.debug(f'mua copy stats db command: {copy_stats_db_command}')
        new_process.execute(copy_stats_db_command, write_to_stdout=True)
        build_utils.store_mua_stats_db(corpus_run_stats_db, benchmark)


def run_mua_build_ids(benchmark, trial_num, fuzzer, cycle):
    """Run mua_build_ids.py on the container."""
    global EXEC_ID
    if EXEC_ID is None:
        EXEC_ID = read_exec_id()
        logger.debug('Setting EXEC_ID to %s', EXEC_ID)

    container_name = get_container_name(benchmark)
    # get additional info from commons
    experiment_name = experiment_utils.get_experiment_name()
    fuzz_target = benchmark_utils.get_fuzz_target(benchmark)

    # execute command on container
    command = [
        'python3',
        '/mutator/mua_build_ids.py',
        str(EXEC_ID),
        fuzz_target,
        benchmark,
        experiment_name,
        fuzzer,
        str(trial_num),
        # "--debug_num_mutants=200"
    ]

    docker_exec_command = [
        'docker', 'exec', '-t', container_name, '/bin/bash', '-c',
        shlex.join(command)
    ]

    logger.debug(f'mua_build_ids command: {docker_exec_command}')
    mua_build_res = new_process.execute(docker_exec_command)
    logger.info(f'mua_build_ids result: {mua_build_res.retcode} ' +
                f'timed_out: {mua_build_res.timed_out}\n' +
                f'{mua_build_res.output}')
    build_utils.store_mua_build_log(mua_build_res.output or '', benchmark,
                                    fuzzer, trial_num, cycle)
