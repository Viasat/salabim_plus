import salabim as sim
import salabim_plus as simx
import numpy as np

class Activity(sim.Component):
    """
    Activity object

    Parameters
    ----------
    process_func : func


    process_cap : int
       amount of entities/batches that can be processed simultaneaously.
       default: 1 

    in_buffer_cap : int 
        amount of entities/batches the in_buffer can hold.
        default: np.inf

    out_buffer_cap : int
        amount of entities/batches the out_buffer can hold.
        default: np.inf

    in_batch_type : str 
        type of batching activity during the in_buffer to to_process_buffer 
        gate transfer, if any.
        options: "batch", "unbatch", None
        default: None

        if "batch", activity will wait until specified batch size is 
        accumulated in the in_buffer then bundle the entities/batches into a 
        new batch before moving to to_process_buffer.
        if "unbatch", activity will unpack a batch in the in_buffer and move 
        all of the batch contents individually to the to_process_buffer.
        if None (default), activity will move entities/batches to 
        to_process_buffer as they arrive to the in_buffer.
        
    in_batch_size : int
        number of entities/batches per batch, only applicable when 
        in_batch_type="batch".
        default: None
        
    out_batch_type : str
        type of batching activity during the complete_buffer to out_buffer 
        gate transfer, if any.
        options: "batch", "unbatch", None
        default: None

        if "batch", activity will wait until specified batch size is 
        accumulated in the complete_buffer then bundle the entities/batches 
        into a new batch before moving to to_process_buffer.
        if "unbatch", activity will unpack a batch in the complete_buffer and 
        move all of the batch contents individually to the out_buffer.
        if None (default), activity will move entities/batches to 
        to_process_buffer as they arrive to the in_buffer.

    out_batch_size : int
        number of entities/batches per batch, only applicable when 
        in_batch_type="batch".
        default: None

    animate : bool
        indicator for whether or not to generate the activity animation box.
        default: False

        if True, predefined activity animation box will be created given its 
        x, y, w, h, an_fillcolor, and an_textcolor parameters.
        if False, predefined activity animation box will not be generated.

    x : int
        bottom left pixel x-coordinate for where the activity animation box 
        will be created, only applicable when animate=True.
        default: 0

    y : int
        bottom left pixel y-coordinate for where the activity animation box 
        will be created, only applicable when animate=True.
        default: 0

    w : int
        pixel width of the activity animation box, only applicable when 
        animate=True.
        default: 50

    h : int
        pixel height of the activity animation box, only applicable when 
        animate=True.
        default: 30

    an_fillcolor : str
        activity animation box fillcolor, only applicable when animate=True.
        options: must select string option from original salabim animation colors
        default: "blue"

    an_textcolor : str
        activity animation box textcolor, only applicable when animate=True.
        options: must select string option from original salabim animation colors
        default: "white"
    """
    
    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)
    
    def setup(
        self,
        process_func,
        process_cap=1,
        in_buffer_cap=np.inf,
        out_buffer_cap=np.inf,
        in_batch_type=None,
        in_batch_size=None,
        out_batch_type=None,
        out_batch_size=None,
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
        self.in_batch_type = in_batch_type
        self.in_batch_size = in_batch_size
        self.out_batch_type = out_batch_type
        self.out_batch_size = out_batch_size
        
        # animation specific parameters
        self.animate = animate
        self._x = x
        self._y = y
        self._w = w
        self._h = h
        self._an_fillcolor = an_fillcolor
        self._an_textcolor = an_textcolor
        
        # creating activity buffers 
        self._in_buffer = simx.Buffer(
            activity=self, 
            buffer_type='in', 
            cap=in_buffer_cap
        )
        self._to_process = simx.Buffer(
            activity=self, 
            buffer_type='to_process'
        )
        self._processing = simx.Buffer(
            activity=self, 
            buffer_type='processing', 
            cap=process_cap
        )
        self._complete = simx.Buffer(
            activity=self, 
            buffer_type='complete'
        )
        self._out_buffer = simx.Buffer(
            activity=self, 
            buffer_type='out', 
            cap=out_buffer_cap
        )
        
        # creating activity gates
        self._in_gate = simx.Gate(
            activity=self, 
            gate_type='in', 
            batch_type=in_batch_type, 
            batch_size=in_batch_size
        )
        self._process_gate = simx.Gate(
            activity=self, 
            gate_type='process'
        )
        self._out_gate = simx.Gate(
            activity=self, 
            gate_type='out', 
            batch_type=out_batch_type, 
            batch_size=out_batch_size
        )

        # creating processors and unutilized processor holding area
        self._processor_q = sim.Queue(name=self.name()+'_processor_q')
        for _ in range(process_cap):
            simx.Processor(activity=self)
        
        self._assign_processor = sim.State(
            name=self.name()+'_assign_processor'
        )
        self._processor_assigned = sim.State(
            name=self.name()+'_processor_assigned'
        )
        self._processee_q = sim.Queue(
            name=self.name()+'_processee_q'
        )

        # creating animation if initiated
        self._make_animation()

    def process(self):
        """
        Activity object sim.Component process
        
        it processes an entity/batch when ready, given the defined 
        process_func.
        """

        while True:
            # wait until an entity/batch is ready to be assigned a processor
            yield self.wait(self._assign_processor)

            # assign processor to the entity/batch that is ready
            processor = self._processor_q.pop()
            processor.processee = self._processee_q.pop()
            self._processor_assigned.trigger(max=1)

            # initiate processor to execute its process
            processor.activate(process="activity")

    def _make_animation(self):
        """
        makes the activity animation box 
        """

        if self.animate:
            sim.AnimateRectangle(
                spec=lambda activity, t: (0, 0, activity.w(t), activity.h(t)),
                x=self.x,
                y=self.y,
                xy_anchor="sw",
                fillcolor=self.an_fillcolor,
                text=self.name(),
                textcolor=self.an_textcolor,
                text_anchor="n",
                layer = 1,
                arg = self
            )

    def x(self, t):
        """
        returns the activity animation box x-coordinate at env time t
        """
        return self._x

    def y(self, t):
        """
        returns the activity animation box y-coordinate at env time t
        """
        return self._y

    def h(self, t):
        """
        returns the activity animation box width at env time t
        """
        return self._h

    def w(self, t):
        """
        returns the activity animation box height at env time t
        """
        return self._w

    def an_fillcolor(self, t):
        """
        returns the activity animation box fillcolor at env time t
        """
        return self._an_fillcolor

    def an_textcolor(self, t):
        """
        returns the activity animation box textcolor at env time t
        """
        return self._an_textcolor
