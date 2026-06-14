"""
Greedy feasible assignment of participants to buildings (chatky).

Satisfies all hard constraints:
  H1 - single assignment
  H2 - capacity not exceeded
  H3 - no mixed-gender buildings
  H4 - age gap within building ≤ MAX_AGE_GAP
  H5 - bigger buildings house younger kids

Outputs: solution.json
"""

import json
from constraints import BUILDINGS, MAX_AGE_GAP

# ── load data ────────────────────────────────────────────────────────────────

with open("graph.json", encoding="utf-8") as f:
    data = json.load(f)

participants = data["nodes"]
edges = data["edges"]


def age_int(p):
    try:
        return int(p["vek"])
    except Exception:
        return 99


males   = sorted([p for p in participants if p["gender"] == "M"], key=age_int)
females = sorted([p for p in participants if p["gender"] == "F"], key=age_int)
print(f"Males: {len(males)}, Females: {len(females)}")

# ── allocate buildings to genders ────────────────────────────────────────────
# Sort all buildings by capacity descending, then alternate M / F.
# This gives each gender a mix of large and small buildings while keeping
# the largest buildings for the youngest kids of each gender.

all_blds = sorted(BUILDINGS.items(), key=lambda x: (-x[1], x[0]))

m_buildings = [b for i, b in enumerate(all_blds) if i % 2 == 0]  # even → M
f_buildings = [b for i, b in enumerate(all_blds) if i % 2 == 1]  # odd  → F

print(f"M buildings: {len(m_buildings)}  cap={sum(c for _,c in m_buildings)}")
print(f"F buildings: {len(f_buildings)}  cap={sum(c for _,c in f_buildings)}")

# ── pack kids into buildings ──────────────────────────────────────────────────

def pack_consecutive(kids: list, bld_list: list) -> tuple[dict, list]:
    """
    Fill buildings (largest first) with age-sorted kids consecutively.
    Stops filling a building when the next kid would violate MAX_AGE_GAP.
    Returns (assignment dict, leftover list).
    """
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
    leftover = kids[idx:]
    return result, leftover


m_assign, m_left = pack_consecutive(males,   m_buildings)
f_assign, f_left = pack_consecutive(females, f_buildings)

if m_left:
    print(f"WARNING: {len(m_left)} male(s) unassigned: {[p['id'] for p in m_left]}")
if f_left:
    print(f"WARNING: {len(f_left)} female(s) unassigned: {[p['id'] for p in f_left]}")

# ── build solution object ─────────────────────────────────────────────────────

participant_to_building: dict[str, str] = {}
buildings_out: dict[str, dict] = {}

for bld_id, kids in {**m_assign, **f_assign}.items():
    ages = sorted(age_int(k) for k in kids)
    buildings_out[bld_id] = {
        "capacity":    BUILDINGS[bld_id],
        "count":       len(kids),
        "gender":      kids[0]["gender"],
        "age_min":     ages[0],
        "age_max":     ages[-1],
        "age_gap":     ages[-1] - ages[0],
        "participants": [
            {
                "id":    k["id"],
                "vek":   k["vek"],
                "gender": k["gender"],
                "oddil": k["oddil"],
            }
            for k in kids
        ],
    }
    for k in kids:
        participant_to_building[k["id"]] = bld_id

# ── compute preference satisfaction ──────────────────────────────────────────

satisfied_edges = [
    e for e in edges
    if (e["source"] in participant_to_building
        and e["target"] in participant_to_building
        and participant_to_building[e["source"]] == participant_to_building[e["target"]])
]

kids_with_friend = {e["source"] for e in satisfied_edges} | {e["target"] for e in satisfied_edges}
kids_with_friend &= set(participant_to_building.keys())

mutual_satisfied = [
    e for e in satisfied_edges
    if any(e2["source"] == e["target"] and e2["target"] == e["source"]
           for e2 in satisfied_edges)
]

# ── unassigned ────────────────────────────────────────────────────────────────

all_ids = {p["id"] for p in participants}
unassigned = sorted(all_ids - set(participant_to_building.keys()))

# ── verify constraints ────────────────────────────────────────────────────────

violations = []
for bld_id, info in buildings_out.items():
    # H2
    if info["count"] > info["capacity"]:
        violations.append(f"H2 violated: {bld_id} has {info['count']} > {info['capacity']}")
    # H3
    genders_in = {p["gender"] for p in info["participants"]}
    if len(genders_in) > 1:
        violations.append(f"H3 violated: {bld_id} has mixed genders {genders_in}")
    # H4
    if info["age_gap"] > MAX_AGE_GAP:
        violations.append(f"H4 violated: {bld_id} age gap {info['age_gap']} > {MAX_AGE_GAP}")

# H5: for each pair of buildings, bigger should have younger or equal median age
import statistics
medians = {
    bld_id: statistics.median([age_int(p) for p in info["participants"]])
    for bld_id, info in buildings_out.items()
}
for b1, info1 in buildings_out.items():
    for b2, info2 in buildings_out.items():
        if info1["capacity"] > info2["capacity"] and medians[b1] > medians[b2]:
            violations.append(
                f"H5 violated: {b1}(cap={info1['capacity']}, median={medians[b1]}) "
                f"> {b2}(cap={info2['capacity']}, median={medians[b2]})"
            )

if violations:
    print("\nCONSTRAINT VIOLATIONS:")
    for v in violations:
        print(" ", v)
else:
    print("\nAll hard constraints satisfied ✓")

# ── write solution.json ───────────────────────────────────────────────────────

solution = {
    "buildings": buildings_out,
    "participants": participant_to_building,
    "satisfied_edges": satisfied_edges,
    "unassigned": unassigned,
    "stats": {
        "total_participants":       len(participants),
        "assigned":                 len(participant_to_building),
        "unassigned_count":         len(unassigned),
        "total_preference_edges":   len(edges),
        "satisfied_preference_edges": len(satisfied_edges),
        "participants_with_friend": len(kids_with_friend),
        "mutual_pairs_satisfied":   len(mutual_satisfied) // 2,
        "constraint_violations":    len(violations),
    },
}

with open("solution.json", "w", encoding="utf-8") as f:
    json.dump(solution, f, ensure_ascii=False, indent=2)

# ── print summary ─────────────────────────────────────────────────────────────

print(f"\nWritten solution.json")
print(f"Assigned: {solution['stats']['assigned']}/{solution['stats']['total_participants']}")
print(f"Unassigned: {unassigned if unassigned else 'none'}")
print(f"Preference edges satisfied: {solution['stats']['satisfied_preference_edges']}/{solution['stats']['total_preference_edges']}")
print(f"Kids with ≥1 friend: {solution['stats']['participants_with_friend']}/{solution['stats']['assigned']}")
print(f"Mutual pairs together: {solution['stats']['mutual_pairs_satisfied']}")

print("\nBuilding assignments:")
header = f"  {'Bldg':5s}  {'n/cap':6s}  {'G':1s}  {'Ages':7s}  Participants"
print(header)
print("  " + "-" * 80)
for bld_id in sorted(buildings_out.keys(), key=lambda x: (len(x), x)):
    info = buildings_out[bld_id]
    age_str = f"{info['age_min']}-{info['age_max']}"
    names = ", ".join(p["id"] for p in info["participants"])
    print(f"  {bld_id:5s}  {info['count']:2d}/{info['capacity']:2d}  {info['gender']}  {age_str:7s}  {names}")
