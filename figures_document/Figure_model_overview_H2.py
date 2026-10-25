# The course slide "Final model: overview", redrawn with our hydrogen extension as agreed with Francesco (14 October)
# and the group decisions of 15 October (base = 100 %). Drawn for the package it is in (energy_model/package.py):
# without additions, or with the additions (hydrogen storage, the pure green route and pink hydrogen, in every run).
#   teal          = added for hydrogen
#   dashed boxes  = processes and storage technologies, as in the course slide
#   dashed teal   = the additions (only in the package with additions): hydrogen storage, the pure green route
#                   (dedicated wind + solar) and pink hydrogen (dedicated nuclear)
# Hydrogen is a DEMAND (1.3 Mt/yr, fixed in every period, flat profile), not a secondary resource. Three end-use
# technologies feed it directly: SMR (grey), SMR + CCS (blue) and the electrolyser (green, grid electricity).
# Water is not modelled: the water-scarcity scenarios limit the electrolyser capacity in the capacity constraints
# (parameter 1: Base 100 % = the cost-optimal capacity, Medium 50 %, Scarce 0 %).
#
# Run:    pip install matplotlib   then   python Figure_model_overview_H2.py
# Output: Figure_model_overview_H2.png / .pdf / .svg (same folder).
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch, PathPatch, Polygon
from matplotlib.path import Path as MPath

plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Arial", "Liberation Sans", "Helvetica", "FreeSans", "DejaVu Sans"]
plt.rcParams["svg.fonttype"] = "none"          # text stays editable in the SVG

W, H = 1240, 860                               # drawing units (x to the right, y downwards)
FIG_W = 12.4                                   # inches
PT = FIG_W * 72 / W                            # points per drawing unit: font sizes and line widths below are in units

C = dict(fg="#1a2320", muted="#56635e", line="#3a4541", white="#ffffff",
         h2="#0b7a67", h2_fill="#dbf1ea", q="#b05f05",
         prim="#d3e9f6", prim_t="#1d6b94", emis="#dadddc", emis_arrow="#c3c8c6",
         sec="#a9caea", sec_t="#163f6b", pill_el="#edf5fd",
         dem="#fbe4d8", dem_t="#b8322a", prof="#f3dcee", prof_l="#9b4a8c",
         store="#d4edcb", store_t="#2c6522")
DASH = (0, (4, 2.6))


# ---------------------------------------------------------------- drawing helpers
def box(ax, x, y, w, h, fc, ec="none", lw=0.0, ls="-", r=4, z=1):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}", fc=fc, ec=ec,
                                lw=lw * PT, ls=ls, zorder=z))


def text(ax, x, y, s, size=12.5, weight="normal", color=C["fg"], ha="left", style="normal", z=6):
    """Text with its baseline at y (as in the course slide layout)."""
    return ax.text(x, y, s, fontsize=size * PT, fontweight=weight, color=color, ha=ha, va="baseline",
                   fontstyle=style, zorder=z)


def head(ax, p_from, p_to, color, size=10.0, z=4):
    """Filled arrow head with its tip at p_to."""
    (x0, y0), (x1, y1) = p_from, p_to
    d = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
    ux, uy = (x1 - x0) / d, (y1 - y0) / d
    bx, by = x1 - ux * size, y1 - uy * size
    px, py = -uy * size * 0.45, ux * size * 0.45
    ax.add_patch(Polygon([(x1, y1), (bx + px, by + py), (bx - px, by - py)], closed=True, fc=color, ec="none", zorder=z))


