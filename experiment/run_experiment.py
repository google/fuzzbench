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
import os
import re
import subprocess
import sys
import tarfile
import tempfile
from typing import Dict, List

import jinja2
import yaml

from common import benchmark_utils
from common import experiment_utils
from common import filesystem
from common import fuzzer_utils
from common import gcloud
from common import gsutil
from common import filestore_utils
from common import logs
from common import new_process
from common import utils
from common import yaml_utils

BENCHMARKS_DIR = os.path.join(utils.ROOT_DIR, 'benchmarks')
FUZZERS_DIR = os.path.join(utils.ROOT_DIR, 'fuzzers')
OSS_FUZZ_PROJECTS_DIR = os.path.join(utils.ROOT_DIR, 'third_party', 'oss-fuzz',
                                     'projects')
RESOURCES_DIR = os.path.join(utils.ROOT_DIR, 'experiment', 'resources')
FUZZER_NAME_REGEX = re.compile(r'^[a-z][a-z0-9_]+$')
EXPERIMENT_CONFIG_REGEX = re.compile(r'^[a-z0-9-]{0,30}$')
FILTER_SOURCE_REGEX = re.compile(r'('
                                 r'^\.git/|'
                                 r'^\.pytype/|'
                                 r'^\.venv/|'
                                 r'^.*\.pyc$|'
                                 r'^__pycache__/|'
                                 r'.*~$|'
                                 r'\#*\#$|'
                                 r'\.pytest_cache/|'
                                 r'.*/test_data/|'
                                 r'^third_party/oss-fuzz/build/|'
                                 r'^docker/generated.mk$|'
                                 r'^docs/)')
_OSS_FUZZ_CORPUS_BACKUP_URL_FORMAT = (
    'gs://{project}-backup.clusterfuzz-external.appspot.com/corpus/'
    'libFuzzer/{fuzz_target}/public.zip')


def read_and_validate_experiment_config(config_filename: str) -> Dict:
    """Reads |config_filename|, validates it, finds as many errors as possible,
    and returns it."""
    config = yaml_utils.read(config_filename)
    filestore_params = {'experiment_filestore', 'report_filestore'}
    cloud_config = {'cloud_compute_zone', 'cloud_project'}
    docker_config = {'docker_registry'}
    string_params = cloud_config.union(filestore_params).union(docker_config)
    int_params = {'trials', 'max_total_time'}
    required_params = int_params.union(filestore_params).union(docker_config)
    bool_params = {'private', 'merge_with_nonprivate'}

    local_experiment = config.get('local_experiment', False)
    snapshot_period = config.get('snapshot_period',
                                 experiment_utils.DEFAULT_SNAPSHOT_SECONDS)
    if not local_experiment:
        required_params = required_params.union(cloud_config)

    valid = True
    if 'cloud_experiment_bucket' in config or 'cloud_web_bucket' in config:
        logs.error('"cloud_experiment_bucket" and "cloud_web_bucket" are now '
                   '"experiment_filestore" and "report_filestore".')

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

        if param in bool_params and not isinstance(value, bool):
            valid = False
            logs.error('Config parameter "%s" is "%s". It must be a bool.',
                       param, str(value))
            continue

        if param not in filestore_params:
            continue

        if local_experiment and not value.startswith('/'):
            valid = False
            logs.error(
                'Config parameter "%s" is "%s". Local experiments only support '
                'using Posix file systems as filestores.', param, value)
            continue

        if not local_experiment and not value.startswith('gs://'):
            valid = False
            logs.error(
                'Config parameter "%s" is "%s". '
                'It must start with gs:// when running on Google Cloud.', param,
                value)

    if not valid:
        raise ValidationError('Config: %s is invalid.' % config_filename)

    config['local_experiment'] = local_experiment
    config['snapshot_period'] = snapshot_period
    return config


class ValidationError(Exception):
    """Error validating user input to this program."""


def get_directories(parent_dir):
    """Returns a list of subdirectories in |parent_dir|."""
    return [
        directory for directory in os.listdir(parent_dir)
        if os.path.isdir(os.path.join(parent_dir, directory))
    ]


