# -*- coding: utf-8 -*-
import random
import math
from async_pyb import coroutine, sleep, GetRunningLoop, Sleep
from pyb import Timer, rng, micros, elapsed_micros
from uctypes import addressof

class Lights:
    def __init__(self, leds, timer=None):
        self.leds = leds
        self.timer = timer
        self.leds_sync_last_done = 0
        self.leds_need_sync = False

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
        if any(a > b for a,b in zip(led, stoichiometric)):
            return bytes(max(a-b, 0) for a,b in zip(led, stoichiometric))
        if all(a == b for a,b in zip(led, stoichiometric)):
            #return stoichiometric
            if all(all(a == b for a,b in zip(leds[i], stoichiometric)) \
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


class RingRamp(Lights):
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
        return self.display_list_for(θ * self.pix_per_radian,
                                     color, blur)

    def display_list_for(self, x, color, blur=1.0):
        # In pixel circle coordinates
        rv = []
        for i, w in self.pixel_weights_for(x, blur):
            try:                # DEBUG
                sc = bytes(round(v*w) for v in color)
            except TypeError:
                print(repr(color))
                raise
            if sc:
                rv.append((i, sc))
        return rv

    def pixel_weights_for(self, x, blur=1.0):
        # In arbitrary pixel coordinates
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

    @coroutine
    def integrate_continuously(self, nap=10):
        #print("integrating continuously, napping %d" % nap)
        tscale = 1 / 1000000
        then = micros()
        should_be_less_than = (nap + 30) * 1000 
        while True:
            dt = elapsed_micros(then)
            #if dt >= should_be_less_than:
            #    print("integration dt was", dt)
            then = micros()
            self.integrate(dt * tscale)
            self.show_balls()
            yield from sleep(nap)
