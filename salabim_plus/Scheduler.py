import salabim as sim

class Scheduler(sim.Component):

    def __init__(self, xresource, *args, **kwargs):

        # input in xresource name to sim.component
        super().__init__(*args, **kwargs)

    def setup(self):
        pass
        # parameters ...
        # shift_dict
        # shift_type 
        # ...

    def process(self):
        pass
        # methods ...
        # delay, get resource claimers, c.interrupt, c.release, 
        