"""Figures for the presentation (16:9 slides), drawn from the saved runs in results/runs.

    The interface calls `main()` for every figure whose runs are on disk, or
    passes selected figure names from `FIGURES`.

Each figure is sized for the content box of the group's slide template (16:9, 11.5 x 4.76 inches under the title;
fonts of 10.5 pt or more at that size) and saved as PNG (200 dpi) and SVG in results/plots/presentation. Colours as in h2_plots: the colour of the hydrogen (green, pure
green, pink, blue, and grey with a hatch) and the scenarios (Base violet, Medium yellow, Scarce red, never blue or
green, so a scenario is not mistaken for a hydrogen colour). Every chart with two or more series has a legend or
direct labels; values are written on the bars.

Storyline, one figure per slide (Table 2 of the report gives the plot for each parameter):
  P00 colours      the colours of hydrogen and the routes in the model (framing; options are dashed)
  P01 routes       hydrogen by route per scenario and period (row 1: stacked bar)
  P02 sankey       the hydrogen system per scenario in 2050 (row 1: Sankey)
  P03 cost         what water scarcity costs: system cost, CO2, gas imports, cost per kg of green hydrogen lost
  P04 story        the policy story: system cost, gas, electricity mix, electrolysers (Francesco, 14 Oct)
  P05 subsidy      (2a) electrolyser subsidy and low CAPEX
  P06 co2price     (2b) hydrogen by route and CO2 emissions against the CO2 price
  P07 options      the options (H2 storage, pure green, pink) in every scenario: heat table
  P08 storage      (2c) hydrogen storage: what is built, what it is worth, how it is used over the year
  P09 battery      (3a-c) batteries where electrolysis is limited
  P10 co2storage   blue hydrogen competes with industry and power for the capped CO2 storage
  P11 water        water for hydrogen by route
  P12 oversized    building for abundant water, then a drought (the over-dimensioned plant)
  P13 overview     every variation x scenario: heat table
  P14 numbers      key numbers per scenario (a table for a slide)
  P15 system       Sankey of the whole energy system, Base and Scarce, 2050
  P16 levers       green levers within the water scenarios (desalinated water, production subsidy, mandate): heat table
  P16b levers_co2  each lever: system cost against CO2, both against the same scenario without it

    The interface can request the report style with `styles=('apa',)`.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, to_rgb
from matplotlib.patches import FancyBboxPatch, Patch, Rectangle

from .h2_plots import (ROUTE_COLORS, ROUTE_HATCH, SCEN_COLORS, INK, INK2, MUTED, GRID, NEUTRAL_BAR, CARRIER_COLORS,
                       _style, plot_policy_story, plot_soc_duration, plot_electrolyser_duration, _active)
from .h2_results import (h2_balance, summary, ROUTES, ELECTROLYSIS_ROUTES, cumulative_co2, gas_use, _horizon, subsidy_cost, limit_cost,
                         co2_emissions, co2_stored_by_sector, water_use, electrolyser_investment, ts, _w)
from .h2_sankey import plot_sankeys_row
from energy_model.h2_presets import CO2_PRICES, CO2_STORAGE_CAPS, WATER_L_PER_KG, ELECTROLYSIS, BATTERY, H2_STORAGE
ADDITIONS = False
SET_NAME = 'without additions'

ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = ROOT / 'results' / 'runs'
OUT_DIR = ROOT / 'results' / 'plots' / 'presentation'
SLIDE = (11.5, 4.76)          # the content placeholder of the group's template (Presentation2.pptx)
SCEN = {'Base': 'S1', 'Medium': 'S2', 'Scarce': 'S3'}
SCEN_TITLE = {'Base': 'Base: no water scarcity',
              'Medium': 'Medium: ≤ 50% of Base without additions' if ADDITIONS else 'Medium: electrolysers ≤ 50% of Base',
              'Scarce': 'Scarce: no electrolysers'}
PRES_RC = {'font.size': 11, 'axes.titlesize': 12, 'axes.labelsize': 11, 'xtick.labelsize': 11,
           'ytick.labelsize': 10.5, 'legend.fontsize': 10.5, 'axes.titleweight': 'bold', 'axes.titlelocation': 'left',
           'hatch.color': 'white', 'hatch.linewidth': 1.0}
VARIANT_NAMES = {'': 'central (all additions)' if ADDITIONS else 'central',
                 '_sub20': 'subsidy 20%', '_sub40': 'subsidy 40%', '_capexlow': 'low electrolyser CAPEX',
                 '_infra20': 'infrastructure subsidy 20%', '_infra40': 'infrastructure subsidy 40%',
                 '_co2low': 'CO$_2$ price low', '_co2high': 'CO$_2$ price high',
                 '_noadd': 'without additions', '_storage': 'only H$_2$ storage', '_green': 'only pure green',
                 '_pink': 'only pink', '_storage_x3': 'H$_2$ storage 3x cost',
                 '_green_only': 'pure green only (no grid electrolysis)',
                 '_battery_cheap': 'batteries half price', '_battery_8h': 'batteries 8 h',
                 '_oversized': 'oversized plant', '_10pct': 'Scarce at 10%', '_htp_fuel': 'H$_2$ as high-temp. fuel',
                 '_desal': 'lever: desalinated water', '_desal_x10': 'desalinated water 10x cost',
                 '_prod1': 'lever: subsidy €1/kg H$_2$', '_prod2': 'lever: subsidy €2/kg H$_2$',
                 '_mandate': 'lever: mandate 60%', '_desal_mandate': 'mandate + desalinated water'}
_CACHE = {}

# Two styles of every figure: 'slide' (the content box of the group's template, large fonts, a subtitle and footnote
# that explain the figure) and 'apa' (report: 6.5 inches wide, fonts of 8 pt or more, no text that belongs in the
# figure title or note of the document; four panels as 2 x 2). Both in colour.
APA_DIR = ROOT / 'results' / 'plots' / 'apa'
STYLES = {
    'slide': dict(name='slide', size=SLIDE, tall=SLIDE, fs=1.0, notes=True, dpi=200, out=OUT_DIR, grid4=False,
                  formats=('png', 'svg')),
    'apa': dict(name='apa', size=(6.5, 3.1), tall=(6.5, 5.0), fs=0.76, notes=False, dpi=300, out=APA_DIR, grid4=True,
                formats=('png', 'svg', 'pdf'), min_pt=8.0),
}
ST = dict(STYLES['slide'])


def set_style(name):
    """Draw the next figures in this style: 'slide' or 'apa'."""
    ST.clear()
    ST.update(STYLES[name])


def F(pt):
    """A font size (points) in the current style (APA: at least 8 pt)."""
    return max(pt * ST['fs'], ST.get('min_pt', 0.0))


def RC(**extra):
    """The rc settings of the current style (font sizes scaled)."""
    rc = {k: (F(v) if k.endswith('size') and isinstance(v, (int, float)) else v) for k, v in PRES_RC.items()}
    rc.update(extra)
    return rc


def note(fig, x, y, text, **kw):
    """Text that explains the figure (subtitle, footnote): on slides only; in APA it belongs in the figure note."""
    if ST['notes']:
        fig.text(x, y, text, **kw)


def _rect(l, b, r, t):
    """tight_layout rect: in the APA style there is no subtitle, so the top is free."""
    return (l, b, r, t) if ST['notes'] else (l, b, r, 0.995)


def _row_axes(n, width_ratios=None, sharey=False):
    """A figure with n axes: one row on a slide; 2 x 2 in the APA style when n == 4."""
    if ST['grid4'] and n == 4:
        fig, axes = plt.subplots(2, 2, figsize=ST['tall'])
        return fig, list(np.ravel(axes))
    kw = dict(width_ratios=width_ratios) if width_ratios else None
    fig, axes = plt.subplots(1, n, figsize=ST['size'], sharey=sharey, gridspec_kw=kw)
    return fig, list(np.atleast_1d(axes))


def apa():
    return ST['name'] == 'apa'


# --------------------------------------------------------------------------
# Loading the saved runs
# --------------------------------------------------------------------------

def run(name):
    """A saved run (pypsa.Network), loaded once; None if it is not on disk."""
    if name not in _CACHE:
        path = RUNS_DIR / f'{name}.nc'
        if not path.exists():
            return None
        import logging
        import pypsa
        logging.getLogger('pypsa').setLevel(logging.ERROR)
        _CACHE[name] = pypsa.Network(str(path))
    return _CACHE[name]


def runs(names):
    """{label: network} for {label: run name}; None if a run is missing (the figure is then skipped)."""
    out = {}
    for label, nm in names.items():
        n = run(nm)
        if n is None:
            return None
        out[label] = n
    return out


def scenarios():
    return runs(SCEN)


def scen_color(label):
    return SCEN_COLORS[SCEN[label]]


def _econ_cost(n):
    """Economic system cost, discounted 2020-2059 (bn €): the objective plus any subsidy (a transfer)."""
    from .h2_results import economic_cost
    return economic_cost(n)


def _label(ax, x, v, txt, fs=None, color=INK, pad=0.0):
    fs = F(11) if fs is None else fs
    ax.text(x, v + (pad if v >= 0 else -pad), txt, ha='center', va='bottom' if v >= 0 else 'top', fontsize=fs,
            color=color)


def _delta(v, fmt='{:+.1f}', eps=0.05):
    """A difference as text; differences smaller than eps (solver noise) are shown as 0."""
    return '0' if abs(v) < eps else fmt.format(v)


def _ylim_with_labels(ax, vals, top=1.22, bottom=1.22):
    lo, hi = min(min(vals), 0.0), max(max(vals), 0.0)
    span = max(hi - lo, 1e-9)
    ax.set_ylim(lo - (bottom - 1) * span if lo < 0 else 0, hi + (top - 1) * span if hi > 0 else 0.05 * span)


def _green_cmap():
    """Sequential ramp, one hue (green, the colour of the hydrogen it shows), light to dark."""
    return LinearSegmentedColormap.from_list('green', ['#f2f8f2', '#bfe0bf', '#7cc07c', '#2f9a2f', '#006300'])


def _ink_on(rgb):
    r, g, b = to_rgb(rgb)
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return INK if lum > 0.5 else 'white'


# --------------------------------------------------------------------------
# P00 the colours of hydrogen (framing)
# --------------------------------------------------------------------------

def fig_colours():
    """Which colours of hydrogen exist (Broadleaf scheme, in van der Zwaan's lecture) and which ones the model has."""
    if ADDITIONS:       # the additions: in every run of this set (dashed frame)
        pure_row = ('Pure green', ROUTE_COLORS['Pure green (dedicated wind + solar)'],
                    'own offshore wind + solar → electrolysis', ('in the model (addition)', 'no grid connection'),
                    'water for electrolysis', True)
        pink_row = ('Pink', ROUTE_COLORS['Pink (nuclear electrolysis)'], 'own nuclear plant → electrolysis',
                    ('in the model (addition)', ''), 'water for electrolysis', True)
    else:               # not in this set (grey, like turquoise and brown)
        pure_row = ('Pure green', '#ffffff', 'own offshore wind + solar → electrolysis',
                    ('not in this set', 'in the package with additions'), 'water for electrolysis', None)
        pink_row = ('Pink', '#ffffff', 'own nuclear plant → electrolysis',
                    ('not in this set', 'in the package with additions'), 'water for electrolysis', None)
    rows = [
        ('Green', ROUTE_COLORS['Green (grid electrolysis)'], 'grid electricity → electrolysis',
         ('in the model', 'only as green as the grid (Broadleaf: yellow)'), 'water for electrolysis', False),
        pure_row,
        pink_row,
        ('Blue', ROUTE_COLORS['Blue (SMR + CCS)'], 'natural gas → SMR + CO$_2$ capture and storage',
         ('in the model', ''), 'cooling and process water', False),
        ('Grey', ROUTE_COLORS['Grey (SMR)'], 'natural gas → SMR (reformer), CO$_2$ to the air',
         ('in the model', 'incl. the reformers of 2020'), 'cooling and process water', False),
        ('Turquoise, brown', '#ffffff', 'methane pyrolysis; coal gasification', ('not in the model', ''), '', None),
    ]
    with plt.rc_context(RC()):
        fig = plt.figure(figsize=ST['size'])
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(0, 133)
        ax.set_ylim(0, 56)
        ax.axis('off')
        cols = [(2, 'Colour'), (31, 'Made from'), (79, 'In our model'), (110, 'Water use')]
        for x, h in cols:
            ax.text(x, 52.5, h, fontsize=F(11.5), fontweight='bold', color=INK, va='center')
        ax.plot([2, 131], [50.2, 50.2], color=MUTED, lw=0.8)
        for i, (name, col, made, model, water, option) in enumerate(rows):
            y = 45.4 - i * 7.4
            if option is None:
                ax.add_patch(FancyBboxPatch((2, y - 2.2), 5.4, 4.4, boxstyle='round,pad=0,rounding_size=0.8',
                                            facecolor='white', edgecolor=MUTED, lw=1.0, ls=(0, (2, 2))))
            else:
                ax.add_patch(FancyBboxPatch((2, y - 2.2), 5.4, 4.4, boxstyle='round,pad=0,rounding_size=0.8',
                                            facecolor=col, edgecolor='white', lw=1.0,
                                            hatch=ROUTE_HATCH.get('Grey (SMR)') if name == 'Grey' else None))
            c = MUTED if option is None else INK
            ax.text(9, y, name, fontsize=F(11.5), fontweight='bold', color=c, va='center')
            ax.text(31, y, made, fontsize=F(10.5), color=c, va='center')
            main, note = model
            ax.text(79, y + (1.25 if note else 0), main, fontsize=F(10.5), va='center',
                    color=c, fontweight='bold' if option else 'normal')
            if note:
                ax.text(79, y - 1.6, note, fontsize=F(8.8), va='center', color=INK2, style='italic')
            ax.text(110, y, water, fontsize=F(10.5), color=c, va='center')
            if option:
                ax.add_patch(FancyBboxPatch((0.8, y - 3.3), 130.6, 6.6, boxstyle='round,pad=0,rounding_size=1.0',
                                            facecolor='none', edgecolor=MUTED, lw=1.0, ls=(0, (3, 2))))
        ax.text(2, 0.5, 'Colour scheme: Broadleaf, as shown by van der Zwaan (2026). '
                        + ('Dashed rows = the additions, in every run of this set.' if ADDITIONS
                           else 'Grey rows: not in this set.')
                        + '\nThe water limit of the scenarios applies to every electrolyser, whatever its '
                        'electricity source.', fontsize=F(9), style='italic', color=INK2, linespacing=1.3, va='bottom')
    return fig


# --------------------------------------------------------------------------
# Implementation slide: what we added to the course model, and the parameters
# --------------------------------------------------------------------------

def fig_implementation():
    """Diagram for the 'Scenario implementation' slide: the hydrogen extension of the final course model, the water
    limit on electrolysers (the scenario) and the parameters that vary within each scenario. The package with additions
    also shows hydrogen storage, the pure green route and pink hydrogen (dashed: the additions, on in every run)."""
    tint = {'grid': ('#ddf3ea', ROUTE_COLORS['Green (grid electrolysis)']),
            'pure': ('#dcefdc', ROUTE_COLORS['Pure green (dedicated wind + solar)']),
            'pink': ('#fbe6ee', ROUTE_COLORS['Pink (nuclear electrolysis)']),
            'blue': ('#dde9f8', ROUTE_COLORS['Blue (SMR + CCS)']),
            'grey': ('#ecebe8', ROUTE_COLORS['Grey (SMR)']),
            'gas': ('#f3e9dc', CARRIER_COLORS['gas']),
            'power': ('#f4f3f0', INK2), 'demand': ('#ecebe8', INK), 'store': ('#ffffff', INK2)}
    n_runs = len(list(RUNS_DIR.glob('*.nc')))

    with plt.rc_context(RC()):
        fig = plt.figure(figsize=ST['size'])
        ax = fig.add_axes([0, 0, 1, 1])
        W, H = 115, 47.6
        ax.set_xlim(0, W)
        ax.set_ylim(0, H)
        ax.axis('off')

        def box(x, y, w, h, kind, title, sub='', dashed=False, ts=12, ss=10.5):
            fc, ec = tint[kind]
            ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0,rounding_size=0.8', facecolor=fc,
                                        edgecolor=ec, lw=1.6, ls=(0, (3, 2)) if dashed else '-', zorder=2))
            if sub:
                nl = sub.count('\n') + 1                        # lines of the subtitle (1 line = 1.7 units)
                total = 1.8 + 0.45 + 1.7 * nl
                yt = y + h / 2 + total / 2 - 0.9
                ax.text(x + w / 2, yt, title, ha='center', va='center', fontsize=ts, fontweight='bold',
                        color=INK, zorder=3)
                ax.text(x + w / 2, yt - 0.9 - 0.45 - 0.85 * nl, sub, ha='center', va='center', fontsize=ss, color=INK2,
                        zorder=3, linespacing=1.15)
            else:
                ax.text(x + w / 2, y + h / 2, title, ha='center', va='center', fontsize=ts, fontweight='bold',
                        color=INK, zorder=3, linespacing=1.15)
            return dict(l=x, r=x + w, b=y, t=y + h, cy=y + h / 2, cx=x + w / 2)

        def arrow(x0, y0, x1, y1, both=False, color=INK2):
            ax.annotate('', xy=(x1, y1), xytext=(x0, y0), zorder=1,
                        arrowprops=dict(arrowstyle='<|-|>' if both else '-|>', color=color, lw=1.3, mutation_scale=11,
                                        shrinkA=0, shrinkB=0))

        # technologies (middle column), bottom to top
        TX, TW = 24.5, 30.0
        if ADDITIONS:
            TH, GAP, Y0 = 5.6, 1.4, 3.4
            ys = [Y0 + i * (TH + GAP) for i in range(5)]
            smr = box(TX, ys[0], TW, TH, 'grey', 'SMR (grey)', 'CO$_2$ to the air, at the CO$_2$ price')
            ccs = box(TX, ys[1], TW, TH, 'blue', 'SMR + CCS (blue)', '90% of CO$_2$ to capped storage')
            pink = box(TX, ys[2], TW, TH, 'pink', 'Electrolyser: pink', 'addition: own nuclear plant', dashed=True)
            pure = box(TX, ys[3], TW, TH, 'pure', 'Electrolyser: pure green', 'addition: own wind + solar, no grid',
                       dashed=True)
            grid = box(TX, ys[4], TW, TH, 'grid', 'Electrolyser (green)', 'grid electricity')
            electrolysers = [pink, pure, grid]
        else:
            smr = box(TX, 3.4, TW, 7.0, 'grey', 'SMR (grey)', 'CO$_2$ to the air, at the CO$_2$ price')
            ccs = box(TX, 13.0, TW, 7.0, 'blue', 'SMR + CCS (blue)', '90% of CO$_2$ to capped storage')
            grid = box(TX, 29.5, TW, 7.5, 'grid', 'Electrolyser (green)', 'grid electricity')
            electrolysers = [grid]
            ax.text(TX + TW / 2, 24.3, 'gas routes: no water limit', ha='center', va='center', fontsize=F(10),
                    color=INK2, style='italic')
        # the water limit: a frame around every electrolyser
        fx0, fx1, fy0, fy1 = TX - 1.6, TX + TW + 1.6, electrolysers[0]['b'] - 0.7, H - 0.8
        ax.add_patch(FancyBboxPatch((fx0, fy0), fx1 - fx0, fy1 - fy0, boxstyle='round,pad=0,rounding_size=1.0',
                                    facecolor='none', edgecolor=INK, lw=1.4, ls=(0, (7, 2, 1.5, 2)), zorder=1))
        ax.text((fx0 + fx1) / 2, fy1 - 1.6, 'Water limit = the scenario (1)', ha='center', va='center', fontsize=F(11.5),
                fontweight='bold', color=INK)
        ax.text((fx0 + fx1) / 2, fy1 - 3.9, 'all electrolysers, share of Base without additions:' if ADDITIONS
                else 'electrolyser capacity, share of Base:', ha='center', va='center', fontsize=F(9.8), color=INK2)
        for (lab, col), xx in zip([('Base 100%', SCEN_COLORS['S1']), ('Medium 50%', SCEN_COLORS['S2']),
                                   ('Scarce 0%', SCEN_COLORS['S3'])], [fx0 + 1.3, fx0 + 11.8, fx0 + 22.6]):
            ax.add_patch(Rectangle((xx, fy1 - 7.0), 1.3, 1.3, color=col, zorder=3))
            ax.text(xx + 1.8, fy1 - 6.35, lab, ha='left', va='center', fontsize=F(9.6), color=INK, fontweight='bold')
        # sources (left column)
        SX, SW = 0.6, 19.0
        powr = box(SX, grid['b'], SW, fy1 - 8.5 - grid['b'] + 1.4, 'power', 'Power system',
                   'course model: wind,\nsolar, gas, nuclear,\nbiomass, batteries')
        gas = box(SX, smr['b'], SW, ccs['t'] - smr['b'], 'gas', 'Natural gas', 'imports, TTF price path')
        arrow(powr['r'], grid['cy'], grid['l'], grid['cy'])
        if ADDITIONS:
            own_res = box(SX, pure['b'], SW, TH, 'pure', 'Own wind + solar', 'addition', dashed=True)
            own_nuc = box(SX, pink['b'], SW, TH, 'pink', 'Own nuclear plant', 'addition', dashed=True)
            arrow(own_res['r'], pure['cy'], pure['l'], pure['cy'])
            arrow(own_nuc['r'], pink['cy'], pink['l'], pink['cy'])
        xg = gas['r'] + 2.5
        ax.plot([gas['r'], xg], [gas['cy'], gas['cy']], color=INK2, lw=1.3, zorder=1)
        ax.plot([xg, xg], [smr['cy'], ccs['cy']], color=INK2, lw=1.3, zorder=1)
        arrow(xg, smr['cy'], smr['l'], smr['cy'])
        arrow(xg, ccs['cy'], ccs['l'], ccs['cy'])
        # the hydrogen demand (right of the technologies)
        DX, DW = 62.0, 17.0
        dy0 = 14.0 if ADDITIONS else 8.0
        dem = box(DX, dy0, DW, grid['t'] - dy0, 'demand', 'Hydrogen\ndemand', '', ts=13)
        ax.text(dem['cx'], dem['cy'] - 5.6, '1.3 Mt/yr (43 TWh)\nrefineries, ammonia\nfixed, flat profile',
                ha='center', va='center', fontsize=F(10.5), color=INK2, linespacing=1.3, zorder=3)
        xc = fx1 + 3.0
        for b in [smr, ccs] + electrolysers:
            ax.plot([b['r'], xc], [b['cy'], b['cy']], color=INK2, lw=1.3, zorder=1)
        ax.plot([xc, xc], [smr['cy'], grid['cy']], color=INK2, lw=1.3, zorder=1)
        arrow(xc, dem['cy'], dem['l'], dem['cy'])
        if ADDITIONS:
            sto = box(DX, smr['b'], DW, ccs['t'] - smr['b'] - 5.0, 'store', 'H$_2$ storage', 'addition: salt caverns',
                      dashed=True)
            arrow(sto['cx'], sto['t'], sto['cx'], dem['b'], both=True)
        # the parameters within each scenario (right column)
        PX, PW = 83.0, 31.0
        ax.add_patch(FancyBboxPatch((PX, smr['b']), PW, fy1 - smr['b'], boxstyle='round,pad=0,rounding_size=0.8',
                                    facecolor='#f7f7f5', edgecolor='none', zorder=0))
        ax.text(PX + 1.5, fy1 - 2.0, 'Within each scenario', ha='left', va='center', fontsize=F(12.5),
                fontweight='bold', color=INK)
        rows = [('2a', 'Electrolyser cost', 'subsidy 20% or 40%; low CAPEX'),
                ('2b', 'CO$_2$ price in 2050', 'low 170, central 250, high 500 €/t')]
        if ADDITIONS:
            rows.append(('2c', 'H$_2$ storage cost', 'three times the cost'))
        rows += [('3a-c', 'Batteries', 'half the price; 8 h instead of 4 h'),
                 ('+', 'Green levers', 'desalinated water; €1-2/kg; mandate')]
        step = 6.9 if len(rows) > 4 else 7.6
        for i, (code, t1, t2) in enumerate(rows):
            y = fy1 - 7.6 - i * step
            ax.text(PX + 1.5, y, code, ha='left', va='center', fontsize=F(11.5), fontweight='bold', color=INK2)
            ax.text(PX + 7.0, y + 1.0, t1, ha='left', va='center', fontsize=F(11.5), fontweight='bold', color=INK)
            ax.text(PX + 7.0, y - 1.5, t2, ha='left', va='center', fontsize=F(10.5), color=INK2)
        foot = (f'Dashed = addition, in every run.\nDutch data, 2024 euros. {n_runs} runs.' if ADDITIONS
                else f'Dutch data, 2024 euros. {n_runs} runs.')
        ax.text(PX + 1.5, smr['b'] + 3.2, foot, ha='left', va='center', fontsize=F(10.5), color=INK2, style='italic',
                linespacing=1.3)
    return fig


