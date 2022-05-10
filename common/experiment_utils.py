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
"""Config management."""

import os
import posixpath

from common import environment
from common import experiment_path as exp_path

DEFAULT_SNAPSHOT_SECONDS = 15 * 60  # Seconds.
CONFIG_DIR = 'config'


def get_internal_experiment_config_relative_path():
    """Returns the path of the internal config file relative to the data
    directory of an experiment."""
    return os.path.join(CONFIG_DIR, 'experiment.yaml')


def get_snapshot_seconds():
    """Returns the amount of time in seconds between snapshots of a
    fuzzer's corpus during an experiment."""
    return environment.get('SNAPSHOT_PERIOD', DEFAULT_SNAPSHOT_SECONDS)


def get_cycle_time(cycle):
    """Return time elapsed for a cycle."""
    return cycle * get_snapshot_seconds()


def get_work_dir():
    """Returns work directory."""
    return os.environ['WORK']


def get_experiment_name():
    """Returns experiment name."""
    return os.environ['EXPERIMENT']


def get_experiment_folders_dir():
    """Returns experiment folders directory."""
    return exp_path.path('experiment-folders')


def get_cloud_project():
    """Returns the cloud project."""
    return os.environ['CLOUD_PROJECT']


def get_experiment_filestore_path():
    """Returns experiment filestore path."""
    experiment_filestore = os.environ['EXPERIMENT_FILESTORE']
    experiment_name = get_experiment_name()
    return posixpath.join(experiment_filestore, experiment_name)


def get_oss_fuzz_corpora_filestore_path():
    """Returns path containing OSS-Fuzz corpora for various fuzz targets."""
    return posixpath.join(get_experiment_filestore_path(), 'oss_fuzz_corpora')


def get_custom_seed_corpora_filestore_path():
    """Returns path containing the user-provided seed corpora."""
    return posixpath.join(get_experiment_filestore_path(),
                          'custom_seed_corpora')


def get_dispatcher_instance_name(experiment: str) -> str:
    """Returns a dispatcher instance name for an experiment."""
    return 'd-%s' % experiment


def get_trial_instance_name(experiment: str, trial_id: int) -> str:
    """Returns a unique instance name for each trial of an experiment."""
    return 'r-%s-%d' % (experiment, trial_id)


def get_cycle_filename(basename: str, cycle: int) -> str:
    """Returns a filename for a file that is relevant to a particular snapshot
    cycle."""
    filename = basename + '-' + ('%04d' % cycle)
    return filename


def get_corpus_archive_name(cycle: int) -> str:
    """Returns a corpus archive name given a cycle."""
    return get_cycle_filename('corpus-archive', cycle) + '.tar.gz'


def get_stats_filename(cycle: int) -> str:
    """Returns a corpus archive name given a cycle."""
    return get_cycle_filename('stats', cycle) + '.json'


def get_crash_metadata_filename(cycle: int) -> str:
    """Returns a crash metadata name given a cycle."""
    return get_cycle_filename('crashes', cycle) + '.json'


def get_crashes_archive_name(cycle: int) -> str:
    """Returns a crashes archive name given a cycle."""
    return get_cycle_filename('crashes', cycle) + '.tar.gz'


def is_local_experiment():
    """Returns True if running a local experiment."""
    return bool(environment.get('LOCAL_EXPERIMENT'))


def get_trial_dir(fuzzer, benchmark, trial_id):
    """Returns the unique directory for |fuzzer|, |benchmark|, and
    |trial_id|."""
    benchmark_fuzzer_directory = get_benchmark_fuzzer_dir(benchmark, fuzzer)
    trial_subdir = 'trial-%d' % trial_id
    return posixpath.join(benchmark_fuzzer_directory, trial_subdir)


def get_benchmark_fuzzer_dir(benchmark, fuzzer):
    """Returns the directory for |benchmark| and |fuzzer|."""
    return '%s-%s' % (benchmark, fuzzer)


def get_trial_bucket_dir(fuzzer, benchmark, trial_id):
    """Returns the unique directory in experiment-folders int the bucket for
    |fuzzer|, |benchmark|, and |trial_id|."""
    bucket = os.environ['EXPERIMENT_FILESTORE']
    return posixpath.join(bucket, get_experiment_name(), 'experiment-folders',
                          get_trial_dir(fuzzer, benchmark, trial_id))
