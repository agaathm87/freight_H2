"""System figures for the freight study: where the trucks' energy comes from, and what the trucks change in the
energy system. Built on the group's system plots (system_plots.py), with the freight trucks as a sector of their own
and hydrogen as an intermediate node (the group's version treats hydrogen production as end use).

* system_flows(n, period)          whole-system flows (TWh/yr): primary sources -> electricity -> hydrogen -> sectors
                                   (incl. the freight trucks), plus conversion losses
* plot_sankey(runs, period)        one Sankey panel per run, all on one scale
* final_energy(n)                  final energy per sector and carrier (the energy balance), incl. the freight trucks
* plot_freight_energy(runs)        final energy of the freight trucks by carrier, per run and period
* plot_energy_balance(n)           final energy per sector and carrier of one run (all sectors)
* hydrogen_supply_use(n)           hydrogen supply by route and hydrogen use (industry, trucks), per period
* plot_hydrogen(runs)              hydrogen supply by route per run and period, with the trucks' use marked

Values are per year of the representative year of each period (TWh/yr). Final energy = the input of the end-use
technologies: diesel for ICE trucks, electricity for BETs, hydrogen for FCETs and H2-ICE trucks.
"""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch

_saved_rc = dict(plt.rcParams)
from . import system_plots as sp                   # imports h2_plots, which sets its own rcParams ...
from .h2_plots import ROUTE_COLORS, ROUTE_HATCH
from .h2_results import ts, _w, h2_balance
plt.rcParams.update(_saved_rc)                     # ... so the freight figures keep their own style

TWH = 1e6
INK, MUTED, GRID = '#1f2328', '#59636e', '#e6e8eb'
STYLE = {'font.size': 8, 'axes.titlesize': 9, 'axes.labelsize': 8, 'legend.fontsize': 7, 'xtick.labelsize': 7.5,
         'ytick.labelsize': 7.5, 'axes.spines.top': False, 'axes.spines.right': False, 'axes.edgecolor': MUTED,
         'axes.labelcolor': INK, 'xtick.color': MUTED, 'ytick.color': MUTED, 'font.family': 'DejaVu Sans'}

# demand bus -> sector label (final energy); the hydrogen demand is a sector fed by the Hydrogen node
SECTORS = {'Residential electricity': 'Households: electricity', 'Residential heat': 'Households: heat',
           'Transportation': 'Passenger cars', 'Freight transport': 'Freight trucks',
           'Industrial machinery': 'Industry: machinery', 'Industrial HTP': 'Industry: high-temp. heat'}
H2_SECTOR = 'Industry: hydrogen (feedstock)'
# bus -> carrier label; the course's 'Gasoline supply' is the oil product of cars (petrol) and ICE trucks (diesel)
FUEL_OF_BUS = {'Gas supply': 'Natural gas', 'Gasoline supply': 'Oil products', 'Biomass supply': 'Biomass',
               'Nuclear supply': 'Nuclear', 'Hydrogen': 'Hydrogen', **{b: 'Electricity' for b in sp.ELEC_BUSES}}
SOURCES = ['Wind', 'Solar', 'Nuclear', 'Biomass', 'Oil products', 'Natural gas']        # first column, top down
SECTOR_ORDER = ['Households: electricity', 'Households: heat', 'Passenger cars', 'Freight trucks',
                'Industry: machinery', 'Industry: high-temp. heat', H2_SECTOR, 'Conversion losses']
COLORS = {**sp.COLORS, 'Oil products': sp.COLORS['Petrol']}
# final-energy carriers (stacking order) and colours: the system plots' colours (validated there), hydrogen aqua
CARRIERS = ['Oil products', 'Natural gas', 'Electricity', 'Hydrogen']
CARRIER_COLORS = {'Oil products': sp.COLORS['Petrol'], 'Natural gas': sp.COLORS['Natural gas'],
                  'Electricity': sp.COLORS['Electricity'], 'Hydrogen': sp.COLORS['Hydrogen']}


