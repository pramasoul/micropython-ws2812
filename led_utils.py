# -*- coding: utf-8 -*-
import random
import math
from async_pyb import coroutine, sleep, GetRunningLoop, Sleep
from pyb import Timer, rng, micros, elapsed_micros
import uctypes
from ws2812 import SubscriptableForPixel

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
        self.sync = ws.sync
        self.mem = ws.mem
        self.a = uctypes.addressof(ws.buf) + 3*4*start
        self.buf = uctypes.bytearray_at(self.a, 3*4*(end - start))

    def __len__(self):
        return len(self.pixels)

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
    def __init__(self, leds, timer=None):
        self.leds = leds
        self.timer = timer
        self.leds_sync_last_done = 0
        self.leds_need_sync = False

    def clear(self):
        _fillwords(self.a, 0x11111111, len(self.leds))

    def add_color_to(self, i, color):
        led = self.leds[i]
        for i in range(len(led)):
            led[i] += color[i]

    def sub_color_from(self, i, color):
        led = self.leds[i]
        for i in range(len(led)):
            led[i] -= color[i]

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
                self.leds.sync()
                self.leds_sync_last_done = loop.time()
                self.leds_need_sync = False


class Percolator(Lights):
    def __init__(self, leds):
        # Assume 8x8, and 0-based, for now
        super().__init__(leds)
        self.top_i = len(leds) - 1
        self.bottom_i = 0
        self.random = random.SystemRandom()
        self.perk_quit = False
        self.stoichiometric = (31,31,31)

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
    def perk(self, delay, color, start=None):
        #print("perk(%d, %r, %r)" % (delay, color, start))
        stoichiometric = self.stoichiometric
        i = None
        while True:
            if i is None:
                if start is None:
                    i = self.top_i
                else:
                    i = start
            self.add_color_to(i, color)
            yield from self.show_for(delay)
            if self.at_mid(i):
                new_color = yield from self.react_at(i)
                if new_color is None:
                    return
                else:
                    color = new_color
            prev_i = i
            i = self.down(i, rng()&1)
            self.sub_color_from(prev_i, color)
            self.leds_need_sync = True
            if i is None:
                return color
            if self.perk_quit:
                break
        self.perk_quit -= 1


    @coroutine
    def react_at(self, i):
        stoichiometric = self.stoichiometric
        leds = self.leds
        led = self.leds[i]
        if any(c > s for c,s in zip(led, stoichiometric)):
            return bytes(max(c-s, 0) for c,s in zip(led, stoichiometric))
        if all(c == s for c,s in zip(led, stoichiometric)):
            #return stoichiometric
            if all(all(c == s for c,s in zip(leds[i], stoichiometric)) \
                   for i in range(7, 63, 7)):
                print("bingo!")
                yield self.bingo()
            return None
        yield
        return None


    @coroutine
    def play(self):
        random = self.random
        self.play_on = True
        self.perk_quit = 0
        while self.play_on:
            delay = random.randrange(30,100)
            color = random.choice(((8,0,0), (0,8,0), (0,0,8)))
            yield self.perk(delay, color)
            yield from sleep(random.randrange(200, 300))


π = math.pi
two_pi = 2*π

class Ball:
    def __init__(self, θ=0.0, ω=0.0, Fd=0.01, color=(8,0,0)):
        self.theta = θ
        self.ω = ω
        self.Fd = Fd
        self.color = color
        self.last_shown = []
        self.zap = False
    
    @property
    def θ(self):
        assert -π <= self.theta < π
        return self.theta

    @θ.setter
    def θ(self, v):
        v %= two_pi
        if v >= π:
            v -= two_pi
        self.theta = v

    # DEBUG: find who sets our color to zero
    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, v):
        if sum(iter(v)) == 0:
            raise ValueError("blackball")
        self._color = v
    # end DEBUG

    def integrate(self, dt, a=0):
        ω = self.ω
        self.ω = ω + (a - self.Fd * ω * abs(ω)) * dt
        self.θ = (self.θ + (ω + self.ω) * 0.5 * dt) % two_pi # Trapezoidal integration

    def __repr__(self):
        s = "<Ball θ %f, ω %f, color %r" % \
            (self.θ, self.ω, self.color)
        try:
            s += ':' + repr(tuple(iter(self.color)))
        except TypeError:
            pass
        return s + '>'


