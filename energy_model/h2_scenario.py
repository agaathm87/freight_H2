# h2_scenario.py    
#  make_scenario(), apply_scenario_inputs(), apply_network_settings()

import numpy as np
import pandas as pd

from .freight_water import apply_freight_inputs, apply_freight_network, apply_water_network   # [Freight]
from .h2_presets import (
    DEFAULTS, SCENARIOS, PRESETS, OPTION_TECHS,
    ELECTROLYSIS, ELECTROLYSIS_GRID, ELECTROLYSIS_SEAWATER,
    H2_STORAGE, BATTERY, GREY, BLUE,
    KG_PER_MWH_H2, MWH_PER_T_H2, H2_LOAD, ETS2_TECHS, CO2_PRICES_ETS2
)

__all__ = [
    'make_scenario', 'apply_scenario_inputs', 'apply_network_settings',
    'electrolyser_reference', 'electrolyser_caps', 'electrolyser_techs',
    'water_limited_electrolyser_techs', 'resolve',
] 


def make_scenario(base='S1', preset=None, **settings):
    """Return the settings for one run, e.g. make_scenario('S3', co2_price='high').

    base is 'S1' (Base), 'S2' (Medium), 'S3' (Scarce) or None (no limit, the same as S1).
    S2 needs the electrolyser capacity of the central S1 run:
    make_scenario('S2', electrolyser_reference=electrolyser_reference(n_S1))
    Hydrogen storage and the green levers are optional settings.
    The defaults are the central Dutch values used to build input_databases/h2_nl.
    preset: None or 'nl' (the same; 'nl' is accepted so older scripts keep working).
    """
    scen = dict(DEFAULTS)
    if preset not in (None, 'nl'):
        raise KeyError(f'Unknown preset {preset!r}')
    scen['preset'] = 'nl'
    if base is not None:
        scen.update(SCENARIOS[base])
        scen['scenario'] = base
    unknown = set(settings) - set(DEFAULTS)
    if unknown:
        raise KeyError(f'Unknown scenario settings: {sorted(unknown)}')
    scen.update(settings)
    if scen['label'] is None:
        scen['label'] = base or 'no limit'
    return scen



# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def resolve(key, value):
    """Turn a preset name into its values (dict or list); leave numbers/dicts/lists as they are."""
    if isinstance(value, str):
        return PRESETS[key][value]
    return value


def _per_year(value, years, key=None):
    """Scalar, preset name or {year: value} dict -> pd.Series over the model years (interpolated)."""
    if isinstance(value, str):
        value = PRESETS[key or 'co2_price'][value]
    if isinstance(value, dict):
        s = pd.Series({int(k): v for k, v in value.items()}, dtype=float)
        s = s.reindex(sorted(set(s.index) | set(years))).interpolate(method='index').ffill().bfill()
        return s.loc[years]
    return pd.Series(float(value), index=years)


def _has(techs_d, tech, par):
    return (tech, par) in techs_d.index


def _set_resource(resources_pars, resource, parameter, values, years):
    row = (resources_pars.Resource == resource) & (resources_pars.Parameter == parameter)
    resources_pars.loc[row, years] = values


def _disable(techs_s, techs):
    for t in techs:
        if (t, 'Type') in techs_s.index:
            techs_s.loc[(t, 'Type'), 'Value'] = 'Disabled'   # techs_by_type() then skips it


# --------------------------------------------------------------------------
# 1. The scenario: electrolyser capacity in the capacity constraints
# --------------------------------------------------------------------------

def electrolyser_reference(n):
    """{technology: {year: MW of hydrogen OUTPUT capacity}} that a solved run builds per electrolyser vintage.

    Use it on the cost-optimal run (the central S1) and pass it to
    make_scenario(..., electrolyser_reference=...). Values below 1 MW are solver noise and count as 0.
    """
    out = {}
    for name, l in n.links[n.links.carrier.isin(ELECTROLYSIS)].iterrows():
        t, y = l.carrier, str(int(l.build_year))
        out.setdefault(t, {})
        out[t][y] = out[t].get(y, 0.0) + float(l.p_nom_opt) * float(l.efficiency)
    return {t: {y: (v if v > 1.0 else 0.0) for y, v in sorted(d.items())} for t, d in out.items()}


