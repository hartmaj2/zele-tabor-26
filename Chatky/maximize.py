"""
Maximize splněná přání (satisfied preference edges) — constraints ignored for fun.
Only hard rule: each kid assigned to exactly one building, capacity not exceeded.
Gender, age gap, age-size ordering: all ignored.

Approach:
  1. Louvain community detection on undirected preference graph → initial clusters
  2. Map clusters to buildings greedily (largest cluster → largest building)
  3. Local search: repeatedly try random swaps between buildings;
     accept if satisfied-edge count improves (hill-climbing + occasional
     random restarts to escape local optima)

Outputs: solutions/solution_max.json + visualisations/solution_max.pdf
"""

import json, math, random, time
from collections import defaultdict
import networkx as nx
from networkx.algorithms import community as nx_community
from constraints import BUILDINGS

# ── load data ─────────────────────────────────────────────────────────────────

with open("graph.json", encoding="utf-8") as f:
    gdata = json.load(f)

participants = gdata["nodes"]
all_edges    = gdata["edges"]
names        = [p["id"] for p in participants]
name_set     = set(names)
node_map     = {p["id"]: p for p in participants}

# ── build undirected preference graph ─────────────────────────────────────────

G = nx.Graph()
G.add_nodes_from(names)
for e in all_edges:
    G.add_edge(e["source"], e["target"])

# ── score function ─────────────────────────────────────────────────────────────

def score(assign: dict[str, str]) -> int:
    """Count directed preference edges where both endpoints are in the same building."""
    return sum(1 for e in all_edges
               if assign.get(e["source"]) == assign.get(e["target"])
               and assign.get(e["source"]) is not None)

def score_delta(assign: dict[str, str], pid: str, new_bld: str) -> int:
    """Change in score if pid is moved to new_bld (without modifying assign)."""
    old_bld = assign[pid]
    if old_bld == new_bld:
        return 0
    delta = 0
    for e in all_edges:
        nb = None
        if e["source"] == pid:
            nb = e["target"]
        elif e["target"] == pid:
            nb = e["source"]
        if nb is None or nb not in assign:
            continue
        nb_bld = assign[nb]
        # losing old_bld match
        if nb_bld == old_bld:
            delta -= 1
        # gaining new_bld match
        if nb_bld == new_bld:
            delta += 1
    return delta

# ── step 1: Louvain initial assignment ────────────────────────────────────────

print("Running Louvain community detection …")
communities = list(nx_community.louvain_communities(G, seed=42))
communities.sort(key=lambda c: -len(c))  # largest first

# Map community members to buildings largest-first
bld_list = sorted(BUILDINGS.items(), key=lambda x: -x[1])  # largest cap first
capacities = dict(BUILDINGS)
counts: dict[str, int] = {b: 0 for b in BUILDINGS}
assign: dict[str, str] = {}

# Flatten communities into an ordered list
ordered_kids = []
for comm in communities:
    ordered_kids.extend(sorted(comm))  # deterministic order within community

# Greedy fill: put each kid in the current building if it fits, else next
bld_idx = 0
for kid in ordered_kids:
    # advance to a building with remaining capacity
    while bld_idx < len(bld_list) and counts[bld_list[bld_idx][0]] >= bld_list[bld_idx][1]:
        bld_idx += 1
    if bld_idx >= len(bld_list):
        break  # shouldn't happen (116 cap > 99 kids)
    bld_id = bld_list[bld_idx][0]
    assign[kid] = bld_id
    counts[bld_id] += 1

# any unassigned (shouldn't happen)
for kid in names:
    if kid not in assign:
        for b, c in bld_list:
            if counts[b] < c:
                assign[kid] = b
                counts[b] += 1
                break

initial_score = score(assign)
print(f"Louvain initial score: {initial_score}/{len(all_edges)}")

# ── step 2: hill-climbing local search with random restarts ──────────────────

best_assign  = dict(assign)
best_score   = initial_score
current      = dict(assign)
current_score = initial_score

rng = random.Random(0)
t0  = time.time()
MAX_TIME    = 15.0   # seconds
iters       = 0
improvements = 0
restarts    = 0
stagnation  = 0
STAG_LIMIT  = 5000   # restart after this many non-improving iters

print(f"Hill-climbing for {MAX_TIME:.0f}s …")

