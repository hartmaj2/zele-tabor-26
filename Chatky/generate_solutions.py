"""
Generate multiple diverse solutions to the chatka assignment problem
and save each to solutions/solution_N.json.

Strategies:
  0 – Age-greedy baseline (same logic as solve.py)
  1 – Preference-cluster aware: group preference-connected kids first,
      then fill buildings
  2 – Age-greedy, reversed gender→building mapping
  3 – Preference-cluster aware, reversed gender→building mapping
  4 – Age-greedy, random seed A (shuffle within same-age groups)
  5 – Age-greedy, random seed B
  6 – Preference-cluster aware, seed A
  7 – Preference-cluster aware, seed B
"""

import json
import os
import random
import itertools
from collections import defaultdict
from constraints import BUILDINGS, MAX_AGE_GAP

# ── load data ────────────────────────────────────────────────────────────────

with open("graph.json", encoding="utf-8") as f:
    gdata = json.load(f)

participants = gdata["nodes"]
all_edges    = gdata["edges"]

# name → node dict
node_map = {p["id"]: p for p in participants}

# preference adjacency (undirected) for clustering
adj: dict[str, set] = defaultdict(set)
for e in all_edges:
    adj[e["source"]].add(e["target"])
    adj[e["target"]].add(e["source"])

sat_set_from_assign = lambda p2b: {
    (e["source"], e["target"])
    for e in all_edges
    if p2b.get(e["source"]) and p2b.get(e["target"])
    and p2b[e["source"]] == p2b[e["target"]]
}


def age_int(p):
    try:
        return int(p["vek"])
    except Exception:
        return 99


def bld_sort_key(b):
    if b.isdigit():
        return (0, int(b))
    if b.startswith("n"):
        return (1, int(b[1:]))
    if b.startswith("m"):
        return (2, int(b[1:]))
    return (3, b)


# All buildings sorted largest→smallest
all_blds_sorted = sorted(BUILDINGS.items(), key=lambda x: (-x[1], bld_sort_key(x[0])))


# ── building→gender split helpers ────────────────────────────────────────────

def split_buildings(reverse: bool = False):
    """Alternate buildings between M and F (largest first).
    reverse=True swaps which gender gets even/odd slots."""
    m_blds = [(b, c) for i, (b, c) in enumerate(all_blds_sorted) if (i % 2 == 0) != reverse]
    f_blds = [(b, c) for i, (b, c) in enumerate(all_blds_sorted) if (i % 2 == 1) != reverse]
    return m_blds, f_blds


# ── strategy A: age-greedy ───────────────────────────────────────────────────

def pack_age_greedy(kids: list, bld_list: list, rng: random.Random | None = None) -> tuple[dict, list]:
    """Fill buildings largest-first with age-sorted kids.
    If rng is given, shuffle kids of the same age to add variety."""
    if rng:
        # group by age, shuffle within each age group
        by_age = defaultdict(list)
        for k in kids:
            by_age[age_int(k)].append(k)
        kids = []
        for age in sorted(by_age):
            group = by_age[age]
            rng.shuffle(group)
            kids.extend(group)

    result: dict[str, list] = {}
    idx = 0
    for bld_id, cap in bld_list:
        if idx >= len(kids):
            break
        cohort = []
        while idx < len(kids) and len(cohort) < cap:
            kid = kids[idx]
            if cohort and age_int(kid) - age_int(cohort[0]) > MAX_AGE_GAP:
                break
            cohort.append(kid)
            idx += 1
        if cohort:
            result[bld_id] = cohort
    return result, kids[idx:]


# ── strategy B: preference-cluster aware ────────────────────────────────────

