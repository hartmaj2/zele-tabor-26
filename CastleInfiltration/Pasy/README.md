# Renderování pasů

Pasy používají LaTeXovou šablonu `pas_template.tex` do které se pak pomocí skriptu `generate_pasy.py` vloží hodnoty z konfiguračního souboru `passports.json`

## pas_template.tex

- obsahuje okomentované jednotlivé sekce 

- pro uživatele jsou důležité:
  - KONFIGURACE
    - úprava různých vizuálních parametrů pasu (velikost mezer, fotografie, font písma atd.)
  - ÚDAJE PASU
    - LaTeX commandy, které se pak propíšou do odpovídajících políček
    - důležité je, že pokud zůstanou prázdné některé ze tří atributů, tak to nevadí (postará se o to command ZnameniItem)

- programátorsky důležitý je přepínač `\newif\ifzadniStrana \zadniStranatrue`
  - používá se k volbě, zda chceme renderovat i zadní stranu
  - python generátor si toto přepíše, aby zbytečně negeneroval zadní stranu (vždy je stejná)
  
## passports.json

- je to seznam položek ve formátu

```json
{
"cislo_pasu": "CTH-0001",
"jmeno": "Bartoloměj Bystroň",
"pohlavi": "M",
"datum_narozeni": "23.3.2015",
"expirace": "18.8.2026",
"povolani": "Truhlář",
"surovina": "drevo",
"znameni": [
    "dlouhé vousy",
    "přimhouřené oči",
    "obří boty"
]
}
```

## generate_pasy.py

Vezme data z jsonů, načte si tex šablonu, nahradí v ní odpovídající pole hodnotami z jsonu a nově vzniklý tex vyrenderuje do složky ouptut

# Náhodné generování dat pro pasy

O to se stará `randomize_pasy,py`, které čte soubory `data.json` a `znameni.json`

Je možné volit: 
- počet výstupů
- jaká povolání se budou vytvářet
- zda pasy mají být expirované či nikoliv

Použití:
  python3 randomize_pasy.py                # 10 pasů, čísla CTH-0001 až CTH-0010
  python3 randomize_pasy.py --pocet 25
  python3 randomize_pasy.py --pocet 10 --start 50   # čísla od CTH-0050
  python3 randomize_pasy.py --pocet 10 --znameni 2  # každý pas má 2 znamení
  python3 randomize_pasy.py --povolani zelezo

## data.json

Zde je důležité nastavit aktuální datum na datum, kdy má hra proběhnout.

```json
  "expirace": {
    "aktualni_datum": "5.8.2026",
    "max_dni_pred": 10,
    "max_dni_po": 10
  }
```