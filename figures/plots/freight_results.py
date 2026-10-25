"""Freight results and the whole-system water account, from saved runs (results/runs/*.nc).

    from figures.plots import freight_results as fr
    fr.summary(n)                    # key indicators per period
    fr.water_account(n)              # water use of EVERY technology in the system, per period
    fr.compare({'F1': n1, 'F2': n2}, period=2050)
"""
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from energy_model.freight_presets import (ICE_TRUCKS, BETS, FCETS, H2ICE_TRUCKS, HYDROGEN_TRUCKS, ZE_TRUCKS, TRUCKS,
                                          WATER_INTENSITY, WATER_PER_TCO2_CAPTURED, WATER_SECTOR)
from figures.plots.h2_results import annual_system_cost

TRUCK_GROUPS = {'ICE truck': ICE_TRUCKS, 'BET': BETS, 'FCET': FCETS, 'H2-ICE truck': H2ICE_TRUCKS}
COLORS = {'ICE truck': '#7f7f7f', 'BET': '#1f77b4', 'FCET': '#2ca02c', 'H2-ICE truck': '#9467bd', 'Power': '#d62728',
          'Hydrogen': '#2ca02c',
          'Industry': '#8c564b', 'Buildings': '#e377c2', 'Transport': '#1f77b4', 'Freight trucks': '#ff7f0e',
          'Passenger cars': '#9467bd', 'Dedicated power for H2': '#6250d6'}
CO2_SECTOR = {**{t: s for s, ts_ in WATER_SECTOR.items() for t in ts_},
              **{t: 'Freight trucks' for t in ICE_TRUCKS}, 'ICE car': 'Passenger cars',
              'ICE car - existing': 'Passenger cars'}


def _tech(name):
    """Technology (carrier) of a component name: 'BET - urban_2030' -> 'BET - urban'."""
    return name.rsplit('_', 1)[0]


def _w(n):
    """Snapshot weightings (hours each snapshot stands for)."""
    return n.snapshot_weightings.generators


def _flows(n, attr, comp='links'):
    """Weighted annual flows per component and period (MWh/yr): columns = component names."""
    static = getattr(n, comp)
    df = getattr(n, f'{comp}_t')[attr].reindex(columns=static.index, fill_value=0.0)
    return df.mul(_w(n), axis=0).groupby(level=0).sum()


def _by_tech(df, techs=None):
    """Sum the columns (component names) per technology; with techs, reindex to exactly those technologies."""
    out = df.T.groupby(df.columns.map(_tech)).sum().T
    return out if techs is None else out.reindex(columns=techs, fill_value=0.0)


# ---------------------------------------------------------------------------------------------- freight
def freight_output(n):
    """Freight transport energy delivered per truck type (TWh/yr), per period."""
    out = _by_tech(-_flows(n, 'p1'), TRUCKS) / 1e6
    return pd.DataFrame({g: out[ts_].sum(axis=1) for g, ts_ in TRUCK_GROUPS.items()})


def bet_by_duty(n):
    """Freight transport energy of the BETs per duty cycle (TWh/yr): urban (depot), regional (the assignment's BET and
    the 2020 stock) and long haul; the realistic layer's split (bet_tiers), all regional otherwise."""
    out = _by_tech(-_flows(n, 'p1'), BETS) / 1e6
    return pd.DataFrame({'urban': out['BET - urban'], 'regional': out['BET'] + out['BET - existing'],
                         'long-haul': out['BET - long haul']})


def freight_capacity(n):
    """Active output capacity per truck type (GW of transport energy), per period."""
    cap = {}
    for y in n.investment_periods:
        act = n.get_active_assets('Link', y)
        l = n.links[act.reindex(n.links.index, fill_value=False)]
        c = (l.p_nom_opt * l.efficiency).groupby(l.index.map(_tech)).sum() / 1e3
        cap[y] = {g: c.reindex(ts_).fillna(0).sum() for g, ts_ in TRUCK_GROUPS.items()}
    return pd.DataFrame(cap).T


