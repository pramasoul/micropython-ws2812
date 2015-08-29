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

        # prepare SPI data buffer. One long (=4 bytes) for each color.
        z = self.buf_bytes[0]
        self.a = array('L', (z for i in range(3*led_count + 1))) # extra word of zero
        self.buf = bytearray_at(addressof(self.a), 3*4*led_count + 1) # extra byte
        #self.buf = bytearray(z for i in range(3*4*led_count + 1))

        self.buf[-1] = 0        # make it \x00 to idle SPI low after transfer

        # Make a translation table from LED value to SPI bit pattern
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

    def show(self, data):
        # Show RGB data on LEDs. Expected data = [(R, G, B), ...] where R, G and B
        # are intensities of colors in range from 0 to 255. One RGB tuple for each
        # LED. Count of tuples may be less than count of connected LEDs.
        self.fill_buf(data)
        self.send_buf()

    def send_buf(self):
        #Send buffer over SPI.
        self.spi.send(self.buf)

    def update_buf(self, data, start=0):
        return self._update_buf(data, start)

    @micropython.viper
    def _update_buf(self, data, start:int) -> int:
        # Fill a part of the buffer with RGB data.
        #
        # Order of colors in buffer is changed from RGB to GRB because WS2812 LED
        # has GRB order of colors. Each color is represented by 4 bytes in buffer
        # (1 byte for each 2 bits).
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
            start += 1

        return start


    def fill_buf(self, data):
        # Fill buffer with RGB data.
        #
        # All LEDs after the data are turned off.
        end = self.update_buf(data)

        # turn off the rest of the LEDs
        a = self.a
        off = self.bits[0]
        for index in range(end * 3, self.led_count * 3):
            a[index] = off
            index += 1
        # leave last buffer byte value 0