# pylint: disable=too-many-locals
def validate_custom_seed_corpus(custom_seed_corpus_dir, benchmarks):
    """Validate seed corpus provided by user"""
    if not os.path.isdir(custom_seed_corpus_dir):
        raise ValidationError('Corpus location "%s" is invalid.' %
                              custom_seed_corpus_dir)

    for benchmark in benchmarks:
        benchmark_corpus_dir = os.path.join(custom_seed_corpus_dir, benchmark)
        if not os.path.exists(benchmark_corpus_dir):
            raise ValidationError('Custom seed corpus directory for '
                                  'benchmark "%s" does not exist.' % benchmark)
        if not os.path.isdir(benchmark_corpus_dir):
            raise ValidationError('Seed corpus of benchmark "%s" must be '
                                  'a directory.' % benchmark)
        if not os.listdir(benchmark_corpus_dir):
            raise ValidationError('Seed corpus of benchmark "%s" is empty.' %
                                  benchmark)


def validate_benchmarks(benchmarks: List[str]):
    """Parses and validates list of benchmarks."""
    benchmark_types = set()
    for benchmark in set(benchmarks):
        if benchmarks.count(benchmark) > 1:
            raise ValidationError('Benchmark "%s" is included more than once.' %
                                  benchmark)
        # Validate benchmarks here. It's possible someone might run an
        # experiment without going through presubmit. Better to catch an invalid
        # benchmark than see it in production.
        if not benchmark_utils.validate(benchmark):
            raise ValidationError('Benchmark "%s" is invalid.' % benchmark)

        benchmark_types.add(benchmark_utils.get_type(benchmark))

    if (benchmark_utils.BenchmarkType.CODE.value in benchmark_types and
            benchmark_utils.BenchmarkType.BUG.value in benchmark_types):
        raise ValidationError(
            'Cannot mix bug benchmarks with code coverage benchmarks.')


def validate_fuzzer(fuzzer: str):
    """Parses and validates a fuzzer name."""
    if not fuzzer_utils.validate(fuzzer):
        raise ValidationError('Fuzzer: %s is invalid.' % fuzzer)


def validate_experiment_name(experiment_name: str):
    """Validate |experiment_name| so that it can be used in creating
    instances."""
    if not re.match(EXPERIMENT_CONFIG_REGEX, experiment_name):
        raise ValidationError(
            'Experiment name "%s" is invalid. Must match: "%s"' %
            (experiment_name, EXPERIMENT_CONFIG_REGEX.pattern))


def set_up_experiment_config_file(config):
    """Set up the config file that will actually be used in the
    experiment (not the one given to run_experiment.py)."""
    filesystem.recreate_directory(experiment_utils.CONFIG_DIR)
    experiment_config_filename = (
        experiment_utils.get_internal_experiment_config_relative_path())
    with open(experiment_config_filename, 'w') as experiment_config_file:
        yaml.dump(config, experiment_config_file, default_flow_style=False)


def check_no_uncommitted_changes():
    """Make sure that there are no uncommitted changes."""
    if subprocess.check_output(['git', 'diff'], cwd=utils.ROOT_DIR):
        raise ValidationError('Local uncommitted changes found, exiting.')


def get_git_hash():
    """Return the git hash for the last commit in the local repo."""
    output = subprocess.check_output(['git', 'rev-parse', 'HEAD'],
                                     cwd=utils.ROOT_DIR)
    return output.strip().decode('utf-8')


