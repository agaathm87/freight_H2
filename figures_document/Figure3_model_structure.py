# Figure 3 of the report: model structure of the hydrogen extension (set-up agreed with Francesco on 14 October,
# base = no water scarcity, 15 October). Drawn for the package it is in (energy_model/package.py):
#   without additions   SMR (grey), SMR + CCS (blue) and the grid electrolyser (green) feed the hydrogen demand;
#   with additions      plus hydrogen storage, the pure green route (dedicated wind and solar) and pink hydrogen
#                       (dedicated nuclear), in every run (dotted boxes).
# Hydrogen is a demand (1.3 Mt/yr, fixed) that end-use technologies feed directly. The water limit (parameter 1) caps
# the capacity of all electrolysers together. Made with Python + matplotlib. Run:  pip install matplotlib   then
#   python Figure3_model_structure.py        APA, in colour (report): Figure3_model_structure_APA.png / .pdf / .svg
#   python Figure3_model_structure.py --bw   APA, black and white:    Figure3_model_structure_APA_bw.png / .pdf / .svg
# Colour: the fill is the colour of the hydrogen (green, pure green, pink, blue, grey; as in the result charts); the line
# style says what the box is (course model, added, addition, bus, scenario constraint). APA: 6.5 inches wide, text 8 pt
# or larger. The slide version of this figure is P_impl_model_structure in results/figures/presentation (made by
# energy_model/presentation.py): the same structure laid out for 16:9, with the parameters of each scenario.
import re
import sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Arial", "Liberation Sans", "Helvetica", "DejaVu Sans"]


def _additions():
    """The package flag (energy_model/package.py), read as text so that this script needs only matplotlib."""
    f = Path(__file__).resolve().parents[1] / "energy_model" / "package.py"
    m = re.search(r"^ADDITIONS = (True|False)", f.read_text(), re.M) if f.exists() else None
    return bool(m and m.group(1) == "True")


ADDITIONS = _additions()
STORAGE_ENABLED = True
COLOUR = "--bw" not in sys.argv
W = 100
H = 113 if ADDITIONS else (92 if STORAGE_ENABLED else 80)
fig = plt.figure(figsize=(6.5, 6.5 * H / W))
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.axis("off")
BLACK, GRAY, INK2 = "#000000", "#E6E6E6", "#333333"
TS, SS = 9.0, 8.0                       # title / text (pt); APA: 8 pt or more
STEP = 2.25                             # line height of the text lines (units of 0.065 in)
LINE = {"existing": "-", "added": (0, (4, 2)), "option": (0, (1, 1.4)), "bus": "-", "limit": (0, (7, 2, 1.5, 2))}
WIDTH = {"existing": 0.8, "added": 0.9, "option": 1.2, "bus": 2.2, "limit": 1.2}
# colours of the hydrogen (as h2_plots.ROUTE_COLORS): (tint for the fill, colour for the border)
TINT = {"grid": ("#ddf3ea", "#1baf7a"), "pure": ("#dcefdc", "#008300"), "pink": ("#fbe6ee", "#e87ba4"),
        "blue": ("#dde9f8", "#2a78d6"), "grey": ("#ecebe8", "#75746f"), "demand": ("#ecebe8", BLACK),
        None: ("white", BLACK)}


def node(x, y, w, h, title, lines=(), kind="existing", colour=None):
    """kind: existing (solid), added (dashed), option = an addition (dotted), bus (bold). Colour mode: fill and border in
    the colour of the hydrogen; black and white: added = grey fill."""
    if COLOUR:
        fc, ec = TINT[colour]
    else:
        fc, ec = (GRAY if kind == "added" else "white"), BLACK
    ax.add_patch(Rectangle((x, y), w, h, facecolor=fc, edgecolor=ec, linewidth=WIDTH[kind], linestyle=LINE[kind]))
    titles = title.split("\n")
    total = 2.5 * len(titles) + STEP * len(lines) + (0.3 if lines else 0)
    top = y + h / 2 + total / 2
    for t in titles:
        ax.text(x + w / 2, top - 1.25, t, ha="center", va="center", fontsize=TS, fontweight="bold")
        top -= 2.5
    top -= 0.3
    for i, ln in enumerate(lines):
        ax.text(x + w / 2, top - STEP * (i + 0.5), ln, ha="center", va="center", fontsize=SS)
    return dict(x=x, y=y, w=w, h=h, cx=x + w / 2, cy=y + h / 2, l=x, r=x + w, t=y + h, b=y)


