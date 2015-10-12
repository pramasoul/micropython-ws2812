# -*- coding: utf-8 -*-
# Experimentation

#from ws2812 import WS2812
from lights import Lights
from percolator import Percolator
from ringramp import RingRamp, Ball
from jewel7 import Jewel7

import logging

from async_pyb import new_event_loop, set_event_loop, get_event_loop, \
    EventLoop, GetRunningLoop, Sleep, Future, TimeoutError, \
    coroutine, sleep, wait_for

from coro_cli import CoroCLI, inject_standard_commands

import pyb
from pyb import SPI, Pin, info, millis, elapsed_millis, \
    micros, elapsed_micros, rng, Timer

import random
import math
π = math.pi

rand = random.SystemRandom()
log = logging.getLogger("test")

class Lightshow:
    def __init__(self, write_fun=None, config={}):
        self.config = config

        if write_fun is None:
            @coroutine
            def write(self, *args):
                print(*args)
            self.write = write
        else:
            self.write = write_fun

        self.act_led = pyb.LED(3)
        self.err_led = pyb.LED(1)
        self.pkt_led = pyb.LED(2)

        self.pots = [0] * 4

        self.percolator = \
                Percolator(WS2812(spi_bus=config['leds'].get('spi'),
                                  led_count=config['leds'].get('qty')))
        self.percolator.bingo = self.bingo

        self.ws_rings = WS2812(2, 2*7 + 45)
        self.ring_lights = Lights(self.ws_rings)

        self.feed_rollers = [Jewel7(lights=self.ring_lights[0:7]),
                             Jewel7(lights=self.ring_lights[7:14])]

        self.rr = RingRamp(lights=self.ring_lights[14:],
                           circumference=60, \
                           bottom=7, \
                           g=-40.0,
                           ball_check_fun = self.ball_check)

#        self.zap_balls = False
        self.set_brightness(31)
        
    def set_brightness(self, v):
        self.brightness = self.rr.brightness = self.percolator.brightness = v
        self.feed_rollers[0].brightness = self.feed_rollers[1].brightness = v
        
    @coroutine
    def flash_LED(self, led, dur=1):
        led.on()
        yield from sleep(dur)
        led.off()

    @coroutine
    def fuzzle(self, quit_name):
        # For testing
        while not getattr(self, quit_name):
            #yield from self.flash_LED(self.err_led)
            # More queue-costly but let's us proceed without waiting for photons
            yield self.flash_LED(self.err_led) # let a coro do it so we can proceed
            yield from sleep(100)
        assert getattr(self, quit_name)
        setattr(self, quit_name, max(getattr(self, quit_name) - 1, 0))
        

    @coroutine
    def handle_pots(self, b):
        for i in range(4):
            self.pots[i] = big_endian_int(b[2*i:2*(i+1)])
        yield from self.show_pots()
        
    @coroutine
    def show_pots(self):
        s = ', '.join("%d" % v for v in self.pots)
        yield from self.supertitle("Pots: " + s)


    @coroutine
    def supertitle(self, text):
        yield from self.write(b'\x1b[s\x1b[1;1H\x1b[2K')
        yield from self.write(text)
        yield from self.write('\x1b[u')


    @coroutine
    def perk(self, cli, cmd, rol):
        sdelay, _, scolor = str(rol, 'ASCII').partition(' ')
        try:
            delay = int(sdelay)
        except:
            delay = 100
        try:
            color = eval(scolor)
        except:
            color = bytes((8,0,0))
        if not hasattr(self.percolator, 'perk_quit'):
            self.percolator.perk_quit = 0
        yield self.percolator.perk(delay, color) # Launch this and return


    def ball_check(self, ball, θ, ω ):
        # Checks a Ball and possibly affects it
        # Return a list of balls to replace it
        # (e.g. just [ball] to make no changes)
        rv = []
#        if self.zap_balls:
#            ball.zap = True
#            rv.append(ball)
#        if θ > π:
#            θ -= 2 * π

#        elif θ <= -2.408554 <= ball.θ: # and ball.ω >= 0:
        if θ <= -2.408554 <= ball.θ: # and ball.ω >= 0:
            # crossed off the top of the "C"
