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
"""Module for building things locally for use in trials."""

import os
import shutil
from typing import Tuple

from common import benchmark_utils
from common import environment
from common import experiment_utils
from common import logs
from common import new_process
from common import utils

logger = logs.Logger()  # pylint: disable=invalid-name


def make(targets):
    """Invoke |make| with |targets| and return the result."""
    command = ['make', '-j'] + targets
    return new_process.execute(command, cwd=utils.ROOT_DIR)


def build_base_images() -> Tuple[int, str]:
    """Build base images locally."""
    return make(['base-image', 'worker'])


def get_shared_coverage_binaries_dir():
    """Returns the shared coverage binaries directory."""
    experiment_filestore_path = experiment_utils.get_experiment_filestore_path()
    return os.path.join(experiment_filestore_path, 'coverage-binaries')

def get_shared_mua_binaries_dir():
    """Returns the shared mua binaries directory."""
    experiment_filestore_path = experiment_utils.get_experiment_filestore_path()
    return os.path.join(experiment_filestore_path, 'mua-binaries')

def make_shared_coverage_binaries_dir():
    """Make the shared coverage binaries directory."""
    shared_coverage_binaries_dir = get_shared_coverage_binaries_dir()
    if os.path.exists(shared_coverage_binaries_dir):
        return
    os.makedirs(shared_coverage_binaries_dir)

def make_shared_mua_binaries_dir():
    """Make the shared mua binaries directory."""
    shared_mua_binaries_dir = get_shared_mua_binaries_dir()
    if os.path.exists(shared_mua_binaries_dir):
        return
    os.makedirs(shared_mua_binaries_dir)



def build_coverage(benchmark):
    """Build (locally) coverage image for benchmark."""
    image_name = f'build-coverage-{benchmark}'
    result = make([image_name])
    if result.retcode:
        return result
    make_shared_coverage_binaries_dir()
    copy_coverage_binaries(benchmark)
    return result

def build_mua(benchmark):
    """Build (locally) mua image for benchmark."""
    image_name = f'.mutation_analysis-{benchmark}-builder'
    result = make([image_name])
    if result.retcode:
        return result
    make_shared_mua_binaries_dir()
    prepare_mua_binaries(benchmark)
    return result

def create_dir(dir):
        if(not os.path.exists(dir)):
            os.makedirs(dir)
        return os.path.exists(dir)

def initialize_mua(benchmark, trial_num, fuzzer, corpus_dir):
    # find correct container and start it
    container_name = 'mutation_analysis_'+benchmark+'_container'

    docker_start_command = 'docker start '+container_name
    new_process.execute(docker_start_command.split(' '))

    shared_mua_binaries_dir = get_shared_mua_binaries_dir()
    

    # craft command, which is executed in mua container
    command = ''

    # copy corpus from self.corpus_dir into container
    command += '(touch /awesomeItWorks; )'
    
    corpi_dir = shared_mua_binaries_dir+'/corpi'
    fuzzer_corpi_dir = corpi_dir + '/' + fuzzer
    trial_corpi_dir = fuzzer_corpi_dir + '/' + str(trial_num)
    create_dir(corpi_dir)
    create_dir(fuzzer_corpi_dir)
    #create_dir(trial_corpi_dir)
    shutil.copytree(corpus_dir, trial_corpi_dir, dirs_exist_ok=True)

    # check which mutation are covered => these mutants are needed
    # check if needed mutants are in mutant storage
    # if mutants are in storage, copy into mutant directory        
    # if mutants are not in storage, build mutants and add to storage



    # execute command on container
    #command += '"'

    docker_exec_command = 'docker exec -t '+container_name+' /bin/bash -c'
    logger.info('mua initialize command:'+str(docker_exec_command))  
    docker_exec_command_formated = docker_exec_command.split(" ")
    docker_exec_command_formated.append(command)
    print(docker_exec_command_formated)
    new_process.execute(docker_exec_command_formated)