def _per_tech(ref):
    """Accept the reference as {technology: {year: MW}} or, for one electrolyser, as {year: MW}."""
    if not ref:
        return {}
    if all(isinstance(v, dict) for v in ref.values()):
        return ref
    return {ELECTROLYSIS_GRID[0]: ref}


def electrolyser_techs(scen):
    """The grid electrolyser and, when enabled, the alternative-water lever."""
    return ((ELECTROLYSIS_GRID if scen.get('grid_electrolysis', True) else [])
            + (ELECTROLYSIS_SEAWATER if scen.get('desal') else []))


def water_limited_electrolyser_techs(scen):
    """Electrolysers whose capacity is constrained by freshwater availability."""
    return ELECTROLYSIS_GRID if scen.get('grid_electrolysis', True) else []


def electrolyser_total_cap(scen, years):
    """{year: MW of H2 output} allowed for freshwater-limited electrolysers."""
    share = scen.get('electrolyser_cap_share')
    if share is None or scen.get('electrolyser_limit_scope', 'total') != 'total':
        return None
    ref = _per_tech(scen.get('electrolyser_reference'))
    out = {}
    for y in years:
        if y < scen.get('cap_from', 2030):
            continue
        tot = sum(float(d.get(str(y), d.get(y, 0.0)) or 0.0) for d in ref.values()) if float(share) > 0 else 0.0
        out[y] = float(share) * tot
    return out


def electrolyser_caps(scen, years):
    """{technology: {year: MW of hydrogen output}} that the scenario allows per electrolyser vintage, or None.

    Freshwater availability limits grid electrolysis. Desalinated-water
    electrolysis is an alternative-water lever and remains outside this cap.
    * scope 'total' (default): freshwater-limited electrolysers together may be
      at most the share of the total electrolyser capacity of the reference run.
      Each freshwater-limited technology gets that total as its own capacity
      constraint; when several are enabled, make_extra_functionality() adds the
      joint limit.
    * scope 'per_technology': each freshwater-limited electrolyser may be at
      most the share of what the reference run builds of it.
    """
    share = scen.get('electrolyser_cap_share')
    if share is None:
        return None
    share = float(share)
    ref = _per_tech(scen.get('electrolyser_reference'))
    techs = water_limited_electrolyser_techs(scen)
    total = electrolyser_total_cap(scen, years)
    if total is not None:
        if share > 0 and not ref:
            raise ValueError(
                f"Scenario {scen.get('label')!r} limits the electrolysers to {share:.0%} of the cost-optimal capacity, so "
                "it needs that capacity: make_scenario(..., electrolyser_reference=electrolyser_reference(n_S1)).")
        return {t: dict(total) for t in techs}
    if share > 0:
        missing = [t for t in techs if t not in ref]
        if missing:
            raise ValueError(
                f"Scenario {scen.get('label')!r} limits the electrolysers to {share:.0%} of the cost-optimal capacity, so "
                f"it needs that capacity for {missing}: make_scenario(..., electrolyser_reference="
                f"electrolyser_reference(n_S1)), where n_S1 is the solved S1 (Base) run "
                f"(electrolyser_limit_scope='per_technology': S1 with the same options).")
    caps = {}
    for t in techs:
        caps[t] = {}
        for y in years:
            if y < scen.get('cap_from', 2030):
                continue
            r = 0.0 if share == 0 else float(ref[t].get(str(y), ref[t].get(y, 0.0)) or 0.0)
            caps[t][y] = share * r
    return caps


def _set_capacity_constraint(cn, tech, kind, values, years):
    """Write a min or max row {year: MW of output} into the capacity constraints (course table, per vintage)."""
    row = pd.DataFrame([[np.nan] * len(cn.columns)], columns=cn.columns,
                       index=pd.MultiIndex.from_tuples([(tech, kind)], names=cn.index.names))
    if 'Unit' in row.columns:
        row['Unit'] = 'MW'
    for y in years:
        if y in values and y in row.columns:
            row[y] = float(values[y])
    cn = pd.concat([cn.drop(index=(tech, kind), errors='ignore'), row])
    return cn.sort_index()


