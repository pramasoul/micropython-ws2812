import random
from pyb import rng
from async_pyb import coroutine, sleep
from lights import Lights


class Percolator(Lights):
    def __init__(self, leds):
        # Assume 8x8, and 0-based, for now
        super().__init__(leds)
        self.top_i = len(leds) - 1
        self.bottom_i = 0
        self.random = random.SystemRandom()
        self.perk_quit = False
        self.stoichiometric = (1,1,1)

    def down_left(self, i):
        # return the index into leds that is down-left of i
        if i // 8:
            return i-8
        else:
            return None

    def down_right(self, i):
        # return the index into leds that is down-right of i
        if i % 8:
            return i-1
        else:
            return None

    def steer_down(self, i, right):
        # Go down
        if right:
            rv = self.down_right(i)
        else:
            rv = self.down_left(i)
        return rv

    def down(self, i, right):
        rv = self.steer_down(i, right)
        if rv is None:
            rv = self.steer_down(i, not right)
        return rv

    def at_mid(self, i):
        return i//8 + i%8 == 7


    @coroutine
    def perk(self, delay, color, start=None):
        #print("perk(%d, %r, %r)" % (delay, color, start))
        stoichiometric = self.stoichiometric
        i = None
        while True:
            if i is None:
                if start is None:
                    i = self.top_i
                else:
                    i = start
            self.add_color_to(i, color)
            yield from self.show_for(delay)
            if self.at_mid(i):
                new_color = yield from self.react_at(i)
                if new_color is None:
                    return
                else:
                    color = new_color
            prev_i = i
            i = self.down(i, rng()&1)
            self.sub_color_from(prev_i, color)
            self.leds_need_sync = True
            if i is None:
                return color
            if self.perk_quit:
                break
        self.perk_quit -= 1


    @coroutine
    def react_at(self, i):
        stoichiometric = self.stoichiometric
        lattice = self.lattice
        p = lattice[i]
        if any(c > s for c,s in zip(p, stoichiometric)):
            return bytes(max(c-s, 0) for c,s in zip(p, stoichiometric))
        if all(c == s for c,s in zip(p, stoichiometric)):
            #return stoichiometric
            if all(all(c == s for c,s in zip(lattice[i], stoichiometric)) \
                   for i in range(7, 63, 7)):
                print("bingo!")
                yield self.bingo()
            return None
        yield
        return None


    @coroutine
    def play(self):
        random = self.random
        self.play_on = True
        self.perk_quit = 0
        while self.play_on:
            delay = random.randrange(30,100)
            color = random.choice(((8,0,0), (0,8,0), (0,0,8)))
            yield self.perk(delay, color)
            yield from sleep(random.randrange(200, 300))


