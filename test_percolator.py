# -*- coding: utf-8 -*-

import unittest
#import logging

import pyb
import gc
#import math
#import random
import uctypes

from ws2812 import WS2812 #, Pixel, PREALLOCATE, CACHE, RECREATE
from lights import Lights
from percolator import Percolator

#log = logging.getLogger("test_ws2812")

def tg(led_count, start):

    def triple(n):
        for i in range(3):
            yield (n + i) & 0xff

    for i in range(led_count):
        yield triple(start + 3*i)


class PercolatorTestCase(unittest.TestCase):
    def setUp(self):
        #logging.basicConfig(level=logging.INFO)
        #random.seed("WSlice")
        self.ws = ws = WS2812(1,64)
        for i in range(len(ws)):
            ws[i] = (i, 2*i, 3*i)
        self.p = Percolator(ws)

    def tearDown(self):
        self.ws = self.p = None
        gc.collect()
    
    def test_render_init(self):
        # A Percolator is initially in a state that renders all off
        self.p.render()
        self.assertTrue(all(sum(v)==0 for v in self.ws))

    def test_render_time(self):
        # Rendering takes the expected amount of time
        n = 10
        t0 = pyb.micros()
        for i in range(n):
            self.p.render()
        dt = pyb.elapsed_micros(t0)
        average_ms = dt / (n * 1000)
        print("%d renders average %f ms" % (n, average_ms), end='')
        self.assertTrue(average_ms < 15, "average render time %f ms" % (average_ms))

    def test_render_at_index_0(self):
        # A Percolator can render itself to the backing LEDs
        lattice = self.p.lattice
        ref = (12, 34, 56)
        for i, v in enumerate(ref):
            lattice[0][i] = v
        self.p.render()
        self.assertEqual(tuple(self.ws[0]), ref)
        self.assertTrue(all(sum(v)==0 for v in self.ws[1:]))

    def test_render_at_index_0_various_brightness(self):
        # A Percolator can render itself to the backing LEDs with controlled brightness
        lattice = self.p.lattice
        color = (12, 34, 56)
        ref = [0] * 3
        for brightness in (1.0, 0.5, 0.1, 0.01, 3/17, 1/254, 1/255, 1/256, 0.0):
            print(' %r' % brightness, end='')
            self.p.brightness = brightness
            for i, v in enumerate(color):
                lattice[0][i] = v
                ref[i] = round(brightness * v)
            self.p.render()
            self.assertEqual(tuple(self.ws[0]), tuple(ref))
            self.assertTrue(all(sum(v)==0 for v in self.ws[1:]))

    def test_render_at_several_positions(self):
        # A Percolator can render itself to the backing LEDs
        lattice = self.p.lattice
        for k, g in enumerate(tg(64, 0)):
            for i, v in enumerate(g):
                lattice[k][i] = v
        self.p.render()
        for led, g in zip(self.ws, tg(64,0)):
            self.assertEqual(tuple(led), tuple(g))


def main():
    unittest.main()
    return
    # Burn-in test:
    while True:
        try:
            unittest.main()
        except MemoryError as e:
            #print("MemoryError:", e)
            pyb.info()
            raise

if __name__ == '__main__':
    main()
        
