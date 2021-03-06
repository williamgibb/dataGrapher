import argparse
import logging
import multiprocessing
import os
import queue
import sys
import time
# Third Party Code
import pandas
import serial.tools.list_ports as list_ports
# Custom Code
from . import daq
from . import grapher
from . import model
from . import serializer
from . import serial_settings
from . import utils

log = logging.getLogger(__name__)

RANDOM = 'random'
SAWTOOTH = 'sawtooth'


def main(options):
    die_event = multiprocessing.Event()
    close_event = multiprocessing.Event()
    daq_queue = multiprocessing.Queue()
    serial_queue = multiprocessing.Queue()
    vis_queue = multiprocessing.Queue()
    serial_lock = multiprocessing.Lock()
    ls = model.LogSession(name=options.name,
                          notes=options.notes,
                          user=options.user)

    if options.test == RANDOM:
        daqt = daq.MockDAQ(serial_port_settings={},
                           output_queue=daq_queue,
                           die_event=die_event)
    elif options.test == SAWTOOTH:
        daqt = daq.MockSawtoothDAQ(serial_port_settings={},
                                   output_queue=daq_queue,
                                   die_event=die_event)
    else:
        # Now we use a real DAQ!
        port = options.port
        if not port:
            log.error('Must specify a port.')
            sys.exit(1)
        ps = serial_settings.MT_NCLASSIC_DEFAULT.copy()
        ps['port'] = options.port
        daqt = daq.MettlerNBDAQ(serial_port_settings=ps,
                                output_queue=daq_queue,
                                die_event=die_event,
                                stable_only=options.stable_only)
    daqt.name = 'DAQ-Thread'
    sert = serializer.DBSerializer(output_queue=serial_queue,
                                   die_event=die_event,
                                   serial_lock=serial_lock,
                                   db_fp=options.db,
                                   logsession=ls,
                                   print_diff=options.print_diff)
    sert.name = 'SERT-Thread'
    # noinspection PyUnusedLocal
    c = grapher.Canvas(output_queue=vis_queue,
                       n=100,
                       close_event=close_event)
    threads = [daqt, sert]
    for thread in threads:
        thread.start()

    # noinspection PyBroadException
    try:
        grapher.app.create()
        while True:
            try:
                v = daq_queue.get(timeout=0.01)
            except queue.Empty:
                v = None
            if v:
                log.debug('Main Q got: {}'.format(v))
                serial_queue.put(v)
                vis_queue.put(v)
            grapher.app.process_events()
            if close_event.is_set():
                break
            for thread in threads:
                if not thread.is_alive():
                    log.error('Thread [{}] was found dead! Exiting main loop.'.format(thread.name))
    except KeyboardInterrupt:
        log.info('Caught KeyboardInterrupt')
    except:
        log.exception('Unhandled exception')
    finally:
        log.info('Shutting down UI and threads.')
        if not die_event.is_set():
            die_event.set()
        grapher.app.quit()
        for thread in threads:
            while True:
                log.debug('Checking [{}]'.format(thread.name))
                if not thread.is_alive():
                    log.debug('[{}] is not alive.'.format(thread.name))
                    break
                time.sleep(0.1)

    sys.exit(0)


def dump_sessions(options):
    if not os.path.isfile(options.db):
        log.error('DB is not a file. [{}]'.format(options.db))
        sys.exit(1)
    with model.session_scope(options.db) as s:
        r = s.query(model.LogSession).all()
        r = [model.row2dict(row) for row in r]
    if not r:
        log.error('No LogSession rows found.')
        sys.exit(1)
    ba = utils.BetterAsciiTable('')
    ba.add_rows(r, wrap_keys={'notes': {'width': 37}})
    print(ba.table)
    sys.exit(0)


def dump_session_data(options):
    if not os.path.isfile(options.db):
        log.error('DB is not a file. [{}]'.format(options.db))
        sys.exit(1)
    with model.session_scope(options.db) as s:
        r = s.query(model.LogData).filter_by(session_id=options.id).all()
        r = [model.row2dict(row) for row in r]
    if not r:
        log.error('No rows found for id: {}'.format(options.id))
        sys.exit(1)
    fp = options.output
    if not options.output:
        with model.session_scope(options.db) as s:
            ls = s.query(model.LogSession).filter_by(id=options.id).one()
            fp = '{}_{}_{}.xlsx'.format(ls.name, ls.start, ls.stop)
    log.info('Writing data to [{}]'.format(fp))
    df = pandas.DataFrame(r)
    df.to_excel(fp, index=False)
    sys.exit(0)


