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

import shlex
import uuid
from common import logs
from common import benchmark_utils
from common import experiment_utils
from common import new_process
from experiment.build import build_utils


logger = logs.Logger()

# Exec id is used to identify the current run, if the dispatcher container
# is preempted the exec id will change. This allows us to identify which actions
# were performed by earlier runs and which were performed by the current run.
# We use this to identify which mutants builds were interrupted by a
# preemption.
EXEC_ID = uuid.uuid4()


def get_container_name(benchmark):
    """Return the container name for the given benchmark."""
    return f'mutation_analysis_{benchmark}_container'


def start_mua_container(benchmark):
    """Start the mutation analysis container for the benchmark."""
    # find correct container and start it
    container_name = get_container_name(benchmark)

    docker_start_command = 'docker start ' + container_name
    new_process.execute(docker_start_command.split(' '))


def copy_mua_stats_db(benchmark, mua_results_dir):
    """Copy the stats db from the container to the mua results dir."""
    container_name = get_container_name(benchmark)
    corpus_run_stats_db = mua_results_dir / 'stats.sqlite'

    if not corpus_run_stats_db.is_file():
        logger.info(
            f'Copying stats db from container to: {corpus_run_stats_db}')

        copy_stats_db_command = [
            'docker', 'cp', f'{container_name}:/mua_build/build/stats.db',
            str(corpus_run_stats_db)
        ]
        logger.info(f'mua copy stats db command: {copy_stats_db_command}')
        new_process.execute(copy_stats_db_command, write_to_stdout=True)
        build_utils.store_mua_stats_db(corpus_run_stats_db, benchmark)


def run_mua_build_ids(benchmark, trial_num, fuzzer, cycle):
    """Run mua_build_ids.py on the container."""
    container_name = get_container_name(benchmark)
    # get additional info from commons
    experiment_name = experiment_utils.get_experiment_name()
    fuzz_target = benchmark_utils.get_fuzz_target(benchmark)

    # execute command on container
    command = [
        'python3', '/mutator/mua_build_ids.py',
        str(EXEC_ID), fuzz_target, experiment_name, fuzzer,
        str(trial_num), '--debug_num_mutants=10'
    ]

    docker_exec_command = [
        'docker', 'exec', '-t', container_name, '/bin/bash', '-c',
        shlex.join(command)
    ]

    logger.info(f'mua_build_ids command: {docker_exec_command}')
    mua_build_res = new_process.execute(docker_exec_command)
    logger.info(f'mua_build_ids result: {mua_build_res}')
    build_utils.store_mua_build_log(mua_build_res.output, benchmark,
                                    fuzzer, cycle)