while time.time() - t0 < MAX_TIME:
    iters += 1

    # Pick a random kid and a random different building that has room
    pid   = rng.choice(names)
    old_b = current[pid]
    # candidate buildings with spare capacity
    cands = [b for b, c in BUILDINGS.items()
             if b != old_b and counts[b] < c]
    if not cands:
        continue
    new_b = rng.choice(cands)

    delta = score_delta(current, pid, new_b)

    if delta > 0:
        # accept improvement
        current[pid] = new_b
        counts[old_b] -= 1
        counts[new_b] += 1
        current_score += delta
        improvements += 1
        stagnation = 0
        if current_score > best_score:
            best_score  = current_score
            best_assign = dict(current)
    else:
        stagnation += 1

    # random restart from best when stuck
    if stagnation >= STAG_LIMIT:
        current       = dict(best_assign)
        counts        = {b: 0 for b in BUILDINGS}
        for k, b in current.items():
            counts[b] += 1
        current_score = best_score
        stagnation    = 0
        restarts += 1

elapsed = time.time() - t0
print(f"Done: {iters:,} iters in {elapsed:.1f}s, "
      f"{improvements:,} improvements, {restarts} restarts")
print(f"Best score: {best_score}/{len(all_edges)}  "
      f"({100*best_score/len(all_edges):.1f}%)")

# ── compare with previous best (S3) ──────────────────────────────────────────

with open("solutions/solution_3.json", encoding="utf-8") as f:
    s3 = json.load(f)
prev_best = s3["stats"]["satisfied_preference_edges"]
print(f"Previous best (S3): {prev_best}/{len(all_edges)}  "
      f"({100*prev_best/len(all_edges):.1f}%)")
print(f"Improvement: +{best_score - prev_best} edges "
      f"({100*(best_score-prev_best)/len(all_edges):.1f} pp)")

# ── build solution object ─────────────────────────────────────────────────────

buildings_out: dict[str, dict] = {}
for bld_id in BUILDINGS:
    kids = [node_map[k] for k, b in best_assign.items() if b == bld_id]
    if not kids:
        continue
    ages = sorted(int(k["vek"]) for k in kids if str(k["vek"]).isdigit())
    age_min = ages[0] if ages else 0
    age_max = ages[-1] if ages else 0
    genders  = {k["gender"] for k in kids}
    buildings_out[bld_id] = {
        "capacity":     BUILDINGS[bld_id],
        "count":        len(kids),
        "gender":       "/".join(sorted(genders)),   # may be mixed — that's OK here
        "age_min":      age_min,
        "age_max":      age_max,
        "age_gap":      age_max - age_min,
        "participants": [{"id": k["id"], "vek": k["vek"],
                          "gender": k["gender"], "oddil": k["oddil"]}
                         for k in kids],
    }

sat_edges = [e for e in all_edges
             if best_assign.get(e["source"]) == best_assign.get(e["target"])]
kids_with_friend = {e["source"] for e in sat_edges} | {e["target"] for e in sat_edges}
mutual = [e for e in sat_edges
          if any(e2["source"] == e["target"] and e2["target"] == e["source"]
                 for e2 in sat_edges)]
unassigned = sorted(name_set - set(best_assign.keys()))

solution = {
    "buildings":       buildings_out,
    "participants":    best_assign,
    "satisfied_edges": sat_edges,
    "unassigned":      unassigned,
    "stats": {
        "total_participants":           len(participants),
        "assigned":                     len(best_assign),
        "unassigned_count":             len(unassigned),
        "total_preference_edges":       len(all_edges),
        "satisfied_preference_edges":   best_score,
        "participants_with_friend":     len(kids_with_friend),
        "mutual_pairs_satisfied":       len(mutual) // 2,
    },
    "strategy": {
        "index": "max",
        "name":  "Maximise splněná přání (no constraints)",
        "reverse": False,
        "seed": 0,
    },
    "constraint_violations": {
        "gender_mixed":  sum(1 for b, i in buildings_out.items()
                             if "/" in i["gender"]),
        "age_gap_over3": sum(1 for b, i in buildings_out.items()
                             if i["age_gap"] > 3),
    },
}

import os, subprocess, sys
os.makedirs("solutions", exist_ok=True)
with open("solutions/solution_max.json", "w", encoding="utf-8") as f:
    json.dump(solution, f, ensure_ascii=False, indent=2)
print("Written solutions/solution_max.json")
print(f"  Constraint violations — mixed gender: "
      f"{solution['constraint_violations']['gender_mixed']}  "
      f"age gap >3: {solution['constraint_violations']['age_gap_over3']}")

# ── visualise ─────────────────────────────────────────────────────────────────

os.makedirs("visualisations", exist_ok=True)
result = subprocess.run(
    [sys.executable, "visualize.py",
     "solutions/solution_max.json",
     "visualisations/solution_max.pdf"],
    capture_output=True, text=True
)
if result.returncode == 0:
    print("Written visualisations/solution_max.pdf")
else:
    print("Visualisation FAILED:", result.stderr[-300:])