def co2_by_sector(n):
    """CO2 emitted to the atmosphere per sector (Mt/yr), per period (links with bus2 = CO2 atmosphere)."""
    l = n.links[n.links.get('bus2', pd.Series('', index=n.links.index)) == 'CO2 atmosphere']
    em = _flows(n, 'p0')[l.index] * l.efficiency2
    return (_by_tech(em).T.groupby(lambda t: CO2_SECTOR.get(t, 'Other')).sum().T / 1e6)


# ---------------------------------------------------------------------------------------------- water
def water_account(n, intensity=None):
    """Water use of every technology in the system (long table): period, technology, sector, output (TWh/yr),
    water and freshwater consumption (million m3/yr). Industrial CCS is counted per t of CO2 captured."""
    table = {**WATER_INTENSITY, **(intensity or {})}
    out1 = pd.concat([_by_tech(-_flows(n, 'p1')), _by_tech(_flows(n, 'p', 'generators'))], axis=1)
    if len(n.storage_units):
        out1 = pd.concat([out1, _by_tech(_flows(n, 'p_dispatch', 'storage_units'))], axis=1)
    if n.stores.e_nom_extendable.any():
        st = n.stores.index[n.stores.e_nom_extendable]
        out1 = pd.concat([out1, _by_tech(_flows(n, 'p', 'stores')[st].clip(lower=0))], axis=1)
    out1 = out1.T.groupby(level=0).sum().T
    if 'bus3' in n.links:
        l3 = n.links.index[n.links.carrier.isin(WATER_PER_TCO2_CAPTURED)]
        cap = _by_tech(_flows(n, 'p0')[l3] * n.links.loc[l3, 'efficiency3'])
    missing = sorted(set(out1.columns) - set(table) - set(WATER_PER_TCO2_CAPTURED))
    if missing:
        warnings.warn(f'No water intensity for {missing}: counted as 0. Add them to WATER_INTENSITY.')
    rows = []
    for y in out1.index:
        for t in out1.columns:
            m3, fresh = table.get(t, (0.0, 1.0))
            water = out1.at[y, t] * m3
            freshwater = water * fresh
            if t in WATER_PER_TCO2_CAPTURED and 'bus3' in n.links and t in cap.columns:
                m3c, freshc = WATER_PER_TCO2_CAPTURED[t]
                water += cap.at[y, t] * m3c
                freshwater += cap.at[y, t] * m3c * freshc
            sector = next((s for s, ts_ in WATER_SECTOR.items() if t in ts_), 'Other')
            rows.append(dict(period=y, technology=t, sector=sector, output_TWh=out1.at[y, t] / 1e6,
                             water_Mm3=water / 1e6, freshwater_Mm3=freshwater / 1e6))
    return pd.DataFrame(rows)


def water_summary(n):
    """Water and freshwater use per sector (Mm3/yr) and the water intensity of electricity and hydrogen."""
    a = water_account(n)
    s = a.pivot_table(index='period', columns='sector', values=['water_Mm3', 'freshwater_Mm3'], aggfunc='sum')
    elec = a[(a.sector == 'Power') & (a.technology != 'Battery')].groupby('period').output_TWh.sum()
    h2 = a[(a.sector == 'Hydrogen') & (a.technology != 'H2 storage')].groupby('period').output_TWh.sum()
    h2w = s[('water_Mm3', 'Hydrogen')] + (s[('water_Mm3', 'Dedicated power for H2')]
                                          if ('water_Mm3', 'Dedicated power for H2') in s.columns else 0.0)
    s[('intensity', 'electricity (m3/MWh)')] = s[('water_Mm3', 'Power')] / elec
    s[('intensity', 'hydrogen (m3/MWh)')] = h2w / h2.replace(0, np.nan)   # incl. its dedicated wind/solar/nuclear
    return s


def freight_water(n):
    """Water attributed to each truck type through its energy (Mm3/yr): BET via the average water intensity of
    electricity, FCET and H2-ICE truck via that of hydrogen; ICE trucks use no water in operation (refining is
    outside the system)."""
    s = water_summary(n)
    inp = _by_tech(_flows(n, 'p0'), TRUCKS)
    return pd.DataFrame({
        'ICE truck': 0.0 * inp[ICE_TRUCKS].sum(axis=1),
        'BET': inp[BETS].sum(axis=1) * s[('intensity', 'electricity (m3/MWh)')] / 1e6,
        'FCET': inp[FCETS].sum(axis=1) * s[('intensity', 'hydrogen (m3/MWh)')].fillna(0) / 1e6,
        'H2-ICE truck': inp[H2ICE_TRUCKS].sum(axis=1) * s[('intensity', 'hydrogen (m3/MWh)')].fillna(0) / 1e6})


