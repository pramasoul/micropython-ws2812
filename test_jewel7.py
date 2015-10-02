import unittest
import gc
from ws2812 import WS2812
from lights import Lights
from jewel7 import Jewel7
from gear import Gear

# A helper
def tg(led_count, start):

    def triple(n):
        for i in range(3):
            yield (n + i) & 0xff

    for i in range(led_count):
        yield triple(start + 3*i)


class Jewel7TestCase(unittest.TestCase):
    def setUp(self):
        #logging.basicConfig(level=logging.INFO)
        ws = self.ws = WS2812(1, 10)
        lights = self.lights = Lights(ws)

        # Fill the lattice with a recognizable pattern
        for i, p in enumerate(tg(len(lights), 0)):
            lat = lights.lattice[i]
            for j, c in enumerate(p):
                lat[j] = c

        # The leds are all clear
        self.assertEqual(sum(sum(c) for c in ws), 0)

        self.jewel7 = Jewel7(lights=lights[1:]) # intentionally too long

    def tearDown(self):
        self.ws = self.lights = None
        gc.collect()


    def test_Jewel7_length(self):
        # It has the correct length
        self.assertEqual(len(self.jewel7), 7)

    def test_Jewel7_center(self):
        j7 = self.jewel7
        # It has a center
        self.assertTrue(hasattr(j7, 'center'))

        # The correct one
        self.assertIs(j7.center, self.lights[1])

        # Center can be written
        j7.center[0] = 7
        j7.center[1] = 9
        j7.center[2] = 11
        with self.assertRaises(IndexError):
            j7.center[3] = 13

        # Center can be replaced
        j7.center = (15, 17, 3.1416)
        self.assertEqual(j7.center, (15, 17, 3.1416))

    def test_Jewel7_gear(self):
        jewel7 = self.jewel7
        # It has a Gear
        self.assertTrue(hasattr(jewel7, 'gear'))
        gear = jewel7.gear
        self.assertTrue(isinstance(gear, Gear))
        
        # Gear has six lattice points
        self.assertEqual(len(gear), 6)


    def test_Jewel7_rendering(self):
        # A jewel7 renders correctly for default brightness=1.0
        ws = self.ws
        lights = self.lights
        j7 = self.jewel7

        j7.center = (100, 101, 102)
        j7.gear[:] = tg(6, 55)

        #Wrong expect = [tuple(c) for c in tg(len(lights), 0)]
        expect = [(0,)*3 for i in range(len(lights))]
        expect[1] = tuple(v for v in j7.center)
        # FAILS with huge memory allocation error expect[2:8] = (tuple(c) for c in tg(6, 55)
        expect[2:8] = list(tuple(c) for c in tg(6, 55))

        # LEDs all dark before render
        self.assertEqual(list(tuple(led) for led in ws), [tuple([0]*3)]*len(ws))

        # Lights as expected before render
        # IRRELEVANT self.assertEqual(list(tuple(p) for p in lights), expect)

        # Default brightness is 1.0
        self.assertEqual(j7.brightness, 1.0)

        # It can render
        j7.render()

        # LEDs as expected
        self.assertEqual(list(tuple(led) for led in ws), expect)

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
        
