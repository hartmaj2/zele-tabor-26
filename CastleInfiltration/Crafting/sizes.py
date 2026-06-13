"""sizes.py – Sdílené rozměry čerpané z pas_template.tex"""

import os
import re

_TEX = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "..", "Pasy", "pas_template.tex")


def _mm(name):
    with open(_TEX, "r", encoding="utf-8") as f:
        for line in f:
            m = re.search(r'\\newcommand\{\\' + name + r'\}\{([\d.]+)mm\}', line)
            if m:
                return float(m.group(1))
    raise ValueError(f"\\{name} nenalezeno v {_TEX}")


# 22 mm – velikost jedné buňky batohu z pas_template.tex
BATOH_BUNKA_MM = _mm("batohBunkaSirka")
