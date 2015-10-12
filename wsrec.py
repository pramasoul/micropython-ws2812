# -*- coding: utf-8 -*-

import pyb
from array import array
from uctypes import addressof, bytearray_at

import ws2812
from ws2812 import Pixel, PREALLOCATE, CACHE, RECREATE

class WS2812(ws2812.WS2812):
    def __init__(self, *args, **kwargs):
        ws2812.WS2812.__init__(self, *args, **kwargs)
        #print("owned")
        rec_fname = 'ws2812_recording_spi{}.binary'.format(self.spi.bus)
        print(rec_fname)
        self.spi.recording_file = open(rec_fname, 'wb')