def start_experiment(  # pylint: disable=too-many-arguments
        experiment_name: str,
        config_filename: str,
        benchmarks: List[str],
        fuzzers: List[str],
        description: str = None,
        no_seeds=False,
        no_dictionaries=False,
        oss_fuzz_corpus=False,
        allow_uncommitted_changes=False,
        concurrent_builds=None,
        measurers_cpus=None,
        runners_cpus=None,
        region_coverage=False,
        custom_seed_corpus_dir=None):
    """Start a fuzzer benchmarking experiment."""
    if not allow_uncommitted_changes:
        check_no_uncommitted_changes()

    validate_experiment_name(experiment_name)
    validate_benchmarks(benchmarks)

    config = read_and_validate_experiment_config(config_filename)
    config['fuzzers'] = fuzzers
    config['benchmarks'] = benchmarks
    config['experiment'] = experiment_name
    config['git_hash'] = get_git_hash()
    config['no_seeds'] = no_seeds
    config['no_dictionaries'] = no_dictionaries
    config['oss_fuzz_corpus'] = oss_fuzz_corpus
    config['description'] = description
    config['concurrent_builds'] = concurrent_builds
    config['measurers_cpus'] = measurers_cpus
    config['runners_cpus'] = runners_cpus
    config['runner_machine_type'] = config.get('runner_machine_type',
                                               'n1-standard-1')
    config['runner_num_cpu_cores'] = config.get('runner_num_cpu_cores', 1)
    assert (runners_cpus is None or
            runners_cpus >= config['runner_num_cpu_cores'])
    # Note this is only used if runner_machine_type is None.
    # 12GB is just the amount that KLEE needs, use this default to make KLEE
    # experiments easier to run.
    config['runner_memory'] = config.get('runner_memory', '12GB')
    config['region_coverage'] = region_coverage

    config['custom_seed_corpus_dir'] = custom_seed_corpus_dir
    if config['custom_seed_corpus_dir']:
        validate_custom_seed_corpus(config['custom_seed_corpus_dir'],
                                    benchmarks)

    return start_experiment_from_full_config(config)


def start_experiment_from_full_config(config):
    """Start a fuzzer benchmarking experiment from a full (internal) config."""

    set_up_experiment_config_file(config)

    # Make sure we can connect to database.
    local_experiment = config.get('local_experiment', False)
    if not local_experiment:
        if 'POSTGRES_PASSWORD' not in os.environ:
            raise ValidationError(
                'Must set POSTGRES_PASSWORD environment variable.')
        gcloud.set_default_project(config['cloud_project'])

    start_dispatcher(config, experiment_utils.CONFIG_DIR)


def start_dispatcher(config: Dict, config_dir: str):
    """Start the dispatcher instance and run the dispatcher code on it."""
    dispatcher = get_dispatcher(config)
    # Is dispatcher code being run manually (useful for debugging)?
    copy_resources_to_bucket(config_dir, config)
    if not os.getenv('MANUAL_EXPERIMENT'):
        dispatcher.start()


def add_oss_fuzz_corpus(benchmark, oss_fuzz_corpora_dir):
    """Add latest public corpus from OSS-Fuzz as the seed corpus for various
    fuzz targets."""
    project = benchmark_utils.get_project(benchmark)
    fuzz_target = benchmark_utils.get_fuzz_target(benchmark)

    if not fuzz_target.startswith(project):
        full_fuzz_target = '%s_%s' % (project, fuzz_target)
    else:
        full_fuzz_target = fuzz_target

    src_corpus_url = _OSS_FUZZ_CORPUS_BACKUP_URL_FORMAT.format(
        project=project, fuzz_target=full_fuzz_target)
    dest_corpus_url = os.path.join(oss_fuzz_corpora_dir, f'{benchmark}.zip')
    gsutil.cp(src_corpus_url, dest_corpus_url, parallel=True, expect_zero=False)


