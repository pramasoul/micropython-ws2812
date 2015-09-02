# -*- coding: utf-8 -*-

import pyb
from array import array
from uctypes import addressof, bytearray_at


class WS2812:
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

    def __init__(self, spi_bus=1, led_count=1, intensity=1):
        #Params:
        # spi_bus = SPI bus ID (1 or 2)
        # led_count = count of LEDs
        # intensity = light intensity (float up to 1)
        self.led_count = led_count
        self.intensity = intensity
        # FIXME: intensity is ignored

        # prepare SPI data buffer (4 bytes for each color for each pixel)

        # Accessable as word-per-color via the self.a array of 32-bit longs:
        self.a = array('L', range(3*led_count + 1)) # extra word of zero

        # The byte array buffer that gets sent out the SPI is the one underlying self.a:
        self.buf = bytearray_at(addressof(self.a), 3*4*led_count + 1) # extra byte
        self.buf[-1] = 0        # make it \x00 to idle SPI low after transfer

        # Prepare an empty cache by index of Pixel objects
        self.pixels = [None] * led_count

        # OBSOLETE
        self.bits = array('L', range(256))
        bb = bytearray_at(addressof(self.bits), 4*256)
        mask = 0x03
        buf_bytes = self.buf_bytes
        for i in range(256):
            index = 4*i
            bb[index] = buf_bytes[i >> 6 & 0x03]
            bb[index+1] = buf_bytes[i >> 4 & 0x03]
            bb[index+2] = buf_bytes[i >> 2 & 0x03]
            bb[index+3] = buf_bytes[i & 0x03]

        # SPI init
        self.spi = pyb.SPI(spi_bus, pyb.SPI.MASTER, baudrate=3200000, polarity=0, phase=1)

        # turn LEDs off
        self.show([])

    def __len__(self):
        return self.led_count

    def get_led_values(self, index, rgb=None):
        # The asm function is unguarded as to index, so enforce here:
        if index >= self.led_count or index < 0:
            raise IndexError("tried to get item", index)
        a_get = _get
        ix = index * 3
        rv = rgb or bytearray(3)
        rv[0] = a_get(self.buf, ix+1) # ws2812 part is green first
        rv[1] = a_get(self.buf, ix+0) # then red
        rv[2] = a_get(self.buf, ix+2) # then blue
        return rv

    def get_led_pixel(self, index):
        # The asm function is unguarded as to index, so enforce here:
        if index >= self.led_count or index < 0:
            raise IndexError("tried to get item", index)
        pixels = self.pixels
        if pixels[index]:
            return pixels[index]
        pix = pixels[index] = Pixel(self.buf, index*3)
        return pix

    __getitem__ = get_led_pixel

    def set_led(self, index, value):
        # set LED buffer at index to value
        # value is bytearray((r,g,b)) or bytes((r,g,b))
        # The asm function is unguarded as to index, so enforce here
        if index >= self.led_count or index < 0:
            raise IndexError
        if isinstance(value, bytes):
            value = bytearray_at(addressof(value), 3)
        elif isinstance(value, Pixel):
            value = bytearray(list(value))
        return self.a_set_rgb_values(self.buf, index, value)

    __setitem__ = set_led

    @staticmethod
    @micropython.asm_thumb
    def a_set_rgb_values(r0, r1, r2):
        # Register arguments:
        # r0: base of encoded pixel buffer (12 bytes / pixel)
        # r1: pixel #
        # r2: base of bytearray((r,g,b)) of values to set

        # r3: address of first (i.e. green) encoded 32-bit word
        # r4: 2
        # r5: base of data table
        # r6: 3
        # r7: temporary

        mov(r5, pc)        # know the base of the data table
        b(START)           # get to entry point
        data(1, 0x11, 0x13, 0x31, 0x33) # encoded bytes corresponding to 2-bit values
        align(2)           # ritual requirement

        label(ENCODE)      # The encode(r1) entry point
        # r1 is value in 0-255 to encode
        # returns encoded word in r0
        mov(r7, r1)        # r7 is value
        and_(r7, r6)       # r7 is bottom two bits of value
        add(r7, r7, r5)    # r7 is address of encoded data byte
        ldrb(r0, [r7,0])   # r0 is encoded data byte

        lsr(r1, r4)        # r1 is value >> 2
        mov(r7, r1)        # r7 is value >> 2
        and_(r7, r6)       # r7 is b3b2 of value
        add(r7, r7, r5)    # r7 is address of encoded data byte
        ldrb(r7, [r7,0])   # r7 is encoded data byte
        lsl(r0, r6)        # r0 <<= 3
        lsl(r0, r6)        # r0 <<= 3
        lsl(r0, r4)        # r0 <<= 2 (in sum, r0 <<= 8)
        orr(r0, r7)        # r0 half done

        lsr(r1, r4)        # r1 is value >> 4
        mov(r7, r1)        # r7 is value >> 4
        and_(r7, r6)       # r7 is b5b4 of value
        add(r7, r7, r5)    # r7 is address of encoded data byte
        ldrb(r7, [r7,0])   # r7 is encoded data byte
        lsl(r0, r6)        # r0 <<= 3
        lsl(r0, r6)        # r0 <<= 3
        lsl(r0, r4)        # r0 <<= 2 (in sum, r0 <<= 8)
        orr(r0, r7)        # r0 three-quarters done

        lsr(r1, r4)        # r1 is value >> 6
        mov(r7, r1)        # r7 is value >> 6
        and_(r7, r6)       # r7 is b7b6 of value
        add(r7, r7, r5)    # r7 is address of encoded data byte
        ldrb(r7, [r7,0])   # r7 is encoded data byte
        lsl(r0, r6)        # r0 <<= 3
        lsl(r0, r6)        # r0 <<= 3
        lsl(r0, r4)        # r0 <<= 2 (in sum, r0 <<= 8)
        orr(r0, r7)        # r0 all done
        bx(lr)

        label(START)        # entry point

        # Find the starting address of where we store result
        mov(r3, 12)         # 12 bytes per pixel
        mul(r3, r1)         # r3 is address offset from base
        add(r3, r3, r0)     # r3 is address of first (i.e. green) encoded 32-bit word

        # set up useful constants
        mov(r4, 2)
        mov(r6, 3)

        ldrb(r1, [r2,1])   # get green value
        bl(ENCODE)
        str(r0, [r3,0])     # store encoded green

        ldrb(r1, [r2,0])   # get red value
        bl(ENCODE)
        str(r0, [r3,4])     # store encoded red

        ldrb(r1, [r2,2])   # get blue value
        bl(ENCODE)
        str(r0, [r3,8])     # store encoded blue



    def show(self, data):
        # Show RGB data on LEDs. Expected data = [(R, G, B), ...] where R, G and B
        # are intensities of colors in range from 0 to 255. One RGB tuple for each
        # LED. Count of tuples may be less than count of connected LEDs.
        self.fill_buf(data)
        self.send_buf()

    def send_buf(self):
        #Send buffer over SPI.
        self.spi.send(self.buf)

    sync = send_buf             # better name

    def was_update_buf(self, data, start=0):
        # Fill a part of the buffer with RGB data.
        #
        # Order of colors in buffer is changed from RGB to GRB because WS2812 LED
        # has GRB order of colors. Each color is represented by 4 bytes in buffer
        # (1 byte for each 2 bits), corresponding to one 32-bit word in self.a
        #
        # Returns the index of the first unfilled LED

        a = self.a
        bits = self.bits
        intensity = self.intensity
        index = start * 3

        for red, green, blue in tuple(data):
            red = min(round(red * intensity), 0xff)
            green = min(round(green * intensity), 0xff)
            blue = min(round(blue * intensity), 0xff)

            a[index] = bits[green]
            a[index+1] = bits[red]
            a[index+2] = bits[blue]

            index += 3

        return index // 3

    def update_buf(self, data, where=0):
        # Fill a part of the buffer with RGB data.
        # Returns the index of the first unfilled LED
        # data is an iterable that returns an iterable
        # e.g. [(1,2,3), (4,5,6)]
        # or some generator of tuples or generators
        set_led = self.set_led
        b = bytearray(3)
        for b[0], b[1], b[2] in tuple(data):
            set_led(where, b)
            where += 1
        return where

    def fill_buf(self, data):
        # Fill buffer with RGB data.
        # All LEDs after the data are turned off.
        end = self.update_buf(data)

        # turn off the rest of the LEDs
        a = self.a
        for i in range(end * 3, self.led_count * 3):
            a[i] = 0x11111111   # off


