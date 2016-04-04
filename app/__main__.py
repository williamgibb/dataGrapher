import argparse
import logging
import multiprocessing
import queue
import time

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
    daq_queue = multiprocessing.Queue()
    serial_queue = multiprocessing.Queue()
    vis_queue = multiprocessing.Queue()
    serial_lock = multiprocessing.Lock()
    ls = model.LogSesssion(name=options.name,
                           notes=options.notes,
                           user=options.user)

    daqt = daq.MockDAQ(serial_port_settings={},
                       output_queue=daq_queue,
                       die_event=die_event)
    sert = serializer.DBSerializer(output_queue=serial_queue,
                                   die_event=die_event,
                                   serial_lock=serial_lock,
                                   db_fp=options.db,
                                   logsession=ls)
    # grat = grapher.MockGrapher(output_queue=vis_queue,
    #                            die_event=die_event)
    grat = grapher.VisGrapher(output_queue=vis_queue,
                              die_event=die_event,
                              array_size=100)
    daqt.start()
    sert.start()
    grat.start()
    try:
        while True:
            try:
                v = daq_queue.get(timeout=1)
            except queue.Empty:
                continue
            serial_queue.put(v)
            vis_queue.put(v)
    except KeyboardInterrupt:
        die_event.set()
        for t in [daqt, sert, grat]:
            while True:
                if not t.is_alive():
                    break
                time.sleep(0.1)
        raise



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
    p = get_parser()
    options = p.parse_args()
    main(options)
