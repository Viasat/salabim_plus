import salabim as sim
import numpy as np

class Buffer(sim.Component):
    
    def __init__(self, activity, buffer_type, cap=np.inf, *args, **kwargs):
        
        self._activity = activity
        self.buffer_type = buffer_type
        self.cap = cap
        
        name = '_'.join([activity.name(), buffer_type, 'buffer'])
        super().__init__(name=name, *args, **kwargs)
    
    def setup(self):
        
        self._q = sim.Queue(name=self.name()+'_q')
        self._lvl = sim.State(name=self.name()+'_lvl', value=0)
        self._is_full = sim.State(name=self.name()+'_is_full', value='NO')
        self._txn = sim.State(name=self.name()+'_txn')
        self._txn_done = sim.State(name=self.name()+'_txn_done')

        self._make_animation()
    
    def process(self):
        
        while True:
            yield self.wait(self._txn)
            self._lvl.set(len(self._q))
            self.check_is_full()
            self._txn_done.trigger(max=1)
            self._make_animation()
    
    def is_full(self):
        return self._is_full.value()
    
    def lvl(self):
        return self._lvl.value()
    
    def txn(self):
        return self._txn.value()
    
    def has_one(self, x):
        v, c, s = x
        return v > 0

    def _make_animation(self):

        if self._activity.animate:
            print(f'buffer test {self._activity.name()} {self.buffer_type}')

            x, y, text_anchor = self._get_an_xy()

            if self.is_full() == 'YES':
                textcolor = "red"
            else:
                textcolor = self._activity.textcolor

            sim.AnimateText(
                text=str(self.lvl()),
                x = x,
                y = y,
                text_anchor = text_anchor,
                textcolor = textcolor,
                arg = self
                # parent = self
            )

    def _get_an_xy(self):

        if self.buffer_type == 'in':
            x = self._activity.x + self._activity.w*0.1
            y = self._activity.y - self._activity.h*0.1
            text_anchor = "nw"

        elif self.buffer_type == 'to_process':
            x = self._activity.x + self._activity.w*0.1
            y = self._activity.y + self._activity.h - self._activity.h*0.1
            text_anchor = "sw"

        elif self.buffer_type == 'processing':
            x = self._activity.x + self._activity.w*0.5
            y = self._activity.y + self._activity.h*0.5
            text_anchor = "c"

        elif self.buffer_type == 'complete':
            x = self._activity.x + self._activity.w - self._activity.w*0.1
            y = self._activity.y + self._activity.h - self._activity.h*0.1
            text_anchor = "se"

        elif self.buffer_type == 'out':
            x = self._activity.x + self._activity.w - self._activity.w*0.1
            y = self._activity.y - self._activity.h*0.1
            text_anchor = "ne"

        else:
            x = self._activity.x
            y = self._activity.y
            text_anchor = "e"

        return (x, y, text_anchor)
    
    def check_is_full(self):
        
        if self.is_full() == 'YES':
            if self.lvl() < self.cap:
                self._is_full.set('NO')
            
        else:
            if self.lvl() >= self.cap:
                self._is_full.set('YES') 