def preference_clusters(kids: list) -> list[list]:
    """
    BFS to find connected components in the preference graph restricted to
    this gender's kids. Returns list of clusters sorted by size desc.
    """
    kid_set  = {k["id"] for k in kids}
    kid_map  = {k["id"]: k for k in kids}
    visited: set[str] = set()
    clusters = []

    for kid in kids:
        pid = kid["id"]
        if pid in visited:
            continue
        cluster = []
        queue   = [pid]
        while queue:
            cur = queue.pop()
            if cur in visited or cur not in kid_set:
                continue
            visited.add(cur)
            cluster.append(kid_map[cur])
            for nb in adj.get(cur, []):
                if nb not in visited and nb in kid_set:
                    queue.append(nb)
        clusters.append(cluster)

    # sort clusters: largest first, then by median age (youngest first)
    clusters.sort(key=lambda c: (-len(c), sum(age_int(k) for k in c) / len(c)))
    return clusters


def pack_cluster_aware(kids: list, bld_list: list, rng: random.Random | None = None) -> tuple[dict, list]:
    """
    Fill buildings by placing whole preference clusters together.
    Within a cluster, sort by age. Fall back to age-greedy for remainder.
    """
    clusters = preference_clusters(kids)
    if rng:
        # shuffle clusters of the same size to add variety
        by_size = defaultdict(list)
        for c in clusters:
            by_size[len(c)].append(c)
        clusters = []
        for sz in sorted(by_size, reverse=True):
            group = by_size[sz]
            rng.shuffle(group)
            clusters.extend(group)

    # flatten clusters to an ordered kid list, respecting age-gap constraint
    # Strategy: sort each cluster internally by age, then try to fit clusters
    # into buildings in order. If a cluster doesn't fit (capacity or age gap),
    # break it into smaller pieces.
    result: dict[str, list] = {}
    leftover: list = []

    for bld_id, cap in bld_list:
        if not clusters:
            break

        cohort:  list  = []
        pending: list  = []  # clusters that didn't fit this building

        for cluster in clusters:
            cluster_sorted = sorted(cluster, key=age_int)

            # Can we fit this cluster (or part of it) in remaining space?
            for kid in cluster_sorted:
                if len(cohort) >= cap:
                    pending.append(kid)
                    continue
                if cohort and age_int(kid) - age_int(cohort[0]) > MAX_AGE_GAP:
                    pending.append(kid)
                    continue
                cohort.append(kid)

        clusters = []
        # rebuild pending into mini-clusters for next iteration
        if pending:
            # re-cluster pending (they are individual kids now)
            clusters = [[k] for k in sorted(pending, key=age_int)]

        if cohort:
            result[bld_id] = cohort

    # any still-pending → leftover
    for c in clusters:
        leftover.extend(c)

    # try to squeeze leftover into remaining buildings (age-greedy fallback)
    leftover_sorted = sorted(leftover, key=age_int)
    used_blds = set(result.keys())
    remaining_blds = [(b, c) for b, c in bld_list if b not in used_blds]
    extra, still_left = pack_age_greedy(leftover_sorted, remaining_blds)
    result.update(extra)
    return result, still_left


# ── build + score a solution ──────────────────────────────────────────────────

def make_solution(m_assign: dict, f_assign: dict) -> dict:
    p2b: dict[str, str] = {}
    buildings_out: dict[str, dict] = {}

    for bld_id, kids in {**m_assign, **f_assign}.items():
        ages = sorted(age_int(k) for k in kids)
        buildings_out[bld_id] = {
            "capacity":     BUILDINGS[bld_id],
            "count":        len(kids),
            "gender":       kids[0]["gender"],
            "age_min":      ages[0],
            "age_max":      ages[-1],
            "age_gap":      ages[-1] - ages[0],
            "participants": [{"id": k["id"], "vek": k["vek"],
                              "gender": k["gender"], "oddil": k["oddil"]}
                             for k in kids],
        }
        for k in kids:
            p2b[k["id"]] = bld_id

    sat_edges = [
        e for e in all_edges
        if p2b.get(e["source"]) and p2b.get(e["target"])
        and p2b[e["source"]] == p2b[e["target"]]
    ]
    kids_with_friend = {e["source"] for e in sat_edges} | {e["target"] for e in sat_edges}
    kids_with_friend &= set(p2b.keys())
    mutual = [e for e in sat_edges
              if any(e2["source"] == e["target"] and e2["target"] == e["source"]
                     for e2 in sat_edges)]

    unassigned = sorted({p["id"] for p in participants} - set(p2b.keys()))

    return {
        "buildings":        buildings_out,
        "participants":     p2b,
        "satisfied_edges":  sat_edges,
        "unassigned":       unassigned,
        "stats": {
            "total_participants":           len(participants),
            "assigned":                     len(p2b),
            "unassigned_count":             len(unassigned),
            "total_preference_edges":       len(all_edges),
            "satisfied_preference_edges":   len(sat_edges),
            "participants_with_friend":     len(kids_with_friend),
            "mutual_pairs_satisfied":       len(mutual) // 2,
        },
    }


