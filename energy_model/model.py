"""Build and solve the PyPSA energy model.

Hydrogen extension based on the final course model
---------------------------------------------------
Lines marked with ``# [H2]`` were added or changed for the hydrogen study.
Everything else is the P06 course model. Without the new keyword arguments,
``model_run`` behaves exactly as before (Gurobi, no scenario constraint).

New keyword arguments of ``model_run``:
    solver_name     'gurobi'
    solver_options  dict passed to Gurobi; defaults are applied when omitted
    scenario        dict with scenario settings (see model.make_scenario), or None for the
                    plain course model
    results_dir     folder for the solver log
"""

import os

import numpy as np
import pandas as pd
import pypsa

# Logging to control running log output
import logging
logging.getLogger("pypsa").setLevel(logging.ERROR)
logging.getLogger("linopy").setLevel(logging.ERROR)
logging.getLogger("gurobipy").setLevel(logging.ERROR)

from .preprocessing import (
    preprocess_demand,
    preprocess_supply,
    preprocess_technologies,
    int_extrapolate
)

from .h2_scenario import make_scenario, apply_scenario_inputs, apply_network_settings
from .h2_constraints import make_extra_functionality, store_shadow_prices

# ============================================================
# MODEL HELPER FUNCTIONS
# ============================================================

def annuity(disc_rate, life):
    return disc_rate / (1.0 - 1.0 / (1.0 + disc_rate) ** life)

def investment_cost(technology, year, techs_d, rt):
    capex = techs_d.at[(technology,'CAPEX'),year]
    fom = techs_d.at[(technology,'FOM'),year]
    lt = techs_d.at[(technology,'Lifetime'),year]
    return (capex*annuity(rt, lt) + fom) # (€/activity output unit)


def techs_by_type(techs_s, t):
    """Retrieve a list with all techs of type t (e.g link, generator, etc.)"""
    types = techs_s.query("Parameter=='Type'").reset_index()
    return list(types[types['Value']==t]['Technology'].unique())

#     - ```def get_topology(t)```:
def get_topology(techs_s, technology):
    """returns a df with the inputs and outputs of technology, with t's buses as index"""
    techdf = techs_s.loc[(technology,slice(None)),:].reset_index()
    techdf = techdf[techdf.Parameter.str.startswith('bus')].set_index('Parameter')
    return techdf

#     - ```def start_year(t)```:
def start_year(techs_s, technology, years):
    """if a start-year is specified returns it, otherwise default to years[0]"""
    try:
        sy = techs_s.at[(technology,'Start year'),'Value']
    except KeyError:
        sy = years[0]
    return sy


def static_value(techs_s, technology, parameter, default=None):  # [H2]
    """Return a static parameter (e.g. 'Max hours') or a default if it is not in the database."""
    try:
        return float(techs_s.at[(technology, parameter), 'Value'])
    except (KeyError, ValueError, TypeError):
        return default


def get_cap_constraints(t, years, cn):
    """
    Returns a df with any user-defined constraints (cn) on capacity for tech t.
    The base year is only used to set up fixed capacity bounds. This is not extrapolated to future years.
    Any min/max constraints set for future years are inter/extrapolated.
    Returns a NaN df if there are no constraints for t.
    """

    # Set up empty df (float, so pandas 3 does not silently drop the values: the old
    # `df.loc[t, :] = cn.loc[t, :]` assignment returned all-NaN with pandas >= 3.0)   [Freight: bug fix]
    df = pd.DataFrame(np.nan, columns=years, dtype=float,
                      index=pd.MultiIndex.from_product([[t], ['min', 'max']], names=['Technology', 'Type']))

    # Fill it with user-defined constraints from the technologies input table
    if t in cn.index.get_level_values(0):
        sub = cn.xs(t, level=0)
        for typ in sub.index:
            if typ in ('min', 'max'):
                for y in years:
                    if y in sub.columns and pd.notna(sub.at[typ, y]):
                        df.loc[(t, typ), y] = float(sub.at[typ, y])

    # The base year is only used to set up fixed capacity bounds, we don't want to extrapolate those to future years.
    # We only want to int/extrapolate if there are user-constraints on max or min cap limits after the base year:
    # Slice df for years > base year, and store index of non-nan values
    df_idx = df.loc[:,[y for y in years if ((y>years[0]) and (y in df.columns))]]
    idx = np.where(df_idx.notna())

    # If there are no non-nan values, return df as it is:
    if len(df_idx.iloc[idx[0],idx[1]])==0:
        ret = df

    # otherwise int-extrapolate:
    else:
        ret = int_extrapolate(df, years)

    return ret


