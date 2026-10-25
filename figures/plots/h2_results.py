"""Result tables for the hydrogen study (the "Key outputs" of Table 2 in the report) and the policy story.

Francesco (14 Oct): what you can tell policymakers when you compare the scenarios is how
  * the cost of the system changes,
  * the amount of gas (imported) changes,
  * the electricity generation mix changes,
  * how much money is saved by building a smaller electrolyser (or lost by building one that is too big).
policy_table() puts these side by side.

All energy values are per year of the representative year of each period (TWh/yr, Mt/yr, ...), unless a name says
2020-2059 (each period then counts its ten years).
"""

import numpy as np
import pandas as pd

from energy_model.h2_presets import (ELECTROLYSIS, ELECTROLYSIS_GRID, ELECTROLYSIS_SEAWATER,
                       GREY, BLUE, BATTERY, H2_BUS, H2_LOAD, H2_STORAGE, MWH_PER_KG, WATER_L_PER_KG)

try:
    from energy_model.h2_presets import ELECTROLYSIS_GREEN, ELECTROLYSIS_PINK, DEDICATED_RES_CARRIERS, DEDICATED_NUCLEAR
except ImportError:
    ELECTROLYSIS_GREEN = []
    ELECTROLYSIS_PINK = []
    DEDICATED_RES_CARRIERS = []
    DEDICATED_NUCLEAR = []

# Hydrogen supply routes ("colours" of hydrogen), in stacking order (bottom to top)
ROUTES = {
    'Green (grid electrolysis)': ELECTROLYSIS_GRID + ELECTROLYSIS_SEAWATER,   # incl. the lever on desalinated water
    'Pure green (dedicated wind + solar)': ELECTROLYSIS_GREEN,   # option pure_green
    'Pink (nuclear electrolysis)': ELECTROLYSIS_PINK,          # option pink
    'Blue (SMR + CCS)': BLUE,
    'Grey (SMR)': GREY,
}
GREEN_ROUTES = ['Green (grid electrolysis)', 'Pure green (dedicated wind + solar)']
ELECTROLYSIS_ROUTES = GREEN_ROUTES + ['Pink (nuclear electrolysis)']     # all routes that use water for electrolysis

# Electricity generation by source: generator carriers and power-plant links (output at bus1), including the
# dedicated wind, solar and nuclear of the options (their electricity goes to the electrolysers only)
POWER_SOURCES = {
    'Solar': ('Generator', ['Solar', 'Solar - dedicated']),
    'Wind onshore': ('Generator', ['Wind onshore']),
    'Wind offshore': ('Generator', ['Wind offshore', 'Wind offshore - dedicated']),
    'Nuclear': ('Link', ['Nuclear plant', 'Nuclear plant - dedicated']),
    'Gas': ('Link', ['CCGT', 'CCGT - existing']),
    'Gas + CCS': ('Link', ['CCGT CCS']),
    'Biomass': ('Link', ['Biomass plant']),
    'Biomass + CCS': ('Link', ['Biomass plant CCS']),
}


def _w(n):
    return n.snapshot_weightings.generators


def ts(n, component, attr):
    """Time series of all components (columns that PyPSA did not store, e.g. unused assets, are 0)."""
    static = getattr(n, component)
    df = getattr(n, f'{component}_t')[attr]
    return df.reindex(columns=static.index, fill_value=0.0)


def _by_period(df):
    """Sum over snapshots per period."""
    return df.groupby(level=0).sum()


def _zero(n):
    return pd.Series(0.0, index=n.investment_periods)


def link_output(n, carriers, port=1):
    """Annual flow out of the links with these carriers at `port` (MWh/yr), per period."""
    links = n.links.index[n.links.carrier.isin(carriers)]
    if len(links) == 0:
        return _zero(n)
    p = -ts(n, 'links', f'p{port}')[links]
    return _by_period(p.mul(_w(n), axis=0)).sum(axis=1)


def link_input(n, carriers):
    links = n.links.index[n.links.carrier.isin(carriers)]
    if len(links) == 0:
        return _zero(n)
    return _by_period(ts(n, 'links', 'p0')[links].mul(_w(n), axis=0)).sum(axis=1)


