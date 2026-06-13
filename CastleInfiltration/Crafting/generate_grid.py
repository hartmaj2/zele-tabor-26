#!/usr/bin/env python3
"""generate_grid.py – Tiskový arch prázdných 3×3 mřížek na A4

Každá buňka mřížky má stejnou velikost jako políčko batohu z pas_template.tex
(\\batohBunkaSirka). Samolepky z generate_stickers.py přesně pasují do buněk.

Na každou A4 stranu se vejde více mřížek, oddělených malou mezerou pro ořez.

Použití:
  python3 generate_grid.py           # 1 strana
  python3 generate_grid.py --pages 3
"""

import argparse
import os
import sys

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
except ImportError:
    sys.exit("[CHYBA] Nainstaluj knihovnu:  pip install reportlab")

from sizes import BATOH_BUNKA_MM

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "grids.pdf")

CELL       = BATOH_BUNKA_MM * mm
GRID_COLS  = 3
GRID_ROWS  = 3
GRID_W     = GRID_COLS * CELL
GRID_H     = GRID_ROWS * CELL
GAP        = 2 * mm   # mezera mezi mřížkami pro ořez

A4_W, A4_H = A4
GRIDS_X = int(A4_W // (GRID_W + GAP))
GRIDS_Y = int(A4_H // (GRID_H + GAP))
OFFSET_X = (A4_W - GRIDS_X * (GRID_W + GAP) + GAP) / 2
OFFSET_Y = (A4_H - GRIDS_Y * (GRID_H + GAP) + GAP) / 2


def draw_page(c):
    for gy in range(GRIDS_Y):
        for gx in range(GRIDS_X):
            ox = OFFSET_X + gx * (GRID_W + GAP)
            oy = OFFSET_Y + gy * (GRID_H + GAP)
            # inner cell lines
            c.setStrokeColorRGB(0.6, 0.6, 0.6)
            c.setLineWidth(0.3)
            for row in range(GRID_ROWS):
                for col in range(GRID_COLS):
                    c.rect(ox + col * CELL, oy + row * CELL, CELL, CELL)
            # thick outer border
            c.setStrokeColorRGB(0.2, 0.2, 0.2)
            c.setLineWidth(1.5)
            c.rect(ox, oy, GRID_W, GRID_H)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pages", type=int, default=1,
                        help="Počet stran (výchozí: 1).")
    args = parser.parse_args()

    print(f"Buňka: {BATOH_BUNKA_MM:.1f} mm × {BATOH_BUNKA_MM:.1f} mm")
    print(f"Mřížek na stranu: {GRIDS_X}×{GRIDS_Y} = {GRIDS_X * GRIDS_Y}")

    c = canvas.Canvas(OUTPUT_PATH, pagesize=A4)
    for _ in range(args.pages):
        draw_page(c)
        c.showPage()
    c.save()

    print(f"Hotovo! {args.pages} stran uloženo: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