def arrow(p1, p2, both=False):
    ax.annotate("", xy=p2, xytext=p1,
                arrowprops=dict(arrowstyle="<|-|>" if both else "-|>", color=BLACK, lw=0.8, mutation_scale=8,
                                shrinkA=0, shrinkB=0))


def seg(xs, ys):
    ax.plot(xs, ys, color=BLACK, lw=0.8, solid_capstyle="butt")


def path(points, both=False):
    """Orthogonal connector: straight segments through points, arrow head on the last segment."""
    for (x1, y1), (x2, y2) in zip(points[:-2], points[1:-1]):
        seg([x1, x2], [y1, y2])
    arrow(points[-2], points[-1], both=both)


# ---- column geometry ----
C0, C1, C2, C3 = 1.0, 21.5, 42.0, 74.5
BW, BUSW, TW, DW = 17.5, 16.0, 22.0, 24.5     # supply, bus, technology and demand box widths

for x, w, t in [(C0, BW, "Supply"), (C1, BUSW, "Carrier bus"), (C2, TW, "End-use technologies"),
                (C3, DW, "Demand")]:
    ax.text(x + w / 2, H - 2.2, t, ha="center", va="center", fontsize=TS + 0.4, fontweight="bold")
    ax.plot([x, x + w], [H - 4.0, H - 4.0], color=BLACK, lw=0.6)

# ---- rows (y of the boxes): the package with additions has two more electrolysers and H2 storage ----
if ADDITIONS:
    Y = dict(ded=83.0, bat=70.5, gen=56.5, ely=56.5, nuc=45.5, smr=28.5, ccs=15.0, gas=22.0, dem=56.0, sto=40.0, fb=43.0)
else:
    Y = dict(bat=62.0, gen=48.5, ely=48.5, smr=28.5, ccs=15.0, gas=21.5, dem=26.0, sto=40.0, fb=46.0)

# ---- the water limit: a frame around every electrolyser ----
FX, FW, FB, FT = C2 - 3.5, TW + 7.0, Y["fb"], H - 6.5
ax.add_patch(Rectangle((FX, FB), FW, FT - FB, facecolor="none", edgecolor=BLACK, linewidth=WIDTH["limit"],
                       linestyle=LINE["limit"]))
ax.text(FX + FW / 2, FT - 2.3, "Water limit (1)", ha="center", va="center", fontsize=TS, fontweight="bold")
LIMIT_LINES = (["all electrolysers together ≤ a", "share of what Base without", "additions builds: 100% Base,",
                "50% Medium, 0% Scarce"] if ADDITIONS else
               ["electrolyser capacity ≤ a share", "of the cost-optimal capacity", "(Base): 100% Base, 50%",
                "Medium, 0% Scarce"])
for i, ln in enumerate(LIMIT_LINES):
    ax.text(FX + FW / 2, FT - 5.0 - STEP * i, ln, ha="center", va="center", fontsize=SS)

# ---- nodes ----
bat = node(C1, Y["bat"], BUSW, 9.5, "Battery", ["course model;", "sensitivities 3a–c"], "existing")
gen = node(C0, Y["gen"], BW, 10.5, "Electricity", ["generation (wind,", "solar, gas, …)"], "existing")
ebus = node(C1, Y["gen"] + 0.5, BUSW, 9.5, "Electricity\nbus", [], "bus")
ely = node(C2, Y["ely"], TW, 10.5, "Electrolyser", ["green H₂ (grid)", "investment cost (2a)"], "added", "grid")
smr = node(C2, Y["smr"], TW, 10.5, "SMR", ["grey H₂ (existing + new)", "CO₂ emitted, priced (2b)"], "added", "grey")
ccs = node(C2, Y["ccs"], TW, 10.5, "SMR + CCS", ["blue H₂: 90% of CO₂", "captured and stored"], "added", "blue")
gas = node(C0, Y["gas"], BW, 8.5, "Natural gas", ["supply (imported)"], "existing")
dem = node(C3, Y["dem"], DW, 25.0, "Industrial H₂", ["1.3 Mt/yr, fixed in all", "periods and scenarios", "(exogenous):",
                                                     "refineries, ammonia"], "added", "demand")
