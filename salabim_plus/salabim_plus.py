import salabim as sim
# import pprint
import copy
from collections import OrderedDict

class Error(Exception):
    """Base class for exceptions in this module."""
    pass

class InputError(Error):
    
    def __init__(self, entered, var, options):       
        print(f'{entered} is an invalid input for {var},')
        print(f'use any of the following options: {options}')
    
class ComputationalError(Error):
    
    def __init__(self):
        print(f'It appears nothing happened on a function')


class Environment(sim.Environment):
    """
    Extend `sim.Environment`
    """

    def setup(self, suppress_trace_linenumbers=True):
        """
        sim.Environment setup method for custom functionality

        Args:
            suppress_trace_linenumbers (bool): option to print or not print 
                                               the reference code line number 
                                               within the trace output, 
                                               defaulted to True
        """

        self._env_objs = {}
        self._suppress_trace_linenumbers = suppress_trace_linenumbers

    def _add_env_objectlist(self, obj):
        """
        add to the objectlist noting objects inside of the simulation

        Args:
            obj (sim.Component): salabim_plus top level object 
        """

        self._env_objs[obj._name] = obj

class EntityGenerator(sim.Component):
    """
    Extend `sim.Component` 
    Controls when entities of var_name enter the sim.env system   
    """
    
    # 'continuous','periodic','ordered','inv_based'
    def __init__(self, var_name, steps_func, env, 
                 arrival_type=None, start_at=0, 
                 bom=None, main_exit=None, cut_queue=False, interval=None, 
                 inv_level=None, *args, **kwargs):
        """
        extend `sim.Component.__init__()`, override name variable, 
        setup EntityGenerator specific attributes
        
        Args:
            var_name (str): name of the entity
            # steps (dict): nested dictionary mapping out steps an entity will 
            #               take, must follow standard steps dictionary 
            #               formatting (see steps variable documentation)
            steps_func (function): entity step building function that maps out
                                   the steps an entity will take, must return 
                                   a properly formatted steps dictionary (see 
                                   steps variable documentation)
            env (EnvironmentPlus): salabim_plus simulation environment
            arrival_type (str): predefined method in which entities can 
                                arrive, available methods: ('continuous',
                                'periodic','ordered','inv_based')
            start_at (int): time epoch to wait until before starting 
                            EntityGenerator, optional, default=0
            bom (dict): nested dictionary mapping out build of materials 
                        required to process an entity, must follow standard 
                        bom dictionary formatting (see bom variable 
                        documentation), optional, default=None
            main_exit (Kanban|Storage): location to move entity when its completed,
                                        optional, default=None
            cut_queue (bool): indicator denoting entity should enter queues at
                              head of queue  
            interval (int): time epoch between entity arrivals (only for 
                            arrival_type=`periodic`, optional, default=None)
            inv_level (int): inventory level at which work in process should 
                             be maintained (only for arrival_type=`inv_based`,
                             optional, default=None)
            *arg, **kwargs: sim.Component specific default attributes
        """
        
        sim.Component.__init__(self, name='gener.'+var_name, *args, **kwargs)
        
        self.entity = Entity # Entity base class
        self.make_count = 0 
        self.tracker = EntityTracker(var_name, env) # EntityTracker instance of var_name=var_name
        self.var_name = self._name.replace('gener.','').replace('.','_')
        # self.steps = steps
        self.steps_func = steps_func
        self.bom = bom
        self.main_exit = main_exit
        self.cut_queue = cut_queue
        self.arrival_type = arrival_type
        self.start_at = start_at
        self.env = env
        env._add_env_objectlist(self)
        
        # decision tree to initialize arrival_type specific attributes
        if arrival_type == 'continuous':
            pass
        elif arrival_type == 'periodic':
            self.interval = interval
        elif arrival_type == 'ordered':  
            # sim.State used to know if any entities have been ordered
            self.ordered_qty = (
                sim.State(self.var_name+'_ordered_qty', value=0)
            )
        elif arrival_type == 'inv_based':
            self.inv_level = inv_level
        # raise error for an unrecognized arrival_type method 
        else:
            options = ['continuous','periodic','ordered','inv_based']
            raise InputError(arrival_type, 'arrival_type', options)
        
    def arrive(self):
        """
        main sim.Component process to start generating entities
        """
        
        yield self.hold(self.start_at) # delay process to start_at time epoch
        
        # decision tree to determine method call
        if self.arrival_type == 'continuous':
            yield from self.continuous_arrivals()
        elif self.arrival_type == 'periodic':
            yield from self.periodic_arrivals()
        elif self.arrival_type == 'ordered':
            yield from self.ordered_arrivals()
        elif self.arrival_type == 'inv_based':
            yield from self.inv_based_arrivals()
        # raise error for an unrecognized arrival_type method
        else:
            raise ComputationalError()
    
    def continuous_arrivals(self):
        """
        continuously make entities
        """
        
        while True:
            if self.bom:
                yield from self.check_bom_inv()
            self.make_entity()
            yield self.hold(1) # delay 1 time epoch to prevent inf loop
            
    def periodic_arrivals(self):
        """
        make entities at a predefined rate
        """
        
        while True:
            if self.bom:
                yield from self.check_bom_inv()
            self.make_entity()
            yield self.hold(self.interval)
            
    def ordered_arrivals(self):
        """
        make entities as they are ordered by other sim.Components
        """
        
        while True:
            yield self.wait((self.ordered_qty, lambda v, c, s: v > 0))

            if self.bom:
                yield from self.check_bom_inv()
            yield from self.fulfill_order()      
            
    def inv_based_arrivals(self):
        """
        make entities to maintain a predefined inventory level
        """
        
        while True:
            yield self.wait(
                (self.tracker.wip_count, lambda v, c, s: v < self.inv_level)
            )
            if self.bom:
                yield from self.check_bom_inv()
            yield from self.release_inv()
        
    def fulfill_order(self):
        """
        makes entities of a specified order quantity
        """
        
        for _ in range(self.ordered_qty()):
            if self.bom:
                yield from self.check_bom_inv()
            self.make_entity()
        self.ordered_qty.set(0)
            
    def release_inv(self):
        """
        makes entities needed to reach a specified inventory threshold
        """
        
        for _ in range(self.inv_level - self.tracker.wip_count()):
            if self.bom:
                # print(True)
                yield from self.check_bom_inv()
            self.make_entity()
    
    def make_entity(self):
        """
        makes an entity
        """
        
        self.make_count += 1
        # pprint.pprint(globals())
        self.entity(var_name=self.var_name+'_'+str(self.make_count), env=self.env,
                    steps=self.steps_func(env=self.env._env_objs), tracker=self.tracker, 
                    bom=self.bom, main_exit=self.main_exit, cut_queue=self.cut_queue)

    def populate_inv(self, location):
        """
        """

        self.make_count += 1
        self.entity(var_name=self.var_name+'_'+str(self.make_count), env=self.env,
                    steps=[{'route_to': location}], tracker=self.tracker, prepop=True)
        
    def send_order(self, qty):
        """
        sends an order to make more entities of a specified quantity (only 
        for arrival_type=`ordered`)
        
        Args:
            qty (int): number of entities in order
        """
        
        self.ordered_qty.set(qty)
        
    def check_bom_inv(self):
        """
        check build of material inventory to ensure adequate material is 
        available, wait until all material is available if short
        """
        
        bom_requirements = [
            (details['location'].count, lambda v, c, s: v >= details['qty'])
            for part, details in self.bom.items()
        ]
