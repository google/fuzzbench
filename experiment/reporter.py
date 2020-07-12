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
import posixpath

from common import experiment_utils
from common import experiment_path as exp_path
from common import filesystem
from common import filestore_utils
from common import logs
from analysis import generate_report
from analysis import data_utils

logger = logs.Logger('reporter')  # pylint: disable=invalid-name


def get_reports_dir():
    """Return reports directory."""
    return exp_path.path('reports')


def output_report(experiment_config: dict, in_progress=False):
    """Generate the HTML report and write it to |web_bucket|."""
    experiment_name = experiment_utils.get_experiment_name()
    web_filestore_path = posixpath.join(experiment_config['report_filestore'],
                                        experiment_name)

    reports_dir = get_reports_dir()

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
            in_progress=in_progress,
            merge_with_clobber_nonprivate=merge_with_nonprivate)
        filestore_utils.rsync(str(reports_dir),
                              web_filestore_path,
                              gsutil_options=[
                                  '-h',
                                  'Cache-Control:public,max-age=0,no-transform'
                              ])
        logger.debug('Done generating report.')
    except data_utils.EmptyDataError:
        logs.warning('No snapshot data.')
    except Exception:  # pylint: disable=broad-except
        logger.error('Error generating HTML report.')
