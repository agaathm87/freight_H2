"""Scenario logic for the freight extension and the water module.

Called from h2_scenario (input data and the built network) and h2_constraints (extra constraints). Every function is a
no-op when the database has no freight technologies or the setting is off, so the hydrogen package runs unchanged.
"""
import numpy as np
import pandas as pd
import xarray as xr

from .freight_presets import (TRUCK_FUEL_PRICES, TRUCK_TOLLS, BET_SUBSIDIES, H2TRUCK_SUBSIDIES, TOLL_KWH_OUT_PER_KM,
                              ICE_TRUCKS, RFNBO_TRANSPORT, ROAD_TRANSPORT, GREEN_MANDATES, CO2_CAPS, ZE_MANDATES,
                              BET_COSTS, GASOLINE_PRICES, FCETS, ZE_TRUCKS, FREIGHT_LOAD, H2ICE_TRUCKS, HYDROGEN_TRUCKS,
                              H2ICE_ENGINE_VOM, BET_TIERS, BET_TIER_TECHS, H2_TRUCK_SHARES, BETS,
                              FREIGHT_PROFILES, WATER_SCARCITY, WATER_GROUPS, WATER_INTENSITY,
                              WATER_PER_TCO2_CAPTURED, THERMAL_FRESHWATER, SUMMER_MONTHS, DROUGHTS,
                              WATER_USE_GROUP, WATER_GROUP_CATEGORY, WATER_REFERENCE_DRY, WATER_ALT_COSTS)


def _series(value, years, presets=None):
    """A setting as a Series over the model years: a scalar, a preset name (key of `presets`) or a {year: value}
    dict, interpolated between the given years and filled forward and backward (so give every period)."""
    if isinstance(value, str):
        value = presets[value]
    if isinstance(value, dict):
        s = pd.Series({int(k): float(v) for k, v in value.items()})
        return s.reindex(sorted(set(s.index) | set(years))).interpolate(method='index').ffill().bfill().loc[years]
    return pd.Series(float(value), index=years)


def _tech(name):
    """Technology name of a component name such as 'CCGT - existing_2020'."""
    return name.rsplit('_', 1)[0]


# --------------------------------------------------------------------------------------------------------------
# 1. Input data (before the network is built; techs_d is in €/MW and €/MWh here)
# --------------------------------------------------------------------------------------------------------------

