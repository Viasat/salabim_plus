import salabim as sim
import salabim_plus as simx
import numpy as np

class Activity(sim.Component):
    
    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)
    
    def setup(
        self,
        process_func,
        process_cap=1,
        in_buffer_cap=np.inf,
        out_buffer_cap=np.inf,
        in_unbatch=False,
        in_batch_qty=1,
        out_unbatch=True,
        out_batch_qty=None,
        animate=False,
        x=0,
        y=0,
        w=50,
        h=30,
        an_fillcolor="blue",
        an_textcolor="white"
    ):

        # assigning input parameters    
        self.process_func = process_func
        self.process_cap = process_cap
        self.in_unbatch = in_unbatch
        self.in_batch_qty = in_batch_qty
        self.out_unbatch = out_unbatch
        self.out_batch_qty = out_batch_qty
        
        # animation specific parameters
        self.animate = animate
        self._x = x
        self._y = y
        self._w = w
        self._h = h
        self._an_fillcolor = an_fillcolor
        self._an_textcolor = an_textcolor
        
        # creating activity buffers 
        self._in_buffer = simx.Buffer(activity=self, buffer_type='in', cap=in_buffer_cap)
        self._to_process = simx.Buffer(activity=self, buffer_type='to_process')
        self._processing = simx.Buffer(activity=self, buffer_type='processing', cap=process_cap)
        self._complete = simx.Buffer(activity=self, buffer_type='complete')
        self._out_buffer = simx.Buffer(activity=self, buffer_type='out', cap=out_buffer_cap)
        
        # creating activity gates
        self._in_gate = simx.Gate(activity=self, gate_type='in')
        self._process_gate = simx.Gate(activity=self, gate_type='process')
        self._out_gate = simx.Gate(activity=self, gate_type='out')

        # creating processors and unutilized processor holding area
        self._processor_q = sim.Queue(name=self.name()+'_processor_q')
        for _ in range(process_cap):
            simx.Processor(activity=self)
        
        self._assign_processor = sim.State(name=self.name()+'_assign_processor')
        self._processor_assigned = sim.State(name=self.name()+'_processor_assigned')
        self._processee_q = sim.Queue(name=self.name()+'_processee_q')

        # creating animation if initiated
        self._make_animation()

    def process(self):

        while True:
            yield self.wait(self._assign_processor)
            processor = self._processor_q.pop()
            processor.processee = self._processee_q.pop()
            self._processor_assigned.trigger(max=1)
            processor.activate(process="activity")

    def _make_animation(self):

        if self.animate:
            sim.AnimateRectangle(
                spec=(0, 0, self._w, self._h),
                x=self._x,
                y=self._y,
                xy_anchor="nw",
                fillcolor=self.an_fillcolor,
                text=self._name,
                textcolor=self.an_textcolor,
                text_anchor="c",
                arg = self
            )

    def x(self, t):
        return self._x

    def y(self, t):
        return self._y

    def h(self, t):
        return self._h

    def w(self, t):
        return self._w

    def an_fillcolor(self, t):
        return self._an_fillcolor

    def an_textcolor(self, t):
        return self._an_textcolor
