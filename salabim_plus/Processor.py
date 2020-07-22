import salabim as sim

class Processor(sim.Component):

    def __init__(self, activity, *args, **kwargs):

        self._activity = activity
        self.processee = None
        
        name = '_'.join([activity.name(),'processor'])
        super().__init__(name=name, *args, **kwargs)

    # def setup(self):
    
    def process(self):

        self.enter(self._activity._processor_q)
        self.passivate()
    
    def activity(self):

        yield from self._activity.process_func(processor=self)
        
        self.processee.leave(self._activity._processing._q)
        self._activity._processing._txn.trigger(max=1)
        yield self.wait(self._activity._processing._txn_done)

        self.processee.enter(self._activity._complete._q)
        self._activity._complete._txn.trigger(max=1)
        yield self.wait(self._activity._complete._txn_done)

        self.processee = None
        self.enter(self._activity._processor_q)
        self.passivate()