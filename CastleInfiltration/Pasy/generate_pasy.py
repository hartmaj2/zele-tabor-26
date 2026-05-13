#!/usr/bin/env python3
"""
generate_pasy.py – Generátor cestovních pasů pro CTH (Infiltrace hradu)
=======================================================================

Pro každý záznam v passports.json skript:
  1. Načte šablonu pas_template.tex
  2. Nahradí hard-kódované \newcommand hodnoty daty z JSON
  3. Zkompiluje výsledný .tex soubor pomocí pdflatex (2x pro správné tikz rozložení)
  4. Uloží výstupní PDF do složky output/ pod názvem <cislo_pasu>.pdf

Požadavky:
  - Python 3.6+
  - pdflatex (TeX Live / MacTeX) dostupný v PATH

Použití:
  python3 generate_pasy.py
  python3 generate_pasy.py --json /cesta/k/jinemu/souboru.json
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile


# ── Výchozí cesty (relativní k umístění tohoto skriptu) ──────────────────────
SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(SCRIPT_DIR, "pas_template.tex")
JSON_PATH     = os.path.join(SCRIPT_DIR, "passports.json")
OUTPUT_DIR    = os.path.join(SCRIPT_DIR, "output")


# ── Pomocné funkce ────────────────────────────────────────────────────────────

def substitute_values(template: str, passport: dict) -> str:
    """
    Nahradí hodnoty \newcommand příkazů v LaTeX šabloně hodnotami z JSON záznamu.

    Šablona obsahuje řádky ve tvaru:
        \\newcommand{\\pasJmeno}{Bartoloměj Křivohlávek}

    Tato funkce nahradí pouze část v druhých složených závorkách {…},
    přičemž název příkazu zůstane beze změny.

    Parametry:
        template  – celý obsah .tex souboru jako řetězec
        passport  – slovník s daty jednoho pasu (záznam z JSON)

    Vrátí upravenou šablonu jako řetězec.
    """

    # Zvláštní znamení – musí být přesně 3; doplní se prázdnými řetězci
    znameni = passport.get("znameni", [])
    znameni = (znameni + ["", "", ""])[:3]

    # Mapování: název LaTeX příkazu → nová hodnota
    mapping = {
        "pasJmeno":         passport["jmeno"],
        "pasPohlavi":       passport["pohlavi"],
        "pasDatumNarozeni": passport["datum_narozeni"],
        "pasExpirace":      passport["expirace"],
        "pasPovolani":      passport["povolani"],
        "pasVlastnostiA":   znameni[0],
        "pasVlastnostiB":   znameni[1],
        "pasVlastnostiC":   znameni[2],
        "pasCisloPasu":     passport["cislo_pasu"],
    }

    # Skript generuje pouze přední stranu
    result = template.replace(r"\zadniStranatrue", r"\zadniStranafalse")

    for cmd_name, new_value in mapping.items():
        # Regex: najde \newcommand{\<cmd_name>}{<cokoliv>}
        # a nahradí obsah druhých závorek novou hodnotou.
        # [^}]* matchuje vše kromě } (předpokládá, že hodnota neobsahuje }).
        pattern     = r"(\\newcommand\{\\" + re.escape(cmd_name) + r"\})\{[^}]*\}"
        replacement = r"\1{" + new_value + "}"
        result      = re.sub(pattern, replacement, result)

    return result


def compile_pdf(tex_content: str, output_path: str) -> bool:
    """
    Zapíše LaTeX obsah do dočasného souboru, zkompiluje ho pdflatexem
    a zkopíruje výsledné PDF na output_path.

    pdflatex je spuštěn dvakrát – to je nutné pro správné vykreslení
    tikz/pgf překryvů (AddToShipoutPictureBG).

    Vrátí True při úspěchu, False při chybě.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tex_file = os.path.join(tmpdir, "pas.tex")
        pdf_file = os.path.join(tmpdir, "pas.pdf")

        # Zápis upraveného .tex souboru
        with open(tex_file, "w", encoding="utf-8") as f:
            f.write(tex_content)

        # Dvojí kompilace pro korektní tikz layout
        for run_index in range(1, 3):
            result = subprocess.run(
                [
                    "pdflatex",
                    "-interaction=nonstopmode",   # neinteraktivní režim
                    "-output-directory", tmpdir,
                    tex_file,
                ],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                print(f"    [CHYBA] pdflatex selhal (průchod {run_index}).")
                # Vypíše posledních 20 řádků logu pro diagnostiku
                log_lines = result.stdout.splitlines()
                for line in log_lines[-20:]:
                    print(f"      {line}")
                return False

        # Kontrola, zda PDF skutečně vzniklo
        if not os.path.exists(pdf_file):
            print("    [CHYBA] PDF nebylo vytvořeno (pdflatex neskončil chybou, ale PDF chybí).")
            return False

        # Přesun do výstupní složky
        shutil.copy2(pdf_file, output_path)
        return True


def validate_passport(passport: dict, index: int) -> list[str]:
    """
    Zkontroluje, zda záznam pasu obsahuje všechna povinná pole.
    Vrátí seznam chybových zpráv (prázdný seznam = vše ok).
    """
    required_fields = ["cislo_pasu", "jmeno", "pohlavi", "datum_narozeni",
                        "expirace", "povolani", "znameni"]
    errors = []

    for field in required_fields:
        if field not in passport:
            errors.append(f"Pas #{index}: chybí povinné pole '{field}'.")

    if "znameni" in passport:
        if not isinstance(passport["znameni"], list):
            errors.append(f"Pas #{index}: pole 'znameni' musí být seznam (list).")
        elif not (1 <= len(passport["znameni"]) <= 3):
            errors.append(
                f"Pas #{index} ({passport.get('cislo_pasu', '?')}): "
                f"'znameni' musí mít 1 až 3 položky, nalezeno {len(passport['znameni'])}."
            )

    return errors


# ── Hlavní logika ─────────────────────────────────────────────────────────────

def main():
    # --- Argumenty příkazové řádky -------------------------------------------
    parser = argparse.ArgumentParser(
        description="Generuje PDF pasy pro CTH ze šablony a JSON dat."
    )
    parser.add_argument(
        "--template",
        default=TEMPLATE_PATH,
        help=f"Cesta k .tex šabloně (výchozí: {TEMPLATE_PATH})",
    )
    parser.add_argument(
        "--json",
        default=JSON_PATH,
        help=f"Cesta k JSON souboru s daty pasů (výchozí: {JSON_PATH})",
    )
    parser.add_argument(
        "--output",
        default=OUTPUT_DIR,
        help=f"Výstupní složka pro PDF soubory (výchozí: {OUTPUT_DIR})",
    )
    args = parser.parse_args()

    # --- Kontrola závislostí -------------------------------------------------
    if not shutil.which("pdflatex"):
        sys.exit(
            "[CHYBA] pdflatex nebyl nalezen v PATH.\n"
            "Nainstalujte TeX Live (Linux/Mac) nebo MiKTeX (Windows)."
        )

    # --- Načtení šablony -----------------------------------------------------
    if not os.path.exists(args.template):
        sys.exit(f"[CHYBA] Šablona nebyla nalezena: {args.template}")

    with open(args.template, "r", encoding="utf-8") as f:
        template = f.read()

    print(f"Šablona: {args.template}")

    # --- Načtení JSON dat ----------------------------------------------------
    if not os.path.exists(args.json):
        sys.exit(f"[CHYBA] JSON soubor nebyl nalezen: {args.json}")

    with open(args.json, "r", encoding="utf-8") as f:
        passports = json.load(f)

    if not passports:
        sys.exit("[CHYBA] JSON soubor neobsahuje žádný pas.")

    print(f"JSON:    {args.json}")
    print(f"Výstup:  {args.output}")
    print()

    # --- Validace všech záznamů před generováním -----------------------------
    all_errors = []
    for i, passport in enumerate(passports, start=1):
        all_errors.extend(validate_passport(passport, i))

    if all_errors:
        print("[CHYBA] Neplatná data v JSON:")
        for err in all_errors:
            print(f"  • {err}")
        sys.exit(1)

    # --- Příprava výstupní složky --------------------------------------------
    os.makedirs(args.output, exist_ok=True)

    # --- Generování PDF pro každý pas ----------------------------------------
    print(f"Generuji {len(passports)} pas(ů)…\n")

    success_count = 0
    fail_count    = 0

    for passport in passports:
        cislo = passport["cislo_pasu"]
        jmeno = passport["jmeno"]

        print(f"  [{cislo}]  {jmeno}")

        # Nahradí hodnoty v šabloně
        tex_content = substitute_values(template, passport)

        # Zkompiluje a uloží PDF
        output_path = os.path.join(args.output, f"{cislo}.pdf")
        success = compile_pdf(tex_content, output_path)

        if success:
            print(f"    → output/{cislo}.pdf  ✓")
            success_count += 1
        else:
            print(f"    → SELHALO pro {cislo}")
            fail_count += 1

    # --- Souhrn --------------------------------------------------------------
    print()
    print(f"Hotovo: {success_count} úspěšně, {fail_count} selhalo.")


if __name__ == "__main__":
    main()