def prepare_mua_binaries(benchmark):
    """Run commands on mua container to prepare it"""
    project = benchmark_utils.get_project(benchmark)
    fuzz_target = benchmark_utils.get_fuzz_target(benchmark)

    shared_mua_binaries_dir = get_shared_mua_binaries_dir()
    mount_arg = f'{shared_mua_binaries_dir}:{shared_mua_binaries_dir}'
    builder_image_url = benchmark_utils.get_builder_image_url(
        benchmark, 'mutation_analysis', environment.get('DOCKER_REGISTRY'))
    
    mua_build_archive = f'mutation-analysis-build-{benchmark}.tar.gz'
    mua_build_archive_shared_dir_path = os.path.join(
        shared_mua_binaries_dir, mua_build_archive)
    
    container_name = 'mutation_analysis_'+benchmark+'_container'
    #new_image_name = builder_image_url+'_prepared'

    command = (
        '(python3 /mutator/mua_idle.py; '
        'touch /out/testentry; '
        'cd /src/'+project+' && /bin/mua_build_benchmark; '
        'cd /mutator && gradle build; '
        'ldconfig /mutator/build/install/LLVM_Mutation_Tool/lib/; '
        'pipx run hatch run src/mua_fuzzer_benchmark/eval.py locator_local --config-path /tmp/config.json --result-path /tmp/test/; '
        'cd /tmp && /tmp/test/progs/'+fuzz_target+'/'+fuzz_target+'.locator /benchmark.yaml; '
        'cd /mutator && python locator_signal_to_mutation_list.py --trigger-signal-dir /tmp/trigger_signal/ --prog xml --out /out/mua_all_list.json; '
        'cp /tmp/test/progs/'+fuzz_target+'/'+fuzz_target+'.locator /out/'+fuzz_target+'.locator; '
        'cp /tmp/config.json /out/config.json; '
        'tar -czvf '+mua_build_archive_shared_dir_path+' /out;'
        ')'
        )
    
    logger.info('mua prepare command:'+str(command))  
    docker_rm_command = 'docker rm -f '+container_name
    try:
        #print("docker rm")
        #print(docker_rm_command)
        new_process.execute(docker_rm_command.split(" "))
    except:
        pass
    
    new_process.execute([
        'docker', 'run', '--name', container_name, '-v', mount_arg, 
        '-e', 'FUZZ_OUTSIDE_EXPERIMENT=1',
        '-e', 'FORCE_LOCAL=1',
        '-e', 'TRIAL_ID=1',
        '-e', 'FUZZER=mutation_analysis',
        '-e', 'DEBUG_BUILDER=1',
        builder_image_url, '/bin/bash', '-c',
        command
    ])
    
    #docker_commit_command = 'docker commit '+container_name+' '+new_image_name
    #new_process.execute(docker_commit_command.split(' '))
    
    

def copy_coverage_binaries(benchmark):
    """Copy coverage binaries in a local experiment."""
    shared_coverage_binaries_dir = get_shared_coverage_binaries_dir()
    mount_arg = f'{shared_coverage_binaries_dir}:{shared_coverage_binaries_dir}'
    builder_image_url = benchmark_utils.get_builder_image_url(
        benchmark, 'coverage', environment.get('DOCKER_REGISTRY'))
    coverage_build_archive = f'coverage-build-{benchmark}.tar.gz'
    coverage_build_archive_shared_dir_path = os.path.join(
        shared_coverage_binaries_dir, coverage_build_archive)
    command = (
        '(cd /out; '
        f'tar -czvf {coverage_build_archive_shared_dir_path} * /src /work)')
    return new_process.execute([
        'docker', 'run', '-v', mount_arg, builder_image_url, '/bin/bash', '-c',
        command
    ])


def build_fuzzer_benchmark(fuzzer: str, benchmark: str) -> bool:
    """Builds |benchmark| for |fuzzer|."""
    image_name = f'build-{fuzzer}-{benchmark}'
    make([image_name])