#         print(bom_requirements)
#         for cond in bom_requirements:
#             print(cond[0]())
        yield self.wait(*bom_requirements, all=True)            

class EntityTracker(sim.Component):
    """
    Extend `sim.Component` 
    Tracks when entities of var_name enter and leave the sim.env system
    """
    
    def __init__(self, var_name, env, *args, **kwargs):
        """
        extend `sim.Component.__init__()`, override name variable,
        setup EntityTracker specific attributes
        
        Args:
            var_name (str): name of the entity
            env (EnvironmentPlus): salabim_plus simulation environment
            *arg, **kwargs: sim.Component specific default attributes
        """
        
        sim.Component.__init__(self, name='track.'+var_name, *args, **kwargs)
        
        self.wip = sim.Queue(self._name+'_wip')
        self.complete = sim.Queue(self._name+'_complete')
        self.wip_count = sim.State(self._name+'_wip_count', value=0)
        self.complete_count = sim.State(self._name+'_complete_count', value=0)
        self.env = env
        env._add_env_objectlist(self)
        
    def update(self):
        """
        updates the tracker states so they are consistent with the tracker 
        queues
        """
        
        self.wip_count.set(len(self.wip))
        self.complete_count.set(len(self.complete))
    
            
class Entity(sim.Component):
    """
    Extend `sim.Component` 
    A work unit that gets processed in the sim.env system
    """
    
    def __init__(self, var_name, env, steps, tracker, bom=None, 
                 main_exit=None, cut_queue=False, prepop=False, 
                 *args, **kwargs):
        """
        extend `sim.Component.__init__()`, override name variable,
        setup Entity specific attributes
        
        Args:
            var_name (str): name of the entity
            env (EnvironmentPlus): salabim_plus simulation environment
            steps (dict): nested dictionary mapping out steps an entity will <-- UPDATE!!
                          take, must follow standard steps dictionary 
                          formatting (see steps variable documentation)
            tracker (EntityTracker): entity tracker used to route new and 
                                     completed entities
            bom (dict): nested dictionary mapping out build of materials 
                        required to process an entity, must follow standard 
                        bom dictionary formatting (see bom variable 
                        documentation), optional, default=None
            main_exit (Kanban|Storage): location to move entity when its completed,
                                        optional, default=None
            cut_queue (bool): indicator denoting entity should enter queues at
                              head of queue  
            *arg, **kwargs: sim.Component specific default attributes
        """

        sim.Component.__init__(self, name=var_name, *args, **kwargs)
        
        self.var_name = self._name.replace('.','_') # unique name of that specific entity 
        self.state = sim.State(self.var_name+'_state', value='in_wip') # entity status
        self.step_complete = sim.State(self.var_name+'_step_complete') # trigger state to move to next step
        self.steps = steps
        self.bom = bom
        self.main_exit = main_exit
        self.cut_queue = cut_queue
        self.prepop = prepop
        self.tracker = tracker
        self.as_built = [] # entity contents that were used to built entity
        self.env = env
        env._add_env_objectlist(self)
        
        if self.bom:
            self.get_materials()
        
    def process(self):
        """
        main sim.Component process to run on instantiation, gets material and 
        follows steps given to process part 
        """
        
        self.enter_system()
        
