"""Scenario matrix of the freight study (methodology figure): the parameter paths of the two axes and of the carbon
price, the 2x2 matrix with its runs, and what each set of runs contains (the assignment core and the realistic layer
under current truck and hydrogen policies). Values are read from the presets, so the figure follows the model.
Run from the package folder: python figures_document/Figure_freight_scenarios.py
"""
import os
import sys

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch

sys.path.insert(0, os.getcwd())

from energy_model.freight_presets import BET_COSTS, GASOLINE_PRICES, TRUCK_FUEL_PRICES  # noqa: E402
from energy_model.h2_presets import CO2_PRICES, CO2_PRICES_ETS2  # noqa: E402

BLUE, ORANGE, INK, MUTED, GRID, FILL = '#2a78d6', '#eb6834', '#1f2328', '#59636e', '#e6e8eb', '#f3f6fa'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 7.5, 'axes.spines.top': False,
                     'axes.spines.right': False, 'axes.edgecolor': MUTED, 'xtick.color': MUTED, 'ytick.color': MUTED,
                     'axes.labelcolor': INK})
Y = [2020, 2030, 2040, 2050]
FS = 5.6                                                   # small text


def panel(ax, title, ylim, xmax=2061):
    """Common look of a parameter panel (room on the right for the line labels)."""
    ax.set_title(title, fontsize=7.3, color=INK, loc='left', pad=3)
    ax.set_xticks(Y, ['2020', '30', '40', '50'], fontsize=6.2)
    ax.tick_params(axis='y', labelsize=6.2)
    ax.set_xlim(2016, xmax)
    ax.set_ylim(*ylim)
    ax.grid(axis='y', color=GRID, lw=0.6)
    ax.set_axisbelow(True)


def path(ax, values, ls, color, lw=1.5, ms=2.8, label=None, dy=0.0, **kw):
    """One parameter path, with an optional label at its right end."""
    ax.plot(Y, [values[y] for y in Y], ls=ls, color=color, lw=lw, marker='o' if ms else None, ms=ms, **kw)
    if label:
        ax.text(2051.5, values[2050] + dy, label, ha='left', va='center', fontsize=FS + 0.2,
                color=INK if lw > 1 else MUTED)


fig = plt.figure(figsize=(6.5, 5.6))
outer = fig.add_gridspec(2, 1, height_ratios=[2.7, 1.8], hspace=0.12)
top = outer[0].subgridspec(2, 3, width_ratios=[1, 1, 1.9], hspace=0.55, wspace=0.42)

# ---- X: BET costs (CAPEX and VOM, constant vs decrease) ----
ax = fig.add_subplot(top[0, 0])
for key, ls in (('constant', '--'), ('decrease', '-')):
    path(ax, BET_COSTS[key]['CAPEX'], ls, BLUE, label=key)
panel(ax, 'X: BET CAPEX (€/kW)', (0, 760))
ax = fig.add_subplot(top[0, 1])
for key, ls in (('constant', '--'), ('decrease', '-')):
    path(ax, BET_COSTS[key]['VOM'], ls, BLUE, label=key)
panel(ax, 'X: BET VOM (€/kWh)', (0, 0.125))

# ---- Y: fuel price; course gasoline (thick) and the realistic layer's diesel excluding VAT (thin) ----
ax = fig.add_subplot(top[1, 0])
for key, ls in (('moderate', '--'), ('sharp', '-')):
    path(ax, GASOLINE_PRICES[key], ls, ORANGE)
for key, ls in (('diesel_nl', '--'), ('diesel_nl_sharp', '-')):
    path(ax, TRUCK_FUEL_PRICES[key], ls, ORANGE, lw=0.9, ms=0, alpha=0.6)
ax.legend(handles=[Line2D([], [], color=ORANGE, lw=1.4, ls='-', label='sharp'),
                   Line2D([], [], color=ORANGE, lw=1.4, ls='--', label='moderate'),
                   Line2D([], [], color=ORANGE, lw=0.9, alpha=0.6, label='diesel ex VAT')],
          frameon=False, fontsize=FS, loc='upper left', handlelength=1.6, borderaxespad=0.1, labelspacing=0.3)
panel(ax, 'Y: fuel price (€/MWh)', (0, 700), xmax=2054)

# ---- carbon price: the moderate path in every scenario; central and high as sensitivities ----
ax = fig.add_subplot(top[1, 1])
for key, lw, ms in (('high', 0.9, 0), ('central', 0.9, 0), ('low', 1.5, 2.8)):
    col = INK if key == 'low' else MUTED
    path(ax, CO2_PRICES[key], '-', col, lw=lw, ms=ms, label={'low': 'moderate'}.get(key, key),
         dy={'low': 22, 'central': 12, 'high': 0}[key])
    path(ax, CO2_PRICES_ETS2[key], '--', col, lw=lw, ms=ms)
ax.legend(handles=[Line2D([], [], color=INK, lw=1.1, ls='-', label='ETS1'),
                   Line2D([], [], color=INK, lw=1.1, ls='--', label='ETS2')],
          frameon=False, fontsize=FS, loc='upper left', handlelength=1.6, borderaxespad=0.1, labelspacing=0.3)
