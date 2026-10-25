"""System-wide plots of the final course model with the hydrogen extension.

* course_plot_main_ebs(), course_plot_elc_emi()   the course's quick diagnostic plots (interface.ipynb), unchanged
* course_plot_h2_eb()                             the same quick plot for the hydrogen bus
* final_energy() / plot_energy_balance()         final energy per demand sector and carrier (the energy balances)
* electricity_supply() / plot_electricity_supply()  electricity generation by source, per run and period
* capacity() / plot_capacity()                    installed electricity capacity by source
* co2_by_sector() / plot_co2_by_sector()          CO2 to the atmosphere by sector, with negative emissions (BECCS)
* system_flows() / plot_system_sankey()           Sankey diagram of the whole energy system for one period

All energy values are per year of the representative year of each period (TWh/yr), CO2 in Mt/yr.

Colours (validated with the dataviz palette checker for the stacking orders used below):
  sources   wind #2a78d6, solar #eb6834, nuclear #6250d6, biomass #008300, petrol #e87ba4, natural gas #b07a3a,
            battery #e34948
  carriers  electricity #eda100, hydrogen #1baf7a
  CCS variants use the colour of their fuel with a hatch, so CCS is not shown by colour alone.

The interface calls `main()` to draw plots for the saved main runs into
`results/plots`.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch, PathPatch, Rectangle
from matplotlib.path import Path as MPath

from .h2_plots import INK, INK2, MUTED, GRID, CATEGORICAL, _style
from .h2_results import ts, _w

TWH = 1e6     # MWh per TWh
MT = 1e6      # t per Mt

COLORS = {'Wind': '#2a78d6', 'Solar': '#eb6834', 'Nuclear': '#6250d6', 'Biomass': '#008300',
          'Biomass + CCS': '#008300', 'Petrol': '#e87ba4', 'Natural gas': '#b07a3a', 'Natural gas + CCS': '#b07a3a',
          'Battery': '#e34948', 'Electricity': '#eda100', 'Hydrogen': '#1baf7a'}
HATCHED = {'Natural gas + CCS', 'Biomass + CCS'}
LOSS_COLOR = '#e2e1dc'
SECTOR_COLOR = INK2

# bus -> name of the energy carrier (source) it carries
FUEL_OF_BUS = {'Gas supply': 'Natural gas', 'Gasoline supply': 'Petrol', 'Biomass supply': 'Biomass',
               'Nuclear supply': 'Nuclear', 'Electricity': 'Electricity',
               'Dedicated electricity': 'Electricity', 'Nuclear electricity': 'Electricity',      # options (old names)
               'Electricity - pure green': 'Electricity', 'Electricity - pink': 'Electricity'}   # options ([Freight])
# buses that carry electricity: the grid and the dedicated buses of the pure green and pink options ([Freight]: the
# options' buses are called 'Electricity - pure green' and 'Electricity - pink' in this package)
ELEC_BUSES = ['Electricity', 'Dedicated electricity', 'Nuclear electricity', 'Electricity - pure green',
              'Electricity - pink']
# demand bus -> sector label (final energy). The hydrogen demand is served by end-use technologies (SMR, SMR CCS,
# electrolyser), so its final energy is the gas and electricity those technologies use, like any other sector.
H2_SECTOR = 'Industry: hydrogen (feedstock)'
SECTORS = {'Residential electricity': 'Households: electricity', 'Residential heat': 'Households: heat',
           'Transportation': 'Transport', 'Industrial machinery': 'Industry: machinery',
           'Industrial HTP': 'Industry: high-temp. heat', 'Hydrogen': H2_SECTOR}


# --------------------------------------------------------------------------
# The course's plotting functions (interface.ipynb of the final model), unchanged
# --------------------------------------------------------------------------

def course_plot_main_ebs(scen):
    fig, ax = plt.subplots(1, 5)
    fig.set_size_inches(20, 4)
    for n, c in enumerate(['Residential electricity', 'Residential heat', 'Transportation', 'Industrial machinery',
                           'Industrial HTP']):
        df = scen.statistics.energy_balance(bus_carrier=c)
        df = df.set_index(df.index.get_level_values(1))
        df.T.plot(kind='bar', stacked='True', rot=0, colormap='tab20', ax=ax[n])
        if c == 'Transportation':
            ax[n].set_ylabel('Mvkm')
        else:
            ax[n].set_ylabel('MWh')
        ax[n].set_title(c)
    fig.tight_layout()
    return fig


def course_plot_elc_emi(scen):
    fig, ax = plt.subplots(1, 5)
    fig.set_size_inches(20, 4)
    for n, c in enumerate(['Electricity', 'CO2 atmosphere', 'CO2 storage']):
        df = scen.statistics.energy_balance(bus_carrier=c)
        df = df.set_index(df.index.get_level_values(1))
        df.T.plot(kind='bar', stacked='True', rot=0, colormap='tab20', ax=ax[n])
        if 'CO2' in c:
            ax[n].set_ylabel('tCO2')
        else:
            ax[n].set_ylabel('MWh')
        ax[n].set_title(c)
        ax[n].legend(bbox_to_anchor=(1, -0.5))
    for n, c in enumerate(['CO2 atmosphere', 'CO2 storage']):
        df = scen.statistics.energy_balance(bus_carrier=c).cumsum(axis=1)
        df = df.set_index(df.index.get_level_values(1))
        df.T.plot(kind='bar', stacked=True, colormap='tab20', ax=ax[n + 3])
        ax[n + 3].set_ylabel('tCO2')
        ax[n + 3].set_title(f'Cumulative {c}')
        ax[n + 3].legend(bbox_to_anchor=(1, -0.5))
    fig.tight_layout()
    return fig


def course_plot_h2_eb(scen):
    """[H2] The same kind of quick plot for the hydrogen bus."""
    fig, ax = plt.subplots(figsize=(6, 4))
    df = scen.statistics.energy_balance(bus_carrier='Hydrogen')
    df = df.set_index(df.index.get_level_values(1))
    df.T.plot(kind='bar', stacked=True, rot=0, colormap='tab20', ax=ax)
    ax.set_ylabel('MWh'); ax.set_title('Hydrogen'); ax.legend(bbox_to_anchor=(1, 1))
    fig.tight_layout()
    return fig


# --------------------------------------------------------------------------
# Flows per period (MWh/yr)
# --------------------------------------------------------------------------

def _period_sum(n, component, attr, sign=1.0):
    """Weighted annual sum per period and asset of a time series (MWh/yr): DataFrame period x asset."""
    df = ts(n, component, attr) * sign
    return df.mul(_w(n), axis=0).groupby(level=0).sum()


def _links_where(n, **buses):
    sel = pd.Series(True, index=n.links.index)
    for col, val in buses.items():
        vals = val if isinstance(val, (list, tuple, set)) else [val]
        sel &= n.links[col].isin(vals)
    return n.links.index[sel]


def _fuel_label(carrier, fuel):
    if 'CCS' in carrier and fuel in ('Natural gas', 'Biomass'):
        return f'{fuel} + CCS'
    return fuel


def final_energy(n):
    """Final energy per sector and carrier (TWh/yr): DataFrame with columns (sector, carrier), index period.

    Final energy = the input of the end-use technologies (boilers, heat pumps, cars, machines, furnaces, and the
    reformers and electrolysers that serve the hydrogen demand).
    """
    p0 = _period_sum(n, 'links', 'p0')
    out = {}
    for bus, sector in SECTORS.items():
        for name in _links_where(n, bus1=bus):
            fuel = _fuel_label(n.links.at[name, 'carrier'], FUEL_OF_BUS.get(n.links.at[name, 'bus0'], 'Other'))
            out[(sector, fuel)] = out.get((sector, fuel), 0.0) + p0[name]
    df = pd.DataFrame(out).fillna(0.0) / TWH
    return df.loc[:, (df.abs() > 1e-6).any()]


def electricity_supply(n):
    """Electricity generation by source (TWh/yr), index period."""
    out = {}
    gen = _period_sum(n, 'generators', 'p')
    for g in n.generators.index[n.generators.bus.isin(ELEC_BUSES)]:
        c = n.generators.at[g, 'carrier']
        src = 'Wind' if 'Wind' in c else ('Solar' if 'Solar' in c else c)
        out[src] = out.get(src, 0.0) + gen[g]
    p1 = _period_sum(n, 'links', 'p1', -1.0)
    for name in _links_where(n, bus1=ELEC_BUSES):
        src = _fuel_label(n.links.at[name, 'carrier'], FUEL_OF_BUS.get(n.links.at[name, 'bus0'], 'Other'))
        out[src] = out.get(src, 0.0) + p1[name]
    if len(n.storage_units):
        disp = _period_sum(n, 'storage_units', 'p_dispatch')
        out['Battery'] = disp.sum(axis=1)
    df = pd.DataFrame(out).fillna(0.0) / TWH
    return df.loc[:, (df.abs() > 1e-6).any()]


def capacity(n):
    """Installed electricity capacity by source (GW of electric output), active in each period."""
    rows = {}
    for y in n.investment_periods:
        r = {}
        act_g = n.get_active_assets('Generator', y)
        for g in n.generators.index[n.generators.bus.isin(ELEC_BUSES)]:
            if act_g.get(g, False):
                c = n.generators.at[g, 'carrier']
                src = 'Wind' if 'Wind' in c else ('Solar' if 'Solar' in c else c)
                r[src] = r.get(src, 0.0) + n.generators.at[g, 'p_nom_opt']
        act_l = n.get_active_assets('Link', y)
        for name in _links_where(n, bus1=ELEC_BUSES):
            if act_l.get(name, False):
                src = _fuel_label(n.links.at[name, 'carrier'], FUEL_OF_BUS.get(n.links.at[name, 'bus0'], 'Other'))
                r[src] = r.get(src, 0.0) + n.links.at[name, 'p_nom_opt'] * n.links.at[name, 'efficiency']
        if len(n.storage_units):
            act_s = n.get_active_assets('StorageUnit', y)
            r['Battery'] = sum(n.storage_units.at[s, 'p_nom_opt'] for s in n.storage_units.index if act_s.get(s, False))
        rows[y] = r
    df = pd.DataFrame(rows).T.fillna(0.0) / 1e3
    return df.loc[:, (df.abs() > 1e-3).any()]


CO2_SECTORS = {  # sector: link carriers (emissions at bus2 = CO2 atmosphere)
    'Power': ['CCGT', 'CCGT - existing', 'CCGT CCS'],
    'Hydrogen production': ['SMR', 'SMR - existing', 'SMR CCS'],
    'Households': ['Residential gas boiler', 'Residential gas boiler - existing'],
    'Industry': ['Industrial machinery - fossil', 'Industrial machinery - fossil - existing',
                 'Industrial machinery - fossil CCS', 'Industrial HTP - fossil', 'Industrial HTP - fossil - existing',
                 'Industrial HTP - fossil CCS'],
    'Transport': ['ICE car', 'ICE car - existing'],
    'BECCS (negative)': ['Biomass plant CCS'],
}
CO2_COLORS = {'Power': '#eda100', 'Hydrogen production': '#1baf7a', 'Households': '#2a78d6', 'Industry': '#b07a3a',
              'Transport': '#e87ba4', 'BECCS (negative)': '#008300'}


def co2_by_sector(n):
    """CO2 to the atmosphere by sector (Mt/yr), index period; BECCS is negative."""
    p2 = _period_sum(n, 'links', 'p2', -1.0)       # -p2 = flow INTO the CO2 atmosphere store
    out = {}
    for sector, carriers in CO2_SECTORS.items():
        links = [l for l in _links_where(n, bus2='CO2 atmosphere') if n.links.at[l, 'carrier'] in carriers]
        out[sector] = p2[links].sum(axis=1) if links else pd.Series(0.0, index=p2.index)
    other = [l for l in _links_where(n, bus2='CO2 atmosphere')
             if not any(n.links.at[l, 'carrier'] in c for c in CO2_SECTORS.values())]
    if other:
        out['Other'] = p2[other].sum(axis=1)
    df = pd.DataFrame(out) / MT
    return df.loc[:, (df.abs() > 1e-6).any()]


# --------------------------------------------------------------------------
# Plots: stacked bars per period, one panel per run (shared y axis)
# --------------------------------------------------------------------------

def _stack(ax, df, order, colors, hatched=(), width=0.72):
    """Stacked bars (positive up, negative down) with white gaps between segments."""
    x = np.arange(len(df.index))
    pos = np.zeros(len(x)); neg = np.zeros(len(x))
    for col in [c for c in order if c in df.columns]:
        v = df[col].values
        up = np.where(v > 0, v, 0.0); dn = np.where(v < 0, v, 0.0)
        kw = dict(width=width, color=colors.get(col, MUTED), edgecolor='white', linewidth=1.0,
                  hatch='////' if col in hatched else None)
        if up.any():
            ax.bar(x, up, bottom=pos, **kw); pos += up
        if dn.any():
            ax.bar(x, dn, bottom=neg, **kw); neg += dn
    ax.set_xticks(x, [str(i) for i in df.index])
    if (neg < 0).any():
        ax.axhline(0, color=MUTED, lw=0.8)
    return pos, neg


def _legend(fig, order, colors, hatched=(), present=None, ncol=None):
    labels = [c for c in order if present is None or c in present]
    handles = [Patch(facecolor=colors.get(c, MUTED), edgecolor='white', hatch='////' if c in hatched else None,
                     label=c) for c in labels]
    fig.legend(handles=handles, loc='lower center', ncol=ncol or min(len(handles), 7), frameon=False,
               bbox_to_anchor=(0.5, -0.02))


def _panels(runs, data, order, colors, ylabel, title, hatched=(), total_line=False):
    names = list(runs)
    fig, axes = plt.subplots(1, len(names), figsize=(3.1 * len(names) + 0.6, 3.6), sharey=True, squeeze=False)
    present = set()
    for ax, name in zip(axes[0], names):
        df = data[name]
        present |= set(df.columns)
        _stack(ax, df, order, colors, hatched)
        if total_line:
            tot = df.sum(axis=1)
            ax.plot(np.arange(len(tot)), tot.values, color=INK, lw=0, marker='o', ms=5, label='net', zorder=4)
            for i, v in enumerate(tot.values):          # net value just right of the bar, on a white label
                ax.text(i + 0.40, v, f'{v:.0f}', ha='left', va='center', fontsize=7, color=INK, zorder=5,
                        bbox=dict(facecolor='white', edgecolor='none', pad=0.5))
        ax.set_title(name, loc='left')
        _style(ax)
    axes[0][0].set_ylabel(ylabel)
    fig.suptitle(title, x=0.01, ha='left', fontsize=11, fontweight='bold', color=INK)
    _legend(fig, order, colors, hatched, present)
    fig.tight_layout(rect=(0, 0.1, 1, 0.95))
    return fig


SUPPLY_ORDER = ['Natural gas', 'Natural gas + CCS', 'Nuclear', 'Solar', 'Wind', 'Biomass', 'Biomass + CCS', 'Battery']
CARRIER_ORDER = ['Electricity', 'Natural gas', 'Natural gas + CCS', 'Hydrogen', 'Petrol']
CO2_ORDER = ['Power', 'Hydrogen production', 'Households', 'Industry', 'Transport', 'BECCS (negative)', 'Other']


def plot_electricity_supply(runs):
    data = {k: electricity_supply(n) for k, n in runs.items()}
    return _panels(runs, data, SUPPLY_ORDER, COLORS, 'TWh per year', 'Electricity generation by source',
                   hatched=HATCHED)


def plot_capacity(runs):
    data = {k: capacity(n) for k, n in runs.items()}
    return _panels(runs, data, SUPPLY_ORDER, COLORS, 'GW (electric output)', 'Installed electricity capacity',
                   hatched=HATCHED)


def plot_co2_by_sector(runs):
    data = {k: co2_by_sector(n) for k, n in runs.items()}
    colors = dict(CO2_COLORS, Other=MUTED)
    return _panels(runs, data, CO2_ORDER, colors, 'Mt CO$_2$ per year', 'CO$_2$ to the atmosphere by sector (dot = net)',
                   total_line=True)


def plot_energy_balance(n, title=None):
    """Final energy per demand sector, by carrier and period (TWh/yr): the energy balances of one run."""
    fe = final_energy(n)
    sectors = [s for s in list(SECTORS.values()) + [H2_SECTOR] if s in fe.columns.get_level_values(0)]
    fig, axes = plt.subplots(1, len(sectors), figsize=(2.6 * len(sectors) + 0.6, 3.4), squeeze=False)
    present = set()
    for ax, s in zip(axes[0], sectors):
        df = fe[s]
        present |= set(df.columns)
        _stack(ax, df, CARRIER_ORDER, COLORS, HATCHED)
        ax.set_title(s, loc='left', fontsize=9)
        _style(ax)
    axes[0][0].set_ylabel('TWh per year (final energy)')
    fig.suptitle(title or 'Final energy by sector and carrier', x=0.01, ha='left', fontsize=11, fontweight='bold',
                 color=INK)
    _legend(fig, CARRIER_ORDER, COLORS, HATCHED, present)
    fig.tight_layout(rect=(0, 0.1, 1, 0.94))
    return fig


# --------------------------------------------------------------------------
# Sankey of the whole energy system (final-energy view), one period
# --------------------------------------------------------------------------

SOURCES = ['Wind', 'Solar', 'Nuclear', 'Biomass', 'Petrol', 'Natural gas']     # top to bottom (validated order)
SECTOR_ORDER = list(SECTORS.values()) + ['Conversion losses']


def system_flows(n, period):
    """Flows (source, target, TWh/yr) of the whole system in one period.

    Columns: primary sources -> Electricity -> final-energy sectors (+ conversion losses).
    Power plants show their input; their conversion losses leave the Electricity node as 'Conversion losses'.
    The reformers and electrolysers are end-use technologies: their gas and electricity input is the final energy
    of the hydrogen demand. Battery losses count as conversion losses.
    """
    sl = n.snapshots.get_level_values(0) == period
    w = _w(n)[sl]
    tot = lambda df: df.loc[sl].mul(w, axis=0).sum() / TWH
    p0, p1 = tot(ts(n, 'links', 'p0')), tot(-ts(n, 'links', 'p1'))
    gen = tot(ts(n, 'generators', 'p'))
    flows = {}

    def add(s, t, v):
        if v > 1e-4:
            flows[(s, t)] = flows.get((s, t), 0.0) + v

    for g in n.generators.index:
        c, bus = n.generators.at[g, 'carrier'], n.generators.at[g, 'bus']
        src = 'Wind' if 'Wind' in c else ('Solar' if 'Solar' in c else c)
        add(src, 'Electricity', gen[g])
    for name, l in n.links.iterrows():
        b0, b1 = l.bus0, l.bus1
        f0 = FUEL_OF_BUS.get(b0)
        if b1 in ELEC_BUSES:                                     # power plants (incl. the dedicated nuclear option)
            add(f0, 'Electricity', p0[name]); add('Electricity', 'Conversion losses', p0[name] - p1[name])
        elif b1 in SECTORS:                                      # end-use technologies (incl. hydrogen): final energy
            add(f0, SECTORS[b1], p0[name])
    if len(n.storage_units):
        st = tot(ts(n, 'storage_units', 'p_store')).sum() - tot(ts(n, 'storage_units', 'p_dispatch')).sum()
        add('Electricity', 'Conversion losses', st)
    return flows


def _ribbon(ax, x0, y0t, y0b, x1, y1t, y1b, color, alpha=0.75):
    xm = (x0 + x1) / 2
    verts = [(x0, y0t), (xm, y0t), (xm, y1t), (x1, y1t), (x1, y1b), (xm, y1b), (xm, y0b), (x0, y0b), (x0, y0t)]
    codes = [MPath.MOVETO, MPath.CURVE4, MPath.CURVE4, MPath.CURVE4, MPath.LINETO,
             MPath.CURVE4, MPath.CURVE4, MPath.CURVE4, MPath.CLOSEPOLY]
    ax.add_patch(PathPatch(MPath(verts, codes), facecolor=color, edgecolor='none', alpha=alpha, zorder=1))


def _spread(ys, min_gap):
    """Label heights (top to bottom) moved apart so that neighbours are at least min_gap apart."""
    ys = list(ys)
    for i in range(1, len(ys)):
        ys[i] = min(ys[i], ys[i - 1] - min_gap)
    return ys


def draw_system_sankey(ax, flows, title, scale, top=100.0, gap=2.2, fs=1.0, min_label_gap=0.0, title_dy=6.0,
                       sources=None, sectors=None, colors=None):
    """Draw one Sankey panel in axis units (x 0-100, y from `top` down); fs scales the fonts; labels of the first and
    last column are moved apart to at least min_label_gap (axis units). sources / sectors / colors: node orders and
    colours of the first and last column (default: this module's SOURCES, SECTOR_ORDER and COLORS; [Freight] the
    freight study passes its own, with the freight trucks as a sector)."""
    SOURCES_ = sources or SOURCES
    SECTOR_ORDER_ = sectors or SECTOR_ORDER
    COLORS_ = colors or COLORS
    X = {0: 12.0, 1: 40.0, 2: 60.0, 3: 82.0}
    NW = 1.6
    col = {s: 0 for s in SOURCES_}
    col.update({'Electricity': 1, 'Hydrogen': 2})
    col.update({s: 3 for s in SECTOR_ORDER_})
    nodes = [nm for nm in SOURCES_ + ['Electricity', 'Hydrogen'] + SECTOR_ORDER_
             if any(nm in k for k in flows)]
    inflow = {nm: sum(v for (s, t), v in flows.items() if t == nm) for nm in nodes}
    outflow = {nm: sum(v for (s, t), v in flows.items() if s == nm) for nm in nodes}
    size = {nm: max(inflow[nm], outflow[nm]) for nm in nodes}
    # vertical positions: column 0 and 3 stacked from the top; Electricity at the top, Hydrogen below the middle
    pos = {}
    for c in (0, 3):
        y = top
        for nm in [m for m in nodes if col[m] == c]:
            pos[nm] = (y, y - size[nm] * scale); y -= size[nm] * scale + gap
    if 'Electricity' in nodes:
        pos['Electricity'] = (top, top - size['Electricity'] * scale)
    if 'Hydrogen' in nodes:
        # put the hydrogen node at the height of the sectors it supplies (flat ribbons), below the electricity node
        outs = [(t, v) for (s_, t), v in flows.items() if s_ == 'Hydrogen' and t in pos]
        centre = (sum((pos[t][0] + pos[t][1]) / 2 * v for t, v in outs) / sum(v for _, v in outs)) if outs else top / 2
        h = size['Hydrogen'] * scale
        e_bottom = pos['Electricity'][1] if 'Electricity' in pos else top
        h_top = min(centre + h / 2, e_bottom - 3 * gap)
        pos['Hydrogen'] = (h_top, h_top - h)
    # ribbons: at each node, outgoing flows ordered by the height of their target and incoming flows by the height
    # of their source, so that ribbons cross as little as possible
    centre = {nm: (pos[nm][0] + pos[nm][1]) / 2 for nm in nodes}
    y_out, y_in = {}, {}
    for nm in nodes:
        off = 0.0
        for (s_, t), v in sorted([kv for kv in flows.items() if kv[0][0] == nm], key=lambda kv: -centre[kv[0][1]]):
            y_out[(s_, t)] = pos[nm][0] - off; off += v * scale
        off = 0.0
        for (s_, t), v in sorted([kv for kv in flows.items() if kv[0][1] == nm], key=lambda kv: -centre[kv[0][0]]):
            y_in[(s_, t)] = pos[nm][0] - off; off += v * scale
    for (s_, t), v in flows.items():
        h = v * scale
        color = LOSS_COLOR if t == 'Conversion losses' else COLORS_.get(s_, MUTED)
        _ribbon(ax, X[col[s_]] + NW, y_out[(s_, t)], y_out[(s_, t)] - h, X[col[t]], y_in[(s_, t)], y_in[(s_, t)] - h, color)
    label_y = {}
    for c in (0, 3):
        names_c = [m for m in nodes if col[m] == c]
        ys = _spread([(pos[m][0] + pos[m][1]) / 2 for m in names_c], min_label_gap)
        label_y.update(dict(zip(names_c, ys)))
    for nm in nodes:
        yt, yb = pos[nm]
        fc = COLORS_.get(nm, SECTOR_COLOR if nm != 'Conversion losses' else '#b9b8b2')
        ax.add_patch(Rectangle((X[col[nm]], yb), NW, max(yt - yb, 0.25), facecolor=fc, edgecolor='none', zorder=2))
        lab = f'{nm}  {size[nm]:.0f}'
        if col[nm] == 0:
            ax.text(X[0] - 1.0, label_y[nm], lab, ha='right', va='center', fontsize=7 * fs, color=INK)
        elif col[nm] == 3:
            ax.text(X[3] + NW + 1.0, label_y[nm], lab, ha='left', va='center', fontsize=7 * fs, color=INK)
        else:
            ax.text(X[col[nm]] + NW / 2, yt + 0.8, lab, ha='center', va='bottom', fontsize=7 * fs, color=INK, zorder=3,
                    bbox=dict(facecolor='white', edgecolor='none', pad=0.3, alpha=0.9))
    if title:
        ax.text(0, top + title_dy, title, ha='left', va='center', fontsize=9.5 * fs, fontweight='bold', color=INK)


def plot_system_sankey(runs, period=2050, fs=1.0, figsize=None, title=None, note=True, scale_runs=None, fit=False):
    """One Sankey panel per run, all on the same scale (TWh/yr): primary sources -> electricity -> hydrogen ->
    final-energy sectors and conversion losses. fs scales the fonts; figsize (w, h) for slides; title: a
    function name -> panel title; scale_runs: runs that set the common scale (default: runs), so that figures of
    single runs can share one scale."""
    all_flows = {k: system_flows(n, period) for k, n in runs.items()}

    def col_total(fl, names):
        return max(sum(v for (s, t), v in fl.items() if s == nm or t == nm) for nm in names) if fl else 0

    scale_flows = all_flows if scale_runs is None else {k: system_flows(n, period) for k, n in scale_runs.items()}
    tallest = max(max(sum(v for (s, t), v in fl.items() if s in SOURCES),
                      sum(v for (s, t), v in fl.items() if t in SECTOR_ORDER)) for fl in scale_flows.values())
    scale = 70.0 / tallest
    panel_h = 70.0 + 2.2 * 8 + 16
    H = panel_h * len(runs) + 8
    fig = plt.figure(figsize=figsize or (8.0, H / 13.0))
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 100); ax.set_ylim(0, H); ax.axis('off')
    units_per_pt = H / (fig.get_figheight() * 72)
    for i, (k, fl) in enumerate(all_flows.items()):
        top = H - 12 - i * panel_h
        draw_system_sankey(ax, fl, title(k) if title else f'{k}: energy system in {period} (TWh per year, final energy)',
                           scale, top=top, fs=fs, min_label_gap=7 * fs * 1.25 * units_per_pt,
                           title_dy=max(6.0, 7 * fs * 2.4 * units_per_pt))
    if note:
        ax.text(0, 3, 'Model results. Ribbon width = energy (TWh/yr). Power plants enter with their input; their losses '
                      'leave as conversion losses. Sector values are final energy: for hydrogen, the gas and electricity '
                      'that the reformers and electrolysers use.',
                fontsize=6.6 * min(fs, 1.4), style='italic', color=INK2, va='center')
    if fit:                 # keep every label inside the figure (fixed width for the report or a slide)
        from .h2_sankey import fit_texts
        fit_texts(ax)
    return fig


# --------------------------------------------------------------------------
# Draw the figures for the saved main runs
# --------------------------------------------------------------------------

def save(fig, path_stem):
    for ext in ('png', 'svg'):
        fig.savefig(f'{path_stem}.{ext}', dpi=300, bbox_inches='tight', facecolor='white')
    plt.close(fig)


def main(fig_dir='results/plots'):
    import os
    import pypsa
    os.makedirs(fig_dir, exist_ok=True)
    load = lambda r: pypsa.Network(f'results/runs/{r}.nc')
    B = {'Base': load('S1'), 'Medium': load('S2'), 'Scarce': load('S3')}
    for k in B:
        save(plot_energy_balance(B[k], f'{k}: final energy by sector and carrier'), f'{fig_dir}/S_energy_balance_{k}')
    save(plot_electricity_supply(B), f'{fig_dir}/S_electricity_supply')
    save(plot_capacity(B), f'{fig_dir}/S_capacity')
    save(plot_co2_by_sector(B), f'{fig_dir}/S_co2_by_sector')
    save(plot_system_sankey(B, 2050), f'{fig_dir}/S_system_sankey_2050')
    save(plot_system_sankey({'Base': B['Base']}, 2020), f'{fig_dir}/S_system_sankey_2020')
    save(course_plot_main_ebs(B['Base']), f'{fig_dir}/course_main_ebs_Base')
    save(course_plot_elc_emi(B['Base']), f'{fig_dir}/course_elc_emi_Base')
    print('figures written to', fig_dir)


if __name__ == '__main__':
    import warnings
    warnings.filterwarnings('ignore')
    main()

