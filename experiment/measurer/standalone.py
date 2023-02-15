# Copyright 2023 Google LLC
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
"""Module for starting a measure manager outside of an experiment. Useful when
measuring results in OSS-Fuzz."""
import os
import sys

from database import models
from database import utils as db_utils
from experiment.measurer import measure_manager
from experiment import scheduler


def _initialize_db():
    """Initializes |experiment| in the database by creating the experiment
    entity. Warning you probably should not be using this method if connected to
    anything other than a throwaway sqlite db. Most of this code is copied from
    dispatcher.py which usually has the job of setting up an experiment."""
    # TODO(metzman): Most of the strings in this function should probably be
    # configurable.

    db_utils.initialize()
    # One time set up for any db used by FuzzBench.
    models.Base.metadata.create_all(db_utils.engine)

    # Now set up the experiment.
    with db_utils.session_scope() as session:
        experiment_name = 'oss-fuzz-on-demand'
        experiment_exists = session.query(models.Experiment).filter(
            models.Experiment.name == experiment_name).first()
    if experiment_exists:
        raise Exception('Experiment already exists in database.')

    db_utils.add_all([
        db_utils.get_or_create(models.Experiment,
                               name=experiment_name,
                               git_hash='none',
                               private=True,
                               experiment_filestore='/out/filestore',
                               description='none'),
    ])

    # Set up the trial.
    trial = models.Trial(fuzzer=os.environ['FUZZER'],
                         experiment='oss-fuzz-on-demand',
                         benchmark=os.environ['BENCHMARK'],
                         preemptible=False,
                         time_started=scheduler.datetime_now(),
                         time_ended=scheduler.datetime_now())
    db_utils.add_all([trial])


def main():
    """Runs the measurer."""
    _initialize_db()
    return measure_manager.main()


if __name__ == '__main__':
    sys.exit(main())
