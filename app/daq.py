import logging
import threading
import multiprocessing
import random
import re
import time

import serial

from . import constants

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
                log.info('[{}] Die event set'.format(self.name))
                break
            v = random.random()
            log.debug('Emitting {}'.format(v))
            self.queue.put(v)
            time.sleep(0.3)
            # In reality we would do non-blocking reads for line oriented data
        log.info('[{}] is exiting'.format(self.name))


class MockSawtoothDAQ(threading.Thread):
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
        increment = 0.1
        v = 0.0
        while True:
            if self.die_event.is_set():
                log.info('[{}] Die event set'.format(self.name))
                break
            v += increment
            log.debug('Emitting {}'.format(v))
            self.queue.put(v)
            time.sleep(0.3)
            if v + increment > 1.0:
                increment *= -1.0
            if v + increment < - 1.0:
                increment *= -1.0
                # In reality we would do non-blocking reads for line oriented data
        log.info('[{}] is exiting'.format(self.name))


class ReplayDAQ(threading.Thread):
    def __init__(self,
                 output_queue: multiprocessing.Queue,
                 die_event: multiprocessing.Event,
                 replay_data: list,
                 replay_rate: float =1.0,
                 ):
        super().__init__()
        self.queue = output_queue
        self.die_event = die_event
        self.replay_data = replay_data
        self.replay_rate = replay_rate

    def run(self):
        log.info('{} is running!'.format(self.name))
        i = 0
        j = len(self.replay_data)
        while True:
            if self.die_event.is_set():
                log.info('[{}] Die event set'.format(self.name))
                break
            v = self.replay_data[i]
            log.debug('Emitting {}'.format(v))
            self.queue.put(v)
            time.sleep(self.replay_rate)
            i = (i + 1) % j
        log.info('[{}] is exiting'.format(self.name))


class MettlerNBDAQ(threading.Thread):
    """
    DAQ for reading in serial data from the Mettler-Toledo
    NewBalance scales.

    This assumes that the scale has been configured to operate
    in PRINTER or HOST mode, not PC-DIR mode.

    LPT: Don't use PC-DIR mode ever.  It is really only good
    for use with the MT keystroke-capture software - it sends
    weird 'enter\x1b' line terminators instead of the configured
    line terminators for the balance.
    """
    def __init__(self,
                 serial_port_settings: dict,
                 output_queue: multiprocessing.Queue,
                 die_event: multiprocessing.Event,
                 stable_only: bool =False):
        super().__init__()
        self.serial_port_settings = serial_port_settings
        self.queue = output_queue
        self.die_event = die_event
        self.stable_only = stable_only
        self.serial = serial.Serial()


    def run(self):
        log.info('{} is running!'.format(self.name))
        # Open up the serial port
        self.serial = serial.Serial(**self.serial_port_settings)
        while True:
            if self.die_event.is_set():
                log.info('[{}] Die event set'.format(self.name))
                break
            line = self.serial.readline()
            if not line:
                continue
            try:
                s = line.decode().strip()
            except UnicodeDecodeError:
                log.error('Failed to decode line: {}'.format(line))
                continue
            log.debug('Read line: [{}]'.format(s))
            if self.stable_only:
                # PRINTER MODE
                # STAB - no indicator of change is included - simply no lines are printed
                # AUTO - only the stable weights are printed regardless of interval setting.
                # ALL - every value is printed when the interval fires
                #     There sometimes are 'D' characters inserted on non-stable measures
                #
                # HOST MODE
                # STABLE - only the stable values are printed w/ a 'S S'.
                # CONT - Constant measurement (no rate limiting!) - with 'S S' and 'S D' included.
                # AUTO - only stable values are printed w/ a 'S S'
                # ALL - stable values are printed w/ a 'S S'.  Changing (unstable values) have a 'S D' in them.
                if 'D' in s:
                    continue
            self.emit_value(s)
        log.info('Closing serial port')
        self.serial.close()
        # Close the serial port
        log.info('[{}] is exiting'.format(self.name))

    def emit_value(self, s):
        """
        Emits a string of data which only contains the numeric portion of the reading and any size measurements.

        :param s:
        :return:
        """
        m = constants.EMISSION_REGEX.search(s)
        if not m:
            log.warning('Unable to find emission match for: [{}]'.format(s))
            return
        v = m.group()
        self.queue.put(v)
