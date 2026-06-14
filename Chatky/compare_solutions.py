"""
Compare all solutions in solutions/ and produce a comparison PDF.
"""

import json
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyBboxPatch
import matplotlib.gridspec as gridspec
import numpy as np

# ── load summary and all solutions ───────────────────────────────────────────

with open("solutions/summary.json", encoding="utf-8") as f:
    summary = json.load(f)

solutions = []
for entry in summary:
    path = f"solutions/solution_{entry['index']}.json"
    with open(path, encoding="utf-8") as f:
        solutions.append(json.load(f))

with open("graph.json", encoding="utf-8") as f:
    gdata = json.load(f)
all_edges = gdata["edges"]

N = len(summary)
COLORS = plt.colormaps["tab10"].resampled(N)
BAR_COLORS = [COLORS(i) for i in range(N)]

# short labels
labels = [f"S{s['index']}: {s['name'].replace('Age-greedy', 'Age').replace('Preference-cluster','Pref-cluster')[:35]}"
          for s in summary]
short_labels = [f"S{s['index']}" for s in summary]

# ── metrics ───────────────────────────────────────────────────────────────────

sat_edges   = [s["sat_edges"]   for s in summary]
pct_edges   = [s["pct_edges"]   for s in summary]
with_friend = [s["with_friend"] for s in summary]
pct_friend  = [s["pct_friend"]  for s in summary]
mutual      = [s["mutual_pairs"] for s in summary]
total_e     = summary[0]["total_edges"]
total_p     = summary[0]["assigned"]

best_idx = max(range(N), key=lambda i: (sat_edges[i], mutual[i]))

def bld_sort_key(b):
    if b.isdigit():     return (0, int(b))
    if b.startswith("n"): return (1, int(b[1:]))
    if b.startswith("m"): return (2, int(b[1:]))
    return (3, b)

# ═══════════════════════════════════════════════════════════════════════════════
# PDF
# ═══════════════════════════════════════════════════════════════════════════════