# --------------------------------------------------------------------------
# 2. Input changes (before the network is built)
# --------------------------------------------------------------------------

def apply_scenario_inputs(techs_s, techs_d, resources_pars, cn, scen, years):
    """Apply the scenario (electrolyser capacity) and the data settings and sensitivities to the input data.

    Note: techs_d is already in €/MW and €/MWh here (preprocessing multiplied by 1e3).
    """
    techs_s, techs_d, resources_pars, cn = techs_s.copy(), techs_d.copy(), resources_pars.copy(), cn.copy()

    # Options (off by default): the technologies of an option that is not switched on are disabled
    for option, techs in OPTION_TECHS.items():
        if not scen.get(option, False):
            _disable(techs_s, techs)
    if not scen.get('grid_electrolysis', True):
        _disable(techs_s, ELECTROLYSIS_GRID)

    # (1) Freshwater availability: the largest grid-electrolyser capacity per vintage.
    limit_on = scen.get('electrolyser_limit_on', 'capacity')
    if limit_on == 'capacity':
        caps = electrolyser_caps(scen, years)
        if caps is not None:
            for t, c in caps.items():
                cn = _set_capacity_constraint(cn, t, 'max', c, years)
            scen['_electrolyser_caps_mw_h2'] = {t: {str(y): float(v) for y, v in c.items()}
                                                for t, c in caps.items()}       # kept on n.meta
            total = electrolyser_total_cap(scen, years)
            if total is not None:
                scen['_electrolyser_cap_total_mw_h2'] = {str(y): float(v) for y, v in total.items()}
    elif limit_on == 'output':
        # the plant (min = max per vintage): electrolyser_plant_reference, or else the reference run itself. The water
        # limit: p_max_pu = share (apply_network_settings), or, with a separate plant, an hourly cap on the output of all
        # electrolysers together at share x the water reference (make_extra_functionality)
        ref = _per_tech(scen.get('electrolyser_plant_reference') or scen.get('electrolyser_reference'))
        if not ref:
            raise ValueError("electrolyser_limit_on='output' needs electrolyser_reference (the plant of the S1 run)")
        if scen.get('electrolyser_plant_reference'):
            water = _per_tech(scen.get('electrolyser_reference'))
            share = float(scen.get('electrolyser_cap_share') or 0.0)
            scen['_electrolyser_water_mw_h2'] = {
                str(y): share * sum(float(d.get(str(y), d.get(y, 0.0)) or 0.0) for d in water.values())
                for y in years if y >= scen.get('cap_from', 2030)}
        fixed = {}
        for t in electrolyser_techs(scen):
            size = {y: float(ref.get(t, {}).get(str(y), 0.0) or 0.0) for y in years if y >= scen.get('cap_from', 2030)}
            cn = _set_capacity_constraint(cn, t, 'max', size, years)
            cn = _set_capacity_constraint(cn, t, 'min', size, years)
            fixed[t] = {str(y): v for y, v in size.items()}
        scen['_electrolyser_fixed_mw_h2'] = fixed
    else:
        raise ValueError("electrolyser_limit_on must be 'capacity' or 'output'")

    # (2c) H2 storage cost (option)
    for t in H2_STORAGE:
        for par in ('CAPEX', 'FOM'):
            if _has(techs_d, t, par):
                techs_d.loc[(t, par), years] = techs_d.loc[(t, par), years].values * scen.get('h2_storage_cost_factor', 1.0)

    # VOM convention check (applies to every technology, so the comparison stays like-for-like)
    if scen.get('vom_scale', 1.0) != 1.0:
        vom = techs_d.index.get_level_values('Parameter') == 'VOM'
        techs_d.loc[vom, years] = techs_d.loc[vom, years].values * scen['vom_scale']

    # (2a) Electrolyser CAPEX path (€/kW_e -> €/kW_H2 output via the efficiency), then the subsidy
    if scen.get('electrolyser_capex') is not None:
        capex_e = _per_year(scen['electrolyser_capex'], years, 'electrolyser_capex') * 1e3  # €/MW_e
        for t in ELECTROLYSIS:
            if _has(techs_d, t, 'CAPEX'):
                eff = techs_d.loc[(t, 'Efficiency'), years].values.astype(float)
                old = techs_d.loc[(t, 'CAPEX'), years].values.astype(float)
                new = capex_e.values / eff
                techs_d.loc[(t, 'CAPEX'), years] = new
                if _has(techs_d, t, 'FOM'):   # FOM is a share of CAPEX, keep that share
                    techs_d.loc[(t, 'FOM'), years] = techs_d.loc[(t, 'FOM'), years].values * new / old
    sub = _per_year(scen['electrolyser_subsidy'], years)
    infrastructure_sub = _per_year(scen['infrastructure_subsidy'], years)
    total_sub = 1 - (1 - sub) * (1 - infrastructure_sub)
    scen['_subsidy_eur_per_mw_h2'] = {}          # kept on n.meta, used by h2_results.subsidy_cost()
    scen['_infrastructure_subsidy_eur_per_mw_h2'] = {}
    scen['_capex_eur_per_mw_h2'] = {}            # electrolyser CAPEX before the subsidy (investment outputs)
    for t in ELECTROLYSIS:
        if _has(techs_d, t, 'CAPEX'):
            capex = techs_d.loc[(t, 'CAPEX'), years].values.astype(float)
            scen['_capex_eur_per_mw_h2'][t] = {str(y): float(v) for y, v in zip(years, capex)}
            scen['_subsidy_eur_per_mw_h2'][t] = {str(y): float(v) for y, v in zip(years, capex * total_sub.values)}
            scen['_infrastructure_subsidy_eur_per_mw_h2'][t] = {
                str(y): float(v) for y, v in zip(years, capex * infrastructure_sub.values)
            }
            techs_d.loc[(t, 'CAPEX'), years] = capex * (1 - total_sub.values)

    # Green levers: the cost of desalinated water and an operating subsidy per kg, both as variable cost (VOM, € per
    # MWh of electricity INPUT = € per kg x kg per MWh of hydrogen x efficiency)
    for t in ELECTROLYSIS:
        if not (_has(techs_d, t, 'VOM') and _has(techs_d, t, 'Efficiency')):
            continue
        eff = techs_d.loc[(t, 'Efficiency'), years].values.astype(float)
        add = np.zeros(len(years))
        if t in ELECTROLYSIS_SEAWATER:
            add += float(scen.get('desal_cost_eur_per_kg', 0.0)) * KG_PER_MWH_H2 * eff
        add -= float(scen.get('h2_production_subsidy', 0.0)) * KG_PER_MWH_H2 * eff
        if add.any():
            techs_d.loc[(t, 'VOM'), years] = techs_d.loc[(t, 'VOM'), years].values.astype(float) + add
    scen['_prod_subsidy_eur_per_mwh_h2'] = float(scen.get('h2_production_subsidy', 0.0)) * KG_PER_MWH_H2

    # (2b) CO2 price (€/tCO2). The database row is called "CO2 atmosphere / Price".
    if scen['co2_price'] is not None:
        price = _per_year(scen['co2_price'], years, 'co2_price')
        if scen['co2_price_scope'] == 'all':
            _set_resource(resources_pars, 'CO2 atmosphere', 'Price', price.values, years)
        elif scen['co2_price_scope'] == 'h2':
            for t in GREY + BLUE:
                if _has(techs_d, t, 'Emissions'):
                    techs_d.loc[(t, 'VOM'), years] = (techs_d.loc[(t, 'VOM'), years].values
                                                      + price.values * techs_d.loc[(t, 'Emissions'), years].values)
        else:
            raise ValueError("co2_price_scope must be 'all' or 'h2'")

    # Natural gas price path and reserve
    if scen.get('gas_price') is not None:
        _set_resource(resources_pars, 'Gas supply', 'Price',
                      _per_year(scen['gas_price'], years, 'gas_price').values, years)
    if scen.get('gas_reserve') is not None:
        _set_resource(resources_pars, 'Gas supply', 'Reserves', float(scen['gas_reserve']), years)

    # CO2 transport and storage cost (€/tCO2 captured), applies to every CCS technology
    if scen.get('co2_storage_price') is not None:
        _set_resource(resources_pars, 'CO2 storage', 'Price',
                      _per_year(scen['co2_storage_price'], years, 'co2_storage_price').values, years)

    # CAPEX multipliers per technology (cost variations)
    for t, f in (scen.get('capex_factors') or {}).items():
        if _has(techs_d, t, 'CAPEX'):
            techs_d.loc[(t, 'CAPEX'), years] = techs_d.loc[(t, 'CAPEX'), years].values * float(f)

    # (3) Batteries
    for t in BATTERY:
        if not scen['battery']:
            _disable(techs_s, [t])
            continue
        hours = scen['battery_max_hours']
        factor = scen['battery_cost_factor']
        if hours is not None:
            base_hours = float(techs_s.at[(t, 'Max hours'), 'Value']) if (t, 'Max hours') in techs_s.index else 1.0
            techs_s.loc[(t, 'Max hours'), 'Value'] = hours
            # the database CAPEX is for a battery of base_hours; scale it with the energy capacity
            factor = factor * hours / base_hours
        if _has(techs_d, t, 'CAPEX'):
            techs_d.loc[(t, 'CAPEX'), years] = techs_d.loc[(t, 'CAPEX'), years].values * factor

    # [Freight] BET costs, gasoline price, FCET / ICE-only switches
    techs_s, techs_d, resources_pars = apply_freight_inputs(techs_s, techs_d, resources_pars, scen, years)
    # [Freight] calibration test (truck_stock=False): without the 2020 truck stock the 'existing' trucks are off and
    # the base-year limits of the trucks are dropped, so the model builds new ICE trucks and BETs in 2020
    if not scen.get('truck_stock', True):
        _disable(techs_s, ['ICE truck - existing', 'BET - existing'])
        cn = cn.drop(index=[(t, k) for t in ('ICE truck', 'BET', 'BET - existing') for k in ('min', 'max')],
                     errors='ignore')
    return techs_s, techs_d, resources_pars, cn


