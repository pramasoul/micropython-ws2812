# -*- coding: utf-8 -*-

import unittest
#import logging

import pyb
import gc
import math
#import random
import uctypes

from ws2812 import WS2812, Pixel, PREALLOCATE, CACHE, RECREATE
from led_utils import WSlice, _fillwords, _movewords
from led_utils import Percolator

#log = logging.getLogger("test_ws2812")

def tg(led_count, start):

    def triple(n):
        for i in range(3):
            yield (n + i) & 0xff

    for i in range(led_count):
        yield triple(start + 3*i)


class VariousTestCase(unittest.TestCase):
    def setUp(self):
        #logging.basicConfig(level=logging.INFO)
        gc.collect()
        #random.seed("WSlice")

    def tearDown(self):
        pass
    
    def test_fillwords(self):
        b = bytearray(range(8*4))
        ref = b[:]
        self.assertEqual(b, ref)
        a = uctypes.addressof(b)
        self.assertEqual(a&3, 0) # word-aligned

        # A zero-length fill does nothing
        _fillwords(a+2*4, 0x12345678, 0)
        self.assertEqual(b, ref)

        # A negative-length fill does nothing
        _fillwords(a+2*4, 0x12345678, -1)
        self.assertEqual(b, ref)

        # Fills single word correctly
        ref = b[:]
        _fillwords(a+2*4, 0x79616b6f, 1)
        ref[4*2:4*(2+1)] = b'okay'
        self.assertEqual(b, ref)

        # Fills multiple words correctly
        b = bytearray(range(8*4))
        a = uctypes.addressof(b)
        ref = b[:]
        _fillwords(a+2*4, 0x79616b6f, 3)
        ref[4*2:4*(2+3)] = b'okay' * 3
        self.assertEqual(b, ref)


    def test_movewords(self):
        b = bytearray(range(8*4))
        ref = b[:]
        self.assertEqual(b, ref)
        a = uctypes.addressof(b)
        self.assertEqual(a&3, 0) # word-aligned

        # A zero-length move does nothing
        _movewords(a, a+3*4, 0)
        self.assertEqual(b, ref)

        # A negative-length move does nothing
        _movewords(a, a+3*4, -2)
        self.assertEqual(b, ref)

        # A move with dest=src does nothing
        _movewords(a+3*4, a+3*4, 0)
        self.assertEqual(b, ref)

        # A simple move down
        b = bytearray(range(8*4))
        a = uctypes.addressof(b)
        ref = b[:]
        ref[0*4:2*4] = b[3*4:5*4]
        _movewords(a, a+3*4, 2)
        self.assertEqual(list(b), list(ref))

        # A simple move up
        b = bytearray(range(8*4))
        a = uctypes.addressof(b)
        ref = b[:]
        ref[3*4:5*4] = b[0*4:2*4]
        _movewords(a+3*4, a, 2)
        self.assertEqual(list(b), list(ref))

        # An overlapping move down
        b = bytearray(range(8*4))
        a = uctypes.addressof(b)
        ref = b[:]
        ref[0*4:6*4] = b[2*4:8*4]
        _movewords(a, a+2*4, 6)
        self.assertEqual(list(b), list(ref))

        # An overlapping move up
        b = bytearray(range(8*4))
        a = uctypes.addressof(b)
        ref = b[:]
        ref[2*4:8*4] = b[0*4:6*4]
        _movewords(a+2*4, a, 6)
        self.assertEqual(list(b), list(ref))


