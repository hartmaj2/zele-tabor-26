"""
Parse participant preferences from 'osekane děti.xlsx' into a directed graph.
Each edge (A → B) means "participant A wants to be with participant B".
Outputs:
  - graph.json   — nodes + edges (for D3, vis.js, etc.)
  - edges.csv    — flat edge list
  - graph.graphml — GraphML for Gephi / NetworkX
  - unmatched.txt — preferences that couldn't be resolved to a participant
"""

import re
import json
import unicodedata
from difflib import SequenceMatcher
from collections import defaultdict

import openpyxl
import networkx as nx

XLSX = "osekane děti.xlsx"


# ── helpers ──────────────────────────────────────────────────────────────────

def strip_accents(s: str) -> str:
    """Return ASCII-folded string (for accent-insensitive comparison)."""
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )


def normalize(s: str) -> str:
    return strip_accents(s.strip().lower())


def tokens(s: str) -> set[str]:
    return set(re.findall(r"[a-zA-ZÀ-ž]+", normalize(s)))


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


# ── gender detection ─────────────────────────────────────────────────────────
# In Czech, female surnames end in -ová or -á (adjectival); male do not.
# For non-Czech/ambiguous surnames we fall back to the given name.

_FEMALE_FIRST_NAMES = {
    "nikol", "bela", "bela", "nela", "anna", "aneta", "adela", "andrea",
    "adriana", "alzbeta", "barbora", "edebhagba karolina", "ela", "ella",
    "eliska", "eva", "jana", "johana", "jolana", "josefina", "julie",
    "karolina", "karin", "klara", "kristina", "kristyna", "laura", "legnerova",
    "liliana", "lucie", "meda", "mia", "nela", "nikol", "petra", "sofie",
    "stela", "stepanka", "tereza", "valerie", "veronika", "viola", "zuzana",
    "anabella", "stela", "lili", "lilian", "liliana",
}
_MALE_FIRST_NAMES = {
    "adam", "albert", "antonin", "benjamin", "ben", "bocksteffel", "boris",
    "bořek", "borek", "brian", "bruno", "daniel", "david", "dominik",
    "filip", "frantisek", "jakub", "jan", "jiri", "kryštof", "krystof",
    "lukas", "lukáš", "marek", "martin", "matej", "matěj", "max",
    "michael", "ondrej", "ondřej", "pavel", "robin", "samuel", "sebastian",
    "simon", "šimon", "stepan", "štěpán", "tadeas", "tadeáš", "timmy",
    "viktor", "vojtěch", "vojtech",
}


def detect_gender(full_name: str) -> str:
    """
    Return 'F' or 'M' based on Czech surname morphology and first-name lists.
    The dataset uses 'Last First' ordering.
    """
    parts = full_name.strip().split()
    if not parts:
        return "?"
    surname = normalize(parts[0])
    given = normalize(" ".join(parts[1:])) if len(parts) > 1 else ""
    given_first = normalize(parts[-1]) if len(parts) > 1 else ""

    # Czech female surnames end in -ová or an adjectival -á/-á
    if surname.endswith("ova") or surname.endswith("ska") or surname.endswith("cka"):
        return "F"
    # adjectival female surnames: Nácovská, Stránská, Hradecká, …
    if re.search(r"(ska|cka|ova|ská|cká|ová)$", surname):
        return "F"
    # male adjectival: Bačkovský, Podlipský, …
    if re.search(r"sky$|cky$", surname):
        return "M"

    # Fall back to first / given name
    if given_first in _FEMALE_FIRST_NAMES:
        return "F"
    if given_first in _MALE_FIRST_NAMES:
        return "M"
    # try full given name (handles "Benjamin William")
    if given in _FEMALE_FIRST_NAMES:
        return "F"
    if given in _MALE_FIRST_NAMES:
        return "M"

    return "?"


# Manual overrides for edge-case names
_GENDER_OVERRIDES: dict[str, str] = {
    "Ota Dvid": "M",                # typo for "Ota David"
    "Taylor Benjamin William": "M",
    "Karhanová Robin": "F",         # surname is female form; Robin used for girls too
    "Hasnedl Robin": "M",
}


# Czech name inflection: strip common suffixes to get a stem that may match
_SUFFIXES = [
    "ovou", "ovem", "ové", "ovi", "ova", "oví",
    "kem", "kem", "ku", "ka",
    "em", "ym", "im", "ím",
    "ou", "ám", "am", "ě", "e", "u", "a",
]