def copy_resources_to_bucket(config_dir: str, config: Dict):
    """Copy resources the dispatcher will need for the experiment to the
    experiment_filestore."""

    def filter_file(tar_info):
        """Filter out unnecessary directories."""
        if FILTER_SOURCE_REGEX.match(tar_info.name):
            return None
        return tar_info

    # Set environment variables to use corresponding filestore_utils.
    os.environ['EXPERIMENT_FILESTORE'] = config['experiment_filestore']
    os.environ['EXPERIMENT'] = config['experiment']
    experiment_filestore_path = experiment_utils.get_experiment_filestore_path()

    base_destination = os.path.join(experiment_filestore_path, 'input')

    # Send the local source repository to the cloud for use by dispatcher.
    # Local changes to any file will propagate.
    source_archive = 'src.tar.gz'
    with tarfile.open(source_archive, 'w:gz') as tar:
        tar.add(utils.ROOT_DIR, arcname='', recursive=True, filter=filter_file)
    filestore_utils.cp(source_archive, base_destination + '/', parallel=True)
    os.remove(source_archive)

    # Send config files.
    destination = os.path.join(base_destination, 'config')
    filestore_utils.rsync(config_dir, destination, parallel=True)

    # If |oss_fuzz_corpus| flag is set, copy latest corpora from each benchmark
    # (if available) in our filestore bucket.
    if config['oss_fuzz_corpus']:
        oss_fuzz_corpora_dir = (
            experiment_utils.get_oss_fuzz_corpora_filestore_path())
        for benchmark in config['benchmarks']:
            add_oss_fuzz_corpus(benchmark, oss_fuzz_corpora_dir)

    if config['custom_seed_corpus_dir']:
        for benchmark in config['benchmarks']:
            benchmark_custom_corpus_dir = os.path.join(
                config['custom_seed_corpus_dir'], benchmark)
            filestore_utils.cp(
                benchmark_custom_corpus_dir,
                experiment_utils.get_custom_seed_corpora_filestore_path() + '/',
                recursive=True,
                parallel=True)


class BaseDispatcher:
    """Class representing the dispatcher."""

    def __init__(self, config: Dict):
        self.config = config
        self.instance_name = experiment_utils.get_dispatcher_instance_name(
            config['experiment'])

    def start(self):
        """Start the experiment on the dispatcher."""
        raise NotImplementedError


class LocalDispatcher(BaseDispatcher):
    """Class representing the local dispatcher."""

    def __init__(self, config: Dict):
        super().__init__(config)
        self.process = None

    def start(self):
        """Start the experiment on the dispatcher."""
        container_name = 'dispatcher-container'
        experiment_filestore_path = os.path.abspath(
            self.config['experiment_filestore'])
        filesystem.create_directory(experiment_filestore_path)
        sql_database_arg = (
            'SQL_DATABASE_URL=sqlite:///{}?check_same_thread=False'.format(
                os.path.join(experiment_filestore_path, 'local.db')))

        docker_registry = self.config['docker_registry']
        set_instance_name_arg = 'INSTANCE_NAME={instance_name}'.format(
            instance_name=self.instance_name)
        set_experiment_arg = 'EXPERIMENT={experiment}'.format(
            experiment=self.config['experiment'])
        shared_experiment_filestore_arg = '{0}:{0}'.format(
            self.config['experiment_filestore'])
        # TODO: (#484) Use config in function args or set as environment
        # variables.
        set_docker_registry_arg = 'DOCKER_REGISTRY={}'.format(docker_registry)
        set_experiment_filestore_arg = (
            'EXPERIMENT_FILESTORE={experiment_filestore}'.format(
                experiment_filestore=self.config['experiment_filestore']))
        shared_report_filestore_arg = '{0}:{0}'.format(
            self.config['report_filestore'])
        set_report_filestore_arg = (
            'REPORT_FILESTORE={report_filestore}'.format(
                report_filestore=self.config['report_filestore']))
        set_snapshot_period_arg = 'SNAPSHOT_PERIOD={snapshot_period}'.format(
            snapshot_period=self.config['snapshot_period'])
        docker_image_url = '{docker_registry}/dispatcher-image'.format(
            docker_registry=docker_registry)
        command = [
            'docker',
            'run',
            '-ti',
            '--rm',
            '-v',
            '/var/run/docker.sock:/var/run/docker.sock',
            '-v',
            shared_experiment_filestore_arg,
            '-v',
            shared_report_filestore_arg,
            '-e',
            set_instance_name_arg,
            '-e',
            set_experiment_arg,
            '-e',
            sql_database_arg,
            '-e',
            set_experiment_filestore_arg,
            '-e',
            set_snapshot_period_arg,
            '-e',
            set_report_filestore_arg,
            '-e',
            set_docker_registry_arg,
            '-e',
            'LOCAL_EXPERIMENT=True',
            '--cap-add=SYS_PTRACE',
            '--cap-add=SYS_NICE',
            '--name=%s' % container_name,
            docker_image_url,
            '/bin/bash',
            '-c',
            'rsync -r '
            '"${EXPERIMENT_FILESTORE}/${EXPERIMENT}/input/" ${WORK} && '
            'mkdir ${WORK}/src && '
            'tar -xvzf ${WORK}/src.tar.gz -C ${WORK}/src && '
            'PYTHONPATH=${WORK}/src python3 '
            '${WORK}/src/experiment/dispatcher.py || '
            '/bin/bash'  # Open shell if experiment fails.
        ]
        logs.info('Starting dispatcher with container name: %s', container_name)
        return new_process.execute(command, write_to_stdout=True)