with PdfPages("solutions/comparison.pdf") as pdf:

    # ── PAGE 1: BAR CHARTS COMPARISON ────────────────────────────────────────

    fig = plt.figure(figsize=(14, 9))
    fig.patch.set_facecolor("#f8f9fa")
    fig.suptitle("Porovnání řešení – splněná přání", fontsize=17,
                 fontweight="bold", color="#2c3e50", y=0.98)

    gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.45, wspace=0.35)

    def bar_chart(ax, values, title, ylabel, color_scale, ref_line=None,
                  fmt="{:.0f}"):
        bars = ax.bar(short_labels, values,
                      color=[COLORS(i) for i in range(N)],
                      edgecolor="white", linewidth=0.8, zorder=2)
        ax.set_title(title, fontsize=11, fontweight="bold", color="#2c3e50", pad=6)
        ax.set_ylabel(ylabel, fontsize=8)
        ax.set_ylim(0, max(values) * 1.22)
        ax.grid(axis="y", alpha=0.3, zorder=0)
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(axis="x", labelsize=8)
        if ref_line is not None:
            ax.axhline(ref_line, color="#e74c3c", lw=1.2, ls="--", alpha=0.7,
                       label=f"Max možné: {ref_line}")
            ax.legend(fontsize=7)
        # value labels on bars
        for bar, val in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + max(values) * 0.015,
                    fmt.format(val),
                    ha="center", va="bottom", fontsize=8, fontweight="bold")
        # highlight best
        bars[best_idx].set_edgecolor("#e74c3c")
        bars[best_idx].set_linewidth(2.5)

    ax1 = fig.add_subplot(gs[0, 0])
    bar_chart(ax1, sat_edges,  "Splněných přání (počet hran)",
              "Počet hran", COLORS, ref_line=total_e)

    ax2 = fig.add_subplot(gs[0, 1])
    bar_chart(ax2, pct_edges, "Splněných přání (%)",
              "%", COLORS, fmt="{:.1f}%")

    ax3 = fig.add_subplot(gs[1, 0])
    bar_chart(ax3, with_friend, "Dětí s alespoň 1 kamarádem",
              "Počet dětí", COLORS, ref_line=total_p)

    ax4 = fig.add_subplot(gs[1, 1])
    bar_chart(ax4, mutual, "Vzájemných párů v jedné chatce",
              "Počet párů", COLORS)

    # legend for solution names
    legend_patches = [
        mpatches.Patch(color=COLORS(i), label=labels[i])
        for i in range(N)
    ]
    fig.legend(handles=legend_patches, loc="lower center",
               ncol=2, fontsize=7.5, framealpha=0.9,
               bbox_to_anchor=(0.5, 0.0),
               title="Strategie přiřazení", title_fontsize=8)

    fig.subplots_adjust(bottom=0.22)
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)

    # ── PAGE 2: RANKING TABLE ─────────────────────────────────────────────────

    fig, ax = plt.subplots(figsize=(14, 7))
    fig.patch.set_facecolor("#f8f9fa")
    ax.axis("off")
    ax.set_title("Pořadí řešení – seřazeno dle splněných přání",
                 fontsize=15, fontweight="bold", color="#2c3e50", pad=14)

    ranked = sorted(summary, key=lambda s: (-s["sat_edges"], -s["mutual_pairs"]))

    col_labels = ["#", "Řešení", "Strategie",
                  "Splněno hran", "% hran",
                  "Dětí s kamarádem", "% dětí",
                  "Vzáj. párů"]
    col_xs = [0.02, 0.06, 0.36, 0.62, 0.71, 0.79, 0.89, 0.95]
    row_h  = 0.072
    y0     = 0.82

    # header
    for cx, lbl in zip(col_xs, col_labels):
        ax.text(cx, y0, lbl, ha="left", va="center",
                fontsize=9, fontweight="bold", color="white",
                transform=ax.transAxes,
                bbox=dict(facecolor="#2c3e50", edgecolor="none",
                          boxstyle="round,pad=0.25"))

    for rank, s in enumerate(ranked):
        y = y0 - (rank + 1) * row_h
        is_best = (s["index"] == best_idx)
        row_bg  = "#fef9e7" if is_best else ("#eaf2ff" if rank % 2 == 0 else "white")
        ax.add_patch(plt.Rectangle((0.0, y - row_h * 0.45), 1.0, row_h,
                                    facecolor=row_bg, edgecolor="none",
                                    transform=ax.transAxes, zorder=0))

        medal = {0: "[1]", 1: "[2]", 2: "[3]"}.get(rank, "   ")
        vals = [
            f"{rank+1}. {medal}",
            f"S{s['index']}",
            s["name"][:38],
            f"{s['sat_edges']} / {s['total_edges']}",
            f"{s['pct_edges']} %",
            f"{s['with_friend']} / {s['assigned']}",
            f"{s['pct_friend']} %",
            str(s["mutual_pairs"]),
        ]
        for cx, v in zip(col_xs, vals):
            weight = "bold" if is_best else "normal"
            color  = "#c0392b" if is_best else "#1a1a1a"
            ax.text(cx, y, v, ha="left", va="center",
                    fontsize=8.5, fontweight=weight, color=color,
                    transform=ax.transAxes)

    # note best
    best_name = next(s["name"] for s in summary if s["index"] == best_idx)
    ax.text(0.5, 0.03,
            f"★ Nejlepší řešení: S{best_idx} – {best_name}",
            ha="center", va="center", fontsize=10, fontweight="bold",
            color="#c0392b", transform=ax.transAxes,
            bbox=dict(facecolor="#fef9e7", edgecolor="#c0392b",
                      boxstyle="round,pad=0.4"))

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)

    # ── PAGE 3: PER-BUILDING SATISFACTION FOR BEST SOLUTION ──────────────────

    best_sol = solutions[best_idx]
    best_blds = best_sol["buildings"]
    sat_set   = {(e["source"], e["target"]) for e in best_sol["satisfied_edges"]}

    bld_ids = sorted(best_blds.keys(), key=bld_sort_key)
    bld_sat  = []
    bld_total = []
    bld_cap  = []
    bld_fill = []
    bld_gend = []

    for b in bld_ids:
        info     = best_blds[b]
        members  = {p["id"] for p in info["participants"]}
        # edges where both endpoints are in this building
        b_edges  = [e for e in all_edges
                    if e["source"] in members and e["target"] in members]
        b_sat    = sum(1 for e in b_edges if (e["source"], e["target"]) in sat_set)
        bld_sat.append(b_sat)
        bld_total.append(len(b_edges))
        bld_cap.append(info["capacity"])
        bld_fill.append(info["count"])
        bld_gend.append(info["gender"])

    M_C = "#2980b9"
    F_C = "#e91e8c"
    colors_bld = [M_C if g == "M" else F_C for g in bld_gend]

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.patch.set_facecolor("#f8f9fa")
    fig.suptitle(f"Nejlepší řešení S{best_idx}: detail podle chatky\n({best_name})",
                 fontsize=14, fontweight="bold", color="#2c3e50")

    # left: satisfied edges per building
    ax = axes[0]
    x  = np.arange(len(bld_ids))
    w  = 0.35
    bars_sat   = ax.bar(x - w/2, bld_sat,   w, label="Splněno", color=[c + "cc" for c in colors_bld],
                        edgecolor="white")
    bars_total = ax.bar(x + w/2, bld_total, w, label="Celkem možných", color="lightgrey",
                        edgecolor="white")
    ax.set_xticks(x)
    ax.set_xticklabels(bld_ids, rotation=45, ha="right", fontsize=7)
    ax.set_title("Splněná přání v každé chatce", fontsize=10, fontweight="bold")
    ax.set_ylabel("Počet hran")
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    ax.spines[["top", "right"]].set_visible(False)

    # right: occupancy
    ax2 = axes[1]
    bars_fill = ax2.bar(x, bld_fill, color=[c + "cc" for c in colors_bld], edgecolor="white", label="Obsazeno")
    bars_capc = ax2.step(np.append(x - 0.5, x[-1] + 0.5),
                         np.append(bld_cap, bld_cap[-1]),
                         where="post", color="#e74c3c", lw=1.5, ls="--", label="Kapacita")
    ax2.set_xticks(x)
    ax2.set_xticklabels(bld_ids, rotation=45, ha="right", fontsize=7)
    ax2.set_title("Obsazenost chatek", fontsize=10, fontweight="bold")
    ax2.set_ylabel("Počet dětí")
    ax2.legend(fontsize=8)
    ax2.grid(axis="y", alpha=0.3)
    ax2.spines[["top", "right"]].set_visible(False)

    # colour legend
    m_patch = mpatches.Patch(color=M_C + "cc", label="Chlapci ♂")
    f_patch = mpatches.Patch(color=F_C + "cc", label="Dívky ♀")
    fig.legend(handles=[m_patch, f_patch], loc="lower center",
               ncol=2, fontsize=9, bbox_to_anchor=(0.5, 0.0))
    fig.subplots_adjust(bottom=0.15)

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)

    # ── PAGE 4: RADAR / SPIDER CHART ─────────────────────────────────────────

    fig = plt.figure(figsize=(10, 8))
    fig.patch.set_facecolor("#f8f9fa")
    fig.suptitle("Radarový graf – porovnání metrik", fontsize=14,
                 fontweight="bold", color="#2c3e50")

    categories = ["Splněné hrany", "% hran", "Dětí s kamarádem",
                  "% dětí", "Vzáj. párů"]
    n_cat = len(categories)
    angles = [2 * np.pi * i / n_cat for i in range(n_cat)]
    angles += angles[:1]

    ax = fig.add_subplot(111, polar=True)
    ax.set_facecolor("#f0f4f8")

    # normalize each metric to [0,1]
    def norm(vals):
        mn, mx = min(vals), max(vals)
        if mx == mn:
            return [0.5] * len(vals)
        return [(v - mn) / (mx - mn) for v in vals]

    metrics = [sat_edges, pct_edges, with_friend, pct_friend, mutual]
    normed  = [norm(m) for m in metrics]

    for i in range(N):
        values = [normed[j][i] for j in range(n_cat)] + [normed[0][i]]
        ax.plot(angles, values, "o-", lw=2, color=COLORS(i),
                label=f"S{i}", alpha=0.85)
        ax.fill(angles, values, color=COLORS(i), alpha=0.07)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, fontsize=9)
    ax.set_yticks([0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["25%", "50%", "75%", "100%"], fontsize=7, color="grey")
    ax.set_ylim(0, 1)
    ax.grid(color="grey", alpha=0.3)

    ax.legend(handles=[mpatches.Patch(color=COLORS(i), label=labels[i])
                        for i in range(N)],
              loc="upper right", bbox_to_anchor=(1.45, 1.15),
              fontsize=7.5, framealpha=0.9, title="Strategie", title_fontsize=8)

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)

    d = pdf.infodict()
    d["Title"]  = "Porovnání řešení přiřazení do chatek"
    d["Author"] = "compare_solutions.py"

print("Written solutions/comparison.pdf")
