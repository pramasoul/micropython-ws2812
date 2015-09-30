# -*- coding: utf-8 -*-
#import random
#import math
from async_pyb import coroutine, sleep, GetRunningLoop, Sleep
from pyb import Timer, rng, micros, elapsed_micros
import uctypes
from ws2812 import SubscriptableForPixel

"""
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
"""


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


class WSlice(SubscriptableForPixel):
    # This class encapsulates a WS2812 and provides new capabilities
    # It intrudes into and depends on the internals of the pramasoul
    # version of WS2812
    def __init__(self, ws, start=0, end=None):
        self.ws = ws
        if  start < -len(ws) or start >= len(ws):
            raise IndexError("start %d is outside underlying ws of length %d" % (start, len(ws)))
        start %= len(ws)
        self.start = start
        if end is None:
            self.end = len(ws)
        else:
            self.end = end
        self.pixels = ws[start:end]
        self.sync = ws.sync     # risky
        self.mem = ws.mem
        self.a = uctypes.addressof(ws.buf) + 3*4*start
        self.buf = uctypes.bytearray_at(self.a, 3*4*(end - start))

    def __len__(self):
        return len(self.pixels)

    def update_buf(self, data, where=0):
        self.ws.update_buf(data, where=where+self.start)

    # Too fancy, creates memory stress:
    """
    def rotate_places(self, places):
        length = len(self)
        if places % length == 0: # Optimization, it works without
            return
        unqueued = set(range(length))
        bb = self.ws.buf
        queue = []
        #print(list(tuple(pix) for pix in self))
        while unqueued or queue:
            if queue:
                dst, contents = queue.pop()
            else:
                src = unqueued.pop()
                #print(src, end='')
                dst = (src + places) % length
                contents = bb[12*src:12*(src+1)]
            if dst in unqueued:
                queue.insert(0, ((dst + places) % length, \
                                 bytes(bb[12*dst:12*(dst+1)])))
                unqueued.remove(dst)
            #print('->', dst, end=' ')
            bb[12*dst:12*(dst+1)] = contents
            #print(list(tuple(pix) for pix in self))
    """

    
    def cw(self, start=0, stop=None):
        # Rotates [start, stop) one pixel clockwise
        # i.e. toward the lower index
        length = len(self)
        if stop is None or stop > length:
            stop = length
        if stop <= start + 1:   # Trivial rotation
            return
        a = uctypes.addressof(self.buf)
        tbuf = bytearray(12)
        b = uctypes.addressof(tbuf)
        _movewords(b, a+12*start, 3) # stash 3 words that will get overwritten
        _movewords(a+12*start, a+12*(start+1), 3*(stop-start-1)) # move all but the last word down
        _movewords(a+12*(stop-1), b, 3) # unstash

    def ccw(self, start=0, stop=None):
        # Rotates [start, stop) one pixel counter-clockwise
        # i.e. toward the higher index
        length = len(self)
        if stop is None or stop > length:
            stop = length
        if stop <= start + 1:   # Trivial rotation
            return
        a = uctypes.addressof(self.buf)
        tbuf = bytearray(12)
        b = uctypes.addressof(tbuf)
        _movewords(b, a+12*(stop-1), 3) # stash 3 words that will get overwritten
        _movewords(a+12*(start+1), a+12*start, 3*(stop-start-1)) # move all but the last word down
        _movewords(a+12*(start), b, 3) # unstash

    def shift(self, amount=1, start=0, stop=None):
        # Shifts leds[start:end] by amount to the right
        # amount can be negative, making it a left shift
        length = len(self)
        if stop is None or stop > length:
            stop = length
        if amount < 0:
            src = start - amount
            dest = start
            n = max(stop - start + amount, 0)
        else:
            src = start
            dest = start + amount
            n = max(stop - start - amount, 0)
        a = uctypes.addressof(self.buf)
        _movewords(a+12*dest, a+12*src, 3*n)


