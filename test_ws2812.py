# -*- coding: utf-8 -*-

import unittest
import logging

import pyb
import math

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
        self.assertEqual(list(v for v in leds), [bytearray(3)])

        # Individual leds can be accessed by indexing
        pix = leds[0]

        # Accessor provides a mutable indexable
        pix[0] = 255
        pix[1] = 255
        pix[2] = 255

        # leds can be mutated by indexing (only a pixel, not colors directly)
        leds[0] = pix
        self.assertEqual(list(v for v in leds), [bytearray((255,255,255))])
        self.assertEqual('|'.join('%x' % v for v in leds.buf),
                         '33|33|33|33|33|33|33|33|33|33|33|33|0')

        # The colors are in the right place, affecting the correct bits in the buffer
        pix[0] = 2
        pix[1] = 1
        pix[2] = 4
        leds[0] = pix
        self.assertEqual('|'.join('%x' % v for v in leds.buf),
                         '11|11|11|13|11|11|11|31|11|11|13|11|0')
        # variation
        pix[0] = 12
        pix[1] = 34
        pix[2] = 56
        leds[0] = pix
        self.assertEqual(list(v for v in leds), [bytearray((12, 34, 56))])
        self.assertEqual('|'.join('%x' % v for v in leds.buf),
                         '11|31|11|31|11|11|33|11|11|33|31|11|0')
        # variation
        pix[0] = -1
        pix[1] = 345
        pix[2] = 777777777
        leds[0] = pix
        self.assertEqual(list(v for v in leds), [bytearray((255, 89, 113))])
        self.assertEqual('|'.join('%x' % v for v in leds.buf),
                         '13|13|31|13|33|33|33|33|13|33|11|13|0')


    def testGrindSinglePixel(self):
        # get / set work as expected
        leds = WS2812(spi_bus=1, led_count=1, intensity=1)
        pix = bytearray(3)
        for i in range(1000):
            for j in range(3):
                pix[j] = pyb.rng()
            leds[0] = pix
            readback = leds[0]
            self.assertEqual(readback, pix)

    def testMultiPixel(self):
        # buf is the correct length
        for n in range(1, 400, 19):
            leds = WS2812(spi_bus=1, led_count=n)
            self.assertEqual(len(leds.buf), 12*n + 1)
            self.assertEqual(len(leds), n)
            zb = bytearray(3)
            for pix in leds:
                self.assertEqual(pix, zb)


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
        
