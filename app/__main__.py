import argparse
import logging
import multiprocessing
import queue
import time
# Custom Code
from . import daq
from . import grapher
from . import model
from . import serializer
from . import utils

log = logging.getLogger(__name__)


def main(options):
    if not options.verbose:
        logging.disable(logging.DEBUG)
    die_event = multiprocessing.Event()
    close_event = multiprocessing.Event()
    daq_queue = multiprocessing.Queue()
    serial_queue = multiprocessing.Queue()
    vis_queue = multiprocessing.Queue()
    serial_lock = multiprocessing.Lock()
    ls = model.LogSession(name=options.name,
                          notes=options.notes,
                          user=options.user)

    daqt = daq.MockSawtoothDAQ(serial_port_settings={},
                               output_queue=daq_queue,
                               die_event=die_event)
    daqt.name = 'DAQ-Thread'
    sert = serializer.DBSerializer(output_queue=serial_queue,
                                   die_event=die_event,
                                   serial_lock=serial_lock,
                                   db_fp=options.db,
                                   logsession=ls)
    sert.name = 'SERT-Thread'
    # noinspection PyUnusedLocal
    c = grapher.Canvas(output_queue=vis_queue,
                       n=100,
                       close_event=close_event)
    daqt.start()
    sert.start()
    try:
        grapher.app.create()
        while True:
            try:
                v = daq_queue.get(block=False)
            except queue.Empty:
                v = None
            if v:
                log.debug('Main Q got: {}'.format(v))
                serial_queue.put(v)
                vis_queue.put(v)
            grapher.app.process_events()
            if close_event.is_set():
                break
    except KeyboardInterrupt:
        log.info('Caught KeyboardInterrupt')
    finally:
        die_event.set()
        grapher.app.quit()
        for t in [daqt, sert]:
            while True:
                if not t.is_alive():
                    break
                time.sleep(0.1)


def get_parser():
    p = argparse.ArgumentParser(description='Runs the datagrapher application.')
    p.add_argument('-d', '--db', dest='db', default='test.db', action='store', type=str,
                   help='Name of the db to store data into')
    p.add_argument('--collection-name', dest='name', default='Collection', action='store', type=str,
                   help='Name of the data collection')
    p.add_argument('--notes', dest='notes', default=None, action='store', type=str,
                   help='Notes related to the data collection')
    p.add_argument('--username', dest='user', default=utils.current_user(), action='store', type=str,
                   help='User performing the data collection')
    p.add_argument('-v', dest='verbose', default=False, action='store_true',
                   help='Enable verbose output')
    return p


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', datefmt='%m/%d/%Y %I:%M:%S %p',
                        level=logging.DEBUG, )
    parser = get_parser()
    opts = parser.parse_args()
    main(opts)