def generator_output(n, carriers):
    g = n.generators.index[n.generators.carrier.isin(carriers)]
    if len(g) == 0:
        return _zero(n)
    return _by_period(ts(n, 'generators', 'p')[g].mul(_w(n), axis=0)).sum(axis=1)


def route_output(n, route):
    return link_output(n, ROUTES[route])


def h2_balance(n):
    """Hydrogen supply by route and the hydrogen demand, TWh/yr per period."""
    out = pd.DataFrame({route: route_output(n, route) for route in ROUTES})
    out['Hydrogen demand'] = _by_period(n.loads_t.p[H2_LOAD] * _w(n))
    return out / 1e6


def active_capacity(n, component, carriers, attr='p_nom_opt'):
    """Installed capacity of all active vintages per period."""
    c = getattr(n, component)
    names = c.index[c.carrier.isin(carriers)]
    res = {}
    for y in n.investment_periods:
        act = n.get_active_assets(_cname(component), y)
        res[y] = c.loc[[i for i in names if act.get(i, False)], attr].sum()
    return pd.Series(res)


def _cname(component):
    return {'links': 'Link', 'generators': 'Generator', 'storage_units': 'StorageUnit', 'stores': 'Store'}[component]


def electrolyser_output_capacity(n, techs=ELECTROLYSIS):
    """Active electrolyser capacity per period in MW of hydrogen OUTPUT (p_nom x efficiency)."""
    ely = n.links.index[n.links.carrier.isin(techs)]
    return pd.Series({y: sum(n.links.at[l, 'p_nom_opt'] * n.links.at[l, 'efficiency']
                             for l in ely if n.get_active_assets('Link', y).get(l, False))
                      for y in n.investment_periods}, dtype=float)


def co2_emissions(n):
    """CO2 to the atmosphere (Mt/yr) per period: total and from hydrogen production; and CO2 captured."""
    w = _w(n)
    to_atm = n.links.index[n.links.bus2 == 'CO2 atmosphere']
    to_sto = n.links.index[n.links.bus3 == 'CO2 storage'] if 'bus3' in n.links else []
    e_tot = _by_period(-ts(n, 'links', 'p2')[to_atm].mul(w, axis=0))
    h2_links = [l for l in to_atm if n.links.at[l, 'carrier'] in GREY + BLUE]
    c = _by_period(-ts(n, 'links', 'p3')[to_sto].mul(w, axis=0)) if len(to_sto) else None
    h2_ccs = [l for l in to_sto if n.links.at[l, 'carrier'] in BLUE]
    return pd.DataFrame({
        'CO2 total (Mt/yr)': e_tot.sum(axis=1) / 1e6,
        'CO2 from H2 production (Mt/yr)': e_tot[h2_links].sum(axis=1) / 1e6,
        'CO2 captured, all CCS (Mt/yr)': c.sum(axis=1) / 1e6 if c is not None else 0.0,
        'CO2 captured from H2 (Mt/yr)': c[h2_ccs].sum(axis=1) / 1e6 if c is not None else 0.0,
    })


CCS_SECTORS = {  # link carrier -> sector, for the CO2 that goes into the (capped) CO2 storage
    'SMR CCS': 'Hydrogen (blue)',
    'Industrial machinery - fossil CCS': 'Industry', 'Industrial HTP - fossil CCS': 'Industry',
    'CCGT CCS': 'Power (gas)', 'Biomass plant CCS': 'Power (biomass, BECCS)',
}


def co2_stored_by_sector(n):
    """CO2 put into the CO2 storage (Mt/yr) per period and sector. The storage is capped (co2_storage_cap: 10 / 22 /
    25 Mt/yr in 2030 / 2040 / 2050), so blue hydrogen competes with industry and power for it."""
    links = n.links.index[n.links.bus3 == 'CO2 storage'] if 'bus3' in n.links else []
    out = {}
    if len(links):
        p3 = _by_period(-ts(n, 'links', 'p3')[links].mul(_w(n), axis=0)) / 1e6
        for l in links:
            sec = CCS_SECTORS.get(n.links.at[l, 'carrier'], 'Other')
            out[sec] = out.get(sec, 0.0) + p3[l]
    df = pd.DataFrame(out, index=n.investment_periods).fillna(0.0)
    order = [c for c in list(dict.fromkeys(CCS_SECTORS.values())) + ['Other'] if c in df.columns]
    return df[order].mask(df[order].abs() < 1e-6, 0.0)