class Lights:
    # Lights encapsulated a WS2812 or WSlice, and provides a "lattice"
    # model of the pixels and a default rendering of them to the leds
    def __init__(self, leds=None, timer=None, lattice=None, indexed_range=None):
        self.leds = leds
        self.timer = timer
        if leds is None:
            pass                # FIXME
        self.lattice = lattice or [bytearray(3) for i in range(len(leds))]
        if indexed_range is None:
            indexed_range = range(len(leds))
        self.indexed_range = indexed_range
        self.leds_sync_last_done = 0
        self.leds_need_sync = False
        self.brightness = 1.0

    def __len__(self):
        return len(self.indexed_range)

    def clear(self):
        for p in self.lattice:
            p[0] = p[1] = p[2] = 0

    def add_color_to(self, i, color):
        p = self.lattice[i]
        for i in range(3):
            p[i] += color[i]

    def sub_color_from(self, i, color):
        p = self.lattice[i]
        for i in range(3):
            p[i] -= color[i]

    def set_color_of(self, i, color):
        p = self.lattice[i]
        for i in range(3):
            p[i] = color[i]

    def model_colors(self):
        for i in self.indexed_range:
            yield self.lattice[i]

    def gen_RGBs(self):
        br = round(self.brightness * 256)
        #buf = [0, 0, 0] # 18.86ms
        buf = bytearray(range(3)) # 16.93ms
        for p in self.model_colors():
            # The pythonic way (below) is too expensive:
            #yield (min(int((br*v + 128) / 256), 255) for v in p) # 33.45ms
            #yield list(min(int((br*v + 128) / 256), 255) for v in p) # 22.83ms
            r, g, b = p
            buf[0] = min(int((br*r + 128) / 256), 255)
            buf[1] = min(int((br*g + 128) / 256), 255)
            buf[2] = min(int((br*b + 128) / 256), 255)
            yield buf

    def render(self):
        leds = self.leds
        for i, c in zip(self.indexed_range, self.gen_RGBs()):
            leds[i] = c

    @coroutine
    def show_for(self, duration):
        self.leds_need_sync = True
        yield from sleep(duration)

    @coroutine
    def timer_keep_leds_current(self, interval=10):
        # Using a timer to sync the leds seems clever, but one might
        # be half-way through a non-atomic update of color when the
        # timer interrupt hits, so this is often not the best way to
        # do the job
        timer = self.timer
        if timer is None:
            return
        leds = self.leds
        timer.callback(None)
        timer.init(freq=round(1000/interval))
        timer.callback(lambda t: leds.sync())
        yield

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
                #self.leds.sync()
                self.render()
                self.leds.sync()
                self.leds_sync_last_done = loop.time()
                self.leds_need_sync = False

    def __getitem__(self, ix):
        if isinstance(ix, int):
            return self.lattice[self.indexed_range[ix]]
        else:
            ixs = self.indexed_range[ix]
        return Lights(leds=self.leds, lattice=self.lattice, indexed_range=ixs)

    def __setitem__(self, ix, val):
        if isinstance(ix, int):
            p = self.lattice[self.indexed_range[ix]]
            for i in range(3):
                p[i] = val[i]
        else:
            for i, v in zip(self.indexed_range[ix], val):
                p = self.lattice[i]
                for i in range(3):
                    p[i] = v[i]

    def __repr__(self):
        return "<Lights {} with {}>".format(self.leds, self.indexed_range)



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

@micropython.asm_thumb
def _fillwords(r0, r1, r2):
    # _fillwords(address, word, n), returns first word address past fill
    # Registers:
    # r0: address of start of block of words to fill
    # r1: value to fill with
    # r2: number of 32-bit words to fill
    # Note this could be improved by using the full Thumb instruction set. See:
    # http://docs.micropython.org/en/latest/reference/asm_thumb2_hints_tips.html#use-of-unsupported-instructions
    mov(r4, 4)
    label(loop)
    cmp(r2, 0)
    ble(done)
    str(r1, [r0, 0])
    add(r0, 4)
    sub(r2, 1)
    b(loop)
    label(done)

@micropython.asm_thumb
def _movewords(r0, r1, r2):
    # styled after memmove(dest, src, n), but moving words instead of bytes
    # Registers:
    # r0: destination address
    # r1: source address
    # r2: number of 32-bit words to move
    # r3: temporary
    # r4: step
    # Note this could be improved by using the full Thumb instruction set. See:
    # http://docs.micropython.org/en/latest/reference/asm_thumb2_hints_tips.html#use-of-unsupported-instructions
    cmp(r2, 0)                  # if n <= 0:
    ble(done)                   #  return
    mov(r4, 4)                  # words are 4 bytes
    cmp(r1, r0)                 # src - dest
    beq(done)                   # src == dest: return
    bhi(loop)                   # src > dest: move'em

    # Here the source is a lower address than the destination. To
    # protect against overwriting the data during the move, we move it
    # starting at the end (high) address
    neg(r4, r4)                 # -4
    add(r3, r2, r2)             # 2 * n
    add(r3, r3, r3)             # 4 * n
    add(r3, r3, r4)             # 4 * (n - 1)
    add(r0, r0, r3)             # r0 is dest[-1]
    add(r1, r1, r3)             # r1 is src[-1]

    # The moving itself
    label(loop)
    ldr(r3, [r1, 0])
    str(r3, [r0, 0])
    add(r0, r0, r4)
    add(r1, r1, r4)
    sub(r2, 1)
    bgt(loop)

    label(done)