#         if self.bom:
#             yield from self.get_materials()
        if not self.prepop:    
            yield from self.process_part()
        
        if not isinstance(self.steps[-1]['route_to'], str):
            self.push(to_inv=self.steps[-1]['route_to'])

        self.leave_system()
        self.state.set('complete')
        
    def get_materials(self):
        """
        gathers materials needed to make Entity, as noted in its bom, waits 
        for necessary materails if none available
        """
        
        for part, details in self.bom.items():
            
            for _ in range(self.bom[part]['qty']): # add materials to its as_built
                self.pull(from_inv=self.bom[part]['location'])
            
            
#             if len(self.bom[part]['location'].queue) < self.bom[part]['qty']:
#                 yield self.wait(
#                     (
#                         self.bom[part]['location'].count, # state waiting on
#                         '$ >='+str(self.bom[part]['qty']) # evaluation criteria waiting on
#                     )
#                 )
                      
            
            # update location values from pick location
                
                
    def process_part(self):
        """
        processes part, following the instructions given in its steps
        """
        
        for step in self.steps:
            self.current_step = step
            
            # route to first available machine when MachineGroup is indicated 
            if isinstance(step['location'], MachineGroup):
                step['location'] = (
                    step['location'].find_first_available()
                )
            
            # decision tree to determine where in queue entity shall enter
            if self.cut_queue:
                self.enter_at_head(step['location'].queue)
            else:
                self.enter(step['location'].queue)
            
            self.state.set('waiting') # <<-- insert a get_wait_type statement based on machine state
            step['location'].in_queue.trigger(max=1)
            yield self.wait(self.step_complete)
            yield self.hold(step['transit_time'])
            
    def push(self, to_inv):
        """
        pushes entity to the exit inventory queue, if indicated 
        """
        
        self.enter(to_inv.queue)
        to_inv.entity_entered()

        if (isinstance(self.main_exit, Kanban)) and (self.main_exit != to_inv):
            self.main_exit.entity_entered()
        
    def pull(self, from_inv):
        """
        pulls an entity from the inventory queue indicated in bom
        """
        
        self.as_built.append(from_inv.queue.pop())
        from_inv.entity_left()
        
    def enter_system(self):
        """
        updates metrics that track entities when an entity enters the sim.env
        """
        
        self.enter(self.tracker.wip)
        self.tracker.update()
        
    def leave_system(self):
        """
        updates metrics that track entities when an entity has completed its 
        process in sim.env
        """
        
        self.leave(self.tracker.wip)
        self.enter(self.tracker.complete)
        self.tracker.update()
         
