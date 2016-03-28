import argparse
import logging
import multiprocessing
import queue
import time

from . import daq
from . import serializer
from . import grapher

log = logging.getLogger(__name__)

def main(options):
    if not options.verbose:
        logging.disable(logging.DEBUG)
    die_event = multiprocessing.Event()
    daq_queue = multiprocessing.Queue()
    serial_queue = multiprocessing.Queue()
    vis_queue = multiprocessing.Queue()

    daqt = daq.MockDAQ(serial_port_settings={},
                       output_queue=daq_queue,
                       die_event=die_event)
    sert = serializer.MockSerializer(output_queue=serial_queue,
                                     die_event=die_event)
    grat = grapher.MockGrapher(output_queue=vis_queue,
                               die_event=die_event)
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
        for t in [daqt, sert]:
            while True:
                if not t.is_alive():
                    break
                time.sleep(0.1)
        raise



def get_parser():
    p = argparse.ArgumentParser(description='Runs the datagrapher application.')
    p.add_argument('-v', dest='verbose', default=False, action='store_true',
                   help='Enable verbose output')
    return p

if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', datefmt='%m/%d/%Y %I:%M:%S %p',
                        level=logging.DEBUG, )
    p = get_parser()
    options = p.parse_args()
    main(options)
