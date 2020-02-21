import pandas as pd 
import datetime
import plotly.figure_factory as ff
import plotly.express as px

def get_trace_df(filepath):
    """
    reads in the output trace text file from a salabim_plus simulation

    Args:
        filepath (str): filepath mapping to the output trace text file

    Returns:
        pd.DataFrame(): dataframe of output trace text file contents
    """
    
    # read in file
    df = (
        pd.read_fwf(filepath, 
                    widths=[6,11,21,36,50], 
                    header=0, 
                    skiprows=range(1,5)
                    )
    )

    # forward fill columns with multiple events to carry over values  
    df.loc[:,['time','current component']] = (
        df
        .loc[
            :,
            ['time','current component']
        ]
        .ffill() 
    )

    return df

def get_state_df(filepath):
    """
    reads in the output trace text file from a salabim_plus simulation, 
    retains only data pertinent to state changes

    Args:
        filepath (str): filepath mapping to the output trace text file

    Returns: 
        pd.DataFrame(): dataframe of state changes within simulation
    """

    tmp = get_trace_df(filepath)

    df = (
        tmp
        # filter to state change rows
        .loc[
            tmp['action'].str.contains('set|create|creat|crea')
            & tmp['information'].str.contains('value')
        ]
        # extract state change info as separate columns
        .assign(
            action_component= lambda row: row['action'].str.split(' ').str[0],
            value= lambda row: (
                row['information'].str.extract(r'value\s?= (.*|\d*)')
            )
        )
    )

    return df

def get_machine_state_df(state_df, start_time, duration, machine_list):
    """
    filters out a state change dataframe to only have machine relevant status 
    changes, applies correct time variables

    Args:
        state_df (pd.DataFrame): dataframe containing only state changes from 
                                 salabim_plus simulation
        start_time (datetime.datetime): assumed start of the simulation
        duration (datetime.timedelta): the simulation duration
        machine_list ([str,...]): a list of machine classes used in simulation

    Returns:
        pd.DataFrame(): dataframe of state changes for machines in simulation
    """

    end_time = start_time + duration
    # add status suffix to machine classes
    machine_list = [machine+'_status' for machine in machine_list]

    df = (
        state_df.loc[:,['time','action_component','value']]
        # create time relevant columns
        .assign(
            time = lambda x: start_time + pd.to_timedelta(x['time'], unit='m'),
            end_time = lambda x: (
                x.groupby('action_component')['time']
                .shift(-1, fill_value=end_time)
            ),
            run_time = lambda x: x['end_time'] - x['time']
        )
        .dropna()
        # filter to only machine relevant rows
        # and stayed at status longer than 1 epoch
        .loc[
            lambda x: (
                (x['action_component'].isin(machine_list))
                & (x['run_time'] != datetime.timedelta(minutes=0))
            ),
        ]
        .sort_values(['action_component','time'])
    )

    return df

def plot_machine_timeline(machine_df):
    """
    plots a timeline of machine state changes 

    Args:
        machine_df (pd.DataFrame): dataframe containing only state changes of 
                                   machines in a salabim_plus simulation
    """

    data = (
        machine_df
        # rename columns to standard names for ff.create_gantt()
        .rename(columns={
            'time':'Start',
            'end_time':'Finish',
            'action_component':'Task', 
            'value':'Resource'
            })
        .to_dict('records')
    )

    # standard color status mapping
    colors = {
        'waiting_worker': 'rgb(255, 0, 0)',
        'waiting_material': 'rgb(255, 128, 0)',
        'running': 'rgb(0, 255, 0)',
        'changeover_teardown': 'rgb(0, 0, 255)',
        'changeover_setup': 'rgb(0, 0, 255)',
        'idle': 'rgb(160, 160, 160)'
        }

    fig = ff.create_gantt(
        data, 
        group_tasks=True, 
        index_col='Resource', 
        show_colorbar=True, 
        colors=colors, 
        width=1200, height=500
    )
    fig.update_layout(title_text='Machine Timeline', title_font_size=28)
    fig.show()