def gas_use(n):
    """Natural gas used (TWh/yr) per period: in total (all imported at the TTF price) and for hydrogen."""
    gas = n.links.index[n.links.bus0 == 'Gas supply']
    p0 = _by_period(ts(n, 'links', 'p0')[gas].mul(_w(n), axis=0))
    h2 = [l for l in gas if n.links.at[l, 'carrier'] in GREY + BLUE]
    return pd.DataFrame({'Gas use, total (TWh/yr)': p0.sum(axis=1) / 1e6,
                         'Gas for H2 (TWh/yr)': p0[h2].sum(axis=1) / 1e6})


def electricity_mix(n):
    """Electricity generation by source (TWh/yr) per period."""
    out = {}
    for src, (comp, carriers) in POWER_SOURCES.items():
        out[src] = generator_output(n, carriers) if comp == 'Generator' else link_output(n, carriers)
    return pd.DataFrame(out) / 1e6


def _dense(n, comp, attr):
    return n.get_switchable_as_dense(comp, attr)


def annual_system_cost(n):
    """Undiscounted annual system cost per period (bn €/yr): annualised investment + FOM + operating cost."""
    w = _w(n)
    mc_l = _dense(n, 'Link', 'marginal_cost')
    mc_g = _dense(n, 'Generator', 'marginal_cost')
    cost = {}
    for y in n.investment_periods:
        capex = 0.0
        for comp, attr in [('generators', 'p_nom_opt'), ('links', 'p_nom_opt'),
                           ('storage_units', 'p_nom_opt'), ('stores', 'e_nom_opt')]:
            c = getattr(n, comp)
            act = n.get_active_assets(_cname(comp), y)
            ext = c.index[c[attr.replace('_opt', '_extendable')] & act.reindex(c.index, fill_value=False)]
            capex += (c.loc[ext, 'capital_cost'] * c.loc[ext, attr]).sum()
        sl = n.snapshots.get_level_values(0) == y
        opex = (ts(n, 'generators', 'p').loc[sl] * mc_g.loc[sl]).mul(w[sl], axis=0).sum().sum()
        opex += (ts(n, 'links', 'p0').loc[sl] * mc_l.loc[sl]).mul(w[sl], axis=0).sum().sum()
        if len(n.storage_units):
            opex += (ts(n, 'storage_units', 'p_dispatch').loc[sl].mul(w[sl], axis=0)
                     * n.storage_units.marginal_cost).sum().sum()
        cost[y] = (capex + opex) / 1e9
    return pd.Series(cost, name='System cost (bn €/yr)')


def lcoh_by_route(n):
    """Average cost of hydrogen per route and period (€/kg): annualised CAPEX + FOM + operating cost
    + the value of the inputs at their bus prices (electricity, gas scarcity, CO2), per kg produced."""
    w = _w(n)
    mc = _dense(n, 'Link', 'marginal_cost')
    lam = n.buses_t.marginal_price
    P0, P1 = ts(n, 'links', 'p0'), ts(n, 'links', 'p1')
    out = {}
    for route, techs in ROUTES.items():
        links = n.links.index[n.links.carrier.isin(techs)]
        row = {}
        for y in n.investment_periods:
            sl = n.snapshots.get_level_values(0) == y
            act = n.get_active_assets('Link', y)
            la = [l for l in links if act.get(l, False)]
            prod = sum((-P1.loc[sl, l] * w[sl]).sum() for l in la)
            if prod < 1e3:
                row[y] = np.nan
                continue
            cost = sum(n.links.at[l, 'capital_cost'] * n.links.at[l, 'p_nom_opt'] for l in la)
            for l in la:
                p0 = P0.loc[sl, l] * w[sl]
                cost += (p0 * mc.loc[sl, l]).sum()
                cost += (p0 * lam.loc[sl, n.links.at[l, 'bus0']]).sum()
                for i in (2, 3):
                    b = n.links.at[l, f'bus{i}'] if f'bus{i}' in n.links else ''
                    if isinstance(b, str) and b and b in lam:
                        cost -= (p0 * n.links.at[l, f'efficiency{i}'] * lam.loc[sl, b]).sum()
            row[y] = cost / prod * MWH_PER_KG
        out[f'LCOH {route} (€/kg)'] = pd.Series(row)
    return pd.DataFrame(out)