def apply_freight_inputs(techs_s, techs_d, resources_pars, scen, years):
    """Apply the freight settings to the technology and resource tables before the network is built (in place; also
    returned). In order: BET costs (X axis) and the charging-penalty factor, FCET and H2-ICE factors, the AanZET and
    SWiM purchase subsidies, the BET duty-cycle tiers (BET values x factors), the truck toll (VOM per MWh of output),
    the gasoline price (Y axis) and the trucks' own diesel price; then switches technologies off (no hydrogen trucks,
    ICE-only counterfactual, no tiers). techs_d is in €/MW and €/MWh here."""
    has = lambda t, p: (t, p) in techs_d.index
    if scen.get('bet_costs') is not None:
        costs = BET_COSTS[scen['bet_costs']] if isinstance(scen['bet_costs'], str) else scen['bet_costs']
        for par in ('CAPEX', 'VOM'):
            if par in costs and has('BET', par):
                techs_d.loc[('BET', par), years] = _series(costs[par], years).values * 1e3
    if has('BET', 'VOM') and scen.get('bet_vom_factor', 1.0) != 1.0:
        techs_d.loc[('BET', 'VOM'), years] = techs_d.loc[('BET', 'VOM'), years].values * float(scen['bet_vom_factor'])
    if has('FCET', 'CAPEX') and scen.get('fcet_capex_factor', 1.0) != 1.0:
        techs_d.loc[('FCET', 'CAPEX'), years] = techs_d.loc[('FCET', 'CAPEX'), years].values * scen['fcet_capex_factor']
    if has('FCET', 'VOM') and scen.get('fcet_vom_factor', 1.0) != 1.0:
        techs_d.loc[('FCET', 'VOM'), years] = techs_d.loc[('FCET', 'VOM'), years].values * scen['fcet_vom_factor']
    # H2-ICE truck: CAPEX factor; the hydrogen delivery + station part of its VOM follows fcet_vom_factor (same
    # stations), the engine part (H2ICE_ENGINE_VOM) does not
    h2 = 'H2-ICE truck'
    if has(h2, 'CAPEX') and scen.get('h2ice_capex_factor', 1.0) != 1.0:
        techs_d.loc[(h2, 'CAPEX'), years] = techs_d.loc[(h2, 'CAPEX'), years].values * float(scen['h2ice_capex_factor'])
    if has(h2, 'VOM') and scen.get('fcet_vom_factor', 1.0) != 1.0:
        eng = H2ICE_ENGINE_VOM * 1e3
        v = techs_d.loc[(h2, 'VOM'), years].values.astype(float)
        techs_d.loc[(h2, 'VOM'), years] = (v - eng) * float(scen['fcet_vom_factor']) + eng
    # battery-truck policies: AanZET purchase subsidy (share of BET CAPEX) and the CO2-differentiated truck toll
    if scen.get('bet_capex_subsidy') is not None and has('BET', 'CAPEX'):
        sub = _series(scen['bet_capex_subsidy'], years, BET_SUBSIDIES)
        scen['_bet_subsidy_eur_per_mw'] = {str(y): float(v) for y, v in
                                           zip(years, techs_d.loc[('BET', 'CAPEX'), years].values * sub.values)}
        techs_d.loc[('BET', 'CAPEX'), years] = techs_d.loc[('BET', 'CAPEX'), years].values * (1 - sub.values)
    # SWiM: share of the hydrogen trucks' CAPEX paid by subsidy (FCET and H2-ICE truck), per build year
    if scen.get('h2truck_capex_subsidy') is not None:
        sub = _series(scen['h2truck_capex_subsidy'], years, H2TRUCK_SUBSIDIES)
        scen['_h2truck_subsidy_eur_per_mw'] = {}           # kept on n.meta for the transfer accounting
        for t in ('FCET', 'H2-ICE truck'):
            if has(t, 'CAPEX'):
                capex = techs_d.loc[(t, 'CAPEX'), years].values.astype(float)
                scen['_h2truck_subsidy_eur_per_mw'][t] = {str(y): float(v) for y, v in zip(years, capex * sub.values)}
                techs_d.loc[(t, 'CAPEX'), years] = capex * (1 - sub.values)
    # realistic layer: BETs by duty cycle take the (scenario) BET costs times their factors, before the toll is added
    tiers = scen.get('bet_tiers')
    if tiers:
        tiers = BET_TIERS[tiers] if isinstance(tiers, str) else tiers
        for t, f in tiers.items():
            if t == 'BET':
                continue
            for par, k in (('CAPEX', 'capex'), ('FOM', 'capex'), ('VOM', 'vom')):
                if has(t, par) and has('BET', par):
                    techs_d.loc[(t, par), years] = techs_d.loc[('BET', par), years].values.astype(float) * float(f[k])
    if scen.get('truck_toll') is not None:
        toll = TRUCK_TOLLS[scen['truck_toll']] if isinstance(scen['truck_toll'], str) else scen['truck_toll']
        for group, techs in (('ICE', ICE_TRUCKS), ('ZE', ZE_TRUCKS)):
            eur_per_mwh_out = _series(toll[group], years).values / TOLL_KWH_OUT_PER_KM * 1e3
            for tt in techs:
                if has(tt, 'VOM') and has(tt, 'Efficiency'):
                    eff = techs_d.loc[(tt, 'Efficiency'), years].values.astype(float)
                    vom = techs_d.loc[(tt, 'VOM'), years].values.astype(float)
                    techs_d.loc[(tt, 'VOM'), years] = vom + eur_per_mwh_out * eff
    if scen.get('gasoline_price') is not None:
        row = (resources_pars.Resource == 'Gasoline supply') & (resources_pars.Parameter == 'Price')
        resources_pars.loc[row, years] = _series(scen['gasoline_price'], years, GASOLINE_PRICES).values
    # own fuel price for ICE trucks (diesel ex VAT) on top of the shared gasoline bus: VOM += diesel - gasoline
    if scen.get('truck_fuel_price') is not None:
        row = (resources_pars.Resource == 'Gasoline supply') & (resources_pars.Parameter == 'Price')
        gas_p = resources_pars.loc[row, years].astype(float).values[0]
        diff = _series(scen['truck_fuel_price'], years, TRUCK_FUEL_PRICES).values - gas_p
        for tt in ICE_TRUCKS:
            if has(tt, 'VOM'):
                techs_d.loc[(tt, 'VOM'), years] = techs_d.loc[(tt, 'VOM'), years].values.astype(float) + diff
    off = []
    if not scen.get('fcet', True) or scen.get('ice_only'):
        off += FCETS
    h2ice = scen.get('h2ice')
    if h2ice is None:                   # default: the hydrogen trucks come together (the extension)
        h2ice = scen.get('fcet', True)
    if not h2ice or scen.get('ice_only'):
        off += H2ICE_TRUCKS
    if scen.get('ice_only'):
        off += ['BET']                  # 'BET - existing' (the 2020 stock) stays: the base year is the same
    if not scen.get('bet_tiers') or scen.get('ice_only'):
        off += BET_TIER_TECHS
    for t in off:
        if (t, 'Type') in techs_s.index:
            techs_s.loc[(t, 'Type'), 'Value'] = 'Disabled'
    return techs_s, techs_d, resources_pars