def plot_machine_utilization(machine_df, duration):
    """
    plots the utilization of each machine 

    Args:
        machine_df (pd.DataFrame): dataframe containing only state changes of
                                   machines in a salabim_plus simulation
        duration (datetime.timedelta): the simulation duration
    """

    duration = duration.total_seconds()

    machine_agg_df = (
        machine_df
        .assign(
            run_time= lambda x: x['run_time'].dt.total_seconds()
        )
        .groupby(['action_component','value'])
        .agg({'run_time':'sum'})
        .reset_index()
        .assign(
            run_time_perc = lambda x: x['run_time'] / duration
        )
    )

    # list of standard statuses from salabim_plus
    category_orders = {
    'value': [
        'running','changeover_setup','changeover_teardown',
        'waiting_worker','waiting_material','idle'
        ]
    }

    # standard color status mapping
    colors = {
        'waiting_worker': 'rgb(255, 0, 0)',
        'waiting_material': 'rgb(255, 128, 0)',
        'running': 'rgb(0, 255, 0)',
        'changeover_teardown': 'rgb(0, 0, 255)',
        'changeover_setup': 'rgb(0, 0, 255)',
        'idle': 'rgb(160, 160, 160)'
    }

    fig = px.bar(
        machine_agg_df, 
        x="action_component", 
        y="run_time_perc", 
        color='value', 
        color_discrete_map=colors, 
        category_orders=category_orders
    )
    fig.update_layout(title_text='Machine Utilization', title_font_size=28)
    fig.show()

def get_worker_state_df(state_df, start_time, duration, worker_list):
    """
    filters out a state change dataframe to only have worker relevant status 
    changes, applies correct time variables

    Args:
        state_df (pd.DataFrame): dataframe containing only state changes from 
                                 salabim_plus simulation
        start_time (datetime.datetime): assumed start of the simulation
        duration (datetime.timedelta): the simulation duration
        worker_list ([str,...]): a list of worker classes used in simulation

    Returns:
        pd.DataFrame(): dataframe of state changes for workers in simulation
    """

    end_time = start_time + duration

    # add num_working suffix to machine classes
    workers_num = [worker + '_num_working' for worker in worker_list]
    # add status suffix to machine classes
    workers_status = [worker + '_status' for worker in worker_list]
    workers = workers_num + workers_status

    df = (
        state_df
        .loc[
            :,
            ['time','action_component','value']
        ]
        # create time relevant columns
        .assign(
            time = lambda x: start_time + pd.to_timedelta(x['time'], unit='m'),
            end_time = lambda x: (
                x.groupby('action_component')['time']
                .shift(-1, fill_value=end_time)
            ),
            run_time = lambda x: x['end_time'] - x['time']
        )
        .dropna()
        # filter to only worker relevant rows
        # and stayed at status longer than 1 epoch
        .loc[
            lambda x: (
                (x['action_component'].isin(workers))
                & (x['run_time'] != datetime.timedelta(minutes=0))
            ),
        ]
        .sort_values(['action_component','time'])
    )

    return df

def plot_worker_in_use_timeline(worker_df, worker_list):
    """
    plots a timeline of workers in use state changes 

    Args:
        worker_df (pd.DataFrame): dataframe containing only state changes of 
                                  workerss in a salabim_plus simulation
        worker_list ([str,...]): a list of worker classes used in simulation
    """

    # add num_working suffix to machine classes
    workers_num = [worker + '_num_working' for worker in worker_list]

    fig = px.line(
        (
            worker_df
            .loc[
                worker_df['action_component'].isin(workers_num)
                , 
            ]
        ), 
        x='time', 
        y='value', 
        color='action_component', 
        line_shape='hv'
    )
    fig.update_layout(title_text='Workers in Use', title_font_size=28)
    fig.show()

