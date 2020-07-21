import salabim as sim
import numpy as np

class Buffer(sim.Component):
    
    def __init__(self, activity, buffer_type, cap=np.inf, *args, **kwargs):
        
        self.activity = activity
        self.buffer_type = buffer_type
        self.cap = cap
        
        name = '_'.join([activity.name(), buffer_type, 'buffer'])
        super().__init__(name=name, *args, **kwargs)
    
    def setup(self):
        
        self._q = sim.Queue(name=self.name()+'_q')
        self._lvl = sim.State(name=self.name()+'_lvl', value=0)
        self._is_full = sim.State(name=self.name()+'_is_full', value=False)
        self._txn = sim.State(name=self.name()+'_txn')
        self._txn_done = sim.State(name=self.name()+'_txn_done')
    
    def process(self):
        
        while True:
#             yield self.wait((self._lvl, self.txn))
            yield self.wait(self._txn)
            self._lvl.set(len(self._q))
            self.check_is_full()
            self._txn_done.trigger()
    
    def is_full(self):
        return self._is_full.value()
    
    def lvl(self):
        return self._lvl.value()
    
    def txn(self):
        return self._txn.value()
    
    def has_one(self, x):
        v, c, s = x
        return v > 0
    
    def check_is_full(self):
        
        if self.is_full():
            if self.lvl() < self.cap:
                self._is_full.set(False)
            
        else:
            if self.lvl() >= self.cap:
                self._is_full.set(True) 