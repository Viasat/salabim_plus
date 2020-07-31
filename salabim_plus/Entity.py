import salabim as sim

class Entity(sim.Component):
    """
    Entity object
    """
    
    def __init__(self, *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        
        self._activity_done = sim.State(name=self.name()+'_activity_done')
        self._routing_done = sim.State(name=self.name()+'_routing_done')
        self._activity = None
        
    def b_enter(self, b):
        
        self.enter(b._q)
        b._txn.trigger(max=1)
        yield self.wait(b._txn_done)
        self._routing_done.trigger(max=1)
        
    def b_leave(self, b):
        
        self.leave(b._q)
        b._txn.trigger(max=1)
        yield self.wait(b._txn_done)
        self._routing_done.trigger(max=1)