class GoogleCloudDispatcher(BaseDispatcher):
    """Class representing the dispatcher instance on Google Cloud."""

    def start(self):
        """Start the experiment on the dispatcher."""
        with tempfile.NamedTemporaryFile(dir=os.getcwd(),
                                         mode='w') as startup_script:
            self.write_startup_script(startup_script)
            if not gcloud.create_instance(self.instance_name,
                                          gcloud.InstanceType.DISPATCHER,
                                          self.config,
                                          startup_script=startup_script.name):
                raise RuntimeError('Failed to create dispatcher.')
            logs.info('Started dispatcher with instance name: %s',
                      self.instance_name)

    def _render_startup_script(self):
        """Renders the startup script template and returns the result as a
        string."""
        jinja_env = jinja2.Environment(
            undefined=jinja2.StrictUndefined,
            loader=jinja2.FileSystemLoader(RESOURCES_DIR),
        )
        template = jinja_env.get_template(
            'dispatcher-startup-script-template.sh')
        cloud_sql_instance_connection_name = (
            self.config['cloud_sql_instance_connection_name'])

        kwargs = {
            'instance_name': self.instance_name,
            'postgres_password': os.environ['POSTGRES_PASSWORD'],
            'experiment': self.config['experiment'],
            'cloud_project': self.config['cloud_project'],
            'experiment_filestore': self.config['experiment_filestore'],
            'cloud_sql_instance_connection_name':
                (cloud_sql_instance_connection_name),
            'docker_registry': self.config['docker_registry'],
        }
        return template.render(**kwargs)

    def write_startup_script(self, startup_script_file):
        """Get the startup script to start the experiment on the dispatcher."""
        startup_script = self._render_startup_script()
        startup_script_file.write(startup_script)
        startup_script_file.flush()


def get_dispatcher(config: Dict) -> BaseDispatcher:
    """Return a dispatcher object created from the right class (i.e. dispatcher
    factory)."""
    if config.get('local_experiment'):
        return LocalDispatcher(config)
    return GoogleCloudDispatcher(config)