#            ball.zap = True
#            rv.append(ball)
            #print("θ=%f, ω=%f" % (θ, ω ))
            #print("zapped %r" % ball)
            self.loop.call_soon(self.perk_and_roll(100, ball.color))

        #elif θ < 0.0 < ball.θ: # and ball.ω >= 0:
        #elif θ < 0.0 < ball.θ or θ > 0.0 > ball.θ : # and ball.ω >= 0:
        elif θ < 0.0 < ball.θ or \
                θ > 0.0 > ball.θ and max(abs(θ), abs(ball.θ)) < 1.5: # and ball.ω >= 0:
            # Crossed the centerline of the drive rollers
            #print("rollered %r" % ball)
            #ball.ω = max(ball.ω , 2.08)
#            # Can't omit this ball, have to zap it for correct rendering
#            ball.zap = True
#            rv.append(ball)

            # Grind this ball up into primary colors
            color = list(iter(ball.color))
            #Below does not grind up fused primaries of same color:
            #colors = list(v for v in [(color[0], 0, 0),
            #                          (0, color[1], 0),
            #                          (0, 0, color[2])]
            #              if sum(v))

            t = stoichiometric = self.percolator.stoichiometric
            stoi_primaries = [(t[0], 0, 0),
                             (0, t[1], 0),
                             (0, 0, t[2])]
            colors = []
            for i in range(3):
                while color[i] >= stoichiometric[i]:
                    colors.append(stoi_primaries[i])
                    color[i] -= stoichiometric[i]
                if color[i]:
                    t = [0, 0, 0]
                    t[i] = color[i]
                    colors.append(tuple(t))

            assert colors, colors # At least one
            for c in colors:
                rv.append(Ball(θ=0.1, ω =rand.gauss(4.5, 0.2), color=c))
            #print(rv)
        else:
            rv.append(ball)
        return rv

    @coroutine
    def perk_and_roll(self, speed, color, i=None):
        out_color = yield from self.percolator.perk(speed, color, i)
        if out_color is not None:
            ball = Ball(θ = 2*π * -7/60,
                        ω = 0.3,
                        color=out_color)
            self.rr.balls.append(ball)
        #else:
        #    print("perk yielded a None")

    @coroutine
    def bingo(self):
        stars = list(range(7, 63, 7))
        p = self.percolator
        lattice = p.lattice
        rand.shuffle(stars)
        for i in stars:
            yield from sleep(200)
            color = tuple(lattice[i])
            p.set_color_of(i, (0,0,0))
            i = self.percolator.down(i, rng()&1)
            yield self.perk_and_roll(100, color, i)

    @coroutine
    def spin_feed_rollers(self):
        lower, upper = self.feed_rollers
        lower.center[2] = upper.center[2] = 1
        v = 1.0
        for i in range(len(lower.gear)):
            lower.gear[i] = [v, 0, 0]
            upper.gear[(3-i)%len(lower.gear)] = [0, v, 0]
            v *= 0.3
        while True:
            #time = self.loop.time
            #then = time()
            lower.gear.cw()
            upper.gear.ccw()
            lower.render()
            upper.render()
            #now = time()
            #t = 20 - (now - then)
            #then = now
            #yield from sleep(t)
            yield from sleep(20)

    @coroutine
    def manage_brightness(self):
        a = pyb.ADC(pyb.Pin('Y12'))
        amb = a.read()/4096
        while True:
            v = a.read()
            amb = 0.95*amb + 0.05*v/4096
            bv = 254*amb + 1
            self.set_brightness(bv)
            yield from sleep(123)

    @coroutine
    def play(self, cli, cmd, rol):
        yield self.percolator.play()

    @coroutine
    def stop(self, cli, cmd, rol):
        self.percolator.play_on = False
        yield

    @coroutine
    def master(self):
        self.loop = yield GetRunningLoop(None)
        yield self.manage_brightness()
        yield self.percolator.keep_leds_current(10)
        for i in range(7, 63, 7):
            self.percolator.set_color_of(i, self.percolator.stoichiometric)
        yield self.percolator.bingo()
        yield self.rr.integrate_continuously()
        yield self.spin_feed_rollers()
        while True:
            yield from self.flash_LED(self.act_led)
            yield from sleep(1000)

    def run(self):
        loop = get_event_loop()
        loop.run_until_complete(self.master())