# --------------------------------------------------------------------------
# P01 hydrogen by route per scenario and period
# --------------------------------------------------------------------------

def fig_routes(R=None, periods=(2030, 2040, 2050)):
    R = R or scenarios()
    with plt.rc_context(RC()):
        fig, axes = plt.subplots(1, len(R), figsize=ST['size'], sharey=True)
        used = set()
        top = 0
        for ax, (label, n) in zip(axes, R.items()):
            bal = h2_balance(n).loc[list(periods)]
            x = np.arange(len(bal))
            bottom = np.zeros(len(x))
            for route, col in ROUTE_COLORS.items():
                v = bal[route].clip(lower=0).values
                if v.max() <= 1e-3:
                    continue
                ax.bar(x, v, bottom=bottom, width=0.66, color=col, edgecolor='white', linewidth=1.5,
                       hatch=ROUTE_HATCH.get(route))
                used.add(route)
                bottom += v
            ely = bal[ELECTROLYSIS_ROUTES].sum(axis=1).values
            for i in range(len(x)):
                share = max(100 * ely[i] / bottom[i], 0.0) if bottom[i] > 0 else 0.0
                ax.text(x[i], bottom[i] + 0.8, f'{share:.0f}%', ha='center', va='bottom', fontsize=F(12),
                        fontweight='bold', color=INK)
            top = max(top, bottom.max())
            ax.set_xticks(x, [str(p) for p in periods])
            ax.set_title(label if apa() else SCEN_TITLE.get(label, label), fontsize=F(12.5))
            _style(ax)
        axes[0].set_ylabel('TWh H$_2$ per year')
        axes[0].set_ylim(0, top * 1.14)
        handles = [Patch(facecolor=ROUTE_COLORS[r], hatch=ROUTE_HATCH.get(r), edgecolor='white', label=r)
                   for r in ROUTE_COLORS if r in used]
        fig.legend(handles=handles, loc='lower center', ncol=len(handles), frameon=False, bbox_to_anchor=(0.5, 0.0),
                   fontsize=F(10.5))
        note(fig, 0.01, 0.94, 'Hydrogen supply by route (1.3 Mt/yr = 43 TWh in every scenario); '
                             'percentage = share made by electrolysis', fontsize=F(11), color=INK2)
        fig.tight_layout(rect=_rect(0, 0.08, 1, 0.93))
    return fig


