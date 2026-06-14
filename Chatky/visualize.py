"""
Visualize a chatka assignment solution as a multi-page PDF.

Page 1 – Summary stats + building overview table
Page 2 – Male buildings (cards with participants)
Page 3 – Female buildings (cards with participants)
Page 4 – Preference graph: nodes coloured by building, edges = preferences,
          bold edges = satisfied (same building)

Usage:
  python visualize.py [solution.json] [output.pdf]
  (defaults: solution.json → solution.pdf)
"""

import json
import math
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyBboxPatch

# ── load data ────────────────────────────────────────────────────────────────

sol_path = sys.argv[1] if len(sys.argv) > 1 else "solution.json"
pdf_path = sys.argv[2] if len(sys.argv) > 2 else "solution.pdf"

with open(sol_path, encoding="utf-8") as f:
    sol = json.load(f)

with open("graph.json", encoding="utf-8") as f:
    gdata = json.load(f)

buildings   = sol["buildings"]
p2b         = sol["participants"]      # name → building id
sat_edges   = {(e["source"], e["target"]) for e in sol["satisfied_edges"]}
all_edges   = gdata["edges"]
stats       = sol["stats"]

# ── colour palettes ───────────────────────────────────────────────────────────

M_CARD   = "#d6eaf8"   # light blue
F_CARD   = "#fde8f0"   # light pink
M_HEADER = "#2980b9"
F_HEADER = "#e91e8c"
SAT_EDGE = "#27ae60"   # green = preference satisfied
UNSAT_EDGE = "#d5d8dc"  # grey = unsatisfied
FONT     = "DejaVu Sans"

# deterministic building sort
def bld_sort_key(b):
    if b.isdigit():
        return (0, int(b))
    if b.startswith("n"):
        return (1, int(b[1:]))
    if b.startswith("m"):
        return (2, int(b[1:]))
    return (3, b)

male_blds   = sorted([b for b, i in buildings.items() if i["gender"] == "M"], key=bld_sort_key)
female_blds = sorted([b for b, i in buildings.items() if i["gender"] == "F"], key=bld_sort_key)

# colour per building (for the graph page) – use tab20
import matplotlib.cm as cm
all_blds_sorted = sorted(buildings.keys(), key=bld_sort_key)
cmap = plt.colormaps["tab20"].resampled(len(all_blds_sorted))
bld_color = {b: cmap(i) for i, b in enumerate(all_blds_sorted)}

# ── helpers ───────────────────────────────────────────────────────────────────

def short(name: str) -> str:
    """'Karásková Laura' → 'L. Karásková'"""
    parts = name.strip().split()
    if len(parts) >= 2:
        return f"{parts[-1][0]}. {parts[0]}"
    return name


def draw_building_card(ax, bld_id: str, info: dict, show_satisfied: bool = True):
    """Draw one building card on the given Axes."""
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    g = info["gender"]
    card_color  = M_CARD  if g == "M" else F_CARD
    hdr_color   = M_HEADER if g == "M" else F_HEADER

    # card background
    ax.add_patch(FancyBboxPatch((0.02, 0.02), 0.96, 0.96,
                                boxstyle="round,pad=0.02",
                                facecolor=card_color, edgecolor=hdr_color,
                                linewidth=1.5, zorder=0))

    # header bar
    ax.add_patch(FancyBboxPatch((0.02, 0.80), 0.96, 0.18,
                                boxstyle="round,pad=0.02",
                                facecolor=hdr_color, edgecolor=hdr_color,
                                linewidth=0, zorder=1))

    gender_sym = "♂" if g == "M" else "♀"
    ax.text(0.50, 0.89,
            f"Chatka {bld_id}  {gender_sym}  {info['count']}/{info['capacity']}",
            ha="center", va="center", fontsize=8, fontweight="bold",
            color="white", zorder=2)
    ax.text(0.50, 0.81,
            f"věk {info['age_min']}–{info['age_max']}",
            ha="center", va="center", fontsize=6.5, color="white", zorder=2)

    # participant list
    names = info["participants"]
    n     = len(names)
    y_start = 0.74
    step    = min(0.072, 0.70 / max(n, 1))

    for i, p in enumerate(names):
        pid   = p["id"]
        in_bld = p2b.get(pid, "")
        # check if this person has any satisfied pref in this building
        has_friend = any(
            (pid, q["id"]) in sat_edges or (q["id"], pid) in sat_edges
            for q in names if q["id"] != pid
        )
        y = y_start - i * step
        dot_color = SAT_EDGE if has_friend else "#aab7b8"
        ax.plot(0.08, y, "o", color=dot_color, markersize=4, zorder=3)
        ax.text(0.14, y, short(pid),
                va="center", fontsize=6, color="#1a1a1a", zorder=3)

    # occupancy bar at bottom
    fill = info["count"] / info["capacity"]
    ax.add_patch(plt.Rectangle((0.04, 0.04), 0.92 * fill, 0.04,
                                facecolor=hdr_color, alpha=0.6, zorder=2))
    ax.add_patch(plt.Rectangle((0.04, 0.04), 0.92, 0.04,
                                facecolor="none", edgecolor=hdr_color,
                                linewidth=1, zorder=2))


