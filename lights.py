# -*- coding: utf-8 -*-
from async_pyb import coroutine, sleep, GetRunningLoop, Sleep

class Lights:
    # Lights encapsulated a WS2812, and provides a "lattice" model of
    # the pixels and a default rendering of them to the leds.  This
    # lattice model has a default treatment in the rendering, which
    # subclasses are free to override. They can then use their lattice
    # points in their own models however they please.
    def __init__(self, leds=None, lights=None, timer=None, lattice=None, indexed_range=None,
                 *args, **kwargs):
        if isinstance(lights, Lights):
            leds = leds or lights.leds
            timer = timer or lights.timer
            lattice = lattice or lights.lattice
            indexed_range = indexed_range or lights.indexed_range
        self.leds = leds
        self.timer = timer
        if leds is None:
            pass                # FIXME
        self.lattice = lattice or [bytearray(3) for i in range(len(leds))]
        if indexed_range is None:
            indexed_range = range(len(leds))
        self.indexed_range = indexed_range
        self.leds_sync_last_done = 0
        self.leds_need_sync = False
        self.brightness = 1.0

    def __len__(self):
        return len(self.indexed_range)

    def __getitem__(self, ix):
        # Indexing with an integer gets you the underlying lattice point
        # Indexing with a slice gets you a new Lights with the derivative indexed_range
        if isinstance(ix, int):
            return self.lattice[self.indexed_range[ix]]
        else:
            ixs = self.indexed_range[ix]
        return self.__class__(lights=self, indexed_range=ixs)

    def __setitem__(self, ix, val):
        if isinstance(ix, int):
            i_val = [(self.indexed_range[ix], val)]
        else:
            i_val = zip(self.indexed_range[ix], val)

        for i, val in i_val:
            p = self.lattice[i]
            try: # to reuse storage
                for k,v in enumerate(val):
                    p[k] = v
            except (TypeError, IndexError):
                self.lattice[i] = val

    def clear(self):
        for p in self:
            p[0] = p[1] = p[2] = 0

    def add_color_to(self, i, color):
        p = self[i]
        for i in range(3):
            p[i] += color[i]

    def sub_color_from(self, i, color):
        p = self[i]
        for i in range(3):
            p[i] -= color[i]

    def set_color_of(self, i, color):
        p = self[i]
        for i in range(3):
            p[i] = color[i]

    def model_colors(self):
        lattice = self.lattice
        for i in self.indexed_range:
            yield lattice[i]

    def gen_RGBs(self):
        br = round(self.brightness * 256)
        #buf = [0, 0, 0] # 18.86ms
        buf = bytearray(range(3)) # 16.93ms
        for p in self.model_colors():
            # The pythonic way is too expensive:
            #yield (min(int((br*v + 128) / 256), 255) for v in p) # 33.45ms
            #yield list(min(int((br*v + 128) / 256), 255) for v in p) # 22.83ms
            r, g, b = p

            # 13.4546ms
            #buf[0] = min(int((br*r + 128) / 256), 255)
            #buf[1] = min(int((br*g + 128) / 256), 255)
            #buf[2] = min(int((br*b + 128) / 256), 255)

            # 12.3317ms
            #buf[0] = min((int(br*r) + 128) // 256, 255)
            #buf[1] = min((int(br*g) + 128) // 256, 255)
            #buf[2] = min((int(br*b) + 128) // 256, 255)

            # 12.2485ms
            buf[0] = min((int(br*r) + 128) >> 8, 255)
            buf[1] = min((int(br*g) + 128) >> 8, 255)
            buf[2] = min((int(br*b) + 128) >> 8, 255)
            yield buf

    def render(self):
        leds = self.leds
        for i, c in zip(self.indexed_range, self.gen_RGBs()):
            leds[i] = c

    @coroutine
    def show_for(self, duration):
        self.leds_need_sync = True
        yield from sleep(duration)

    @coroutine
    def timer_keep_leds_current(self, interval=10):
        # Using a timer to sync the leds seems clever, but one might
        # be half-way through a non-atomic update of color when the
        # timer interrupt hits, so this is often not the best way to
        # do the job
        timer = self.timer
        if timer is None:
            return
        leds = self.leds
        timer.callback(None)
        timer.init(freq=round(1000/interval))
        timer.callback(lambda t: leds.sync())
        yield

    @coroutine
    def keep_leds_current(self, interval):
        last_check_time = 0
        loop = yield GetRunningLoop(None)
        while True:
            now = loop.time()
            if now < last_check_time + interval:
                yield Sleep(last_check_time + interval - now)
            last_check_time = loop.time()
            if self.leds_need_sync:
                #self.leds.sync()
                self.render()
                self.leds.sync()
                self.leds_sync_last_done = loop.time()
                self.leds_need_sync = False

    def __repr__(self):
        return "<{} {} with {}>"\
            .format(self.__class__.__name__, self.leds, self.indexed_range)

