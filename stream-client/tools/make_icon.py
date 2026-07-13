"""Generate shah-stream.ico for the Windows EXE from the logo PNG.

Composites the black-and-white logo onto a white rounded card (so it stays
visible on any background) and writes a multi-resolution .ico. Run once (or
whenever the logo changes):

    pip install pillow
    python tools/make_icon.py
"""

from __future__ import annotations

import os

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG_DIR = os.path.join(ROOT, "stream-client", "assests", "img")
SRC_PNG = os.path.join(IMG_DIR, "shah-logo.png")
OUT_ICO = os.path.join(IMG_DIR, "shah-stream.ico")

BASE = 256
RADIUS = int(BASE * 0.22)
PAD = int(BASE * 0.14)


def main() -> None:
    logo = Image.open(SRC_PNG).convert("RGBA")

    card = Image.new("RGBA", (BASE, BASE), (0, 0, 0, 0))
    mask = Image.new("L", (BASE, BASE), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, BASE - 1, BASE - 1], radius=RADIUS, fill=255)
    white = Image.new("RGBA", (BASE, BASE), (255, 255, 255, 255))
    card.paste(white, (0, 0), mask)

    inner = BASE - 2 * PAD
    logo_resized = logo.resize((inner, inner), Image.LANCZOS)
    card.alpha_composite(logo_resized, (PAD, PAD))

    card.save(
        OUT_ICO,
        format="ICO",
        sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)],
    )
    print("wrote", OUT_ICO)


if __name__ == "__main__":
    main()