# Does it make send to make worker a sim.Component for WorkerGroups???, but what about benefits of sim.Resource 
# class Worker(sim.Component):
#     """
#     Extend `sim.Component`
#     """
    
#     def __init__(self, var_name, *args, **kwargs):
#         """
#         Extend `sim.Component.__init__()` to setup Machine specific attributes
#         """
#         sim.Component.__init__(self, name=var_name, *args, **kwargs)
        
#         self.var_name = self._name.replace('.','_')
#         self.location = None
#         self.state = sim.State(self.var_name+'_status', value='idle')
#         self.time_remaining = 0
    
class Machine(sim.Component):
    """
    Extend `sim.Component`
    """
    
    def __init__(self, var_name, env, *args, **kwargs):
        """
        extend `sim.Component.__init__()`, override name variable,
        setup Machine specific attributes
        
        Args:
            var_name (str): name of the machine
            env (EnvironmentPlus): salabim_plus simulation environment
            *arg, **kwargs: sim.Component specific default attributes
        """
        
        sim.Component.__init__(self, name=var_name, *args, **kwargs)
        
        self.var_name = self._name.replace('.','_') # unique name of that specific machine 
        self.queue = sim.Queue(self.var_name+'_queue') # queue of entities to work on
        self.in_queue = sim.State(self.var_name+'_in_queue') # trigger state to work on an entity
        self.state = sim.State(self.var_name+'_status', value='idle') # machine status
        self.time_remaining = 0 # time until machine finishes entity being process
        self.env = env
        env._add_env_objectlist(self)
        
    def process(self):
        """
        main sim.Component process to run on instantiation, processes parts, 
        if an entity is in its queue to work on, else waits until entity to 
        work on 
        """
        
        while True:
            # sit idle until entity to work on 
            if len(self.queue) == 0:
                self.state.set('waiting_material')
                yield self.wait(self.in_queue)

            # run machine
            self.in_process = self.queue.pop()
            yield from self.run(**self.in_process.current_step)
            
    def run(self, location, setup_time, run_time, teardown_time, transit_time,
            worker=None, manned=None, **kwargs):
        """
        runs a machine to process an entity as indicated in an entity's step 
        instructions
        
        Args:
            location (Machine): machine, physical location an entity is 
                                processed
            setup_time (int): time required to setup a machine prior to 
                              processing an entity
            run_time (int): time required to process an entity
            teardown_time (int): time required to teardown a machine after 
                                 processing an entity
            transit_time (int): time require to move an entity to the next 
                                step in its steps
            worker (Worker): worker, resource that is required to process an 
                             entity, optional, default=None
            manned (bool): indicator whether a worker is tied to the entity 
                           during machine processing, optional, default=None
        """

        self.in_process.state.set('processing')
        self.update_time_remaining(setup_time + run_time + teardown_time)
        
        yield from self.setup_machine(setup_time, worker, manned) 
        yield from self.process_entity(run_time)
        yield from self.teardown_machine(teardown_time, worker, manned)
        
        self.in_process.step_complete.trigger(max=1)
        
    def process_entity(self, run_time):
        """
        process an entity through the machine
        
        Args:
            run_time (int): time required to process an entity
        """
        
        self.state.set('running')
        yield self.hold(run_time)
        self.update_time_remaining(-run_time)
        
    def setup_machine(self, setup_time, worker=None, manned=None):
        """
        sets up the machine to process an entity
        
        Args:
            setup_time (int): time required to setup a machine prior to 
                              processing an entity
            worker (Worker): worker, resource that is required to process an 
                             entity, optional, default=None
            manned (bool): indicator whether a worker is tied to the entity 
                           during machine processing, optional, default=None
        """
        
        if setup_time > 0:
            if worker:
                self.state.set(self.get_wait_type(worker))
                if self.state() == 'idle':
                    yield self.wait((worker.state, 'on_clock'))
                yield self.request(worker)
                worker.update_num_working()

            self.state.set('changeover_setup')
            yield self.hold(setup_time)
            self.update_time_remaining(-setup_time)

            if worker and not manned:
                self.release(worker)
                worker.update_num_working()

        elif worker and manned:
            self.state.set(self.get_wait_type(worker))
            if self.state() == 'idle':
                yield self.wait((worker.state, 'on_clock'))
            yield self.request(worker)
            worker.update_num_working()

        # # conditional to see if a worker needed
        # if worker:
        #     self.state.set(self.get_wait_type(worker))
        #     if self.state() == 'idle':
        #         yield self.wait((worker.state, 'on_clock'))
        #     yield self.request(worker)
        #     worker.update_num_working()
        
        # if setup_time > 0:
        #     self.state.set('changeover_setup')
        #     yield self.hold(setup_time)
        #     self.update_time_remaining(-setup_time)

        # # conditional to see if a worker needs to be released
        # if not manned and worker:
        #     self.release(worker)
        #     worker.update_num_working()
        
    def teardown_machine(self, teardown_time, worker=None, manned=None):
        """
        tears down the machine after an entity is processed
        
        Args:
            teardown_time (int): time required to teardown a machine after 
                                 processing an entity
            worker (Worker): worker, resource that is required to process an 
                             entity, optional, default=None
            manned (bool): indicator whether a worker is tied to the entity 
                           during machine processing, optional, default=None
        """
        if teardown_time > 0:
            # conditional to see if a worker needs to be requested
            if worker and not manned:
                self.state.set(self.get_wait_type(worker))
                if self.state() == 'idle':
                    yield self.wait((worker.state, 'on_clock'))
                yield self.request(worker)
                worker.update_num_working()

            self.state.set('changeover_teardown')
            yield self.hold(teardown_time)
            self.update_time_remaining(-teardown_time)

            if worker:
                self.release(worker)
                worker.update_num_working()

        elif worker and manned:
            self.release(worker)
            worker.update_num_working()

        # if teardown_time > 0:
        #     # conditional to see if a worker needs to be requested
        #     if (worker and not manned):
        #         self.state.set(self.get_wait_type(worker))
        #         yield self.request(worker)
        #         worker.update_num_working()
                
        #     self.state.set('changeover_teardown')
        #     yield self.hold(teardown_time)
        #     self.update_time_remaining(-teardown_time)
        #     self.release(worker)
        #     worker.update_num_working()
            
        # # conditional to see if a worker needs to be released
        # if (worker and manned):
        #     self.release(worker)
        #     worker.update_num_working()
             
    
    def update_time_remaining(self, time):
        """
        updates the time required on the machine until an entity has finished 
        its process
        
        Args: 
            time (int): time summate to machine time_remaining attribute
        """
        
        self.time_remaining += time 
        
    def get_wait_type(self, worker):
        """
        get the correct machine state based on the worker's state
        
        Args:
            worker (Worker): worker, resource that is required to process an 
                             entity, optional, default=None
        """
        
        if worker.state() == 'off_clock':
            return 'idle'
        else:
            return 'waiting_worker'