def renewable_curtailment(n, carriers=('Solar', 'Wind onshore', 'Wind offshore')):
    """Curtailed wind and solar electricity (TWh/yr) per period."""
    g = n.generators
    ren = g.index[g.carrier.isin(list(carriers))]
    if len(ren) == 0:
        return _zero(n)
    avail = ts(n, 'generators', 'p_max_pu')[ren] * g.loc[ren, 'p_nom_opt']
    act = pd.DataFrame({y: n.get_active_assets('Generator', y).reindex(ren) for y in n.investment_periods})
    mask = act.T.reindex(n.snapshots.get_level_values(0)).set_axis(n.snapshots)
    avail = avail.where(mask.astype(bool), 0.0)
    curt = (avail - ts(n, 'generators', 'p')[ren]).clip(lower=0).mul(_w(n), axis=0)
    return _by_period(curt).sum(axis=1) / 1e6


def water_use(n):
    """Water use for hydrogen production (million m3/yr), with WATER_L_PER_KG from model.py (output only)."""
    b = h2_balance(n)
    kg = lambda twh: twh * 1e6 / MWH_PER_KG
    m3 = (kg(b[ELECTROLYSIS_ROUTES].sum(axis=1)) * WATER_L_PER_KG['electrolysis']
          + kg(b['Grey (SMR)']) * WATER_L_PER_KG['SMR']
          + kg(b['Blue (SMR + CCS)']) * WATER_L_PER_KG['SMR CCS']) / 1e3
    return (m3 / 1e6).rename('Water for H2 (Mm3/yr)')


def electrolyser_investment(n):
    """Overnight investment in NEW electrolysers built in each period (bn €, before any subsidy)."""
    scen = (n.meta or {}).get('scenario') or {}
    capex = scen.get('_capex_eur_per_mw_h2') or {}
    out = _zero(n)
    for name, l in n.links[n.links.carrier.isin(ELECTROLYSIS)].iterrows():
        y = int(l.build_year)
        per_mw = (capex.get(l.carrier) or {}).get(str(y))
        if per_mw is None or y not in out.index:
            continue
        out[y] += per_mw * l.p_nom_opt * l.efficiency / 1e9                # € per MW output x MW output
    return out


