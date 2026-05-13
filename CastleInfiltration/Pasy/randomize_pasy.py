#!/usr/bin/env python3
"""
randomize_pasy.py – Náhodný generátor záznamů do passports.json
================================================================

Čte:
  data.json    – pool jmen, příjmení, povolání, dat expirace
  znameni.json – kategorie zvláštních znamení

Vytvoří:
  passports.json – seznam pasů s náhodně vyplněnými hodnotami

Zvláštní znamení jsou vybírána tak, že se nejprve náhodně zvolí
N kategorií a z každé se pak vybere jedno znamení.
To zabrání kombinacím jako "kulhání na pravou + kulhání na levou".

Použití:
  python3 randomize_pasy.py                # 10 pasů, čísla CTH-0001 až CTH-0010
  python3 randomize_pasy.py --pocet 25
  python3 randomize_pasy.py --pocet 10 --start 50   # čísla od CTH-0050
  python3 randomize_pasy.py --pocet 10 --znameni 2  # každý pas má 2 znamení
  python3 randomize_pasy.py --povolani zelezo
"""

import argparse
import calendar
import json
import os
import random
import sys
from datetime import datetime, timedelta


# ── Výchozí cesty ──────────────────────────────────────────────────────────────
SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))
DATA_PATH     = os.path.join(SCRIPT_DIR, "data.json")
ZNAMENI_PATH  = os.path.join(SCRIPT_DIR, "znameni.json")
OUTPUT_PATH   = os.path.join(SCRIPT_DIR, "passports.json")


# ── Pomocné funkce ─────────────────────────────────────────────────────────────

def random_date(year_from: int, year_to: int) -> str:
    """
    Vygeneruje náhodné datum v zadaném rozmezí let.
    Výstupní formát: 'D.M.RRRR' (bez nul, jak je zvykem v češtině).
    """
    year  = random.randint(year_from, year_to)
    month = random.randint(1, 12)
    # monthrange vrátí (číslo prvního dne týdne, počet dní v měsíci)
    max_day = calendar.monthrange(year, month)[1]
    day   = random.randint(1, max_day)
    return f"{day}.{month}.{year}"


def random_expiration(expirace_config: dict, stav: str) -> str:
    """
    Vygeneruje datum expirace relativně k referenčnímu dni z data.json.

    `stav`:
      - "1" nebo "expirovane": 1 až max_dni_pred dní před aktuálním dnem
      - "0" nebo "validni":    1 až max_dni_po dní po aktuálním dni
    """
    aktualni_datum = datetime.strptime(expirace_config["aktualni_datum"], "%d.%m.%Y")

    if stav in ["1", "expirovane"]:
        max_posun = expirace_config["max_dni_pred"]
        delta = -random.randint(1, max_posun)
    else:
        max_posun = expirace_config["max_dni_po"]
        delta = random.randint(1, max_posun)

    expirace = aktualni_datum + timedelta(days=delta)
    return f"{expirace.day}.{expirace.month}.{expirace.year}"


def flatten_kategorie(znameni: dict) -> list[list[str]]:
    """
    Převede vnořenou strukturu znameni.json na plochý seznam podkategorií.

    Vstup (znameni.json):  { "skupina": { "podkategorie": ["znak1", ...], ... }, ... }
    Výstup:                [ ["znak1", ...], ["znak2", ...], ... ]

    Každá podkategorie tvoří skupinu vzájemně se vylučujících znamení.
    """
    flat = []
    for subgroups in znameni.values():
        for znaky in subgroups.values():
            flat.append(znaky)
    return flat


def pick_znameni(flat_kategorie: list[list[str]], count: int) -> list[str]:
    """
    Náhodně vybere `count` znamení z `count` různých podkategorií.

    Princip: náhodně se vyberou podkategorie (bez opakování),
    pak se z každé vybrané podkategorie zvolí jedno náhodné znamení.
    Takto nikdy nedostanou dva znaky ze stejné podkategorie.

    Pokud je `count` větší než počet podkategorií, použijí se všechny.
    """
    selected = random.sample(flat_kategorie, min(count, len(flat_kategorie)))
    return [random.choice(znaky) for znaky in selected]


def pick_povolani(
    povolani_podle_suroviny: dict[str, list[str]],
    vybrana_surovina: str | None = None,
) -> tuple[str, str]:
    """
    Vybere surovinu a odpovídající povolání ze stejné skupiny.

    Pokud je zadána `vybrana_surovina`, bere jen z této sekce.
    """
    if vybrana_surovina is None:
        surovina = random.choice(list(povolani_podle_suroviny.keys()))
    else:
        surovina = vybrana_surovina

    povolani = random.choice(povolani_podle_suroviny[surovina])
    return povolani, surovina


def generate_passport(
    data: dict,
    flat_kategorie: list[list[str]],
    cislo: int,
    znameni_count: int,
    expirace_stav: str,
    vybrana_surovina: str | None = None,
) -> dict:
    """
    Sestaví jeden náhodný pas.

    Parametry:
        data           – obsah data.json
        flat_kategorie – plochý seznam podkategorií (výstup flatten_kategorie)
        cislo          – číslo pasu (použije se pro CTH-XXXX)
        znameni_count  – počet zvláštních znamení (1–3)
        expirace_stav  – "expirovane" nebo "validni"
        vybrana_surovina – omezení výběru povolání na jednu sekci
    """
    # Pohlaví určuje, ze které skupiny jmen a příjmení se vybírá
    pohlavi  = random.choice(["M", "Ž"])
    jmeno    = random.choice(data["jmena"][pohlavi])
    prijmeni = random.choice(data["prijmeni"][pohlavi])

    datum_narozeni = random_date(
        data["datum_narozeni_rok_od"],
        data["datum_narozeni_rok_do"],
    )

    expirace = random_expiration(data["expirace"], expirace_stav)
    povolani, surovina = pick_povolani(data["povolani"], vybrana_surovina)
    znameni  = pick_znameni(flat_kategorie, znameni_count)

    return {
        "cislo_pasu":     f"CTH-{cislo:04d}",
        "jmeno":          f"{jmeno} {prijmeni}",
        "pohlavi":        pohlavi,
        "datum_narozeni": datum_narozeni,
        "expirace":       expirace,
        "povolani":       povolani,
        "surovina":       surovina,
        "znameni":        znameni,
    }


