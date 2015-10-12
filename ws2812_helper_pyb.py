# -*- coding: utf-8 -*-
from uctypes import addressof #, bytearray_at

def _get(a, i):
    rv = __get(a, i)
    #print("<%d is %r>" % (i, rv))        # DEBUG
    return rv

def _set(a, i, v):
    #print("<%d becoming %r>" % (i, v))        # DEBUG
    return __set(a, i, v)

def _clearLEDs(buf, i, qty):
    # Clear qty LEDs in buffer starting at i
    a = addressof(buf)
    _fillwords(a + 4*3*i, 0x11111111, 3*qty)


@micropython.asm_thumb
def __get(r0, r1):
    # Registers:
    # r0: base of array of 32-bit words, each encoding a color,
    #     each triple (G,R,B) encoding a pixel
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
def __set(r0, r1, r2):
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


@micropython.asm_thumb
def _set_rgb_values(r0, r1, r2):
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
