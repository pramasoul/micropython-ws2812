#import pyb
#import gc
#from ws2812 import WS2812
#import random


class Percolator:
    def __init__(self, leds):
        # Assume 8x8, and 0-based, for now
        self.leds = leds
        self.top_i = len(leds) - 1
        self.bottom_i = 0

    def down_left(self, i):
        # return the index into leds that is down-left of i
        if i // 8:
            return i-8
        else:
            return None

    def down_right(self, i):
        # return the index into leds that is down-right of i
        if i % 8:
            return i-1
        else:
            return None

    def steer_down(self, i, right):
        # Go down
        if right:
            rv = self.down_right(i)
        else:
            rv = self.down_left(i)
        return rv

    def down(self, i, right):
        rv = self.steer_down(i, right)
        if rv is None:
            rv = self.steer_down(i, not right)
        return rv

    def at_mid(self, i):
        return i//8 + i%8 == 7
