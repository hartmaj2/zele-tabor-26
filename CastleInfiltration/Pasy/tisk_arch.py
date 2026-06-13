#!/usr/bin/env python3
"""tisk_arch.py – Tiskový arch pasů na A4 (přední + zadní strana)

Vytvoří tisk_arch.pdf: pro každé 4 pasy jedna strana předních stran,
následovaná stranou zadních stran (2×2 mřížka na A4).

Požadavky: pip install pypdf
"""

import os
import sys

try:
    from pypdf import PdfReader, PdfWriter, PageObject, Transformation
except ImportError:
    sys.exit("[CHYBA] Nainstaluj knihovnu:  pip install pypdf")

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR   = os.path.join(SCRIPT_DIR, "output")
TEMPLATE_PDF = os.path.join(SCRIPT_DIR, "pas_template.pdf")
OUTPUT_PATH  = os.path.join(SCRIPT_DIR, "tisk_arch.pdf")

PT   = 72 / 25.4
A4_W = 210 * PT
A4_H = 297 * PT
COLS, ROWS = 2, 2


def build_sheet(source_pages):
    sheet  = PageObject.create_blank_page(width=A4_W, height=A4_H)
    cell_w = A4_W / COLS
    cell_h = A4_H / ROWS

    for idx, src in enumerate(source_pages):
        src_w = float(src.mediabox.width)
        src_h = float(src.mediabox.height)
        scale = min(cell_w / src_w, cell_h / src_h)
        offset_x = (cell_w - src_w * scale) / 2
        offset_y = (cell_h - src_h * scale) / 2
        col = idx % COLS
        row = idx // COLS
        x = col * cell_w + offset_x
        y = A4_H - (row + 1) * cell_h + offset_y
        sheet.merge_transformed_page(src, Transformation().scale(scale).translate(x, y))

    return sheet


def main():
    pdf_files = sorted(f for f in os.listdir(OUTPUT_DIR) if f.lower().endswith(".pdf"))
    if not pdf_files:
        sys.exit(f"[CHYBA] Žádná PDF nenalezena v {OUTPUT_DIR}/")

    if not os.path.isfile(TEMPLATE_PDF):
        sys.exit(f"[CHYBA] Šablona nenalezena: {TEMPLATE_PDF}")
    back_page = PdfReader(TEMPLATE_PDF).pages[1]

    front_pages = [PdfReader(os.path.join(OUTPUT_DIR, f)).pages[0] for f in pdf_files]

    writer = PdfWriter()
    per_sheet = COLS * ROWS
    for i in range(0, len(front_pages), per_sheet):
        batch = front_pages[i:i + per_sheet]
        writer.add_page(build_sheet(batch))
        writer.add_page(build_sheet([back_page] * len(batch)))

    with open(OUTPUT_PATH, "wb") as f:
        writer.write(f)

    total = len(front_pages)
    sheets = (total + per_sheet - 1) // per_sheet
    print(f"Hotovo! {total} pasů → {sheets * 2} stran uloženo: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
