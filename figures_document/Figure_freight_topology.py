"""The freight module of the model (methodology figure): the carriers the trucks draw on, the six truck technologies
(filled in the colours of the result figures), the freight demand they serve, and the limits and price instruments of
the realistic layer. Grey = the course model and the group's hydrogen module; * and dashed = realistic layer only.
Run from the package folder: python figures_document/Figure_freight_topology.py
"""
import os

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

INK, MUTED, OLD, FILL = '#1f2328', '#59636e', '#8a8f98', '#f3f6fa'
TRUCK = {'ICE': '#8a8f98', 'BET_LH': '#104281', 'BET': '#2a78d6', 'BET_U': '#86b6ef', 'FCET': '#1baf7a',
         'H2ICE': '#6250d6'}
DASH = (0, (3, 2))
plt.rcParams.update({'font.family': 'DejaVu Sans'})
fig, ax = plt.subplots(figsize=(6.5, 4.9))
ax.set_xlim(0, 100), ax.set_ylim(0, 75), ax.axis('off')


def box(x, y, w, h, text='', edge=OLD, fill='white', ink=INK, dashed=False, size=6.0, lw=1.0):
    """Rounded box with centred text."""
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.3,rounding_size=1.0', linewidth=lw,
                                edgecolor=edge, facecolor=fill, linestyle=DASH if dashed else '-'))
    if text:
        ax.text(x + w / 2, y + h / 2, text, ha='center', va='center', fontsize=size, color=ink, linespacing=1.3)


def arrow(x0, y0, x1, y1, color=MUTED, lw=0.9):
    ax.annotate('', xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(arrowstyle='-|>', color=color, lw=lw, shrinkA=0, shrinkB=0, mutation_scale=7))


def listing(x, y, head, items, size=5.7, step=2.45):
    """A bold heading and bullet items, top-aligned at y (items starting with a space continue the previous one)."""
    ax.text(x, y, head, fontsize=size + 0.4, weight='bold', color=INK, va='top', linespacing=1.25)
    y -= step * (head.count('\n') + 1.35)
    for s in items:
        ax.text(x, y, ('   ' if s.startswith(' ') else '• ') + s.strip(), fontsize=size, color=INK, va='top')
        y -= step


# ---- carriers: the course model and the group's hydrogen module ----
CX, CW = 1, 19
box(CX, 57.5, CW, 7, 'Oil products\nprice: Y axis')
box(CX, 36.5, CW, 10, 'Electricity\ncourse power sector\n(wind, solar, gas,\nnuclear, batteries)')
box(CX, 19.0, CW, 11.5, 'Hydrogen\ngrey · blue · green\ngroup H$_2$ module\n(+ 1.3 Mt industry\ndemand)')

# ---- truck technologies ----
TX, TW = 27, 31
box(TX, 58, TW, 6, 'ICE truck (+ 2020 stock)\nη 40% · 0.25 t CO$_2$/MWh', TRUCK['ICE'], TRUCK['ICE'], 'white')
box(TX, 47.3, TW, 3.8, 'BET, urban* · depot charging', INK, TRUCK['BET_U'], INK, dashed=True, size=5.9)
box(TX, 40.1, TW, 5.6, 'BET (course table, + 2020 stock)\nη 70% · costs: X axis', TRUCK['BET'], TRUCK['BET'],
    'white', size=5.9)
box(TX, 34.7, TW, 3.8, 'BET, long haul* · public charging', INK, TRUCK['BET_LH'], 'white', dashed=True, size=5.9)
box(TX, 26.5, TW, 3.8, 'FCET, from 2030 · η 45–55%', TRUCK['FCET'], TRUCK['FCET'], 'white', size=5.9)
box(TX, 20.3, TW, 3.8, 'H$_2$-ICE truck, from 2030 · η 35–40%', TRUCK['H2ICE'], TRUCK['H2ICE'], 'white', size=5.9)
# carriers -> trucks
arrow(CX + CW + 0.6, 61.0, TX - 0.6, 61.0)
for y in (49.2, 42.9, 36.6):
    arrow(CX + CW + 0.6, 41.5, TX - 0.6, y)
for y in (28.4, 22.2):
    arrow(CX + CW + 0.6, 24.75, TX - 0.6, y)

# ---- freight demand and CO2 ----
FX, FW = 69, 30
box(FX, 59, FW, 6, 'CO$_2$ to air\nETS2 on road fuels from 2028')
arrow(TX + TW + 0.6, 62.0, FX - 0.6, 62.0)
box(FX, 33.5, FW, 16.5, 'Freight transport\nheavy-duty road (truck output)\n25 TWh (90 PJ) in 2020,\n'
    '35 TWh in 2050 (GDP$^{0.6}$)\nhourly profile; Sunday-ban\nand night-ban variants', INK, FILL, INK, size=6.0,
    lw=1.2)
for (y0, y1) in ((60.0, 48.0), (49.2, 45.5), (42.9, 43.0), (36.6, 40.5), (28.4, 38.0), (22.2, 35.5)):
    arrow(TX + TW + 0.6, y0, FX - 0.6, y1, color=INK, lw=0.8)

# ---- realistic layer: limits on the truck mix (shares of the freight energy per period) ----
box(FX, 1.5, FW, 28.5, '', INK, 'white', dashed=True, lw=0.9)
listing(FX + 1.4, 29.0, 'Realistic layer*: limits on\nthe shares of freight',
        ['zero-emission ≥ 30 / 65 / 75%', ' (EU CO$_2$ standards)', 'zero-emission ≤ 40 / 90%',
         ' (market ramp-up, AFIR)', 'FCET + H$_2$-ICE ≤ 3 / 25%', 'BET urban ≤ 25%, regional ≤ 35%',
         'heavy segment 5%: no BET', 'RED III: renewable H$_2$ for road', 'test: renewable H$_2$ at the pump'],
        size=5.6, step=2.25)
ax.plot([FX + FW / 2, FX + FW / 2], [30.6, 32.9], color=INK, lw=0.8, ls=DASH)

# ---- realistic layer: prices, taxes and subsidies ----
box(TX - 6, 1.5, 43, 15.8, '', INK, 'white', dashed=True, lw=0.9)
listing(TX - 4.8, 16.5, 'Realistic layer*: prices, toll and subsidies',
        ['diesel excluding VAT on both Y paths', 'truck toll €0.20/km (ICE), €0.039/km (zero-emission)',
         'AanZET: BET CAPEX −20% (2030s)', 'SWiM: FCET and H$_2$-ICE truck CAPEX −60% (2030s)',
         'OWE: electrolyser CAPEX −50% (2030 vintage)'], size=5.6, step=2.25)

# ---- key ----
ax.text(1, 73.4, 'Grey: course model and the group\'s hydrogen module.  Coloured: truck technologies (colours of the '
        'result figures).', fontsize=5.9, color=MUTED, va='center')
ax.text(1, 70.9, '* and dashed: realistic layer only (current policies, real prices, market frictions).',
        fontsize=5.9, color=MUTED, va='center')

os.makedirs('figures_document', exist_ok=True)
for ext in ('png', 'svg'):
    fig.savefig(f'figures_document/Figure_freight_topology.{ext}', dpi=300, bbox_inches='tight', facecolor='white')
print('saved figures_document/Figure_freight_topology.png')
