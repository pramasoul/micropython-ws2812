# -*- coding: utf-8 -*-

import pyb
from array import array
from uctypes import addressof, bytearray_at


class WS2812:
    #Driver for WS2812 RGB LEDs. May be used for controlling single LED or chain
    #of LEDs.
    #
    #Example of use:
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
    #Version: 1.0

    buf_bytes = (0x11, 0x13, 0x31, 0x33)

    def __init__(self, spi_bus=1, led_count=1, intensity=1):
        #Params:
        # spi_bus = SPI bus ID (1 or 2)
        # led_count = count of LEDs
        # intensity = light intensity (float up to 1)
        self.led_count = led_count
        self.intensity = intensity

        # prepare SPI data buffer (4 bytes for each color for each pixel)
        self.a = array('L', range(3*led_count + 1)) # extra word of zero
        self.buf = bytearray_at(addressof(self.a), 3*4*led_count + 1) # extra byte
        #self.buf = bytearray(z for i in range(3*4*led_count + 1))

        self.buf[-1] = 0        # make it \x00 to idle SPI low after transfer

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

    def get_led(self, index, rgb=None):
        if index >= self.led_count or index < 0:
            raise IndexError("tried to get item", index)
        a_get = self.a_get
        ix = index * 3
        rv = rgb or bytearray(3)
        rv[0] = a_get(self.buf, ix+1)
        rv[1] = a_get(self.buf, ix+0)
        rv[2] = a_get(self.buf, ix+2)
        return rv

    __getitem__ = get_led

    @staticmethod
    @micropython.asm_thumb
    def a_get(r0, r1):
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


    def set_led(self, index, value):
        # set LED buffer at index to value
        # value is bytearray((r,g,b))
        if index >= self.led_count or index < 0:
            raise IndexError
        return self.a_set(self.buf, index, value)

    __setitem__ = set_led

    @staticmethod
    @micropython.asm_thumb
    def a_set(r0, r1, r2):
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
        # (1 byte for each 2 bits).
        #
        # Returns the index of the first unfilled LED
        #
        # Note: If you find this function ugly, it's because speed optimisations
        # beat purity of code.

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
