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

import sqlalchemy
from sqlalchemy import orm

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
    Session = orm.sessionmaker(bind=engine)
    session = Session()
    global lock
    lock = threading.Lock()
    return engine, session


# TODO(metzman): Use sessions as described here rather than creating them
# globally:
# https://docs.sqlalchemy.org/en/13/orm/session_basics.html#when-do-i-construct-a-session-when-do-i-commit-it-and-when-do-i-close-it
def use_session(function):
    """Initialize the database if it isn't already."""

    # TODO(metzman): The use of decorators with optional closes is pretty ugly.
    # Replace it with a class/object.
    def locked_function(*args, **kwargs):
        global session
        global engine
        global lock
        if session is None or engine is None or lock is None:
            initialize()
        lock.acquire()
        try:
            return function(*args, **kwargs)
        finally:
            lock.release()

    return locked_function


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


@use_session
def add_all(entities):
    """Save all |entities| to the database connected to by session."""
    try:
        session.add_all(entities)
        session.commit()
        return
    except Exception as e:
        session.rollback()
        raise e


@use_session
def bulk_save(entities):
    """Save all |entities| to the database connected to by session."""
    try:
        session.bulk_save_objects(entities)
        session.commit()
        return
    except Exception as e:
        session.rollback()
        raise e


@use_session
def query(*args, **kwargs):
    """Returns a query on the database connected to by |session|."""
    try:
        return session.query(*args, **kwargs)
    except Exception as e:
        session.rollback()
        raise e


@use_session
def get_or_create(model, **kwargs):
    """If a |model| with the conditions specified by |kwargs| exists, then it is
    retrieved from the database. If not, it is created and saved to the
    database."""
    instance = session.query(model).filter_by(**kwargs).first()
    if instance:
        return instance
    instance = model(**kwargs)
    session.add(instance)
    return instance