# --------------------------------------------------------------------------
# 3. Changes to the built network
# --------------------------------------------------------------------------

def ets2_price(scen, years):
    """ETS2 price per period (pd.Series, €/tCO2) for ETS2_TECHS, or None if they pay the ETS1 price."""
    v = scen.get('co2_price_ets2', 'auto')
    if v is None or scen.get('co2_price') is None or scen.get('co2_price_scope', 'all') != 'all':
        return None
    if isinstance(v, str) and v == 'auto':
        v = scen['co2_price'] if isinstance(scen['co2_price'], str) else None
        if v not in CO2_PRICES_ETS2:
            return None          # own ETS1 values: households and cars pay the same price
    return _per_year(v, years, 'co2_price_ets2')


def set_period_prices(n, resources_pars, years, overrides=None):
    """Let every link pay the fuel, CO2 and CO2-storage prices of the PERIOD it operates in.

    The course code fixes these prices at the build year of each vintage (a 2030 SMR would pay the
    2030 CO2 price until 2060). Here the static marginal cost is split into VOM (vintage) and bus
    prices (period), and a time-varying marginal cost is set per snapshot.
    overrides: {link carrier: {bus: pd.Series of prices per year}}, e.g. the ETS2 price on the
    'CO2 atmosphere' bus for the household gas boilers and petrol cars.
    """
    price = resources_pars[resources_pars.Parameter == 'Price'].set_index('Resource')[years].astype(float)
    per = n.snapshots.get_level_values(0)
    overrides = overrides or {}
    mc = {}
    for name, l in n.links.iterrows():
        try:
            y = int(name.rsplit('_', 1)[1])
        except (IndexError, ValueError):
            continue
        buses = [(l.bus0, 1.0), (l.bus1, l.efficiency)]
        for i in (2, 3):
            b = l.get(f'bus{i}', '')
            if isinstance(b, str) and b:
                buses.append((b, l[f'efficiency{i}']))
        priced = [(b, f) for b, f in buses if b in price.index]
        if not priced or y not in years:
            continue
        vom = l.marginal_cost - sum(price.at[b, y] * f for b, f in priced)   # the build-year prices of model.py
        own = overrides.get(l.carrier, {})
        mc[name] = vom + sum((own[b] if b in own else price.loc[b]).loc[per].values * f for b, f in priced)
    if mc:
        n.links_t.marginal_cost = pd.DataFrame(mc, index=n.snapshots)


