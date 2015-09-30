from lights import Lights
from gear import Gear

class Jewel7(Lights):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.center = self.lattice[self.indexed_range[0]]
        self.gear = Gear(leds=self.leds, timer=self.timer,
                         lattice=self.lattice,
                         indexed_range=self.indexed_range[1:])
        
    def model_colors(self):
        yield self.lattice[0]
        yield from self.gear.model_colors()