# ------------------------------------------------------------------------------------------------------------ flows
def system_flows(n, period):
    """Flows {(source, target): TWh/yr} of the whole system in one period.

    Columns: primary sources -> Electricity -> Hydrogen -> sectors (+ conversion losses). Power plants enter
    Electricity with their input and their losses leave it as 'Conversion losses'; the same for the hydrogen
    producers (SMR, SMR + CCS, electrolysers) and the Hydrogen node. Sectors get the input of their end-use
    technologies; the hydrogen demand gets the hydrogen it uses. Battery losses count as conversion losses."""
    sl = n.snapshots.get_level_values(0) == period
    w = _w(n)[sl]
    tot = lambda df: df.loc[sl].mul(w, axis=0).sum() / TWH
    p0, p1 = tot(ts(n, 'links', 'p0')), tot(-ts(n, 'links', 'p1'))
    flows = {}

    def add(s, t, v):
        if s and t and v > 1e-4:
            flows[(s, t)] = flows.get((s, t), 0.0) + float(v)

    gen = tot(ts(n, 'generators', 'p'))
    for g in n.generators.index[n.generators.bus.isin(sp.ELEC_BUSES)]:
        c = n.generators.at[g, 'carrier']
        add('Wind' if 'Wind' in c else ('Solar' if 'Solar' in c else c), 'Electricity', gen[g])
    for name, l in n.links.iterrows():
        f0 = FUEL_OF_BUS.get(l.bus0)
        if l.bus1 in sp.ELEC_BUSES and l.bus0 not in sp.ELEC_BUSES:            # power plants
            add(f0, 'Electricity', p0[name])
            add('Electricity', 'Conversion losses', p0[name] - p1[name])
        elif l.bus1 == 'Hydrogen':                                             # hydrogen producers
            add(f0, 'Hydrogen', p0[name])
            add('Hydrogen', 'Conversion losses', p0[name] - p1[name])
        elif l.bus1 in SECTORS:                                                # end use, incl. the trucks
            add(f0, SECTORS[l.bus1], p0[name])
    h2_loads = n.loads.index[n.loads.bus == 'Hydrogen']
    if len(h2_loads):
        add('Hydrogen', H2_SECTOR, tot(n.get_switchable_as_dense('Load', 'p_set')[h2_loads]).sum())
    if len(n.storage_units):
        add('Electricity', 'Conversion losses', tot(ts(n, 'storage_units', 'p_store')).sum()
            - tot(ts(n, 'storage_units', 'p_dispatch')).sum())
    return flows


def plot_sankey(runs, period=2050, titles=None, width=7.0, fs=1.0, note=True):
    """One Sankey panel per run (under each other), all on one scale (TWh/yr of final energy)."""
    all_flows = {k: system_flows(n, period) for k, n in runs.items()}
    tallest = max(max(sum(v for (s, t), v in fl.items() if s in SOURCES),
                      sum(v for (s, t), v in fl.items() if t in SECTOR_ORDER)) for fl in all_flows.values())
    scale = 70.0 / tallest
    panel_h = 70.0 + 2.2 * 9 + 16
    H = panel_h * len(runs) + 8
    with plt.rc_context(STYLE):
        fig = plt.figure(figsize=(width, H / 13.0))
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(0, 100), ax.set_ylim(0, H), ax.axis('off')
        units_per_pt = H / (fig.get_figheight() * 72)
        for i, (k, fl) in enumerate(all_flows.items()):
            top = H - 12 - i * panel_h
            title = (titles or {}).get(k, f'{k}: energy system in {period} (TWh per year, final energy)')
            sp.draw_system_sankey(ax, fl, title, scale, top=top, fs=fs, min_label_gap=7 * fs * 1.25 * units_per_pt,
                                  title_dy=max(6.0, 7 * fs * 2.4 * units_per_pt), sources=SOURCES,
                                  sectors=SECTOR_ORDER, colors=COLORS)
        if note:
            ax.text(0, 4, 'Model results. Ribbon width = energy (TWh/yr). Power plants and hydrogen producers enter '
                          'with their input; their losses leave as conversion losses.\nSectors: final energy (diesel '
                          'for ICE trucks, electricity for BETs, hydrogen for FCETs and H2-ICE trucks).',
                    fontsize=6.2 * min(fs, 1.4), style='italic', color=MUTED, va='center', linespacing=1.4)
    return fig