def summary(n, name=None):
    """One table per run with the key outputs, per period."""
    bal = h2_balance(n)
    prod = bal[list(ROUTES)].sum(axis=1)
    green = bal[GREEN_ROUTES].sum(axis=1)
    ely_twh = bal[ELECTROLYSIS_ROUTES].sum(axis=1)
    ely_out_cap = electrolyser_output_capacity(n)
    flh = (ely_twh * 1e6 / ely_out_cap.where(ely_out_cap > 1.0)).fillna(0.0)  # ignore < 1 MW
    meta = n.meta or {}
    scen = meta.get('scenario') or {}
    caps = scen.get('_electrolyser_caps_mw_h2') or {}
    if caps and not all(isinstance(v, dict) for v in caps.values()):      # runs saved before the options
        caps = {ELECTROLYSIS_GRID[0]: caps}
    cap_tot = dict(scen.get('_electrolyser_cap_total_mw_h2') or {})      # joint limit on all electrolysers
    if not cap_tot:                                                      # per technology (or one electrolyser)
        for c in caps.values():
            for y, v in c.items():
                cap_tot[y] = cap_tot.get(y, 0.0) + v
    sp = meta.get('electrolyser_cap_shadow_price_eur_per_kw_h2') or {}
    ely_sp = sp.get('total') or sp.get(ELECTROLYSIS_GRID[0]) or {}
    used = prod > 0.01                       # periods in which hydrogen is produced at all (> 10 GWh/yr)
    lam = n.buses_t.marginal_price
    per = n.investment_periods
    df = pd.concat([
        bal,
        pd.DataFrame({
            'Green H2 total (TWh/yr)': green,
            'Green share (%)': 100 * green / prod.where(used),
            'Electrolysis share (%)': 100 * ely_twh / prod.where(used),
            'Electrolyser capacity (GW_el)': active_capacity(n, 'links', ELECTROLYSIS) / 1e3,
            'of which pure green (GW_el)': active_capacity(n, 'links', ELECTROLYSIS_GREEN) / 1e3,
            'of which pink (GW_el)': active_capacity(n, 'links', ELECTROLYSIS_PINK) / 1e3,
            'of which on desalinated water (GW_el)': active_capacity(n, 'links', ELECTROLYSIS_SEAWATER) / 1e3,
            'Production subsidy (bn €/yr)': production_subsidy_cost(n)[0],
            'Electrolyser capacity (GW_H2)': ely_out_cap / 1e3,
            'Electrolyser limit, new build (GW_H2)': pd.Series(
                {y: (cap_tot[str(y)] / 1e3 if str(y) in cap_tot else np.nan) for y in per}),
            'Value of 1 kW more electrolyser, present value (€/kW_H2)': pd.Series(
                {y: ely_sp.get(str(y), np.nan) for y in per}),
            'Implied water value, levelised (€/m3)': water_shadow_price(n)['Implied water value, levelised (€/m3)'],
            'Electrolyser full-load hours (h/yr)': flh,
            'Electrolyser investment, new build (bn €)': electrolyser_investment(n),
            'Electricity for H2 (TWh/yr)': link_input(n, ELECTROLYSIS) / 1e6,
            'H2 storage (GWh)': active_capacity(n, 'stores', H2_STORAGE, 'e_nom_opt') / 1e3,
            'Dedicated wind + solar (GW)': active_capacity(n, 'generators', DEDICATED_RES_CARRIERS) / 1e3,
            'Dedicated nuclear (GW_el)': electrolyser_output_capacity(n, DEDICATED_NUCLEAR) / 1e3,   # p_nom x efficiency
            'Battery (GW)': active_capacity(n, 'storage_units', BATTERY) / 1e3,
            'Curtailment (TWh/yr)': renewable_curtailment(n),
            'Electricity price, mean (€/MWh)': lam['Electricity'].groupby(level=0).mean(),
            'H2 price, mean (€/kg)': lam[H2_BUS].groupby(level=0).mean() * MWH_PER_KG,
            'Shadow price of the CO2 storage cap (€/t)': pd.Series(
                {y: (meta.get('co2_storage_cap_shadow_price') or {}).get(str(y), np.nan) for y in per}),
        }),
        gas_use(n),
        electricity_mix(n).add_prefix('Electricity: ').add_suffix(' (TWh/yr)'),
        lcoh_by_route(n),
        co2_emissions(n),
        water_use(n),
        annual_system_cost(n),
    ], axis=1)
    df = df.mask(df.abs() < 1e-6, 0.0)       # solver noise (-0.00) shown as 0
    df.index.name = 'period'
    if name is not None:
        df = pd.concat({name: df}, names=['run'])
    return df