# --------------------------------------------------------------------------
# P02 Sankey of the hydrogen system per scenario
# --------------------------------------------------------------------------

def fig_sankey(R=None, period=2050):
    R = R or scenarios()
    if apa():      # the report: the three panels under each other, on one scale
        from .h2_sankey import plot_sankeys
        return plot_sankeys(R, period, note=False, width=6.5, fs=1.28, fit=True,
                            titles={k: f'{SCEN_TITLE.get(k, k)} (TWh per year, {period})' for k in R})
    return plot_sankeys_row(R, period, figsize=ST['size'], fs=1.45,
                            titles={k: SCEN_TITLE.get(k, k) for k in R})


def save_sankey_decades(R=None, periods=(2020, 2030, 2040, 2050), out=None, duration=1400):
    """Save one presentation Sankey PNG per model period and a looping GIF of the frames.

    The model's final representative period is stored as 2050 and covers the
    model horizon through 2060; it remains named 2050 to match the existing
    result files.
    """
    from PIL import Image

    R = R or scenarios()
    if R is None:
        return []
    out = Path(out or OUT_DIR)
    out.mkdir(parents=True, exist_ok=True)
    frames = []
    stems = []
    for period in periods:
        fig = fig_sankey(R, period=period)
        stem = f'P02_h2_sankey_{period}'
        path = out / f'{stem}.png'
        save(fig, stem, out=out)
        frames.append(Image.open(path).convert('P'))
        stems.append(stem)
    animation = out / 'P02_h2_sankey_decades.gif'
    frames[0].save(animation, save_all=True, append_images=frames[1:],
                   duration=duration, loop=0, optimize=False)
    for frame in frames:
        frame.close()
    return [*stems, animation.stem]


# --------------------------------------------------------------------------
# P03 what water scarcity costs
# --------------------------------------------------------------------------

def scarcity_numbers(R=None, ref='Base'):
    """Differences with the Base run over 2020-2059: system cost (bn €, discounted), CO2 (Mt), gas imports (TWh),
    and the cost per kg of green hydrogen that is lost (€/kg, discounted)."""
    R = R or scenarios()
    b = R[ref]
    rows = {}
    for k, n in R.items():
        if k == ref:
            continue
        rows[k] = {
            'Extra system cost (bn €)': _econ_cost(n) - _econ_cost(b),
            'Extra CO2 (Mt)': cumulative_co2(n) - cumulative_co2(b),
            'Extra gas imports (TWh)': _horizon(n, gas_use(n)['Gas use, total (TWh/yr)'])
            - _horizon(b, gas_use(b)['Gas use, total (TWh/yr)']),
            'Cost per kg of green H2 lost (€/kg)': limit_cost(n, b),
        }
    return pd.DataFrame(rows)


def fig_cost(R=None, ref='Base'):
    R = R or scenarios()
    d = scarcity_numbers(R, ref)
    panels = [('Extra system cost (bn €)', 'Extra system cost\n2020-2059, bn € (discounted)', '+{:.1f}'),
              ('Extra CO2 (Mt)', 'Extra CO$_2$ emissions\n2020-2059, Mt', '+{:.0f}'),
              ('Extra gas imports (TWh)', 'Extra natural gas imports\n2020-2059, TWh', '+{:.0f}'),
              ('Cost per kg of green H2 lost (€/kg)', 'Cost per kg of green\nhydrogen lost, €/kg', '{:.2f}')]
    with plt.rc_context(RC()):
        fig, axes = _row_axes(4)
        names = list(d.columns)
        x = np.arange(len(names))
        for ax, (row, title, fmt) in zip(axes, panels):
            v = d.loc[row].astype(float).values
            ax.bar(x, np.nan_to_num(v), width=0.58, color=[scen_color(k) for k in names], edgecolor='white')
            for i, vi in enumerate(v):
                _label(ax, x[i], 0 if np.isnan(vi) else vi, 'n/a' if np.isnan(vi) else fmt.format(vi), fs=F(13))
            ax.axhline(0, color=MUTED, lw=0.8)
            ax.set_xticks(x, names)
            ax.set_title(title, fontsize=F(12.5))
            _ylim_with_labels(ax, np.nan_to_num(v))
            _style(ax)
        note(fig, 0.01, 0.95, f'What water scarcity costs, compared with {ref} (no water scarcity)', fontsize=F(11),
                 color=INK2)
        note(fig, 0.01, 0.015, 'System cost: the model objective (years discounted at 1%, the social rate of the course '
                              'model; investments as annuities at 7%). Cost per kg: extra system cost / discounted '
                              'green hydrogen not made.', fontsize=F(9.5), style='italic', color=INK2)
        fig.tight_layout(rect=_rect(0, 0.04, 1, 0.94))
    return fig


# --------------------------------------------------------------------------
# P04 the policy story
# --------------------------------------------------------------------------

def fig_story(R=None, period=2050):
    """What else changes when water limits electrolysis (Francesco, 14 Oct): gas, electricity generation, electrolysers.
    (The system cost is on P03.)"""
    from .h2_plots import POWER_STACK, _POWER_GROUPS
    from .h2_results import electricity_mix
    R = R or scenarios()
    names = list(R)
    x = np.arange(len(names))
    with plt.rc_context(RC()):
        if apa():           # 2 x 2: the fourth cell holds the legends
            fig, all_axes = _row_axes(4)
            axes, leg_ax = all_axes[:3], all_axes[3]
            leg_ax.axis('off')
        else:
            fig, axes = plt.subplots(1, 3, figsize=ST['size'])
            leg_ax = None
        # (a) natural gas: for hydrogen and for everything else
        g = {k: gas_use(R[k]).loc[period] for k in names}
        h2 = np.array([g[k]['Gas for H2 (TWh/yr)'] for k in names])
        tot = np.array([g[k]['Gas use, total (TWh/yr)'] for k in names])
        ax = axes[0]
        ax.bar(x, tot - h2, width=0.6, color='#d8c3a5', edgecolor='white', linewidth=1.5, label='other uses')
        ax.bar(x, h2, bottom=tot - h2, width=0.6, color=CARRIER_COLORS['gas'], edgecolor='white', linewidth=1.5,
               label='for hydrogen')
        for i in range(len(x)):
            ax.text(x[i], tot[i] + 3, f'{tot[i]:.0f}', ha='center', va='bottom', fontsize=F(11.5), color=INK)
            ax.text(x[i], tot[i] - h2[i] / 2, f'{h2[i]:.0f}', ha='center', va='center', fontsize=F(10.5), color='white')
        ax.set_ylim(0, tot.max() * 1.15)
        ax.set_ylabel('TWh per year')
        ax.set_title(f'Natural gas used, {period}', fontsize=F(12))
        h_gas, l_gas = ax.get_legend_handles_labels()
        if leg_ax is None:
            ax.legend(h_gas[::-1], l_gas[::-1], loc='upper left', fontsize=F(10), ncol=2, bbox_to_anchor=(0, 1.0))
        ax.set_ylim(0, tot.max() * 1.3)
        # (b) electricity generation by source
        mix = {k: electricity_mix(R[k]).loc[period] for k in names}
        ax = axes[1]
        bottom = np.zeros(len(names))
        for src, col in POWER_STACK.items():
            v = np.array([sum(mix[k].get(s_, 0.0) for s_ in _POWER_GROUPS[src]) for k in names])
            if v.max() <= 0.05:
                continue
            ax.bar(x, v, width=0.6, bottom=bottom, color=col, edgecolor='white', linewidth=1.5, label=src)
            bottom += v
        for i in range(len(names)):
            ax.text(x[i], bottom[i] + 2, f'{bottom[i]:.0f}', ha='center', va='bottom', fontsize=F(11.5), color=INK)
        ax.set_ylim(0, bottom.max() * 1.3)
        ax.set_ylabel('TWh per year')
        ax.set_title(f'Electricity generation, {period}', fontsize=F(12))
        h, l = ax.get_legend_handles_labels()
        if leg_ax is None:
            ax.legend(h[::-1], l[::-1], fontsize=F(10), loc='upper right', ncol=2)
        else:
            leg1 = leg_ax.legend([hh for hh in h_gas[::-1]], [ll for ll in l_gas[::-1]],
                                 loc='upper left', title='Natural gas used', fontsize=F(10), title_fontsize=F(10),
                                 alignment='left')
            leg_ax.add_artist(leg1)
            leg_ax.legend(h[::-1], l[::-1], loc='lower left', title='Electricity generation', fontsize=F(10),
                          title_fontsize=F(10), ncol=2, alignment='left')
        # (c) electrolysers: capacity and investment
        s = {k: summary(R[k]).loc[period] for k in names}
        cap = [s[k]['Electrolyser capacity (GW_el)'] for k in names]
        inv = [float(electrolyser_investment(R[k]).sum()) for k in names]
        ax = axes[2]
        ax.bar(x, cap, width=0.6, color=ROUTE_COLORS['Green (grid electrolysis)'], edgecolor='white')
        for i in range(len(names)):
            ax.text(x[i], cap[i] + 0.15, f'{cap[i]:.1f} GW\n€{inv[i]:.1f} bn', ha='center', va='bottom',
                    fontsize=F(10.5), color=INK, linespacing=1.15)
        ax.set_ylim(0, max(max(cap), 0.1) * 1.35)
        ax.set_ylabel('GW of electricity input')
        ax.set_title(f'Electrolysers, {period}', fontsize=F(12))
        for ax in axes:
            ax.set_xticks(x, names)
            _style(ax)
        note(fig, 0.01, 0.95, 'What else changes when water limits electrolysis: more gas, less wind and solar, '
                             'fewer electrolysers (investment = overnight, 2020-2059)', fontsize=F(10.5), color=INK2)
        fig.tight_layout(rect=_rect(0, 0, 1, 0.94))
    return fig


# --------------------------------------------------------------------------
# P05 (2a) electrolyser and infrastructure subsidies, and low CAPEX
# --------------------------------------------------------------------------

