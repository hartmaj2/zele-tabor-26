#!/usr/bin/env python3
"""
randomize_pasy.py – Generátor záznamů do passports.json

Použití:
  python3 randomize_pasy.py           # 10 pasů
  python3 randomize_pasy.py --pocet 25
"""

import argparse
import calendar
import json
import os
import random
import sys
from datetime import datetime, timedelta

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
DATA_PATH    = os.path.join(SCRIPT_DIR, "data.json")
ZNAMENI_PATH = os.path.join(SCRIPT_DIR, "znameni.json")
OUTPUT_PATH  = os.path.join(SCRIPT_DIR, "passports.json")


def random_date(year_from, year_to):
    year = random.randint(year_from, year_to)
    month = random.randint(1, 12)
    day = random.randint(1, calendar.monthrange(year, month)[1])
    return f"{day}.{month}.{year}"


def random_expiration(expirace_config, expired):
    ref = datetime.strptime(expirace_config["aktualni_datum"], "%d.%m.%Y")
    if expired:
        delta = -random.randint(1, expirace_config["max_dni_pred"])
    else:
        delta = random.randint(1, expirace_config["max_dni_po"])
    d = ref + timedelta(days=delta)
    return f"{d.day}.{d.month}.{d.year}"


def pick_znameni(flat_kategorie):
    selected = random.sample(flat_kategorie, min(3, len(flat_kategorie)))
    return [random.choice(znaky) for znaky in selected]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pocet", type=int, default=10)
    args = parser.parse_args()

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    with open(ZNAMENI_PATH, "r", encoding="utf-8") as f:
        kategorie = json.load(f)

    # Flatten all occupations with their surovina into a cycling list
    povolani_list = [
        (povolani, surovina)
        for surovina, povolani_pool in data["povolani"].items()
        for povolani in povolani_pool
    ]

    # Flatten znameni categories
    flat_kategorie = [
        znaky
        for subgroups in kategorie.values()
        for znaky in subgroups.values()
    ]

    passports = []
    for i in range(args.pocet):
        cislo = i + 1
        expired = (cislo % 10 == 0)
        povolani, surovina = povolani_list[i % len(povolani_list)]
        pohlavi = random.choice(["M", "Ž"])

        passport = {
            "cislo_pasu":     f"CTH-{cislo:04d}",
            "jmeno":          f"{random.choice(data['jmena'][pohlavi])} {random.choice(data['prijmeni'][pohlavi])}",
            "pohlavi":        pohlavi,
            "datum_narozeni": random_date(data["datum_narozeni_rok_od"], data["datum_narozeni_rok_do"]),
            "expirace":       random_expiration(data["expirace"], expired),
            "povolani":       povolani,
            "surovina":       surovina,
            "znameni":        pick_znameni(flat_kategorie),
        }
        passports.append(passport)
        print(f"  {passport['cislo_pasu']} | {passport['povolani']:12} | {'EXPIROVÁN' if expired else 'platný':9} | {passport['expirace']}")

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(passports, f, ensure_ascii=False, indent=2)

    print(f"\nUloženo → {OUTPUT_PATH}")
    print("Nyní spusť:  python3 generate_pasy.py  pro vygenerování PDF.")


if __name__ == "__main__":
    main()