def _shares(d):
    """{category: share} of one drought: a key of DROUGHTS or a dict (keys made int); None for no drought."""
    if not d:
        return None
    d = DROUGHTS[d] if isinstance(d, str) else d
    return {int(k): float(v) for k, v in d.items()}


def drought_shares(drought):
    """Resolve a drought setting into (shares, by_year). A single drought (key of DROUGHTS or {category: share})
    applies to every period: (shares, None). A path {year: drought} is the water-scarcity driver: by_year holds the
    shares per period (a period without a drought is unrestricted) and shares the lowest share of each category over
    the path (the categories that are ever restricted)."""
    if not drought:
        return None, None
    if isinstance(drought, dict) and all(int(k) >= 2000 for k in drought):
        by_year = {int(y): _shares(v) or {} for y, v in drought.items()}
        cats = {c for s in by_year.values() for c in s}
        return {c: min(s.get(c, 1.0) for s in by_year.values()) for c in cats} or None, by_year
    return _shares(drought), None


def drought_share(ws, c, y):
    """Share of its reference drought-season water that category c may use in period y (1 = unrestricted)."""
    if ws.get('drought_by_year') is not None:
        return ws['drought_by_year'].get(int(y), {}).get(c, 1.0)
    return (ws.get('drought') or {}).get(c, 1.0)


def _per_period(value, periods):
    """A number or a {year: number} path (e.g. the summer derating) as one value per period (0 where not given)."""
    if isinstance(value, dict):
        return {int(y): float(value.get(int(y), value.get(str(y), 0.0)) or 0.0) for y in periods}
    return {int(y): float(value or 0.0) for y in periods}


def water_settings(scen):
    """Resolve the water-scarcity level and the overrides into one dict (caps, budget, summer, derate). The drought
    and the summer derating may be paths over the periods (the water-scarcity driver, level 'driver')."""
    lvl = scen.get('water_scarcity') or 'none'
    w = dict(WATER_SCARCITY[lvl]) if isinstance(lvl, str) else {**WATER_SCARCITY['none'], **lvl}
    caps = scen.get('water_caps') if scen.get('water_caps') is not None else w.get('caps')
    f = float(scen.get('water_cap_factor', 1.0))
    w['caps'] = {g: {int(y): float(v) * f for y, v in c.items()} for g, c in (caps or {}).items()}
    budget = scen.get('water_budget') if scen.get('water_budget') is not None else w.get('budget')
    if budget is not None and not isinstance(budget, dict):
        budget = {y: budget for y in (2030, 2040, 2050)}
    bf = float(scen.get('water_budget_factor', 1.0))
    w['budget'] = {int(y): float(v) * bf for y, v in budget.items()} if budget else None
    if scen.get('water_summer_factor') is not None:
        w['summer'] = scen['water_summer_factor']
    drought = scen.get('water_drought') if scen.get('water_drought') is not None else w.get('drought')
    w['drought'], w['drought_by_year'] = drought_shares(drought)
    w['drought_months'] = tuple(scen.get('water_drought_months') or SUMMER_MONTHS)
    w['electrolysis_category'] = int(scen.get('electrolysis_category') or 3)
    w['allocation'] = scen.get('water_allocation') or 'verdringingsreeks'
    if w['allocation'] not in ('verdringingsreeks', 'cost_optimal'):
        raise ValueError("water_allocation must be 'verdringingsreeks' or 'cost_optimal'")
    if scen.get('thermal_summer_derate') is not None:
        w['derate'] = scen['thermal_summer_derate']
    alt = scen.get('water_alt_cost', w.get('alt_cost', 1.4))
    w['alt_cost'] = WATER_ALT_COSTS[alt] if isinstance(alt, str) else alt
    w['intensity'] = {**WATER_INTENSITY, **(scen.get('water_intensity') or {})}
    return w


# --------------------------------------------------------------------------------------------------------------
# 2. The built network
# --------------------------------------------------------------------------------------------------------------

