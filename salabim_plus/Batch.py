import salabim_plus as simx

class Batch(simx.Entity):
    
    def __init__(self):
        super().__init__()
    
    def setup(self, entities):
        self.contents = entities