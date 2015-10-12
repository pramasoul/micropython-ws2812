# -*- coding: utf-8 -*-
#import random
import math
#from async_pyb import coroutine, sleep, GetRunningLoop, Sleep
#from pyb import Timer, rng, micros, elapsed_micros


def display_list_for(x, color, blur=1.0):
    # In arbitrary pixel coordinates
    rv = []
    for i, w in gaussian_blur_weights(x, blur):
        try:                # DEBUG
            sc = bytes(round(v*w) for v in color)
        except TypeError:
            print(repr(color))
            raise
        if sc:
            rv.append((i, sc))
    return rv

def gaussian_blur_weights(x, blur=1.0):
    # In arbitrary pixel coordinates in a 1-D space
    # Provides an iterable of (i, weight)'s for a point source at float x
    # where the positions i are integers, sum(weights) is 1.0, and 
    # min(weight) about 1/255
    nearest_i = round(x)
    if not blur:
        return [(nearest_i, 1)]
    sharp = 1.0 / blur
    lattice_offset = nearest_i - x # Add to x to get to nearest lattice point
                    # Subtract from lattice point to get to x + some integer
    erfs = []
    i = nearest_i
    while True:
        e = math.erf(sharp * (i - nearest_i - 0.5 + lattice_offset))
        if e < -0.992:
            break
        erfs.insert(0, (i, e))
        i -= 1
    i = nearest_i + 1
    while True:
        e = math.erf(sharp * (i - nearest_i - 0.5 + lattice_offset))
        if e > 0.992:
            break
        erfs.append((i, e))
        i += 1
    rv = []
    if erfs:
        prior_e = -1.0
        for i, e in erfs:
            rv.append((i-1, 0.5 * (e - prior_e)))
            prior_e = e
        rv.append((i, 0.5 * (1.0 - e)))
    else:                   # Only one pixel with significant weight
        return [(nearest_i, 1)]
    return rv


