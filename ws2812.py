# -*- coding: utf-8 -*-

import pyb
from array import array
from uctypes import addressof, bytearray_at
from _collections import namedtuple
from sys import platform

if platform == 'pyboard':
    from ws2812_helper_pyb import _get, _set, _set_rgb_values, _clearLEDs
else:
    from ws2812_helper_sim import _get, _set, _set_rgb_values, _clearLEDs

# Values of "mem" to WS2812 init
PREALLOCATE = 0
CACHE = 1
RECREATE = 2

class SubscriptableForPixel:
    # Provides subscripting of one's pixels

    def get_led_pixel(self, index):
        # This layer works to prevent heap garbage creation that was
        # being created by an iterator even when it was not in the
        # execution path! This keeps that iterator out of the method
        # called for an integer index
        if isinstance(index, int):
            return self.get_one_led_pixel(index)
        else:
            return self.get_led_pixel_slice(index)

    def get_one_led_pixel(self, index):
        #return self.pixels[index] # DEBUG
        mem = self.mem
        if mem <= CACHE:
            pixels = self.pixels
        length = len(self)
        if True:
            if not -length <= index < length:
                raise IndexError("tried to get pixel", index)

            if mem >= RECREATE:
                return Pixel(self.buf, 3*(index%length))
            index %= length
            pix = pixels[index]
            if pix is None:
                pix = pixels[index] = Pixel(self.buf, index*3)
            return pix

    def get_led_pixel_slice(self, index):
        mem = self.mem
        if mem <= CACHE:
            pixels = self.pixels
        length = len(self)
        try:
            start, stop, step = index.start, index.stop, index.step
        except AttributeError:
            # e.g. 'slice(3, 6, None)'
            start, stop, step = eval(str(index)[5:])
        #print(start, stop, step)
        #print(list(range(length)[start:stop]))
        # Could raise NotImplemented if step is not None
        want = range(length)[start:stop]
        if mem >= RECREATE:
            return [self[i] for i in want]

        # Hasn't happened, can probably remove:
        if isinstance(want, int):
            assert not isinstance(want, int), "Hey, want is %r" % want # DEBUG
            want = [want]

        if len(want) == 0:
            raise IndexError("tried to get pixel %r" % index)

        if mem == CACHE:
            # Make sure all the positions we're hitting are cached
            for i in want:
                if pixels[i] is None:
                    pixels[i] = Pixel(self.buf, 3*i)

        return pixels[index]


    __getitem__ = get_led_pixel
    #__getitem__ = get_led_values

    # A helper method
    set_led_buf = bytearray(3)
    def _addressable(self, v):
        # This dance is so we create less garbage on the heap
        if isinstance(v, bytearray):
            pass
        elif isinstance(v, bytes):
            v = addressof(v)
        else:
            #vb = bytearray(iter(vb))
            vb = self.set_led_buf # Reuse to minimise heap impact
            #print("vb starts as", vb, end=' ')
            try:
                for i in range(3):
                    vb[i] = v[i]
                #print("vb is", vb, end=' ')
            except:
                it = iter(v)
                vb[0] = next(it)
                vb[1] = next(it)
                vb[2] = next(it)
            v = vb
        return v


    def set_led(self, index, value):
        # set LED buffer at index to value
        # value is bytearray((r,g,b)) or bytes((r,g,b))
        # The asm function is unguarded as to index, so enforce here

        length = len(self)

        if isinstance(index, int):
            if not -length <= index < length:
                raise IndexError("tried to set LED", index, "out of", length)
            if not isinstance(value, bytearray):
                value = self._addressable(value)
            _set_rgb_values(self.buf, index, value)
            return

        #else
        # assume it's a slice
        try:
            start, stop, step = index.start, index.stop, index.step
        except AttributeError:
            # e.g. 'slice(3, 6, None)'
            start, stop, step = eval(str(index)[5:])
        #print(start, stop, step)
        #print(list(range(length)[start:stop]))
        dests = range(length)[start:stop]

        for i, v in zip(dests, value):
            #print("i", i, "v", v, end=' ')
            v = self._addressable(v)
            #print("now v is", v)
            _set_rgb_values(self.buf, i, v)


    __setitem__ = set_led