def apply_network_settings(n, scen, techs_d, resources_pars, years):
    """Settings that act on the built network: prices per period, the use of the hydrogen demand, demand path."""
    ets2 = ets2_price(scen, years)
    overrides = {t: {'CO2 atmosphere': ets2} for t in ETS2_TECHS} if ets2 is not None else None

    # Fixing default mismatch
    if scen.get('period_prices', True):
        set_period_prices(n, resources_pars, years, overrides)
    elif ets2 is not None:       # prices of the build year: swap the ETS1 part for the ETS2 price of that year
        co2 = resources_pars[(resources_pars.Resource == 'CO2 atmosphere')
                             & (resources_pars.Parameter == 'Price')][years].astype(float).iloc[0]
        for name in n.links.index[n.links.carrier.isin(ETS2_TECHS) & (n.links.bus2 == 'CO2 atmosphere')]:
            y = int(name.rsplit('_', 1)[1])
            n.links.at[name, 'marginal_cost'] += (ets2[y] - co2[y]) * n.links.at[name, 'efficiency2']
    if ets2 is not None:
        n.meta = {**n.meta, 'co2_price_ets2': {str(y): float(v) for y, v in ets2.items()}}

    # Storage cycles within each period. PyPSA 1.3 defaults to one cycle over the whole horizon, which lets a
    # battery or the H2 store fill in the 2040 representative year and empty in 2050.
    if scen.get('storage_cyclic_per_period', True):
        if len(n.storage_units):
            n.storage_units['cyclic_state_of_charge_per_period'] = True
        if len(n.stores):
            ext = n.stores.e_nom_extendable          # only built storage, not the fuel reserves or CO2 stores
            n.stores.loc[ext, 'e_cyclic_per_period'] = True

    # Over-dimensioned plant: water lets the electrolysers run at no more than this share of their capacity
    if (scen.get('electrolyser_limit_on', 'capacity') == 'output' and scen.get('electrolyser_cap_share') is not None
            and not scen.get('electrolyser_plant_reference')):
        ely = n.links.index[n.links.carrier.isin(ELECTROLYSIS)]
        n.links.loc[ely, 'p_max_pu'] = float(scen['electrolyser_cap_share'])

    per = n.snapshots.get_level_values(0)
    if scen.get('h2_demand_mt') is not None and H2_LOAD in n.loads.index:
        mt = _per_year(scen['h2_demand_mt'], years, 'h2_demand_mt')
        mw = mt * 1e6 * MWH_PER_T_H2 / 8760.0                      # flat MW
        n.loads_t.p_set[H2_LOAD] = mw.loc[per].values

    # What the hydrogen demand is used for (Francesco, 14 Oct):
    #   feedstock (refineries, ammonia): a separate demand stream on top of the course demands, nothing subtracted;
    #   fuel for high-temperature heat: subtract the heat it delivers from the industrial HTP demand.
    use = scen.get('h2_demand_use', 'feedstock')
    if use == 'htp_fuel' and H2_LOAD in n.loads.index and 'industrial_htp' in n.loads.index:
        eff = float(techs_d.at[('Industrial HTP - fossil - existing', 'Efficiency'), years[0]])
        red = n.loads_t.p_set[H2_LOAD] * eff               # MW of heat that this hydrogen delivers in a furnace
        htp = n.loads_t.p_set['industrial_htp']
        if (htp - red).min() < 0:
            raise ValueError('The hydrogen demand is larger than the industrial HTP demand')
        n.loads_t.p_set['industrial_htp'] = htp - red
        n.meta = {**n.meta, 'htp_reduction_twh': {str(y): float((red[per == y] * n.snapshot_weightings.generators[
            per == y]).sum() / 1e6) for y in years}}
    elif use not in ('feedstock', 'htp_fuel'):
        raise ValueError("h2_demand_use must be 'feedstock' or 'htp_fuel'")

    # [Freight] freight demand profile (time restrictions) and scale; water: summer derating of thermal plants
    apply_freight_network(n, scen, scen.get('_db_dir'))
    apply_water_network(n, scen)