def _freight_profile(n, column, db_dir):
    """Normalised alternative profile (sheet 'freight_profiles'), resampled like the course profiles."""
    from .preprocessing import propagate_profiles
    years = list(n.investment_periods)
    t_res = int(round(float(n.snapshot_weightings.generators.iloc[0])))
    prof = pd.read_excel(f'{db_dir}//demand.xlsx', sheet_name='freight_profiles').set_index('time')[[column]]
    prj = propagate_profiles(prof, model_years=years, t_res=t_res)
    return prj[column].values


def apply_freight_network(n, scen, db_dir=None):
    """Settings that act on the built network: the temporal profile of the freight demand (base, Sunday ban or night
    ban, from the database's profile sheet) and its scale (freight_scale)."""
    if FREIGHT_LOAD not in n.loads.index:
        return
    per = n.snapshots.get_level_values(0)
    w = n.snapshot_weightings.generators
    p = n.loads_t.p_set[FREIGHT_LOAD] * float(scen.get('freight_scale', 1.0))
    col = FREIGHT_PROFILES.get(scen.get('freight_profile', 'base'), scen.get('freight_profile'))
    if col != FREIGHT_PROFILES['base'] and db_dir is not None:
        shape = pd.Series(_freight_profile(n, col, db_dir), index=n.snapshots)
        for y in n.investment_periods:
            sl = per == y
            energy = float((p[sl] * w[sl]).sum())
            p[sl] = shape[sl] / float((shape[sl] * w[sl]).sum()) * energy
    n.loads_t.p_set[FREIGHT_LOAD] = p


def apply_water_network(n, scen):
    """Summer derating of freshwater-cooled thermal plants (cooling-water temperature and discharge limits); a number
    or a path per period (the water-scarcity driver). Also stores the resolved water settings on n.meta."""
    ws = water_settings(scen)
    quota, pool = drought_quotas(ws)
    derate = _per_period(ws.get('derate'), n.investment_periods)
    by_year = ws.get('drought_by_year')
    n.meta = {**n.meta, 'water': {'budget': {str(k): v for k, v in (ws.get('budget') or {}).items()},
                                  'summer': ws.get('summer'), 'alt_cost': ws.get('alt_cost'),
                                  'derate': {str(y): v for y, v in derate.items()},
                                  'caps': {g: {str(k): v for k, v in c.items()} for g, c in ws['caps'].items()},
                                  'drought': None if not ws.get('drought') else {
                                      'shares': {str(k): v for k, v in ws['drought'].items()},
                                      'shares_by_year': None if by_year is None else {
                                          str(y): {str(c): v for c, v in s.items()} for y, s in by_year.items()},
                                      'months': list(ws['drought_months']),
                                      'allocation': ws['allocation'],
                                      'electrolysis_category': ws['electrolysis_category'],
                                      'quota_mm3': {str(c): {str(y): v for y, v in d.items()}
                                                    for c, d in quota.items()},
                                      'pool_mm3': {str(y): v for y, v in pool.items()}}}}
    if max(derate.values(), default=0.0) <= 0:
        return
    summer = np.isin(n.snapshots.get_level_values(1).month, SUMMER_MONTHS)
    d = np.array([derate[int(y)] for y in n.snapshots.get_level_values(0)])
    links = [l for l in n.links.index if _tech(l) in THERMAL_FRESHWATER]
    pu = {}
    for l in links:
        fresh = ws['intensity'].get(_tech(l), (0, 1.0))[1]
        pu[l] = np.where(summer, 1.0 - d * fresh, 1.0)
    if pu:
        df = pd.DataFrame(pu, index=n.snapshots)
        n.links_t.p_max_pu = pd.concat([n.links_t.p_max_pu.drop(columns=df.columns, errors='ignore'), df], axis=1)


# --------------------------------------------------------------------------------------------------------------
# 3. Extra constraints
# --------------------------------------------------------------------------------------------------------------

def _period_pos(sns, y):
    """Integer positions of the snapshots of investment period y."""
    return np.where(sns.get_level_values(0) == y)[0]


def _flow(n, links, sns, pos, coeff_per_link):
    """sum_t sum_l w_t * coeff_l * p0_lt for links in the snapshots at pos (a linopy expression)."""
    p = n.model['Link-p']
    dim = [d for d in p.dims if d != 'snapshot'][0]
    w = n.snapshot_weightings.generators.iloc[pos].values
    return (p.isel(snapshot=pos).sel({dim: list(links)}) * np.outer(w, coeff_per_link)).sum()


