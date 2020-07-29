import salabim_plus as simx

class Batch(simx.Entity):
    
    def __init__(self, *args, **kwargs):

        # name = '_'.join([activity.name(),'batch'])
        # super().__init__(name=name, *args, **kwargs)
        super().__init__(*args, **kwargs)
    
    def setup(self, contents):
        self.contents = contents