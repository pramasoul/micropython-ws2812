# -*- coding: utf-8 -*-
#import random
import math
#from async_pyb import coroutine, sleep, GetRunningLoop, Sleep
#from pyb import Timer, rng, micros, elapsed_micros


def display_list_for(x, color, blur=1.0):
    # In arbitrary pixel coordinates
    rv = []
    for i, w in gaussian_blur_weights(x, blur):
        try:                # DEBUG
            sc = bytes(round(v*w) for v in color)
        except TypeError:
            print(repr(color))
            raise
        if sc:
            rv.append((i, sc))
    return rv

def gaussian_blur_weights(x, blur=1.0):
    # In arbitrary pixel coordinates in a 1-D space
    # Provides an iterable of (i, weight)'s for a point source at float x
    # where the positions i are integers, sum(weights) is 1.0, and 
    # min(weight) about 1/255
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


@micropython.asm_thumb
def _fillwords(r0, r1, r2):
    # _fillwords(address, word, n), returns first word address past fill
    # Registers:
    # r0: address of start of block of words to fill
    # r1: value to fill with
    # r2: number of 32-bit words to fill
    # Note this could be improved by using the full Thumb instruction set. See:
    # http://docs.micropython.org/en/latest/reference/asm_thumb2_hints_tips.html#use-of-unsupported-instructions
    mov(r4, 4)
    label(loop)
    cmp(r2, 0)
    ble(done)
    str(r1, [r0, 0])
    add(r0, 4)
    sub(r2, 1)
    b(loop)
    label(done)

@micropython.asm_thumb
def _movewords(r0, r1, r2):
    # styled after memmove(dest, src, n), but moving words instead of bytes
    # Registers:
    # r0: destination address
    # r1: source address
    # r2: number of 32-bit words to move
    # r3: temporary
    # r4: step
    # Note this could be improved by using the full Thumb instruction set. See:
    # http://docs.micropython.org/en/latest/reference/asm_thumb2_hints_tips.html#use-of-unsupported-instructions
    cmp(r2, 0)                  # if n <= 0:
    ble(done)                   #  return
    mov(r4, 4)                  # words are 4 bytes
    cmp(r1, r0)                 # src - dest
    beq(done)                   # src == dest: return
    bhi(loop)                   # src > dest: move'em

    # Here the source is a lower address than the destination. To
    # protect against overwriting the data during the move, we move it
    # starting at the end (high) address
    neg(r4, r4)                 # -4
    add(r3, r2, r2)             # 2 * n
    add(r3, r3, r3)             # 4 * n
    add(r3, r3, r4)             # 4 * (n - 1)
    add(r0, r0, r3)             # r0 is dest[-1]
    add(r1, r1, r3)             # r1 is src[-1]

    # The moving itself
    label(loop)
    ldr(r3, [r1, 0])
    str(r3, [r0, 0])
    add(r0, r0, r4)
    add(r1, r1, r4)
    sub(r2, 1)
    bgt(loop)

    label(done)