# Known nicknames / alternative spellings → participant first-name token
_ALIASES: dict[str, str] = {
    "timmi": "timmy",
    "bertikem": "albert",
    "bertou": "albert",
    "bertik": "albert",
    "bert": "albert",
    "bertu": "albert",
    "jirkou": "jiri",
    "jirka": "jiri",
    "ondrou": "ondrej",
    "ondra": "ondrej",
    "honzik": "jan",
    "honza": "jan",
    "stela": "stela",    # already matches
    "annou": "anna",
    "terkou": "tereza",
    "terka": "tereza",
    "lucinkou": "lucie",
    "lucinka": "lucie",
    "julinka": "julie",
}

def stems(word: str) -> list[str]:
    """Return the word itself plus likely stems after removing Czech suffixes."""
    w = normalize(word)
    result = [w]
    # Check alias table first
    if w in _ALIASES:
        result.append(_ALIASES[w])
    for suf in _SUFFIXES:
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            stem = w[: -len(suf)]
            result.append(stem)
            if stem in _ALIASES:
                result.append(_ALIASES[stem])
    return result


# ── load participants ────────────────────────────────────────────────────────

wb = openpyxl.load_workbook(XLSX)
ws = wb["List1"]
rows = list(ws.iter_rows(values_only=True))[1:]  # skip header

# Each participant: (display_name, oddil, vek, preference_text)
participants: list[dict] = []
for row in rows:
    if not row[0]:
        continue
    participants.append(
        {
            "id": row[0].strip(),
            "oddil": row[1],
            "vek": row[2],
            "prani": row[4],
        }
    )

name_list = [p["id"] for p in participants]
print(f"Loaded {len(name_list)} participants")

# Pre-compute token sets for every participant name (both "Last First" and
# "First Last" orderings are present in the source data).
norm_names: dict[str, str] = {}   # normalize(name) → original id
for name in name_list:
    norm_names[normalize(name)] = name

# Also index individual tokens (first / last name) → list of candidates
token_index: dict[str, list[str]] = defaultdict(list)
for name in name_list:
    for tok in tokens(name):
        if len(tok) >= 3:          # skip very short tokens
            token_index[tok].append(name)


# ── name matching ────────────────────────────────────────────────────────────

def find_participant(mention: str) -> str | None:
    """
    Try to resolve a free-text mention to a participant id.
    Returns the participant id or None.
    """
    mention = mention.strip()
    if not mention:
        return None

    # 1. Exact normalised match
    nm = normalize(mention)
    if nm in norm_names:
        return norm_names[nm]

    # 2. Reversed order  (preference text often has "First Last",
    #    participant list has "Last First")
    parts = mention.strip().split()
    if len(parts) >= 2:
        reversed_mention = " ".join(reversed(parts))
        rnm = normalize(reversed_mention)
        if rnm in norm_names:
            return norm_names[rnm]

    # 3. Token overlap with stem-based fuzzy matching
    mention_stems: set[str] = set()
    for word in re.findall(r"[a-zA-ZÀ-ž]+", mention):
        mention_stems.update(stems(word))

    candidates: dict[str, int] = defaultdict(int)
    for stem in mention_stems:
        if stem in token_index:
            for cand in token_index[stem]:
                candidates[cand] += 1
        # also search stems of candidate tokens
        for tok, cands in token_index.items():
            if tok in mention_stems or stem in stems(tok):
                for cand in cands:
                    candidates[cand] += 1

    # Best candidate = most token overlaps, tie-break by string similarity
    if candidates:
        best = max(
            candidates,
            key=lambda c: (
                candidates[c],
                similarity(normalize(mention), normalize(c)),
            ),
        )
        # Require at least 2 matching tokens OR very high similarity
        if candidates[best] >= 2 or similarity(normalize(mention), normalize(best)) > 0.82:
            return best

    # 4. Single-token: try matching against every individual token of every name
    mention_words = re.findall(r"[a-zA-ZÀ-ž]+", mention)
    if len(mention_words) == 1:
        mw = normalize(mention_words[0])
        mw_stems = stems(mention_words[0])
        for name in name_list:
            for tok in tokens(name):
                tok_stems = stems(tok)
                if mw in tok_stems or any(s in tok_stems for s in mw_stems):
                    # Only accept if this token uniquely identifies the person
                    # (i.e. no other candidate shares this match)
                    matching = [
                        n for n in name_list
                        if any(s in stems(t) for t in re.findall(r"[a-zA-ZÀ-ž]+", n)
                               for s in mw_stems)
                    ]
                    if len(matching) == 1:
                        return matching[0]

    # 5. High-similarity full-name match (handles slight typos)
    best_sim = 0.0
    best_name = None
    for name in name_list:
        s = similarity(normalize(mention), normalize(name))
        if s > best_sim:
            best_sim = s
            best_name = name
    if best_sim > 0.85:
        return best_name

    return None


