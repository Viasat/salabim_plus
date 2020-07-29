import salabim as sim
import salabim_plus as simx

class Gate(sim.Component):
    
    def __init__(self, activity, gate_type, batch_type=None, batch_size=None, *args, **kwargs):
        
        self._activity = activity
        self.gate_type = gate_type
        self.batch_type = batch_type
        self.batch_size = batch_size
        self.on_move = []
        
        name = '_'.join([activity.name(), gate_type, 'gate'])
        super().__init__(name=name, urgent=True, *args, **kwargs)
        
    def setup(self):
        
        if self.gate_type == 'in':
            self.ingress = self._activity._in_buffer
            self.egress = self._activity._to_process
            
        elif self.gate_type == 'out':
            self.ingress = self._activity._complete
            self.egress = self._activity._out_buffer
            
        elif self.gate_type == 'process':
            self.ingress = self._activity._to_process
            self.egress = self._activity._processing
            
        else:
            pass
            # raise InputError("Invalid input give for the gate_type ['in','out','process']")
            
    def process(self):
        
        while True:
            
            if self.egress.is_full():
                yield self.wait((self.egress._is_full, 'NO'))
            
            if self.batch_type == 'unbatch':
                yield self.wait((self.ingress._lvl, lambda v,c,s: v>0))
                
                yield from self.pull()
                self.unbatch()
                yield from self.put()
                
            elif self.batch_type == 'batch':
                yield self.wait((self.ingress._lvl, lambda v,c,s: v>=self.batch_size))
                
                yield from self.pull(amt=self.batch_size)
                self.batch()
                yield from self.put()
                
            else:
                yield self.wait((self.ingress._lvl, lambda v,c,s: v>0))

                yield from self.pull()
                yield from self.put()
            
            if self.gate_type == 'out':
                for e in self.on_move:
                    e._activity_done.trigger(max=1)
                    yield self.wait(e._routing_done)
                # self.on_move[0]._activity_done.trigger(max=1)
            
            elif self.gate_type == 'process':
                self.on_move[0].enter(self._activity._processee_q)
                self._activity._assign_processor.trigger(max=1)
                yield self.wait(self._activity._processor_assigned)

            self.on_move = []

    def batch(self):

        self.on_move = [simx.Batch(contents=self.on_move)]
    
    def unbatch(self):

        tmp = []
        for item in self.on_move[0].contents:
            tmp.append(item)

        self.on_move = tmp

    def pull(self, amt=1):
        
        for _ in range(amt):
            self.on_move.append(self.ingress._q.pop())
#         self.on_move = self.ingress._q.pop()

        self.ingress._txn.trigger(max=1)
        yield self.wait(self.ingress._txn_done)
        
    def put(self):
        
        for e in self.on_move:
            e.enter(self.egress._q)

        self.egress._txn.trigger(max=1)
        yield self.wait(self.egress._txn_done)