def line(ax, pts, color, lw=1.7, ls="-", start=False, end=True, size=10.0, z=3):
    """Orthogonal connector through pts, with arrow heads at the end (and/or start)."""
    (sx, sy), (ex, ey) = pts[0], pts[-1]
    pts = list(pts)
    if end:      # stop the line where the head starts, so dashes do not show through the head
        (ax_, ay_), (bx_, by_) = pts[-2], pts[-1]
        d = ((bx_ - ax_) ** 2 + (by_ - ay_) ** 2) ** 0.5
        pts[-1] = (bx_ - (bx_ - ax_) / d * size * 0.8, by_ - (by_ - ay_) / d * size * 0.8)
    if start:
        (ax_, ay_), (bx_, by_) = pts[1], pts[0]
        d = ((bx_ - ax_) ** 2 + (by_ - ay_) ** 2) ** 0.5
        pts[0] = (bx_ - (bx_ - ax_) / d * size * 0.8, by_ - (by_ - ay_) / d * size * 0.8)
    xs, ys = zip(*pts)
    ax.plot(xs, ys, color=color, lw=lw * PT, ls=ls, solid_joinstyle="miter", dash_joinstyle="miter",
            solid_capstyle="butt", dash_capstyle="butt", zorder=z)
    if end:
        head(ax, pts[-2] if len(pts) > 1 else (sx, sy), (ex, ey), color, size, z + 1)
    if start:
        head(ax, pts[1], (sx, sy), color, size, z + 1)


def chip(ax, x, y, w, h, label, dashed=False, size=12.0, weight="medium"):
    box(ax, x, y, w, h, C["h2_fill"], C["h2"], 1.3, DASH if dashed else "-", r=6, z=2)
    return text(ax, x + 12, y + h / 2 + size * 0.36, label, size, weight, C["h2"])


def bullet(ax, x, y, s, size=12.5):
    ax.add_patch(Circle((x - 8, y - 4), 2.4, fc=C["line"], ec="none", zorder=5))
    return text(ax, x, y, s, size)


def marker(ax, x, y, n):
    ax.add_patch(Circle((x, y), 10, fc=C["q"], ec="none", zorder=8))
    ax.text(x, y + 0.5, str(n), fontsize=11 * PT, fontweight="bold", color=C["white"], ha="center", va="center",
            zorder=9)


def _additions():
    """The package flag (energy_model/package.py), read as text so that this script needs only matplotlib."""
    f = Path(__file__).resolve().parents[1] / "energy_model" / "package.py"
    m = re.search(r"^ADDITIONS = (True|False)", f.read_text(), re.M) if f.exists() else None
    return bool(m and m.group(1) == "True")


ADDITIONS = _additions()
STORAGE_ENABLED = True