def plot_worker_utilization(worker_df, worker_cap_dict):
    """
    plots the utilization of each worker resource

    Args:
        worker_df (pd.DataFrame): dataframe containing only state changes of 
                                  workerss in a salabim_plus simulation
        worker_cap_dict ({str: int}): dictionary noting capacity of each 
                                      worker resource
    """

    # add num_working suffix to machine classes
    workers_num = [
        worker + '_num_working' for worker in worker_cap_dict.keys()
    ]
    # add status suffix to machine classes
    workers_status = [
        worker + '_status' for worker in worker_cap_dict.keys()
    ]

    worker_agg_df = (    
        pd.concat(
            [
                (
                    worker_df
                    .loc[
                        worker_df['action_component'].isin(workers_num)
                    ]
                    .assign(
                        utilized_hours= lambda x: (
                            x['run_time'].dt.total_seconds() 
                            * x['value'].astype(int) / 3600
                        ),
                        worker= lambda x: (
                            x['action_component']
                            .str.replace('_num_working','')
                        )
                    )
                    .groupby(['worker'])
                    .agg({'utilized_hours':'sum'})
                    .reset_index()
                    .set_index('worker')
                ),
                (
                    worker_df
                    .loc[
                        worker_df['action_component'].isin(workers_status)
                    ]
                    .assign(
                        worker= lambda x: (
                            x['action_component']
                            .str.replace('_status','')
                        ),
                        cap= lambda x: x['worker'].map(worker_cap_dict),
                        hours= lambda x: (
                            x['run_time'].dt.total_seconds() 
                            / 3600 * x['cap']
                        )
                    )
                    .groupby(['worker','value'])
                    .agg({'hours':'sum'})
                    .reset_index()
                    .pivot(index='worker', columns='value', values='hours')
                    .reset_index()
                    .set_index('worker')
                )
            ],
            axis=1
        )
        .reset_index()
        .assign(
            unutilized_hours= lambda x: x['on_clock'] - x['utilized_hours'],
            total_time= lambda x: (
                x['utilized_hours'] + x['off_clock'] + x['unutilized_hours']
            ),
            utilized_hours_perc= lambda x: (
                x['utilized_hours'] / x['total_time']
            ),
            off_clock_perc= lambda x: x['off_clock'] / x['total_time'],
            unutilized_hours_perc= lambda x: (
                x['unutilized_hours'] / x['total_time']
            )
        )
        .drop(
            [
                'utilized_hours','off_clock','on_clock',
                'unutilized_hours','total_time'
            ], 
            axis=1
        )
        .melt(id_vars='worker', var_name='category',value_name='percent')
    )  
        
    # status order for plotting
    category_orders = {
        'category': ['utilized_hours_perc','unutilized_hours_perc','off_clock_perc']
    }

    # standard color status mapping
    colors = {
        'unutilized_hours_perc': 'rgb(255, 0, 0)',
        'utilized_hours_perc': 'rgb(0, 255, 0)',
        'off_clock_perc': 'rgb(160, 160, 160)'
            }

    fig = px.bar(
        worker_agg_df, 
        x="worker", 
        y="percent", 
        color='category', 
        color_discrete_map=colors, 
        category_orders=category_orders
    )
    fig.update_layout(title_text='Workforce Utilization', title_font_size=28)
    fig.show() 

def get_entity_state_df(state_df, start_time, duration):
    """
    filters out a state change dataframe to only have entity relevant status 
    changes, applies correct time variables

    Args:
        state_df (pd.DataFrame): dataframe containing only state changes from 
                                 salabim_plus simulation
        start_time (datetime.datetime): assumed start of the simulation
        duration (datetime.timedelta): the simulation duration

    Returns:
        pd.DataFrame(): dataframe of state changes for entities in simulation
    """

    end_time = start_time + duration

    df = (
        state_df
        # filter to only entity relevant rows
        .loc[
            state_df['action_component'].str.contains('count'),
            ['time','action_component','value']
        ]
        # create time relevant columns
        # create entity specific columns
        .assign(
            time = lambda x: (
                start_time + pd.to_timedelta(x['time'], unit='m')
            ),
            end_time = lambda x: (
                x.groupby('action_component')['time']
                .shift(-1, fill_value=end_time)
            ),
            run_time = lambda x: x['end_time'] - x['time'],
            counts = lambda x: (
                x['action_component'].str.replace('track.','')
                .str.replace('_count','')
            ),
            entity = lambda x: x['counts'].str.extract(r"(.*_?.*)_.*")
        )
        .dropna()
        # filter to status longer than 1 epoch
        .loc[
            lambda x: (
                (x['run_time'] != datetime.timedelta(minutes=0))
            ),
        ]
        .sort_values(['counts','time'])
    )

    return df

def plot_entity_timeline(entity_df, height):
    """
    plots a timeline of entity state changes 

    Args:
        entity_df (pd.DataFrame): dataframe containing only state changes of 
                                  entities in a salabim_plus simulation
        height (int): height of the plot
    """

    fig = px.line(
        entity_df, 
        x='time', 
        y='value', 
        color='counts', 
        line_shape='hv',
        facet_row='entity',
        height=height
    )
    fig.update_yaxes(matches=None)
    fig.update_layout(title_text='Entity Counts', title_font_size=28)
    fig.show()