def _gen_flow(n, gens, sns, pos, coeff_per_gen):
    """Linear expression: the weighted output of these generators over the snapshots at `pos`, each times its
    coefficient (e.g. water per MWh)."""
    p = n.model['Generator-p']
    dim = [d for d in p.dims if d != 'snapshot'][0]
    w = n.snapshot_weightings.generators.iloc[pos].values
    return (p.isel(snapshot=pos).sel({dim: list(gens)}) * np.outer(w, coeff_per_gen)).sum()


def freshwater_coefficients(n, ws):
    """{component: (names, m3 of freshwater per MW of the optimisation variable per hour)}."""
    links, lc, gens, gc = [], [], [], []
    for l in n.links.index:
        t = _tech(l)
        c = 0.0
        if t in ws['intensity']:                                       # per MWh of output -> per MWh of input (p0)
            m3, fresh = ws['intensity'][t]
            c += m3 * fresh * float(n.links.at[l, 'efficiency'])
        if t in WATER_PER_TCO2_CAPTURED:                               # industrial CCS: per t captured (bus3)
            m3, fresh = WATER_PER_TCO2_CAPTURED[t]                     # (both terms: the CCS links are also in
            c += m3 * fresh * float(n.links.at[l, 'efficiency3'])      #  the intensity table, with 0 per MWh)
        if c > 0:
            links.append(l); lc.append(c)
    for g in n.generators.index:
        m3, fresh = ws['intensity'].get(_tech(g), (0.0, 0.0))
        if m3 * fresh > 0:
            gens.append(g); gc.append(m3 * fresh)
    return links, np.array(lc), gens, np.array(gc)


def water_category(tech, ws):
    """Verdringingsreeks category (2, 3 or 4) of a technology, or None if it uses no freshwater."""
    g = WATER_USE_GROUP.get(tech)
    if g is None:
        return None
    c = WATER_GROUP_CATEGORY[g]
    return ws['electrolysis_category'] if c is None else c


def drought_quotas(ws):
    """Drought-season water per category ({category: {year: Mm3}}: share x the reference use of the groups in it)
    and the pool for the cost-optimal allocation ({year: Mm3}: the same water in total, all categories)."""
    if not ws.get('drought'):
        return {}, {}
    ref = {}
    for g, d in WATER_REFERENCE_DRY.items():
        c = WATER_GROUP_CATEGORY[g] or ws['electrolysis_category']
        for y, v in d.items():
            ref.setdefault(c, {})
            ref[c][int(y)] = ref[c].get(int(y), 0.0) + float(v)
    quota = {c: {y: drought_share(ws, c, y) * v for y, v in d.items()} for c, d in ref.items()}
    years = sorted({y for d in quota.values() for y in d})
    pool = {y: sum(d.get(y, 0.0) for d in quota.values()) for y in years}
    return quota, pool


def season_use(n, ws=None, months=None):
    """Freshwater use per verdringingsreeks category in the drought season (Mm3), per period, from a solved run."""
    ws = ws or water_settings({})
    months = months or ws.get('drought_months') or SUMMER_MONTHS
    links, lc, gens, gc = freshwater_coefficients(n, ws)
    w = n.snapshot_weightings.generators
    dry = np.isin(n.snapshots.get_level_values(1).month, months)
    use = pd.concat([(n.links_t.p0.reindex(columns=links, fill_value=0.0) * lc).mul(w, axis=0),
                     (n.generators_t.p.reindex(columns=gens, fill_value=0.0) * gc).mul(w, axis=0)], axis=1)
    cat = {c: water_category(_tech(c), ws) for c in use.columns}
    return use[dry].groupby(level=0).sum().T.groupby(cat).sum().T / 1e6


