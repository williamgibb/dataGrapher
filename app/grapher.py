import logging
import math
import multiprocessing
import queue
# Third party code
import numpy as np
from vispy import gloo
from vispy import app

log = logging.getLogger(__name__)

# Shaders lifted
# from https://github.com/vispy/vispy/blob/master/examples/demo/gloo/realtime_signals.py
VERT_SHADER = """
#version 120

// y coordinate of the position.
attribute float a_position;

// row, col, and time index.
attribute vec3 a_index;
varying vec3 v_index;

// 2D scaling factor (zooming).
uniform vec2 u_scale;

// Size of the table.
uniform vec2 u_size;

// Number of samples per signal.
uniform float u_n;

// Color.
attribute vec3 a_color;
varying vec4 v_color;

// Varying variables used for clipping in the fragment shader.
varying vec2 v_position;
varying vec4 v_ab;

void main() {
    float nrows = u_size.x;
    float ncols = u_size.y;

    // Compute the x coordinate from the time index.
    float x = -1 + 2*a_index.z / (u_n-1);
    vec2 position = vec2(x - (1 - 1 / u_scale.x), a_position);

    // Find the affine transformation for the subplots.
    vec2 a = vec2(1./ncols, 1./nrows)*.9;
    vec2 b = vec2(-1 + 2*(a_index.x+.5) / ncols,
                  -1 + 2*(a_index.y+.5) / nrows);
    // Apply the static subplot transformation + scaling.
    gl_Position = vec4(a*u_scale*position+b, 0.0, 1.0);

    v_color = vec4(a_color, 1.);
    v_index = a_index;

    // For clipping test in the fragment shader.
    v_position = gl_Position.xy;
    v_ab = vec4(a, b);
}
"""

FRAG_SHADER = """
#version 120

varying vec4 v_color;
varying vec3 v_index;

varying vec2 v_position;
varying vec4 v_ab;

void main() {
    gl_FragColor = v_color;

    // Discard the fragments between the signals (emulate glMultiDrawArrays).
    if ((fract(v_index.x) > 0.) || (fract(v_index.y) > 0.))
        discard;

    // Clipping test.
    vec2 test = abs((v_position.xy-v_ab.zw)/v_ab.xy);
    if ((test.x > 1) || (test.y > 1))
        discard;
}
"""


class Canvas(app.Canvas):
    def __init__(self,
                 output_queue: multiprocessing.Queue,
                 n: int,
                 close_event: multiprocessing.Event):
        # Setup stuff
        self.queue = output_queue
        self.close_event = close_event
        self.n = n
        self.nrows = 2
        self.ncols = 1
        self.m = self.nrows * self.ncols
        self.lock = multiprocessing.Lock()
        self.input_data = np.array([1.0 for i in range(self.n)])
        self.diff_data = np.array([1.0 for i in range(self.n)])
        self.graph_data = np.stack((self.diff_data, self.input_data)).astype(np.float32)
        self.index = np.c_[np.repeat(np.repeat(np.arange(self.ncols), self.nrows), self.n),
                           np.repeat(np.tile(np.arange(self.nrows), self.ncols), self.n),
                           np.tile(np.arange(self.n), self.m)].astype(np.float32)
        # These colors should be fixed colors!
        self.color = np.repeat(np.random.uniform(size=(self.m, 3), low=.5, high=.9),
                               self.n,
                               axis=0).astype(np.float32)
        # Build the app.Canvas and  set variables
        app.Canvas.__init__(self, title='Use your wheel to zoom!',
                            keys='interactive')
        self.program = gloo.Program(VERT_SHADER, FRAG_SHADER)
        with self.lock:
            self.program['a_position'] = self.graph_data.reshape(-1, 1)
        self.program['a_color'] = self.color
        self.program['a_index'] = self.index
        self.program['u_scale'] = (1., 1.)
        self.program['u_size'] = (self.nrows, self.ncols)
        self.program['u_n'] = n

        gloo.set_viewport(0, 0, *self.physical_size)

        self._timer = app.Timer(connect=self.on_timer, start=True)

        gloo.set_state(clear_color='black', blend=True,
                       blend_func=('src_alpha', 'one_minus_src_alpha'))
        self.show()

    def on_resize(self, event):
        gloo.set_viewport(0, 0, *event.physical_size)

    def on_mouse_wheel(self, event):
        dx = np.sign(event.delta[1]) * .05
        scale_x, scale_y = self.program['u_scale']
        scale_x_new, scale_y_new = (scale_x * math.exp(2.5 * dx),
                                    scale_y * math.exp(0.0 * dx))
        self.program['u_scale'] = (max(1, scale_x_new), max(1, scale_y_new))
        self.update()

    def on_timer(self, event):
        """
        Grab data from the queue and put them onto the end of the numpy arrays.
        :param event:
        :return:
        """
        while True:
            try:
                v = self.queue.get(block=False)
            except queue.Empty:
                break
            self.update_array(v)
            with self.lock:
                self.program['a_position'].set_data(self.graph_data.ravel().astype(np.float32))
        self.update()

    def on_draw(self, event):
        gloo.clear()
        self.program.draw('line_strip')

    def on_close(self, event):
        log.debug('Close event found.')
        self.close_event.set()

    def update_array(self, v):
        """
        Append a value to the end of the numpy array and update
        the difference array.

        :param v:
        :return:
        """
        k = 1
        with self.lock:
            self.input_data[:-k] = self.input_data[k:]
            self.input_data[-k:] = v
            self.diff_data = np.diff(self.input_data)
            # lol its like leftpad
            self.diff_data = np.insert(self.diff_data, 0, self.diff_data[0])
            self.graph_data = np.stack((self.diff_data, self.input_data)).astype(np.float32)
