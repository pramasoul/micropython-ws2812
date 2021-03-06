import unittest
import gc
from ws2812 import WS2812, Pixel, PREALLOCATE, CACHE, RECREATE
from wslice import WSlice

# A helper
def tg(led_count, start):

    def triple(n):
        for i in range(3):
            yield (n + i) & 0xff

    for i in range(led_count):
        yield triple(start + 3*i)


class WSliceTestCase(unittest.TestCase):
    names = """Attrs PixelAccess Rotate RotateInset RotatePart""".split()
    names = """Attrs RotatePart""".split()

    def setUp(self):
        #logging.basicConfig(level=logging.INFO)
        gc.collect()
        #random.seed("WSlice")

    def tearDown(self):
        pass

    #@unittest.skip("x")
    def testAllMemoryStrategies(self):
        print()
        for mem in (PREALLOCATE, CACHE, RECREATE):
            for name in self.names:
                fun = getattr(self, 'doTest'+name)
                print("\tdoTest%s(mem==%d) ... " % (name, mem), end='')
                try:
                    gc.collect()
                    fun(mem)
                except:
                    print("Fail:", name, "with mem =", mem)
                    raise
                else:
                    print("ok")


    def doTestAttrs(self, mem):
        # A WSlice attributes have expected values
        ws = WS2812(spi_bus=1, led_count=7, mem=mem)
        ws.fill_buf(tg(len(ws), 0))
        leds = WSlice(ws, 2, 4)
        self.assertEqual(leds.buf, ws.buf[12*2:12*4])


    def doTestPixelAccess(self, mem):
        # A WSlice gives a view into the underlying WS2912
        ws = WS2812(spi_bus=1, led_count=99, mem=mem)
        ws.fill_buf(tg(len(ws), 0))
        
        # A simple slice has the correct length
        leds = WSlice(ws, 3, 6)
        #print("ws:", ws[:8], "...")
        #print("leds:", leds[:])
        self.assertEqual(len(leds), 3)

        # A simple slice has the correct values
        self.assertEqual([tuple(led) for led in leds],
                         [tuple(v) for v in tg(len(leds), 3*3)])

        # The end can be negative, with correct slice behavior
        leds = WSlice(ws, len(ws)-5, -2)
        self.assertEqual(len(leds), 3)
        self.assertEqual([tuple(led) for led in leds],
                         [tuple(v) for v in tg(len(leds), 3*(len(ws)-5))])

        # The start and end can be negative, with correct slice behavior
        leds = WSlice(ws, 3 - len(ws), 6 - len(ws))
        self.assertEqual(len(leds), 3)
        self.assertEqual([tuple(led) for led in leds],
                         [tuple(v) for v in tg(len(leds), 3*3)])

        # The start can be negative, with correct slice behavior
        leds = WSlice(ws, 3 - len(ws), 6)
        self.assertEqual(len(leds), 3)
        self.assertEqual([tuple(led) for led in leds],
                         [tuple(v) for v in tg(len(leds), 3*3)])

        # These are true for multiple test values
        for n in (1, 2, 7, 16, 33, 70):
            leds = WSlice(ws, n, n+5)
            self.assertEqual(len(leds), 5)
            self.assertTrue(all(v==r) for v, r in \
                            zip(tuple(led) for led in leds,
                                tuple(v) for v in tg(len(leds), 3*n)))

            leds = WSlice(ws, len(ws)-(n+5), -n)
            self.assertEqual(len(leds), 5)
            self.assertTrue(all(v==r) for v, r in \
                            zip(tuple(led) for led in leds,
                                tuple(v) for v in tg(len(leds), 3*(len(ws)-(n+5)))))

            leds = WSlice(ws, -(n+5), -n)
            self.assertEqual(len(leds), 5)
            self.assertTrue(all(v==r) for v, r in \
                            zip(tuple(led) for led in leds,
                                tuple(v) for v in tg(len(leds), 3*(len(ws)-(n+5)))))

            leds = WSlice(ws, -(n+5), len(ws)-n)
            self.assertEqual(len(leds), 5)
            self.assertTrue(all(v==r) for v, r in \
                            zip(tuple(led) for led in leds,
                                tuple(v) for v in tg(len(leds), 3*(len(ws)-(n+5)))))



    def doTestRotate(self, mem):
        # A whole WSlice can be rotated
        ws = WS2812(spi_bus=1, led_count=75, mem=mem)
        for n in (1, 2, 7, 16, 33, 70):#, 190, 244, 400):
            leds = None
            t = None
            gc.collect()
            leds = WSlice(ws, 0, n)
            ws.fill_buf(tg(n, 0))
            ref = list(tuple(t) for t in tg(n, 0))
            self.assertTrue(all(tuple(leds[i]) == ref[i] for i in range(len(leds))))
            for k in range(n):
                leds.cw()
                self.assertTrue(all(tuple(leds[i]) == ref[(k+1+i)%n] for i in range(n)))
            for k in range(n):
                leds.ccw()
                self.assertTrue(all(tuple(leds[i]) == ref[(-(k+1)+i)%n] for i in range(n)))

                
    def doTestRotateInset(self, mem):
        # A WSlice that starts past the beginning of the underlying WS2812 can be rotated
        ws = WS2812(spi_bus=1, led_count=7, mem=mem)
        for i in range(len(ws)):
            ws[i] = b'foo'
        self.assertTrue(all(bytes(ws[i]) == b'foo' for i in range(len(ws))))
        leds = WSlice(ws, 2, 5)
        n = len(leds)
        for i, t in zip(range(n), tg(n,0)):
            leds[i] = t
        self.assertEqual([tuple(led) for led in leds], [(0,1,2), (3,4,5), (6,7,8)])
        self.assertTrue(all(bytes(ws[i]) == b'foo' for i in range(len(ws)) if i not in range(2,5)))
        leds.cw()
        self.assertEqual([tuple(led) for led in leds], [(3,4,5), (6,7,8), (0,1,2)])
        self.assertTrue(all(bytes(ws[i]) == b'foo' for i in range(len(ws)) if i not in range(2,5)))
        leds.cw()
        self.assertEqual([tuple(led) for led in leds], [(6,7,8), (0,1,2), (3,4,5)])
        self.assertTrue(all(bytes(ws[i]) == b'foo' for i in range(len(ws)) if i not in range(2,5)))
        leds.cw()
        self.assertEqual([tuple(led) for led in leds], [(0,1,2), (3,4,5), (6,7,8)])
        self.assertTrue(all(bytes(ws[i]) == b'foo' for i in range(len(ws)) if i not in range(2,5)))
        leds.ccw()
        self.assertEqual([tuple(led) for led in leds], [(6,7,8), (0,1,2), (3,4,5)])
        self.assertTrue(all(bytes(ws[i]) == b'foo' for i in range(len(ws)) if i not in range(2,5)))
        leds.ccw()
        self.assertEqual([tuple(led) for led in leds], [(3,4,5), (6,7,8), (0,1,2)])
        self.assertTrue(all(bytes(ws[i]) == b'foo' for i in range(len(ws)) if i not in range(2,5)))
        leds.ccw()
        self.assertEqual([tuple(led) for led in leds], [(0,1,2), (3,4,5), (6,7,8)])
        self.assertTrue(all(bytes(ws[i]) == b'foo' for i in range(len(ws)) if i not in range(2,5)))
        ws = WS2812(spi_bus=1, led_count=90, mem=mem)
        for n in (1, 2, 7, 16, 33, 70):#, 190, 244, 400):
            leds = ref = None
            gc.collect()
            leds_start = n//7
            leds_end = n + n//7
            leds = WSlice(ws, leds_start, leds_end)
            self.assertEqual(len(leds), n)
            for i, t in enumerate(tg(n,0)):
                leds[i] = t
            ref = list(tuple(leds[i]) for i in range(n))
            #print("\n\nstart %d, end %d" % (leds_start, leds_end))
            #print("ref", ref)
            #print("leds", leds[:])
            for k in range(n):
                #print("\nk", k, "leds", leds[:])
                #print("leds before cw:", [tuple(leds[i]) for i in range(n)])
                leds.cw()
                #print(" leds after cw:", [tuple(leds[i]) for i in range(n)])
                #print("ref:", [ref[(k+1+i)%n] for i in range(n)])
                self.assertTrue(all(tuple(leds[i]) == ref[(k+1+i)%n] for i in range(n)))
            for k in range(n):
                leds.ccw()
                self.assertTrue(all(tuple(leds[i]) == ref[(-(k+1)+i)%n] for i in range(n)))


    def doTestRotatePart(self, mem):
        # Some part of a WSlice that starts past the beginning of the
        # underlying WS2812 can be rotated
        ws = WS2812(spi_bus=1, led_count=8, mem=mem)
        for i in range(len(ws)):
            ws[i] = b'foo'
        self.assertTrue(all(bytes(ws[i]) == b'foo' for i in range(len(ws))))
        leds = WSlice(ws, 2, 6)
        n = len(leds)
        for i, t in zip(range(n), tg(n,0)):
            leds[i] = t
        self.assertTrue(all(bytes(ws[i]) == b'foo' for i in range(len(ws)) if i not in range(2,6)))
        self.assertEqual([tuple(led) for led in leds], [(0,1,2), (3,4,5), (6,7,8), (9,10,11)])
        leds.cw(1)
        self.assertTrue(all(bytes(ws[i]) == b'foo' for i in range(len(ws)) if i not in range(2,6)))
        self.assertEqual([tuple(led) for led in leds], [(0,1,2), (6,7,8), (9,10,11), (3,4,5)])
        leds.cw(1)
        self.assertTrue(all(bytes(ws[i]) == b'foo' for i in range(len(ws)) if i not in range(2,6)))
        self.assertEqual([tuple(led) for led in leds], [(0,1,2), (9,10,11), (3,4,5), (6,7,8)])
        leds.cw(1)
        self.assertTrue(all(bytes(ws[i]) == b'foo' for i in range(len(ws)) if i not in range(2,6)))
        self.assertEqual([tuple(led) for led in leds], [(0,1,2), (3,4,5), (6,7,8), (9,10,11)])
        leds.ccw(1)
        self.assertTrue(all(bytes(ws[i]) == b'foo' for i in range(len(ws)) if i not in range(2,6)))
        self.assertEqual([tuple(led) for led in leds], [(0,1,2), (9,10,11), (3,4,5), (6,7,8)])
        leds.ccw(1)
        self.assertTrue(all(bytes(ws[i]) == b'foo' for i in range(len(ws)) if i not in range(2,6)))
        self.assertEqual([tuple(led) for led in leds], [(0,1,2), (6,7,8), (9,10,11), (3,4,5)])
        leds.ccw(1)
        self.assertTrue(all(bytes(ws[i]) == b'foo' for i in range(len(ws)) if i not in range(2,6)))
        self.assertEqual([tuple(led) for led in leds], [(0,1,2), (3,4,5), (6,7,8), (9,10,11)])


    @unittest.skip("FIXME: blows memory")
    def testRotatePlaces(self):
        # A chain can be rotated
        for n in range(1, 400, 19):
            leds = None
            gc.collect()
            leds = WS2812(spi_bus=1, led_count=n)
            leds.fill_buf(tg(n, 1))
            for j in range(0, n, (n//7)+1):
                gc.collect()
                for pix, pg in zip(leds, tg(n, 1)):
                    self.assertEqual(list(pix), list(pg))
                #pixlist = list(list(pix) for pix in leds)
                #rpixlist = pixlist[-j:] + pixlist[:-j]
                leds.rotate_places(j)
                gc.collect()
                #self.assertEqual(list(list(pix) for pix in leds), rpixlist)
                leds.rotate_places(-j)


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
        
