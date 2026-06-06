#!/usr/bin/env python3
"""Vygeneruje PDF receptar z recepty.json."""

from itertools import zip_longest
from pathlib import Path
import json
import re
import shutil
import subprocess
import sys
import tempfile


BASE_DIR = Path(__file__).resolve().parent
RECIPES_JSON = BASE_DIR / "recepty.json"
TEMPLATE = BASE_DIR / "receptar_template.tex"
ICONS_DIR = BASE_DIR / "ikonky"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_PDF = OUTPUT_DIR / "receptar.pdf"
OUTPUT_TEX = OUTPUT_DIR / "receptar.tex"

EMPTY = " "
ICONS = {
    "D": "drevo.png",
    "Z": "zelezo.png",
    "L": "latka.png",
    "J": "jidlo.png",
    "V": "vedomosti.png",
}


def latex_escape(value):
    text = str(value)
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in text)


def latex_path(path):
    return r"\detokenize{" + path.resolve().as_posix() + "}"


def parse_param(template, name):
    r"""Precte hodnotu \newcommand{\Name}{value} ze sablony."""
    pattern = r"\\newcommand\{\\" + re.escape(name) + r"\}\{([^}]*)\}"
    m = re.search(pattern, template)
    if not m:
        sys.exit(f"[CHYBA] Parametr \\{name} nebyl nalezen v sablone.")
    return m.group(1)


def parse_grid_params(template):
    """Nacte vizualni parametry mrizky ze sablony."""
    return {
        "cell_size": float(parse_param(template, "ParamGridCellMM")),
        "icon_size_mm": float(parse_param(template, "ParamGridIconMM")),
        "corner": parse_param(template, "ParamGridCorner"),
        "line_width_pt": float(parse_param(template, "ParamGridLinePt")),
    }


def strip_dummy(template):
    """Odstrani sekci dummy nahledu mezi %DUMMY_BEGIN a %DUMMY_END."""
    return re.sub(
        r"^%DUMMY_BEGIN$.*?^%DUMMY_END$\n?",
        "",
        template,
        flags=re.MULTILINE | re.DOTALL,
    )


def load_recipes():
    with RECIPES_JSON.open("r", encoding="utf-8") as file:
        recipes = json.load(file)

    if not isinstance(recipes, list):
        sys.exit("[CHYBA] recepty.json musi obsahovat primo seznam receptu.")

    return recipes


def validate_recipes(recipes):
    for recipe_index, recipe in enumerate(recipes, start=1):
        for key in ["name", "points", "grid"]:
            if key not in recipe:
                sys.exit(f"[CHYBA] Recept #{recipe_index} nema pole '{key}'.")

        grid = recipe["grid"]
        if len(grid) != 3 or any(len(row) != 3 for row in grid):
            sys.exit(f"[CHYBA] Recept '{recipe['name']}' nema grid 3 x 3.")

        for row_index, row in enumerate(grid, start=1):
            for col_index, cell in enumerate(row, start=1):
                if cell != EMPTY and cell not in ICONS:
                    sys.exit(
                        f"[CHYBA] Recept '{recipe['name']}', bunka {row_index},{col_index}: "
                        f"povolena je mezera nebo {', '.join(ICONS)}."
                    )

    for filename in ICONS.values():
        path = ICONS_DIR / filename
        if not path.exists():
            sys.exit(f"[CHYBA] Chybi ikonka: {path}")


def grid_to_latex(grid, params):
    cell_size = params["cell_size"]
    icon_size = f"{params['icon_size_mm']}mm"
    corner = params["corner"]
    line_width = f"{params['line_width_pt']}pt"

    lines = [
        r"\begin{tikzpicture}[x=1mm,y=1mm]",
        r"  \foreach \r in {0,1,2} {",
        r"    \foreach \c in {0,1,2} {",
        rf"      \draw[draw=gridline, fill=panel, line width={line_width}, rounded corners={corner}] (\c*{cell_size},-\r*{cell_size}) rectangle ++({cell_size},-{cell_size});",
        r"    }",
        r"  }",
    ]

    for row_index, row in enumerate(grid):
        for col_index, cell in enumerate(row):
            if cell == EMPTY:
                continue

            icon = ICONS_DIR / ICONS[cell]
            x = col_index * cell_size + cell_size / 2
            y = -(row_index * cell_size + cell_size / 2)
            lines.append(
                rf"  \node at ({x:.1f},{y:.1f}) "
                rf"{{\includegraphics[width={icon_size},height={icon_size},keepaspectratio]{{{latex_path(icon)}}}}};"
            )

    lines.append(r"\end{tikzpicture}")
    return "\n".join(lines)


def recipe_to_latex(recipe, params):
    name = latex_escape(recipe["name"])
    points = latex_escape(recipe["points"])
    grid = grid_to_latex(recipe["grid"], params)
    return f"\\recipeCard{{{name}}}{{Body: {points}}}{{%\n{grid}\n}}\n"


def recipes_to_latex(recipes, params):
    cards = [recipe_to_latex(recipe, params) for recipe in recipes]
    rows = []

    for left, right in zip_longest(cards[::2], cards[1::2], fillvalue=""):
        if right:
            rows.append(f"\\noindent\n{left}\\hfill\n{right}\\par\\vspace{{5mm}}")
        else:
            rows.append(f"\\noindent\n{left}\\par\\vspace{{5mm}}")

    return "\n\n".join(rows)


def compile_pdf(tex_content):
    if not shutil.which("pdflatex"):
        sys.exit("[CHYBA] pdflatex nebyl nalezen v PATH.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_TEX.write_text(tex_content, encoding="utf-8")

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        tex_file = tmpdir / "receptar.tex"
        pdf_file = tmpdir / "receptar.pdf"
        tex_file.write_text(tex_content, encoding="utf-8")

        for _ in range(2):
            result = subprocess.run(
                [
                    "pdflatex",
                    "-interaction=nonstopmode",
                    "-halt-on-error",
                    "-output-directory",
                    str(tmpdir),
                    str(tex_file),
                ],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                print("[CHYBA] pdflatex selhal.")
                print("\n".join(result.stdout.splitlines()[-20:]))
                sys.exit(1)

        shutil.copy2(pdf_file, OUTPUT_PDF)


def main():
    recipes = load_recipes()
    validate_recipes(recipes)

    template = TEMPLATE.read_text(encoding="utf-8")
    params = parse_grid_params(template)
    tex_content = (
        strip_dummy(template)
        .replace(r"\detokenize{__BOOK_TITLE__}", latex_escape("Receptář předmětů"))
        .replace("\\end{document}", recipes_to_latex(recipes, params) + "\n\\end{document}")
    )

    compile_pdf(tex_content)
    print(f"Vytvoren receptar: {OUTPUT_PDF}")
    print(f"Vytvoren TeX:      {OUTPUT_TEX}")
    print(f"Pocet receptu:     {len(recipes)}")
    print(f"Parametry mrizky:  cell={params['cell_size']}mm, icon={params['icon_size_mm']}mm, "
          f"corner={params['corner']}, border={params['line_width_pt']}pt")


if __name__ == "__main__":
    main()