# ── run all strategies ────────────────────────────────────────────────────────

males   = sorted([p for p in participants if p["gender"] == "M"], key=age_int)
females = sorted([p for p in participants if p["gender"] == "F"], key=age_int)

STRATEGIES = [
    # (name, pack_fn, reverse_split, rng_seed)
    ("Age-greedy (baseline)",                 pack_age_greedy,     False, None),
    ("Preference-cluster aware",              pack_cluster_aware,  False, None),
    ("Age-greedy, reversed gender split",     pack_age_greedy,     True,  None),
    ("Preference-cluster, reversed split",    pack_cluster_aware,  True,  None),
    ("Age-greedy, shuffle seed 42",           pack_age_greedy,     False, 42),
    ("Age-greedy, shuffle seed 137",          pack_age_greedy,     False, 137),
    ("Preference-cluster, shuffle seed 42",   pack_cluster_aware,  False, 42),
    ("Preference-cluster, shuffle seed 137",  pack_cluster_aware,  False, 137),
]

os.makedirs("solutions", exist_ok=True)
summary = []

for i, (name, pack_fn, reverse, seed) in enumerate(STRATEGIES):
    m_blds, f_blds = split_buildings(reverse)
    rng = random.Random(seed) if seed is not None else None

    m_assign, m_left = pack_fn(males,   m_blds, rng)
    rng2 = random.Random(seed + 1000) if seed is not None else None
    f_assign, f_left = pack_fn(females, f_blds, rng2)

    if m_left or f_left:
        print(f"[{i}] WARNING: {len(m_left)+len(f_left)} unassigned: "
              f"{[p['id'] for p in m_left+f_left]}")

    sol = make_solution(m_assign, f_assign)
    sol["strategy"] = {"index": i, "name": name, "reverse": reverse, "seed": seed}

    path = f"solutions/solution_{i}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(sol, f, ensure_ascii=False, indent=2)

    s = sol["stats"]
    summary.append({
        "index":      i,
        "name":       name,
        "assigned":   s["assigned"],
        "sat_edges":  s["satisfied_preference_edges"],
        "total_edges": s["total_preference_edges"],
        "pct_edges":  round(100 * s["satisfied_preference_edges"] / s["total_preference_edges"], 1),
        "with_friend": s["participants_with_friend"],
        "pct_friend": round(100 * s["participants_with_friend"] / s["assigned"], 1),
        "mutual_pairs": s["mutual_pairs_satisfied"],
    })
    print(f"[{i}] {name:45s}  "
          f"sat={s['satisfied_preference_edges']:3d}/{s['total_preference_edges']}  "
          f"({100*s['satisfied_preference_edges']/s['total_preference_edges']:.0f}%)  "
          f"with_friend={s['participants_with_friend']:2d}  "
          f"mutual={s['mutual_pairs_satisfied']}")

# write summary JSON
with open("solutions/summary.json", "w", encoding="utf-8") as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)

print(f"\n{len(STRATEGIES)} solutions written to solutions/")
