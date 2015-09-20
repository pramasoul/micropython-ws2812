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
    names = """PixelAccess Rotate RotateSubsection""".split()
    #names = """PixelAccess""".split()

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
                print("\tdoTest%s(mem==%d) ... " % (name, mem), end='')
                try:
                    gc.collect()
                    fun(mem)
                except:
                    print("Fail:", name, "with mem =", mem)
                    raise
                else:
                    print("ok")


    def doTestPixelAccess(self, mem):
        # A WSlice gives a view into the underlying WS2912
        ws = WS2812(spi_bus=1, led_count=99, mem=mem)
        ws.fill_buf(tg(len(ws), 0))
        
        # A simple slice has the correct length
        leds = WSlice(ws, 3, 6)
        #print("ws:", ws[:8], "...")
        #print("leds:", leds[:])
        self.assertEqual(len(leds), 3)

        # A simple slice has the correct values
        self.assertEqual([tuple(led) for led in leds],
                         [tuple(v) for v in tg(len(leds), 3*3)])

        # The end can be negative, with correct slice behavior
        leds = WSlice(ws, len(ws)-5, -2)
        self.assertEqual(len(leds), 3)
        self.assertEqual([tuple(led) for led in leds],
                         [tuple(v) for v in tg(len(leds), 3*(len(ws)-5))])

        # The start and end can be negative, with correct slice behavior
        leds = WSlice(ws, 3 - len(ws), 6 - len(ws))
        self.assertEqual(len(leds), 3)
        self.assertEqual([tuple(led) for led in leds],
                         [tuple(v) for v in tg(len(leds), 3*3)])

        # The start can be negative, with correct slice behavior
        leds = WSlice(ws, 3 - len(ws), 6)
        self.assertEqual(len(leds), 3)
        self.assertEqual([tuple(led) for led in leds],
                         [tuple(v) for v in tg(len(leds), 3*3)])

        # These are true for multiple test values
        for n in (1, 2, 7, 16, 33, 70):
            leds = WSlice(ws, n, n+5)
            self.assertEqual(len(leds), 5)
            self.assertTrue(all(v==r) for v, r in \
                            zip(tuple(led) for led in leds,
                                tuple(v) for v in tg(len(leds), 3*n)))

            leds = WSlice(ws, len(ws)-(n+5), -n)
            self.assertEqual(len(leds), 5)
            self.assertTrue(all(v==r) for v, r in \
                            zip(tuple(led) for led in leds,
                                tuple(v) for v in tg(len(leds), 3*(len(ws)-(n+5)))))

            leds = WSlice(ws, -(n+5), -n)
            self.assertEqual(len(leds), 5)
            self.assertTrue(all(v==r) for v, r in \
                            zip(tuple(led) for led in leds,
                                tuple(v) for v in tg(len(leds), 3*(len(ws)-(n+5)))))

            leds = WSlice(ws, -(n+5), len(ws)-n)
            self.assertEqual(len(leds), 5)
            self.assertTrue(all(v==r) for v, r in \
                            zip(tuple(led) for led in leds,
                                tuple(v) for v in tg(len(leds), 3*(len(ws)-(n+5)))))



    def doTestRotate(self, mem):
        # A WSlice can be rotated
        return
        ws = WS2812(spi_bus=1, led_count=75, mem=mem)
        for n in (1, 2, 7, 16, 33, 70):#, 190, 244, 400):
            leds = None
            t = None
            gc.collect()
            leds = WSlice(ws, 0, n)
            ws.fill_buf(tg(n, 0))
            ref = list(tuple(t) for t in tg(n, 0))
            self.assertEqual(list(tuple(v) for v in leds), ref)
            for k in range(n):
                leds.cw()
                self.assertTrue(all(tuple(leds[i]) == ref[(k+1+i)%n] for i in range(n)))
            for k in range(n):
                leds.ccw()
                self.assertTrue(all(tuple(leds[i]) == ref[(-(k+1)+i)%n] for i in range(n)))

                
    def doTestRotateSubsection(self, mem):
        # A chain can be rotated
        ws = WS2812(spi_bus=1, led_count=90, mem=mem)
        for n in (1, 2, 7, 16, 33, 70):#, 190, 244, 400):
            leds = None
            t = None
            gc.collect()
            leds = WSlice(ws, n//7, n + n//7)
            self.assertEqual(len(leds), n)
            for i, t in zip(range(n), tg(n,0)):
                leds[i] = t
            ref = list(tuple(leds[i]) for i in range(n))
            print("ref", ref)
            print("leds", leds[:])
            self.assertEqual(list(tuple(v) for v in leds), ref)
            for k in range(n):
                leds.cw()
                self.assertTrue(all(tuple(leds[i]) == ref[(k+1+i)%n] for i in range(n)))
            for k in range(n):
                leds.ccw()
                self.assertTrue(all(tuple(leds[i]) == ref[(-(k+1)+i)%n] for i in range(n)))

                
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
        