def replay_session(options):
    if not os.path.isfile(options.db):
        log.error('DB is not a file. [{}]'.format(options.db))
        sys.exit(1)
    with model.session_scope(options.db) as s:
        r = s.query(model.LogData).filter_by(session_id=options.id).all()
        r = [row.data for row in r]

    die_event = multiprocessing.Event()
    close_event = multiprocessing.Event()
    daq_queue = multiprocessing.Queue()
    vis_queue = multiprocessing.Queue()
    daqt = daq.ReplayDAQ(output_queue=daq_queue,
                         die_event=die_event,
                         replay_data=r,
                         replay_rate=options.replay_rate)
    daqt.name = 'Replay-Thread'
    # noinspection PyUnusedLocal
    c = grapher.Canvas(output_queue=vis_queue,
                       n=100,
                       close_event=close_event)
    daqt.start()

    # noinspection PyBroadException
    try:
        grapher.app.create()
        while True:
            try:
                v = daq_queue.get(timeout=0.01)
            except queue.Empty:
                v = None
            if v:
                log.debug('Main Q got: {}'.format(v))
                vis_queue.put(v)
            grapher.app.process_events()
            if close_event.is_set():
                log.info('UI window closed - ending data collection')
                break
    except KeyboardInterrupt:
        log.info('Caught KeyboardInterrupt')
    except:
        log.exception('Unhandled exception')
    finally:
        die_event.set()
        grapher.app.quit()
        for t in [daqt]:
            while True:
                if not t.is_alive():
                    break
                time.sleep(0.1)
    sys.exit(0)


# noinspection PyUnusedLocal,PyShadowingNames
def call_list_ports(opts):
    """
    List all of the available serial ports on the system.

    :param opts: Unused.
    :return:
    """
    sys.argv = [sys.argv[0]]
    list_ports.main()
    sys.exit(0)


def get_parser():
    p = argparse.ArgumentParser(description='Runs the datagrapher application.')
    subps = p.add_subparsers(help='sub-command help')
    p.add_argument('-d', '--db', dest='db', default='test.db', action='store', type=str,
                   help='Name of the db to store data into')
    p.add_argument('-v', dest='verbose', default=False, action='store_true',
                   help='Enable verbose output')
    collect = subps.add_parser('collect', help='Collect, graph and store data.')
    collect.set_defaults(func=main)
    collect.add_argument('-t', '--test', dest='test', choices=[None, RANDOM, SAWTOOTH], default=None, type=str.lower,
                         help='Perform a data capture and serialization test.')
    collect.add_argument('-c', '--collection-name', dest='name', default='Collection', action='store', type=str,
                         help='Name of the data collection')
    collect.add_argument('-n', '--notes', dest='notes', default=None, action='store', type=str,
                         help='Notes related to the data collection')
    collect.add_argument('-u', '--username', dest='user', default=utils.current_user(), action='store', type=str,
                         help='User performing the data collection')
    collect.add_argument('-p', '--port', dest='port', default=None, action='store', type=str,
                         help='Serial port to connect to in order to collect data.')
    collect.add_argument('--no-print-diff', dest='print_diff', default=True, action='store_false',
                         help='Do not print the difference value written to the database.')
    collect.add_argument('-s', '--stable-only', dest='stable_only', default=False, action='store_true',
                         help='Only record stable values')
    listd = subps.add_parser('list', help='List session collection data')
    listd.set_defaults(func=dump_sessions)
    listp = subps.add_parser('ports', help='List serial ports available for use')
    listp.set_defaults(func=call_list_ports)
    dumpd = subps.add_parser('dump', help='Dump session collection data')
    dumpd.set_defaults(func=dump_session_data)
    dumpd.add_argument('-i', '--id', required=True, type=int,
                       help='Dump the data from a particular data collection to a xlsx file.')
    dumpd.add_argument('-o', '--output', default=None, type=str,
                       help='File to dump the data out too')
    replay = subps.add_parser('replay', help='Replay the visualization for a given session')
    replay.add_argument('-i', '--id', required=True, type=int,
                        help='Session ID to replay the data from.')
    replay.add_argument('-r', '--replay-rate', default=0.3, type=float, dest='replay_rate',
                        help='Rate in which to replay events from the database.')
    replay.set_defaults(func=replay_session)

    return p


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s:%(levelname)s: %(message)s [%(module)s.%(funcName)s]',
                        datefmt='%m/%d/%Y %I:%M:%S %p',
                        level=logging.DEBUG, )
    parser = get_parser()
    opts = parser.parse_args()
    if 'func' not in opts:
        parser.print_help()
        sys.exit(1)
    if not opts.verbose:
        logging.disable(logging.DEBUG)
    opts.func(opts)