class WS2812(SubscriptableForPixel):
    # Driver for WS2812 RGB LEDs. May be used for controlling single LED or chain
    # of LEDs.
    #
    # Examples of use:
    #
    #    chain = WS2812(spi_bus=1, led_count=4)
    #    i = 0
    #    for pixel in chain:
    #        pixel.r = i
    #        pixel.g = i + 1
    #        pixel.b = i + 2
    #        i += 3
    #    chain.sync()
    #
    #    chain = WS2812(spi_bus=1, led_count=4)
    #    data = [
    #        (255, 0, 0),    # red
    #        (0, 255, 0),    # green
    #        (0, 0, 255),    # blue
    #        (85, 85, 85),   # white
    #    ]
    #    chain.show(data)
    #
    # Version: 1.5

    buf_bytes = (0x11, 0x13, 0x31, 0x33)
    ReadOnlyPixel = namedtuple('Pixel', 'r g b')

    def __init__(self, spi_bus=1, led_count=1, intensity=1, mem=PREALLOCATE):
        #Params:
        # spi_bus = SPI bus ID (1 or 2)
        # led_count = count of LEDs
        # intensity = light intensity (float up to 1)
        # mem = how stingy to be with memory (comes at a speed & GC cost)
        self.led_count = led_count
        self.intensity = intensity # FIXME: intensity is ignored
        self.mem = mem
        # 0 prealloc
        # 1 cache
        # 2 create Pixel each time

        # prepare SPI data buffer (4 bytes for each color for each pixel,
        # with an additional zero byte at the end to make sure the data line
        # comes to rest low)
        self.buf = bytearray(4*3*led_count + 1)

        if mem <= CACHE:
            # Prepare a cache by index of Pixel objects
            self.pixels = pixels = [None] * led_count
            if mem == PREALLOCATE: # Pre-allocate the pixels
                for i in range(led_count):
                    pixels[i] = Pixel(self.buf, 3*i)

        # OBSOLETE
        #self.bits = array('L', range(256))
        #bb = bytearray_at(addressof(self.bits), 4*256)
        #mask = 0x03
        #buf_bytes = self.buf_bytes
        #for i in range(256):
        #    index = 4*i
        #    bb[index] = buf_bytes[i >> 6 & 0x03]
        #    bb[index+1] = buf_bytes[i >> 4 & 0x03]
        #    bb[index+2] = buf_bytes[i >> 2 & 0x03]
        #    bb[index+3] = buf_bytes[i & 0x03]

        # SPI init
        self.spi = pyb.SPI(spi_bus, pyb.SPI.MASTER, baudrate=3200000, polarity=0, phase=1)

        # turn LEDs off
        self.show([])

    def __len__(self):
        return self.led_count

    def get_led_values(self, index, rgb=None):
        # The asm function is unguarded as to index, so enforce here
        if index >= self.led_count or index < -self.led_count:
            raise IndexError("tried to get values at", index)
        ix = index * 3
        return self.ReadOnlyPixel(_get(self.buf, ix+1), \
                                  _get(self.buf, ix+0), \
                                  _get(self.buf, ix+2))

    def show(self, data):
        # Show RGB data on LEDs. Expected data = [(R, G, B), ...] where R, G and B
        # are intensities of colors in range from 0 to 255. One RGB tuple for each
        # LED. Count of tuples may be less than count of connected LEDs.
        self.fill_buf(data)
        self.send_buf()

    def send_buf(self):
        #Send buffer over SPI.
        self.spi.send(self.buf)

    def sync(self, to=None):
        if to is None:
            self.spi.send(self.buf)
        else:
            short_buf = bytearray_at(addressof(self.buf), 3*4*to + 1) # extra byte
            t = short_buf[-1]
            short_buf[-1] = 0
            self.spi.send(short_buf)
            short_buf[-1] = t

    _ubb = bytearray(3)
    def update_buf(self, data, where=0):
        # Fill a part of the buffer with RGB data.
        # Returns the index of the first unfilled LED
        # data is an iterable that returns an iterable
        # e.g. [(1,2,3), (4,5,6)]
        # or some generator of tuples or generators
        set_led = self.set_led
        b = self._ubb
        for d in data:
            if not isinstance(d, bytearray):
                b[0], b[1], b[2] = d
                d = b
            set_led(where, d)
            where += 1
        return where

    def fill_buf(self, data):
        # Fill buffer with RGB data.
        # All LEDs after the data are turned off.
        end = self.update_buf(data)

        # turn off the rest of the LEDs
        #b = self.buf
        #for i in range(4*3*end, 4*3*self.led_count):
        #    b[i] = 0x11   # off
        _clearLEDs(self.buf, end, self.led_count-end)


class Pixel:
    cmap = (1,0,2)

    def __init__(self, a, i):
        self.a = a
        self.i = i

    @property
    def r(self):
        return _get(self.a, self.i+1)

    @r.setter
    def r(self, v):
        _set(self.a, self.i+1, v)

    @property
    def g(self):
        return _get(self.a, self.i)

    @g.setter
    def g(self, v):
        _set(self.a, self.i, v)

    @property
    def b(self):
        return _get(self.a, self.i+2)

    @b.setter
    def b(self, v):
        _set(self.a, self.i+2, v)

    def __getitem__(self, i):
        if i >= 3 or i < 0:
            raise IndexError("only 3 colors")
        return _get(self.a, self.i + self.cmap[i])

    def __setitem__(self, i, v):
        if i >= 3 or i < 0:
            raise IndexError("only 3 colors")
        return _set(self.a, self.i + self.cmap[i], v)

    def off(self):
        self.r = self.b = self.g = 0

    def __len__(self):
        return 3

    def __repr__(self):
        return "<Pixel %d (%d, %d, %d) of chain 0x%x>" % \
            (self.i//3, self.r, self.g, self.b, addressof(self.a))