# FIXME: does this have a purpose?
class Ring:
    def __init__(self, leds, start=0, length=None):
        self.leds = leds
        self.start = start
        if length is None:
            self.length = len(leds)
        else:
            self.length = length

    def cw(self):
        self.leds.cw(start=self.start, stop=self.start+self.length)

    def ccw(self):
        self.leds.ccw(start=self.start, stop=self.start+self.length)

    def clear(self):
        for i in range(self.start, self.start+self.length):
            self.leds[i].off()

    def one(self, rgb=(1,1,1), pos=0):
        self.leds[self.start + pos % self.length] = bytes(rgb)

    def __repr__(self):
        return("<ring start %d len %d leds %r>" % \
               (self.start, self.length, self.leds))


class RingRamp(Lights):
    # A ring-shaped ramp for balls in gravity
    # The balls ghost through each other
    # Coordinate systems:
    # 1) angle in radians
    # 2) pixels clockwise from the bottom pixel
    # 3) led index
    #
    # To suit the neopixel rings, we adopt θ = 0 at the bottom,
    # and clockwise as the direction of increasing θ

    def __init__(self, leds,
                 circumference=None,
                 bottom=0,
                 g=-1.0,
                 blur=None,
                 ball_check_fun=lambda b, θ, ω :[b]):
        super().__init__(leds)
        self.g = g
        self.bottom = bottom
        if circumference is not None:
            self.circumference = circumference
        else:
            self.circumference = led(leds)
        self.pix_per_radian = self.circumference / two_pi
        self.r = self.circumference / two_pi
        self.blur = blur
        self.balls = []
        self.ball_check_fun = ball_check_fun

    def integrate(self, dt):
        next_balls = []
        for ball in self.balls:
            θ = ball.θ
            ω = ball.ω
            ball.integrate(dt, a = self.g * math.sin(ball.θ) / self.r)
            t = self.ball_check_fun(ball, θ, ω )
            if t:
                try:
                    next_balls.extend(t)
                except MemoryError:
                    print('len(balls) =', len(self.balls), 'len(next_balls) =', len(next_balls))
                    raise
        self.balls = next_balls

    def show_balls(self):
        c = self.circumference
        survivors = []
        for ball in self.balls:
            self.change_leds(subtract=ball.last_shown)
            #print(ball, end='') # DEBUG
            #print("%2.2d" % i, ball, end='\r')      # DEBUG
            if not ball.zap:
                try:
                    survivors.append(ball)
                except MemoryError as e:
                    print("len(survivors) =", len(survivors))
                    for ball in survivors:
                        print(ball)
                    raise e
                # DEBUG:
                if sum(ball.color) == 0:
                    print("dark ball", ball)
                try:
                    ball.last_shown = \
                        self.display_list_for_angle(ball.θ, ball.color, self.blur)
                except Exception as e:
                    print(e)
                    print(ball)
                    raise
                self.change_leds(add=ball.last_shown)
        self.balls = survivors
        self.leds.sync()

    def change_leds(self, subtract=[], add=[]):
        # Input positions in pixel circle space
        # Rotates to LED space and clips to available arc
        c = self.circumference
        bottom = self.bottom
        led_len = len(self.leds)
        for i, color in subtract:
            k = (i + bottom) % c
            if k < led_len:
                self.sub_color_from(k, color)
        for i, color in add:
            k = (i + bottom) % c
            if k < led_len:
                self.add_color_to(k, color)

    def display_list_for_angle(self, θ, color, blur=1.0):
        return display_list_for(θ * self.pix_per_radian, color, blur)

    @coroutine
    def integrate_continuously(self, nap=10):
        #print("integrating continuously, napping %d" % nap)
        tscale = 1 / 1000000
        then = micros()
        #should_be_less_than = (nap + 30) * 1000
        while True:
            dt = elapsed_micros(then)
            #if dt >= should_be_less_than:
            #    print("integration dt was", dt)
            then = micros()
            self.integrate(dt * tscale)
            self.show_balls()
            yield from sleep(nap)



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