def subsidy_table(scens=('Base', 'Medium'),
                  variants=('', '_sub20', '_sub40', '_infra20', '_infra40', '_capexlow'), period=2050):
    rows = []
    for sc in scens:
        base = run(SCEN[sc])
        if base is None:
            return None
        for v in variants:
            n = run(SCEN[sc] + v)
            if n is None:
                return None
            s = summary(n).loc[period]
            sub_over, sub_pv = subsidy_cost(n)
            rows.append({'scenario': sc, 'variant': VARIANT_NAMES[v],
                         'Electrolysers (GW_el)': s['Electrolyser capacity (GW_el)'],
                         'Electrolysis share (%)': s['Electrolysis share (%)'],
                         'Subsidy (bn €, overnight)': sub_over,
                         'Extra system cost (bn €)': _econ_cost(n) - _econ_cost(base),
                         'CO2 avoided (Mt)': cumulative_co2(base) - cumulative_co2(n)})
    return pd.DataFrame(rows)


def _water_value(n, year='2050'):
    """Value of 1 kW more electrolyser (hydrogen output) where water limits it, present value (€/kW): the duals of the
    joint limit and of the electrolyser's own limit (a run stores one or both). None if not stored."""
    if n is None:
        return None
    sp = (n.meta or {}).get('electrolyser_cap_shadow_price_eur_per_kw_h2') or {}
    if not sp:
        return None
    tot = float((sp.get('total') or {}).get(year, 0.0) or 0.0)
    own = max([float((v or {}).get(year, 0.0) or 0.0) for k, v in sp.items() if k != 'total'] or [0.0])
    return tot + own


def fig_subsidy():
    df = subsidy_table()
    if df is None:
        return None
    metrics = [('Electrolysers (GW_el)', 'Electrolysers 2050\nGW of electricity input', '{:.1f}'),
               ('Subsidy (bn €, overnight)', 'Public subsidy\nbn € (overnight)', '{:.1f}'),
               ('Extra system cost (bn €)', 'System cost vs central\nbn € (incl. subsidy)', '{:+.1f}')]
    variants = list(dict.fromkeys(df.variant))
    shades = ['#8a8984', '#b3a9ee', '#6250d6', '#8bcf9a', '#2f9a4a', '#2f2470']
    with plt.rc_context(RC()):
        fig, all_axes = _row_axes(4, [1, 1, 1, 0.95])
        axes, text_ax = all_axes[:3], all_axes[3]
        scs = list(dict.fromkeys(df.scenario))
        w = 0.8 / len(variants)
        for ax, (m, title, fmt) in zip(axes, metrics):
            allv = []
            for j, var in enumerate(variants):
                for i, sc in enumerate(scs):
                    v = float(df[(df.scenario == sc) & (df.variant == var)][m].iloc[0])
                    v = 0.0 if abs(v) < 1e-3 else v
                    allv.append(v)
                    xx = i + (j - (len(variants) - 1) / 2) * w
                    ax.bar(xx, v, width=w * 0.92, color=shades[j % len(shades)], edgecolor='white',
                           label=var if i == 0 else None)
                    txt = '0' if v == 0 else fmt.format(v)
                    ax.text(xx, v, txt, ha='center', va='bottom' if v >= 0 else 'top', fontsize=F(8.5), color=INK)
            ax.axhline(0, color=MUTED, lw=0.8)
            ax.set_xticks(range(len(scs)), scs)
            ax.set_title(title, fontsize=F(11.5))
            lo, hi = min(min(allv), 0.0), max(max(allv), 0.0)
            span = max(hi - lo, 1.0)
            ax.set_ylim(lo - (0.15 * span if lo < 0 else 0.0), hi + 0.15 * span)
            _style(ax)
        # what the variations change: a text panel, from the numbers
        ax = text_ax
        ax.axis('off')
        lines = [('Electrolysis share, 2050:', True)]
        unchanged = True
        for sc in scs:
            sh = df[df.scenario == sc]['Electrolysis share (%)'].astype(float)
            gw = df[df.scenario == sc]['Electrolysers (GW_el)'].astype(float)
            c = float(sh.iloc[0])
            if sh.max() - sh.min() < 0.5 and gw.max() - gw.min() < 0.05:
                lines.append((f'{sc}: {c:.0f}% in every run', False))
            else:
                unchanged = False
                lines.append((f'{sc}: {c:.0f}% → {sh.iloc[1:].min():.0f}-{sh.iloc[1:].max():.0f}%', False))
        lines.append(('', False))
        if unchanged:
            lines += [('No change in hydrogen, gas or CO$_2$:', False), ('a subsidy moves money; the low', False),
                      ('CAPEX path only lowers the cost.', False)]
        else:
            lines += [('A subsidy is a transfer: the', False), ('system cost counts it back in.', False)]
        lines += [('', False), ('Value of 1 kW more electrolyser', True), ('in Medium (€/kW of H$_2$, present value):', False)]
        y = 0.97
        for t, bold in lines:
            ax.text(0.0, y, t, fontsize=F(10.5), color=INK if bold else INK2, fontweight='bold' if bold else 'normal',
                    transform=ax.transAxes, va='top')
            y -= 0.075 if apa() else 0.062
        sp = []
        for var_code, var in [('', 'central'), ('_sub20', 'subsidy 20%'), ('_sub40', 'subsidy 40%'),
                              ('_infra20', 'infrastructure subsidy 20%'), ('_infra40', 'infrastructure subsidy 40%'),
                              ('_capexlow', 'low CAPEX')]:
            v = _water_value(run('S2' + var_code))
            sp.append(f'{var} {v:,.0f}' if v is not None else f'{var} n/a')
        for t in sp:
            ax.text(0.04, y, t, fontsize=F(10.5), color=INK, transform=ax.transAxes, va='top')
            y -= 0.075 if apa() else 0.062
        h, l = axes[0].get_legend_handles_labels()
        fig.legend(h, l, loc='lower center', ncol=len(variants), frameon=False)
        note(fig, 0.01, 0.95, '(2a) Electrolyser and infrastructure subsidies, or the low CAPEX path',
                 fontsize=F(11), color=INK2)
        fig.tight_layout(rect=_rect(0, 0.08, 1, 0.94))
    return fig


# --------------------------------------------------------------------------
# P06 (2b) the CO2 price
# --------------------------------------------------------------------------

def fig_co2price(period=2050):
    variants = {'low': '_co2low', 'central': '', 'high': '_co2high'}
    data = {}
    for sc in SCEN:
        d = {}
        for lev, v in variants.items():
            n = run(SCEN[sc] + v)
            if n is None:
                return None
            d[CO2_PRICES[lev][period]] = n
        data[sc] = d
    with plt.rc_context(RC()):
        fig, axes = _row_axes(4, [1, 1, 1, 1.15])
        used = set()
        ymax = 0
        for ax, (sc, d) in zip(axes[:3], data.items()):
            prices = sorted(d)
            bal = pd.DataFrame({p: h2_balance(d[p]).loc[period] for p in prices}).T
            for route, col in ROUTE_COLORS.items():
                if bal[route].abs().max() <= 1e-2:
                    continue
                used.add(route)
                ax.plot(prices, bal[route], '-', color=col, lw=2.4, marker='o', ms=8,
                        markeredgecolor='white', markeredgewidth=1.5)
                ymax = max(ymax, bal[route].max())
            ax.set_title(SCEN_TITLE[sc].split(':')[0], fontsize=F(12.5))
            ax.set_xticks(prices, [f'{p:.0f}' for p in prices])
            ax.set_xlabel(f'CO$_2$ price {period} (€/t)')
            _style(ax)
        for ax in axes[:3]:
            ax.set_ylim(0, ymax * 1.1)
        axes[0].set_ylabel(f'TWh H$_2$ per year, {period}')
        if apa():
            axes[2].set_ylabel(f'TWh H$_2$ per year, {period}')
        ax = axes[3]
        for sc, d in data.items():
            prices = sorted(d)
            co2 = [cumulative_co2(d[p]) for p in prices]
            ax.plot(prices, co2, '-', color=scen_color(sc), lw=2.4, marker='o', ms=8, markeredgecolor='white',
                    markeredgewidth=1.5, label=sc)
            ax.text(prices[-1] + 12, co2[-1], sc, va='center', fontsize=F(11), color=INK)
        ax.set_xticks(sorted(data['Base']), [f'{p:.0f}' for p in sorted(data['Base'])])
        ax.set_xlabel(f'CO$_2$ price {period} (€/t)')
        ax.set_ylabel('CO$_2$ 2020-2059 (Mt), all sectors')
        ax.set_title('CO$_2$ emissions', fontsize=F(12.5))
        ax.set_xlim(right=max(sorted(data['Base'])) * 1.22)
        _style(ax)
        handles = [plt.Line2D([], [], color=ROUTE_COLORS[r], lw=2.4, marker='o', ms=8, markeredgecolor='white',
                              label=r) for r in ROUTE_COLORS if r in used]
        fig.legend(handles=handles, loc='lower center', ncol=len(handles), frameon=False)
        note(fig, 0.01, 0.95, '(2b) Hydrogen by route and CO$_2$ against the CO$_2$ price path '
                             '(low / central / high: 170 / 250 / 500 €/t in 2050)', fontsize=F(11), color=INK2)
        fig.tight_layout(rect=_rect(0, 0.08, 1, 0.94))
    return fig


# --------------------------------------------------------------------------
# P07 the options in every scenario: heat table
# --------------------------------------------------------------------------

def heat_table(ax, values, texts, rows, cols, cmap, vmin, vmax, fs=None, empty='not run'):
    """Coloured cells (values; NaN = grey 'not run') with text; rows top to bottom."""
    fs = F(11.5) if fs is None else fs
    ax.set_xlim(0, len(cols))
    ax.set_ylim(0, len(rows))
    ax.invert_yaxis()
    norm = matplotlib.colors.Normalize(vmin, vmax)
    for i in range(len(rows)):
        for j in range(len(cols)):
            v = values[i][j]
            if v is None or (isinstance(v, float) and np.isnan(v)):
                ax.add_patch(Rectangle((j, i), 1, 1, facecolor='#f4f3f0', edgecolor='white', lw=2))
                ax.text(j + 0.5, i + 0.5, texts[i][j] or empty, ha='center', va='center',
                        fontsize=max(fs * 0.87, ST.get('min_pt', 0.0)), color=MUTED, style='italic')
                continue
            fc = cmap(norm(v))
            ax.add_patch(Rectangle((j, i), 1, 1, facecolor=fc, edgecolor='white', lw=2))
            ax.text(j + 0.5, i + 0.5, texts[i][j], ha='center', va='center', fontsize=fs, color=_ink_on(fc),
                    linespacing=1.25)
    ax.set_xticks(np.arange(len(cols)) + 0.5, cols)
    ax.xaxis.tick_top()
    ax.set_yticks(np.arange(len(rows)) + 0.5, rows)
    ax.tick_params(length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)


def _cell(scen, variant, period=2050, ref_variant=''):
    """(electrolysis share %, text) of one run, with the cost difference against the same scenario's central run."""
    n = run(SCEN[scen] + variant)
    if n is None:
        return np.nan, ''
    s = summary(n).loc[period]
    share = float(np.nan_to_num(s['Electrolysis share (%)']))
    ref = run(SCEN[scen] + ref_variant)
    txt = f'{share:.0f}%'
    if variant != ref_variant and ref is not None:
        dc = _econ_cost(n) - _econ_cost(ref)
        txt += f'\n{dc:+.1f} bn €' if abs(dc) >= 0.05 else '\n±0.0 bn €'
    return share, txt


ADDITION_ROWS = ['_noadd', '_storage', '_green', '_pink', '', '_storage_x3', '_green_only']


def fig_options(period=2050):
    """Package with additions: what the additions do in every scenario (heat table). One cell = one run: the share of
    hydrogen made by electrolysis in 2050, and the system cost against the same scenario without additions."""
    if not ADDITIONS:
        return None
    if any(run(SCEN[sc] + o) is None for sc in SCEN for o in ['', '_noadd']):
        return None
    opts = [o for o in ADDITION_ROWS if any(run(SCEN[sc] + o) is not None for sc in SCEN)]
    vals, txts = [], []
    for o in opts:
        rv, rt = [], []
        for sc in SCEN:
            v, t = _cell(sc, o, period, ref_variant='_noadd')
            rv.append(v)
            rt.append(t)
        vals.append(rv)
        txts.append(rt)
    labels = {'': 'all additions (central)', '_noadd': 'without additions'}
    with plt.rc_context(RC()):
        fig = plt.figure(figsize=(6.5, 3.9) if apa() else ST['size'])
        ax = fig.add_axes([0.33, 0.02, 0.66, 0.90] if apa() else [0.27, 0.06, 0.46, 0.79])
        heat_table(ax, vals, txts, [labels.get(o, VARIANT_NAMES[o]) for o in opts], list(SCEN), _green_cmap(), 0, 100,
                   fs=F(10.5) if not apa() else None)
        note(fig, 0.01, 0.95, f'What the additions do: share of hydrogen made by electrolysis in {period} (colour) and '
                             'the system cost against the same scenario without additions', fontsize=F(11), color=INK2)
        tx = 0.755
        notes = ['How to read: one cell = one model run.',
                 'Top line: electrolysis share (grid, pure',
                 'green and pink) of the hydrogen in 2050.',
                 'Bottom line: system cost 2020-2059',
                 '(discounted) minus the same scenario',
                 'without additions (negative = cheaper).',
                 '',
                 'The water limit stays the same in MW',
                 '(Medium: 3.5 GW for all electrolysers',
                 'together; Scarce: none).']
        for i, t in enumerate(notes):
            note(fig, tx, 0.80 - i * 0.055, t, fontsize=F(10.5), color=INK2)
    return fig