class WSliceTestCase(unittest.TestCase):
    names = """Attrs PixelAccess Rotate RotateInset RotatePart""".split()
    names = """Attrs RotatePart""".split()

    def setUp(self):
        #logging.basicConfig(level=logging.INFO)
        gc.collect()
        #random.seed("WSlice")

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


    def doTestAttrs(self, mem):
        # A WSlice attributes have expected values
        ws = WS2812(spi_bus=1, led_count=7, mem=mem)
        ws.fill_buf(tg(len(ws), 0))
        leds = WSlice(ws, 2, 4)
        self.assertEqual(leds.buf, ws.buf[12*2:12*4])


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
        # A whole WSlice can be rotated
        ws = WS2812(spi_bus=1, led_count=75, mem=mem)
        for n in (1, 2, 7, 16, 33, 70):#, 190, 244, 400):
            leds = None
            t = None
            gc.collect()
            leds = WSlice(ws, 0, n)
            ws.fill_buf(tg(n, 0))
            ref = list(tuple(t) for t in tg(n, 0))
            self.assertTrue(all(tuple(leds[i]) == ref[i] for i in range(len(leds))))
            for k in range(n):
                leds.cw()
                self.assertTrue(all(tuple(leds[i]) == ref[(k+1+i)%n] for i in range(n)))
            for k in range(n):
                leds.ccw()
                self.assertTrue(all(tuple(leds[i]) == ref[(-(k+1)+i)%n] for i in range(n)))

                
    def doTestRotateInset(self, mem):
        # A WSlice that starts past the beginning of the underlying WS2812 can be rotated
        ws = WS2812(spi_bus=1, led_count=7, mem=mem)
        for i in range(len(ws)):
            ws[i] = b'foo'
        self.assertTrue(all(bytes(ws[i]) == b'foo' for i in range(len(ws))))
        leds = WSlice(ws, 2, 5)
        n = len(leds)
        for i, t in zip(range(n), tg(n,0)):
            leds[i] = t
        self.assertEqual([tuple(led) for led in leds], [(0,1,2), (3,4,5), (6,7,8)])
        self.assertTrue(all(bytes(ws[i]) == b'foo' for i in range(len(ws)) if i not in range(2,5)))
        leds.cw()
        self.assertEqual([tuple(led) for led in leds], [(3,4,5), (6,7,8), (0,1,2)])
        self.assertTrue(all(bytes(ws[i]) == b'foo' for i in range(len(ws)) if i not in range(2,5)))
        leds.cw()
        self.assertEqual([tuple(led) for led in leds], [(6,7,8), (0,1,2), (3,4,5)])
        self.assertTrue(all(bytes(ws[i]) == b'foo' for i in range(len(ws)) if i not in range(2,5)))
        leds.cw()
        self.assertEqual([tuple(led) for led in leds], [(0,1,2), (3,4,5), (6,7,8)])
        self.assertTrue(all(bytes(ws[i]) == b'foo' for i in range(len(ws)) if i not in range(2,5)))
        leds.ccw()
        self.assertEqual([tuple(led) for led in leds], [(6,7,8), (0,1,2), (3,4,5)])
        self.assertTrue(all(bytes(ws[i]) == b'foo' for i in range(len(ws)) if i not in range(2,5)))
        leds.ccw()
        self.assertEqual([tuple(led) for led in leds], [(3,4,5), (6,7,8), (0,1,2)])
        self.assertTrue(all(bytes(ws[i]) == b'foo' for i in range(len(ws)) if i not in range(2,5)))
        leds.ccw()
        self.assertEqual([tuple(led) for led in leds], [(0,1,2), (3,4,5), (6,7,8)])
        self.assertTrue(all(bytes(ws[i]) == b'foo' for i in range(len(ws)) if i not in range(2,5)))
        ws = WS2812(spi_bus=1, led_count=90, mem=mem)
        for n in (1, 2, 7, 16, 33, 70):#, 190, 244, 400):
            leds = ref = None
            gc.collect()
            leds_start = n//7
            leds_end = n + n//7
            leds = WSlice(ws, leds_start, leds_end)
            self.assertEqual(len(leds), n)
            for i, t in enumerate(tg(n,0)):
                leds[i] = t
            ref = list(tuple(leds[i]) for i in range(n))
            #print("\n\nstart %d, end %d" % (leds_start, leds_end))
            #print("ref", ref)
            #print("leds", leds[:])
            for k in range(n):
                #print("\nk", k, "leds", leds[:])
                #print("leds before cw:", [tuple(leds[i]) for i in range(n)])
                leds.cw()
                #print(" leds after cw:", [tuple(leds[i]) for i in range(n)])
                #print("ref:", [ref[(k+1+i)%n] for i in range(n)])
                self.assertTrue(all(tuple(leds[i]) == ref[(k+1+i)%n] for i in range(n)))
            for k in range(n):
                leds.ccw()
                self.assertTrue(all(tuple(leds[i]) == ref[(-(k+1)+i)%n] for i in range(n)))


    def doTestRotatePart(self, mem):
        # Some part of a WSlice that starts past the beginning of the
        # underlying WS2812 can be rotated
        ws = WS2812(spi_bus=1, led_count=8, mem=mem)
        for i in range(len(ws)):
            ws[i] = b'foo'
        self.assertTrue(all(bytes(ws[i]) == b'foo' for i in range(len(ws))))
        leds = WSlice(ws, 2, 6)
        n = len(leds)
        for i, t in zip(range(n), tg(n,0)):
            leds[i] = t
        self.assertTrue(all(bytes(ws[i]) == b'foo' for i in range(len(ws)) if i not in range(2,6)))
        self.assertEqual([tuple(led) for led in leds], [(0,1,2), (3,4,5), (6,7,8), (9,10,11)])
        leds.cw(1)
        self.assertTrue(all(bytes(ws[i]) == b'foo' for i in range(len(ws)) if i not in range(2,6)))
        self.assertEqual([tuple(led) for led in leds], [(0,1,2), (6,7,8), (9,10,11), (3,4,5)])
        leds.cw(1)
        self.assertTrue(all(bytes(ws[i]) == b'foo' for i in range(len(ws)) if i not in range(2,6)))
        self.assertEqual([tuple(led) for led in leds], [(0,1,2), (9,10,11), (3,4,5), (6,7,8)])
        leds.cw(1)
        self.assertTrue(all(bytes(ws[i]) == b'foo' for i in range(len(ws)) if i not in range(2,6)))
        self.assertEqual([tuple(led) for led in leds], [(0,1,2), (3,4,5), (6,7,8), (9,10,11)])
        leds.ccw(1)
        self.assertTrue(all(bytes(ws[i]) == b'foo' for i in range(len(ws)) if i not in range(2,6)))
        self.assertEqual([tuple(led) for led in leds], [(0,1,2), (9,10,11), (3,4,5), (6,7,8)])
        leds.ccw(1)
        self.assertTrue(all(bytes(ws[i]) == b'foo' for i in range(len(ws)) if i not in range(2,6)))
        self.assertEqual([tuple(led) for led in leds], [(0,1,2), (6,7,8), (9,10,11), (3,4,5)])
        leds.ccw(1)
        self.assertTrue(all(bytes(ws[i]) == b'foo' for i in range(len(ws)) if i not in range(2,6)))
        self.assertEqual([tuple(led) for led in leds], [(0,1,2), (3,4,5), (6,7,8), (9,10,11)])


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
        self.assertTrue(average_ms < 20, "average render time %f ms" % (average_ms))

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
        
