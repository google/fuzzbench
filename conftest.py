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
"""A pytest conftest.py file that defines fixtures and does other things many
tests might need (such as using an in-memory SQLite database)."""

import os
import sqlite3
from unittest import mock

import pytest
import sqlalchemy

from common import new_process

# Never wait for a timeout so that tests don't take any longer than they need
# to.
new_process.WAIT_SECONDS = 0

# Set this to an in-memory instance of SQLite so that db_utils can be imported
# without running a real Postgres database.
# pylint: disable=wrong-import-position
os.environ['SQL_DATABASE_URL'] = 'sqlite://'

from database import utils as db_utils
from database import models


# Give this a short name since it is a fixture.
@pytest.fixture
def db():  # pylint: disable=invalid-name
    """Connect to the SQLite database and create all the expected tables."""
    db_utils.initialize()
    models.Base.metadata.create_all(db_utils.engine)
    with mock.patch('database.utils.cleanup'):
        yield
    db_utils.cleanup()


@sqlalchemy.event.listens_for(sqlalchemy.engine.Engine, 'connect')
def set_sqlite_pragma(connection, _):
    """Force SQLite to enforce non-null foreign key relationships.
    Based on
    https://docs.sqlalchemy.org/en/13/dialects/sqlite.html#foreign-key-support
    """
    if not isinstance(connection, sqlite3.Connection):
        return

    cursor = connection.cursor()
    cursor.execute('PRAGMA foreign_keys=ON')
    cursor.close()


@pytest.fixture
def environ():
    """Patch environment."""
    # TODO(metzman): Make sure this is used by all tests that modify the
    # environment.
    patcher = mock.patch.dict(os.environ, {})
    patcher.start()
    yield
    patcher.stop()


@pytest.fixture
def experiment(environ):  # pylint: disable=redefined-outer-name,unused-argument
    """Mock an experiment."""
    os.environ['WORK'] = '/work'
    os.environ['EXPERIMENT'] = 'test-experiment'
    os.environ['EXPERIMENT_FILESTORE'] = 'gs://experiment-data'
    os.environ['REPORT_FILESTORE'] = 'gs://web-bucket'
    os.environ['CLOUD_PROJECT'] = 'fuzzbench'
    os.environ['DOCKER_REGISTRY'] = 'gcr.io/fuzzbench'


@pytest.fixture
def use_local_filestore(experiment):  # pylint: disable=redefined-outer-name,unused-argument
    """Mock a local filestore usage experiment."""
    os.environ['EXPERIMENT_FILESTORE'] = '/experiment-data'
    os.environ['REPORT_FILESTORE'] = '/experiment-report'
    os.environ['LOCAL_EXPERIMENT'] = 'true'
    os.environ['DOCKER_REGISTRY'] = 'gcr.io/fuzzbench'


@pytest.fixture
def use_gsutil(experiment):  # pylint: disable=redefined-outer-name,unused-argument
    """Mock a Google Cloud Storage bucket usage experiment."""