# ── extract candidate name mentions from preference text ────────────────────

def extract_mentions(text: str) -> list[str]:
    """
    Split preference text into candidate name fragments.
    Names are typically separated by commas, newlines, '+', 'a', 's', 'se'.
    """
    # Split on common delimiters
    parts = re.split(r"[,\n+]|(?<!\w)[as]\s+(?=[A-ZÁÉÍÓÚÝŽŠČŘĎŤŇĚ])", text)
    mentions = []
    for part in parts:
        # Remove parenthetical remarks, leading/trailing filler words
        part = re.sub(
            r"\b(prosím|prosime|prosíme|ubytování|ubytovat|bydlet|pokoji|chatce"
            r"|s\b|se\b|kamarád|kamarádkou|kamarádkami|kamarádi|bratrem|bratrancem"
            r"|sestrou|sestřičkou|sourozencem|dcera|syn|tábor|ADAMEM|s ním"
            r"|v jedné|na pokoji|spolu|ideálně|nejraději|konkrétně"
            r"|prosim|dekuji|děkuji|díky|pokud|možno|možné|ráda|rád|chtěla|chce"
            r"|určitě|stejném|stejná)\b",
            " ",
            part,
            flags=re.IGNORECASE,
        )
        part = part.strip(" .-:;()")
        # Keep only parts that look like they could contain a name
        # (at least one capitalised word of ≥3 chars)
        if re.search(r"[A-ZÁÉÍÓÚÝŽŠČŘĎŤŇĚ][a-záéíóúýžščřďťňě]{2,}", part):
            mentions.append(part.strip())
    return mentions


# ── build directed graph ────────────────────────────────────────────────────

G = nx.DiGraph()
for p in participants:
    name = p["id"]
    gender = _GENDER_OVERRIDES.get(name, detect_gender(name))
    G.add_node(
        name,
        oddil=str(p["oddil"]),
        vek=str(p["vek"]) if p["vek"] else "",
        gender=gender,
    )

unmatched: list[tuple[str, str]] = []

for p in participants:
    src = p["id"]
    prani = p["prani"]
    if not prani:
        continue

    mentions = extract_mentions(prani)
    for mention in mentions:
        # Skip if mention is clearly non-name (too short, or no capitals)
        if len(mention) < 3:
            continue
        target = find_participant(mention)
        if target and target != src:
            G.add_edge(src, target)
        else:
            if not target:
                unmatched.append((src, mention))

# ── output ──────────────────────────────────────────────────────────────────

# 1. JSON (D3 / vis.js friendly)
data = {
    "nodes": [
        {
            "id": n,
            "oddil": G.nodes[n].get("oddil", ""),
            "vek": G.nodes[n].get("vek", ""),
            "gender": G.nodes[n].get("gender", "?"),
            "out_degree": G.out_degree(n),
            "in_degree": G.in_degree(n),
        }
        for n in G.nodes
    ],
    "edges": [
        {"source": u, "target": v}
        for u, v in G.edges
    ],
}
with open("graph.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print(f"Written graph.json  ({len(data['nodes'])} nodes, {len(data['edges'])} edges)")

# 2. CSV edge list
with open("edges.csv", "w", encoding="utf-8") as f:
    f.write("source,target\n")
    for u, v in G.edges:
        f.write(f'"{u}","{v}"\n')
print(f"Written edges.csv")

# 3. GraphML
nx.write_graphml(G, "graph.graphml")
print("Written graph.graphml")

# 4. Unmatched mentions (for manual inspection)
with open("unmatched.txt", "w", encoding="utf-8") as f:
    for src, mention in unmatched:
        f.write(f"{src!r:40s}  →  {mention!r}\n")
print(f"Written unmatched.txt  ({len(unmatched)} unresolved mentions)")

# ── quick summary ────────────────────────────────────────────────────────────
print()
print("=== Top in-degree (most wanted as roommate) ===")
for node, deg in sorted(G.in_degree(), key=lambda x: -x[1])[:10]:
    print(f"  {deg:3d}  {node}")

print()
print("=== Gender annotation ===")
for node in sorted(G.nodes):
    g = G.nodes[node].get("gender", "?")
    print(f"  {g}  {node}")
unknown = [n for n in G.nodes if G.nodes[n].get("gender") == "?"]
if unknown:
    print(f"\nUnresolved gender ({len(unknown)}): {unknown}")
