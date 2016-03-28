import logging
import threading
import multiprocessing
import random
import time

import serial

log = logging.getLogger(__name__)

class MockDAQ(threading.Thread):
    def __init__(self,
                 serial_port_settings: dict,
                 output_queue: multiprocessing.Queue,
                 die_event: multiprocessing.Event,
                 ):
        super().__init__()
        self.serial_port_settings = serial_port_settings
        self.queue = output_queue
        self.die_event = die_event

    def run(self):
        log.info('{} is running!'.format(self.name))
        while True:
            if self.die_event.is_set():
                break
            v = random.random() * 10
            log.debug('Emitting {}'.format(v))
            self.queue.put(v)
            # In reality we would do non-blocking reads for line oriented data
            time.sleep(1)
        log.info('[{}] is exiting'.format(self.name))