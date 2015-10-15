# playback for WS2812 recording

#from collections import namedtuple
import pdb
import subprocess
import sys

from pprint import pprint
from PIL import Image, ImageDraw, ImageFilter

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
        colors = [(data[3*i+1],
                   data[3*i+0],
                   data[3*i+2]) for i in range(n)]
        return ts, colors


class MovieFrames:
    def __init__(self, fps=30, start=0, stop=None, dimensions=(512,512),
                 dot_radius=8 ):
        self.fps = fps
        self.start = start
        self.stop = stop
        self.dimensions = dimensions
        self.dot_radius = dot_radius
        xdim = dimensions[0]
        ydim = dimensions[1]
        dx = 28
        dy = 28
        self.positions = [(dx//2 + dx*(i%8),
                           dy//2 + dy*(i//8)) for i in range(64)]

    def __iter__(self):
        return self.frames()

    def frames(self):
        rv = Image.new('RGB', self.dimensions)
        d = ImageDraw.Draw(rv)
        r = self.dot_radius
        for positions, colors in self.leds():
            for pos, color in zip(positions, colors):
                if not color:
                    continue
                x, y = pos
                d.ellipse((x-r, y-r, x+r, y+r), color)
            #rv = rv.filter(ImageFilter.GaussianBlur(3))
            #return rv
            yield rv


    def ff_colors(self):
        prev = None
        for rec in self.recording:
            if prev:
                yield (rec[0]-prev[0])*self.fps, prev[1]
            prev = rec

    def frame_color_sets(self):
        # yields sets of colors that apply to each frame in succession,
        # with weightings
        frame_frac = 0
        rv = []
        for ff, colors in self.ff_colors():
            while ff + frame_frac >= 1:
                fraction_to_finish_frame = 1 - frame_frac
                rv.append([fraction_to_finish_frame, colors])
                yield rv
                rv = []
                frame_frac = 0
                ff -= fraction_to_finish_frame
            rv.append([ff, colors])
            frame_frac += ff


    def leds(self):
        mul_svot = self._mul_svot
        n = 0
        for fcs in self.frame_color_sets():
            assert sum(v[0] for v in fcs) == 1
            #if len(fcs) > 1:
            #    print([v[0] for v in fcs])
            if len(fcs) == 1:
                colors= fcs[0][1]
            else:
                #print([v[0] for v in fcs])
                t = zip(*[mul_svot(v[0], v[1]) for v in fcs])
                colors = list(tuple(round(sum(b)) for b in zip(*a)) for a in t)
            yield self.positions, colors
            n += 1
        #print('**************** %d frames' % n)
            
    def _mul_svot(self, scalar, vector_of_tuples):
        return [[scalar * vi for vi in tuple] for tuple in vector_of_tuples]


class MovieMaker:
    def __init__(self, frames):
        self.frames = frames
        
    def make(self):
        command = [ 'ffmpeg',
                    '-y', # (optional) overwrite output file if it exists
                    '-f', 'rawvideo',
#                    '-vcodec','rawvideo',
                    '-s', '512x512', # size of one frame
                    '-pix_fmt', 'rgb24',
                    '-r', '30', # frames per second
                    '-i', '-', # The imput comes from a pipe
                    '-an', # Tells FFMPEG not to expect any audio
                    '-vcodec', 'libx264',
                    # slower than PIL gaussian:
                    #'-filter', "fftfilt=dc_Y=0:weight_Y='squish((Y+X)/100-1)'",
                   't.mov' ]
        encoder = subprocess.Popen(command,
                                   stdin=subprocess.PIPE)
        for frame in self.frames:
            encoder.stdin.write(frame.tobytes())
        encoder.stdin.close()
        

def main(argv):
    mf = MovieFrames()
    with open(argv[1], 'rb') as inf:
        spi_rec = WS2812Recording(inf)
        mf.recording = spi_rec
        #print(mf.positions)
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
