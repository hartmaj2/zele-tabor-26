"""
Convert rozdeleni_chatek_optimalni.json to the standard solution format,
then visualize it.
"""

import json

# ── load sources ──────────────────────────────────────────────────────────────

with open("solutions/rozdeleni_chatek_optimalni.json", encoding="utf-8") as f:
    raw = json.load(f)

with open("graph.json", encoding="utf-8") as f:
    gdata = json.load(f)

all_edges   = gdata["edges"]
all_nodes   = gdata["nodes"]
node_map    = {p["id"]: p for p in all_nodes}

# ── name normalisation (the raw file has trailing spaces on some names) ────────

def norm_name(s: str) -> str:
    return " ".join(s.strip().split())

# Build a lookup: normalised name → canonical id from graph.json
canon = {norm_name(p["id"]): p["id"] for p in all_nodes}

def canonical(name: str) -> str:
    n = norm_name(name)
    return canon.get(n, name)   # fallback: return normalised name

# ── build standard buildings dict ─────────────────────────────────────────────

buildings_out: dict[str, dict] = {}
p2b: dict[str, str] = {}

for cabin in raw:
    bld_id  = cabin["cabin_name"]
    members = cabin["members"]
    if not members:
        continue

    kids = []
    for m in members:
        cid = canonical(m["name"])
        kids.append({
            "id":     cid,
            "vek":    str(m["age"]),
            "gender": m["gender"],
            "oddil":  str(m["oddil"]),
        })
        p2b[cid] = bld_id

    ages    = sorted(int(k["vek"]) for k in kids)
    genders = {k["gender"] for k in kids}
    buildings_out[bld_id] = {
        "capacity":     cabin["capacity"],
        "count":        len(kids),
        "gender":       "/".join(sorted(genders)),
        "age_min":      ages[0],
        "age_max":      ages[-1],
        "age_gap":      ages[-1] - ages[0],
        "participants": kids,
    }

# ── compute satisfied edges ───────────────────────────────────────────────────

sat_edges = [
    e for e in all_edges
    if p2b.get(canonical(e["source"])) is not None
    and p2b.get(canonical(e["source"])) == p2b.get(canonical(e["target"]))
]

kids_with_friend = (
    {canonical(e["source"]) for e in sat_edges} |
    {canonical(e["target"]) for e in sat_edges}
)
kids_with_friend &= set(p2b.keys())

mutual = [
    e for e in sat_edges
    if any(e2["source"] == e["target"] and e2["target"] == e["source"]
           for e2 in sat_edges)
]

# ── unassigned ────────────────────────────────────────────────────────────────

all_ids    = {p["id"] for p in all_nodes}
assigned   = set(p2b.keys())
unassigned = sorted(all_ids - assigned)
if unassigned:
    print(f"Unassigned ({len(unassigned)}): {unassigned}")
else:
    print("All participants assigned.")

# ── assemble solution ─────────────────────────────────────────────────────────

solution = {
    "buildings":       buildings_out,
    "participants":    p2b,
    "satisfied_edges": sat_edges,
    "unassigned":      unassigned,
    "stats": {
        "total_participants":           len(all_nodes),
        "assigned":                     len(p2b),
        "unassigned_count":             len(unassigned),
        "total_preference_edges":       len(all_edges),
        "satisfied_preference_edges":   len(sat_edges),
        "participants_with_friend":     len(kids_with_friend),
        "mutual_pairs_satisfied":       len(mutual) // 2,
    },
    "strategy": {
        "index": "optimalni",
        "name":  "Rozdělen\u00ed chatek optim\u00e1ln\u00ed (external)",
        "reverse": False,
        "seed": None,
    },
}

out_path = "solutions/solution_optimalni.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(solution, f, ensure_ascii=False, indent=2)

s = solution["stats"]
print(f"Written {out_path}")
print(f"  Assigned:          {s['assigned']}/{s['total_participants']}")
print(f"  Satisfied edges:   {s['satisfied_preference_edges']}/{s['total_preference_edges']}  "
      f"({100*s['satisfied_preference_edges']/s['total_preference_edges']:.1f}%)")
print(f"  Kids with friend:  {s['participants_with_friend']}/{s['assigned']}")
print(f"  Mutual pairs:      {s['mutual_pairs_satisfied']}")

# ── visualise ─────────────────────────────────────────────────────────────────

import os, subprocess, sys

os.makedirs("visualisations", exist_ok=True)
result = subprocess.run(
    [sys.executable, "visualize.py",
     out_path,
     "visualisations/solution_optimalni.pdf"],
    capture_output=True, text=True
)
if result.returncode == 0:
    print("Written visualisations/solution_optimalni.pdf")
else:
    print("Visualisation FAILED:")
    print(result.stderr[-600:])