# --------------------------------------------------------------------------
# P08 (2c) hydrogen storage
# --------------------------------------------------------------------------

def _store_level(n, period):
    st = [s for s in n.stores.index if n.stores.at[s, 'carrier'] in H2_STORAGE]
    if not st:
        return None
    sl = n.snapshots.get_level_values(0) == period
    e = ts(n, 'stores', 'e').loc[sl, st].sum(axis=1) / 1e6
    return pd.Series(e.values, index=n.snapshots[sl].get_level_values(1))


def fig_storage(period=2050):
    """(2c) Package with additions: hydrogen storage built (central and at 3x the cost), what the additions are
    worth (system cost with additions minus without) and the storage level over the year."""
    if not ADDITIONS:
        return None
    R = scenarios()
    C = runs({k: v + '_noadd' for k, v in SCEN.items()})
    if R is None or C is None:
        return None
    x3 = {k: run(SCEN[k] + '_storage_x3') for k in ('Base', 'Medium')}
    with plt.rc_context(RC()):
        if apa():           # two bar panels on top, the storage level over the year below (full width)
            fig = plt.figure(figsize=ST['tall'])
            gs = fig.add_gridspec(2, 2, height_ratios=[1, 0.9])
            a1, a2, a3 = fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1]), fig.add_subplot(gs[1, :])
        else:
            fig = plt.figure(figsize=ST['size'])
            gs = fig.add_gridspec(1, 3, width_ratios=[1, 1, 2.1])
            a1, a2, a3 = fig.add_subplot(gs[0]), fig.add_subplot(gs[1]), fig.add_subplot(gs[2])
        labels = list(R)
        x = np.arange(len(labels))
        cap = [summary(R[k]).loc[period, 'H2 storage (GWh)'] / 1e3 for k in labels]
        a1.bar(x, cap, width=0.6, color=[scen_color(k) for k in labels], edgecolor='white')
        for i, k in enumerate(labels):
            _label(a1, x[i], cap[i], f'{cap[i]:.2f}', fs=F(12))
            if x3.get(k) is not None:
                c3 = summary(x3[k]).loc[period, 'H2 storage (GWh)'] / 1e3
                if c3 > 0.01:           # nothing built at 3x the cost: no marker over the '0.00' label
                    a1.plot([x[i] - 0.3, x[i] + 0.3], [c3, c3], color=INK, lw=2, ls=(0, (2, 1.5)))
        a1.plot([], [], color=INK, lw=2, ls=(0, (2, 1.5)), label='at 3x the cost')
        a1.legend(loc='upper right', fontsize=F(10))
        a1.set_xticks(x, labels)
        a1.set_ylabel('TWh of H$_2$')
        a1.set_title(f'Storage built, {period}', fontsize=F(12.5))
        _ylim_with_labels(a1, cap + [5.0])
        a1.axhline(5.0, color=MUTED, lw=1, ls=(0, (4, 2)))
        a1.text(len(labels) - 0.5, 5.0, 'cap 5 TWh', ha='right', va='bottom', fontsize=F(10), color=INK2)
        _style(a1)
        d = [_econ_cost(R[k]) - _econ_cost(C[k]) for k in labels]
        a2.bar(x, d, width=0.6, color=[scen_color(k) for k in labels], edgecolor='white')
        for i in range(len(labels)):
            _label(a2, x[i], 0.0 if abs(d[i]) < 0.05 else d[i], _delta(d[i]), fs=F(12))
        a2.axhline(0, color=MUTED, lw=0.8)
        a2.set_xticks(x, labels)
        a2.set_ylabel('bn €, discounted 2020-2059')
        a2.set_title('System cost with additions\nminus without', fontsize=F(12.5))
        _ylim_with_labels(a2, d)
        _style(a2)
        for k in labels:
            lev = _store_level(R[k], period)
            if lev is not None and lev.max() > 1e-3:
                a3.plot(lev.index, lev.values, color=scen_color(k), lw=2, label=k)
        a3.set_ylabel('TWh of H$_2$ in storage')
        a3.set_title(f'Storage level over {period}', fontsize=F(12.5))
        a3.legend(loc='upper left', fontsize=F(10.5), ncol=3)
        a3.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%b'))
        a3.set_ylim(bottom=0)
        _style(a3)
        built = [k for k in labels if cap[labels.index(k)] > 0.01]
        note(fig, 0.01, 0.95, '(2c) Hydrogen storage (an addition) is built in ' + (' and '.join(built) or 'no scenario')
             + ': it lets the electrolysers be larger than the flat demand' + (
                 '. Under a water limit it is not used' if built == ['Base'] else ''), fontsize=F(11), color=INK2)
        fig.tight_layout(rect=_rect(0, 0, 1, 0.94))
    return fig


# --------------------------------------------------------------------------
# P09 (3a-c) batteries
# --------------------------------------------------------------------------

def fig_battery(period=2050):
    names = {'Medium': 'S2', 'Medium, half-price batteries': 'S2_battery_cheap', 'Medium, 8 h batteries': 'S2_battery_8h'}
    R = runs(names)
    C = scenarios()
    if R is None or C is None:
        return None
    with plt.rc_context(RC()):
        if apa():           # two bar panels on top, the state of charge below (full width)
            fig = plt.figure(figsize=ST['tall'])
            gs = fig.add_gridspec(2, 2, height_ratios=[1, 0.9])
            a1, a2, a3 = fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1]), fig.add_subplot(gs[1, :])
        else:
            fig = plt.figure(figsize=ST['size'])
            gs = fig.add_gridspec(1, 3, width_ratios=[1.25, 1.0, 1.25])
            a1, a2, a3 = fig.add_subplot(gs[0]), fig.add_subplot(gs[1]), fig.add_subplot(gs[2])
        labels = list(R)
        short = ['central', 'half price', '8 h']
        x = np.arange(len(labels))
        shades = ['#eda100', '#c98500', '#8a6400']        # Medium yellow, darker for the variants
        s = {k: summary(R[k]).loc[period] for k in labels}
        gw = [s[k]['Battery (GW)'] for k in labels]
        a1.bar(x, gw, width=0.6, color=shades, edgecolor='white')
        for i in range(len(labels)):
            _label(a1, x[i], gw[i], f'{gw[i]:.1f} GW\n{s[labels[i]]["Curtailment (TWh/yr)"]:.1f} TWh curt.', fs=F(10.5))
        a1.set_xticks(x, short)
        a1.set_ylabel('GW of battery power')
        a1.set_title(f'(3a) Battery capacity, {period}', fontsize=F(12.5))
        _ylim_with_labels(a1, gw, top=1.35)
        _style(a1)
        d = [_econ_cost(R[k]) - _econ_cost(R[labels[0]]) for k in labels]
        a2.bar(x, d, width=0.6, color=shades, edgecolor='white')
        for i in range(len(labels)):
            _label(a2, x[i], 0.0 if abs(d[i]) < 0.05 else d[i], _delta(d[i]), fs=F(12))
        a2.axhline(0, color=MUTED, lw=0.8)
        a2.set_xticks(x, short)
        a2.set_ylabel('bn €, discounted 2020-2059')
        a2.set_title('System cost vs central', fontsize=F(12.5))
        _ylim_with_labels(a2, d)
        _style(a2)
        allr = {'Base': C['Base'], 'Medium': C['Medium'], 'Scarce': C['Scarce'], 'Medium, 8 h': R['Medium, 8 h batteries']}
        cols = [scen_color('Base'), scen_color('Medium'), scen_color('Scarce'), '#8a6400']
        for (k, n), c in zip(allr.items(), cols):
            bat = _active(n, 'StorageUnit', BATTERY, period)
            if not bat:
                continue
            capm = (n.storage_units.loc[bat, 'p_nom_opt'] * n.storage_units.loc[bat, 'max_hours']).sum()
            if capm <= 1:
                continue
            soc = ts(n, 'storage_units', 'state_of_charge').loc[period, bat].sum(axis=1) / capm
            dur = np.sort(soc.values)[::-1]
            hours = np.arange(1, len(dur) + 1) * n.snapshot_weightings.generators.loc[period].iloc[0]
            a3.plot(hours, dur, color=c, lw=2.2, label=k, ls='-' if '8 h' not in k else (0, (4, 2)))
        a3.set_xlabel('Hours per year')
        a3.set_ylabel('State of charge (share)')
        a3.set_ylim(0, 1.05)
        a3.set_title(f'(3c) Battery state of charge, {period}', fontsize=F(12.5))
        a3.legend(fontsize=F(10.5), loc='upper right')
        _style(a3)
        note(fig, 0.01, 0.95, '(3a-c) Batteries where electrolysis is limited (Medium). Caveat: with 15-hour time steps a '
                             'battery can only shift energy between 15-hour blocks', fontsize=F(11), color=INK2)
        fig.tight_layout(rect=_rect(0, 0, 1, 0.94))
    return fig


def fig_operation(period=2050):
    """(3b) Electrolyser and battery operation in a winter and a summer fortnight, Base and Medium."""
    C = scenarios()
    if C is None:
        return None
    windows = [('January', f'{period}-01-08', f'{period}-01-22'), ('July', f'{period}-07-08', f'{period}-07-22')]
    with plt.rc_context(RC()):
        fig, axes = plt.subplots(2, 2, figsize=ST['tall'] if apa() else ST['size'], sharex='col', sharey=True)
        for r, k in enumerate(['Base', 'Medium']):
            n = C[k]
            ely = _active(n, 'Link', ELECTROLYSIS, period)
            bat = _active(n, 'StorageUnit', BATTERY, period)
            t = n.snapshots[n.snapshots.get_level_values(0) == period].get_level_values(1)
            e = pd.Series(ts(n, 'links', 'p0').loc[period, ely].sum(axis=1).values / 1e3, index=t) if ely else None
            b = pd.Series(ts(n, 'storage_units', 'p').loc[period, bat].sum(axis=1).values / 1e3, index=t) if bat else None
            for c, (lab, a, z) in enumerate(windows):
                ax = axes[r, c]
                if e is not None:
                    ax.fill_between(e.loc[a:z].index, 0, e.loc[a:z].values, step='post',
                                    color=ROUTE_COLORS['Green (grid electrolysis)'], alpha=0.85, lw=0,
                                    label='Electrolysers (power use)')
                if b is not None:
                    ax.step(b.loc[a:z].index, b.loc[a:z].values, where='post', color='#6250d6', lw=1.8,
                            label='Battery (+ discharge, - charge)')
                ax.axhline(0, color=MUTED, lw=0.8)
                ax.set_title(f'{k}, {lab} {period}', fontsize=F(12))
                if apa():       # fewer date ticks on the narrow report panels
                    ax.xaxis.set_major_locator(matplotlib.dates.DayLocator(interval=4))
                ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%d %b'))
                _style(ax)
            axes[r, 0].set_ylabel('GW')
        h, l = axes[0, 0].get_legend_handles_labels()
        fig.legend(h, l, loc='lower center', ncol=2, frameon=False)
        note(fig, 0.01, 0.95, '(3b) Electrolysers run when wind and sun are plentiful (15-hour time steps)',
                 fontsize=F(11), color=INK2)
        fig.tight_layout(rect=_rect(0, 0.07, 1, 0.94))
    return fig


# --------------------------------------------------------------------------
# P10 CO2 storage competition
# --------------------------------------------------------------------------

SECTOR_COLORS = {'Hydrogen (blue)': ROUTE_COLORS['Blue (SMR + CCS)'], 'Industry': '#b07a3a',
                 'Power (gas)': '#eda100', 'Power (biomass, BECCS)': '#008300', 'Other': MUTED}


