import uctypes
from ws2812 import SubscriptableForPixel

from led_utils import gaussian_blur_weights
from led_utils import _movewords

class WSlice(SubscriptableForPixel):
    # This class encapsulates a WS2812 and provides new capabilities
    # It intrudes into and depends on the internals of the pramasoul
    # version of WS2812
    def __init__(self, ws, start=0, end=None):
        self.ws = ws
        if  start < -len(ws) or start >= len(ws):
            raise IndexError("start %d is outside underlying ws of length %d" % (start, len(ws)))
        start %= len(ws)
        self.start = start
        if end is None:
            self.end = len(ws)
        else:
            self.end = end
        self.pixels = ws[start:end]
        self.sync = ws.sync     # risky
        self.mem = ws.mem
        self.a = uctypes.addressof(ws.buf) + 3*4*start
        self.buf = uctypes.bytearray_at(self.a, 3*4*(end - start))

    def __len__(self):
        return len(self.pixels)

    def update_buf(self, data, where=0):
        self.ws.update_buf(data, where=where+self.start)

    # Too fancy, creates memory stress:
    """
    def rotate_places(self, places):
        length = len(self)
        if places % length == 0: # Optimization, it works without
            return
        unqueued = set(range(length))
        bb = self.ws.buf
        queue = []
        #print(list(tuple(pix) for pix in self))
        while unqueued or queue:
            if queue:
                dst, contents = queue.pop()
            else:
                src = unqueued.pop()
                #print(src, end='')
                dst = (src + places) % length
                contents = bb[12*src:12*(src+1)]
            if dst in unqueued:
                queue.insert(0, ((dst + places) % length, \
                                 bytes(bb[12*dst:12*(dst+1)])))
                unqueued.remove(dst)
            #print('->', dst, end=' ')
            bb[12*dst:12*(dst+1)] = contents
            #print(list(tuple(pix) for pix in self))
    """

    
    def cw(self, start=0, stop=None):
        # Rotates [start, stop) one pixel clockwise
        # i.e. toward the lower index
        length = len(self)
        if stop is None or stop > length:
            stop = length
        if stop <= start + 1:   # Trivial rotation
            return
        a = uctypes.addressof(self.buf)
        tbuf = bytearray(12)
        b = uctypes.addressof(tbuf)
        _movewords(b, a+12*start, 3) # stash 3 words that will get overwritten
        _movewords(a+12*start, a+12*(start+1), 3*(stop-start-1)) # move all but the last word down
        _movewords(a+12*(stop-1), b, 3) # unstash

    def ccw(self, start=0, stop=None):
        # Rotates [start, stop) one pixel counter-clockwise
        # i.e. toward the higher index
        length = len(self)
        if stop is None or stop > length:
            stop = length
        if stop <= start + 1:   # Trivial rotation
            return
        a = uctypes.addressof(self.buf)
        tbuf = bytearray(12)
        b = uctypes.addressof(tbuf)
        _movewords(b, a+12*(stop-1), 3) # stash 3 words that will get overwritten
        _movewords(a+12*(start+1), a+12*start, 3*(stop-start-1)) # move all but the last word down
        _movewords(a+12*(start), b, 3) # unstash

    def shift(self, amount=1, start=0, stop=None):
        # Shifts leds[start:end] by amount to the right
        # amount can be negative, making it a left shift
        length = len(self)
        if stop is None or stop > length:
            stop = length
        if amount < 0:
            src = start - amount
            dest = start
            n = max(stop - start + amount, 0)
        else:
            src = start
            dest = start + amount
            n = max(stop - start - amount, 0)
        a = uctypes.addressof(self.buf)
        _movewords(a+12*dest, a+12*src, 3*n)


