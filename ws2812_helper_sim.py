# -*- coding: utf-8 -*-
from uctypes import addressof, bytearray_at

def _get(a, i):
#    b = bytearray_at(a, 64*3*4)
    rv = a[i]
    #print("<%d is %r>" % (i, rv))        # DEBUG
    return rv

def _set(a, i, v):
#    b = bytearray_at(a, 64*3*4)
    b = a
    #print("<%d becoming %r>" % (i, v))        # DEBUG
    b[i] = v

def _set_rgb_values(buf, index, value):
    #print("_set_rgb_values(0x%x, %d, %r)" % (addressof(buf), index, value))
    if isinstance(value, int):
        value = bytearray_at(value, 3)
    i = index * 3
    # G, R, B
    buf[i] = value[1]
    buf[i+1] = value[0]
    buf[i+2] = value[2]

def _clearLEDs(buf, start, qty):
    # Clear qty LEDs in buffer starting at i
    for i in range(start, start + qty):
        buf[i] = 0