# ---------------------------------------------------------------------------------------------- summaries
def summary(n):
    """Key indicators of one run per period: freight demand, shares per truck type and BET duty cycle, CO2 by sector,
    water, prices, capacities and the system cost (one row per period)."""
    out = freight_output(n)
    tot = out.sum(axis=1)
    co2 = co2_by_sector(n)
    ws = water_account(n).groupby('period')[['water_Mm3', 'freshwater_Mm3']].sum()
    inp = _by_tech(_flows(n, 'p0'), TRUCKS) / 1e6
    price = n.buses_t.marginal_price.get('Electricity')
    df = pd.DataFrame({
        'Freight demand (TWh/yr)': tot,
        'ICE share of freight (%)': 100 * out['ICE truck'] / tot,
        'BET share of freight (%)': 100 * out['BET'] / tot,
        'FCET share of freight (%)': 100 * out['FCET'] / tot,
        'H2-ICE share of freight (%)': 100 * out['H2-ICE truck'] / tot,
        **{f'BET {lab} share of freight (%)': 100 * v / tot for lab, v in bet_by_duty(n).items()},
        'ZE share of freight (%)': 100 * (out['BET'] + out['FCET'] + out['H2-ICE truck']) / tot,
        **{f'{g} capacity (GW)': v for g, v in freight_capacity(n).items()},
        'Electricity for trucks (TWh/yr)': inp[BETS].sum(axis=1),
        'Hydrogen for trucks (TWh/yr)': inp[HYDROGEN_TRUCKS].sum(axis=1),
        'Gasoline for trucks (TWh/yr)': inp[ICE_TRUCKS].sum(axis=1),
        'CO2 freight trucks (Mt/yr)': co2.get('Freight trucks', 0.0),
        'CO2 passenger cars (Mt/yr)': co2.get('Passenger cars', 0.0),
        'CO2 total (Mt/yr)': co2.sum(axis=1),
        'System cost (bn €/yr)': annual_system_cost(n),
        'Water use (Mm3/yr)': ws.water_Mm3,
        'Freshwater use (Mm3/yr)': ws.freshwater_Mm3,
    })
    if price is not None:
        df['Electricity price, mean (€/MWh)'] = price.groupby(level=0).mean()
    meta = n.meta if isinstance(n.meta, dict) else {}
    dr = drought_table(n)
    if dr is not None:
        df['Alternative water in drought season (Mm3)'] = dr['Alternative water (Mm3)'].reindex(df.index).fillna(0.0)
    budget = (meta.get('water') or {}).get('budget') or {}
    if budget:   # freshwater above the annual budget = alternative water (desalination, reuse); not the summer excess
        df['Alternative water above budget (Mm3/yr)'] = [
            max(0.0, float(ws.freshwater_Mm3.get(y, 0.0)) - float(budget.get(str(y), np.inf))) for y in df.index]
    return df


def compare(runs, period=None):
    """summary() of several runs in one table (index run, period), or one period of it."""
    df = pd.concat({k: summary(n) for k, n in runs.items()}, names=['run', 'period'])
    return df.xs(period, level='period') if period is not None else df


RT = 0.07          # technical discount rate of the model (run_freight.RT): annuity of the subsidised CAPEX


def _annuity(life):
    return RT / (1.0 - (1.0 + RT) ** -float(life))