def water_shadow_price(n, ref_flh=5000.0):
    """Shadow price of water per period (restored with store_shadow_prices; group Table 1: 'value to the system of one
    extra unit of water').

    * Value of 1 kW more electrolyser where water limits it (€/kW_H2, present value over its life): the dual of the
      electrolyser water limit (joint limit 'total' + the electrolyser's own limit).
    * Implied water value (€/m3, levelised): that value divided by the water the extra kW would use over its life,
      discounted the same way: sum over its active periods of objective weighting x full-load hours x 0.66 m3/MWh_H2
      (full-load hours of the run's electrolysers; ref_flh when none are built, e.g. S3).
    * With the hourly output limit (electrolyser_limit_on='output'): the mean and summer water shadow price (€/m3).
    Compare with desalinated water (about €1.4/m3, i.e. €0.03/kg H2) and Dutch industrial water tariffs (€1-2/m3).
    """
    meta = n.meta or {}
    sp = meta.get('electrolyser_cap_shadow_price_eur_per_kw_h2') or {}
    out_sp = meta.get('electrolyser_water_output_shadow_price') or {}
    m3_per_mwh = WATER_L_PER_KG['electrolysis'] / MWH_PER_KG / 1e3               # 0.66 m3 of water per MWh of H2
    per = list(n.investment_periods)
    w = n.investment_period_weightings['objective']
    cap = electrolyser_output_capacity(n, ELECTROLYSIS_GRID)
    h2 = link_output(n, ELECTROLYSIS_GRID)                                         # MWh/yr
    flh = pd.Series({y: (h2[y] / cap[y] if cap[y] > 1.0 else ref_flh) for y in per})
    rows = {}
    for y in per:
        val = sum(float((d or {}).get(str(y), 0.0) or 0.0) for d in sp.values())
        link = f'{ELECTROLYSIS_GRID[0]}_{y}'
        if link in n.links.index:
            life = [p for p in per if n.get_active_assets('Link', p).get(link, False)]
        else:
            life = [p for p in per if p >= y]
        water_pv = sum(float(w[p]) * flh[p] * m3_per_mwh / 1e3 for p in life)      # m3 per kW_H2, discounted
        o = out_sp.get(str(y)) or {}
        rows[y] = {'Value of 1 kW more electrolyser, PV (€/kW_H2)': val if sp else np.nan,
                   'Electrolyser full-load hours used (h/yr)': flh[y],
                   'Implied water value, levelised (€/m3)': (val / water_pv if (sp and water_pv > 0) else np.nan),
                   'Hourly water limit: mean water value (€/m3)': o.get('eur_per_m3_mean', np.nan),
                   'Hourly water limit: summer water value (€/m3)': o.get('eur_per_m3_summer', np.nan)}
    return pd.DataFrame(rows).T


def compare(runs, period=None):
    """Summary of several runs side by side: runs = {name: network}."""
    df = pd.concat([summary(n, k) for k, n in runs.items()])
    if period is not None:
        df = df.xs(period, level='period')
    return df


def _horizon(n, series):
    """Sum of a per-year series over 2020-2059 (each period counts its number of years)."""
    return float((series * n.investment_period_weightings.years).sum())


def cumulative_co2(n):
    """CO2 to the atmosphere over the whole horizon (Mt; each period counts its number of years)."""
    return _horizon(n, co2_emissions(n)['CO2 total (Mt/yr)'])


def cost_per_tonne_avoided(n_run, n_ref):
    """Extra discounted system cost per tonne of CO2 avoided, relative to a reference run (€/tCO2)."""
    d_cost = n_run.objective - n_ref.objective
    d_em = (cumulative_co2(n_ref) - cumulative_co2(n_run)) * 1e6
    return d_cost / d_em if d_em != 0 else np.nan


def limit_cost(n_run, n_ref):
    """Average cost of the water limit relative to the reference run (S1 Base), in €/kg H2:
    extra discounted system cost (objective) divided by the discounted green hydrogen that is lost."""
    w = n_run.investment_period_weightings.objective
    g = lambda n: h2_balance(n)[GREEN_ROUTES].sum(axis=1)
    lost = ((g(n_ref) - g(n_run)) * 1e6 * w).sum()                    # discounted MWh
    if lost <= 1e3:
        return np.nan
    return (n_run.objective - n_ref.objective) / lost * MWH_PER_KG


def subsidy_cost(n):
    """Electrolyser investment subsidy (2a): overnight amount and present value of its annuities (bn €).

    The objective uses the subsidised CAPEX, so the subsidy is a transfer that is NOT in the system cost.
    Economic system cost = objective + subsidy_pv.
    """
    scen = (n.meta or {}).get('scenario') or {}
    per_mw = scen.get('_subsidy_eur_per_mw_h2') or {}
    rt = (n.meta or {}).get('rt', 0.07)
    w = n.investment_period_weightings.objective
    overnight, pv = 0.0, 0.0
    for name, l in n.links[n.links.carrier.isin(list(per_mw))].iterrows():
        y = str(int(l.build_year))
        sub = per_mw[l.carrier].get(y, 0.0) * l.efficiency * l.p_nom_opt        # € (per MW output x MW output)
        if sub <= 0:
            continue
        overnight += sub
        ann = sub * rt / (1 - (1 + rt) ** -l.lifetime)
        for per in n.investment_periods:
            if n.get_active_assets('Link', per).get(name, False):
                pv += ann * w.loc[per]
    return overnight / 1e9, pv / 1e9