def fig_co2storage(R=None, periods=(2030, 2040, 2050)):
    R = R or scenarios()
    with plt.rc_context(RC()):
        fig, axes = _row_axes(len(R) + 1, [1] * len(R) + [1.1])
        used = set()
        for ax, (k, n) in zip(axes, R.items()):
            df = co2_stored_by_sector(n).loc[list(periods)]
            x = np.arange(len(df))
            bottom = np.zeros(len(x))
            for sec in df.columns:
                v = df[sec].values
                if v.max() <= 1e-3:
                    continue
                ax.bar(x, v, bottom=bottom, width=0.66, color=SECTOR_COLORS.get(sec, MUTED), edgecolor='white',
                       linewidth=1.5)
                used.add(sec)
                bottom += v
            caps = [CO2_STORAGE_CAPS['central'].get(p, np.nan) for p in periods]
            for i, c in enumerate(caps):
                ax.plot([x[i] - 0.4, x[i] + 0.4], [c, c], color=INK, lw=2)
            ax.set_xticks(x, [str(p) for p in periods])
            ax.set_title(k, fontsize=F(12.5))
            ax.set_ylim(0, 28)
            _style(ax)
        axes[0].set_ylabel('Mt CO$_2$ stored per year')
        if apa():
            axes[2].set_ylabel('Mt CO$_2$ stored per year')
        axes[0].plot([], [], color=INK, lw=2, label='storage cap')
        ax = axes[-1]
        x = np.arange(len(R))
        ind = [float(co2_stored_by_sector(n).loc[periods[-1]].get('Industry', 0.0)) for n in R.values()]
        emi = [float(co2_emissions(n).loc[periods[-1], 'CO2 total (Mt/yr)']) for n in R.values()]
        ax.bar(x, emi, width=0.58, color=[scen_color(k) for k in R], edgecolor='white')
        for i in range(len(x)):
            _label(ax, x[i], emi[i], f'{emi[i]:.1f}', fs=F(12))
        ax.set_xticks(x, list(R))
        ax.set_title(f'CO$_2$ to the air, {periods[-1]}', fontsize=F(12.5))
        ax.set_ylabel('Mt CO$_2$ per year, all sectors')
        _ylim_with_labels(ax, emi)
        _style(ax)
        handles = [Patch(facecolor=SECTOR_COLORS[s], edgecolor='white', label=s) for s in SECTOR_COLORS if s in used]
        handles.append(plt.Line2D([], [], color=INK, lw=2, label='storage cap (10 / 22 / 25 Mt)'))
        fig.legend(handles=handles, loc='lower center', ncol=len(handles), frameon=False)
        note(fig, 0.01, 0.95, 'CO$_2$ storage is capped: blue hydrogen takes storage that industry and power would '
                             'otherwise use', fontsize=F(11), color=INK2)
        fig.tight_layout(rect=_rect(0, 0.08, 1, 0.94))
    return fig


# --------------------------------------------------------------------------
# P11 water for hydrogen by route
# --------------------------------------------------------------------------

def water_by_route(n, period=2050):
    """Water for hydrogen (million m3/yr) by route in one period (litres per kg from hydrogen.WATER_L_PER_KG)."""
    from energy_model.h2_presets import MWH_PER_KG
    b = h2_balance(n).loc[period]
    per = {r: WATER_L_PER_KG['electrolysis'] for r in ROUTES if r not in ('Blue (SMR + CCS)', 'Grey (SMR)')}
    per.update({'Blue (SMR + CCS)': WATER_L_PER_KG['SMR CCS'], 'Grey (SMR)': WATER_L_PER_KG['SMR']})
    return pd.Series({r: b[r] * 1e6 / MWH_PER_KG * per[r] / 1e3 / 1e6 for r in ROUTES})


def fig_water(R=None, period=2050):
    R = R or scenarios()
    with plt.rc_context(RC()):
        fig = plt.figure(figsize=ST['size'])
        gs = fig.add_gridspec(1, 2, width_ratios=[1.5, 1])
        a1, a2 = fig.add_subplot(gs[0]), fig.add_subplot(gs[1])
        x = np.arange(len(R))
        bottom = np.zeros(len(x))
        data = {k: water_by_route(n, period) for k, n in R.items()}
        used = []
        for route in ROUTE_COLORS:
            v = np.array([data[k][route] for k in R])
            if v.max() <= 1e-3:
                continue
            a1.bar(x, v, bottom=bottom, width=0.6, color=ROUTE_COLORS[route], edgecolor='white', linewidth=1.5,
                   hatch=ROUTE_HATCH.get(route), label=route)
            used.append(route)
            bottom += v
        for i in range(len(x)):
            _label(a1, x[i], bottom[i], f'{bottom[i]:.1f}', fs=F(13))
        a1.set_xticks(x, list(R))
        a1.set_ylabel('million m$^3$ of water per year')
        a1.set_title(f'Water for hydrogen, {period}', fontsize=F(12.5))
        _ylim_with_labels(a1, bottom)
        h, l = a1.get_legend_handles_labels()
        if apa():           # the legend under the panels: no empty space between them
            fig.legend(h[::-1], l[::-1], loc='lower center', ncol=len(h), frameon=False, fontsize=F(10.5))
        else:
            a1.legend(h[::-1], l[::-1], loc='upper left', bbox_to_anchor=(1.0, 1.0), fontsize=F(10.5))
        _style(a1)
        lpk = [('Electrolysis', WATER_L_PER_KG['electrolysis'], ROUTE_COLORS['Green (grid electrolysis)'], None),
               ('SMR + CCS (blue)', WATER_L_PER_KG['SMR CCS'], ROUTE_COLORS['Blue (SMR + CCS)'], None),
               ('SMR (grey)', WATER_L_PER_KG['SMR'], ROUTE_COLORS['Grey (SMR)'], '////')]
        a2.barh(np.arange(len(lpk)), [v for _, v, _, _ in lpk], color=[c for _, _, c, _ in lpk],
                hatch=[h for *_, h in lpk], edgecolor='white', height=0.55)
        for i, (_, v, _, _) in enumerate(lpk):
            a2.text(v + 0.5, i, f'{v:.0f} L/kg', va='center', fontsize=F(12), color=INK)
        a2.set_yticks(np.arange(len(lpk)), [nm for nm, *_ in lpk])
        a2.invert_yaxis()
        a2.set_xlim(0, max(v for _, v, _, _ in lpk) * 1.35)
        a2.set_xlabel('litres of water per kg H$_2$')
        a2.set_title('Water per kg (consumption)', fontsize=F(12.5))
        a2.spines[['top', 'right']].set_visible(False)
        note(fig, 0.01, 0.95, 'Water is not modelled; this is an output: hydrogen by route x litres per kg '
                             '(electrolysis 17.5-22.3, SMR 8-12.5, SMR + CCS 24-32 L/kg; research report)',
                 fontsize=F(11), color=INK2)
        note(fig, 0.01, 0.015, 'Electrolysis needs purified water at the plant; most water of the reformers is cooling '
                              'water, which can come from other sources.', fontsize=F(9.5), style='italic', color=INK2)
        fig.tight_layout(rect=_rect(0, 0.10 if apa() else 0.04, 1, 0.94))
    return fig


# --------------------------------------------------------------------------
# P12 the oversized plant
# --------------------------------------------------------------------------

def fig_oversized(period=2050):
    names = {'Base': 'S1', 'Medium': 'S2', 'Medium, oversized': 'S2_oversized'}
    R = runs(names)
    if R is None:
        return None
    with plt.rc_context(RC()):
        fig, axes = plt.subplots(1, 3, figsize=ST['size'])
        labels = list(R)
        x = np.arange(len(labels))
        cols = [scen_color('Base'), scen_color('Medium'), '#8a6400']
        s = {k: summary(R[k]).loc[period] for k in labels}
        cap = [s[k]['Electrolyser capacity (GW_el)'] for k in labels]
        flh = [s[k]['Electrolyser full-load hours (h/yr)'] for k in labels]
        dc = [_econ_cost(R[k]) - _econ_cost(R['Medium']) for k in labels]
        for ax, v, title, fmt in [(axes[0], cap, f'Electrolysers {period}\nGW of electricity input', '{:.1f}'),
                                  (axes[1], flh, f'Full-load hours {period}\nh per year', '{:,.0f}'),
                                  (axes[2], dc, 'System cost vs Medium\nbn €, discounted 2020-2059', '{:+.1f}')]:
            ax.bar(x, v, width=0.6, color=cols, edgecolor='white')
            for i in range(len(x)):
                _label(ax, x[i], v[i], _delta(v[i]) if fmt == '{:+.1f}' else fmt.format(v[i]), fs=F(12.5))
            ax.axhline(0, color=MUTED, lw=0.8)
            ax.set_xticks(x, ['Base', 'Medium', 'Medium,\noversized'])
            ax.set_title(title, fontsize=F(12.5))
            _ylim_with_labels(ax, v)
            _style(ax)
        note(fig, 0.01, 0.95, 'Building for abundant water, then a drought: the electrolysers of Base are built, but '
                             'water allows only as much hydrogen output as in Medium (Medium, oversized)', fontsize=F(11),
             color=INK2)
        fig.tight_layout(rect=_rect(0, 0, 1, 0.94))
    return fig


# --------------------------------------------------------------------------
# P13 overview of every variation
# --------------------------------------------------------------------------

OVERVIEW = (['', '_noadd', '_storage', '_green', '_pink', '_storage_x3', '_green_only'] if ADDITIONS else ['']) + [
    '_sub20', '_sub40', '_infra20', '_infra40', '_capexlow', '_co2low', '_co2high', '_battery_cheap', '_battery_8h', '_oversized', '_10pct',
    '_htp_fuel']


def fig_overview(period=2050):
    rows = [v for v in OVERVIEW if any(run(SCEN[sc] + v) is not None for sc in SCEN)]
    if '' not in rows:
        return None
    vals, txts = [], []
    for v in rows:
        rv, rt = [], []
        for sc in SCEN:
            share, t = _cell(sc, v, period)
            rv.append(share)
            rt.append(t.replace('\n', '   '))
        vals.append(rv)
        txts.append(rt)
    with plt.rc_context(RC(**{'ytick.labelsize': F(9.5), 'xtick.labelsize': F(10.5)})):
        fig = plt.figure(figsize=(6.5, 6.6) if apa() else ST['size'])
        ax = fig.add_axes([0.37, 0.01, 0.62, 0.93] if apa() else [0.25, 0.01, 0.62, 0.86])
        heat_table(ax, vals, txts, ['central'] + [VARIANT_NAMES[v] for v in rows[1:]], list(SCEN), _green_cmap(),
                   0, 100, fs=F(9.2))
        note(fig, 0.01, 0.965, f'Every run: electrolysis share of hydrogen in {period} (colour, first number) and system '
                              'cost against the central run of the same scenario (bn €, discounted)',
                 fontsize=F(10), color=INK2)
    return fig


# --------------------------------------------------------------------------
# P16 green levers within the water scenarios
# --------------------------------------------------------------------------

# lever (suffix of the run name) -> label; the runs are defined in run_batch.py
LEVERS = {'': 'none (central)',
          '_desal': 'desalinated water (+€0.03/kg)',
          '_desal_x10': 'desalinated water at 10x (+€0.30/kg)',
          '_prod1': 'production subsidy €1/kg',
          '_prod2': 'production subsidy €2/kg',
          '_mandate': 'mandate: 60% electrolysis from 2040',
          '_desal_mandate': 'mandate + desalinated water'}
# cells that are not a model run, with the reason (a 60% mandate cannot be met on fresh water under a limit)
LEVER_CELLS = {('Base', '_desal'): 'no water limit', ('Base', '_desal_x10'): 'no water limit',
               ('Base', '_desal_mandate'): 'no water limit\n(= mandate)',
               ('Medium', '_desal_x10'): 'not run',
               ('Medium', '_mandate'): 'INFEASIBLE\nnot enough water', ('Scarce', '_mandate'): 'INFEASIBLE\nno electrolysers',
               ('Scarce', '_prod1'): 'no electrolysers', ('Scarce', '_prod2'): 'no electrolysers'}


