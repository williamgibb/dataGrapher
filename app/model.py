import contextlib
import json
import logging
import os
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


class LogSession(Base):
    __tablename__ = 'logsession'
    id = Column(Integer, primary_key=True, autoincrement=True)
    start = Column(DateTime)
    stop = Column(DateTime)
    name = Column(String, default='Collection')
    notes = Column(String, default=None)
    user = Column(String, default=None)

    def __init__(self, name, notes=None, user=None):
        self.start = utils.now()
        self.name = name
        self.notes = notes
        self.user = user


class LogData(Base):
    __tablename__ = 'logdata'
    id = Column(Integer, primary_key=True, autoincrement=True)
    data = Column(String)
    timestamp = Column(DateTime, default=None)
    session_id = Column(Integer, ForeignKey('logsession.id'), index=True)
    session = relationship(LogSession)


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
def session_scope(fp, commit=False, lock=None):
    """Provide a transactional scope around a series of operations."""
    if lock:
        with lock:
            session = get_session(fp)
            try:
                yield session
                if commit:
                    session.commit()
            except exc.SQLAlchemyError:
                log.exception('Failure during session - rolling back any changes.')
                session.rollback()
                raise
            finally:
                session.close()
    else:
        session = get_session(fp)
        try:
            yield session
            if commit:
                session.commit()
        except exc.SQLAlchemyError:
            log.exception('Failure during session - rolling back any changes.')
            session.rollback()
            raise
        finally:
            session.close()