def add_constraints(n, sns, scen):
    """Add the freight and water constraints to the linopy model n.model (called from h2_constraints after the
    group's constraints). (a) caps on the water-scarce capacity per group; (b) the freshwater budget (year and
    summer) and (b2) the verdringingsreeks drought quotas, with alternative water above them;
    (c) zero-emission share of freight (max: diffusion / market ramp-up; min: mandate or CO2-standards floor);
    (c2) the realistic layer's caps (BET duty cycles, hydrogen-truck availability, heavy special segment);
    (d) the net-zero CO2 cap; (e) the RED III transport target for renewable hydrogen. Constraint names end in
    '-<year>' so that store_shadow_prices can map their duals."""
    periods = sns.get_level_values(0).unique()
    m = n.model
    ws = water_settings(scen)

    # (a) water caps on the capacity that may operate in each period, per group (all vintages together)
    for g, cap in ws['caps'].items():
        spec = WATER_GROUPS[g]
        var = m['Link-p_nom']
        dim = var.dims[0]
        for y in periods:
            if y not in cap:
                continue
            act = n.get_active_assets('Link', y)
            names = [l for l in n.links.index[n.links.carrier.isin(spec['carriers'])] if act.get(l, False)]
            ext = [l for l in names if n.links.at[l, 'p_nom_extendable']]
            if not ext:
                continue
            k = n.links.loc[ext, 'efficiency'].values if spec['basis'] == 'output' else np.ones(len(ext))
            fixed = sum(float(n.links.at[l, 'p_nom']) * (float(n.links.at[l, 'efficiency'])
                        if spec['basis'] == 'output' else 1.0) for l in names if l not in ext)
            coef = xr.DataArray(k, coords={dim: ext})
            m.add_constraints((var.sel({dim: ext}) * coef).sum() <= cap[y] - fixed,
                              name=f"Water-cap-{g.replace(' ', '_')}-{y}")

    # (b) a freshwater budget for all energy technologies together (and a tighter one in summer). Freshwater above
    #     the budget must come from alternative water (desalination, effluent reuse) at alt_cost €/m3; with
    #     alt_cost None the budget is hard (it can be infeasible: fixed hydrogen demand always needs water).
    if ws.get('budget'):
        links, lc, gens, gc = freshwater_coefficients(n, ws)
        months = sns.get_level_values(1).month
        alt_cost = ws.get('alt_cost')
        w_obj = n.investment_period_weightings['objective']
        extra_cost = []
        for y in periods:
            if y not in ws['budget']:
                continue
            slack = {}
            if alt_cost is not None:
                for tag in ('year', 'summer'):
                    slack[tag] = m.add_variables(lower=0, name=f'Water-alternative-{tag}-{y}')
                    extra_cost.append(slack[tag] * float(alt_cost) * float(w_obj[y]))
            for tag, mask, share in [('year', np.ones(len(sns), bool), 1.0),
                                     ('summer', np.isin(months, SUMMER_MONTHS), ws.get('summer'))]:
                if share is None:
                    continue
                pos = np.where((sns.get_level_values(0) == y) & mask)[0]
                expr = _flow(n, links, sns, pos, lc) if links else 0
                if gens:
                    expr = expr + _gen_flow(n, gens, sns, pos, gc)
                hours = float(n.snapshot_weightings.generators.iloc[pos].sum())
                total = float(n.snapshot_weightings.generators.iloc[_period_pos(sns, y)].sum())
                limit = ws['budget'][y] * 1e6 * (1.0 if tag == 'year' else share * hours / total)
                if slack:      # alternative water used in summer also counts for the year
                    expr = expr - slack[tag] - (slack['summer'] if tag == 'year' else 0)
                m.add_constraints(expr <= limit, name=f'Water-budget-{tag}-{y}')
        if extra_cost:
            obj = m.objective.expression
            for e in extra_cost:
                obj = obj + e
            m.add_objective(obj, overwrite=True)

    # (b2) the verdringingsreeks in the drought season: a quota per restricted category ('verdringingsreeks'), or the
    #      same water as one pool for all categories ('cost_optimal': no priority order, water goes where it saves
    #      the most cost). Water above a quota or the pool is alternative water at alt_cost €/m3 (None: hard limit).
    quota, pool = drought_quotas(ws)
    if quota:
        links, lc, gens, gc = freshwater_coefficients(n, ws)
        lcat = np.array([water_category(_tech(l), ws) or 0 for l in links])
        gcat = np.array([water_category(_tech(g), ws) or 0 for g in gens])
        months = sns.get_level_values(1).month
        dry = np.isin(months, ws['drought_months'])
        alt_cost = ws.get('alt_cost')
        w_obj = n.investment_period_weightings['objective']
        extra = []
        for y in periods:
            pos = np.where((sns.get_level_values(0) == y) & dry)[0]
            if not len(pos):
                continue
            if ws['allocation'] == 'cost_optimal':
                groups = ([('pool', None, pool.get(int(y)))]
                          if any(drought_share(ws, c, y) < 1.0 for c in quota) else [])
            else:
                groups = [(f'cat{c}', c, quota[c].get(int(y))) for c in sorted(quota)
                          if drought_share(ws, c, y) < 1.0]
            for tag, c, limit in groups:
                if limit is None:
                    continue
                sel_l = [i for i, cc in enumerate(lcat) if cc and (c is None or cc == c)]
                sel_g = [i for i, cc in enumerate(gcat) if cc and (c is None or cc == c)]
                if not sel_l and not sel_g:
                    continue
                expr = 0
                if sel_l:
                    expr = _flow(n, [links[i] for i in sel_l], sns, pos, lc[sel_l])
                if sel_g:
                    expr = expr + _gen_flow(n, [gens[i] for i in sel_g], sns, pos, gc[sel_g])
                if alt_cost is not None:
                    slack = m.add_variables(lower=0, name=f'Water-drought-alternative-{tag}-{y}')
                    extra.append(slack * float(alt_cost) * float(w_obj[y]))
                    expr = expr - slack
                m.add_constraints(expr <= float(limit) * 1e6, name=f'Water-drought-{tag}-{y}')
        if extra:
            obj = m.objective.expression
            for e in extra:
                obj = obj + e
            m.add_objective(obj, overwrite=True)

    # (c) zero-emission share of freight: a diffusion limit (max) or a mandate (min)
    if FREIGHT_LOAD in n.loads.index:
        ze = [l for l in n.links.index if n.links.at[l, 'carrier'] in ZE_TRUCKS]
        p_set = n.get_switchable_as_dense('Load', 'p_set')[FREIGHT_LOAD]
        w = n.snapshot_weightings.generators
        for key, sign in (('ze_max_share', '<='), ('ze_min_share', '>=')):
            shares = scen.get(key) or {}
            if isinstance(shares, str):
                shares = ZE_MANDATES[shares]
            for y in periods:
                s = shares.get(y, shares.get(str(y)))
                if s is None or not ze:
                    continue
                pos = _period_pos(sns, y)
                demand = float((p_set.iloc[pos] * w.iloc[pos]).sum())
                expr = _flow(n, ze, sns, pos, n.links.loc[ze, 'efficiency'].values)
                con = expr <= float(s) * demand if sign == '<=' else expr >= float(s) * demand
                m.add_constraints(con, name=f'Freight-{key}-{y}')

    # (c2) realistic layer: BETs by duty cycle serve at most their segments' shares of freight (cumulative, so the
    #      cheaper duty types come first), and hydrogen trucks (FCET + H2-ICE) at most their availability share
    if FREIGHT_LOAD in n.loads.index and (scen.get('bet_tiers') or scen.get('h2_truck_max_share')
                                          or scen.get('freight_heavy_share')):
        p_set = n.get_switchable_as_dense('Load', 'p_set')[FREIGHT_LOAD]
        w = n.snapshot_weightings.generators
        caps = []
        tiers = scen.get('bet_tiers')
        if tiers:
            tiers = BET_TIERS[tiers] if isinstance(tiers, str) else tiers
            cum, group = 0.0, []
            for t, f in tiers.items():
                if f.get('share') is None:
                    continue
                cum += float(f['share'])
                group.append(t)
                caps.append((f"Freight-bet-tier-{t.replace(' ', '')}", list(group), {y: cum for y in periods}))
        h2 = scen.get('h2_truck_max_share')
        if h2:
            h2 = H2_TRUCK_SHARES[h2] if isinstance(h2, str) else h2
            caps.append(('Freight-h2-truck-max', list(HYDROGEN_TRUCKS), h2))
        hv = scen.get('freight_heavy_share')
        if hv:     # heavy-duty special transport: only ICE or H2-ICE trucks, so BETs + FCETs serve at most the rest
            caps.append(('Freight-heavy-segment', list(BETS) + list(FCETS), {y: 1.0 - float(hv) for y in periods}))
        for tag, techs, shares in caps:
            links = [l for l in n.links.index if n.links.at[l, 'carrier'] in techs]
            if not links:
                continue
            for y in periods:
                s = shares.get(y, shares.get(str(y)))
                if s is None:
                    continue
                pos = _period_pos(sns, y)
                demand = float((p_set.iloc[pos] * w.iloc[pos]).sum())
                m.add_constraints(_flow(n, links, sns, pos, n.links.loc[links, 'efficiency'].values)
                                  <= float(s) * demand, name=f'{tag}-{y}')

    # (d) net-zero policy: a cap on the annual CO2 to the atmosphere of the whole system (shadow price = the carbon
    #     price that the target needs on top of the ETS prices)
    cap = scen.get('co2_cap')
    if isinstance(cap, str):
        cap = CO2_CAPS[cap]
    if cap and 'bus2' in n.links:
        em = list(n.links.index[n.links.bus2 == 'CO2 atmosphere'])
        for y in periods:
            c = cap.get(y, cap.get(str(y)))
            if c is None or not em:
                continue
            pos = _period_pos(sns, y)
            m.add_constraints(_flow(n, em, sns, pos, n.links.loc[em, 'efficiency2'].values) <= float(c) * 1e6,
                              name=f'CO2-cap-{y}')

    # (e) hydrogen as a road fuel (RED III transport RFNBO target): the hydrogen trucks (FCET, H2-ICE) use the
    #     required renewable hydrogen, and renewable electrolysis (grid, seawater, pure green; not pink) supplies it on
    #     top of the industrial mandate
    rf = scen.get('rfnbo_transport')
    if isinstance(rf, str):
        rf = RFNBO_TRANSPORT[rf]
    if rf and FREIGHT_LOAD in n.loads.index:
        from .h2_presets import ELECTROLYSIS, ELECTROLYSIS_PINK, H2_LOAD
        mult = float(scen.get('rfnbo_multiplier', 2.0))
        road = [l for l in n.links.index if n.links.at[l, 'carrier'] in ROAD_TRANSPORT]
        fc = [l for l in n.links.index if n.links.at[l, 'carrier'] in HYDROGEN_TRUCKS]
        green = [e for e in ELECTROLYSIS if e not in ELECTROLYSIS_PINK]          # renewable electrolysis (RFNBO)
        ren = [l for l in n.links.index if n.links.at[l, 'carrier'] in green]
        gm = scen.get('green_mandate') or {}
        if isinstance(gm, str):
            gm = GREEN_MANDATES[gm]
        w = n.snapshot_weightings.generators
        p_h2 = n.get_switchable_as_dense('Load', 'p_set')[H2_LOAD] if H2_LOAD in n.loads.index else None
        for y in periods:
            s = rf.get(y, rf.get(str(y)))
            if not s or not fc or not road:
                continue
            pos = _period_pos(sns, y)
            need = _flow(n, road, sns, pos, np.ones(len(road))) * (float(s) / mult)
            m.add_constraints(_flow(n, fc, sns, pos, np.ones(len(fc))) - need >= 0, name=f'RFNBO-transport-use-{y}')
            g = gm.get(y, gm.get(str(y))) if gm else None
            ind = float(g) * float((p_h2.iloc[pos] * w.iloc[pos]).sum()) if (g and p_h2 is not None) else 0.0
            if ren:
                m.add_constraints(_flow(n, ren, sns, pos, n.links.loc[ren, 'efficiency'].values) - need >= ind,
                                  name=f'RFNBO-transport-supply-{y}')

    # (e2) renewable hydrogen at the pump (a policy test, h2_trucks_rfnbo): ALL hydrogen the trucks use is renewable
    #      (RFNBO), made by renewable electrolysis (grid, seawater, pure green; not pink) on top of the industrial
    #      mandate. Stands for an RFNBO obligation on hydrogen sold to road transport (the ERE system only credits
    #      renewable hydrogen); it implies the RED III transport supply constraint above.
    if scen.get('h2_trucks_rfnbo') and FREIGHT_LOAD in n.loads.index:
        from .h2_presets import ELECTROLYSIS, ELECTROLYSIS_PINK, H2_LOAD
        fc = [l for l in n.links.index if n.links.at[l, 'carrier'] in HYDROGEN_TRUCKS]
        green = [e for e in ELECTROLYSIS if e not in ELECTROLYSIS_PINK]          # renewable electrolysis (RFNBO)
        ren = [l for l in n.links.index if n.links.at[l, 'carrier'] in green]
        gm = scen.get('green_mandate') or {}
        if isinstance(gm, str):
            gm = GREEN_MANDATES[gm]
        w = n.snapshot_weightings.generators
        p_h2 = n.get_switchable_as_dense('Load', 'p_set')[H2_LOAD] if H2_LOAD in n.loads.index else None
        for y in periods:
            if not fc or not ren:
                continue
            pos = _period_pos(sns, y)
            g = gm.get(y, gm.get(str(y))) if gm else None
            ind = float(g) * float((p_h2.iloc[pos] * w.iloc[pos]).sum()) if (g and p_h2 is not None) else 0.0
            m.add_constraints(_flow(n, ren, sns, pos, n.links.loc[ren, 'efficiency'].values)
                              - _flow(n, fc, sns, pos, np.ones(len(fc))) >= ind, name=f'H2-trucks-rfnbo-{y}')
