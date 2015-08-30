# -*- coding: utf-8 -*-

import unittest
import logging

import pyb
import gc
import math

import random

from ws2812 import WS2812

log = logging.getLogger("test_ws2812")

def tg(led_count, start):

    def triple(n):
        for i in range(3):
            yield n +i

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

    def setUp(self):
        logging.basicConfig(level=logging.INFO)
        random.seed("ws2812")

    def tearDown(self):
        pass

    def testSinglePixel(self):
        # buf is the correct length
        leds = WS2812(spi_bus=1, led_count=1, intensity=1)
        self.assertEqual(len(leds.buf), 13)

        # As-created the pixels are all off
        # Off is represented correctly in the buffer
        self.assertEqual('|'.join('%x' % v for v in leds.buf),
                         '11|11|11|11|11|11|11|11|11|11|11|11|0')

        # leds can be accessed via iterator
        self.assertEqual(list(list(v) for v in leds), [[0]*3])

        # Individual leds can be accessed by indexing
        pix = leds[0]

        # pixels have r,g,b
        pix.r = 1
        pix.g = 2
        pix.b = 3
        self.assertEqual([pix.r, pix.g, pix.b], [1,2,3])

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
        self.assertEqual(list(leds[0]), [102, 111, 111])

        # All-ones is represented correctly in the buffer
        leds[0] = b'\xff\xff\xff'
        self.assertEqual(list(leds[0]), [255, 255, 255])
        self.assertEqual('|'.join('%x' % v for v in leds.buf),
                         '33|33|33|33|33|33|33|33|33|33|33|33|0')

        # The colors are in the right place, affecting the correct bits in the buffer
        pix[0] = 2
        pix[1] = 1
        pix[2] = 4
        self.assertEqual('|'.join('%x' % v for v in leds.buf),
                         '11|11|11|13|11|11|11|31|11|11|13|11|0')
        # variation
        pix[0] = 12
        pix[1] = 34
        pix[2] = 56
        self.assertEqual(list(leds[0]), [12, 34, 56])
        self.assertEqual('|'.join('%x' % v for v in leds.buf),
                         '11|31|11|31|11|11|33|11|11|33|31|11|0')
        # variation
        pix[0] = -1
        pix[1] = 345
        pix[2] = 777777777
        self.assertEqual(list(leds[0]), [255, 89, 113])
        self.assertEqual('|'.join('%x' % v for v in leds.buf),
                         '13|13|31|13|33|33|33|33|13|33|11|13|0')

    def testGrindSinglePixel(self):
        # get / set work as expected
        leds = WS2812(spi_bus=1, led_count=1, intensity=1)
        for i in range(1000):
            r = leds[0].r = random.getrandbits(8)
            g = leds[0].g = random.getrandbits(8)
            b = leds[0].b = random.getrandbits(8)
            self.assertEqual(list(leds[0]), [r, g, b])


    def testMultiPixel(self):
        # buf is the correct length
        # WS2812 can be iterated over to yield pixels
        # pixel values can be set and read back
        for n in range(1, 400, 19):
            leds = None
            gc.collect()
            leds = WS2812(spi_bus=1, led_count=n)
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
        
