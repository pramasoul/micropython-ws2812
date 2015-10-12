# playback for WS2812 recording

#from collections import namedtuple

from pyb import _little_endian_int

class SPIRecording:
    #SPIWrite = namedtuple('SPIWrite', 'ts', 'values')
    def __init__(self, inf):
        self.inf = inf

    def __iter__(self):
        return self

    def __next__(self):
        inf = self.inf
        rlen_bytes = inf.read(2)
        time_bytes = inf.read(8)
        if len(time_bytes) != 8:
            raise StopIteration
        rlen = _little_endian_int(rlen_bytes)
        ts = _little_endian_int(time_bytes) / 1000000
        val_bytes = inf.read(rlen - 8)
        if len(val_bytes) != rlen - 8:
            raise StopIteration
        return ts, val_bytes


class WS2812Recording(SPIRecording):

    def __next__(self):
        ts, data = SPIRecording.__next__(self)
        n = len(data) // (3*4)
        colors = [(data[3*4*i+1],
                   data[3*4*i+0],
                   data[3*4*i+2]) for i in range(n)]
        return ts, colors


def main(argv):
    with open(argv[1], 'rb') as inf:
        spi_rec = WS2812Recording(inf)
        for ts, colors in spi_rec:
            print(ts, colors)
    

if __name__ == '__main__':
    import sys
    main(sys.argv)