# ------------------------------------------------------------------------------------------------- energy balance
def final_energy(n):
    """Final energy per sector and carrier (TWh/yr): DataFrame with columns (sector, carrier), index period."""
    p0 = ts(n, 'links', 'p0').mul(_w(n), axis=0).groupby(level=0).sum()
    out = {}
    for name, l in n.links.iterrows():
        if l.bus1 in SECTORS:
            key = (SECTORS[l.bus1], FUEL_OF_BUS.get(l.bus0, 'Other'))
            out[key] = out.get(key, 0.0) + p0[name]
    h2_loads = n.loads.index[n.loads.bus == 'Hydrogen']
    if len(h2_loads):
        d = n.get_switchable_as_dense('Load', 'p_set')[h2_loads].sum(axis=1)
        out[(H2_SECTOR, 'Hydrogen')] = d.mul(_w(n)).groupby(level=0).sum()
    df = pd.DataFrame(out).fillna(0.0) / TWH
    return df.loc[:, (df.abs() > 1e-6).any()]


def _stack(ax, df, x, width=0.72):
    """Stacked bars of the final-energy carriers in their fixed order; returns the bar tops."""
    bottom = np.zeros(len(df))
    for c in [c for c in CARRIERS if c in df.columns]:
        v = df[c].values
        ax.bar(x, v, bottom=bottom, width=width, color=CARRIER_COLORS[c], edgecolor='white', linewidth=1, label=c)
        bottom = bottom + v
    return bottom


def plot_freight_energy(runs, titles=None):
    """Final energy of the freight trucks by carrier (TWh/yr), one panel per run, periods on the x axis. The labels
    above the bars give the freight transport energy delivered (truck output), so the efficiency gap is visible."""
    with plt.rc_context(STYLE):
        fig, axes = plt.subplots(1, len(runs), figsize=(1.55 * len(runs) + 0.7, 2.9), sharey=True, squeeze=False)
        for ax, (k, n) in zip(axes[0], runs.items()):
            fe = final_energy(n)
            df = fe['Freight trucks'] if 'Freight trucks' in fe.columns.get_level_values(0) else pd.DataFrame()
            x = np.arange(len(df))
            top = _stack(ax, df, x)
            from .freight_results import freight_output
            outp = freight_output(n).sum(axis=1).reindex(df.index)
            for i, (t, o) in enumerate(zip(top, outp.values)):
                ax.text(i, t + 1.0, f'{o:.0f}', ha='center', va='bottom', fontsize=6, color=MUTED)
            ax.set_ylim(0, 72)
            ax.set_xticks(x, [str(p) for p in df.index], fontsize=6.5)
            ax.set_title((titles or {}).get(k, k), fontsize=7.5, loc='left', color=INK)
            ax.grid(axis='y', color=GRID, linewidth=0.6)
            ax.set_axisbelow(True)
        axes[0][0].set_ylabel('Final energy of freight trucks\n(TWh/yr)')
        present = {c for ax in axes[0] for c in ax.get_legend_handles_labels()[1]}
        handles = [Patch(facecolor=CARRIER_COLORS[c], edgecolor='white', label=c) for c in CARRIERS if c in present]
        fig.legend(handles=handles, loc='lower center', ncol=len(handles), frameon=False, bbox_to_anchor=(0.5, -0.03))
        fig.text(0.99, 0.01, 'Labels: freight delivered (TWh/yr)', ha='right', fontsize=6, color=MUTED)
        fig.tight_layout(rect=(0, 0.07, 1, 1))
    return fig


