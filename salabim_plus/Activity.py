import salabim as sim
import salabim_plus as simx
import numpy as np

class Activity(sim.Component):
    
    def setup(
        self,
#         process_func,
        time,
        process_cap=1,
        in_buffer_cap=np.inf,
        out_buffer_cap=np.inf,
        in_unbatch=False,
        in_batch_qty=1,
        out_unbatch=True,
        out_batch_qty=None
    ):
        
#         self.process_func = process_func
        self.time = time
        self.in_unbatch = in_unbatch
        self.in_batch_qty = in_batch_qty
        self.out_unbatch = out_unbatch
        self.out_batch_qty = out_batch_qty
        
        self._in_buffer = simx.Buffer(activity=self, buffer_type='in', cap=in_buffer_cap)
        self._in_buffer.activate()
        self._to_process = simx.Buffer(activity=self, buffer_type='to_process', cap=1)
#         self._start_staging = Buffer(activity=self, buffer_type='start_staging', cap=1)
        self._processing = simx.Buffer(activity=self, buffer_type='processing', cap=process_cap)
        self._complete = simx.Buffer(activity=self, buffer_type='complete')
        self._out_buffer = simx.Buffer(activity=self, buffer_type='out', cap=out_buffer_cap)
        
        self._in_gate = simx.Gate(activity=self, gate_type='in', )
        self._process_gate = simx.Gate(activity=self, gate_type='process')
        self._out_gate = simx.Gate(activity=self, gate_type='out')
#         self._start_process = sim.State(name=self.name()+'_start_process')
        
#     def process(self):
        
#         while True:
#             yield self.wait((self._start_staging._lvl, self._start_staging.has_one))
            
#             tmp = self._start_staging.pop()
#             tmp.time = self.time
#             tmp._activity = self
            
#             tmp.activate(process='activity')