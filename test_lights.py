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
        self.ws = WS2812(1, 8)
        self.lights = lights = Lights(self.ws)

        # Fill the lattice with a recognizable pattern
        for i, c in enumerate(tg(len(lights), 0)):
            p = lights.lattice[i]
            for j, v in enumerate(c):
                p[j] = v

    def tearDown(self):
        self.ws = self.lights = None
        gc.collect()

    def test_slice(self):
        ws = self.ws
        lights = self.lights
        self.assertEqual(len(lights), 8)

    def test_clear(self):
        ws = self.ws
        lights = self.lights
        lights.clear()
        self.assertEqual(sum(sum(c) for c in lights), 0)

    def test_clear_sliced(self):
        ws = self.ws
        lights = self.lights
        sls = lights[-2:-6:-2]
        expect = [tuple(c) for c in tg(len(lights), 0)]
        self.assertEqual(len(sls), 2)
        self.assertEqual(list(sls), [bytearray(v) for v in [(18,19,20), (12,13,14)]])
        self.assertEqual([tuple(v) for v in lights], expect)
        sls.clear()
        expect[6] = expect[4] = (0,0,0)
        self.assertEqual([tuple(v) for v in lights], expect)


    def test_slice_sliced_rval(self):
        # Lights sliced as an rval
        ws = self.ws
        lights = self.lights

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
        ws = self.ws
        lights = self.lights
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
        
        # Can accept generator rval
        sls[:] = tg(1000, 50)   # which can be willing to run over
        self.assertEqual([p for p in sls],
                         [bytearray(c) for c in tg(len(sls), 50)])

                         
class LightSliceTestCaseMore(unittest.TestCase):
    def setUp(self):
        #logging.basicConfig(level=logging.INFO)
        self.ws = WS2812(1, 8)
        self.lights = lights = Lights(self.ws)

        # Fill the lattice with a recognizable pattern
        for i, p in enumerate(tg(len(lights), 0)):
            lat = lights.lattice[i]
            for j, c in enumerate(p):
                lat[j] = c

        self.sls = lights[-2:-6:-2]

    def tearDown(self):
        self.ws = self.lights = None
        gc.collect()

    
    ################################################################
    # And now for some questionable behavior

    def test_indexed_sliced_lval_fp(self):
        ws = self.ws
        lights = self.lights
        sls = self.sls

        # Can accept floating point, replacing the place in the lattice
        t = [1.0, 2.718, 3.14]
        sls[0] = t
        self.assertEqual(sls[0], [1.0, 2.718, 3.14])
        self.assertIs(sls[0], t)

        # That list we placed is accessable
        sls[0][1] = 1000
        self.assertEqual(sls[0], [1.0, 1000, 3.14])
        self.assertIs(sls[0], t)

    def test_indexed_sliced_lval_short(self):
        ws = self.ws
        lights = self.lights
        sls = self.sls
        sls_zero = sls[0]
        ref = sls[0][2]

        # A short one gets its items entered in
        sls[0] = (1,2)
        self.assertEqual(sls[0], bytearray([1, 2, ref]))
        self.assertIs(sls[0], sls_zero)

    def test_indexed_sliced_lval_long(self):
        ws = self.ws
        lights = self.lights
        sls = self.sls

        # A long one replaces
        t2 = (1,2,3,4)
        sls[0] = t2
        self.assertEqual(sls[0], (1,2,3,4)) # Note NOT a list, it's been replaced
        self.assertIs(sls[0], t2)

    def test_slice_sliced_lval_short(self):
        ws = self.ws
        lights = self.lights
        sls = self.sls

        # Assign a slice, short or equal element changes data
        t3 = (53, 59, 61)
        sls[:] = [(5,6,7,8), t3]
        self.assertEqual([v for v in sls], [(5,6,7,8), bytearray([53, 59, 61])])
        self.assertIsNot(sls[1], t3)
        
    def test_slice_sliced_lval_long(self):
        ws = self.ws
        lights = self.lights
        sls = self.sls

        # Assign a slice, long element replaces
        t4 = (53, 59, 61, 67)
        sls[:] = [(5,6,7,8), t4]
        self.assertEqual([v for v in sls], [(5,6,7,8), t4])
        self.assertIs(sls[1], t4)
        
    def test_slice_sliced_lval_mixed(self):
        ws = self.ws
        lights = self.lights
        sls = self.sls

        # Assign a slice
        sls[:] = [(5,6,7,8), tuple(1/v for v in range(9,13))]
        self.assertEqual(list(v for v in sls),
                         [(5,6,7,8), (1/9, 0.1, 1/11, 1/12)])

    @unittest.skip("FIXME")
    def test_slice_sliced_lval_complex(self):
        ws = self.ws
        lights = self.lights
        sls = self.sls

        # Assign a slice
        sls[:] = [(5,6,7,8), (1/v for v in range(9,13))]
        self.assertEqual(list(v for v in sls), (1,2,3,4)) # Note NOT a list, it's been replaced


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
        
