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
"""Utility functions for using the database."""

import os
import threading
from contextlib import contextmanager

import sqlalchemy

# pylint: disable=invalid-name,no-member
engine = None
session = None
lock = None


def initialize():
    """Initialize the database for use. Sets the database engine and session.
    Since this function is called when this module is imported one should rarely
    need to call it (tests are an exception)."""
    database_url = os.getenv('SQL_DATABASE_URL')
    if not database_url:
        postgres_password = os.getenv('POSTGRES_PASSWORD')
        assert postgres_password, 'POSTGRES_PASSWORD needs to be set.'
        database_url = (
            'postgresql+psycopg2://postgres:{password}@127.0.0.1:5432'.format(
                password=postgres_password))

    global engine
    engine = sqlalchemy.create_engine(database_url)
    global session
    Session = sqlalchemy.orm.sessionmaker(bind=engine)
    session = Session()
    global lock
    lock = threading.Lock()
    return engine, session


def cleanup():
    """Close the session and dispose of the engine. This is useful for avoiding
    having too many connections and other weirdness when using
    multiprocessing."""
    global session
    if session:
        session.commit()
        session.close()
        session = None
    global engine
    if engine:
        engine.dispose()
    engine = None
    global lock
    lock = None


@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    global session
    global engine
    global lock
    if session is None or engine is None or lock is None:
        initialize()
    lock.acquire()
    try:
        yield session
    except Exception as e:
        session.rollback()
        raise e
    finally:
        lock.release()


def add_all(entities):
    """Save all |entities| to the database connected to by session."""
    with session_scope() as scoped_session:
        scoped_session.add_all(entities)
        scoped_session.commit()


def bulk_save(entities):
    """Save all |entities| to the database connected to by session."""
    with session_scope() as scoped_session:
        scoped_session.bulk_save_objects(entities)
        scoped_session.commit()


def get_or_create(model, **kwargs):
    """If a |model| with the conditions specified by |kwargs| exists, then it is
    retrieved from the database. If not, it is created and saved to the
    database."""
    with session_scope() as scoped_session:
        instance = scoped_session.query(model).filter_by(**kwargs).first()
        if instance:
            return instance
        instance = model(**kwargs)
        scoped_session.add(instance)
        return instance