# ---------------------------------------------------------------- the figure
def draw():
    fig = plt.figure(figsize=(FIG_W, FIG_W * H / W))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(H, 0)
    ax.axis("off")
    fig.patch.set_facecolor(C["white"])

    # --- scenario layer
    text(ax, 620, 24, "Scenario assumptions and constraints", 15, "bold", ha="center")
    br = MPath([(30, 56), (30, 36), (50, 36), (1190, 36), (1210, 36), (1210, 56)],
               [MPath.MOVETO, MPath.CURVE3, MPath.CURVE3, MPath.LINETO, MPath.CURVE3, MPath.CURVE3])
    ax.add_patch(PathPatch(br, fc="none", ec=C["line"], lw=1.5 * PT, zorder=2))
    chip(ax, 30, 64, 560, 30, "(1) Water → electrolyser capacity ≤ Base 100 / Medium 50 / Scarce 0 % of cost-optimal",
         weight="bold", size=11.6)
    chip(ax, 600, 64, 320, 30, "CO₂ (ETS1, ETS2) and gas prices per period")
    chip(ax, 930, 64, 280, 30, "Caps: CO₂ storage, build rates")
    chip(ax, 30, 102, 560, 30, "(2a) Electrolyser cost or subsidy · (2b) CO₂ price paths")
    chip(ax, 600, 102, 610, 30, "(2c) H₂ storage cost · (3a–c) Battery cost, power and duration"
         if STORAGE_ENABLED else "(3a–c) Battery cost, power and duration · green levers")

    # --- emissions
    box(ax, 400, 154, 380, 68, C["emis"])
    text(ax, 590, 175, "Emissions", 13.5, "bold", ha="center")
    text(ax, 590, 193, "Atmospheric CO₂ · Stored CO₂", ha="center")
    text(ax, 590, 212, "+ SMR CO₂ · CCS storage limited to 10 / 22 / 25 Mt/yr", 11.5, "medium", C["h2"], ha="center")
    for x in (440, 700):
        ax.add_patch(Polygon([(x - 5, 262), (x - 5, 239), (x - 12, 239), (x, 226), (x + 12, 239), (x + 5, 239),
                              (x + 5, 262)], closed=True, fc=C["emis_arrow"], ec="none", zorder=2))

    # --- fuels used directly (primary resources -> end-use technologies)
    line(ax, [(250, 246), (760, 246), (760, 261)], C["line"])
    text(ax, 262, 240, "fuels used directly", 11, color=C["muted"])
    text(ax, 470, 240, "+ gas for SMR", 11, "medium", C["h2"])

    # --- primary resources
    box(ax, 30, 262, 220, 230, C["prim"])
    text(ax, 56, 288, "Primary resources", 13.5, "bold", C["prim_t"])
    for i, s in enumerate(["Natural gas", "Biomass", "Wind onshore", "Wind offshore", "Solar radiation", "Uranium",
                           "Gasoline"]):
        bullet(ax, 68, 314 + 22 * i, s)
    ax.plot([52, 47, 47, 52], [348, 348, 406, 406], color=C["prof_l"], lw=1.6 * PT, zorder=3)
    line(ax, [(250, 372), (299, 372)], C["line"])

    # --- conversion processes
    box(ax, 300, 262, 280, 230, "none", C["fg"], 1.3, DASH, r=14)
    text(ax, 440, 284, "Conversion processes", 13.5, "bold", ha="center")
    text(ax, 440, 312, "Gas, biomass and nuclear plants", ha="center")
    text(ax, 440, 332, "Wind and solar parks", ha="center")
    if ADDITIONS:
        box(ax, 314, 420, 252, 56, C["h2_fill"], C["h2"], 1.3, DASH, r=6, z=2)
        text(ax, 326, 441, "Dedicated plants for H₂ only:", 11.5, "bold", C["h2"])
        text(ax, 326, 462, "wind + solar (pure green), nuclear (pink)", 11.0, "medium", C["h2"])
        line(ax, [(566, 448), (654, 448)], C["h2"], 1.7, ls=DASH, size=10)

    # --- end-use technologies
    box(ax, 640, 262, 240, 230, "none", C["fg"], 1.3, DASH, r=14)
    text(ax, 760, 284, "End-use technologies", 13.5, "bold", ha="center")
    text(ax, 760, 312, "Gas boilers, heat pumps", ha="center")
    text(ax, 760, 332, "Petrol and electric cars", ha="center")
    text(ax, 760, 352, "Furnaces, machinery", ha="center")
    chip(ax, 655, 362, 210, 24, "SMR (grey): existing + new", size=11.5)
    chip(ax, 655, 390, 210, 24, "SMR + CCS (blue)", size=11.5)
    chip(ax, 655, 418, 210, 24, "Electrolyser (green, grid)", size=11.5)
    if ADDITIONS:
        chip(ax, 655, 446, 210, 36, "", dashed=True)
        text(ax, 667, 461, "Electrolysers: pure green,", 11.5, "medium", C["h2"])
        text(ax, 667, 476, "pink (additions)", 11.5, "medium", C["h2"])
    line(ax, [(880, 340), (929, 340)], C["line"])
    line(ax, [(880, 445), (947, 445)], C["h2"], 2.2, size=11)

    # --- demands
    box(ax, 930, 154, 280, 354, C["dem"])
    text(ax, 950, 180, "Demands", 14, "bold", C["dem_t"])
    text(ax, 950, 208, "Buildings", weight="bold")
    bullet(ax, 970, 229, "Residential electricity")
    bullet(ax, 970, 249, "Residential heat")
    text(ax, 950, 280, "Transportation", weight="bold")
    bullet(ax, 970, 301, "Passenger cars")
    text(ax, 950, 332, "Industry", weight="bold")
    bullet(ax, 970, 353, "Industrial machinery")
    bullet(ax, 970, 373, "High-temperature")
    text(ax, 970, 390, "industrial processes")
    box(ax, 948, 412, 244, 76, C["h2_fill"], C["h2"], 1.3, r=6, z=2)
    text(ax, 962, 434, "Industrial hydrogen", weight="bold")
    text(ax, 962, 454, "1.3 Mt/yr, fixed in every period", 11.5, "medium", C["h2"])
    text(ax, 962, 474, "feedstock: refineries, ammonia", 11.5, "medium", C["h2"])

    # --- secondary resources
    box(ax, 300, 528, 280, 122, C["sec"])
    text(ax, 360, 586, "Secondary", 13.5, "bold", C["sec_t"], ha="center")
    text(ax, 360, 602, "resources", 13.5, "bold", C["sec_t"], ha="center")
    box(ax, 450, 572, 115, 40, C["pill_el"], C["sec_t"], 1.2, r=20, z=2)
    text(ax, 507.5, 597, "Electricity", 13.5, "bold", ha="center")
    line(ax, [(507, 492), (507, 571)], C["line"])
    text(ax, 513, 512, "electricity", 11, color=C["muted"])
    line(ax, [(565, 592), (700, 592), (700, 493)], C["line"])
    text(ax, 706, 562, "+ power for", 11, "medium", C["h2"])
    text(ax, 706, 578, "electrolysers", 11, "medium", C["h2"])

    # --- storage
    line(ax, [(507, 612), (507, 671)], C["line"], start=True)
    box(ax, 450, 672, 115, 32, C["white"], C["fg"], 1.2, (0, (3, 2.2)), r=10, z=2)
    text(ax, 507.5, 693, "Batteries", ha="center")
    box(ax, 448, 710, 120, 22, C["store"], r=3)
    text(ax, 507.5, 725, "Electricity storage", 11, "medium", C["store_t"], ha="center")
    # hydrogen storage (2c): on the hydrogen balance, next to the industrial hydrogen demand
    if STORAGE_ENABLED:
        box(ax, 948, 540, 214, 44, C["h2_fill"], C["h2"], 1.3, DASH, r=6, z=2)
        text(ax, 960, 559, "H₂ storage", 12, "bold", C["h2"])
        text(ax, 960, 577, "salt caverns", 11.0, "medium", C["h2"])
        line(ax, [(1040, 539), (1040, 489)], C["h2"], 1.7, ls=DASH, start=True, size=10)

    # --- profiles and drivers
    box(ax, 30, 788, 220, 52, C["prof"])
    text(ax, 140, 808, "Hourly profiles", 13.5, "bold", ha="center")
    text(ax, 140, 828, "+ flat profile for H₂ demand", 11.5, "medium", C["h2"], ha="center")
    line(ax, [(30, 814), (18, 814), (18, 377), (46, 377)], C["prof_l"], 1.6, size=9)
    box(ax, 990, 788, 220, 52, C["prof"])
    text(ax, 1100, 808, "Macroeconomic drivers", 13.5, "bold", ha="center")
    text(ax, 1100, 828, "+ H₂ demand constant over time", 11.5, "medium", C["h2"], ha="center")
    line(ax, [(1170, 788), (1170, 509)], C["prof_l"], 1.6, size=9)

    # --- legend
    items = [("course", "Course model"), ("h2", "Added for hydrogen")] + (
        [("opt", "Addition (in every run of this package)")] if ADDITIONS else [])
    renderer = fig.canvas.get_renderer()
    labels = [text(ax, 0, 818, label, 12, color=C["muted"]) for _, label in items]
    widths = [t.get_window_extent(renderer).width * W / (FIG_W * fig.dpi) for t in labels]
    gap, sw = 30, 34                                   # space between items; swatch + its gap to the label
    x = 620 - (sum(widths) + len(items) * sw + (len(items) - 1) * gap) / 2
    for (kind, _), t, w in zip(items, labels, widths):
        if kind == "course":
            box(ax, x, 805, 26, 16, C["white"], C["line"], 1.3, r=3)
        elif kind == "h2":
            box(ax, x, 805, 26, 16, C["h2_fill"], C["h2"], 1.3, r=3)
        else:
            box(ax, x, 805, 26, 16, C["h2_fill"], C["h2"], 1.3, DASH, r=3)
        t.set_x(x + sw)
        x += sw + w + gap
    return fig, ax


def save(fig, stem, formats=("png", "pdf", "svg")):
    out = Path(__file__).resolve().parent
    for ext in formats:
        fig.savefig(out / f"{stem}.{ext}", dpi=400, facecolor="white")
    print("written", stem)


if __name__ == "__main__":
    fig, _ = draw()
    save(fig, "Figure_model_overview_H2")
    plt.close(fig)
