import misc_tools
import random

def create_routing(env, first_step='op1'):

    tasks = {
        'op1': misc_tools.make_assembly_step(
            env=env, 
            run_time=random.gauss(mu=3, sigma=0.25), 
            route_to='op2'
            ),
        'op2': {
            'location': env['machine_2'],
            'worker': env['technician'],
            'manned': False,
            'setup_time': random.uniform(a=2, b=5),
            'run_time': random.gauss(mu=5, sigma=0.5),
            'teardown_time': 0,
            'transit_time': 1,
            'yield': 0.95,
            'route_to_pass': 'op3',
            'route_to_fail': 'rework'
        },
        'op3': {
            'location': env['common_process'],
            'worker': env['technician'],
            'manned': True,
            'setup_time': random.triangular(low=1, high=4, mode=2),
            'run_time': random.gauss(mu=2, sigma=0.5),
            'teardown_time': random.uniform(a=1, b=2),
            'transit_time': 1,
            'route_to': env['part_b_kanban']
        },
        'rework': {
            'location': env['assembly_bench'],
            'worker': env['assembler'],
            'manned': True,
            'setup_time': 0,
            'run_time': random.expovariate(lambd=0.5)*7,
            'teardown_time': 0,
            'transit_time': 1,
            'fail_count': 2,
            'route_to_pass': 'op2',
            'route_to_fail': env['scrap_storage']
        }
    }

    return misc_tools.make_steps(first_step=first_step, tasks=tasks)

def create_kanban_attrs(env):

    return misc_tools.make_kanban_attrs(order_gen=env['gener.part_b'],
                                        order_point=4, order_qty=5,
                                        init_qty=8, warmup_time=0)