import salabim as sim

class Gate(sim.Component):
    
    def __init__(self, activity, gate_type, batch_type=None, batch_size=None, *args, **kwargs):
        
        self.activity = activity
        self.gate_type = gate_type
        self.batch_type = batch_type
        self.batch_size = batch_size
        self.on_move = []
        
        name = '_'.join([activity.name(), gate_type, 'gate'])
        super().__init__(name=name, *args, **kwargs)
        
    def setup(self):
        
        if self.gate_type == 'in':
            self.ingress = self.activity._in_buffer
            self.egress = self.activity._to_process
            
        elif self.gate_type == 'out':
            self.ingress = self.activity._complete
            self.egress = self.activity._out_buffer
            
        elif self.gate_type == 'process':
            self.ingress = self.activity._to_process
            self.egress = self.activity._processing
            
        else:
            pass
            # raise InputError("Invalid input give for the gate_type ['in','out','process']")
            
    def process(self):
        
        while True:
            
            if self.egress.is_full():
                yield self.wait((self.egress._is_full, False))
            
            if self.batch_type == 'unbatch':
                yield self.wait((self.ingress._lvl, lambda v,c,s: v>0))
                
                yield from self.pull()
                # unbatch
                yield from self.put()
                
            elif self.batch_type == 'batch':
                yield self.wait((self.ingress._lvl, lambda v,c,s: v>self.batch_size))
                
                yield from self.pull()
                # batch(self.batch_size)
                yield from self.put()
                
            else:
                yield from self.pull()
                yield from self.put()
            
            if self.gate_type == 'process':
                self.enter(self.activity._start_staging._q)
                self.activity._start_process.trigger(max=1)

    def pull(self, amt=1):
        
        for _ in range(amt):
            self.on_move.append(self.ingress._q.pop())
#         self.on_move = self.ingress._q.pop()

        self.ingress._txn.trigger()
        yield self.wait(self.ingress._txn_done)
        
    def put(self):
        
        for e in self.on_move:
            e.enter(self.egress._q)
            
        self.egress._txn.trigger()
        yield self.wait(self.egress._txn_done)