def default_solver_options(solver_name, results_dir):  # [H2]
    """Return the Gurobi options used by the model."""
    if solver_name != 'gurobi':
        raise ValueError(f"Unsupported solver {solver_name!r}; this project requires 'gurobi'.")
    return {"LogFile": os.path.join(results_dir, "solver_run.log"),
            "LogToConsole": 0,
            "TimeLimit": 43200}

# ============================================================
# MAIN MODEL FUNCTION
# ============================================================

def model_run(db_dir, years, t_res, passenger_cars_cf, rt, rs,
              solver_name='gurobi', solver_options=None,      # [H2]
              scenario=None, results_dir='results'):          # [H2]
    """
    Build and solve the energy model.

    Parameters
    ----------
    db_dir
        Folder containing the input database.
    years
        Model periods.
    t_res
        Intra-year temporal resolution.
    passenger_cars_cf
        Conversion factor for passenger cars.
    rt
        Technical discount rate.
    rs
        Social discount rate.
    solver_name, solver_options          [H2]
        Solver to use. The published model uses Gurobi.
    scenario                             [H2]
        None (plain course model) or a scenario dict from model.make_scenario().
    results_dir                          [H2]
        Folder for the solver log.

    Returns
    -------
    pypsa.Network
        The optimized PyPSA network.
    """

    # --------------------------
    # 1. PREPROCESS INPUT DATA
    # --------------------------

    # Call the preprocessing functions and store their outputs.

    demands, demand_profiles_prj = preprocess_demand(
            db_dir, years, t_res
        )
    resources, resources_pars, ren_profiles = preprocess_supply(
            db_dir, years, t_res
        )

    techs_s, techs_d, cn = preprocess_technologies(
            db_dir, years, passenger_cars_cf
        )

    # [H2] The scenario changes the input data before the network is built: the largest electrolyser capacity
    #      per vintage goes into the capacity constraints (cn), and sensitivities change prices and costs
    #      (CO2 price, gas price, electrolyser CAPEX or subsidy, battery cost/duration).
    if scenario is not None:
        techs_s, techs_d, resources_pars, cn = apply_scenario_inputs(
            techs_s, techs_d, resources_pars, cn, scenario, years)

    # --------------------------
    # 2. CREATE PYPSA NETWORK
    # --------------------------

    # Create the network and define snapshots/model periods.

    n = pypsa.Network()

    # Define snapshots and investment periods from demand profiles index:
    n.set_snapshots(demand_profiles_prj.index,
                    default_snapshot_weightings=t_res)

    n.investment_periods = years

    # Set the legth of each period:
    n.investment_period_weightings['years'] = list(np.diff(years)) + [list(np.diff(years))[-1]] # the last period gets the same delta as the second last

    # Set the weight of each period on the objective function.
    # For this we use a "social" discount rate rs=1%
    # (lower than the "technical" discout rate rt used for annuitization):
    T = 0
    for period, nyears in n.investment_period_weightings.years.items():
        discounts = [(1 / (1 + rs) ** t) for t in range(T, T + nyears)]
        n.investment_period_weightings.at[period, 'objective'] = sum(discounts)
        T += nyears



    # --------------------------
    # 3. ADD MODEL COMPONENTS
    # --------------------------

    # From the demand dataframes: add all buses and corresponding loads

    # Add demand buses and corresponding carrier
    for b in demands.Bus.unique():
        n.add("Bus", b, carrier=demands[demands.Bus==b]['Carrier'].values[0])

    # Add loads, with the right demand bus from the demand dataframe
    # and the right profile from the demand_profiles_prj dataframe
    for d in demands.index:
        n.add("Load", d,
            bus=demands.at[d,'Bus'],
            p_set=demand_profiles_prj.loc[:,d].values)

    # From the resources dataframe: Loop over all resources and distinguish three separate cases
    #     - For Secondary resources add a bus
    #     - For Reserves add a bus and a store
    #     - For Emissions add a bus, a store and a maximum limit

    for s in resources['Resource'].unique():

        # for secondary resources add a bus
        if resources[resources.Resource==s]['Type'].values[0] == 'Secondary':
            n.add("Bus", s, carrier = resources[resources.Resource==s]['Carrier'].values[0])

        #  for reserves add a bus...
        elif resources[resources.Resource==s]['Type'].values[0] == 'Reserve':
            n.add("Bus", s, carrier=resources[resources.Resource==s]['Carrier'].values[0])

            # ... and a store
            n.add(
                "Store",
                s,
                carrier = resources[resources.Resource==s]['Carrier'].values[0],
                bus = s,
                # Max energy in the store at any given time:
                e_nom = resources_pars[(resources_pars.Resource==s) & (resources_pars.Parameter=='Reserves')][years[0]].values[0],
                # Initial energy in the store (it's a reserve, so we set it equal to e_nom)
                e_initial = resources_pars[(resources_pars.Resource==s) & (resources_pars.Parameter=='Reserves')][years[0]].values[0],
                # Whether the model can optimize e_nom
                e_nom_extendable = False,
                # Whether the stored energy has to return to e_initial at the end of a period
                e_cyclic = False,
                )

        # For emissions add a bus...
        elif resources[resources.Resource==s]['Type'].values[0] == 'Emissions':
            n.add("Bus", s, carrier=resources[resources.Resource==s]['Carrier'].values[0])

            # ... an upper value to limit maximum cumulated emissions at any snapshot within a given year...
            co2_max_profile = pd.Series(index=n.snapshots, dtype=float)
            for y in years:
                co2_max_profile.loc[y] = resources_pars[(resources_pars.Resource==s) &\
                                                        (resources_pars.Parameter=='Budget')][y].values[0]

            # ... and a store
            n.add(
                "Store",
                s,
                carrier=resources[resources.Resource==s]['Carrier'].values[0],
                bus=s,
                # For CO2 we add e_nom as a normalized value...
                e_nom=1,
                # ... and then we set the yearly max cumulated emissions relative to e_nom
                e_max_pu = co2_max_profile,
                e_initial=0,
                e_nom_extendable=False,
                e_cyclic=False,
                )


    # Loop over periods to add all technologies, distinguishing three separate cases:
    #     - Generators - loop through all generators and add them to the network
    #     - Links - loop over all links, check type of link (nr of inputs and outputs), and add to the network
    #     - Storage Units - loop over all storage units and add them to the network
    #     - [H2] Stores - energy storage with a separate energy capacity (the H2 storage option)


    # [H2] In the course code, a technology whose start year lies after y is still added in loop year y,
    #      with build_year = start year but with the costs and fuel/CO2 prices of year y. 'SMR CCS_2020' is then
    #      built in 2030 but pays 2020 gas and CO2 prices for its whole lifetime. In scenario runs these
    #      early copies are skipped (setting skip_early_vintages, default True); the plain course model keeps them.
    skip_early = scenario is not None and scenario.get('skip_early_vintages', True)

    def too_early(t, y):
        return skip_early and y < int(start_year(techs_s, t, years))

    # Loop over model years to add all technologies:
    for y in years:
        print(y)

        # We use techs_by_type to distinguish generators, links and storage units

        # Generators:
        for t in techs_by_type(techs_s, 'Generator'):
            if too_early(t, y):  # [H2]
                continue
            bus0 = techs_s.at[(t,'bus0'), 'Value'] # bus0 as carrier
            bus1 = techs_s.at[(t,'bus1'), 'Value'] # bus1 as bus

            # Retrieve any user-defined capacity constraints for this technology/vintage
            cap_constraints = get_cap_constraints(t, years, cn)

            n.add(
                'Generator',
                f'{t}_{y}',
                carrier = techs_s.at[(t,'Carrier'),'Value'] if (t,'Carrier') in techs_s.index else bus0,  # [H2] own carrier (dedicated wind/solar option)
                bus = bus1,
                p_nom_extendable = True,
                p_max_pu = ren_profiles[bus0].values, # apply renewable profiles as max availability factors
                build_year = max([start_year(techs_s,t,years),y]),  # make sure t won't be built before its start_year
                capital_cost = investment_cost(t, y, techs_d, rt),
                marginal_cost = techs_d.at[(t,'VOM'),y],
                lifetime = techs_d.at[(t,'Lifetime'),y],
                efficiency = techs_d.at[(t,'Efficiency'),y],
                # capacity constraints (NaN -> PyPSA treats as unconstrained: p_nom_max=inf, p_nom_min=0)
                p_nom_max = cap_constraints.at[(t,'max'),y],
                p_nom_min = cap_constraints.at[(t,'min'),y],
                )

        # Links:
        for t in techs_by_type(techs_s,'Link'):
            if too_early(t, y):  # [H2]
                continue

            # "existing" technologies may only be installed in the base year (they represent the
            # 2020 stock, with CAPEX=0 and a short lifetime); skip them in all later vintages.
            if ('existing' in t) and (y > years[0]):
                continue

            # Retrieve any user-defined capacity constraints for this technology/vintage
            cap_constraints = get_cap_constraints(t, years, cn)

            # First, get the link topology dataframe
            topology = get_topology(techs_s, t)

            # Second, check if a cost is specified for any of the buses in the link
            bus_cost = {}
            for b in topology.index:
                try:
                    bus_cost[b] = resources_pars[(resources_pars.Resource==topology.at[b,'Value']) &\
                                                (resources_pars.Parameter=='Price')][y].values[0]
                # In case there are no costs specified and an error is raised, set the costs to 0:
                except IndexError:
                    bus_cost[b] = 0
                except KeyError:
                    bus_cost[b] = 0

            # 1. Simple link, one input one output (two  buses)
            if len(topology)==2:
                n.add(
                    'Link',
                    f'{t}_{y}',
                    carrier = t, # for links we will use the technology name as carrier (it helps sorting out the results)
                    bus0 = topology.at['bus0','Value'], # input bus
                    bus1 = topology.at['bus1','Value'], # output bus
                    p_nom_extendable = True,
                    build_year = max([start_year(techs_s,t,years),y]),
                    capital_cost = investment_cost(t, y, techs_d, rt) * techs_d.at[(t,'Efficiency'), y], # for links costs are expressed in €/activity unit input
                    marginal_cost = techs_d.at[(t,'VOM'), y] + bus_cost['bus0'] + bus_cost['bus1']*techs_d.at[(t,'Efficiency'), y], # VOM + any costs associated with the inputs or the outputs
                    lifetime = techs_d.at[(t,'Lifetime'), y],
                    efficiency = techs_d.at[(t,'Efficiency'), y],
                    # capacity constraints are given in output units -> divide by efficiency to express them per unit of input (p_nom)
                    p_nom_max = cap_constraints.at[(t,'max'),y] / techs_d.at[(t,'Efficiency'), y],
                    p_nom_min = cap_constraints.at[(t,'min'),y] / techs_d.at[(t,'Efficiency'), y],
                    )

            # 2. Link with three buses (e.g. links with emissions)
            elif len(topology)==3:
                # Such a link will have two efficiencies:
                eff1 = techs_d.at[(t,'Efficiency'), y]
                eff2 = techs_d.at[(t,topology.at['bus2','Efficiency_link']), y]

                n.add(
                    'Link',
                    f'{t}_{y}',
                    carrier = t,
                    bus0 = topology.at['bus0','Value'],
                    bus1 = topology.at['bus1','Value'],
                    bus2 = topology.at['bus2','Value'],
                    p_nom_extendable = True,
                    build_year = max([start_year(techs_s,t,years),y]),
                    capital_cost = investment_cost(t, y, techs_d, rt) * techs_d.at[(t,'Efficiency'), y],
                    marginal_cost = techs_d.at[(t,'VOM'), y] + bus_cost['bus0'] + bus_cost['bus1']*eff1 + bus_cost['bus2']*eff2,
                    lifetime = techs_d.at[(t,'Lifetime'), y],
                    efficiency = eff1,
                    efficiency2 = eff2,
                    p_nom_max = cap_constraints.at[(t,'max'),y] / techs_d.at[(t,'Efficiency'), y],
                    p_nom_min = cap_constraints.at[(t,'min'),y] / techs_d.at[(t,'Efficiency'), y],
                    )

            # 3. Link with four buses: CCS technologies.
            #    bus0 = input, bus1 = main output, bus2 = CO2 emitted to the atmosphere (not captured),
            #    bus3 = CO2 captured and sent to storage. The Efficiency_link column tells us which
            #    dynamic parameter feeds each extra output (Emissions -> bus2, Captured CO2 -> bus3).
            elif len(topology)==4:
                # Such a link has three efficiencies (main output + the two CO2 streams):
                eff1 = techs_d.at[(t,'Efficiency'), y]
                eff2 = techs_d.at[(t,topology.at['bus2','Efficiency_link']), y]
                eff3 = techs_d.at[(t,topology.at['bus3','Efficiency_link']), y]

                n.add(
                    'Link',
                    f'{t}_{y}',
                    carrier = t,
                    bus0 = topology.at['bus0','Value'], # input
                    bus1 = topology.at['bus1','Value'], # main output
                    bus2 = topology.at['bus2','Value'], # CO2 to atmosphere (not captured)
                    bus3 = topology.at['bus3','Value'], # CO2 captured and stored
                    p_nom_extendable = True,
                    build_year = max([start_year(techs_s,t,years),y]),
                    capital_cost = investment_cost(t, y, techs_d, rt) * techs_d.at[(t,'Efficiency'), y],
                    marginal_cost = techs_d.at[(t,'VOM'), y] + bus_cost['bus0'] + bus_cost['bus1']*eff1 + bus_cost['bus2']*eff2 + bus_cost['bus3']*eff3,
                    lifetime = techs_d.at[(t,'Lifetime'), y],
                    efficiency = eff1,
                    efficiency2 = eff2,
                    efficiency3 = eff3,
                    p_nom_max = cap_constraints.at[(t,'max'),y] / techs_d.at[(t,'Efficiency'), y],
                    p_nom_min = cap_constraints.at[(t,'min'),y] / techs_d.at[(t,'Efficiency'), y],
                    )

        # StorageUnits
        for t in techs_by_type(techs_s,'StorageUnit'):
            if too_early(t, y):  # [H2]
                continue
            # [H2] optional battery settings for sensitivities 3a-c (capacity limit, duration)
            cap_constraints = get_cap_constraints(t, years, cn)
            n.add(
                'StorageUnit',
                f'{t}_{y}',
                bus = techs_s.at[(t,'bus0'), 'Value'],
                carrier = t,
                capital_cost = investment_cost(t,y,techs_d,rt),
                marginal_cost = techs_d.at[(t,'VOM'), y],                    # [H2] (0 for the battery)
                efficiency_store = techs_d.at[(t,'Efficiency'), y],
                efficiency_dispatch = techs_d.at[(t,'Efficiency'), y],
                build_year = max([start_year(techs_s,t,years),y]),
                lifetime = techs_d.at[(t,'Lifetime'), y],                    # [H2] was missing (default: infinite)
                max_hours = static_value(techs_s, t, 'Max hours', 1.0),      # [H2] PyPSA default is 1 h
                p_nom_max = cap_constraints.at[(t,'max'),y],                  # [H2] NaN -> unconstrained
                p_nom_min = cap_constraints.at[(t,'min'),y],                  # [H2]
                p_nom_extendable=True,
                cyclic_state_of_charge=True,
            )

        # [H2] Stores: storage with its own energy capacity (the H2 storage option, salt caverns).
        #      CAPEX/FOM are per unit of energy capacity (€/kWh -> €/MWh after preprocessing).
        #      Charging and discharging are free and lossless (no separate compressor is modelled).
        for t in techs_by_type(techs_s, 'Store'):
            if too_early(t, y):  # [H2]
                continue
            n.add(
                'Store',
                f'{t}_{y}',
                bus = techs_s.at[(t,'bus0'), 'Value'],
                carrier = t,
                e_nom_extendable = True,
                e_cyclic = True,
                capital_cost = investment_cost(t, y, techs_d, rt),
                build_year = max([start_year(techs_s,t,years),y]),
                lifetime = techs_d.at[(t,'Lifetime'), y],
            )


    # [H2] Scenario settings that act on the built network:
    #      - fuel and CO2 prices per period instead of per vintage (setting period_prices)
    #      - what the hydrogen demand is used for (feedstock on top, or fuel taken out of the HTP demand)
    if scenario is not None:
        scenario['_db_dir'] = db_dir                          # [Freight] for the alternative freight profiles
        apply_network_settings(n, scenario, techs_d, resources_pars, years)

    # --------------------------
    # 4. SOLVE MODEL
    # --------------------------

    n.sanitize()

    # [H2] solver choice and the extra constraints (CO2-storage cap, build limits, battery cap)
    os.makedirs(results_dir, exist_ok=True)
    if solver_options is None:
        solver_options = default_solver_options(solver_name, results_dir)
    extra = make_extra_functionality(scenario) if scenario is not None else None

    status, condition = n.optimize(multi_investment_periods=True,
            solver_name=solver_name,
            log_to_console=False,
            include_objective_constant=False,
            solver_options=solver_options,
            extra_functionality=extra,          # [H2]
            )

    if scenario is not None and status == 'ok':        # [Freight] restored: settings and shadow prices on n.meta
        try:
            store_shadow_prices(n, scenario)
        except Exception as err:                       # never lose a solved run over the post-processing
            print(f'store_shadow_prices failed: {err!r}')

    print("\n")
    print(f"Model Status: {status}")
    print(f"Termination Condition: {condition}")
    print(f"Objective value: {n.objective}")

    return n
