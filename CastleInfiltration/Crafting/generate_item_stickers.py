#!/usr/bin/env python3
"""Print item-icon stickers on A4, using almost the whole page."""

import argparse
import os
import sys

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
except ImportError:
    sys.exit("[CHYBA] Nainstaluj knihovnu: pip install reportlab")


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ICONS_DIR = os.path.join(SCRIPT_DIR, "ikonky_predmety")
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "stickers_predmety.pdf")

A4_W, A4_H = A4
COLS = 10
ROWS = 14
STICKER = min(A4_W / COLS, A4_H / ROWS)
OFFSET_X = (A4_W - COLS * STICKER) / 2
OFFSET_Y = (A4_H - ROWS * STICKER) / 2


def draw_page(c, image_path):
    for row in range(ROWS):
        for col in range(COLS):
            x = OFFSET_X + col * STICKER
            y = OFFSET_Y + row * STICKER
            c.drawImage(
                image_path,
                x,
                y,
                width=STICKER,
                height=STICKER,
                preserveAspectRatio=True,
                anchor="c",
                mask="auto",
            )
            c.setStrokeColorRGB(0.6, 0.6, 0.6)
            c.setLineWidth(0.3)
            c.rect(x, y, STICKER, STICKER)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pages", type=int, default=1, help="Pages per icon.")
    args = parser.parse_args()

    icons = sorted(name for name in os.listdir(ICONS_DIR) if name.lower().endswith(".png"))
    if not icons:
        sys.exit(f"[CHYBA] Zadna PNG ikonka nenalezena v {ICONS_DIR}")

    print(f"Sticker size: {STICKER / mm:.1f} mm x {STICKER / mm:.1f} mm")
    print(f"Grid: {COLS}x{ROWS} = {COLS * ROWS} stickers per page")
    print(f"Pages per icon: {args.pages}\n")

    c = canvas.Canvas(OUTPUT_PATH, pagesize=A4)
    for icon_name in icons:
        icon_path = os.path.join(ICONS_DIR, icon_name)
        for page in range(args.pages):
            draw_page(c, icon_path)
            c.showPage()
            print(f"  {icon_name} - page {page + 1}/{args.pages}")

    c.save()
    print(f"\nDone: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