electrolysers = [ely]
if ADDITIONS:
    ded = node(C0, Y["ded"], BW, 8.0, "Wind + solar", ["dedicated, no grid"], "option", "pure")
    ely_g = node(C2, Y["ded"], TW, 8.0, "Electrolyser", ["pure green H₂ (addition)"], "option", "pure")
    nuc = node(C0, Y["nuc"], BW, 8.0, "Nuclear plant", ["dedicated"], "option", "pink")
    ely_p = node(C2, Y["nuc"], TW, 8.0, "Electrolyser", ["pink H₂ (addition)"], "option", "pink")
    sto = node(C3, Y["sto"], DW, 10.0, "H₂ storage", ["salt caverns (addition, 2c)"], "option")
    electrolysers = [ely_g, ely, ely_p]
    arrow((ded["r"], ded["cy"]), (ely_g["l"], ded["cy"]))
    arrow((nuc["r"], nuc["cy"]), (ely_p["l"], nuc["cy"]))
    arrow((sto["cx"], sto["t"]), (dem["cx"], dem["b"]), both=True)
elif STORAGE_ENABLED:
    sto = node(C3, Y["sto"], DW, 10.0, "H₂ storage", ["salt caverns (2c)"], "added", "demand")
    arrow((sto["cx"], sto["t"]), (dem["cx"], dem["b"]), both=True)

# ---- arrows ----
arrow((gen["r"], ebus["cy"]), (ebus["l"], ebus["cy"]))
arrow((bat["cx"], bat["b"]), (ebus["cx"], ebus["t"]), both=True)
arrow((ebus["r"], ebus["cy"]), (ely["l"], ebus["cy"]))
xg = gas["r"] + 12.0
seg([gas["r"], xg], [gas["cy"], gas["cy"]])
path([(xg, gas["cy"]), (xg, smr["cy"]), (smr["l"], smr["cy"])])
path([(xg, gas["cy"]), (xg, ccs["cy"]), (ccs["l"], ccs["cy"])])
# every route feeds the hydrogen demand directly (no hydrogen bus): a collector line into the demand box
xd = dem["l"] - 4.0
for b in electrolysers + [smr, ccs]:
    seg([b["r"], xd], [b["cy"], b["cy"]])
seg([xd, xd], [ccs["cy"], electrolysers[0]["cy"]])
arrow((xd, dem["cy"]), (dem["l"], dem["cy"]))

# ---- legend: the line style says what a box is (two rows) ----
items = [("existing", "In the course model"), ("added", "Added for this study")]
if ADDITIONS:
    items.append(("option", "Addition (in every run)"))
items += [("bus", "Bus (carrier balance)"), ("limit", "Scenario constraint")]
pos = [(1.0, 7.0), (34.0, 7.0), (67.0, 7.0), (1.0, 2.2), (34.0, 2.2)]
for (kind, label), (x, y) in zip(items, pos):
    fc = GRAY if (kind == "added" and not COLOUR) else "white"
    ax.add_patch(Rectangle((x, y - 1.2), 3.4, 2.4, facecolor=fc, edgecolor=BLACK, linewidth=WIDTH[kind],
                           linestyle=LINE[kind]))
    ax.text(x + 4.6, y, label, va="center", fontsize=SS)
if COLOUR:
    xy = (67.0, 2.2) if ADDITIONS else (34.0, 2.2)
    ax.text(xy[0], xy[1], "Fill: the colour of the hydrogen", va="center", fontsize=SS, style="italic", color=INK2)

stem = "Figure3_model_structure_APA" + ("" if COLOUR else "_bw")
for ext in ("png", "pdf", "svg"):
    fig.savefig(Path(__file__).with_name(f"{stem}.{ext}"), dpi=400, facecolor="white", bbox_inches="tight",
                pad_inches=0.05)
print("saved", stem, "(with additions)" if ADDITIONS else "(without additions)")
