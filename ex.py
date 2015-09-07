# Experimentation

from ws2812 import WS2812
from led_utils import Percolator

import logging

from ubinascii import hexlify, unhexlify

from async_pyb import new_event_loop, set_event_loop, get_event_loop, \
    EventLoop, GetRunningLoop, Sleep, Future, TimeoutError, \
    coroutine, sleep, wait_for

from coro_cli import CoroCLI, inject_standard_commands

import pyb
from pyb import SPI, Pin, info, millis, elapsed_millis, \
    micros, elapsed_micros, rng

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

        self.leds = WS2812(spi_bus=config['leds'].get('spi'), \
                           led_count=config['leds'].get('qty'))

        self.percolator = Percolator(self.leds)


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


    @coroutine
    def play(self, cli, cmd, rol):
        yield self.percolator.play()

    @coroutine
    def stop(self, cli, cmd, rol):
        self.percolator.play_on = False
        yield

    @coroutine
    def master(self):
        #self.radio_listener_quit = 0
        self.loop = yield GetRunningLoop(None)
        yield self.percolator.keep_leds_current(10)
        while True:
            yield from self.flash_LED(self.act_led)
            yield from sleep(1000)

    def run(self):
        loop = get_event_loop()
        loop.run_until_complete(self.master())



@coroutine
def run(cli, lightshow, config):
    yield lightshow.master()
    yield from cli.repl()


def main():

    @coroutine
    def show_config(cli, cmd, rol):
        yield from cli.writeln(repr(config))

    config = eval(open('lightshow.cfg').read())


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

    loop = new_event_loop()
    set_event_loop(loop)
    loop.run_until_complete(run(cli, lightshow, config))


if __name__ == '__main__':
    main()
