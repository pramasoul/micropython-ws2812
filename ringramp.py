import math
import pyb

from async_pyb import coroutine, sleep
from lights import Lights
from led_utils import display_list_for

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
    # A ring-shaped ramp for balls in gravity
    # The balls ghost through each other
    # Coordinate systems:
    # 1) angle in radians
    # 2) pixels clockwise from the bottom pixel
    # 3) led index
    #
    # To suit the neopixel rings, we adopt θ = 0 at the bottom,
    # and clockwise as the direction of increasing θ
    def __init__(self, circumference=None,
                 bottom=0,
                 g=-1.0,
                 blur=None,
                 ball_check_fun=lambda b, θ, ω :[b],
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
#        super().__init__(lights)
        self.g = g
        self.bottom = bottom
        if circumference is not None:
            self.circumference = circumference
        else:
            self.circumference = len(self)
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

    def gen_RGBs(self):
        c = self.circumference
        bottom = self.bottom
        lattice_len = len(self.lattice)
        for p in self.lattice:
            p[0] = p[1] = p[2] = 0

        for ball in self.balls:
            # DEBUG:
            if sum(ball.color) == 0:
                print("dark ball", ball)

            for i, color in self.display_list_for_angle(ball.θ, ball.color, self.blur):
                # Input positions in pixel circle space
                # Rotates to LED space and clips to available arc
                k = (i + bottom) % c
                if k < lattice_len:
                    self.add_color_to(k, color)

        b = round(self.brightness * 256)
        for p in self.lattice:
            yield (min((b*v + 128) >> 8, 255) for v in p)

    def show_balls(self):
        self.render()
        self.leds.sync()

    def was_show_balls(self):
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

    def change_lights(self, subtract=[], add=[]):
        # Input positions in pixel circle space
        # Rotates to LED space and clips to available arc
        c = self.circumference
        bottom = self.bottom
        led_len = len(self.lights)
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
        then = pyb.micros()
        #should_be_less_than = (nap + 30) * 1000
        while True:
            dt = pyb.elapsed_micros(then)
            #if dt >= should_be_less_than:
            #    print("integration dt was", dt)
            then = pyb.micros()
            self.integrate(dt * tscale)
            self.show_balls()
            yield from sleep(nap)
