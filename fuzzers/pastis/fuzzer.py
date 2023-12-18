# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""Integration code for PASTIS fuzzer."""

import os
import shutil
import subprocess

from fuzzers import utils
from fuzzers.aflplusplus import fuzzer as aflplusplus_fuzzer
from fuzzers.honggfuzz import fuzzer as honggfuzz_fuzzer

TRITONDSE_CONF = """{{
    "seed_format": "RAW",
    "pipe_stdout": false,
    "pipe_stderr": false,
    "skip_sleep_routine": true,
    "smt_solver": "BITWUZLA",
    "smt_timeout": 5000,
    "execution_timeout": 300,
    "exploration_timeout": 0,
    "exploration_limit": 0,
    "thread_scheduling": 200,
    "smt_queries_limit": 0,
    "smt_enumeration_limit": 40,
    "coverage_strategy": "PREFIXED_EDGE",
    "branch_solving_strategy": [
        "ALL_NOT_COVERED"
    ],
    "debug": false,
    "workspace": "",
    "program_argv": {program_argv},
    "time_inc_coefficient": 1e-05,
    "skip_unsupported_import": false,
    "memory_segmentation": true,
    "custom": {{}}
}}
"""


def get_fuzzers_dir(output_directory):
    """Return path to fuzzers directory."""
    return os.path.join(output_directory, 'fuzzers')


def get_aflpp_target_dir(output_directory):
    """Return path to AFL++'s target directory."""
    return os.path.join(output_directory, 'target-aflpp')


def get_honggfuzz_target_dir(output_directory):
    """Return path to Honggfuzz's target directory."""
    return os.path.join(output_directory, 'target-hf')


def get_targets_dir(output_directory):
    """Return path to targets directory."""
    return os.path.join(output_directory, 'targets')


def build_aflpp():
    """Build benchmark with AFL++."""
    print('Building with AFL++')

    out_dir = os.environ['OUT']

    aflpp_target_dir = get_aflpp_target_dir(os.environ['OUT'])

    os.environ['OUT'] = aflpp_target_dir

    src = os.getenv('SRC')
    work = os.getenv('WORK')

    with utils.restore_directory(src), utils.restore_directory(work):
        # Restore SRC to its initial state so we can build again without any
        # trouble. For some OSS-Fuzz projects, build_benchmark cannot be run
        # twice in the same directory without this.
        aflplusplus_fuzzer.build()

    os.environ['OUT'] = out_dir

    fuzzers_dir = get_fuzzers_dir(os.environ['OUT'])
    shutil.move(os.path.join(aflpp_target_dir, 'afl-fuzz'),
                os.path.join(fuzzers_dir, 'afl-fuzz'))


def build_honggfuzz():
    """Build benchmark with Honggfuzz."""
    print('Building with Honggfuzz')

    out_dir = os.environ['OUT']

    hf_target_dir = get_honggfuzz_target_dir(os.environ['OUT'])

    os.environ['OUT'] = hf_target_dir

    src = os.getenv('SRC')
    work = os.getenv('WORK')

    with utils.restore_directory(src), utils.restore_directory(work):
        # Restore SRC to its initial state so we can build again without any
        # trouble. For some OSS-Fuzz projects, build_benchmark cannot be run
        # twice in the same directory without this.
        honggfuzz_fuzzer.build()

    os.environ['OUT'] = out_dir

    fuzzers_dir = get_fuzzers_dir(os.environ['OUT'])
    shutil.move(os.path.join(hf_target_dir, 'honggfuzz'),
                os.path.join(fuzzers_dir, 'honggfuzz'))


def build_tritondse():
    """Build benchmark with TritonDSE."""
    print('Building with TritonDSE')

    new_env = os.environ.copy()

    new_env['CC'] = 'clang'
    new_env['CXX'] = 'clang++'
    new_env['FUZZER_LIB'] = '/libStandaloneFuzzTarget.a'

    src = new_env['SRC']
    work = new_env['WORK']

    with utils.restore_directory(src), utils.restore_directory(work):
        # Restore SRC to its initial state so we can build again without any
        # trouble. For some OSS-Fuzz projects, build_benchmark cannot be run
        # twice in the same directory without this.
        utils.build_benchmark(env=new_env)