def lever_table(period=2050):
    """The green levers per scenario against the central run of the same scenario: electrolysis share, system cost
    (economic: subsidies are transfers), CO2 and gas 2020-2059, the subsidy paid, and the capacity on desalinated water.
    None if the central runs are missing."""
    from .h2_results import production_subsidy_cost
    if scenarios() is None:
        return None
    rows = []
    for sc in SCEN:
        c = run(SCEN[sc])
        for v, name in LEVERS.items():
            n = run(SCEN[sc] + v)
            if n is None:
                continue
            s = summary(n).loc[period]
            dco2 = cumulative_co2(n) - cumulative_co2(c)
            dcost = _econ_cost(n) - _econ_cost(c)
            rows.append({'scenario': sc, 'lever': v, 'label': name,
                         f'Electrolysis share {period} (%)': float(np.nan_to_num(s['Electrolysis share (%)'])),
                         f'Electrolysers {period} (GW_el)': s['Electrolyser capacity (GW_el)'],
                         f'of which on desalinated water (GW_el)': s['of which on desalinated water (GW_el)'],
                         f'Full-load hours {period}': s['Electrolyser full-load hours (h/yr)'],
                         'System cost vs central (bn €)': dcost,
                         'CO2 vs central (Mt)': dco2,
                         'Gas imports vs central (TWh)': _horizon(n, gas_use(n)['Gas use, total (TWh/yr)'])
                         - _horizon(c, gas_use(c)['Gas use, total (TWh/yr)']),
                         'Production subsidy paid (bn €, present value)': production_subsidy_cost(n)[1],
                         f'Fresh water for H2 {period} (Mm3)': s['Water for H2 (Mm3/yr)'] - _desal_water(n, period)})
    return pd.DataFrame(rows)


def _desal_water(n, period):
    """Water for the electrolysers on desalinated seawater (million m3/yr): not fresh water."""
    from .h2_results import link_output
    from energy_model.h2_presets import ELECTROLYSIS_SEAWATER, MWH_PER_KG
    if not n.links.carrier.isin(ELECTROLYSIS_SEAWATER).any():
        return 0.0
    twh = float(link_output(n, ELECTROLYSIS_SEAWATER).loc[period]) / 1e6
    return twh * 1e6 / MWH_PER_KG * WATER_L_PER_KG['electrolysis'] / 1e3 / 1e6


def fig_levers(period=2050):
    """Heat table: every green lever x scenario (electrolysis share in colour; cost and CO2 against the central run
    of the same scenario); infeasible combinations are marked."""
    df = lever_table(period)
    if df is None or len(df) <= len(SCEN):
        return None
    share_col = f'Electrolysis share {period} (%)'
    vals, txts, infeasible = [], [], []
    for i, v in enumerate(LEVERS):
        rv, rt = [], []
        for j, sc in enumerate(SCEN):
            r = df[(df.scenario == sc) & (df.lever == v)]
            if r.empty:
                rv.append(np.nan)
                rt.append(LEVER_CELLS.get((sc, v), 'not run'))
                if 'INFEASIBLE' in LEVER_CELLS.get((sc, v), ''):
                    infeasible.append((i, j))
                continue
            r = r.iloc[0]
            rv.append(r[share_col])
            if v == '':
                rt.append(f'{r[share_col]:.0f}%')
            else:
                dc, de = r['System cost vs central (bn €)'], r['CO2 vs central (Mt)']
                rt.append(f'{r[share_col]:.0f}%\n{_delta(dc)} bn €   {_delta(de, "{:+.0f}", 0.5)} Mt')
        vals.append(rv)
        txts.append(rt)
    with plt.rc_context(RC()):
        fig = plt.figure(figsize=(6.5, 4.3) if apa() else ST['size'])
        ax = fig.add_axes([0.40, 0.01, 0.59, 0.90] if apa() else [0.255, 0.02, 0.45, 0.84])
        heat_table(ax, vals, txts, list(LEVERS.values()), list(SCEN), _green_cmap(), 0, 100,
                   fs=F(9.0) if apa() else F(10.5))
        for (i, j) in infeasible:           # infeasible: hatched, so it is not read as 'not run'
            ax.add_patch(Rectangle((j, i), 1, 1, facecolor='white', edgecolor=MUTED, hatch='////', lw=0, zorder=2))
            ax.add_patch(Rectangle((j + 0.04, i + 0.12), 0.92, 0.76, facecolor='white', edgecolor='none', zorder=3))
            ax.text(j + 0.5, i + 0.5, txts[i][j].replace('INFEASIBLE', 'infeasible'), ha='center', va='center',
                    fontsize=F(9.0) if apa() else F(10.5), color=INK, zorder=4, linespacing=1.2,
                    fontweight='bold')
        note(fig, 0.01, 0.955, f'Green levers within the water scenarios: electrolysis share of hydrogen in {period} '
                              '(colour), system cost and CO$_2$ 2020-2059 against the same scenario without the lever',
             fontsize=F(10.5), color=INK2)
        tx = 0.722
        for k, (t, bold) in enumerate(lever_messages(df, period)):
            note(fig, tx, 0.83 - k * 0.057, t, fontsize=F(10.5), color=INK if bold else INK2,
                 fontweight='bold' if bold else 'normal')
    return fig


def _link_input_change(n, c, carrier, period=2050):
    """Change in what the links of a carrier take from their input bus in one period (TWh/yr), run n minus run c."""
    def use(m):
        w = m.snapshot_weightings.generators.loc[period]
        links = m.links.index[m.links.carrier == carrier]
        if not len(links):
            return 0.0
        return float(m.links_t.p0.loc[period, links].mul(w, axis=0).sum().sum()) / 1e6
    return use(n) - use(c)


def lever_messages(df, period=2050):
    """The text panel of P16, written from the lever results of this package (no hard-coded numbers)."""
    share_col = f'Electrolysis share {period} (%)'

    def get(sc, lev, col):
        r = df[(df.scenario == sc) & (df.lever == lev)]
        return None if r.empty else float(r.iloc[0][col])

    out = [('What works under a water limit', True)]
    d_m, d_s, x10 = (get('Medium', '_desal', 'System cost vs central (bn €)'),
                     get('Scarce', '_desal', 'System cost vs central (bn €)'),
                     get('Scarce', '_desal_x10', 'System cost vs central (bn €)'))
    if d_m is not None and d_s is not None:
        sm, ss = get('Medium', '_desal', share_col), get('Scarce', '_desal', share_col)
        pays = '' if x10 is None else ('; still pays at 10x.' if x10 < 0 else '; not at 10x the cost.')
        out += [('Desalinated water, outside the limit:', False),
                (f'Medium {get("Medium", "", share_col):.0f}% → {sm:.0f}%, Scarce 0% → {ss:.0f}%,', False),
                (f'{d_m:+.1f} / {d_s:+.1f} bn €' + pays, False)]
    p_lo = [get('Medium', v, share_col) for v in ('_prod1', '_prod2')]
    co2 = [get('Medium', v, 'CO2 vs central (Mt)') for v in ('_prod1', '_prod2')]
    if None not in p_lo:
        c0 = get('Medium', '', share_col)
        dco2 = max(abs(x) for x in co2)
        out += [('', False), ('A subsidy per kg raises the hours,', True), ('not the capacity (water caps it):', False),
                (f'Medium {c0:.0f}% → {min(p_lo):.0f}-{max(p_lo):.0f}%, ' +
                 ('but CO$_2$ ≈ 0:' if dco2 < 2 else f'CO$_2$ {min(co2):+.0f} to {max(co2):+.0f} Mt'), False)]
        n, c = run(SCEN['Medium'] + '_prod1'), run(SCEN['Medium'])
        if dco2 < 2 and n is not None and c is not None:
            mach = _link_input_change(n, c, 'Industrial machinery - electricity', period)
            ccs = _link_input_change(n, c, 'Industrial machinery - fossil CCS', period)
            if mach < -1.0 and ccs > 1.0:
                out += [('the power comes from industry,', False), ('which goes back to gas + CCS.', False)]
    m_inf = df[(df.scenario == 'Medium') & (df.lever == '_mandate')].empty
    if m_inf:
        out += [('', False), ('A 60% mandate needs water:', True), ('infeasible in Medium and Scarce', False),
                ('unless desalinated water is allowed.', False)]
    return out


def _group_label(g):
    """One label for lever runs that sit on top of each other in P16b, e.g. 'subsidy €1/kg (Base, Medium)
    and €2/kg (Medium)'; the scenario names are left out when the group has only one scenario (the colour shows it)."""
    names = {'_prod1': 'subsidy €1/kg', '_prod2': 'subsidy €2/kg', '_mandate': 'mandate 60%',
             '_desal_mandate': 'mandate + desal.'}
    scs = list(dict.fromkeys(q[0] for q in g))
    by_lev = {}
    for q in g:
        by_lev.setdefault(q[1], []).append(q[0])
    subs = all(lv in ('_prod1', '_prod2') for lv in by_lev)
    parts = []
    for i, (lv, ss) in enumerate(by_lev.items()):
        nm = names.get(lv, lv).replace('subsidy ', '') if subs and i > 0 else names.get(lv, lv)
        parts.append(nm + (f" ({', '.join(ss)})" if len(scs) > 1 else ''))
    lab = ' and '.join(parts)
    return lab.replace(' and ', '\nand ', 1) if len(lab) > 30 else lab


def fig_levers_cost_co2(period=2050):
    """Each lever run: system cost against CO2, both against the central run of the same scenario (2020-2059)."""
    df = lever_table(period)
    if df is None or len(df) <= len(SCEN):
        return None
    d = df[df.lever != ''].copy()
    short = {'_desal': 'desal. water', '_desal_x10': 'desal. water 10x', '_prod1': 'subsidy €1/kg',
             '_prod2': 'subsidy €2/kg',
             '_mandate': 'mandate 60%', '_desal_mandate': 'mandate + desal.'}
    markers = {'_desal': 'o', '_desal_x10': 'o', '_prod1': 's', '_prod2': 's', '_mandate': '^', '_desal_mandate': 'D'}
    # label offsets in points (dx, dy, ha) of single points; points on top of each other get one label (below)
    offs = {('Scarce', '_desal_x10'): (9, 7, 'left'), ('Scarce', '_desal'): (-9, -2, 'right'),
            ('Medium', '_desal'): (-9, 0, 'right')}
    with plt.rc_context(RC()):
        fig, ax = plt.subplots(figsize=(6.5, 4.0) if apa() else ST['size'])
        x = d['System cost vs central (bn €)'].values
        y = d['CO2 vs central (Mt)'].values
        xmin, xmax = min(x.min(), 0) - 2.5, x.max() + 4.5
        ymin, ymax = min(y.min(), 0) * 1.12, max(y.max(), 0) + (32 if apa() else 22)
        ax.set_xlim(xmin, xmax)
        ax.set_ylim(ymin, ymax)
        ax.axhline(0, color=MUTED, lw=0.8, zorder=1)
        ax.axvline(0, color=MUTED, lw=0.8, zorder=1)
        ax.fill_between([xmin, 0], ymin, 0, color='#f2f8f2', zorder=0)
        ax.text(xmin + 0.3, ymin * 0.97, 'cheaper and\nless CO$_2$', ha='left', va='bottom', fontsize=F(10),
                color='#2f7a2f', style='italic')
        # reference: €250 per tonne avoided (the central CO2 price of 2050): Δcost (bn €) = 250 x ΔCO2 (Mt) / 1000
        xs = np.linspace(0, xmax, 50)
        ax.plot(xs, -xs * 1000 / 250, color=MUTED, lw=1.2, ls=(0, (4, 3)), zorder=1)
        pts = [(r.scenario, r.lever, r['System cost vs central (bn €)'], r['CO2 vs central (Mt)'])
               for _, r in d.iterrows()]
        for sc, lv, xi, yi in pts:
            ax.scatter(xi, yi, s=95 if not apa() else 55, marker=markers[lv], color=scen_color(sc),
                       edgecolor='white', linewidth=1.4, zorder=3)
        # subsidies and mandates that sit (almost) on top of each other get one label together; which ones do
        # depends on the package, so the groups are found from the data
        sx, sy = (xmax - xmin) * 0.05, (ymax - ymin) * 0.05
        groups = []
        for p in pts:
            g = next((g for g in groups if p[1] not in ('_desal', '_desal_x10') and
                      any(q[1] not in ('_desal', '_desal_x10') and abs(p[2] - q[2]) < sx and abs(p[3] - q[3]) < sy
                          for q in g)), None)
            if g is None:
                groups.append([p])
            else:
                g.append(p)
        for g in groups:
            if len(g) == 1:
                sc, lv, xi, yi = g[0]
                dx, dy, ha = offs.get((sc, lv), (9, 0, 'left'))
                ax.annotate(short[lv], (xi, yi), xytext=(dx, dy), textcoords='offset points', ha=ha,
                            va='center', fontsize=F(10), color=INK)
                continue
            lab = _group_label(g)
            cx, cy = np.mean([q[2] for q in g]), max(q[3] for q in g)
            if abs(cx) < 2 * sx and abs(cy) < 2 * sy:          # at the origin: above left, with a leader line
                ax.annotate(lab, (cx, cy), xytext=(-14, 16), textcoords='offset points', ha='right', va='bottom',
                            fontsize=F(10), color=INK,
                            arrowprops=dict(arrowstyle='-', color=INK2, lw=0.8, shrinkA=1, shrinkB=4))
            else:
                ax.annotate(lab, (max(q[2] for q in g), np.mean([q[3] for q in g])), xytext=(9, 0),
                            textcoords='offset points', ha='left', va='center', fontsize=F(10), color=INK)
        ax.set_xlabel('System cost against the central run of the same scenario (bn €, discounted 2020-2059)')
        ax.set_ylabel('CO$_2$ against central (Mt, 2020-2059)')
        _style(ax)
        scen_h = [Patch(facecolor=scen_color(k), edgecolor='white', label=k) for k in SCEN]
        lever_h = [plt.Line2D([], [], ls='', marker=m, ms=8, color=INK2, markeredgecolor='white', label=lab)
                   for m, lab in [('o', 'desalinated water'), ('s', 'production subsidy'), ('^', 'mandate 60%'),
                                  ('D', 'mandate + desal. water')]]
        if apa():           # two legend rows under the plot: scenarios, then levers
            leg = fig.legend(handles=scen_h, loc='lower center', ncol=3, frameon=False, bbox_to_anchor=(0.5, 0.055))
            fig.add_artist(leg)
            fig.legend(handles=lever_h, loc='lower center', ncol=4, frameon=False, bbox_to_anchor=(0.5, -0.01))
            fig.tight_layout(rect=(0, 0.11, 1, 0.995))
        else:
            fig.legend(handles=scen_h + lever_h, loc='lower center', ncol=7, frameon=False, bbox_to_anchor=(0.5, 0.0))
            note(fig, 0.01, 0.955, 'What each green lever buys: cost and CO$_2$ against the same scenario without it '
                                  '(points below the dashed line cost less than €250 per tonne of CO$_2$ avoided)',
                 fontsize=F(10.5), color=INK2)
            fig.tight_layout(rect=(0, 0.07, 1, 0.94))
        # the label of the €250/t line, along the line (angle from the final layout)
        fig.canvas.draw()
        p0, p1 = ax.transData.transform((0, 0)), ax.transData.transform((10, -40))
        ang = np.degrees(np.arctan2(p1[1] - p0[1], p1[0] - p0[0]))
        xl = min(xmax * 0.86, -ymin * 250 / 1000 * 0.8)
        ax.annotate('€250 per t CO$_2$ avoided', (xl, -xl * 4), xytext=(0, 4), textcoords='offset points',
                    ha='center', va='bottom', rotation=ang, rotation_mode='anchor', fontsize=F(9.5), color=INK2)
    return fig


