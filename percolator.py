#import pyb
#import gc
#from ws2812 import WS2812
#import random
from async_pyb import coroutine, sleep, GetRunningLoop, Sleep
from pyb import rng

class Percolator:
    def __init__(self, leds):
        # Assume 8x8, and 0-based, for now
        self.leds = leds
        self.leds_sync_last_done = 0
        self.leds_need_sync = False
        self.top_i = len(leds) - 1
        self.bottom_i = 0

    def add_color_to(self, i, color):
        led = self.leds[i]
        for i in range(len(led)):
            led[i] += color[i]

    def sub_color_from(self, i, color):
        led = self.leds[i]
        for i in range(len(led)):
            led[i] -= color[i]

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


    @coroutine
    def show_for(self, duration):
        self.leds_need_sync = True
        yield from sleep(duration)

    @coroutine
    def keep_leds_current(self, interval):
        last_check_time = 0
        loop = yield GetRunningLoop(None)
        while True:
            now = loop.time()
            if now < last_check_time + interval:
                yield Sleep(last_check_time + interval - now)
            last_check_time = loop.time()
            if self.leds_need_sync:
                self.leds.sync()
                self.leds_sync_last_done = loop.time()
                self.leds_need_sync = False

    @coroutine
    def perk(self, delay, color):
        prev_i = self.top_i
        i = None
        while True:
            if i is None:
                i = self.top_i
            self.add_color_to(i, color)
            if self.at_mid(i):
                yield from self.show_for(14*delay)
            else:
                yield from self.show_for(delay)
            prev_i = i
            i = self.down(i, rng()&1)
            self.sub_color_from(prev_i, color)
            if self.perk_quit:
                break
        self.perk_quit -= 1
