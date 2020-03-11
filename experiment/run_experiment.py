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
"""Creates a dispatcher VM in GCP and sends it all the files and configurations
it needs to begin an experiment."""

import argparse
import multiprocessing
import os
import re
import shutil
import sys
from typing import Dict, List

import yaml

from common import experiment_utils
from common import filesystem
from common import gcloud
from common import gsutil
from common import logs
from common import utils
from common import yaml_utils
from experiment import stop_experiment

BENCHMARKS_DIR = os.path.join(utils.ROOT_DIR, 'benchmarks')
FUZZERS_DIR = os.path.join(utils.ROOT_DIR, 'fuzzers')
OSS_FUZZ_PROJECTS_DIR = os.path.join(utils.ROOT_DIR, 'third_party', 'oss-fuzz',
                                     'projects')
FUZZER_NAME_REGEX = re.compile('^[a-z0-9_]+$')
EXPERIMENT_CONFIG_REGEX = re.compile('^[a-z0-9-]{0,30}$')


def read_and_validate_experiment_config(config_filename: str) -> Dict:
    """Reads |config_filename|, validates it, and returns it."""
    # TODO(metzman) Consider exceptioning early instead of logging error. It
    # will be less useful for users but will simplify this code quite a bit. And
    # it isn't like anything expensive happens before this validation is done so
    # rerunning it is cheap.
    config = yaml_utils.read(config_filename)
    bucket_params = {'cloud_experiment_bucket', 'cloud_web_bucket'}
    string_params = {
        'cloud_compute_zone', 'cloud_experiment_bucket', 'cloud_web_bucket'
    }
    int_params = {'trials', 'max_total_time'}
    required_params = int_params.union(string_params)

    valid = True
    for param in required_params:
        if param not in config:
            valid = False
            logs.error('Config does not contain "%s".', param)
            continue

        value = config[param]
        if param in int_params and not isinstance(value, int):
            valid = False
            logs.error('Config parameter "%s" is "%s". It must be an int.',
                       param, value)
            continue

        if param in string_params and (not isinstance(value, str) or
                                       value != value.lower()):
            valid = False
            logs.error(
                'Config parameter "%s" is "%s". It must be a lowercase string.',
                param, str(value))
            continue

        if param in bucket_params and not value.startswith('gs://'):
            valid = False
            logs.error(
                'Config parameter "%s" is "%s". It must start with gs://.',
                param, value)

    if not valid:
        raise ValidationError('Config: %s is invalid.' % config_filename)
    return config


class ValidationError(Exception):
    """Error validating user input to this program."""


def get_directories(parent_dir):
    """Returns a list of subdirectories in |parent_dir|."""
    return [
        directory for directory in os.listdir(parent_dir)
        if os.path.isdir(os.path.join(parent_dir, directory))
    ]


def validate_benchmarks(benchmarks: List[str]):
    """Parses and validates list of benchmarks."""
    for benchmark in set(benchmarks):
        if benchmarks.count(benchmark) > 1:
            raise Exception('Benchmark "%s" is included more than once.' %
                            benchmark)


def validate_fuzzer(fuzzer: str):
    """Parses and validates a fuzzer name."""
    if not re.match(FUZZER_NAME_REGEX, fuzzer):
        raise Exception(
            'Fuzzer "%s" may only contain lowercase letters, numbers, '
            'or underscores.' % fuzzer)

    fuzzers_directories = get_directories(FUZZERS_DIR)
    if fuzzer not in fuzzers_directories:
        raise Exception('Fuzzer "%s" does not exist.' % fuzzer)


def validate_fuzzer_config(fuzzer_config_name: str):
    """Validate |fuzzer_config_name|."""
    allowed_fields = ['variant_name', 'env', 'fuzzer']
    fuzzer_config = yaml_utils.read(fuzzer_config_name)
    if 'fuzzer' not in fuzzer_config:
        raise Exception('Fuzzer configuration must include the "fuzzer" field.')

    for key in fuzzer_config:
        if key not in allowed_fields:
            raise Exception('Invalid entry "%s" in fuzzer configuration "%s"' %
                            (key, fuzzer_config_name))

    variant_name = fuzzer_config.get('variant_name')
    if variant_name:
        if not re.match(FUZZER_NAME_REGEX, variant_name):
            raise Exception(
                'The "variant_name" option may only contain lowercase letters, '
                'numbers, or underscores.')
    fuzzer_name = fuzzer_config.get('fuzzer')
    if fuzzer_name:
        validate_fuzzer(fuzzer_name)