def plot_energy_balance(n, title=None):
    """Final energy per sector and carrier of one run (TWh/yr): the energy balance, incl. the freight trucks."""
    fe = final_energy(n)
    sectors = [s for s in SECTOR_ORDER if s in fe.columns.get_level_values(0)]
    with plt.rc_context(STYLE):
        fig, axes = plt.subplots(1, len(sectors), figsize=(1.15 * len(sectors) + 0.8, 2.9), sharey=True, squeeze=False)
        for ax, s in zip(axes[0], sectors):
            df = fe[s]
            _stack(ax, df, np.arange(len(df)))
            ax.set_xticks(np.arange(len(df)), [str(p) for p in df.index], rotation=90)
            ax.set_title(s.replace(': ', ':\n'), fontsize=7, loc='left', color=INK)
            ax.grid(axis='y', color=GRID, linewidth=0.6)
            ax.set_axisbelow(True)
        axes[0][0].set_ylabel('Final energy (TWh/yr)')
        present = {c for ax in axes[0] for c in ax.get_legend_handles_labels()[1]}
        handles = [Patch(facecolor=CARRIER_COLORS[c], edgecolor='white', label=c) for c in CARRIERS if c in present]
        fig.legend(handles=handles, loc='lower center', ncol=len(handles), frameon=False, bbox_to_anchor=(0.5, -0.03))
        if title:
            fig.suptitle(title, x=0.01, ha='left', fontsize=9, fontweight='bold', color=INK)
        fig.tight_layout(rect=(0, 0.07, 1, 0.95 if title else 1))
    return fig


# ------------------------------------------------------------------------------------------------------- hydrogen
def hydrogen_supply_use(n):
    """Hydrogen supply by route and use per period (TWh H2/yr): the routes of h2_balance plus 'Use: industry' (the
    1.3 Mt feedstock demand) and 'Use: freight trucks' (FCET and H2-ICE input)."""
    bal = h2_balance(n)[list(ROUTE_COLORS)].clip(lower=0)            # TWh/yr already
    p0 = ts(n, 'links', 'p0').mul(_w(n), axis=0).groupby(level=0).sum()
    trucks = n.links.index[(n.links.bus0 == 'Hydrogen') & (n.links.bus1 == 'Freight transport')]
    bal['Use: freight trucks'] = p0[trucks].sum(axis=1) / TWH if len(trucks) else 0.0
    h2_loads = n.loads.index[n.loads.bus == 'Hydrogen']
    d = n.get_switchable_as_dense('Load', 'p_set')[h2_loads].sum(axis=1)
    bal['Use: industry'] = d.mul(_w(n)).groupby(level=0).sum() / TWH
    return bal


def plot_hydrogen(runs, titles=None):
    """Hydrogen supply by route (stacked bars) per run and period, with the hydrogen the trucks use marked as a
    dark tick (TWh H2/yr)."""
    with plt.rc_context(STYLE):
        fig, axes = plt.subplots(1, len(runs), figsize=(1.55 * len(runs) + 1.6, 2.9), sharey=True, squeeze=False)
        used, ymax = set(), 0.0
        for ax, (k, n) in zip(axes[0], runs.items()):
            b = hydrogen_supply_use(n)
            x = np.arange(len(b))
            bottom = np.zeros(len(b))
            for r, colr in ROUTE_COLORS.items():
                v = b[r].values
                if (v > 1e-3).any():
                    ax.bar(x, v, bottom=bottom, width=0.72, color=colr, hatch=ROUTE_HATCH.get(r), edgecolor='white',
                           linewidth=1, label=r)
                    used.add(r)
                bottom = bottom + v
            t = b['Use: freight trucks'].values
            ax.scatter(x[t > 0.05], t[t > 0.05], marker='_', s=260, linewidths=2.2, color=INK, zorder=4,
                       label='Used by freight trucks')
            ax.set_xticks(x, [str(p) for p in b.index], fontsize=6.5)
            ymax = max(ymax, float(bottom.max()))
            ax.set_title((titles or {}).get(k, k), fontsize=7.5, loc='left', color=INK)
            ax.grid(axis='y', color=GRID, linewidth=0.6)
            ax.set_axisbelow(True)
        axes[0][0].set_ylabel('Hydrogen supply (TWh H$_2$/yr)')
        axes[0][0].set_ylim(0, 1.05 * ymax if ymax > 0 else 1.0)       # shared y axis, from zero
        handles = [Patch(facecolor=ROUTE_COLORS[r], hatch=ROUTE_HATCH.get(r), edgecolor='white', label=r)
                   for r in ROUTE_COLORS if r in used]
        handles.append(plt.Line2D([], [], color=INK, lw=2.2, label='Used by freight trucks'))
        fig.legend(handles=handles, loc='center left', frameon=False, bbox_to_anchor=(1.0, 0.55))
        fig.tight_layout()
    return fig
