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
"""SQLAlchemy Database Models."""
import sqlalchemy
from sqlalchemy.ext import declarative
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import ForeignKeyConstraint
from sqlalchemy import Integer
from sqlalchemy import JSON
from sqlalchemy import String
from sqlalchemy import UnicodeText

Base = declarative.declarative_base()  # pylint: disable=invalid-name


class Experiment(Base):
    """Represents an experiment run."""
    __tablename__ = 'experiment'

    name = Column(String, nullable=False, primary_key=True)
    time_created = Column(DateTime(), server_default=sqlalchemy.func.now())
    time_ended = Column(DateTime(), nullable=True)
    git_hash = Column(String, nullable=True)
    private = Column(Boolean, nullable=False, default=False)
    experiment_filestore = Column(String, nullable=True)
    description = Column(UnicodeText, nullable=True)


class Trial(Base):
    """Represents trials conducted in experiments."""
    __tablename__ = 'trial'

    id = Column(Integer, primary_key=True)
    fuzzer = Column(String, nullable=False)
    experiment = Column(String, ForeignKey('experiment.name'), nullable=False)
    benchmark = Column(String, nullable=False)
    time_started = Column(DateTime(), nullable=True)
    time_ended = Column(DateTime(), nullable=True)

    # Columns used for preemptible experiments.
    preemptible = Column(Boolean, default=False, nullable=False)
    preempted = Column(Boolean, default=False, nullable=False)

    # Every trial has snapshots which is basically the saved state of that trial
    # at a given time. The snapshots field here and the trial field on Snapshot,
    # declare this relationship exists to SQLAlchemy so that it is easy to get
    # columns from snapshots given a trial and vice versa.
    snapshots = sqlalchemy.orm.relationship('Snapshot', back_populates='trial')


class Snapshot(Base):
    """The value of metrics and any other state that is important for analysis
    at a given time in a trial."""
    __tablename__ = 'snapshot'

    time = Column(Integer, nullable=False, primary_key=True)
    trial_id = Column(Integer, ForeignKey('trial.id'), primary_key=True)
    trial = sqlalchemy.orm.relationship('Trial', back_populates='snapshots')
    edges_covered = Column(Integer, nullable=False)
    fuzzer_stats = Column(JSON, nullable=True)
    crashes = sqlalchemy.orm.relationship(
        'Crash',
        backref='snapshot',
        primaryjoin=
        'and_(Snapshot.time==Crash.time, Snapshot.trial_id==Crash.trial_id)')


class Crash(Base):
    """Represents crashes found in experiments."""
    __tablename__ = 'crash'

    time = Column(Integer, nullable=False, primary_key=True)
    trial_id = Column(Integer, nullable=False, primary_key=True)
    crash_key = Column(String, nullable=False, primary_key=True)
    crash_type = Column(String, nullable=False)
    crash_address = Column(String, nullable=False)
    crash_state = Column(String, nullable=False)
    crash_stacktrace = Column(String, nullable=False)
    crash_testcase = Column(String, nullable=False)

    __table_args__ = (ForeignKeyConstraint(
        [time, trial_id], ['snapshot.time', 'snapshot.trial_id']),)
