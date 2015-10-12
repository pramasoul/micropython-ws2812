# -*- coding: utf-8 -*-

import unittest
#import logging

import pyb
import gc
import math

import random
from sys import platform

from ws2812 import WS2812, Pixel, PREALLOCATE, CACHE, RECREATE

#log = logging.getLogger("test_ws2812")

def tg(led_count, start):

    def triple(n):
        for i in range(3):
            yield (n + i) & 0xff

    for i in range(led_count):
        yield triple(start + 3*i)


def count(r):
    c = 1
    for i in range(len(r)):
        rgb = r[i]
        #print("r[%d] = %r" % (i, rgb))
        for color in range(len(rgb)):
            t = rgb[color] + c
            rgb[color] = t & 1
            c = t >> 1
        r[i] = rgb
        #print("r[%d] now %r" % (i, rgb))

def v():
    return ', '.join('0x%x' % v for v in ring.a)

def vg():
    return ', '.join('0x%08x' % ring.get(i) for i in range(ring.led_count * 3))



class WS2812TestCase(unittest.TestCase):
    names = """SinglePixel PixelBufferBits GrindSinglePixel PixelAssignPixel
MultiPixel MultiPixelFedIterator SlicedRval SlicedLval""".split()
    #names = ['SlicedRval']  # DEBUG

    def setUp(self):
        #logging.basicConfig(level=logging.INFO)
        gc.collect()
        random.seed("WS2812")

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


    def doTestSinglePixel(self, mem):
        # buf is the correct length
        leds = WS2812(spi_bus=1, led_count=1, mem=mem)
        self.assertEqual(len(leds.buf), 13)

        # As-created the pixels are all off

        # leds can be accessed via iterator
        self.assertEqual(list(list(v) for v in leds), [[0]*3])

        # Individual leds can be accessed by indexing
        pix = leds[0]

        # pixels have r,g,b
        pix.r = 1
        pix.g = 2
        pix.b = 3
        self.assertEqual([pix.r, pix.g, pix.b], [1,2,3])
        self.assertEqual(list(pix), [1,2,3])

        # Can get a named tuple of values
        p = leds.get_led_values(0)
        self.assertEqual([p.r, p.g, p.b], [1,2,3])

        # pixels can also be indexed into for colors
        self.assertEqual(list(pix), [1,2,3])
        for i in range(len(pix)):
            pix[i] = 12 * (i + 1)
        self.assertEqual(list(pix), [12,24,36])

        # A pixel position in a chain can be mutated by setting it with a bytearray
        leds[0] = bytearray((7,11,92))
        self.assertEqual(list(leds[0]), [7, 11, 92])
        self.assertEqual([pix.r, pix.g, pix.b], [7, 11, 92])

        # A pixel position in a chain can be mutated by setting it with bytes
        leds[0] = b'foo'
        self.assertEqual([pix.r, pix.g, pix.b], [102, 111, 111])

        # A pixel position in a chain can be mutated by setting it with a list
        leds[0] = [11, 22, 33]
        self.assertEqual([pix.r, pix.g, pix.b], [11, 22, 33])

        # A pixel position in a chain can be mutated by setting it with an iterator
        leds[0] = (7*i + 3 for i in range(3))
        self.assertEqual([pix.r, pix.g, pix.b], [3, 10, 17])

        # The pixel.off() method works
        leds[0] = bytearray((7,11,92))
        leds[0].off()
        self.assertEqual(list(leds[0]), [0]*3)


    def doTestPixelBufferBits(self, mem):
        leds = WS2812(spi_bus=1, led_count=1, mem=mem)

        if platform == 'pyboard':
            plati = 0
        else:
            plati = 1

        # As-created the pixels are all off
        # Off is represented correctly in the buffer
        self.assertEqual('|'.join('%x' % v for v in leds.buf),
                         ('11|11|11|11|11|11|11|11|11|11|11|11|0',
                          '0|0|0|0|0|0|0|0|0|0|0|0|0')[plati])

        # All-ones is represented correctly in the buffer
        leds[0] = b'\xff\xff\xff'
        self.assertEqual(list(leds[0]), [255, 255, 255])
        self.assertEqual('|'.join('%x' % v for v in leds.buf),
                         ('33|33|33|33|33|33|33|33|33|33|33|33|0',
                          'ff|ff|ff|0|0|0|0|0|0|0|0|0|0')[plati])

        pix = leds[0]
        # The colors are in the right place, affecting the correct bits in the buffer
        pix[0] = 2
        pix[1] = 1
        pix[2] = 4
        self.assertEqual('|'.join('%x' % v for v in leds.buf),
                         ('11|11|11|13|11|11|11|31|11|11|13|11|0',
                          '1|2|4|0|0|0|0|0|0|0|0|0|0')[plati])
        # variation
        pix[0] = 12
        pix[1] = 34
        pix[2] = 56
        self.assertEqual(list(leds[0]), [12, 34, 56])
        self.assertEqual('|'.join('%x' % v for v in leds.buf),
                         ('11|31|11|31|11|11|33|11|11|33|31|11|0',
                          '22|c|38|0|0|0|0|0|0|0|0|0|0')[plati])
        # variation
        pix[0] = -1
        pix[1] = 345
        pix[2] = 777777777
        self.assertEqual(list(leds[0]), [255, 89, 113])
        self.assertEqual('|'.join('%x' % v for v in leds.buf),
                         ('13|13|31|13|33|33|33|33|13|33|11|13|0',
                          '59|ff|71|0|0|0|0|0|0|0|0|0|0')[plati])


    def testMemoryUsed0(self):
        leds = WS2812(spi_bus=1, led_count=64, mem=PREALLOCATE)
        prev_mem_free = gc.mem_free()
        for i in range(8):
            pass
        delta_mem = gc.mem_free() - prev_mem_free
        if platform == 'pyboard':
            self.assertEqual(delta_mem, 0)

    #@unittest.skip("FIXME")
    def testMemoryUsed1(self):
        leds = WS2812(spi_bus=1, led_count=64, mem=PREALLOCATE)
        prev_mem_free = gc.mem_free()
        for i in range(8):
            leds[0].g = i          # no leak
        delta_mem = gc.mem_free() - prev_mem_free
        if platform == 'pyboard':
            self.assertEqual(delta_mem, 0)

    #@unittest.skip("FIXME")
    def testMemoryUsed2(self):
        leds = WS2812(spi_bus=1, led_count=64, mem=PREALLOCATE)
        prev_mem_free = gc.mem_free()
        for i in range(8):
            leds[0] = b'\x08\x00\x00' # no leak
        delta_mem = gc.mem_free() - prev_mem_free
        if platform == 'pyboard':
            self.assertEqual(delta_mem, 0)

    #@unittest.skip("FIXME")
    def testMemoryUsed3(self):
        leds = WS2812(spi_bus=1, led_count=64, mem=PREALLOCATE)
        foo = b'foo'
        prev_mem_free = gc.mem_free()
        for i in range(8):
            leds[0] = foo           # no leak
        delta_mem = gc.mem_free() - prev_mem_free
        if platform == 'pyboard':
            self.assertEqual(delta_mem, 0)

    #@unittest.skip("FIXME")
    def testMemoryUsed4(self):
        leds = WS2812(spi_bus=1, led_count=64, mem=PREALLOCATE)
        bar = bytearray(range(3))
        prev_mem_free = gc.mem_free()
        for i in range(8):
            leds[0] = bar           # no leak
        delta_mem = gc.mem_free() - prev_mem_free
        if platform == 'pyboard':
            self.assertEqual(delta_mem, 0)

    #@unittest.skip("FIXME")
    def testMemoryUsed5(self):
        leds = WS2812(spi_bus=1, led_count=64, mem=PREALLOCATE)
        prev_mem_free = gc.mem_free()
        for i in range(8):
            p = leds[i]
        delta_mem = gc.mem_free() - prev_mem_free
        if platform == 'pyboard':
            self.assertEqual(delta_mem, 0)

    #@unittest.skip("FIXME")
    def testMemoryUsed6(self):
        leds = WS2812(spi_bus=1, led_count=64, mem=PREALLOCATE)
        prev_mem_free = gc.mem_free()
        for i in range(8):
            r = leds[i].r           # no leak
        delta_mem = gc.mem_free() - prev_mem_free
        if platform == 'pyboard':
            self.assertEqual(delta_mem, 0)

    @unittest.skip("Fails")
    def testMemoryUsed7(self):
        leds = WS2812(spi_bus=1, led_count=64, mem=PREALLOCATE)
        prev_mem_free = gc.mem_free()
        for i in range(8):
            r,g,b = leds[i]                         # -64 each
        delta_mem = gc.mem_free() - prev_mem_free
        if platform == 'pyboard':
            self.assertEqual(delta_mem, 0)

    #@unittest.skip("FIXME")
    def testMemoryUsed8(self):
        leds = WS2812(spi_bus=1, led_count=64, mem=PREALLOCATE)
        prev_mem_free = gc.mem_free()
        for i in range(8):
            r,g,b = leds[i].r, leds[i].g, leds[i].b # no leak
        delta_mem = gc.mem_free() - prev_mem_free
        if platform == 'pyboard':
            self.assertEqual(delta_mem, 0)

    #@unittest.skip("FIXME")
    def testMemoryUsed9(self):
        leds = WS2812(spi_bus=1, led_count=64, mem=PREALLOCATE)
        foo = b'foo'
        bar = bytearray(range(3))
        foolist = list(range(3))
        prev_mem_free = gc.mem_free()
        for i in range(8):
            t = leds[i][0]          # no leak
        delta_mem = gc.mem_free() - prev_mem_free
        if platform == 'pyboard':
            self.assertEqual(delta_mem, 0)

    #@unittest.skip("FIXME")
    def testMemoryUsed10(self):
        leds = WS2812(spi_bus=1, led_count=64, mem=PREALLOCATE)
        prev_mem_free = gc.mem_free()
        for i in range(8):
            for k in range(len(leds[i])): # no leak
                leds[i][k] = leds[i-1][k]
        delta_mem = gc.mem_free() - prev_mem_free
        if platform == 'pyboard':
            self.assertEqual(delta_mem, 0)

    #@unittest.skip("FIXME")
    def testMemoryUsed11(self):
        leds = WS2812(spi_bus=1, led_count=64, mem=PREALLOCATE)
        foolist = list(range(3))
        prev_mem_free = gc.mem_free()
        for i in range(8):
            leds[i] = foolist       # no leak
        delta_mem = gc.mem_free() - prev_mem_free
        if platform == 'pyboard':
            self.assertEqual(delta_mem, 0)

    def testSizes(self):
        gc.collect()
        m0 = gc.mem_free()
        leds = WS2812(spi_bus=1, led_count=256, mem=PREALLOCATE)
        gc.collect()
        m1 = gc.mem_free()
        print((m1-m0)/256)


    #@unittest.skip("x")
    def doTestGrindSinglePixel(self, mem):
        # get / set work as expected
        leds = WS2812(spi_bus=1, led_count=1, intensity=1, mem=mem)
        for i in range(1000):
            r = leds[0].r = random.getrandbits(8)
            g = leds[0].g = random.getrandbits(8)
            b = leds[0].b = random.getrandbits(8)
            self.assertEqual(list(leds[0]), [r, g, b])


    def doTestPixelAssignPixel(self, mem):
        # A pixel can be assigned to another pixel
        leds = WS2812(spi_bus=1, led_count=3, mem=mem)
        for i in range(len(leds)):
            leds[i] = (i, 2*i, 3*i)
        self.assertEqual(list(leds[0]), [0, 0, 0])
        self.assertEqual(list(leds[1]), [1, 2, 3])
        self.assertEqual(list(leds[2]), [2, 4, 6])
        leds[0] = leds[2]
        leds[2] = leds[1]
        leds[1] = [19, 23, 29]
        self.assertEqual(list(leds[0]), [2, 4, 6])
        self.assertEqual(list(leds[1]), [19, 23, 29])
        self.assertEqual(list(leds[2]), [1, 2, 3])
        self.assertIsNot(leds[0], leds[1])
        self.assertIsNot(leds[0], leds[2])
        self.assertIsNot(leds[1], leds[2])


    #@unittest.skip("x")
    def doTestMultiPixel(self, mem):
        # buf is the correct length
        # WS2812 can be iterated over to yield pixels
        # pixel values can be set and read back
        for n in range(1, 400, 19):
            leds = None
            gc.collect()
            leds = WS2812(spi_bus=1, led_count=n, mem=mem)
            self.assertEqual(len(leds), n)
            self.assertEqual(len(leds.buf), 12*n + 1)

            random.seed(n)
            for pix in leds:
                self.assertEqual(list(pix), [0]*3)
                for j in range(len(pix)):
                    pix[j] = random.getrandbits(8)

            pb = [0] * 3
            random.seed(n)
            for pix in leds:
                for j in range(len(pix)):
                    pb[j] = random.getrandbits(8)
                self.assertEqual(list(pix), pb)

    #@unittest.skip("x")
    def doTestMultiPixelFedIterator(self, mem):
        # A chain can be fed from an iterator
        for n in range(1, 200, 19):
            leds = None
            gc.collect()
            leds = WS2812(spi_bus=1, led_count=n, mem=mem)
            leds.fill_buf(tg(n, 1))
            for pix, pg in zip(leds, tg(n, 1)):
                self.assertEqual(list(pix), list(pg))


    def doTestSlicedRval(self, mem):
        # A chain slice can be read
        leds = WS2812(spi_bus=1, led_count=9, mem=mem)
        self.assertTrue(all(isinstance(v, Pixel) for v in leds[:3]))
        self.assertTrue(all(isinstance(v, Pixel) for v in leds[2:5]))
        self.assertTrue(all(isinstance(v, Pixel) for v in leds[7:11]))
        for i in range(len(leds)):
            leds[i] = (i, 2*i, 3*i)
        for k, led in enumerate(leds[3:6]):
            i = k + 3
            self.assertEqual(tuple(led), (i, 2*i, 3*i))
        self.assertEqual(list(tuple(led) for led in leds[-2:]), \
                         [(i, 2*i, 3*i) for i in (7,8)])
        self.assertEqual(list(tuple(led) for led in leds[:]), \
                         [(i, 2*i, 3*i) for i in range(len(leds))])

        # Negative index can be used
        i = len(leds) - 1
        self.assertEqual(tuple(leds[-1]), (i, 2*i, 3*i))
        i = len(leds) - 5
        self.assertEqual(tuple(leds[-5]), (i, 2*i, 3*i))
        i = 0
        self.assertEqual(tuple(leds[-len(leds)]), (i, 2*i, 3*i))

        # Negative index doesn't blow up unallocated
        leds = WS2812(spi_bus=1, led_count=66, mem=mem)
        sum_neg = sum(sum([leds[i].r, leds[i].g, leds[i].b]) for i in range(-1, -len(leds), -1))
        sum_pos = sum(sum([leds[i].r, leds[i].g, leds[i].b]) for i in range(len(leds)))
        self.assertEqual(sum_neg, 0)
        self.assertEqual(sum_pos, 0)


    #@unittest.skip("FIXME")
    def doTestSlicedLval(self, mem):
        # A chain slice can be written
        leds = WS2812(spi_bus=1, led_count=9, mem=mem)
        for i in range(len(leds)):
            leds[i] = (i, 2*i, 3*i)
        leds[0:3] = leds[3:6]
        for k in range(3):
            i = k + 3
            self.assertEqual(tuple(leds[k]), (i, 2*i, 3*i))
        for i in range(len(leds)):
            leds[i] = (i, 2*i, 3*i)
        leds[-3:] = leds[:3]
        for i in range(3):
            k = i + 6
            self.assertEqual(tuple(leds[k]), (i, 2*i, 3*i))



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
        
