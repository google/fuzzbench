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
"""Database queries for acquiring experiment data."""

import pandas as pd

from database.models import Experiment, Trial, Snapshot
from database import utils as db_utils


def get_experiment_data(experiment_names):
    """Get measurements (such as coverage) on experiments from the database."""

    snapshots_query = db_utils.query(
        Experiment.git_hash, Experiment.experiment_filestore,\
        Trial.experiment, Trial.fuzzer, Trial.benchmark,\
        Trial.time_started, Trial.time_ended,\
        Snapshot.trial_id, Snapshot.time, Snapshot.edges_covered)\
        .select_from(Experiment)\
        .join(Trial)\
        .join(Snapshot)\
        .filter(Experiment.name.in_(experiment_names))\
        .filter(Trial.preempted.is_(False))

    return pd.read_sql_query(snapshots_query.statement, db_utils.engine)


def add_nonprivate_experiments_for_merge_with_clobber(experiment_names):
    """Returns a new list containing experiment names preeceeded by a list of
    nonprivate experiments in the order in which they were run, such that
    these nonprivate experiments executed before. This is useful
    if you want to combine reports from |experiment_names| and all nonprivate
    experiments."""
    earliest_creation_time = None
    for result in db_utils.query(Experiment.time_created).filter(
            Experiment.name.in_(experiment_names)):
        experiment_creation_time = result[0]
        if not earliest_creation_time:
            earliest_creation_time = experiment_creation_time
        else:
            earliest_creation_time = min(earliest_creation_time,
                                         experiment_creation_time)

    nonprivate_experiments = db_utils.query(Experiment.name).filter(
        ~Experiment.private, ~Experiment.name.in_(experiment_names),
        ~Experiment.time_ended.is_(None),
        Experiment.time_created <= earliest_creation_time).order_by(
            Experiment.time_created)
    nonprivate_experiment_names = [
        result[0] for result in nonprivate_experiments
    ]

    return nonprivate_experiment_names + experiment_names
