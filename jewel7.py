from lights import Lights
from gear import Gear

class Jewel7(Lights):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.indexed_range = self.indexed_range[:7]
        self.center = self.lattice[self.indexed_range[0]]
        self.gear = Gear(lights=self, indexed_range=self.indexed_range[1:7])
        
    def model_colors(self):
        yield self.center
        yield from self.gear.model_colors()

