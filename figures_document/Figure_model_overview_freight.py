# Model overview of the freight study: the course slide "Final model: overview", as redrawn by the group for the
# hydrogen extension (Figure_model_overview_H2.py), with heavy-duty road freight added for the individual assignment.
#   grey/black   = course model
#   teal         = added for hydrogen (group)
#   blue         = added for freight (this study); dashed blue = realistic layer only
#   pink boxes   = outside drivers: hourly profiles, macroeconomic drivers and the water-scarcity driver
# Freight is a DEMAND (90 PJ of truck output in 2020, GDP driver with elasticity 0.6, hourly profile) served by six
# truck technologies: ICE truck, BET (urban / regional / long haul) and two hydrogen trucks (FCET, H2-ICE truck) that
# draw on the group's hydrogen routes. Water is an outside driver: drought-season quotas of the verdringingsreeks that
# tighten over time, with desalination as the backstop (water_scarcity='driver'; off in the other runs).
#
# Run from the package folder:  python figures_document/Figure_model_overview_freight.py
# Output: figures_document/Figure_model_overview_freight.png / .pdf / .svg
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, FancyBboxPatch, PathPatch, Polygon  # noqa: E402
from matplotlib.path import Path as MPath  # noqa: E402

plt.rcParams["font.family"] = "DejaVu Sans"     # ships with matplotlib; has the subscript and arrow glyphs
plt.rcParams["svg.fonttype"] = "none"           # text stays editable in the SVG

W, H = 1240, 905                               # drawing units (x to the right, y downwards)
FIG_W = 12.4                                   # inches
PT = FIG_W * 72 / W                            # points per drawing unit

C = dict(fg="#1a2320", muted="#56635e", line="#3a4541", white="#ffffff",
         h2="#0b7a67", h2_fill="#dbf1ea",
         fr="#1d5fa8", fr_fill="#e3effa",
         prim="#d3e9f6", prim_t="#1d6b94", emis="#dadddc", emis_arrow="#c3c8c6",
         sec="#a9caea", sec_t="#163f6b", pill_el="#edf5fd",
         dem="#fbe4d8", dem_t="#b8322a", prof="#f3dcee", prof_l="#9b4a8c",
         store="#d4edcb", store_t="#2c6522")
DASH = (0, (4, 2.6))


# ---------------------------------------------------------------- drawing helpers (as in the group's figure)
def box(ax, x, y, w, h, fc, ec="none", lw=0.0, ls="-", r=4, z=1):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}", fc=fc, ec=ec,
                                lw=lw * PT, ls=ls, zorder=z))


def text(ax, x, y, s, size=12.5, weight="normal", color=C["fg"], ha="left", z=6):
    """Text with its baseline at y."""
    return ax.text(x, y, s, fontsize=size * PT, fontweight=weight, color=color, ha=ha, va="baseline", zorder=z)


def head(ax, p_from, p_to, color, size=10.0, z=4):
    """Filled arrow head with its tip at p_to."""
    (x0, y0), (x1, y1) = p_from, p_to
    d = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
    ux, uy = (x1 - x0) / d, (y1 - y0) / d
    bx, by = x1 - ux * size, y1 - uy * size
    px, py = -uy * size * 0.45, ux * size * 0.45
    ax.add_patch(Polygon([(x1, y1), (bx + px, by + py), (bx - px, by - py)], closed=True, fc=color, ec="none",
                         zorder=z))


def line(ax, pts, color, lw=1.7, ls="-", start=False, end=True, size=10.0, z=3):
    """Orthogonal connector through pts, with arrow heads at the end (and/or start)."""
    pts = list(pts)
    (sx, sy), (ex, ey) = pts[0], pts[-1]
    if end:
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
        head(ax, pts[-2], (ex, ey), color, size, z + 1)
    if start:
        head(ax, pts[1], (sx, sy), color, size, z + 1)


def chip(ax, x, y, w, h, label, kind="h2", dashed=False, size=12.0, weight="medium"):
    """Rounded label box in the colour of an addition: kind 'h2' (teal) or 'fr' (freight blue)."""
    box(ax, x, y, w, h, C[f"{kind}_fill"], C[kind], 1.3, DASH if dashed else "-", r=6, z=2)
    return text(ax, x + 12, y + h / 2 + size * 0.36, label, size, weight, C[kind])


