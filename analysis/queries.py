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

from sqlalchemy import and_

from database.models import Experiment, Trial, Snapshot, Crash
from database import utils as db_utils


def get_experiment_data(experiment_names):
    """Get measurements (such as coverage) on experiments from the database."""
    with db_utils.session_scope() as session:
        snapshots_query = session.query(
            Experiment.git_hash, Experiment.experiment_filestore,
            Trial.experiment, Trial.fuzzer, Trial.benchmark,
            Trial.time_started, Trial.time_ended,
            Snapshot.trial_id, Snapshot.time, Snapshot.edges_covered,
            Snapshot.fuzzer_stats, Crash.crash_key)\
            .select_from(Experiment)\
            .join(Trial)\
            .join(Snapshot)\
            .join(Crash,
                  and_(Snapshot.time == Crash.time,
                       Snapshot.trial_id == Crash.trial_id), isouter=True)\
            .filter(Experiment.name.in_(experiment_names))\
            .filter(Trial.preempted.is_(False))

    return pd.read_sql_query(snapshots_query.statement, db_utils.engine)


def get_experiment_description(experiment_name):
    """Get the description of the experiment named by |experiment_name|."""
    # Do another query for the description so we don't explode the size of the
    # results from get_experiment_data.
    with db_utils.session_scope() as session:
        return session.query(Experiment.description)\
                .select_from(Experiment)\
                .filter(Experiment.name == experiment_name).one()


def add_nonprivate_experiments_for_merge_with_clobber(experiment_names):
    """Returns a new list containing experiment names preeceeded by a list of
    nonprivate experiments in the order in which they were run, such that
    these nonprivate experiments executed before. This is useful
    if you want to combine reports from |experiment_names| and all nonprivate
    experiments."""
    earliest_creation_time = None

    with db_utils.session_scope() as session:
        for result in session.query(Experiment.time_created).filter(
                Experiment.name.in_(experiment_names)):
            experiment_creation_time = result[0]
            if not earliest_creation_time:
                earliest_creation_time = experiment_creation_time
            else:
                earliest_creation_time = min(earliest_creation_time,
                                             experiment_creation_time)

        nonprivate_experiments = session.query(Experiment.name).filter(
            ~Experiment.private, ~Experiment.name.in_(experiment_names),
            ~Experiment.time_ended.is_(None),
            Experiment.time_created <= earliest_creation_time).order_by(
                Experiment.time_created)
        nonprivate_experiment_names = [
            result[0] for result in nonprivate_experiments
        ]

    return nonprivate_experiment_names + experiment_names
