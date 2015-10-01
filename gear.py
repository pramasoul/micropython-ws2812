from lights import Lights

class Gear(Lights):
    # A gear has a pattern and a phase (in units of "teeth",
    # i.e. lattice points)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.phase = 0

    def cw(self, n=1):
        self.phase = (self.phase + n) % len(self)

    def ccw(self, n=1):
        self.phase = (self.phase - n) % len(self)

    def model_colors(self):
        start = round(self.phase) % len(self)
        lattice = self.lattice
        for i in self.indexed_range[start:]:
            yield lattice[i]
        for i in self.indexed_range[:start]:
            yield lattice[i]

