# -*- coding: utf-8 -*-

import unittest
#import logging

import pyb
import gc
import math

import random

from ws2812 import WS2812, Pixel, PREALLOCATE, CACHE, RECREATE
from led_utils import WSlice

#log = logging.getLogger("test_ws2812")

def tg(led_count, start):

    def triple(n):
        for i in range(3):
            yield (n + i) & 0xff

    for i in range(led_count):
        yield triple(start + 3*i)


class WSliceTestCase(unittest.TestCase):
    names = """Rotate""".split()

    def setUp(self):
        #logging.basicConfig(level=logging.INFO)
        gc.collect()
        random.seed("WSlice")

    def tearDown(self):
        pass

    #@unittest.skip("x")
    def testAllMemoryStrategies(self):
        print()
        for mem in (PREALLOCATE, CACHE, RECREATE):
            for name in self.names:
                fun = getattr(self, 'doTest'+name)
                print("\tdoTest%s(mem=%d) ... " % (name, mem), end='')
                try:
                    gc.collect()
                    fun(mem=mem)
                except:
                    print("Fail:", name, "with mem =", mem)
                    raise
                else:
                    print("ok")

    #@unittest.skip("x")
    def doTestRotate(self, mem):
        # A chain can be rotated
        for n in (1, 2, 7, 16, 33, 70):#, 190, 244, 400):
            leds = None
            t = None
            gc.collect()
            leds = WSlice(WS2812(spi_bus=1, led_count=n, mem=mem))
            leds.fill_buf(tg(n, 1))
            a = leds.ws.a
            t = a[:]       # Look inside and save the state
            for j in range(0, n, (n//7)+1):
                #gc.collect()
                #self.assertEqual(a, t)
                alen = len(a) - 1 # ignoring the pad
                for i in range(alen):
                    self.assertEqual(a[i], t[i])
                for cnt in range(j):
                    leds.cw()
                for i in range(alen):
                    self.assertEqual(a[i], t[(i+3*j)%alen])
                for cnt in range(j):
                    leds.ccw()

                
    @unittest.skip("FIXME: blows memory")
    def testRotatePlaces(self):
        # A chain can be rotated
        for n in range(1, 400, 19):
            leds = None
            gc.collect()
            leds = WS2812(spi_bus=1, led_count=n)
            leds.fill_buf(tg(n, 1))
            for j in range(0, n, (n//7)+1):
                gc.collect()
                for pix, pg in zip(leds, tg(n, 1)):
                    self.assertEqual(list(pix), list(pg))
                #pixlist = list(list(pix) for pix in leds)
                #rpixlist = pixlist[-j:] + pixlist[:-j]
                leds.rotate_places(j)
                gc.collect()
                #self.assertEqual(list(list(pix) for pix in leds), rpixlist)
                leds.rotate_places(-j)


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
        
