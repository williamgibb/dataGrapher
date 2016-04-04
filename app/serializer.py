import logging
import threading
import multiprocessing
import queue

from .model import session_scope, make_db, LogSesssion, LogData
from . import utils

log = logging.getLogger(__name__)


class MockSerializer(threading.Thread):
    # noinspection PyUnusedLocal
    def __init__(self,
                 output_queue: multiprocessing.Queue,
                 die_event: multiprocessing.Event,
                 serial_lock: multiprocessing.Lock,
                 **kwargs
                 ):
        super().__init__()
        self.queue = output_queue
        self.die_event = die_event
        self.lock = serial_lock

    def run(self):
        log.info('{} is running!'.format(self.name))
        while True:
            if self.die_event.is_set():
                break
            try:
                v = self.queue.get(timeout=1)
            except queue.Empty:
                continue
            with self.lock:
                log.info("Read: {}".format(v))
        log.info('[{}] is exiting'.format(self.name))


class DBSerializer(threading.Thread):
    # noinspection PyUnusedLocal
    def __init__(self,
                 output_queue: multiprocessing.Queue,
                 die_event: multiprocessing.Event,
                 serial_lock: multiprocessing.Lock,
                 db_fp: str,
                 logsession: LogSesssion,
                 **kwargs):
        super().__init__()
        self.queue = output_queue
        self.die_event = die_event
        self.lock = serial_lock
        self.db = db_fp
        self.ls = logsession
        self.session_id = None
        make_db(self.db)

    def run(self):
        log.info('{} is running!'.format(self.name))

        with session_scope(self.db, commit=True, lock=self.lock) as s:
            s.add(self.ls)
            s.commit()
            self.session_id = self.ls.id

        while True:
            if self.die_event.is_set():
                break

            try:
                v = self.queue.get(timeout=1)
            except queue.Empty:
                continue

            with session_scope(self.db, commit=True, lock=self.lock) as s:
                ld = LogData(data=v,
                             timestamp=utils.now(),
                             session_id=self.session_id)
                s.add(ld)

        log.info('Closing session: {}'.format(self.session_id))
        with session_scope(self.db, commit=True, lock=self.lock) as s:
            ls = s.query(LogSesssion).filter_by(id=self.session_id).one()
            ls.stop = utils.now()
            s.add(ls)
        log.info('[{}] is exiting'.format(self.name))
        return