def prepare_build_environment():
    """Prepare build environment."""
    aflpp_target_dir = get_aflpp_target_dir(os.environ['OUT'])
    honggfuzz_target_dir = get_honggfuzz_target_dir(os.environ['OUT'])
    targets_dir = get_targets_dir(os.environ['OUT'])

    fuzzers_dir = get_fuzzers_dir(os.environ['OUT'])

    os.makedirs(aflpp_target_dir, exist_ok=True)
    os.makedirs(honggfuzz_target_dir, exist_ok=True)
    os.makedirs(targets_dir, exist_ok=True)
    os.makedirs(fuzzers_dir, exist_ok=True)


def build():
    """Build benchmark."""
    prepare_build_environment()

    build_tritondse()
    build_aflpp()
    build_honggfuzz()


def prepare_fuzz_environment():
    """Prepare fuzz environment."""
    os.environ['AFLPP_PATH'] = get_fuzzers_dir(os.environ['OUT'])
    os.environ['HFUZZ_PATH'] = get_fuzzers_dir(os.environ['OUT'])


def prepare_tritondse_config(base_dir, target_binary):
    """Prepare TritonDSE configuration."""
    config_dir = os.path.join(base_dir, 'triton_confs')

    os.makedirs(config_dir, exist_ok=True)

    config_filename = os.path.join(config_dir, 'conf1.json')

    target_binary_name = os.path.basename(target_binary)

    program_argv = f'["{target_binary_name}_tt", "@@"]'

    with open(config_filename, 'w', encoding='utf8') as config_file:
        config_file.write(TRITONDSE_CONF.format(program_argv=program_argv))


def fuzz(input_corpus, output_corpus, target_binary):
    """Run pastis-benchmark on target."""
    prepare_fuzz_environment()

    prepare_tritondse_config(output_corpus, target_binary)

    targets_dir = get_targets_dir(os.environ['OUT'])

    target_binary_name = os.path.basename(target_binary)

    # Copy and rename AFL++ target binary.
    aflpp_target_dir = get_aflpp_target_dir(os.environ['OUT'])
    shutil.copy(os.path.join(aflpp_target_dir, target_binary_name),
                os.path.join(targets_dir, target_binary_name + '_aflpp'))

    # Copy and rename Honggfuzz target binary.
    honggfuzz_target_dir = get_honggfuzz_target_dir(os.environ['OUT'])
    shutil.copy(os.path.join(honggfuzz_target_dir, target_binary_name),
                os.path.join(targets_dir, target_binary_name + '_hf'))

    # Copy and rename TritonDSE target binary.
    shutil.copy(os.path.join(os.environ['OUT'], target_binary_name),
                os.path.join(targets_dir, target_binary_name + '_tt'))

    # Copy and rename the dictionary file in case it exists (AFL++).
    dictionary_path = os.path.join(aflpp_target_dir, 'afl++.dict')
    if os.path.exists(dictionary_path):
        shutil.copy(
            dictionary_path,
            os.path.join(targets_dir, target_binary_name + '_aflpp.dict'))

    # Copy and rename the dictionary file in case it exists (Honggfuzz).
    dictionary_path = utils.get_dictionary_path(target_binary)
    if dictionary_path and os.path.exists(dictionary_path):
        shutil.copy(dictionary_path,
                    os.path.join(targets_dir, target_binary_name + '_hf.dict'))

    # Copy cmplog directory if it exists.
    cmplog_path = os.path.join(aflpp_target_dir, 'cmplog', target_binary_name)
    if os.path.exists(cmplog_path):
        shutil.copy(
            cmplog_path,
            os.path.join(targets_dir, target_binary_name + '_aflpp.cmplog'))

    # Prepare command-line string.
    command = [
        'pastis-benchmark',
        'run',
        '-b',
        targets_dir,
        '-w',
        output_corpus,
        '-s',
        input_corpus,
        '-m',
        'FULL',
        '-i',
        'ARGV',
        '-p',
        '5551',
        '--triton',
        '--hfuzz',
        '--hfuzz-threads',
        '1',
        '--aflpp',
        '--skip-cpufreq',
    ]

    print('[fuzz] Running command: ' + ' '.join(command))
    ret_code = subprocess.call(command)
    print(f'Return code: {ret_code}')