def policy_transfers(n):
    """Policy transfers per period (bn €/yr). The toll the trucks pay is in the system cost (added to their VOM); the
    purchase and investment subsidies are left out of it (a lower CAPEX): AanZET (BETs), SWiM (FCETs and H2-ICE
    trucks) and OWE (electrolysers), annualised like the CAPEX (subsidy per MW x annuity x efficiency, for the assets
    built in a subsidised year and active in the period). 'System cost without transfers' = system cost - toll +
    subsidies: the resource cost to the economy. The CO2 price stays in, as in the course model."""
    from energy_model.freight_presets import (TRUCK_TOLLS, TOLL_KWH_OUT_PER_KM, BET_SUBSIDIES, H2TRUCK_SUBSIDIES,
                                              BET_TIERS)
    from energy_model.h2_presets import ELECTROLYSIS
    meta = n.meta if isinstance(n.meta, dict) else {}
    scen = meta.get('scenario') or {}
    get = lambda d, y: float((d or {}).get(y, (d or {}).get(str(y), 0.0)) or 0.0)

    def preset(v, table):
        if isinstance(v, str):
            return table[v]
        return v if isinstance(v, dict) else {}                  # None or a scalar 0: no subsidy

    toll = scen.get('truck_toll')
    toll = TRUCK_TOLLS[toll] if isinstance(toll, str) else toll
    # subsidy in € per MW of CAPEX unit, per technology and build year (stored by the scenario code; fallback: share x
    # the subsidised CAPEX share of capital_cost, an upper bound because capital_cost also holds the FOM)
    bet_sub = scen.get('_bet_subsidy_eur_per_mw') or {}
    tiers = BET_TIERS.get(scen.get('bet_tiers'), {}) if isinstance(scen.get('bet_tiers'), str) else {}
    tier_f = {t: f['capex'] for t, f in tiers.items()}
    per_mw = {'AanZET subsidy (bn €/yr)': (BETS, lambda t, b: get(bet_sub, b) * tier_f.get(t, 1.0)
                                           if t != 'BET - existing' else 0.0, preset(scen.get('bet_capex_subsidy'),
                                                                                       BET_SUBSIDIES)),
              'SWiM subsidy (bn €/yr)': (HYDROGEN_TRUCKS, lambda t, b: get((scen.get('_h2truck_subsidy_eur_per_mw')
                                                                             or {}).get(t), b),
                                         preset(scen.get('h2truck_capex_subsidy'), H2TRUCK_SUBSIDIES)),
              'OWE subsidy (bn €/yr)': (ELECTROLYSIS,
                                        lambda t, b: get((scen.get('_subsidy_eur_per_mw_h2') or {}).get(t), b),
                                        preset(scen.get('electrolyser_subsidy'), {}))}
    out = _by_tech(-_flows(n, 'p1'), TRUCKS)                     # MWh/yr of freight per truck type
    rows = {}
    for y in n.investment_periods:
        r = {}
        for lab, key, techs in (('ICE trucks', 'ICE', ICE_TRUCKS), ('zero-emission trucks', 'ZE', ZE_TRUCKS)):
            rate = get(toll[key], y) if toll else 0.0                  # €/km
            mwh = float(out.loc[y, [t for t in techs if t in out.columns]].sum())
            r[f'Toll paid, {lab} (bn €/yr)'] = mwh * rate / TOLL_KWH_OUT_PER_KM * 1e3 / 1e9
        act = n.get_active_assets('Link', y)
        for lab, (carriers, eur_per_mw, share) in per_mw.items():
            total = 0.0
            for l in n.links.index[n.links.carrier.isin(carriers) & act.reindex(n.links.index, fill_value=False)]:
                t, b = n.links.at[l, 'carrier'], int(n.links.at[l, 'build_year'])
                s_ = get(share, b)
                if s_ <= 0:
                    continue
                v = eur_per_mw(t, b)
                if v > 0:                                              # exact: € per MW x annuity x efficiency
                    total += n.links.at[l, 'p_nom_opt'] * n.links.at[l, 'efficiency'] * _annuity(
                        n.links.at[l, 'lifetime']) * v
                else:                                                  # fallback (runs without the stored values)
                    total += n.links.at[l, 'capital_cost'] * n.links.at[l, 'p_nom_opt'] * s_ / (1 - s_)
            r[lab] = total / 1e9
        rows[y] = r
    df = pd.DataFrame(rows).T
    df['System cost (bn €/yr)'] = annual_system_cost(n)
    df['System cost without transfers (bn €/yr)'] = (df['System cost (bn €/yr)']
                                                     - df.filter(like='Toll').sum(axis=1)
                                                     + df.filter(like='subsidy').sum(axis=1))
    return df


