"""
Generate the VoiceOfIU app icon (.icns) from scratch — no design assets needed.

Draws a rounded-rect gradient tile with a soundwave glyph, renders all the
sizes macOS wants, and packs them with iconutil.

Usage:  .venv/bin/python scripts/make_icon.py
Output: assets/AppIcon.icns
"""

import os
import subprocess
import tempfile

from PIL import Image, ImageDraw

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
BG_TOP = (124, 108, 252)     # #7c6cfc accent
BG_BOTTOM = (74, 222, 128)    # #4ade80 green
FG = (255, 255, 255)


def _render(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Vertical gradient fill
    for y in range(size):
        t = y / size
        r = int(BG_TOP[0] * (1 - t) + BG_BOTTOM[0] * t)
        g = int(BG_TOP[1] * (1 - t) + BG_BOTTOM[1] * t)
        b = int(BG_TOP[2] * (1 - t) + BG_BOTTOM[2] * t)
        draw.line([(0, y), (size, y)], fill=(r, g, b, 255))

    # Rounded-rect mask (macOS squircle-ish)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, size, size], radius=int(size * 0.22), fill=255)
    img.putalpha(mask)

    # Centered soundwave: vertical bars of varying height
    d = ImageDraw.Draw(img)
    bars = [0.30, 0.55, 0.85, 0.55, 0.30]
    bar_w = size * 0.07
    gap = size * 0.05
    total = len(bars) * bar_w + (len(bars) - 1) * gap
    x = (size - total) / 2
    for h in bars:
        bar_h = size * h
        y0 = (size - bar_h) / 2
        d.rounded_rectangle([x, y0, x + bar_w, y0 + bar_h],
                            radius=bar_w / 2, fill=FG)
        x += bar_w + gap
    return img


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        iconset = os.path.join(tmp, "AppIcon.iconset")
        os.makedirs(iconset)
        for base in (16, 32, 128, 256, 512):
            _render(base).save(os.path.join(iconset, f"icon_{base}x{base}.png"))
            _render(base * 2).save(os.path.join(iconset, f"icon_{base}x{base}@2x.png"))
        icns = os.path.join(OUT_DIR, "AppIcon.icns")
        subprocess.run(["iconutil", "-c", "icns", iconset, "-o", icns], check=True)
        print(f"✅ Wrote {icns}")
        # Also keep a 512 PNG for the GUI / docs
        _render(512).save(os.path.join(OUT_DIR, "icon.png"))
        print(f"✅ Wrote {os.path.join(OUT_DIR, 'icon.png')}")


if __name__ == "__main__":
    main()