class Pixel:
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
        return _get(self.a, self.i + (1,0,2)[i])

    def __setitem__(self, i, v):
        if i >= 3 or i < 0:
            raise IndexError("only 3 colors")
        return _set(self.a, self.i + (1,0,2)[i], v)

    def off(self):
        self.r = self.b = self.g = 0

    def __len__(self):
        return 3

    def __repr__(self):
        return "<Pixel %d (%d, %d, %d) of chain 0x%x>" % \
            (self.i//3, self.r, self.g, self.b, addressof(self.a))

@micropython.asm_thumb
def _get(r0, r1):
    # Registers:
    # r0: base of array 'self.a' of 32-bit words
    # r1: index into array
    # r7: 4 * index (byte offset)
    # r6: address of word in array
    # r3: temporary
    # r4: literals
    # Note this could be improved by using the full Thumb instruction set. See:
    # http://docs.micropython.org/en/latest/reference/asm_thumb2_hints_tips.html#use-of-unsupported-instructions
    add(r7, r1, r1)     # * 2
    add(r7, r7, r7)     # * 4
    add(r6, r0, r7)     # base + 4 * index

    # Notation: numeral indicates bit position in decoded result
    # That bit may be True or False. Our job is to herd them to r0
    # "-" is a clear bit (aka False or 0), "+" is a set bit (aka True or 1)
    ldr(r3, [r6, 0])    # r3 is --1+--0+--3+--2+--5+--4+--7+--6+
    mov(r0, r3)         # r0 is --1+--0+--3+--2+--5+--4+--7+--6+
    mov(r4, 1)          # r4 is 1
    lsr(r0, r4)         # r0 is ---1+--0+--3+--2+--5+--4+--7+--6
    and_(r0, r3)        # r0 is ---1---0---3---2---5---4---7---6
    mov(r3, r0)         # r3 is ---1---0---3---2---5---4---7---6
    mov(r4, 3)          # r4 is 3
    lsl(r0, r4)         # r0 is 1---0---3---2---5---4---7---6---
    orr(r0, r3)         # r0 is 1--10--03--32--25--54--47--76--6
    mov(r3, r0)         # r3 is 1--10--03--32--25--54--47--76--6
    mov(r4, 10)
    lsl(r0, r4)         # r0 is -32--25--54--47--76--6----------
    orr(r0, r3)         # r0 is 1321025035432472576546-47--76--6
    mov(r4, 7)
    lsr(r0, r4)         # r0 is -------1321025035432472576546-47
    movwt(r4, 0xf000f0) # r4 is --------++++------------++++----
    and_(r0, r4)        # r0 is --------3210------------7654----
    mov(r3, r0)         # r3 is --------3210------------7654----
    mov(r4, 20)
    lsr(r0, r4)         # r0 is ----------------------------3210
    orr(r0, r3)         # r0 is --------3210------------76543210
    mov(r4, 0xff)
    and_(r0, r4)        # r0 is ------------------------76543210


@micropython.asm_thumb
def _set(r0, r1, r2):
    # Register arguments:
    # r0: base of encoded pixel buffer (12 bytes / pixel)
    # r1: pixel offset e.g. 7 for red value of 3rd pixel in chain
    # r2: value to set

    # r3: address of encoded pixel
    # r4: 2
    # r5: base of data table
    # r6: 3
    # r7: temporary

    mov(r5, pc)        # know the base of the data table
    b(START)           # get to entry point
    data(1, 0x11, 0x13, 0x31, 0x33) # encoded bytes corresponding to 2-bit values
    align(2)           # ritual requirement

    label(ENCODE)      # The encode(r1) entry point
    # r1 is value in 0-255 to encode
    # returns encoded word in r0
    mov(r7, r1)        # r7 is value
    and_(r7, r6)       # r7 is bottom two bits of value
    add(r7, r7, r5)    # r7 is address of encoded data byte
    ldrb(r0, [r7,0])   # r0 is encoded data byte

    lsr(r1, r4)        # r1 is value >> 2
    mov(r7, r1)        # r7 is value >> 2
    and_(r7, r6)       # r7 is b3b2 of value
    add(r7, r7, r5)    # r7 is address of encoded data byte
    ldrb(r7, [r7,0])   # r7 is encoded data byte
    lsl(r0, r6)        # r0 <<= 3
    lsl(r0, r6)        # r0 <<= 3
    lsl(r0, r4)        # r0 <<= 2 (in sum, r0 <<= 8)
    orr(r0, r7)        # r0 half done

    lsr(r1, r4)        # r1 is value >> 4
    mov(r7, r1)        # r7 is value >> 4
    and_(r7, r6)       # r7 is b5b4 of value
    add(r7, r7, r5)    # r7 is address of encoded data byte
    ldrb(r7, [r7,0])   # r7 is encoded data byte
    lsl(r0, r6)        # r0 <<= 3
    lsl(r0, r6)        # r0 <<= 3
    lsl(r0, r4)        # r0 <<= 2 (in sum, r0 <<= 8)
    orr(r0, r7)        # r0 three-quarters done

    lsr(r1, r4)        # r1 is value >> 6
    mov(r7, r1)        # r7 is value >> 6
    and_(r7, r6)       # r7 is b7b6 of value
    add(r7, r7, r5)    # r7 is address of encoded data byte
    ldrb(r7, [r7,0])   # r7 is encoded data byte
    lsl(r0, r6)        # r0 <<= 3
    lsl(r0, r6)        # r0 <<= 3
    lsl(r0, r4)        # r0 <<= 2 (in sum, r0 <<= 8)
    orr(r0, r7)        # r0 all done
    bx(lr)

    label(START)       # entry point

    # Find the address of where we store result
    add(r1, r1, r1)    # * 2
    add(r1, r1, r1)    # * 4 = word width
    add(r3, r0, r1)    # r3 is address of encoded 32-bit word

    # set up useful constants
    mov(r4, 2)
    mov(r6, 3)

    mov(r1, r2)        # pass pixel value to encoder
    bl(ENCODE)
    str(r0, [r3,0])    # store encoded value
