import salabim as sim

class Entity(sim.Component):
    
    def __init__(self):
        
        super().__init__()
        
        self._activity_done = sim.State(name=self.name()+'_activity_done')
        
    # def activity(self):
        
    #     yield self.hold(self.time)
    #     self.exit(self._activity._processing._q)
    #     self.enter(self._activity._complete._q)
        
    def b_enter(self, b):
        
        self.enter(b._q)
        b._txn.trigger()
        yield self.wait(b._txn_done)
        
    def b_leave(self, b):
        
        self.leave(b._q)
        b._txn.trigger()
        yield self.wait(b._txn_done)