def switching_cost(n, n_ice):
    """Cost of switching to zero-emission freight: the run minus its ICE-only counterfactual.
    Per period: extra system cost (bn €/yr) and CO2 avoided (Mt/yr); over the horizon: discounted cost per t
    avoided."""
    dc = annual_system_cost(n) - annual_system_cost(n_ice)
    dco2 = co2_by_sector(n_ice).sum(axis=1) - co2_by_sector(n).sum(axis=1)
    wobj = n.investment_period_weightings['objective']
    wyrs = n.investment_period_weightings['years']
    return pd.DataFrame({'Extra system cost (bn €/yr)': dc, 'CO2 avoided (Mt/yr)': dco2,
                         'Abatement cost, horizon (€/t)': (dc * wobj).sum() * 1e9 / ((dco2 * wyrs).sum() * 1e6)})


# ---------------------------------------------------------------------------------------------- figures
def plot_freight_mix(runs, ax=None):
    """Stacked bars: freight transport energy by truck type, per run and period (TWh/yr)."""
    ax = ax or plt.subplots(figsize=(6.5, 3))[1]
    x, ticks, labels = 0.0, [], []
    for name, n in runs.items():
        out = freight_output(n)
        for y in out.index:
            bottom = 0
            for g in TRUCK_GROUPS:
                ax.bar(x, out.at[y, g], bottom=bottom, color=COLORS[g], width=0.8,
                       label=g if not ticks else None)
                bottom += out.at[y, g]
            ticks.append(x)
            labels.append(f'{y}\n{name}' if y == out.index[0] else str(y))
            x += 1
        x += 0.6
    ax.set_xticks(ticks, labels, fontsize=8)
    ax.set_ylabel('Freight transport energy (TWh/yr)')
    ax.legend(frameon=False, fontsize=8, ncol=3)
    return ax


def plot_co2(runs, ax=None):
    """Lines: CO2 of freight trucks, passenger cars and the rest of the system per run (Mt/yr)."""
    ax = ax or plt.subplots(figsize=(6.5, 3))[1]
    for name, n in runs.items():
        c = co2_by_sector(n)
        f = c.get('Freight trucks', 0.0)
        ax.plot(c.index, f, marker='o', label=f'{name}: freight trucks')
        ax.plot(c.index, c.sum(axis=1), ls='--', alpha=0.6, label=f'{name}: whole system')
    ax.set_ylabel('CO2 (Mt/yr)')
    ax.legend(frameon=False, fontsize=8, ncol=2)
    return ax


def plot_water(runs, period=2050, ax=None):
    """Stacked bars: water consumption per sector for each run in one period, freshwater hatched (Mm3/yr)."""
    ax = ax or plt.subplots(figsize=(6.5, 3))[1]
    for i, (name, n) in enumerate(runs.items()):
        a = water_account(n)
        a = a[a.period == period].groupby('sector')[['water_Mm3', 'freshwater_Mm3']].sum()
        bottom = 0
        for s in ['Power', 'Dedicated power for H2', 'Hydrogen', 'Industry', 'Buildings', 'Transport']:
            if s in a.index and a.at[s, 'water_Mm3'] > 0:
                ax.bar(i, a.at[s, 'water_Mm3'], bottom=bottom, color=COLORS[s], label=s if i == 0 else None)
                ax.bar(i, a.at[s, 'freshwater_Mm3'], bottom=bottom, fill=False, hatch='///', edgecolor='white')
                bottom += a.at[s, 'water_Mm3']
    ax.set_xticks(range(len(runs)), list(runs), fontsize=8)
    ax.set_ylabel(f'Water consumption {period} (million m³/yr)')
    ax.legend(frameon=False, fontsize=8, title='hatched = freshwater', title_fontsize=8)
    return ax