class MachineGroup(sim.Component):
    """
    Extend `sim.Component`
    A group of Machines that can conduct a common process
    """
    
    def __init__(self, var_name, env, machines, *args, **kwargs):
        """
        extend `sim.Component.__init__()`, override name variable,
        setup MachineGroup specific attributes
        
        Args:
            var_name (str): name of the machine group
            env (EnvironmentPlus): salabim_plus simulation environment
            machines ([Machine,...]): list of machines consisting of the group
        """
        
        sim.Component.__init__(self, name=var_name, *args, **kwargs)
        self.var_name = var_name
        self.machines = machines
        self.env = env
        env._add_env_objectlist(self)
        
    def find_first_available(self):
        """
        finds the machine amongst the group of machines that has the lowest 
        queue length and the lowest processing time remaining if multiple 
        machine queues are empty 
        """
        
        # conditional to determine if routing based on queue length should be used (no more than 1 machine has an empty queue) 
        if (2 > len(
            [len(machine.queue) for machine in self.machines 
             if len(machine.queue) == 0]
            )):
            # lowest queue length amongst machine queues
            lowest_queue = min(
                [len(machine.queue) for machine in self.machines]
            )
            # match lowest queue length to its machine
            for machine in self.machines:
                if len(machine.queue) == lowest_queue:
                    return machine
                
            raise ComputationalError # value evaluation incorrect, no machine was matched
        
        # routing based on processing time remaining for machines with an empty queue
        else:
            # only machines with an empty queue
            open_machines = (
                [machine for machine in self.machines 
                 if len(machine.queue) == 0]
            )
            # print(open_machines)
            # print([machine.time_remaining for machine in open_machines])
            # lowest time amongst the empty queue machines
            lowest_time_remaining = min(
                [machine.time_remaining for machine in open_machines]
            )
            # match lowest time to its machine
            for machine in open_machines:
                if machine.time_remaining == lowest_time_remaining:
                    return machine
                
            raise ComputationalError # value evaluation incorrect, no machine was matched
        