@coroutine
def run(cli, lightshow, config):
    yield lightshow.master()
    while True:
        yield from cli.repl()   # Exits when console not connected
        yield from sleep(400)

def main():

    @coroutine
    def show_config(cli, cmd, rol):
        yield from cli.writeln(repr(config))

    config = eval(open('lightshow.cfg').read())
    if config.get('record'):
        exec('from wsrec import WS2812')
        print('recording')
    else:
        exec('from ws2812 import WS2812')


    @coroutine
    def fuzzle(cli, cmd, rol):
        args = rol.split()
        try:
            n = int(args[0])
        except:
            n = 1
        for i in range(n):
            yield lightshow.fuzzle('a_flag')

    @coroutine
    def fuzzkill(cli, cmd, rol):
        args = rol.split()
        try:
            n = int(args[0])
        except:
            n = 1
        lightshow.a_flag = n
        yield

    @coroutine
    def test(cli, cmd, rol):
        yield from cli.write(b'\x1b[s\x1b[1;40H\x1b[2K')
        yield from cli.write(b'Hey there!')
        yield from cli.write('\x1b[u')
        rr = lightshow.rr
        rr.supertitle = lightshow.supertitle
        #yield from rr.timer_keep_leds_current()
        #rr.balls.append(Ball(ω=2.1, Fd=0.01, color=(64,0,0)))
        #rr.balls.append(Ball(ω=2.08, Fd=0.01, color=(0,64,0)))
        #rr.balls.append(Ball(θ=3.1, Fd=0.0025, color=(0,0,255)))
        #rr.balls.append(Ball(θ=-0.733, ω=0, Fd=0.01, color=(64, 64, 64)))

        #for i in range(8):
        #    rr.balls.append(Ball(θ=-0.733, ω=rand.uniform(0.0, -0.3), Fd=0.01, color=(8,8,8)))
        leds = lightshow.percolator.leds
        for i in range(7, 63, 7):
            leds[i] = lightshow.percolator.stoichiometric
        #leds[28].off()
        #rr.balls.append(Ball(θ=-0.733, ω=rand.uniform(0.0, -0.3), Fd=0.01, color=(8,8,8)))
        yield lightshow.percolator.bingo()

        #print(rr.balls)
        yield rr.integrate_continuously()

    @coroutine
    def eval_cmd(cli, cmd, rol):
        d = {'cli': cli,
             'loop': (yield GetRunningLoop(None)),
             'l': lightshow,
             'pyb': pyb
        }
        try:
            v = eval(rol, d)
        except Exception as e:
            v = e
        yield from cli.writeln(repr(v))

    @coroutine
    def exec_cmd(cli, cmd, rol):
        d = {'cli': cli,
             'loop': (yield GetRunningLoop(None)),
             'l': lightshow,
             'pyb': pyb
        }
        try:
            exec(rol, d)
        except Exception as e:
            yield from cli.writeln(repr(e))


    cli = CoroCLI(config.get('role'))
    inject_standard_commands(cli)
    cli.command_dispatch['conf'] = show_config
    cli.command_dispatch['fuzzle'] = fuzzle
    cli.command_dispatch['fuzzoff'] = fuzzkill
    cli.command_dispatch['test'] = test

    lightshow = Lightshow(write_fun=cli.write, config=config)
    lightshow.a_flag = 0

    cli.command_dispatch['perk'] = lightshow.perk
    cli.command_dispatch['play'] = lightshow.play
    cli.command_dispatch['stop'] = lightshow.stop
    cli.command_dispatch['exec'] = exec_cmd
    cli.command_dispatch['eval'] = eval_cmd

    #loop = new_event_loop(64)   # Pre-allocate space for 64 delayed send/call
    loop = new_event_loop()   # Pre-allocate space for 64 delayed send/call
    set_event_loop(loop)
    loop.run_until_complete(run(cli, lightshow, config))


if __name__ == '__main__':
    main()
