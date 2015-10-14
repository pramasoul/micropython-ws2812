# playback for WS2812 recording

#from collections import namedtuple
import pdb
import subprocess

from PIL import Image, ImageDraw

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


class MovieFrames:
    def __init__(self, fps=30, start=0, stop=None, dimensions=(512,512),
                 dot_radius=4):
        self.fps = fps
        self.start = start
        self.stop = stop
        self.dimensions = dimensions
        self.dot_radius = dot_radius
        xdim = dimensions[0]
        ydim = dimensions[1]
        dx = 32
        dy = 32
        self.positions = [((dx*i + dx//2)%xdim, (dx*i + dx//2)//xdim * dy + dy//2) \
                          for i in range(64)]

    def __iter__(self):
        return self

    def __next__(self):
        rv = Image.new('RGB', self.dimensions)
        d = ImageDraw.Draw(rv)
        r = self.dot_radius
        t = self.leds()
        if t is None:
            raise StopIteration
        #print(t)
        positions, (ts, colors) = t
        for pos, color in zip(positions, colors):
            x, y = pos
            d.ellipse((x-r, y-r, x+r, y+r), color)
        return rv

    def leds(self):
        try:
            return self.positions, next(self.recording)
        except StopIteration:
            return None


class MovieMaker:
    def __init__(self, frames):
        self.frames = frames
        
    def make(self):
        command = [ 'ffmpeg',
                    '-y', # (optional) overwrite output file if it exists
                    '-f', 'rawvideo',
                    '-vcodec','rawvideo',
                    '-s', '512x512', # size of one frame
                    '-pix_fmt', 'rgb24',
                    '-r', '10', # frames per second
                    '-i', '-', # The imput comes from a pipe
                    '-an', # Tells FFMPEG not to expect any audio
                    '-vcodec', 'libx264',
                    't.mov' ]
        encoder = subprocess.Popen(command,
                                   stdin=subprocess.PIPE)
                                #stderr=subprocess.PIPE)
        for frame in self.frames:
            #print(frame)
            #rlist, wlist, xlist = select.select([pipe.proc.stderr
            encoder.stdin.write(frame.tobytes())
        encoder.stdin.close()
        

def main(argv):
    mf = MovieFrames()
    with open(argv[1], 'rb') as inf:
        spi_rec = WS2812Recording(inf)
        mf.recording = spi_rec
        print(mf.positions)
        #for i, frame in enumerate(mf):
        #    print(i, end=' ')
        #    frame.save('frame{:06}.png'.format(i))
            #if i == 100:
            #    break
        mm = MovieMaker(mf)
        mm.make()
    

if __name__ == '__main__':
    import sys
    main(sys.argv)
