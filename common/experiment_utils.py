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

DEFAULT_SNAPSHOT_SECONDS = 15 * 60  # Seconds.


def get_snapshot_seconds():
    """Returns the amount of time in seconds between snapshots of a
    fuzzer's corpus during an experiment."""
    return environment.get('SNAPSHOT_PERIOD', DEFAULT_SNAPSHOT_SECONDS)


def get_work_dir():
    """Returns work directory."""
    return os.environ['WORK']


def get_experiment_name():
    """Returns experiment name."""
    return os.environ['EXPERIMENT']


def get_cloud_project():
    """Returns the cloud project."""
    return os.environ['CLOUD_PROJECT']


def get_local_experiment_path():
    """Returns local experiment path."""
    local_experiment_bucket = os.environ['LOCAL_EXPERIMENT_BUCKET']
    experiment_name = get_experiment_name()
    return posixpath.join(local_experiment_bucket, experiment_name)


def get_cloud_experiment_path():
    """Returns cloud experiment path."""
    cloud_experiment_bucket = os.environ['CLOUD_EXPERIMENT_BUCKET']
    experiment_name = get_experiment_name()
    return posixpath.join(cloud_experiment_bucket, experiment_name)


def get_dispatcher_instance_name(experiment: str) -> str:
    """Returns a dispatcher instance name for an experiment."""
    return 'd-%s' % experiment


def get_trial_instance_name(experiment: str, trial_id: int) -> str:
    """Returns a unique instance name for each trial of an experiment."""
    return 'r-%s-%d' % (experiment, trial_id)


def get_corpus_archive_name(cycle: int) -> str:
    """Returns a corpus archive name given a cycle."""
    return 'corpus-archive-%04d.tar.gz' % cycle


def get_crashes_archive_name(cycle: int) -> str:
    """Return as crashes archive name given a cycle."""
    return 'crashes-%04d.tar.gz' % cycle


def get_base_docker_tag(cloud_project=None):
    """Returns the base docker tag (i.e. Docker repo URL) given cloud_project.
    If cloud is not provided, then the value of the environment variable
    CLOUD_PROJECT is used."""
    # Google Cloud Docker repos use the form "gcr.io/$CLOUD_PROJECT"
    if cloud_project is None:
        cloud_project = get_cloud_project()
    return posixpath.join('gcr.io', cloud_project)


def is_local_experiment():
    """Returns True if running a local experiment."""
    return bool(environment.get('LOCAL_EXPERIMENT'))


def is_gsutil_disabled():
    """Returns True if running a gsutil-supported local experiment."""
    return bool(environment.get('GSUTIL_DISABLED'))
