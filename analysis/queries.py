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
        Experiment.git_hash,\
        Trial.experiment, Trial.fuzzer, Trial.benchmark,\
        Trial.time_started, Trial.time_ended,\
        Snapshot.trial_id, Snapshot.time, Snapshot.edges_covered)\
        .select_from(Experiment)\
        .join(Trial)\
        .join(Snapshot)\
        .filter(Experiment.name.in_(experiment_names))

    return pd.read_sql_query(snapshots_query.statement, db_utils.engine)