def main():
    """Run an experiment in the cloud."""
    logs.initialize()

    parser = argparse.ArgumentParser(
        description='Begin an experiment that evaluates fuzzers on one or '
        'more benchmarks.')

    all_benchmarks = benchmark_utils.get_all_benchmarks()
    coverage_benchmarks = benchmark_utils.get_coverage_benchmarks()
    parser.add_argument('-b',
                        '--benchmarks',
                        help=('Benchmark names. '
                              'All code coverage benchmarks of them by '
                              'default.'),
                        nargs='+',
                        required=False,
                        default=coverage_benchmarks,
                        choices=all_benchmarks)
    parser.add_argument('-c',
                        '--experiment-config',
                        help='Path to the experiment configuration yaml file.',
                        required=True)
    parser.add_argument('-e',
                        '--experiment-name',
                        help='Experiment name.',
                        required=True)
    parser.add_argument('-d',
                        '--description',
                        help='Description of the experiment.',
                        required=False)
    parser.add_argument('-cb',
                        '--concurrent-builds',
                        help='Max concurrent builds allowed.',
                        required=False)
    parser.add_argument('-mc',
                        '--measurers-cpus',
                        help='Cpus available to the measurers.',
                        required=False)
    parser.add_argument('-rc',
                        '--runners-cpus',
                        help='Cpus available to the runners.',
                        required=False)
    parser.add_argument('-cs',
                        '--custom-seed-corpus-dir',
                        help='Path to the custom seed corpus',
                        required=False)

    all_fuzzers = fuzzer_utils.get_fuzzer_names()
    parser.add_argument('-f',
                        '--fuzzers',
                        help='Fuzzers to use.',
                        nargs='+',
                        required=False,
                        default=None,
                        choices=all_fuzzers)
    parser.add_argument('-ns',
                        '--no-seeds',
                        help='Should trials be conducted without seed corpora.',
                        required=False,
                        default=False,
                        action='store_true')
    parser.add_argument('-nd',
                        '--no-dictionaries',
                        help='Should trials be conducted without dictionaries.',
                        required=False,
                        default=False,
                        action='store_true')
    parser.add_argument('-a',
                        '--allow-uncommitted-changes',
                        help='Skip check that no uncommited changes made.',
                        required=False,
                        default=False,
                        action='store_true')
    parser.add_argument('-cr',
                        '--region-coverage',
                        help='Use region as coverage metric.',
                        required=False,
                        default=False,
                        action='store_true')
    parser.add_argument(
        '-o',
        '--oss-fuzz-corpus',
        help='Should trials be conducted with OSS-Fuzz corpus (if available).',
        required=False,
        default=False,
        action='store_true')
    args = parser.parse_args()
    fuzzers = args.fuzzers or all_fuzzers

    concurrent_builds = args.concurrent_builds
    if concurrent_builds is not None:
        if not concurrent_builds.isdigit():
            parser.error(
                'The concurrent build argument must be a positive number')
        concurrent_builds = int(concurrent_builds)
    runners_cpus = args.runners_cpus
    if runners_cpus is not None:
        if not runners_cpus.isdigit():
            parser.error('The runners cpus argument must be a positive number')
        runners_cpus = int(runners_cpus)
    measurers_cpus = args.measurers_cpus
    if measurers_cpus is not None:
        if not measurers_cpus.isdigit():
            parser.error(
                'The measurers cpus argument must be a positive number')
        if runners_cpus is None:
            parser.error(
                'With the measurers cpus argument you need to specify the'
                ' runners cpus argument too')
        measurers_cpus = int(measurers_cpus)
    if (runners_cpus if runners_cpus else 0) + (measurers_cpus if measurers_cpus
                                                else 0) > os.cpu_count():
        parser.error('The sum of runners and measurers cpus is greater than the'
                     ' available cpu cores (%d)' % os.cpu_count())

    if args.custom_seed_corpus_dir:
        if args.no_seeds:
            parser.error('Cannot enable options "custom_seed_corpus_dir" and '
                         '"no_seeds" at the same time')
        if args.oss_fuzz_corpus:
            parser.error('Cannot enable options "custom_seed_corpus_dir" and '
                         '"oss_fuzz_corpus" at the same time')

    start_experiment(args.experiment_name,
                     args.experiment_config,
                     args.benchmarks,
                     fuzzers,
                     description=args.description,
                     no_seeds=args.no_seeds,
                     no_dictionaries=args.no_dictionaries,
                     oss_fuzz_corpus=args.oss_fuzz_corpus,
                     allow_uncommitted_changes=args.allow_uncommitted_changes,
                     concurrent_builds=concurrent_builds,
                     measurers_cpus=measurers_cpus,
                     runners_cpus=runners_cpus,
                     region_coverage=args.region_coverage,
                     custom_seed_corpus_dir=args.custom_seed_corpus_dir)
    return 0


if __name__ == '__main__':
    sys.exit(main())
