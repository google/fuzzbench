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
"""Tools for finding changes between experiments. Unlike the rest of this
src_analysis, this can depend on database code."""
from common import logs
from database import utils as db_utils
from database import models
from src_analysis import change_utils
from src_analysis import diff_utils


def get_fuzzers_changed_since_last():
    """Returns a list of fuzzers that have changed since the last experiment
    stored in the database that has a commit that is in the current branch."""
    # TODO(metzman): Figure out a way of skipping experiments that were stopped
    # early.

    # Loop over experiments since some may have hashes that are not in the
    # current branch.
    with db_utils.session_scope() as session:
        experiments = list(
            session.query(models.Experiment).order_by(
                models.Experiment.time_created.desc()))
    if not experiments:
        raise Exception('No experiments found. Cannot find changed fuzzers.')

    changed_files = None
    for experiment in experiments:
        try:
            changed_files = diff_utils.get_changed_files(experiment.git_hash)
            break
        except diff_utils.DiffError:
            logs.warning('Skipping %s. Commit is not in branch.',
                         experiment.git_hash)

    if changed_files is None:
        raise Exception('No in-branch experiments. '
                        'Cannot find changed fuzzers.')
    return change_utils.get_changed_fuzzers(changed_files)
