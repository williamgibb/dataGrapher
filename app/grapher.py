import logging
import threading
import multiprocessing
import queue
import random
import time



log = logging.getLogger(__name__)

class MockGrapher(threading.Thread):
    def __init__(self,
                 output_queue: multiprocessing.Queue,
                 die_event: multiprocessing.Event,
                 ):
        super().__init__()
        self.queue = output_queue
        self.die_event = die_event

    def run(self):
        log.info('{} is running!'.format(self.name))
        while True:
            if self.die_event.is_set():
                break
            try:
                v = self.queue.get(timeout=1)
            except queue.Empty:
                continue
            log.info("Graphing: {}".format(v))
        log.info('[{}] is exiting'.format(self.name))