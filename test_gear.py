import unittest
import gc
from ws2812 import WS2812
from lights import Lights
from gear import Gear

# A helper
def tg(led_count, start):

    def triple(n):
        for i in range(3):
            yield (n + i) & 0xff

    for i in range(led_count):
        yield triple(start + 3*i)


class GearTestCase(unittest.TestCase):
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

        self.gear = Gear(lights=lights)


    def tearDown(self):
        self.ws = self.lights = None
        gc.collect()


    def test_Gear_length(self):
        # It has the correct length
        self.assertEqual(len(self.gear), 8)

    def test_Gear_slice_rval(self):
        # A sliced gear can be an rval
        g3 = self.gear[3:6]
        self.assertTrue(isinstance(g3, Gear), type(g3))
        self.assertEqual(len(g3), 3)

        # A sliced gear gives the correct lattice points
        for a, b in zip(g3, self.lights.lattice[3:6]):
            self.assertIs(a, b)
        
    def test_Gear_slice_lval(self):
        # An indexed gear can be an lval
        g3 = self.gear[3:6]
        g3[0] = (7, 11, 13)
        self.assertEqual(g3[0], bytearray([7, 11, 13]))

        # With a slice index as well
#        g3[1:2] = [(17, 19, 23), (29, 31, 37), (41, 43, 47)]
        g3[1:3] = [(17, 19, 23), (29, 31, 37)]

        # And read back
        self.assertEqual([tuple(v) for v in g3],
                         [(7, 11, 13), (17, 19, 23), (29, 31, 37)])

        # With a generator
        g3[:] = tg(10, 50)      # which can be willing to run over
        self.assertEqual([p for p in g3],
                         [bytearray(c) for c in tg(3, 50)])


    def test_Gear_coloring(self):
        # A gear can be colored
        g3 = self.gear[3:6]
        coloring = [(110, 120, 130), (140, 150, 160), (170, 180, 190)]
        for i in range(len(g3)):
            g3[i] = coloring[i]
        for i in range(len(g3)):
            self.assertEqual(tuple(g3[i]), coloring[i])

    def test_Gear_rendering(self):
        # A gear renders correctly for default brightness=1.0
        ws = self.ws
        g3 = self.gear[3:6]
        coloring = [(110, 120, 130), (140, 150, 160), (170, 180, 190)]
        for i in range(len(g3)):
            g3[i] = coloring[i]
        g3.render()
        for i in range(len(g3)):
            self.assertEqual(tuple(ws[i+3]), coloring[i])

        # A gear renders correctly for brightness=0.1
        g3.brightness = 0.1
        g3.render()
        for i in range(len(g3)):
            self.assertEqual(tuple(ws[i+3]), tuple(v/10 for v in coloring[i]))

    #@unittest.skip("x")
    def test_Gear_rotation(self):
        # A gear can be rotated
        ws = self.ws
        g3 = self.gear[3:6]
        coloring = [(110, 120, 130), (140, 150, 160), (170, 180, 190)]
        for i in range(len(g3)):
            g3[i] = coloring[i]
        g3.cw()
        g3.render()
        self.assertEqual([tuple(ws[i+3]) for i in range(len(g3))],
                         [tuple(v for v in coloring[(i+1)%len(g3)]) for i in range(len(g3))])
        g3.cw()
        g3.render()
        self.assertEqual([tuple(ws[i+3]) for i in range(len(g3))],
                         [tuple(v for v in coloring[(i+2)%len(g3)]) for i in range(len(g3))])
        g3.cw()
        g3.render()
        self.assertEqual([tuple(ws[i+3]) for i in range(len(g3))],
                         [tuple(v for v in coloring[(i)%len(g3)]) for i in range(len(g3))])
        g3.ccw()
        g3.render()
        self.assertEqual([tuple(ws[i+3]) for i in range(len(g3))],
                         [tuple(v for v in coloring[(i+2)%len(g3)]) for i in range(len(g3))])
        g3.ccw()
        g3.render()
        self.assertEqual([tuple(ws[i+3]) for i in range(len(g3))],
                         [tuple(v for v in coloring[(i+1)%len(g3)]) for i in range(len(g3))])
        g3.ccw()
        g3.render()
        self.assertEqual([tuple(ws[i+3]) for i in range(len(g3))],
                         [tuple(v for v in coloring[(i)%len(g3)]) for i in range(len(g3))])


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
        
