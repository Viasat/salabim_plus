import salabim as sim
import salabim_plus as simx

class Processor(sim.Component):

    def __init__(self, activity, *args, **kwargs):

        self._activity = activity
        self.processee = None
        self.requestors = []
        
        name = '_'.join([activity.name(),'processor'])
        super().__init__(name=name, *args, **kwargs)
    
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

    def pick(self, r):

        if isinstance(r, list):
            tmp = []
            for i in r:
                self.requestors.append(simx.Requestor(processor=self, requested=i))
                tmp.append(self.requestors[-1])
                
            for j in tmp:
                yield self.wait((j._fulfilled, 'YES'))

        else:
            self.requestors.append(simx.Requestor(processor=self, requested=r))
            tmp = self.requestors[-1]
            yield self.wait((tmp._fulfilled, 'YES'))

    def place(self, r=None):

        if r==None:
            for requestor in self.requestors:
                requestor._done.set('YES')
                yield self.wait((requestor._released, 'YES'))

        elif isinstance(r, list):
            for i in r:
                for requestor in self.requestors:
                    if requestor.requested == i:
                        tmp = requestor

                tmp._done.set('YES')
                yield self.wait((tmp._released, 'YES'))
        
        else:
            for requestor in self.requestors:
                if requestor.requested == r:
                    tmp = requestor

            tmp._done.set('YES')
            yield self.wait((tmp._released, 'YES'))