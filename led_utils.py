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
#        self.leds = leds
        #if timer is None:
        #    self.timer = Timer(6)
#        self.leds_sync_last_done = 0
#        self.leds_need_sync = False
        self.top_i = len(leds) - 1
        self.bottom_i = 0
        self.random = random.SystemRandom()

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
        #prev_i = self.top_i
        stoichiometric = (8,8,8)
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
        stoichiometric = (8,8,8)
        led = self.leds[i]
        if all(a >= b for a,b in zip(led, stoichiometric)):
            return stoichiometric
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

class Ball:
    def __init__(self):
        self.θ = 3.0
        self.ω = 0.0
        self.color = bytearray((8,0,0))
        self.last_shown_at_i = None
    
    def integrate(self, dt, a=0):
        self.ω = self.ω + a * dt
        self.θ = (self.θ + self.ω * dt) % (2*π)

    def __repr__(self):
        return "<Ball θ %f, ω %f, color %r>" % \
            (self.θ, self.ω, tuple(iter(self.color)))
        


class RingRamp(Lights):
    def __init__(self, leds, timer=None):
        super().__init__(leds, timer)
        self.g = -10.0
        self.bottom = 7
        self.arc = range(-self.bottom, len(leds)-self.bottom)
        print("arc", self.arc)  # DEBUG
        self.circumference = 60
        self.r = self.circumference / (2*π)
        self.balls = []

    def integrate(self, dt):
        # To suit the neopixel rings, we adopt θ = 0 at the bottom,
        # and clockwise as the direction of increasing θ
        for ball in self.balls:
            ball.integrate(dt, a = self.g * math.sin(ball.θ) / self.r)


    def show_balls(self):
        c = self.circumference
        pix_per_radian = c / (2*π)
        bottom = self.bottom
        arc_len = len(self.leds)
        # Cheap
#        for led in self.leds:
#            led.off()
        for ball in self.balls:
            if ball.last_shown_at_i is not None:
                self.sub_color_from(ball.last_shown_at_i, ball.color)
            # cheap for now
            #print(ball, end='') # DEBUG
            i = round(ball.θ * pix_per_radian + bottom) % c 
            assert i >= 0
            print("%2.2d" % i, ball, end='\r')      # DEBUG
            if i < arc_len:           # Show only pixels on our arc
                #yield from self.supertitle("%r at %d" % (ball, i)) # DEBUG
                #print("at", i) # DEBUG
                self.add_color_to(i, ball.color)
                ball.last_shown_at_i = i
            else:
                ball.last_shown_at_i = None
        self.leds.sync()

    @coroutine
    def integrate_continuously(self, nap=10):
        #print("integrating continuously, napping %d" % nap)
        tscale = 1 / 1000000
        then = micros()
        while True:
            dt = elapsed_micros(then)
            then = micros()
            self.integrate(dt * tscale)
            self.show_balls()
            yield from sleep(nap)
