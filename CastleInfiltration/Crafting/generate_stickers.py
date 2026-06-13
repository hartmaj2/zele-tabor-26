#!/usr/bin/env python3
"""generate_stickers.py – Tiskový arch samolepek na A4

Vytvoří stickers.pdf: pro každou ikonku z Crafting/ikonky/ vygeneruje
zadaný počet stran vyplněných mřížkou čtvercových samolepek.

Velikost samolepky = 22 mm × 22 mm  (= \\batohBunkaSirka z pas_template.tex,
beze škálování, protože 4 × A6 = A4).

Použití:
  python3 generate_stickers.py           # 1 strana na ikonku
  python3 generate_stickers.py --pages 3
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

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
IKONKY_DIR  = os.path.join(SCRIPT_DIR, "ikonky")
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "stickers.pdf")

# Must match \batohBunkaSirka in pas_template.tex (A6 = A4/4, no scaling)
STICKER = 22 * mm

A4_W, A4_H = A4
COLS = int(A4_W // STICKER)
ROWS = int(A4_H // STICKER)
OFFSET_X = (A4_W - COLS * STICKER) / 2
OFFSET_Y = (A4_H - ROWS * STICKER) / 2


def draw_page(c, image_path):
    for row in range(ROWS):
        for col in range(COLS):
            x = OFFSET_X + col * STICKER
            y = OFFSET_Y + row * STICKER
            c.drawImage(image_path, x, y, width=STICKER, height=STICKER,
                        preserveAspectRatio=True, anchor="c", mask="auto")
            c.setStrokeColorRGB(0.6, 0.6, 0.6)
            c.setLineWidth(0.3)
            c.rect(x, y, STICKER, STICKER)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pages", type=int, default=1,
                        help="Počet stran na každou ikonku (výchozí: 1).")
    args = parser.parse_args()

    icons = sorted(f for f in os.listdir(IKONKY_DIR) if f.lower().endswith(".png"))
    if not icons:
        sys.exit(f"[CHYBA] Žádné PNG soubory nenalezeny v {IKONKY_DIR}")

    print(f"Ikonky: {', '.join(icons)}")
    print(f"Mřížka: {COLS}×{ROWS} = {COLS * ROWS} samolepek na stranu")
    print(f"Stran na ikonku: {args.pages}\n")

    c = canvas.Canvas(OUTPUT_PATH, pagesize=A4)

    for icon_name in icons:
        icon_path = os.path.join(IKONKY_DIR, icon_name)
        for page_num in range(args.pages):
            draw_page(c, icon_path)
            c.showPage()
            print(f"  {icon_name} – strana {page_num + 1}/{args.pages}")

    c.save()
    print(f"\nHotovo! {len(icons) * args.pages} stran uloženo: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