# ── Hlavní logika ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Generuje náhodné záznamy pasů a uloží je do passports.json."
    )
    parser.add_argument(
        "--pocet", type=int, default=10, metavar="N",
        help="Počet pasů k vygenerování (výchozí: 10).",
    )
    parser.add_argument(
        "--start", type=int, default=1, metavar="N",
        help="Počáteční číslo pasu CTH-XXXX (výchozí: 1).",
    )
    parser.add_argument(
        "--znameni", type=int, default=3, choices=[1, 2, 3], metavar="N",
        help="Počet zvláštních znamení na pas – 1, 2 nebo 3 (výchozí: 3).",
    )
    parser.add_argument(
        "--expirace", default="0", choices=["0", "1", "validni", "expirovane"], metavar="STAV",
        help="0/validni = neexpirované, 1/expirovane = expirované (výchozí: 0).",
    )
    parser.add_argument(
        "--povolani", default=None, metavar="SEKCE",
        help="Omezí výběr povolání na sekci: drevo, zelezo, latka, jidlo, vedomosti.",
    )
    parser.add_argument(
        "--output", default=OUTPUT_PATH, metavar="SOUBOR",
        help=f"Výstupní JSON soubor (výchozí: passports.json).",
    )
    args = parser.parse_args()

    # --- Načtení vstupních souborů -------------------------------------------
    for path in [DATA_PATH, ZNAMENI_PATH]:
        if not os.path.exists(path):
            sys.exit(f"[CHYBA] Soubor nenalezen: {path}")

    with open(DATA_PATH,    "r", encoding="utf-8") as f:
        data = json.load(f)

    with open(ZNAMENI_PATH, "r", encoding="utf-8") as f:
        kategorie = json.load(f)

    expirace_config = data.get("expirace", {})
    povolani_config = data.get("povolani", {})
    required_keys = ["aktualni_datum", "max_dni_pred", "max_dni_po"]
    missing_keys = [key for key in required_keys if key not in expirace_config]
    if missing_keys:
        sys.exit(
            "[CHYBA] V data.json chybí konfigurace expirace: "
            + ", ".join(missing_keys)
        )

    for key in ["max_dni_pred", "max_dni_po"]:
        if not isinstance(expirace_config[key], int) or expirace_config[key] < 1:
            sys.exit(f"[CHYBA] data.json -> expirace -> {key} musí být celé číslo >= 1.")

    try:
        datetime.strptime(expirace_config["aktualni_datum"], "%d.%m.%Y")
    except ValueError:
        sys.exit(
            "[CHYBA] data.json -> expirace -> aktualni_datum musí mít formát D.M.RRRR "
            "nebo DD.MM.RRRR."
        )

    if not isinstance(povolani_config, dict) or not povolani_config:
        sys.exit("[CHYBA] data.json -> povolani musí být neprázdný objekt skupin surovin.")

    for surovina, povolani_list in povolani_config.items():
        if not isinstance(povolani_list, list) or not povolani_list:
            sys.exit(
                f"[CHYBA] data.json -> povolani -> {surovina} musí být neprázdný seznam povolání."
            )

    if args.povolani is not None and args.povolani not in povolani_config:
        dostupne = ", ".join(povolani_config.keys())
        sys.exit(
            f"[CHYBA] Neznámá sekce povolání '{args.povolani}'. Dostupné: {dostupne}."
        )

    # Převede vnořenou strukturu na plochý seznam podkategorií
    flat_kategorie = flatten_kategorie(kategorie)

    # --- Kontrola, zda je dost kategorií pro požadovaný počet znamení --------
    if args.znameni > len(flat_kategorie):
        sys.exit(
            f"[CHYBA] Požadováno {args.znameni} znamení, "
            f"ale znameni.json obsahuje jen {len(flat_kategorie)} podkategorií."
        )

    # --- Generování pasů ------------------------------------------------------
    print(
        f"Generuji {args.pocet} pas(ů) "
        f"(znamení: {args.znameni}, expirace: {args.expirace}, start: CTH-{args.start:04d})…\n"
    )

    passports = []
    for i in range(args.pocet):
        passport = generate_passport(
            data,
            flat_kategorie,
            args.start + i,
            args.znameni,
            args.expirace,
            args.povolani,
        )
        passports.append(passport)

        expirace_str = passport["expirace"]
        print(f"  {passport['cislo_pasu']:^20} | {passport['povolani']:^20} | expirace: {expirace_str:^20}")

    # --- Uložení do JSON ------------------------------------------------------
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(passports, f, ensure_ascii=False, indent=2)

    print(f"\nUloženo → {args.output}")
    print("Nyní spusť:  python3 generate_pasy.py  pro vygenerování PDF.")


if __name__ == "__main__":
    main()
