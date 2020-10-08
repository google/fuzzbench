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
"""A module containing the interface used by an experiment for generating
reports."""
import os
import posixpath

from common import experiment_utils
from common import experiment_path as exp_path
from common import filesystem
from common import filestore_utils
from common import logs
from common import utils
from common import yaml_utils
from analysis import generate_report
from analysis import data_utils

CORE_FUZZERS_YAML = os.path.join(utils.ROOT_DIR, 'service', 'core-fuzzers.yaml')

logger = logs.Logger('reporter')  # pylint: disable=invalid-name


def get_reports_dir():
    """Return reports directory."""
    return exp_path.path('reports')


def get_core_fuzzers():
    """Return list of core fuzzers to be used for merging experiment data."""
    return yaml_utils.read(CORE_FUZZERS_YAML)['fuzzers']


def output_report(experiment_config: dict,
                  in_progress=False,
                  coverage_report=False):
    """Generate the HTML report and write it to |web_bucket|."""
    experiment_name = experiment_utils.get_experiment_name()
    reports_dir = get_reports_dir()

    core_fuzzers = set(get_core_fuzzers())
    experiment_fuzzers = set(experiment_config['fuzzers'])
    fuzzers = experiment_fuzzers.union(core_fuzzers)

    # Calculate path to store report files in filestore.
    web_filestore_path = experiment_config['report_filestore']
    if not fuzzers.issubset(core_fuzzers):
        # This means that we are running an experimental report with fuzzers
        # not in the core list. So, store these in |experimental| sub-directory.
        web_filestore_path = os.path.join(web_filestore_path, 'experimental')
    web_filestore_path = posixpath.join(web_filestore_path, experiment_name)

    # Don't merge with nonprivate experiments until the very end as doing it
    # while the experiment is in progress will produce unusable realtime
    # results.
    merge_with_nonprivate = (not in_progress and experiment_config.get(
        'merge_with_nonprivate', False))

    try:
        logger.debug('Generating report.')
        filesystem.recreate_directory(reports_dir)
        generate_report.generate_report(
            [experiment_name],
            str(reports_dir),
            report_name=experiment_name,
            fuzzers=fuzzers,
            in_progress=in_progress,
            merge_with_clobber_nonprivate=merge_with_nonprivate,
            coverage_report=coverage_report)
        filestore_utils.rsync(
            str(reports_dir),
            web_filestore_path,
            delete=False,  # Don't remove existing coverage jsons.
            gsutil_options=[
                '-h', 'Cache-Control:public,max-age=0,no-transform'
            ])
        logger.debug('Done generating report.')
    except data_utils.EmptyDataError:
        logs.warning('No snapshot data.')
    except Exception:  # pylint: disable=broad-except
        logger.error('Error generating HTML report.')
