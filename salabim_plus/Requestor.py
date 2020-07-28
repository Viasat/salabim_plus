import salabim as sim

class Requestor(sim.Component):

    def __init__(self, processor, requested, *args, **kwargs):

        self._processor = processor
        self.requested = requested
        
        name = '_'.join([processor.name(),'requestor'])
        super().__init__(name=name, *args, **kwargs)

    def setup(self):

        self._fulfilled = sim.State(name=self.name()+'_fulfilled', value='NO')
        self._done = sim.State(name=self.name()+'_done', value='NO')
        self._released = sim.State(name=self.name()+'_released', value='NO')
    
    def process(self):

        yield self.request(self.requested)
        self._fulfilled.set('YES')
        yield self.wait((self._done, 'YES'))
        self.release()
        yield self._released.set('YES')
        self.cancel()   

    def changeover_request(self):

        yield self.request(self.requested)
        self._processor.resume()
        yield self.wait((self._done, 'YES'))
        self.release()
        yield self._released.set('YES')
        self.cancel() 