class ShiftController(sim.Component):
    """
    Extend `sim.Component` 
    """
    
    # 'continuous','pattern','custom'
    def __init__(self, worker, env, start_time, shifts, shift_type, *args, 
                 **kwargs):
        """
        extend `sim.Component.__init__()`, override name variable,
        setup ShiftController specific attributes
        
        Args:
            worker (Worker): worker, resource that is controlled by the shift
            env (EnvironmentPlus): salabim_plus simulation environment
            start_time (int):
            shifts (dict): nested dictionary mapping out the shifts a worker 
                           works, must follow standard shifts dictionary 
                           formatting (see shifts variable documentation)
            shift_type (str): predefined method in which worker works its 
                              shifts, available methods: ('continuous',
                            'pattern','custom')
            *arg, **kwargs: sim.Component specific default attributes
        """
        
        sim.Component.__init__(self, name='control.'+worker._name, *args, 
                               **kwargs)
        
        self.worker = worker
        self.start_time = start_time
        self.shifts = shifts
        self.shift_type = shift_type
        self.worker_cap = worker.capacity() # number of workers in worker sim.Resource
        self.shift_num = 0 # placeholder indicating how many shifts have passed
        self.env = env
        env._add_env_objectlist(self)
        
        # decision tree to verify valid shift_type method
        options = ['continuous','pattern','ordered']
        if shift_type in options:
            pass
        else:
            raise InputError(shift_type, 'shift_type', options) # raise error for an unrecognized shift_type method 
    
    def start_up(self):
        """
        delay shift_controller until the specified start up time epoch 
        """
        
        self.shift_duration = 0
        self.off_duration = self.start_time
        yield from self.run_shift() # delay until indicated start time
    
    def continuous_shifts(self):
        """
        run the same shift continuously
        """
        
        self.shift_duration = self.shifts['shift_duration']
        self.off_duration = self.shifts['off_duration']
        yield from self.run_shift()
        
    def pattern_shifts(self):
        """
        run the pattern shifts repeatedly
        """
        
        idx = self.shift_num % len(self.shifts)
        self.shift_duration = self.shifts[idx]['shift_duration']
        self.off_duration = self.shifts[idx]['off_duration']
        yield from self.run_shift()
        self.shift_num += 1
        
    def custom_shifts(self):
        """
        run the shifts given once
        """
        
        if len(self.shifts) > self.shift_num:
            self.shift_duration = self.shifts[self.shift_num]['shift_duration']
            self.off_duration = self.shifts[self.shift_num]['off_duration']
            yield from self.run_shift()
            self.shift_num += 1
        
    def run_shift(self):
        """
        runs a specificied shift for the worker
        """
        
        self.worker.state.set('on_clock') # update worker state
        yield self.hold(self.shift_duration) # run shift
        
        # stop all machines serviced by the worker at end of shift
        tmp = {}
        for machine in self.worker.claimers():
            machine.interrupt()
            tmp[machine] = copy.deepcopy(machine.state()) # save machine state for start up
            machine.state.set('idle') # update machine state
            
        self.worker.set_capacity(0) # remove worker from env
        self.worker.update_num_working(0) # zero out worker allocation level
        
        self.worker.state.set('off_clock') # update worker state
        yield self.hold(self.off_duration) # unscheduled time
        
        # start all machines back up at start of next shift
        for machine in self.worker.claimers():
            machine.resume()
            machine.state.set(copy.deepcopy(tmp[machine])) # update machine state
        
        self.worker.set_capacity(self.worker_cap) # place worker back in env
        self.worker.update_num_working() # reinstate worker allocation level
        
        
    def work(self):
        """
        activates shift controller to control shifts in which workers work
        """
        
        yield from self.start_up() # delay process to start_up time epoch

        while True:
            # decision tree to determine method call
            if self.shift_type == 'continuous':
                yield from self.continuous_shifts()
            elif self.shift_type == 'pattern':
                yield from self.pattern_shifts()
            elif self.shift_type == 'custom':
                yield from self.custom_shifts()
            # raise error for an unrecognized arrival_type method
            else:
                raise ComputationalError()