def drought_table(n):
    """The verdringingsreeks in the drought season of a run: freshwater use per category (Mm3, June-September),
    the quota per restricted category (or the cost-optimal pool), and the alternative water bought above it.
    None when the run has no drought."""
    meta = n.meta if isinstance(n.meta, dict) else {}
    dr = (meta.get('water') or {}).get('drought')
    if not dr:
        return None
    from energy_model import freight_water as fw
    scen = dict(meta.get('scenario') or {})
    shares = dr.get('shares_by_year') or dr['shares']            # a path per period (driver) or one drought
    ws = fw.water_settings({**scen, 'water_drought': {int(k): v for k, v in shares.items()},
                            'water_drought_months': tuple(dr['months']),
                            'electrolysis_category': dr['electrolysis_category'],
                            'water_allocation': dr['allocation']})
    use = fw.season_use(n, ws, tuple(dr['months']))
    rows = {}
    for y in use.index:
        if str(y) not in dr['pool_mm3']:
            continue
        r = {f'Use cat {c} (Mm3)': float(use.at[y, c]) if c in use.columns else 0.0 for c in (2, 3, 4)}
        alt = 0.0
        if dr['allocation'] == 'cost_optimal':
            if any(fw.drought_share(ws, c, y) < 1.0 for c in (2, 3, 4)):     # no pool in a period without drought
                lim = float(dr['pool_mm3'][str(y)])
                r['Pool (Mm3)'] = lim
                alt = max(0.0, sum(r[f'Use cat {c} (Mm3)'] for c in (2, 3, 4)) - lim)
        else:
            for c, d in dr['quota_mm3'].items():
                share = float(fw.drought_share(ws, int(c), y))     # this period's share (driver: a path)
                if share < 1.0:
                    lim = float(d.get(str(y), 0.0))
                    r[f'Quota cat {c} (Mm3)'] = lim
                    alt += max(0.0, r.get(f'Use cat {c} (Mm3)', 0.0) - lim)
        r['Alternative water (Mm3)'] = alt
        rows[y] = r
    return pd.DataFrame(rows).T