panel(ax, 'CO$_2$ price (€/t)', (0, 700))

# ---- the 2x2 matrix with its runs ----
ax = fig.add_subplot(top[:, 2])
ax.set_xlim(-0.72, 2.05), ax.set_ylim(-0.78, 2.45), ax.axis('off')
cells = {(0, 0): 'F1', (1, 0): 'F2', (0, 1): 'F3', (1, 1): 'F4'}
for (i, j), f in cells.items():
    ax.add_patch(FancyBboxPatch((i + 0.04, j + 0.04), 0.92, 0.92, boxstyle='round,pad=0,rounding_size=0.05',
                                facecolor=FILL, edgecolor=MUTED, lw=0.8))
    ax.text(i + 0.5, j + 0.64, f, ha='center', va='center', fontsize=13, weight='bold', color=INK)
    ax.text(i + 0.5, j + 0.28, f'{f}_nofcet\n{f}_real', ha='center', va='center', fontsize=FS + 0.3,
            color=MUTED, linespacing=1.45)
for i, lab in enumerate(['constant', 'decrease']):
    ax.text(i + 0.5, 2.03, lab, ha='center', va='bottom', fontsize=6.6, color=BLUE)
ax.text(1.0, 2.21, 'X: BET costs', ha='center', va='bottom', fontsize=7.4, color=BLUE, weight='bold')
for j, lab in enumerate(['moderate', 'sharp']):
    ax.text(-0.04, j + 0.5, lab, ha='right', va='center', fontsize=6.6, color=ORANGE, rotation=90)
ax.text(-0.4, 1.0, 'Y: fuel price', ha='center', va='center', fontsize=7.4, color=ORANGE, weight='bold', rotation=90)
ax.text(1.0, -0.07, 'Each cell: the core run (…_nofcet) and the\nrealistic run (…_real); all with the moderate\n'
        'CO$_2$ price. Sensitivities for F1 and F4: CO$_2$ price\ncentral and high, Sunday ban and night ban',
        ha='center', va='top', fontsize=FS + 0.2, color=MUTED, linespacing=1.4)

# ---- what each set of runs contains ----
ax = fig.add_subplot(outer[1])
ax.set_xlim(0, 1), ax.set_ylim(0, 1), ax.axis('off')
LINE = FS * 1.5 / (ax.get_position().height * fig.get_figheight() * 72)     # one text line in axes units


def card(x0, w, head, rows, lab_w=0.0):
    """A box over the full height with a bold heading and rows of (label, lines); label column lab_w wide."""
    y = 1.0 - 0.07
    ax.text(x0 + 0.014, y, head, ha='left', va='top', fontsize=6.7, weight='bold', color=INK)
    y -= 1.85 * LINE
    for lab, lines in rows:
        if lab:
            ax.text(x0 + 0.014, y, lab, ha='left', va='top', fontsize=FS, weight='bold', color=MUTED)
        for k, s in enumerate(lines):
            ax.text(x0 + 0.014 + lab_w, y - k * LINE, s, ha='left', va='top', fontsize=FS, color=INK)
        y -= (len(lines) + 0.35) * LINE
    ax.add_patch(FancyBboxPatch((x0, 0.0), w, 1.0, boxstyle='round,pad=0,rounding_size=0.02', facecolor=FILL,
                                edgecolor=MUTED, lw=0.8, zorder=0, clip_on=False))
    return y


card(0.0, 0.355, 'Assignment core (…_nofcet runs)',
     [(None, ['ICE truck and BET from the course table',
              'course gasoline prices on the Y axis',
              'moderate CO$_2$ price: ETS1 75 → 170 €/t;',
              'ETS2 on road fuels from 2028: 55 → 170 €/t',
              'no truck or hydrogen policies',
              'extension (F1–F4): + FCET and H$_2$-ICE truck'])])
card(0.375, 0.625, 'Realistic layer (…_real runs): policies of October 2026',
     [('Trucks', ['EU CO$_2$ standards: zero-emission share ≥ 30 / 65 / 75%',
                  'truck toll €0.20 vs €0.039/km; AanZET: BET CAPEX −20%']),
      ('Hydrogen', ['RED III transport: ≥ 1% RFNBO (counted twice)',
                    'industry obligation: 4% (2030) → 9.9% (2035) RFNBO',
                    'OWE: electrolysers −50%; SWiM: H$_2$ trucks −60% (2030s)']),
      ('Market', ['ramp-up (AFIR): zero-emission ≤ 40 / 90% of freight',
                  'hydrogen trucks ≤ 3 / 25%; heavy segment 5% (no BET)',
                  'BETs by duty cycle: urban 25%, regional 35%, long haul']),
      ('Prices', ['diesel ex VAT on both Y paths (thin lines); H$_2$ delivery ×1.5'])], lab_w=0.105)

for ext in ('png', 'svg'):
    fig.savefig(f'figures_document/Figure_freight_scenarios.{ext}', dpi=300, bbox_inches='tight', facecolor='white')
print('saved figures_document/Figure_freight_scenarios.png')
