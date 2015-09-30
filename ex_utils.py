# -*- coding: utf-8 -*-
import random
import math
from async_pyb import coroutine, sleep, GetRunningLoop, Sleep
from pyb import Timer, rng, micros, elapsed_micros
import uctypes
from ws2812 import SubscriptableForPixel


"""
def cw(lattice):
    t = lattice[0]
    lattice[:-1] = lattice[1:]
    lattice[-1] = t

def ccw(lattice):
    t = lattice[-1]
    lattice[1:] = lattice[:-1]
    lattice[0] = t
"""

class Jewel7(Lights):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.center = self.lattice[self.indexed_range[0]]
        self.gear = Gear(leds=self.leds, timer=self.timer,
                         lattice=self.lattice,
                         indexed_range=self.indexed_range[1:])
        
    def model_colors(self):
        yield self.lattice[0]
        yield from self.gear.model_colors()


class Gear(Lights):
    # A gear has a pattern and a phase (in units of "teeth",
    # i.e. lattice points)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.phase = 0

    def cw(self, n=1):
        self.phase = (self.phase + n) % len(self)

    def ccw(self, n=1):
        self.phase = (self.phase - n) % len(self)

    def model_colors(self):
        start = round(self.phase) % len(self)
        leds = self.leds
        for i in self.indexed_range[start:]:
            yield leds[i]
        for c in self.indexed_range[:start]:
            yield leds[i]


