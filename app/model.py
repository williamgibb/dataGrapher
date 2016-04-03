import contextlib
import json
import logging
import os
import sys
from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import create_engine
from sqlalchemy import exc
from . import utils

log = logging.getLogger(__name__)

Base = declarative_base()

class ModelError(Exception):
    pass


class DBExists(ModelError):
    pass


class State(Base):
    __tablename__ = 'state'
    _value = Column(String, default="null")
    component = Column(String, primary_key=True)
    key = Column(String, primary_key=True)
    def __init__(self, component, key, _value):
        self.component = component
        self.key = key
        self.value = _value

    @property
    def value(self):
        return json.loads(self._value)

    @value.setter
    def value(self, value):
        self._value = json.dumps(value)


class LogData(Base):
    __tablename__ = 'logdata'
    data = Column(String)
    timestamp = Column(DateTime, default=utils.now())
    session_id = Column(Integer, ForeignKey('logsession.id'))
    session = relationship(LogSesssion)


class LogSesssion(Base):
    __tablename__ = 'logsession'
    id = Column(Integer, primary_key=True, autoincrement=True)
    collection_start = Column(DateTime, default=utils.now())
    collection_stop = Column(DateTime, default=None)
    collection_name = Column(String, default='Collection')
    collection_notes = Column(String, default=None)
    collector = Column(String, default=None)


def get_engine(fp):
    engine = create_engine('sqlite:///{}'.format(fp))
    return engine


def make_db(fp, remove=False):
    if os.path.exists(fp):
        if remove:
            log.info('Removing [{}]'.format(fp))
            os.remove(fp)
        else:
            log.warning('Database already exists. [{}]'.format(fp))
            return
    engine = get_engine(fp)
    Base.metadata.create_all(engine)
    return True


def get_session(fp):
    engine = get_engine(fp)
    session = sessionmaker()
    session.configure(bind=engine)
    s = session()
    return s


@contextlib.contextmanager
def session_scope(fp, commit=False):
    """Provide a transactional scope around a series of operations."""
    session = get_session(fp)
    try:
        yield session
        if commit:
            session.commit()
    except exc.SQLAlchemyError:
        log.exception('Failurre during session - rolling back any changes.')
        session.rollback()
        raise
    finally:
        session.close()