# ═══════════════════════════════════════════════════════════════════════════════
# PDF
# ═══════════════════════════════════════════════════════════════════════════════

strategy = sol.get("strategy", {})
strategy_name = strategy.get("name", "")
sol_index = strategy.get("index", "")
title_suffix = f" – S{sol_index}: {strategy_name}" if strategy_name else ""

with PdfPages(pdf_path) as pdf:

    # ── PAGE 1: SUMMARY ──────────────────────────────────────────────────────

    fig, ax = plt.subplots(figsize=(11.69, 8.27))
    ax.axis("off")
    fig.patch.set_facecolor("#f8f9fa")

    ax.text(0.5, 0.95, f"Přidělení dětí do chatek – přehled{title_suffix}",
            ha="center", va="top", fontsize=20, fontweight="bold",
            color="#2c3e50", transform=ax.transAxes)

    # stats boxes
    stat_items = [
        ("Dětí celkem",          stats["total_participants"]),
        ("Přiděleno",            stats["assigned"]),
        ("Nepřiděleno",          stats["unassigned_count"]),
        ("Chatky obsazeny",      len(buildings)),
        ("Splněných přání",      f"{stats['satisfied_preference_edges']}/{stats['total_preference_edges']}"),
        ("Dětí s kamarádem",     f"{stats['participants_with_friend']}/{stats['assigned']}"),
        ("Vzájemných párů",      stats["mutual_pairs_satisfied"]),
    ]

    box_w, box_h = 0.12, 0.14
    x_positions  = [0.08 + i * 0.135 for i in range(len(stat_items))]
    for x, (label, val) in zip(x_positions, stat_items):
        ax.add_patch(FancyBboxPatch((x - box_w/2, 0.73), box_w, box_h,
                                    boxstyle="round,pad=0.01",
                                    facecolor="white", edgecolor="#2980b9",
                                    linewidth=1.5,
                                    transform=ax.transAxes))
        ax.text(x, 0.73 + box_h * 0.68, str(val),
                ha="center", va="center", fontsize=16, fontweight="bold",
                color="#2980b9", transform=ax.transAxes)
        ax.text(x, 0.73 + box_h * 0.22, label,
                ha="center", va="center", fontsize=6.5, color="#555",
                transform=ax.transAxes, wrap=True)

    # building overview table
    ax.text(0.5, 0.68, "Přehled chatek",
            ha="center", fontsize=13, fontweight="bold",
            color="#2c3e50", transform=ax.transAxes)

    col_headers = ["Chatka", "Kapacita", "Obsazeno", "Pohlaví", "Věk min", "Věk max", "Rozdíl věků"]
    col_xs      = [0.08, 0.20, 0.32, 0.44, 0.56, 0.68, 0.82]
    row_height  = 0.032
    y0          = 0.63

    for cx, hdr in zip(col_xs, col_headers):
        ax.text(cx, y0, hdr, ha="center", va="center",
                fontsize=8, fontweight="bold", color="white",
                transform=ax.transAxes,
                bbox=dict(facecolor="#2c3e50", edgecolor="none",
                          boxstyle="round,pad=0.3"))

    for row_i, bld_id in enumerate(sorted(buildings.keys(), key=bld_sort_key)):
        info  = buildings[bld_id]
        y     = y0 - (row_i + 1) * row_height
        row_bg = "#eaf2ff" if info["gender"] == "M" else "#fde8f0"
        ax.add_patch(plt.Rectangle((0.03, y - row_height * 0.4), 0.94, row_height,
                                    facecolor=row_bg, edgecolor="none",
                                    transform=ax.transAxes, zorder=0))
        vals = [bld_id, info["capacity"], info["count"],
                "♂" if info["gender"] == "M" else "♀",
                info["age_min"], info["age_max"], info["age_gap"]]
        for cx, v in zip(col_xs, vals):
            ax.text(cx, y, str(v), ha="center", va="center",
                    fontsize=7.5, color="#1a1a1a", transform=ax.transAxes)

    # legend
    legend_patches = [
        mpatches.Patch(facecolor=M_CARD, edgecolor=M_HEADER, label="Chlapci"),
        mpatches.Patch(facecolor=F_CARD, edgecolor=F_HEADER, label="Dívky"),
    ]
    ax.legend(handles=legend_patches, loc="lower right", fontsize=9, framealpha=0.9)

    plt.tight_layout()
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)

    # ── PAGES 2 & 3: BUILDING CARDS ──────────────────────────────────────────

    for gender_label, bld_list in [("Chlapci ♂", male_blds), ("Dívky ♀", female_blds)]:
        n_cards  = len(bld_list)
        n_cols   = 4
        n_rows   = math.ceil(n_cards / n_cols)

        fig = plt.figure(figsize=(11.69, max(8.27, n_rows * 3.0)))
        fig.patch.set_facecolor("#f8f9fa")
        fig.suptitle(f"Chatky – {gender_label}", fontsize=16,
                     fontweight="bold", color="#2c3e50", y=0.98)

        for idx, bld_id in enumerate(bld_list):
            row = idx // n_cols
            col = idx  % n_cols
            ax  = fig.add_subplot(n_rows, n_cols, idx + 1)
            draw_building_card(ax, bld_id, buildings[bld_id])

        plt.tight_layout(rect=[0, 0, 1, 0.96])
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

    # ── PAGE 4: PREFERENCE GRAPH ──────────────────────────────────────────────

    import networkx as nx

    G = nx.DiGraph()
    node_data = {p["id"]: p for p in gdata["nodes"]}
    for p in gdata["nodes"]:
        G.add_node(p["id"])
    for e in all_edges:
        G.add_edge(e["source"], e["target"])

    # layout: group nodes by building, arranged in circles around building centres
    n_blds      = len(all_blds_sorted)
    bld_centres = {}
    cols_layout = 6
    for bi, bld_id in enumerate(all_blds_sorted):
        r = bi // cols_layout
        c = bi  % cols_layout
        bld_centres[bld_id] = (c * 2.2, -r * 2.2)

    pos = {}
    for bld_id, info in buildings.items():
        cx, cy = bld_centres[bld_id]
        members = info["participants"]
        n = len(members)
        for j, p in enumerate(members):
            angle = 2 * math.pi * j / max(n, 1)
            r     = 0.55 if n > 1 else 0
            pos[p["id"]] = (cx + r * math.cos(angle), cy + r * math.sin(angle))

    fig, ax = plt.subplots(figsize=(22, 14))
    fig.patch.set_facecolor("#f0f4f8")
    ax.set_facecolor("#f0f4f8")
    ax.set_title("Graf přání – uzly obarveny podle chatky\n"
                 "zelená šipka = přání splněno (ve stejné chatce)",
                 fontsize=13, color="#2c3e50", pad=10)

    # draw building halos
    for bld_id, info in buildings.items():
        cx, cy = bld_centres[bld_id]
        circle = plt.Circle((cx, cy), 0.85, color=bld_color[bld_id],
                             alpha=0.18, zorder=0)
        ax.add_patch(circle)
        ax.text(cx, cy - 0.92, f"Chatka {bld_id}",
                ha="center", va="top", fontsize=6, color="#444",
                fontweight="bold")

    # draw edges
    for e in all_edges:
        src, tgt = e["source"], e["target"]
        if src not in pos or tgt not in pos:
            continue
        x0, y0_e = pos[src]
        x1, y1_e = pos[tgt]
        is_sat = (src, tgt) in sat_edges
        color  = SAT_EDGE if is_sat else UNSAT_EDGE
        lw     = 1.2 if is_sat else 0.4
        alpha  = 0.85 if is_sat else 0.3
        ax.annotate("",
                    xy=(x1, y1_e), xytext=(x0, y0_e),
                    arrowprops=dict(arrowstyle="-|>", color=color,
                                   lw=lw, alpha=alpha,
                                   connectionstyle="arc3,rad=0.12"))

    # draw nodes
    for pid, (x, y) in pos.items():
        bld = p2b.get(pid, "")
        c   = bld_color.get(bld, "grey")
        g   = node_data[pid]["gender"]
        marker = "o" if g == "F" else "s"
        ax.plot(x, y, marker, color=c, markersize=6,
                markeredgecolor="white", markeredgewidth=0.5, zorder=3)
        ax.text(x, y + 0.15, short(pid),
                ha="center", va="bottom", fontsize=4.5, color="#222", zorder=4)

    # legend patches for buildings
    legend_patches = [
        mpatches.Patch(color=bld_color[b],
                       label=f"Chatka {b} ({buildings[b]['gender']}, věk {buildings[b]['age_min']}-{buildings[b]['age_max']})")
        for b in all_blds_sorted if b in buildings
    ]
    ax.legend(handles=legend_patches, loc="lower left",
              fontsize=5.5, ncol=3, framealpha=0.9,
              title="Chatky", title_fontsize=7)

    ax.set_aspect("equal")
    ax.axis("off")
    plt.tight_layout()
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)

    # ── metadata ──────────────────────────────────────────────────────────────
    d = pdf.infodict()
    d["Title"]   = f"Přidělení dětí do chatek{title_suffix}"
    d["Author"]  = "visualize.py"
    d["Subject"] = "Chatka assignment solution"

print(f"Written {pdf_path}")