def validate_experiment_name(experiment_name: str):
    """Validate |experiment_name| so that it can be used in creating
    instances."""
    if not re.match(EXPERIMENT_CONFIG_REGEX, experiment_name):
        raise Exception('Experiment name "%s" is invalid. Must match: "%s"' %
                        (experiment_name, EXPERIMENT_CONFIG_REGEX.pattern))


def start_experiment(experiment_name: str, config_filename: str,
                     benchmarks: List[str], fuzzers: List[str],
                     fuzzer_configs: List[str]):
    """Start a fuzzer benchmarking experiment."""
    validate_benchmarks(benchmarks)

    config = read_and_validate_experiment_config(config_filename)
    config['benchmarks'] = ','.join(benchmarks)
    validate_experiment_name(experiment_name)
    config['experiment'] = experiment_name

    config_dir = 'config'
    filesystem.recreate_directory(config_dir)
    experiment_config_filename = os.path.join(config_dir, 'experiment.yaml')
    with open(experiment_config_filename, 'w') as experiment_config_file:
        yaml.dump(config, experiment_config_file, default_flow_style=False)

    if not fuzzers and not fuzzer_configs:
        raise Exception('Need to provide either a list of fuzzers or '
                        'a list of fuzzer configs.')

    fuzzer_config_dir = os.path.join(config_dir, 'fuzzer-configs')
    filesystem.recreate_directory(fuzzer_config_dir)
    for fuzzer_config in fuzzer_configs:
        if fuzzer_configs.count(fuzzer_config) > 1:
            raise Exception('Fuzzer config "%s" provided more than once.' %
                            fuzzer_config)
        # Validate the fuzzer yaml attributes e.g. fuzzer, env, etc.
        validate_fuzzer_config(fuzzer_config)
        shutil.copy(fuzzer_config, fuzzer_config_dir)
    for fuzzer in fuzzers:
        if fuzzers.count(fuzzer) > 1:
            raise Exception('Fuzzer "%s" provided more than once.' % fuzzer)
        validate_fuzzer(fuzzer)
        fuzzer_config_file_path = os.path.join(fuzzer_config_dir, fuzzer)
        # Create a simple yaml with just the fuzzer attribute.
        with open(fuzzer_config_file_path, 'w') as file_handle:
            file_handle.write('fuzzer: ' + fuzzer)

    # Make sure we can connect to database.
    if 'POSTGRES_PASSWORD' not in os.environ:
        raise Exception('Must set POSTGRES_PASSWORD environment variable.')

    gcloud.set_default_project(config['cloud_project'])

    dispatcher = Dispatcher(config)
    if not os.getenv('MANUAL_EXPERIMENT'):
        dispatcher.create_async()
    copy_resources_to_bucket(config_dir, config)
    if not os.getenv('MANUAL_EXPERIMENT'):
        dispatcher.start()


def copy_resources_to_bucket(config_dir: str, config: Dict):
    """Copy resources the dispatcher will need for the experiment to the
    cloud_experiment_bucket."""
    cloud_experiment_path = os.path.join(config['cloud_experiment_bucket'],
                                         config['experiment'])
    base_destination = os.path.join(cloud_experiment_path, 'input')

    # Send the local source repository to the cloud for use by dispatcher.
    # Local changes to any file will propagate.
    # Filter out unnecessary directories.
    options = [
        '-x',
        ('^\\.git/|^\\.pytype/|^\\.venv/|^.*\\.pyc$|^__pycache__/'
         '|.*~$|\\.pytest_cache/|.*/test_data/|^third_party/oss-fuzz/out/'
         '|^docs/')
    ]
    destination = os.path.join(base_destination, 'src')
    gsutil.rsync(utils.ROOT_DIR, destination, options=options)

    # Send config files.
    destination = os.path.join(base_destination, 'config')
    gsutil.rsync(config_dir, destination)