def production_subsidy_cost(n):
    """Operating subsidy per kg of electrolytic hydrogen (green lever): (bn €/yr per period, present value in bn €).
    The objective contains it as a negative variable cost, so it is a transfer: economic cost = objective + pv."""
    scen = (n.meta or {}).get('scenario') or {}
    rate = float(scen.get('_prod_subsidy_eur_per_mwh_h2') or 0.0)          # € per MWh of hydrogen
    if rate == 0.0:
        return _zero(n), 0.0
    out = link_output(n, ELECTROLYSIS)                                      # MWh/yr per period
    annual = out * rate / 1e9
    pv = float((annual * n.investment_period_weightings.objective).sum())
    return annual, pv


def economic_cost(n):
    """System cost 2020-2059, discounted (bn €): the objective plus the subsidies, which are transfers."""
    return n.objective / 1e9 + subsidy_cost(n)[1] + production_subsidy_cost(n)[1]


def policy_table(runs, ref=None, period=2050):
    """The policy story side by side: one column per run (runs = {name: network}), differences against `ref`.

    System cost = the objective (discounted, 2020-2059, plus the present value of any subsidy, which the objective
    leaves out because it is a transfer). Gas, CO2 and investment are summed over 2020-2059.
    """
    rows = {}
    for k, n in runs.items():
        s = summary(n)
        mix = electricity_mix(n)
        rows[k] = {
            'System cost 2020-2059, discounted (bn €)': economic_cost(n),
            f'Green share {period} (%)': s.at[period, 'Green share (%)'],
            f'H2 {period} (TWh/yr): green / pure green / pink / blue / grey': ' / '.join(
                f"{s.at[period, r]:.1f}" for r in ROUTES),
            f'Electrolyser capacity {period} (GW_el)': s.at[period, 'Electrolyser capacity (GW_el)'],
            f'Electrolyser full-load hours {period} (h/yr)': s.at[period, 'Electrolyser full-load hours (h/yr)'],
            'Electrolyser investment 2020-2059 (bn €, overnight)': float(electrolyser_investment(n).sum()),
            'Gas use 2020-2059 (TWh)': _horizon(n, s['Gas use, total (TWh/yr)']),
            f'Gas use {period} (TWh/yr)': s.at[period, 'Gas use, total (TWh/yr)'],
            f'Gas for H2 {period} (TWh/yr)': s.at[period, 'Gas for H2 (TWh/yr)'],
            f'Electricity generation {period} (TWh/yr)': float(mix.loc[period].sum()),
            f'of which wind + solar {period} (TWh/yr)': float(mix.loc[period, ['Solar', 'Wind onshore',
                                                                                 'Wind offshore']].sum()),
            f'of which gas {period} (TWh/yr)': float(mix.loc[period, ['Gas', 'Gas + CCS']].sum()),
            'CO2 2020-2059 (Mt)': cumulative_co2(n),
            f'CO2 {period} (Mt/yr)': s.at[period, 'CO2 total (Mt/yr)'],
            f'Water for H2 {period} (Mm3/yr)': s.at[period, 'Water for H2 (Mm3/yr)'],
        }
    df = pd.DataFrame(rows)
    if ref is not None and ref in runs:
        for label in ['System cost 2020-2059, discounted (bn €)', 'Gas use 2020-2059 (TWh)', 'CO2 2020-2059 (Mt)',
                      'Electrolyser investment 2020-2059 (bn €, overnight)']:
            base = df.at[label, ref]
            df.loc[f'  difference with {ref}: {label.split(" (")[0].split(" 20")[0]}'] = (
                df.loc[label].astype(float) - float(base))
    return df

