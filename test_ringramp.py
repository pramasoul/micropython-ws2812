import unittest
import gc
from ws2812 import WS2812
from lights import Lights
from ringramp import RingRamp

# A helper
def tg(led_count, start):

    def triple(n):
        for i in range(3):
            yield (n + i) & 0xff

    for i in range(led_count):
        yield triple(start + 3*i)


class RingRampTestCase(unittest.TestCase):
    def setUp(self):
        #logging.basicConfig(level=logging.INFO)
        ws = self.ws = WS2812(1, 8)
        lights = self.lights = Lights(ws)

        # Fill the lattice with a recognizable pattern
        for i, p in enumerate(tg(len(lights), 0)):
            lat = lights.lattice[i]
            for j, c in enumerate(p):
                lat[j] = c

        # The leds are all clear
        self.assertEqual(sum(sum(c) for c in ws), 0)

        self.rr = RingRamp(leds=lights.leds,
                    lattice=lights.lattice,
                    indexed_range=lights.indexed_range)


    def tearDown(self):
        self.ws = self.lights = None
        gc.collect()


    def test_RingRamp_length(self):
        # It has the correct length
        self.assertEqual(len(self.rr), 8)

    def test_RingRamp_slice(self):
        # A rr can be sliced
        rr3 = self.rr[3:6]
        self.assertTrue(isinstance(rr3, RingRamp), type(rr3))
        self.assertEqual(len(rr3), 3)

        # A sliced rr gives the correct lattice points
        for a, b in zip(rr3, self.lights.lattice[3:6]):
            self.assertIs(a, b)
        
    def test_RingRamp_coloring(self):
        # A rr can be colored
        rr3 = self.rr[3:6]
        coloring = [(110, 120, 130), (140, 150, 160), (170, 180, 190)]
        for i in range(len(rr3)):
            rr3[i] = coloring[i]
        for i in range(len(rr3)):
            self.assertEqual(tuple(rr3[i]), coloring[i])

    def test_RingRamp_rendering(self):
        # A rr renders correctly for default brightness=1.0
        ws = self.ws
        rr = self.rr
        # FIXME
        return


        coloring = [(110, 120, 130), (140, 150, 160), (170, 180, 190)]
        for i in range(len(rr3)):
            rr3[i] = coloring[i]
        rr3.render()
        for i in range(len(rr3)):
            self.assertEqual(tuple(ws[i+3]), coloring[i])

        # A rr renders correctly for brightness=0.1
        rr3.brightness = 0.1
        rr3.render()
        for i in range(len(rr3)):
            self.assertEqual(tuple(ws[i+3]), tuple(v/10 for v in coloring[i]))




def main():
    unittest.main()
    return
    # Burn-in test:
    while True:
        try:
            unittest.main()
        except MemoryError as e:
            #print("MemoryError:", e)
            pyb.info()
            raise

if __name__ == '__main__':
    main()
        