def shadow_prices(n, ref_flh=5000.0):
    """Shadow prices stored on n.meta by store_shadow_prices (per year of the period, undiscounted).

    Water: the value of one more m3 of freshwater to the energy system.
    * Freshwater budget (€/m3): the dual of the annual and the summer budget. When alternative water is bought the
      budget dual equals its price (water_alt_cost, 1.4 €/m3); summer water is worth year + summer.
    * Implied freshwater value for electrolysis (€/m3): the shadow price of the electrolyser water cap per kW_el and
      year, divided by the water that 1 kW_el of electrolysis uses per year (full-load hours of the run's freshwater
      electrolysers, or ref_flh when none run, x efficiency x 0.66 m3/MWh_H2).
    Other: CO2-storage and net-zero caps (€/t), mandates, and build limits (€/kW/yr: offshore wind, nuclear, ...).
    """
    meta = n.meta if isinstance(n.meta, dict) else {}
    per = list(n.investment_periods)
    get = lambda d, y: (d or {}).get(str(y), np.nan)
    wc = dict((meta.get('water_cap_shadow_price') or {}).get('Electrolysers') or {})
    caps = (((meta.get('water') or {}).get('caps') or {}).get('Electrolysers') or {})
    for y, c in caps.items():                 # a cap of 0 (high scarcity): degenerate dual, no marginal value
        if c is not None and float(c) <= 1e-6:
            wc[str(y)] = np.nan
    wb = meta.get('water_budget_shadow_price') or {}
    ze = meta.get('ze_share_shadow_price') or {}
    rf = meta.get('rfnbo_transport_shadow_price') or {}
    bc = meta.get('build_cap_shadow_price_eur_per_kw_yr') or {}
    ely = n.links[n.links.carrier.isin(['Electrolyser', 'Electrolyser - pure green', 'Electrolyser - pink'])]
    out = _flows(n, 'p1', 'links').reindex(columns=ely.index, fill_value=0.0)
    rows = {}
    for y in per:
        act = n.get_active_assets('Link', y).reindex(ely.index, fill_value=False)
        cap = float(ely.loc[act, 'p_nom_opt'].sum())
        h2 = float(-out.loc[y, act[act].index].sum()) if act.any() else 0.0
        mwh_h2_per_mw_el = h2 / cap if cap > 1 else ref_flh * 0.65
        m3_per_kw_yr = mwh_h2_per_mw_el * 0.66 / 1e3
        v = get(wc, y)
        yr, su = get(wb.get('year'), y), get(wb.get('summer'), y)
        dsp = meta.get('water_drought_shadow_price') or {}
        rows[y] = {'Drought quota, category 2 (€/m3)': get(dsp.get('cat2'), y),
                   'Drought quota, category 3 (€/m3)': get(dsp.get('cat3'), y),
                   'Drought quota, category 4 (€/m3)': get(dsp.get('cat4'), y),
                   'Drought pool, cost-optimal (€/m3)': get(dsp.get('pool'), y),
                   'Freshwater budget, year (€/m3)': yr,
                   'Freshwater budget, summer (€/m3)': su,
                   'Freshwater value in summer (€/m3)': (np.nansum([yr, su]) if not (np.isnan(yr) and np.isnan(su))
                                                         else np.nan),
                   'Water cap on electrolysers (€/kW_el/yr)': v,
                   'Implied freshwater value for electrolysis (€/m3)':
                       v / m3_per_kw_yr if m3_per_kw_yr > 0 else np.nan,
                   'CO2-storage cap (€/t)': get(meta.get('co2_storage_cap_shadow_price'), y),
                   'CO2 cap, net zero (€/t)': get(meta.get('co2_cap_shadow_price'), y),
                   'ZE freight mandate (€/MWh)': get(ze.get('min'), y),
                   'ZE diffusion limit / market ramp-up (€/MWh)': get(ze.get('max'), y),
                   'Green H2 mandate (€/kg)': get(meta.get('green_mandate_shadow_price_eur_per_kg'), y),
                   'RFNBO transport, use (€/MWh H2)': get(rf.get('use'), y),
                   'RFNBO transport, supply (€/MWh H2)': get(rf.get('supply'), y),
                   'Renewable hydrogen for trucks (€/kg)':
                       get(meta.get('h2_trucks_rfnbo_shadow_price_eur_per_kg'), y)}
        for k, d in bc.items():
            rows[y][f"Build limit {k.replace('_', ' ')} (€/kW/yr)"] = get(d, y)
        seg_names = {'bet-tier-BET-urban': 'BET urban segment cap', 'bet-tier-BET': 'BET urban + regional cap',
                     'h2-truck-max': 'Hydrogen-truck availability', 'heavy-segment': 'Heavy special segment'}
        for k, d in (meta.get('freight_segment_shadow_price') or {}).items():   # realistic layer
            rows[y][f"{seg_names.get(k, k)} (€/MWh)"] = get(d, y)
    return pd.DataFrame(rows).T


def storage(n):
    """Grid batteries and hydrogen storage per period: power (GW), energy (GWh), hours, discharge (TWh/yr),
    equivalent full cycles per year, and salt-cavern hydrogen storage (TWh)."""
    from energy_model.h2_presets import BATTERY, H2_STORAGE
    su = n.storage_units[n.storage_units.carrier.isin(BATTERY)]
    st = n.stores[n.stores.carrier.isin(H2_STORAGE)]
    w = n.snapshot_weightings.generators
    disp = (n.storage_units_t.p_dispatch.reindex(columns=su.index, fill_value=0.0).mul(w, axis=0)
            .groupby(level=0).sum() if len(su) else None)
    rows = {}
    for y in n.investment_periods:
        act = n.get_active_assets('StorageUnit', y).reindex(su.index, fill_value=False)
        p = float(su.loc[act, 'p_nom_opt'].sum())
        e = float((su.loc[act, 'p_nom_opt'] * su.loc[act, 'max_hours']).sum())
        d = float(disp.loc[y, act[act].index].sum()) if (disp is not None and act.any()) else 0.0
        acts = n.get_active_assets('Store', y).reindex(st.index, fill_value=False)
        rows[y] = {'Battery power (GW)': p / 1e3, 'Battery energy (GWh)': e / 1e3,
                   'Battery duration (h)': e / p if p > 1 else np.nan,
                   'Battery discharge (TWh/yr)': d / 1e6,
                   'Battery full cycles (per yr)': d / e if e > 1 else np.nan,
                   'H2 storage (TWh)': float(st.loc[acts, 'e_nom_opt'].sum()) / 1e6}
    return pd.DataFrame(rows).T
