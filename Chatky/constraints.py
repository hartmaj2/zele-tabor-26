"""
Assignment constraints and objectives for the chatka (building) assignment problem.

Problem:
  Assign each participant (kid) to exactly one building (chatka).
  Participants: from graph.json  (99 kids, with id / gender / vek / oddil)
  Buildings:    from chatky.csv  (capacities per building)

===============================================================================
BUILDING TYPES (from chatky.csv)
===============================================================================

  large   : 0  (cap 10), 1  (cap 10)           — biggest; for youngest kids
  medium  : 3  (cap 8),  4  (cap 9),  2 (cap 7), 5 (cap 7)
  small_m : m1–m10 (cap 3 each)                — smallest individual rooms
  medium_n: n1–n7  (cap 5 each)

Age groups observed in the data:
  youngest  ≈ 6–8   (oddil 7, 8, K)
  middle    ≈ 9–11  (oddil 5, 6)
  older     ≈ 12–14 (oddil 2, 3, 4)
  oldest    ≈ 15–16 (oddil 1)

===============================================================================
HARD CONSTRAINTS
===============================================================================

H1. SINGLE ASSIGNMENT
    Every participant is assigned to exactly one building.

H2. CAPACITY
    The number of participants assigned to building b  ≤  capacity(b).

H3. GENDER SEPARATION
    All participants in a building must have the same gender.
    Mixed-gender buildings are forbidden.

H4. AGE COHESION (per building)
    The age gap within any building  ≤  MAX_AGE_GAP years.
    Recommended value:  MAX_AGE_GAP = 3
    (i.e. oldest – youngest participant in the same building ≤ 3 years)

H5. AGE–SIZE ORDERING
    Bigger buildings should house younger kids.
    Formally: for any two buildings b1, b2 where capacity(b1) > capacity(b2),
    the median age of kids assigned to b1  ≤  median age of kids assigned to b2.
    (Applies across buildings of different size tiers; ties are allowed.)

===============================================================================
SOFT CONSTRAINTS / OBJECTIVES  (in priority order)
===============================================================================

O1. FRIEND COVERAGE  [primary]
    Maximise the number of participants who share a building with at least one
    person they listed as a preference  (i.e. there exists a directed edge
    source → target in graph.json where both are in the same building).

O2. MUTUAL PAIR COVERAGE  [secondary, tiebreak for O1]
    Prefer assignments where reciprocal (mutual) preference pairs
    (A → B  AND  B → A) are placed together.

O3. TOTAL PARTICIPANTS ASSIGNED  [tertiary]
    Maximise the number of participants actually assigned
    (relevant only if some participants cannot satisfy H3/H4 without being
    left unassigned).

===============================================================================
"""

# ── Parameters (adjustable) ──────────────────────────────────────────────────

MAX_AGE_GAP = 3        # H4: maximum allowed age difference within a building

# Building capacity lookup (mirrors chatky.csv)
BUILDINGS = {
    "0":  10,
    "1":  10,
    "2":  7,
    "3":  8,
    "4":  9,
    "5":  7,
    "m1": 3,  "m2": 3,  "m3": 3,  "m4": 3,  "m5": 3,
    "m6": 3,  "m7": 3,  "m8": 3,  "m9": 3,  "m10": 3,
    "n1": 5,  "n2": 5,  "n3": 5,  "n4": 5,
    "n5": 5,  "n6": 5,  "n7": 5,
}

# H5: size tiers (descending capacity) for the age–size ordering constraint
# Tier 1 = biggest buildings → youngest kids; tier 6 = smallest → oldest
SIZE_TIERS = [
    ["0", "1"],                                              # cap 10 → youngest
    ["4"],                                                   # cap 9
    ["3"],                                                   # cap 8
    ["2", "5"],                                              # cap 7
    ["n1", "n2", "n3", "n4", "n5", "n6", "n7"],             # cap 5
    ["m1", "m2", "m3", "m4", "m5", "m6", "m7", "m8", "m9", "m10"],  # cap 3 → oldest
]

# Total available spaces
TOTAL_CAPACITY = sum(BUILDINGS.values())
# 10+10+7+8+9+7 + 3×10 + 5×7 = 51 + 30 + 35 = 116
# Total participants = 99  →  17 spaces empty after full assignment