def bullet(ax, x, y, s, size=12.5, color=C["fg"]):
    ax.add_patch(Circle((x - 8, y - 4), 2.4, fc=color, ec="none", zorder=5))
    return text(ax, x, y, s, size, color=color)


# ---------------------------------------------------------------- the figure
def draw():
    fig = plt.figure(figsize=(FIG_W, FIG_W * H / W))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(H, 0)
    ax.axis("off")
    fig.patch.set_facecolor(C["white"])

    # --- scenario layer: the assignment's axes, the carbon price, the realistic layer
    text(ax, 620, 24, "Scenario assumptions and constraints", 15, "bold", ha="center")
    br = MPath([(30, 56), (30, 36), (50, 36), (1190, 36), (1210, 36), (1210, 56)],
               [MPath.MOVETO, MPath.CURVE3, MPath.CURVE3, MPath.LINETO, MPath.CURVE3, MPath.CURVE3])
    ax.add_patch(PathPatch(br, fc="none", ec=C["line"], lw=1.5 * PT, zorder=2))
    chip(ax, 30, 64, 330, 30, "X: BET CAPEX and VOM (constant / decrease)", "fr", weight="bold", size=11.6)
    chip(ax, 370, 64, 240, 30, "Y: fuel price (moderate / sharp)", "fr", weight="bold", size=11.6)
    chip(ax, 620, 64, 340, 30, "CO₂ price: ETS1 + ETS2 (moderate; central, high)", "h2", size=11.6)
    chip(ax, 970, 64, 240, 30, "Caps: CO₂ storage, build rates", "h2", size=11.6)
    chip(ax, 30, 102, 640, 30, "Realistic layer: EU CO₂ standards, truck toll, AanZET, RED III, RFNBO obligation, "
         "OWE, SWiM", "fr", dashed=True, size=11.2)
    chip(ax, 680, 102, 530, 30, "Market: ramp-up, H₂-truck availability, BET duty cycles, heavy segment", "fr",
         dashed=True, size=11.2)

    # --- emissions
    box(ax, 400, 152, 380, 84, C["emis"])
    text(ax, 590, 173, "Emissions", 13.5, "bold", ha="center")
    text(ax, 590, 191, "Atmospheric CO₂ · Stored CO₂", ha="center")
    text(ax, 590, 209, "+ SMR CO₂ · CCS storage limited to 10 / 22 / 25 Mt/yr", 11.5, "medium", C["h2"], ha="center")
    text(ax, 590, 227, "+ truck CO₂ (0.25 t/MWh diesel; ETS2 on road fuels)", 11.5, "medium", C["fr"], ha="center")
    for x in (440, 700):
        ax.add_patch(Polygon([(x - 5, 262), (x - 5, 252), (x - 12, 252), (x, 240), (x + 12, 252), (x + 5, 252),
                              (x + 5, 262)], closed=True, fc=C["emis_arrow"], ec="none", zorder=2))

    # --- fuels used directly (primary resources -> end-use technologies)
    line(ax, [(250, 246), (380, 246)], C["line"], end=False)
    line(ax, [(800, 246), (860, 246), (860, 261)], C["line"])
    text(ax, 262, 240, "fuels used directly", 11, color=C["muted"])
    text(ax, 792, 222, "+ gas for SMR", 11, "medium", C["h2"])
    text(ax, 792, 240, "+ diesel for trucks", 11, "medium", C["fr"])
    ax.plot([380, 400], [246, 246], color=C["line"], lw=1.7 * PT, zorder=0.5)
    ax.plot([780, 800], [246, 246], color=C["line"], lw=1.7 * PT, zorder=0.5)

    # --- primary resources
    box(ax, 30, 262, 220, 230, C["prim"])
    text(ax, 56, 288, "Primary resources", 13.5, "bold", C["prim_t"])
    for i, s in enumerate(["Natural gas", "Biomass", "Wind onshore", "Wind offshore", "Solar radiation", "Uranium",
                           "Gasoline / diesel"]):
        bullet(ax, 68, 314 + 22 * i, s)
    ax.plot([52, 47, 47, 52], [348, 348, 406, 406], color=C["prof_l"], lw=1.6 * PT, zorder=3)
    line(ax, [(250, 372), (299, 372)], C["line"])

    # --- conversion processes
    box(ax, 300, 262, 280, 230, "none", C["fg"], 1.3, DASH, r=14)
    text(ax, 440, 284, "Conversion processes", 13.5, "bold", ha="center")
    text(ax, 440, 312, "Gas, biomass and nuclear plants", ha="center")
    text(ax, 440, 332, "Wind and solar parks", ha="center")

    # --- end-use technologies (course, freight trucks, hydrogen routes)
    box(ax, 640, 262, 240, 278, "none", C["fg"], 1.3, DASH, r=14)
    text(ax, 760, 284, "End-use technologies", 13.5, "bold", ha="center")
    text(ax, 760, 308, "Gas boilers, heat pumps", ha="center")
    text(ax, 760, 326, "Petrol and electric cars", ha="center")
    text(ax, 760, 344, "Furnaces, machinery", ha="center")
    chip(ax, 652, 356, 216, 40, "", "fr")
    text(ax, 664, 373, "ICE truck · BET (urban*,", 11.5, "medium", C["fr"])
    text(ax, 664, 389, "regional, long haul*)", 11.5, "medium", C["fr"])
    chip(ax, 652, 402, 216, 24, "FCET · H₂-ICE truck", "fr", size=11.5)
    chip(ax, 652, 440, 216, 24, "SMR (grey): existing + new", size=11.5)
    chip(ax, 652, 470, 216, 24, "SMR + CCS (blue)", size=11.5)
    chip(ax, 652, 500, 216, 24, "Electrolyser (green, grid)", size=11.5)
    line(ax, [(645, 452), (645, 436), (651, 436), (651, 426)], C["h2"], 1.5, size=8)       # hydrogen to the trucks
    text(ax, 870, 436, "H₂ for trucks", 10.5, "medium", C["h2"], ha="right")
    line(ax, [(880, 300), (929, 300)], C["line"])
    line(ax, [(880, 380), (905, 380), (905, 336), (947, 336)], C["fr"], 2.2, size=11)
    line(ax, [(880, 482), (947, 482)], C["h2"], 2.2, size=11)

    # --- demands
    box(ax, 930, 154, 280, 392, C["dem"])
    text(ax, 950, 180, "Demands", 14, "bold", C["dem_t"])
    text(ax, 950, 206, "Buildings", weight="bold")
    bullet(ax, 970, 227, "Residential electricity")
    bullet(ax, 970, 247, "Residential heat")
    text(ax, 950, 276, "Transportation", weight="bold")
    bullet(ax, 970, 297, "Passenger cars")
    box(ax, 948, 308, 244, 56, C["fr_fill"], C["fr"], 1.3, r=6, z=2)
    text(ax, 962, 330, "Freight transport (heavy road)", weight="bold")
    text(ax, 962, 350, "90 PJ in 2020 (truck output)", 11.5, "medium", C["fr"])
    text(ax, 950, 390, "Industry", weight="bold")
    bullet(ax, 970, 411, "Industrial machinery")
    bullet(ax, 970, 431, "High-temperature")
    text(ax, 970, 448, "industrial processes")
    box(ax, 948, 458, 244, 76, C["h2_fill"], C["h2"], 1.3, r=6, z=2)
    text(ax, 962, 480, "Industrial hydrogen", weight="bold")
    text(ax, 962, 500, "1.3 Mt/yr, fixed in every period", 11.5, "medium", C["h2"])
    text(ax, 962, 520, "feedstock: refineries, ammonia", 11.5, "medium", C["h2"])

    # --- secondary resources
    box(ax, 300, 560, 280, 122, C["sec"])
    text(ax, 360, 618, "Secondary", 13.5, "bold", C["sec_t"], ha="center")
    text(ax, 360, 634, "resources", 13.5, "bold", C["sec_t"], ha="center")
    box(ax, 450, 604, 115, 40, C["pill_el"], C["sec_t"], 1.2, r=20, z=2)
    text(ax, 507.5, 629, "Electricity", 13.5, "bold", ha="center")
    line(ax, [(507, 492), (507, 603)], C["line"])
    text(ax, 513, 512, "electricity", 11, color=C["muted"])
    line(ax, [(565, 624), (700, 624), (700, 541)], C["line"])
    text(ax, 706, 574, "+ power for", 11, "medium", C["h2"])
    text(ax, 706, 590, "electrolysers", 11, "medium", C["h2"])
    text(ax, 706, 608, "+ charging BETs", 11, "medium", C["fr"])

    # --- storage
    line(ax, [(507, 644), (507, 703)], C["line"], start=True)
    box(ax, 450, 704, 115, 32, C["white"], C["fg"], 1.2, (0, (3, 2.2)), r=10, z=2)
    text(ax, 507.5, 725, "Batteries", ha="center")
    box(ax, 448, 742, 120, 22, C["store"], r=3)
    text(ax, 507.5, 757, "Electricity storage", 11, "medium", C["store_t"], ha="center")
    box(ax, 948, 576, 214, 44, C["h2_fill"], C["h2"], 1.3, DASH, r=6, z=2)
    text(ax, 960, 595, "H₂ storage", 12, "bold", C["h2"])
    text(ax, 960, 613, "salt caverns", 11.0, "medium", C["h2"])
    line(ax, [(1040, 575), (1040, 535)], C["h2"], 1.7, ls=DASH, start=True, size=10)

    # --- outside drivers: hourly profiles, the water-scarcity driver, macroeconomic drivers
    box(ax, 30, 790, 300, 76, C["prof"])
    text(ax, 180, 810, "Hourly profiles", 13.5, "bold", ha="center")
    text(ax, 180, 830, "+ flat profile for H₂ demand", 11.5, "medium", C["h2"], ha="center")
    text(ax, 180, 848, "+ freight: weekday peak, night, weekend;", 11.0, "medium", C["fr"], ha="center")
    text(ax, 180, 862, "Sunday-ban and night-ban variants", 11.0, "medium", C["fr"], ha="center")
    line(ax, [(30, 828), (18, 828), (18, 377), (46, 377)], C["prof_l"], 1.6, size=9)

    box(ax, 610, 790, 300, 76, C["prof"], C["fr"], 1.3, DASH, r=4)
    text(ax, 760, 810, "Water-scarcity driver", 13.5, "bold", ha="center")
    text(ax, 760, 830, "verdringingsreeks quotas in dry summers:", 11.0, "medium", C["fr"], ha="center")
    text(ax, 760, 846, "1-in-20 (2030, 2040), 2018-type (2050);", 11.0, "medium", C["fr"], ha="center")
    text(ax, 760, 862, "derated river cooling; desalination €1.4/m³", 11.0, "medium", C["fr"], ha="center")
    line(ax, [(860, 790), (860, 541)], C["prof_l"], 1.6, size=9)
    text(ax, 866, 700, "water for", 10.5, color=C["prof_l"])
    text(ax, 866, 715, "electrolysis,", 10.5, color=C["prof_l"])
    text(ax, 866, 730, "cooling", 10.5, color=C["prof_l"])

    box(ax, 950, 790, 260, 76, C["prof"])
    text(ax, 1080, 810, "Macroeconomic drivers", 13.5, "bold", ha="center")
    text(ax, 1080, 830, "+ H₂ demand constant over time", 11.5, "medium", C["h2"], ha="center")
    text(ax, 1080, 850, "+ freight demand ∝ GDP⁰·⁶", 11.5, "medium", C["fr"], ha="center")
    line(ax, [(1170, 790), (1170, 547)], C["prof_l"], 1.6, size=9)

    # --- legend
    items = [("course", "Course model"), ("h2", "Added for hydrogen (group)"), ("fr", "Added for freight"),
             ("frd", "Freight, realistic layer only (*)")]
    renderer = fig.canvas.get_renderer()
    labels = [text(ax, 0, 892, label, 12, color=C["muted"]) for _, label in items]
    widths = [t.get_window_extent(renderer).width * W / (FIG_W * fig.dpi) for t in labels]
    gap, sw = 30, 34
    x = 620 - (sum(widths) + len(items) * sw + (len(items) - 1) * gap) / 2
    for (kind, _), t, w in zip(items, labels, widths):
        if kind == "course":
            box(ax, x, 879, 26, 16, C["white"], C["line"], 1.3, r=3)
        elif kind == "frd":
            box(ax, x, 879, 26, 16, C["fr_fill"], C["fr"], 1.3, DASH, r=3)
        else:
            box(ax, x, 879, 26, 16, C[f"{kind}_fill"], C[kind], 1.3, r=3)
        t.set_x(x + sw)
        x += sw + w + gap
    return fig, ax


def save(fig, stem, formats=("png", "pdf", "svg")):
    out = Path(__file__).resolve().parent
    for ext in formats:
        fig.savefig(out / f"{stem}.{ext}", dpi=400 if ext == "png" else None, facecolor="white")
    print("written", stem)


if __name__ == "__main__":
    fig, _ = draw()
    save(fig, "Figure_model_overview_freight")
    plt.close(fig)
