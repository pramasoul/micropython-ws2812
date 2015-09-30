# -*- coding: utf-8 -*-
import unittest
#import logging

import pyb
import gc
#import math
#import random

from ws2812 import WS2812
from lights import Lights

#log = logging.getLogger("test_ws2812")

# A helper
def tg(led_count, start):

    def triple(n):
        for i in range(3):
            yield (n + i) & 0xff

    for i in range(led_count):
        yield triple(start + 3*i)


class LightSliceTestCase(unittest.TestCase):
    def setUp(self):
        #logging.basicConfig(level=logging.INFO)
        gc.collect()

    def tearDown(self):
        pass
    

    def test_slice(self):
        ws = WS2812(1, 8)
        lights = Lights(ws)
        self.assertEqual(len(lights), 8)


    def test_slice_sliced_rval(self):
        # Lights sliced as an rval
        ws = WS2812(1, 8)
        lights = Lights(ws)

        # Fill the lattice with a recognizable pattern
        for i, p in enumerate(tg(len(lights), 0)):
            lat = lights.lattice[i]
            for j, c in enumerate(p):
                lat[j] = c

        sls = lights[:2]

        # A sliced Lights has the correct length
        self.assertEqual(len(sls), 2)

        # A sliced Lights refers to the same lattice, not a copy
        self.assertIs(sls.lattice, lights.lattice)

        # A sliced Lights iterates over the correct lattice points
        self.assertEqual(list(sls), [bytearray(v) for v in tg(2,0)])

        # A Lights can be sliced non-trivially and iterate over the
        # correct lattice points
        sls = lights[-2:-6:-2]
        self.assertEqual(len(sls), 2)
        self.assertEqual(list(sls), [bytearray(v) for v in [(18,19,20), (12,13,14)]])

    def test_slice_sliced_lval(self):
        # Lights sliced as an lval
        ws = WS2812(1, 8)
        lights = Lights(ws)

        # Fill the lattice with a recognizable pattern
        for i, p in enumerate(tg(len(lights), 0)):
            lat = lights.lattice[i]
            for j, c in enumerate(p):
                lat[j] = c
        ref = lights.lattice[:]

        sls = lights[-2:-6:-2]

        # A Lights is indexable by an int for writing
        sls[1] = (10, 9, 8)
        self.assertEqual(list(sls), [bytearray(v) for v in [(18,19,20), (10,9,8)]])

        # A Lights is indexable by a slice for writing
        sls[:] = [b'foo', b'bar']
        self.assertEqual(list(sls), [bytearray(v) for v in [b'foo', b'bar']])

        # The writes happen in the right place
        self.assertEqual([lights[6], lights[4]], [bytearray(v) for v in [b'foo', b'bar']])

        # Other places don't get written
        self.assertEqual(list((i, lights[i]) for i in range(len(lights)) if i not in (6,4)),
            list((i, bytearray(t)) for i, t in enumerate(tg(len(lights), 0)) if i not in (6,4)))
        
                         
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
        