class Dispatcher:
    """Class representing the dispatcher instance."""

    def __init__(self, config: Dict):
        self.config = config
        self.instance_name = experiment_utils.get_dispatcher_instance_name(
            config['experiment'])
        self.process = None

    def create_async(self):
        """Creates the instance asynchronously."""
        self.process = multiprocessing.Process(
            target=gcloud.create_instance,
            args=(self.instance_name, gcloud.InstanceType.DISPATCHER,
                  self.config))
        self.process.start()

    def start(self):
        """Start the experiment on the dispatcher."""
        # TODO(metzman): Replace this workflow with a startup script so we don't
        # need to SSH into the dispatcher.
        self.process.join()  # Wait for dispatcher instance.
        # Check that we can SSH into the instance.
        gcloud.robust_begin_gcloud_ssh(self.instance_name,
                                       self.config['cloud_compute_zone'])

        base_docker_tag = experiment_utils.get_base_docker_tag(
            self.config['cloud_project'])
        cloud_sql_instance_connection_name = (
            self.config['cloud_sql_instance_connection_name'])

        command = (
            'echo 0 | sudo tee /proc/sys/kernel/yama/ptrace_scope && '
            'docker run --rm '
            '-e INSTANCE_NAME="{instance_name}" '
            '-e EXPERIMENT="{experiment}" '
            '-e CLOUD_PROJECT="{cloud_project}" '
            '-e CLOUD_EXPERIMENT_BUCKET="{cloud_experiment_bucket}" '
            '-e POSTGRES_PASSWORD="{postgres_password}" '
            '-e CLOUD_SQL_INSTANCE_CONNECTION_NAME='
            '"{cloud_sql_instance_connection_name}" '
            '--cap-add=SYS_PTRACE --cap-add=SYS_NICE '
            '-v /var/run/docker.sock:/var/run/docker.sock '
            '--name=dispatcher-container '
            '{base_docker_tag}/dispatcher-image '
            '/work/startup-dispatcher.sh'
        ).format(
            instance_name=self.instance_name,
            postgres_password=os.environ['POSTGRES_PASSWORD'],
            experiment=self.config['experiment'],
            # TODO(metzman): Create a function that sets env vars based on
            # the contents of a dictionary, and use it instead of hardcoding
            # the configs we use.
            cloud_project=self.config['cloud_project'],
            cloud_experiment_bucket=self.config['cloud_experiment_bucket'],
            cloud_sql_instance_connection_name=(
                cloud_sql_instance_connection_name),
            base_docker_tag=base_docker_tag,
        )
        return gcloud.ssh(self.instance_name,
                          command=command,
                          zone=self.config['cloud_compute_zone'])


def get_all_benchmarks():
    """Returns the list of all benchmarks."""
    benchmarks_dir = os.path.join(utils.ROOT_DIR, 'benchmarks')
    all_benchmarks = []
    for benchmark in os.listdir(benchmarks_dir):
        benchmark_path = os.path.join(benchmarks_dir, benchmark)
        if os.path.isfile(os.path.join(benchmark_path, 'oss-fuzz.yaml')):
            # Benchmark is an OSS-Fuzz benchmark.
            all_benchmarks.append(benchmark)
        elif os.path.isfile(os.path.join(benchmark_path, 'build.sh')):
            # Benchmark is a standard benchmark.
            all_benchmarks.append(benchmark)
    return all_benchmarks


def main():
    """Run an experiment in the cloud."""
    logs.initialize()

    parser = argparse.ArgumentParser(
        description='Begin an experiment that evaluates fuzzers on one or '
        'more benchmarks.')

    all_benchmarks = get_all_benchmarks()

    parser.add_argument('-b',
                        '--benchmarks',
                        help='Benchmark names. All of them by default.',
                        nargs='+',
                        required=False,
                        default=all_benchmarks,
                        choices=all_benchmarks)
    parser.add_argument('-c',
                        '--experiment-config',
                        help='Path to the experiment configuration yaml file.',
                        required=True)
    parser.add_argument('-e',
                        '--experiment-name',
                        help='Experiment name.',
                        required=True)
    parser.add_argument('-f',
                        '--fuzzers',
                        help='Fuzzers to use.',
                        nargs='+',
                        required=False,
                        default=[])
    parser.add_argument('-fc',
                        '--fuzzer-configs',
                        help='Fuzzer configurations to use.',
                        nargs='+',
                        required=False,
                        default=[])
    args = parser.parse_args()

    start_experiment(args.experiment_name, args.experiment_config,
                     args.benchmarks, args.fuzzers, args.fuzzer_configs)
    if not os.getenv('MANUAL_EXPERIMENT'):
        stop_experiment.stop_experiment(args.experiment_name,
                                        args.experiment_config)
    return 0


if __name__ == '__main__':
    sys.exit(main())