class Worker(sim.Resource):
    """
    Extend `sim.Component` 
    """
    
    def __init__(self, var_name, env, capacity, *args, **kwargs):
        """
        extend `sim.Component.__init__()`, override name variable,
        setup Worker specific attributes
        
        Args:
            var_name (str): name of the worker resource
            env (EnvironmentPlus): salabim_plus simulation environment
            capacity (int): indicator for the number of workers in this worker
                            resource 
            *arg, **kwargs: sim.Component specific default attributes
        """
        
        sim.Resource.__init__(self, name=var_name, capacity=capacity, *args, 
                              **kwargs)
        
        self.state = sim.State(self._name+'_status', value='off_clock') # worker status
        self.num_working = sim.State(self._name+'_num_working', value=0) # state indicating how many workers are working
        self.env = env
        env._add_env_objectlist(self)
        
    def update_num_working(self, value=None):
        """
        updates the number of workers that are working
        
        Args:
            value (int): number to update number of workers to, optional, 
                         default=None
        """
        
        if isinstance(value, int):
            self.num_working.set(value)
        else:
            # use the length of the sim.Resource.claimers list if no value indicated, indicates what sim.Components have claimed a resource
            self.num_working.set(len(self.claimers()))
            
class Kanban(sim.Component):
    """
    Extend `sim.Component` 
    """
    
    def __init__(self, var_name, env, kanban_attr, *args, **kwargs):
        """
        extend `sim.Component.__init__()`, override name variable,
        setup Kanban specific attributes
        
        Args:
            var_name (str): name of the kanban storage location
            env (EnvironmentPlus): salabim_plus simulation environment
            kanban_attr (dict): dictionary mapping out characteristics of the 
                                kanban, must follow standard kanban_attr 
                                dictionary formatting (see kanban_attr 
                                variable documentation)
            *arg, **kwargs: sim.Component specific default attributes
        """
        
        sim.Component.__init__(self, name=var_name+'_kanban', *args, **kwargs)
        
        self.order_gen = kanban_attr['order_gen'] # EntityGenerator to order entities from
        self.order_point = kanban_attr['order_point'] # threshold in which an order shall be made
        self.order_qty = kanban_attr['order_qty'] # quantity of an order
        self.init_qty = kanban_attr['init_qty'] # initial quantity to order at beginning of simulation
        self.warmup_time = kanban_attr['warmup_time'] # time to wait in beginning of simulation before evaluating whether an order should be made 
        self.queue = sim.Queue(self._name+'_queue') # kanban queue
        self.count = sim.State(self._name+'_count', value=0) # state indicating how many entities are in kanban queue
        self.on_order = sim.State(self._name+'_on_order', value=0) # state indicating how many entities are on order
        self.total_inv = sim.State(self._name+'_total_inv', value=0) # sum of entities on order and entities in kanban queue
        self.env = env
        env._add_env_objectlist(self)
        
    def process(self):
        """
        main sim.Component process to run on instantiation, sends an order 
        for entities when below its indicated threshold, conducts a warmup 
        period to populate kanban at beginning of sim.env simulation 
        """

        # conduct initial setup/warmup period
        # self.order_gen.send_order(self.init_qty) 
        # self.entity_ordered(self.init_qty) 
        # yield self.hold(self.warmup_time)

        # prepopulate entitys
        if self.init_qty > 0:
        #     # yield from self.populate()
        #     self.on_order.set(self.init_qty)
            for _ in range(self.init_qty):
                self.queue.append(sim.Component(name='dummy'))
        #         self.order_gen.populate_inv(location=self.env.objs[self._name])
            self.update_inv()

        while True:
            yield self.wait((self.total_inv, lambda v, c, s: v < self.order_point)) # wait until the inventory level falls below the indicated threshold
            self.order_gen.send_order(self.order_qty)
            self.entity_ordered(self.order_qty)

    def populate(self):
        """
        """

        for _ in range(self.init_qty):
            self.order_gen.populate_inv(location=self.env._env_objs[self._name])
    
    def entity_ordered(self, qty):
        """
        updates the kaban metrics when an entity is ordered to the kanban 
        queue

        Args:
            qty (int): quantity of entities that have been ordered
        """

        self.on_order.set(self.on_order()+qty)
        self.update_inv()

    def entity_entered(self):
        """
        updates the kanban metrics when an entity enters the kanban queue
        """

        self.on_order.set(self.on_order()-1)
        self.update_inv()

    def entity_left(self):
        """
        updates the kanban metrics when an entity leaves the kanban queue
        """

        self.update_inv()

    def update_inv(self):
        """
        updates the inventory metrics of the kanban
        """

        self.count.set(len(self.queue))
        self.total_inv.set(self.on_order()+self.count())
            
class Storage(sim.Component):
    """
    Extend `sim.Component` 
    """
    
    # 'continuous','pattern','custom'
    def __init__(self, var_name, env, *args, **kwargs):
        """
        extend `sim.Component.__init__()`, override name variable,
        setup Storage specific attributes
        
        Args:
            var_name (str): name of the storage location
            env (EnvironmentPlus): salabim_plus simulation environment
        """
        
        sim.Component.__init__(self, name=var_name+'_storage', *args, 
                               **kwargs)
        
        self.queue = sim.Queue(self._name+'_queue') # storage queue
        self.count = sim.State(self._name+'_count', value=0) # quantity inside storage queue
        self.env = env
        env._add_env_objectlist(self)
        
    def process(self):
        """
        main sim.Component process to run on instantiation
        """

        pass

    def entity_entered(self):
        """
        updates the storage queue count when an entity enters
        """

        self.count.set(len(self.queue))

    def entity_left(self):
        """
        updates the storage queue count when an entity leaves
        """

        self.count.set(len(self.queue))