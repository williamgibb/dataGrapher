import logging
import threading
import multiprocessing
import queue
# Third party code
import numpy

log = logging.getLogger(__name__)

class MockGrapher(threading.Thread):
    def __init__(self,
                 output_queue: multiprocessing.Queue,
                 die_event: multiprocessing.Event,
                 array_size = 100,
                 **kwargs
                 ):
        super().__init__()
        self.queue = output_queue
        self.die_event = die_event
        self.array_size = array_size
        self.input_data = numpy.array([1.0 for i in range(self.array_size)])
        self.diff_data = numpy.diff(self.input_data)


    def run(self):
        log.info('{} is running!'.format(self.name))
        n = 0
        while True:
            if self.die_event.is_set():
                break
            try:
                v = self.queue.get(timeout=1)
            except queue.Empty:
                continue
            log.info("Graphing: {}".format(v))
            self.update_array(v)
            if n == self.array_size:
                print(self.input_data)
                print(self.diff_data)
                n = 0
            n = n + 1
        log.info('[{}] is exiting'.format(self.name))

    def update_array(self, v):
        """
        Append a value to the end of the numpy array and update
        the difference array.

        :param v:
        :return:
        """
        k = 1
        self.input_data[:-k] = self.input_data[k:]
        self.input_data[-k:] = v
        self.diff_data = numpy.diff(self.input_data)