# --------------------------------------------------------------------------
# P14 key numbers
# --------------------------------------------------------------------------

def key_numbers(R=None, period=2050):
    R = R or scenarios()
    rows = {}
    for k, n in R.items():
        s = summary(n)
        rows[k] = {
            'System cost 2020-2059 (bn €, discounted)': f'{_econ_cost(n):,.1f}',
            f'Electrolysis share of H$_2$, {period}': f"{np.nan_to_num(s.at[period, 'Electrolysis share (%)']):.0f}%",
            f'Electrolysers, {period} (GW of power input)': f"{s.at[period, 'Electrolyser capacity (GW_el)']:.1f}",
            f'Electrolyser full-load hours, {period}': f"{s.at[period, 'Electrolyser full-load hours (h/yr)']:,.0f}",
            f'Gas for hydrogen, {period} (TWh)': f"{s.at[period, 'Gas for H2 (TWh/yr)']:.1f}",
            'Gas imports 2020-2059 (TWh)': f"{_horizon(n, s['Gas use, total (TWh/yr)']):,.0f}",
            'CO$_2$ 2020-2059 (Mt)': f'{cumulative_co2(n):,.0f}',
            f'CO$_2$ from hydrogen, {period} (Mt)': f"{s.at[period, 'CO2 from H2 production (Mt/yr)']:.1f}",
            f'Water for hydrogen, {period} (million m$^3$)': f"{s.at[period, 'Water for H2 (Mm3/yr)']:.1f}",
        }
    return pd.DataFrame(rows)


def fig_numbers(R=None, period=2050):
    R = R or scenarios()
    df = key_numbers(R, period)
    with plt.rc_context(RC()):
        fig = plt.figure(figsize=ST['size'])
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(0, 133)
        ax.set_ylim(0, 56)
        ax.axis('off')
        xs = [2, 68, 90, 112]
        ax.text(xs[0], 52, 'Key numbers', fontsize=F(12.5), fontweight='bold', color=INK, va='center')
        for j, k in enumerate(df.columns):
            ax.add_patch(Rectangle((xs[j + 1] - 1, 50.6), 2, 2.8, color=scen_color(k) if k in SCEN else MUTED))
            ax.text(xs[j + 1] + 2, 52, k, fontsize=F(12.5), fontweight='bold', color=INK, va='center')
        ax.plot([2, 131], [49.4, 49.4], color=MUTED, lw=0.8)
        for i, (row, vals) in enumerate(df.iterrows()):
            y = 46 - i * 5.0
            if i % 2 == 0:
                ax.add_patch(Rectangle((1, y - 2.5), 131, 5.0, color='#f4f3f0', lw=0))
            ax.text(xs[0], y, row, fontsize=F(12), color=INK, va='center')
            for j, v in enumerate(vals):
                ax.text(xs[j + 1] + 14, y, v, fontsize=F(12.5), color=INK, va='center', ha='right')
        ax.text(2, 1.4, 'Model results (final course model + hydrogen, Dutch data, 2024 euros). Hydrogen demand '
                        '1.3 Mt/yr in every scenario.', fontsize=F(10), style='italic', color=INK2)
    return fig


# --------------------------------------------------------------------------
# P15 Sankey of the whole energy system
# --------------------------------------------------------------------------

def fig_system(scen='Base', period=2050):
    """The whole energy system of one scenario in one Sankey (the same scale for every scenario, so two slides can be
    compared)."""
    from .system_plots import plot_system_sankey
    C = scenarios()
    if C is None:
        return None
    title = (lambda k: f'{k}: energy system in {period} (TWh per year, final energy)') if apa() else (
        lambda k: f'{k}: energy system in {period}, TWh per year (final energy; the same scale for every scenario)')
    fig = plot_system_sankey({scen: C[scen]}, period, fs=1.2 if apa() else 1.45,
                             figsize=(6.5, 3.4) if apa() else ST['size'], note=False, scale_runs=C, title=title,
                             fit=True)
    note(fig, 0.01, 0.01, 'Power plants enter with their input; their losses leave as conversion losses. Hydrogen = the '
                         'gas and electricity that the reformers and electrolysers use.', fontsize=F(8.5), style='italic',
             color=INK2)
    return fig


# --------------------------------------------------------------------------
# Draw everything
# --------------------------------------------------------------------------

FIGURES = {
    'colours': ('P00_colours_of_hydrogen', fig_colours),
    'implementation': ('P_impl_model_structure', fig_implementation),
    'routes': ('P01_h2_by_route', fig_routes),
    'sankey': ('P02_h2_sankey_2050', fig_sankey),
    'cost': ('P03_cost_of_water_scarcity', fig_cost),
    'story': ('P04_policy_story', fig_story),
    'subsidy': ('P05_subsidy_2a', fig_subsidy),
    'co2price': ('P06_co2_price_2b', fig_co2price),
    'options': ('P07_additions', fig_options),              # package with additions only
    'storage': ('P08_h2_storage_2c', fig_storage),          # package with additions only
    'battery': ('P09_batteries_3a_3c', fig_battery),
    'operation': ('P09b_operation_3b', fig_operation),
    'co2storage': ('P10_co2_storage', fig_co2storage),
    'water': ('P11_water', fig_water),
    'oversized': ('P12_oversized_plant', fig_oversized),
    'overview': ('P13_overview_all_runs', fig_overview),
    'numbers': ('P14_key_numbers', fig_numbers),
    'system': ('P15_system_sankey_2050_Base', lambda: fig_system('Base')),
    'system_scarce': ('P15b_system_sankey_2050_Scarce', lambda: fig_system('Scarce')),
    'levers': ('P16_green_levers', fig_levers),
    'levers_co2': ('P16b_green_levers_cost_co2', fig_levers_cost_co2),
}
if not ADDITIONS:           # hydrogen storage and the other additions are not in this package
    for _k in ('options', 'storage'):
        FIGURES.pop(_k)


SLIDE_ONLY = {'colours', 'implementation', 'numbers'}     # tables and the slide diagram: in a report these are a
                                                         # table (key_numbers_table) and Figure 3


def save(fig, stem, out=None):
    out = Path(out or ST['out'])
    out.mkdir(parents=True, exist_ok=True)
    for ext in ST['formats']:
        fig.savefig(out / f'{stem}.{ext}', dpi=ST['dpi'], facecolor='white', bbox_inches='tight', pad_inches=0.04)
    plt.close(fig)


def key_numbers_table(out=None):
    """The key numbers per scenario as a table for the report (CSV and Markdown), next to the APA figures."""
    out = Path(out or APA_DIR)
    out.mkdir(parents=True, exist_ok=True)
    df = key_numbers()
    df.index = [i.replace('$_2$', '₂').replace('$^3$', '³') for i in df.index]
    df.to_csv(out / 'Table_key_numbers.csv')
    lines = ['| | ' + ' | '.join(df.columns) + ' |', '|---|' + '---|' * len(df.columns)]
    lines += ['| ' + i + ' | ' + ' | '.join(str(v) for v in r) + ' |' for i, r in df.iterrows()]
    (out / 'Table_key_numbers.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def lever_table_files(out=None):
    """The numbers behind P16 (green levers) as CSV and Markdown, next to the APA figures."""
    df = lever_table()
    if df is None:
        return
    out = Path(out or APA_DIR)
    out.mkdir(parents=True, exist_ok=True)
    df = df.drop(columns=['lever']).rename(columns={'label': 'lever'})
    df.round(2).to_csv(out / 'Table_green_levers.csv', index=False)
    num = df.select_dtypes('number').columns
    fmt = {c: (lambda v: f'{int(round(v)):,}') if ('Mt' in c or 'TWh' in c or 'hours' in c)
           else (lambda v: f'{round(v, 1) + 0.0:,.1f}') for c in num}       # + 0.0: no '-0.0'
    lines = ['| ' + ' | '.join(df.columns) + ' |', '|' + '---|' * len(df.columns)]
    for _, r in df.iterrows():
        lines.append('| ' + ' | '.join(fmt[c](r[c]) if c in num else str(r[c]) for c in df.columns) + ' |')
    lines += ['', 'Not in the table: the mandate alone in Medium and Scarce is infeasible (not enough water for 60% '
                  'electrolysis; Medium has no solution, Scarce is not run). Desalinated water is not needed in Base '
                  '(no water limit). Differences are against the central run of the same scenario. System cost: '
                  'discounted 2020-2059; a subsidy is a transfer, so it is added back to the model objective. CO2 and '
                  'gas: summed over 2020-2059.']
    (out / 'Table_green_levers.md').write_text('\n'.join(lines) + '\n')


def main(which=None, styles=('slide', 'apa')):
    """Draw plots in each style: slides -> results/plots/presentation, APA -> results/plots/apa."""
    import warnings
    warnings.filterwarnings('ignore')
    for style in styles:
        set_style(style)
        done, skipped = [], []
        for key, (stem, fn) in FIGURES.items():
            if (which is None and key == 'implementation') or (which and key not in which) or (style == 'apa' and key in SLIDE_ONLY):
                continue
            fig = fn()
            if fig is None:
                skipped.append(key)
                continue
            save(fig, stem)
            done.append(stem)
        if style == 'apa' and (not which or 'numbers' in which) and scenarios() is not None:
            key_numbers_table()
        if style == 'apa' and (not which or 'levers' in which):
            lever_table_files()
        print(f'{style}: written', ', '.join(done) or '-')
        if skipped:
            print(f'{style}: skipped (runs not on disk):', ', '.join(skipped))
    set_style('slide')


if __name__ == '__main__':
    args = sys.argv[1:]
    if '--sankey-decades' in args:
        set_style('slide')
        print('slide: written', ', '.join(save_sankey_decades()) or '-')
        raise SystemExit(0)
    styles = ('slide', 'apa')
    if '--slide' in args or '--apa' in args:
        styles = tuple(s for s in ('slide', 'apa') if f'--{s}' in args)
    main([a for a in args if not a.startswith('--')] or None, styles)
