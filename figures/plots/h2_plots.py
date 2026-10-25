"""Plots for the hydrogen study: the 'Plot' column of Table 2 in the report, in colour.

Colour rules (validated with the dataviz palette checker for adjacent pairs, stacking order bottom to top):
  hydrogen routes   green (grid electrolysis) #1baf7a, pure green (dedicated wind + solar) #008300,
                    pink (nuclear electrolysis) #e87ba4, blue (SMR + CCS) #2a78d6, grey (SMR) #75746f.
                    Grey hydrogen is drawn in grey on purpose (the colour IS its name); the checker flags any grey as
                    'reads gray', so grey bars also get a hatch, which keeps them apart from 'missing' or 'other'.
                    Aqua and pink are below 3:1 against white: charts with them carry a legend and value labels.
  scenarios         S1 Base #6250d6 (violet), S2 Medium #eda100 (yellow), S3 Scarce #e34948 (red): not blue or green,
                    so a scenario is never mistaken for a hydrogen colour; checked for all pairs. Yellow is below 3:1
                    on white, so scenario charts carry value labels. Other runs: the fixed categorical order below.
Text stays in ink colours; every chart with 2+ series has a legend; grids are light and horizontal only.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from .h2_results import (h2_balance, summary, ROUTES, GREEN_ROUTES, co2_emissions, cumulative_co2, ts, subsidy_cost,
                         electricity_mix, gas_use, electrolyser_investment)
from energy_model.h2_presets import ELECTROLYSIS, BATTERY, H2_BUS

INK, INK2, MUTED, GRID, SURFACE = '#0b0b0b', '#52514e', '#8a8984', '#e6e5e0', '#fcfcfb'
ROUTE_COLORS = {
    'Green (grid electrolysis)': '#1baf7a',
    'Pure green (dedicated wind + solar)': '#008300',
    'Pink (nuclear electrolysis)': '#e87ba4',
    'Blue (SMR + CCS)': '#2a78d6',
    'Grey (SMR)': '#75746f',
}
ROUTE_HATCH = {'Grey (SMR)': '////'}
SCEN_COLORS = {'S1': '#6250d6', 'S2': '#eda100', 'S3': '#e34948'}
CATEGORICAL = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#4a3aa7', '#e34948']
CARRIER_COLORS = {'electricity': '#eda100', 'gas': '#b07a3a', 'hydrogen': '#52514e',
                  'loss': '#e2e1dc', 'battery': '#4a3aa7', 'electrolyser': '#1baf7a'}

plt.rcParams.update({
    'font.family': 'sans-serif', 'font.sans-serif': ['Arial', 'Liberation Sans', 'Helvetica', 'DejaVu Sans'],
    'font.size': 9, 'axes.edgecolor': MUTED, 'axes.labelcolor': INK2, 'xtick.color': INK2, 'ytick.color': INK2,
    'axes.titlesize': 10, 'axes.titleweight': 'bold', 'axes.titlecolor': INK, 'figure.facecolor': 'white',
    'axes.facecolor': 'white', 'legend.frameon': False, 'legend.fontsize': 8,
})


def run_color(name, i=0):
    """Scenario colour for names containing S1/S2/S3, else the categorical slot i (fixed order)."""
    for tag, c in SCEN_COLORS.items():
        if name == tag or name.startswith(tag + '_') or f'_{tag}' in name or name.startswith(tag + ' '):
            return c
    return CATEGORICAL[i % len(CATEGORICAL)]


SHORT_TAGS = {'Base': 'S1', 'Medium': 'S2', 'Scarce': 'S3'}


def _tag(name):
    for short, tag in SHORT_TAGS.items():
        if name == short or name.startswith(short + ' ') or name.endswith(' ' + short):
            return tag
    for tag in SCEN_COLORS:
        if name == tag or name.startswith(tag + '_') or name.startswith(tag + ' ') or f'_{tag}' in name:
            return tag
    return None


def colors_for(names):
    """Scenario colours if every run is a different scenario (S1/S2/S3), else the categorical order."""
    tags = [_tag(k) for k in names]
    if None not in tags and len(set(tags)) == len(tags):
        return [SCEN_COLORS[t] for t in tags]
    return [CATEGORICAL[i % len(CATEGORICAL)] for i in range(len(names))]


def _style(ax, ygrid=True):
    ax.spines[['top', 'right']].set_visible(False)
    if ygrid:
        ax.yaxis.grid(True, color=GRID, lw=0.8)
        ax.set_axisbelow(True)


def _new_ax(ax, size=(6, 3.4)):
    if ax is None:
        fig, ax = plt.subplots(figsize=size)
    return ax


# --------------------------------------------------------------------------
# (1) Hydrogen by route
# --------------------------------------------------------------------------

def plot_h2_routes(runs, ax=None, title='Hydrogen supply by route', periods=None):
    """Stacked bars: hydrogen supply by route, per run and period (TWh/yr)."""
    ax = _new_ax(ax, (1.6 + 1.4 * len(runs), 3.6))
    x0, ticks, labels, used = 0, [], [], set()
    for name, n in runs.items():
        bal = h2_balance(n)
        if periods is not None:
            bal = bal.loc[periods]
        for i, y in enumerate(bal.index):
            bottom = 0
            for route, col in ROUTE_COLORS.items():
                v = max(bal.at[y, route], 0)
                if v <= 1e-6:
                    continue
                ax.bar(x0 + i, v, bottom=bottom, width=0.78, color=col, edgecolor='white', linewidth=1.0,
                       hatch=ROUTE_HATCH.get(route), label=route if route not in used else None)
                used.add(route)
                bottom += v
            ticks.append(x0 + i)
            labels.append(str(y))
        if bal[list(ROUTE_COLORS)].clip(lower=0).to_numpy().sum() <= 1e-6:    # a run without any hydrogen
            ax.text(x0 + (len(bal) - 1) / 2, 0.04, 'no hydrogen', transform=ax.get_xaxis_transform(),
                    ha='center', va='bottom', fontsize=8, style='italic', color=MUTED)
        ax.text(x0 + (len(bal) - 1) / 2, -0.2, name, transform=ax.get_xaxis_transform(),
                ha='center', va='top', fontweight='bold', color=INK)
        x0 += len(bal) + 1
    ax.set_xticks(ticks, labels, rotation=90, fontsize=7)
    ax.set_ylabel('TWh H$_2$ per year')
    ax.set_title(title, loc='left')
    # legend in stacking order (top of the stack first)
    from matplotlib.patches import Patch
    handles = [Patch(facecolor=ROUTE_COLORS[r], hatch=ROUTE_HATCH.get(r), edgecolor='white', label=r)
               for r in reversed(list(ROUTE_COLORS)) if r in used]
    ax.legend(handles=handles, loc='upper left', bbox_to_anchor=(1, 1))
    _style(ax)
    return ax


def plot_indicator(runs, column, ax=None, kind='bar', title=None, periods=None):
    """One output from summary() per run and period, e.g. 'Green share (%)'."""
    df = pd.concat({k: summary(n)[column] for k, n in runs.items()}, axis=1)
    if periods is not None:
        df = df.loc[periods]
    ax = _new_ax(ax, (5.5, 3.2))
    cols = colors_for(list(df.columns))
    if kind == 'bar':
        df.plot(kind='bar', ax=ax, color=cols, edgecolor='white', linewidth=1.0, rot=0, width=0.8)
        # mark values that are not defined (e.g. the full-load hours of an electrolyser that is not built)
        nc = len(df.columns)
        for j, c in enumerate(df.columns):
            for i, v in enumerate(df[c].values):
                if pd.isna(v):
                    ax.text(i - 0.4 + 0.8 * (j + 0.5) / nc, 0, 'n/a', rotation=90, ha='center', va='bottom',
                            fontsize=6.5, color=MUTED, transform=ax.get_xaxis_transform())
    else:
        for i, c in enumerate(df.columns):
            ax.plot(df.index, df[c], '-', color=cols[i], lw=2, marker='o', ms=5, label=c)
        ax.set_xticks(df.index)
    ax.set_ylabel(column)
    ax.set_xlabel('')
    ax.set_title(title or column, loc='left')
    ax.legend(fontsize=7)
    _style(ax)
    return ax


# --------------------------------------------------------------------------
# (2a) system cost and cost per tonne of CO2 avoided
# --------------------------------------------------------------------------

def plot_cost_and_co2(runs, ref, axes=None, title_suffix=''):
    """(2a) Economic system cost relative to a reference run (objective + any subsidy, which is a transfer),
    cumulative CO2 2020-2059, and the cost per tonne of CO2 avoided written on the bars.
    If a run has an electrolyser subsidy, a third panel shows the subsidy and the subsidy per tonne avoided."""
    names = list(runs)
    subs = {k: subsidy_cost(runs[k]) for k in names}
    has_sub = any(v[0] > 0 for v in subs.values())
    if axes is None:
        fig, axes = plt.subplots(1, 3 if has_sub else 2, figsize=(15 if has_sub else 10, 3.6))
    econ = {k: runs[k].objective / 1e9 + subs[k][1] for k in names}
    noise = lambda v: 0.0 if abs(v) < 1e-3 else v         # solver noise (e.g. 1e-13 bn) is shown as zero
    dcost = [noise(econ[k] - econ[ref]) for k in names]
    cum = [cumulative_co2(runs[k]) for k in names]
    cols = colors_for(names)
    iref = names.index(ref)
    axes[0].bar(names, dcost, color=cols, edgecolor='white')
    axes[0].axhline(0, color=MUTED, lw=0.8)
    axes[0].set_ylabel(f'Extra system cost vs {ref} (bn €, discounted)')
    axes[0].set_title('System cost (incl. subsidy)' + title_suffix, loc='left')
    dco2 = [noise(c - cum[names.index(ref)]) for c in cum]   # bars from zero: no truncated axis
    axes[1].bar(names, dco2, color=cols, edgecolor='white')
    axes[1].axhline(0, color=MUTED, lw=0.8)
    axes[1].set_ylabel(f'Extra cumulative CO$_2$ vs {ref} (Mt)')
    axes[1].set_title(f'CO$_2$ 2020-2059 (negative = avoided){title_suffix}', loc='left')
    for i, c in enumerate(cum):
        axes[1].text(i, dco2[i], f'{c:,.0f} Mt', ha='center', va='bottom' if dco2[i] >= 0 else 'top',
                     fontsize=7, color=INK2)
    for i, k in enumerate(names):
        if k == ref:
            continue
        d_em = (cum[iref] - cum[i]) * 1e6
        txt = f'{dcost[i] * 1e9 / d_em:,.0f} €/t avoided' if d_em > 1e5 else (
            'more CO$_2$' if d_em < -1e5 else 'no CO$_2$ avoided')
        axes[0].text(i, dcost[i], txt, ha='center', va='bottom' if dcost[i] >= 0 else 'top', fontsize=7, color=INK2)
    for ax, d in ((axes[0], dcost), (axes[1], dco2)):
        if max(abs(v) for v in d) == 0.0:                   # no difference at all: a readable axis and a note
            ax.set_ylim(-1, 1)
            ax.text(0.5, 0.62, 'no difference with ' + ref, transform=ax.transAxes, ha='center', fontsize=8,
                    color=INK2, style='italic')
    if has_sub:
        ov = [subs[k][0] for k in names]
        axes[2].bar(names, ov, color=cols, edgecolor='white')
        axes[2].set_ylabel('Electrolyser subsidy (bn €, overnight)')
        axes[2].set_title('Public subsidy (OWE-type)', loc='left')
        for i, k in enumerate(names):
            d_em = (cum[iref] - cum[i]) * 1e6
            if ov[i] > 0:
                txt = f'{subs[k][1] * 1e9 / d_em:,.0f} € subsidy/t' if d_em > 1e5 else 'no CO$_2$ avoided'
                axes[2].text(i, ov[i], txt, ha='center', va='bottom', fontsize=7, color=INK2)
    for ax in axes:
        ax.tick_params(axis='x', rotation=20)
        _style(ax)
    return axes


# --------------------------------------------------------------------------
# (2b) response to the CO2 price
# --------------------------------------------------------------------------

def plot_co2_price_response(runs_by_price, period=2050, axes=None):
    """Two panels: H2 supply by route and total CO2 against the CO2 price (runs_by_price = {€/t: network})."""
    if axes is None:
        fig, axes = plt.subplots(1, 2, figsize=(10, 3.4))
    prices = sorted(runs_by_price)
    bal = pd.DataFrame({p: h2_balance(runs_by_price[p]).loc[period] for p in prices}).T
    for route, col in ROUTE_COLORS.items():
        if bal[route].abs().max() > 1e-3:
            axes[0].plot(prices, bal[route], '-', color=col, lw=2, marker='o', ms=5, label=route)
    axes[0].set_xlabel(f'CO$_2$ price in {period} (€/t)')
    axes[0].set_ylabel('TWh H$_2$ per year')
    axes[0].set_title(f'Hydrogen by route, {period}', loc='left')
    axes[0].legend(fontsize=7)
    co2 = [co2_emissions(runs_by_price[p]).loc[period] for p in prices]
    axes[1].plot(prices, [c['CO2 total (Mt/yr)'] for c in co2], '-', color=INK2, lw=2, marker='o', ms=5,
                 label='All sectors')
    axes[1].plot(prices, [c['CO2 from H2 production (Mt/yr)'] for c in co2], '-', color=ROUTE_COLORS['Grey (SMR)'],
                 lw=2, marker='s', ms=5, label='Hydrogen production')
    axes[1].axhline(0, color=MUTED, lw=0.8)
    axes[1].set_xlabel(f'CO$_2$ price in {period} (€/t)')
    axes[1].set_ylabel('Mt CO$_2$ per year')
    axes[1].set_title(f'CO$_2$ emissions, {period}', loc='left')
    axes[1].legend(fontsize=7)
    for ax in axes:
        _style(ax)
    return axes


# --------------------------------------------------------------------------
# (2c, 3a) capacity and cost bars
# --------------------------------------------------------------------------

def plot_capacity_and_cost(runs, column, period=2050, axes=None, title=None):
    """Two panels: one capacity output (e.g. 'Electrolyser capacity (GW_el)', 'Battery (GW)') and annual system cost."""
    if axes is None:
        fig, axes = plt.subplots(1, 2, figsize=(10, 3.2))
    names = list(runs)
    s = {k: summary(runs[k]).loc[period] for k in names}
    cols = colors_for(names)
    axes[0].bar(names, [s[k][column] for k in names], color=cols, edgecolor='white')
    axes[0].set_ylabel(column)
    axes[0].set_title(title or f'{column.split(" (")[0]}, {period}', loc='left')
    vals = [s[k]['System cost (bn €/yr)'] for k in names]
    d = [v - vals[0] for v in vals]                        # bars from zero: no truncated axis
    axes[1].bar(names, d, color=cols, edgecolor='white')
    axes[1].axhline(0, color=MUTED, lw=0.8)
    axes[1].set_ylabel(f'Extra annual system cost vs {names[0]} (bn €/yr)')
    axes[1].set_title(f'Annual system cost, {period}', loc='left')
    for i, v in enumerate(vals):
        axes[1].text(i, d[i], f'{v:.1f} bn €/yr', ha='center', va='bottom' if d[i] >= 0 else 'top',
                     fontsize=7, color=INK2)
    span = max(max(d) - min(d), 1e-6)                      # room for the labels above and below the bars
    axes[1].set_ylim(min(min(d), 0) - 0.12 * span, max(max(d), 0) + 0.12 * span)
    for ax in axes:
        ax.tick_params(axis='x', rotation=20)
        _style(ax)
    return axes


# --------------------------------------------------------------------------
# (3b, 3c) operation: time series and duration curves
# --------------------------------------------------------------------------

def _active(n, comp, carriers, period):
    c = {'Link': n.links, 'StorageUnit': n.storage_units, 'Store': n.stores}[comp]
    act = n.get_active_assets(comp, period)
    return [i for i in c.index[c.carrier.isin(carriers)] if act.get(i, False)]


def plot_operation_timeseries(n, period=2050, ax=None, title=None, windows=(('January', '01-01', '01-29'),
                                                                              ('July', '07-01', '07-29'))):
    """(3b) Electrolyser power use and battery charging/discharging (GW) in two 4-week windows."""
    ely = _active(n, 'Link', ELECTROLYSIS, period)
    bat = _active(n, 'StorageUnit', BATTERY, period)
    t = n.snapshots[n.snapshots.get_level_values(0) == period].get_level_values(1)
    e = pd.Series(ts(n, 'links', 'p0').loc[period, ely].sum(axis=1).values / 1e3, index=t) if ely else None
    b = pd.Series(ts(n, 'storage_units', 'p').loc[period, bat].sum(axis=1).values / 1e3, index=t) if bat else None
    fig, axes = plt.subplots(1, len(windows), figsize=(12, 3.2), sharey=True)
    for ax, (lab, a, z) in zip(np.atleast_1d(axes), windows):
        sl = slice(f'{period}-{a}', f'{period}-{z}')
        if e is not None:
            ax.step(e.loc[sl].index, e.loc[sl].values, where='post', color=CARRIER_COLORS['electrolyser'], lw=1.6,
                    label='Electrolysers (power use)')
        if b is not None:
            ax.step(b.loc[sl].index, b.loc[sl].values, where='post', color=CARRIER_COLORS['battery'], lw=1.6,
                    label='Battery (+ discharge / - charge)')
        ax.axhline(0, color=MUTED, lw=0.8)
        ax.set_title(f'{lab} {period}', loc='left', fontsize=9)
        ax.tick_params(axis='x', rotation=30, labelsize=7)
        _style(ax)
    np.atleast_1d(axes)[0].set_ylabel('GW')
    h, l = np.atleast_1d(axes)[0].get_legend_handles_labels()
    fig.legend(h, l, loc='lower center', ncol=2, fontsize=8)
    fig.suptitle(title or f'Electrolyser and battery operation, {period}', x=0.01, ha='left', fontweight='bold',
                 fontsize=10)
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    return fig


def plot_soc_duration(runs, period=2050, ax=None):
    """Duration curve of the battery state of charge (share of energy capacity), one line per run."""
    ax = _new_ax(ax, (5.5, 3.2))
    cols = colors_for(list(runs))
    for i, (name, n) in enumerate(runs.items()):
        bat = _active(n, 'StorageUnit', BATTERY, period)
        if not bat:
            continue
        cap = (n.storage_units.loc[bat, 'p_nom_opt'] * n.storage_units.loc[bat, 'max_hours']).sum()
        if cap <= 1:
            continue
        soc = ts(n, 'storage_units', 'state_of_charge').loc[period, bat].sum(axis=1) / cap
        dur = np.sort(soc.values)[::-1]
        hours = np.arange(1, len(dur) + 1) * n.snapshot_weightings.generators.loc[period].iloc[0]
        ax.plot(hours, dur, color=cols[i], lw=2, label=name)
    ax.set_xlabel('Hours per year')
    ax.set_ylabel('State of charge (share of capacity)')
    ax.set_title(f'Battery state of charge, duration curve {period}', loc='left')
    ax.set_ylim(0, 1.05)
    ax.legend(fontsize=7)
    _style(ax)
    return ax


def plot_electrolyser_duration(runs, period, ax=None):
    """Duration curve of electrolyser use (share of installed capacity), one line per run."""
    ax = _new_ax(ax, (5.5, 3.2))
    cols = colors_for(list(runs))
    for i, (name, n) in enumerate(runs.items()):
        act = _active(n, 'Link', ELECTROLYSIS, period)
        cap = n.links.loc[act, 'p_nom_opt'].sum()
        if cap <= 1:
            continue
        p = ts(n, 'links', 'p0').loc[period, act].sum(axis=1)
        dur = np.sort((p / cap).values)[::-1]
        hours = np.arange(1, len(dur) + 1) * n.snapshot_weightings.generators.loc[period].iloc[0]
        ax.plot(hours, dur, color=cols[i], lw=2, label=name)
    ax.set_xlabel('Hours per year')
    ax.set_ylabel('Electrolyser load (share of capacity)')
    ax.set_title(f'Electrolyser duration curve, {period}', loc='left')
    ax.set_ylim(0, 1.05)
    ax.legend(fontsize=7)
    _style(ax)
    return ax



def plot_hydrogen_balance(scen):
    """Course-style energy balance of the hydrogen demand bus (same layout as plot_main_ebs in P06)."""
    fig, ax = plt.subplots(figsize=(6, 4))
    df = scen.statistics.energy_balance(bus_carrier=H2_BUS)
    df = df.set_index(df.index.get_level_values(1))
    df.T.plot(kind='bar', stacked=True, rot=0, colormap='tab20', ax=ax)
    ax.set_ylabel('MWh')
    ax.set_title('Hydrogen')
    ax.legend(bbox_to_anchor=(1, 1), fontsize=7)
    fig.tight_layout()
    return ax


# --------------------------------------------------------------------------
# The policy story (Francesco, 14 Oct): what changes when water limits electrolysis
# --------------------------------------------------------------------------

# Electricity sources, stacked bottom to top. This order passes the palette checker for adjacent pairs
# (colour-vision deficiency and normal vision); CCS is included in its fuel.
POWER_STACK = {'Solar': '#eb6834', 'Wind': '#2a78d6', 'Biomass': '#008300', 'Nuclear': '#6250d6',
               'Natural gas': '#b07a3a'}
_POWER_GROUPS = {'Solar': ['Solar'], 'Wind': ['Wind onshore', 'Wind offshore'], 'Biomass': ['Biomass', 'Biomass + CCS'],  # incl. dedicated
                 'Nuclear': ['Nuclear'], 'Natural gas': ['Gas', 'Gas + CCS']}
NEUTRAL_BAR = '#8a8984'       # single series without an identity (>= 3:1 on white)


def _label_bars(ax, xs, vals, fmt, dy=0.02):
    for x, v in zip(xs, vals):
        ax.text(x, v, fmt(v), ha='center', va='bottom' if v >= 0 else 'top', fontsize=7.5, color=INK,
                transform=ax.transData)


def plot_policy_story(runs, ref, period=2050, title=None, figsize=(15, 3.9)):
    """Four panels for the scenarios (runs = {name: network}, ref = the cost-optimal run, e.g. 'Base'):
    (a) extra system cost against ref, (b) gas use, (c) electricity generation by source, (d) electrolysers built.
    These are the things Francesco suggested to tell policymakers (meeting of 14 October)."""
    names = list(runs)
    x = np.arange(len(names))
    fig, axes = plt.subplots(1, 4, figsize=figsize)

    # (a) extra system cost, discounted 2020-2059 (objective + the present value of any subsidy)
    cost = [runs[k].objective / 1e9 + subsidy_cost(runs[k])[1] for k in names]
    d = [c - cost[names.index(ref)] for c in cost]
    ax = axes[0]
    ax.bar(x, d, width=0.6, color=NEUTRAL_BAR, edgecolor='white')
    ax.axhline(0, color=MUTED, lw=0.8)
    _label_bars(ax, x, d, lambda v: f'+{v:.1f}' if v > 0.05 else f'{v:.1f}')
    ax.set_ylabel(f'bn €, discounted, 2020-2059')
    ax.set_title(f'(a) Extra system cost vs {ref}', loc='left')

    # (b) gas use in the period: total, with the part used for hydrogen written on the bar
    g = {k: gas_use(runs[k]).loc[period] for k in names}
    tot = [g[k]['Gas use, total (TWh/yr)'] for k in names]
    h2 = [g[k]['Gas for H2 (TWh/yr)'] for k in names]
    ax = axes[1]
    ax.bar(x, tot, width=0.6, color=CARRIER_COLORS['gas'], edgecolor='white')
    for i in range(len(names)):
        ax.text(x[i], tot[i], f'{tot[i]:.0f}\n({h2[i]:.0f} for H$_2$)', ha='center', va='bottom', fontsize=7.5,
                color=INK)
    ax.set_ylim(0, max(tot) * 1.25)
    ax.set_ylabel('TWh per year')
    ax.set_title(f'(b) Natural gas used, {period}', loc='left')

    # (c) electricity generation by source
    mix = {k: electricity_mix(runs[k]).loc[period] for k in names}
    ax = axes[2]
    bottom = np.zeros(len(names))
    for src, col in POWER_STACK.items():
        v = np.array([sum(mix[k].get(s, 0.0) for s in _POWER_GROUPS[src]) for k in names])
        if v.max() <= 0.05:
            continue
        ax.bar(x, v, width=0.6, bottom=bottom, color=col, edgecolor='white', linewidth=1.0, label=src)
        bottom += v
    for i in range(len(names)):
        ax.text(x[i], bottom[i], f'{bottom[i]:.0f}', ha='center', va='bottom', fontsize=7.5, color=INK)
    ax.set_ylim(0, bottom.max() * 1.15)
    ax.set_ylabel('TWh per year')
    ax.set_title(f'(c) Electricity generation, {period}', loc='left')
    h, l = ax.get_legend_handles_labels()
    ax.legend(h[::-1], l[::-1], fontsize=7, loc='upper right', bbox_to_anchor=(1.0, 1.0))

    # (d) electrolysers: capacity in the period and the investment over 2020-2059
    s = {k: summary(runs[k]).loc[period] for k in names}
    cap = [s[k]['Electrolyser capacity (GW_el)'] for k in names]
    inv = [float(electrolyser_investment(runs[k]).sum()) for k in names]
    ax = axes[3]
    ax.bar(x, cap, width=0.6, color=ROUTE_COLORS['Green (grid electrolysis)'], edgecolor='white')
    for i in range(len(names)):
        ax.text(x[i], cap[i], f'{cap[i]:.1f} GW\n€{inv[i]:.1f} bn', ha='center', va='bottom', fontsize=7.5,
                color=INK)
    ax.set_ylim(0, max(max(cap), 0.1) * 1.3)
    ax.set_ylabel('GW of electricity input')
    ax.set_title(f'(d) Electrolysers, {period}', loc='left')

    for ax in axes:
        ax.set_xticks(x, names)
        _style(ax)
    fig.suptitle(title or f'What changes when water limits electrolysis ({period}; costs over 2020-2059)',
                 x=0.01, ha='left', fontweight='bold', fontsize=10.5)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    return fig


# --------------------------------------------------------------------------
# Water shadow price over the year (group Table 1), restored with store_shadow_prices
# --------------------------------------------------------------------------

def plot_water_shadow_price(n, periods=(2040, 2050), ax=None, desal_eur_per_m3=1.4, title=None):
    """Monthly water shadow price (€/m3) under the hourly water limit (electrolyser_limit_on='output', e.g.
    S2_oversized): the value of one more m3 of water for electrolysis, mean per month. The dashed line is desalinated
    water (about €1.4/m3 = €0.03/kg H2). Needs a run solved with the restored store_shadow_prices."""
    sp = (n.meta or {}).get('electrolyser_water_output_shadow_price') or {}
    ax = _new_ax(ax)
    months = list(range(1, 13))
    labels = ['J', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D']
    drawn = 0
    for i, y in enumerate(periods):
        d = (sp.get(str(y)) or {}).get('eur_per_m3_by_month') or {}
        if not d:
            continue
        vals = [float(d.get(str(m), np.nan)) for m in months]
        ax.plot(months, vals, marker='o', ms=3.5, lw=1.8, color=CATEGORICAL[i % len(CATEGORICAL)],
                label=f'{y} (mean €{sp[str(y)]["eur_per_m3_mean"]:.0f}/m³)')
        drawn += 1
    ax.axhline(desal_eur_per_m3, color=MUTED, lw=1.0, ls='--')
    ax.text(12.4, desal_eur_per_m3, f'desalinated water €{desal_eur_per_m3:.1f}/m³', va='bottom', ha='right',
            fontsize=8, color=INK2)
    ax.set_xticks(months, labels)
    ax.set_ylabel('Water shadow price (€/m³)')
    ax.set_ylim(bottom=0)
    if title is not False:
        ax.set_title(title or 'Value of one more m³ of water for electrolysis, per month')
    if drawn:
        ax.legend(frameon=False, fontsize=8, loc='upper left')
    else:
        ax.text(0.5, 0.5, 'no hourly water limit in this run', transform=ax.transAxes, ha='center', color=INK2)
    _style(ax)
    return ax
