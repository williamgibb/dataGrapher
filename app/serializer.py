import logging
import threading
import multiprocessing
import queue

from .model import session_scope, make_db, LogSession, LogData
from . import constants
from . import utils

log = logging.getLogger(__name__)


class DBSerializer(threading.Thread):
    # noinspection PyUnusedLocal
    def __init__(self,
                 output_queue: multiprocessing.Queue,
                 die_event: multiprocessing.Event,
                 serial_lock: multiprocessing.Lock,
                 db_fp: str,
                 logsession: LogSession,
                 print_diff: bool =True
                 **kwargs):
        super().__init__()
        self.queue = output_queue
        self.die_event = die_event
        self.lock = serial_lock
        self.db = db_fp
        self.ls = logsession
        self.session_id = None
        self.previous_value = 0.0
        self.print_diff = print_diff
        make_db(self.db)

    def run(self):
        log.info('{} is running!'.format(self.name))

        with session_scope(self.db, commit=True, lock=self.lock) as s:
            s.add(self.ls)
            s.commit()
            self.session_id = self.ls.id

        while True:
            if self.die_event.is_set():
                log.info('[{}] Die event set'.format(self.name))
                break

            try:
                v = self.queue.get(timeout=1)
            except queue.Empty:
                continue

            log.debug('{} got: {}'.format(self.name, v))

            unit = constants.UNKNOWN_UNIT
            if isinstance(v, str):
                m = constants.EMISSION_REGEX.search(v)
                if not m:
                    pass # XXX ????
                d = m.groupdict()
                unit = d.get('unit')
                v = float(d.get('value'))
            elif isinstance(v, str):
                v = float(v)

            difference = v - self.previous_value
            self.previous_value = v
            if self.print_diff:
                log.info('Diff: {}'.format(difference))

            with session_scope(self.db, commit=True, lock=self.lock) as s:
                ld = LogData(data=v,
                             unit=unit,
                             difference=difference,
                             timestamp=utils.now(),
                             session_id=self.session_id)
                s.add(ld)

        log.info('Closing session: {}'.format(self.session_id))
        with session_scope(self.db, commit=True, lock=self.lock) as s:
            ls = s.query(LogSession).filter_by(id=self.session_id).one()
            ls.stop = utils.now()
            s.add(ls)
        log.info('[{}] is exiting'.format(self.name))
        return
