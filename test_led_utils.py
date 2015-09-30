# -*- coding: utf-8 -*-

import unittest
#import logging

import pyb
import gc
import uctypes

from led_utils import _fillwords, _movewords

#log = logging.getLogger("test_ws2812")

# A helper
def tg(led_count, start):

    def triple(n):
        for i in range(3):
            yield (n + i) & 0xff

    for i in range(led_count):
        yield triple(start + 3*i)


class AsmTestCase(unittest.TestCase):
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
        
