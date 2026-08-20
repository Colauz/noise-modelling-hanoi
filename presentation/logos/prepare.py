#!/usr/bin/env python3
"""Turn the institutional marks in source/ into the files the deck uses.

WHY THIS EXISTS. `main.tex` sizes every logo by HEIGHT (`\\logoheight`). A mark
delivered with a generous white margin therefore renders smaller than its
neighbours by exactly the margin's share of the bounding box -- the VinUniversity
file arrives 500x500 with the wordmark occupying a 90 px band, so dropped in
untouched it would come out about a fifth the size of the others. Trimming is not
cosmetic here; it is what makes a row of logos look like a row.

WHAT IT DOES.

  1. Trims the uniform border, whether it is transparent or a flat colour.
  2. Flattens onto white, because a JPEG has no alpha and the slides are light.
  3. Pads back a small, EQUAL margin so the marks do not touch each other.
  4. Applies a per-mark optical correction (see OPTICAL below) and writes
     <name>.png next to this script.

OPTICAL WEIGHT. Matching bounding-box heights is not the same as matching
apparent size. A circular badge scaled to a wordmark's cap height reads as much
larger than the wordmark, because the wordmark's height is its capitals while the
badge's is its full diameter. The factors below correct that by eye; they are the
one judgement call in this file and they are meant to be adjusted by looking at
the title slide, not by computing anything.

    python3 presentation/logos/prepare.py
    make -C presentation logos          # check what the deck will find
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow is not installed:  pip install Pillow")

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "source"

# Extra canvas height added around a mark, as a multiple of its own height. The
# deck scales to a fixed height, so PADDING THE BOX IS HOW A MARK IS MADE SMALLER:
# 1.0 leaves it at full size, 1.2 renders it a sixth smaller. Values below 1.0 do
# nothing -- a mark cannot be drawn larger than \logoheight.
OPTICAL = {
    "cosmos": 1.00,   # a round badge is already narrow at a matched height
    "vinuni": 1.00,
    "isima": 1.00,
    "uca": 1.00,
}

# Margin added back after trimming, as a fraction of the trimmed height.
MARGIN = 0.06


def trim(im: Image.Image) -> Image.Image:
    """Drop a uniform border, transparent or flat-coloured."""
    if im.mode in ("RGBA", "LA") and im.getchannel("A").getextrema()[0] < 255:
        box = im.getchannel("A").getbbox()
    else:
        rgb = im.convert("RGB")
        # The corner pixel is the background by assumption -- true of every
        # logo delivered as a file, and visibly false the moment it is not.
        bg = Image.new("RGB", rgb.size, rgb.getpixel((0, 0)))
        from PIL import ImageChops

        box = ImageChops.difference(rgb, bg).convert("L").point(
            lambda p: 255 if p > 12 else 0
        ).getbbox()
    return im.crop(box) if box else im


def flatten(im: Image.Image) -> Image.Image:
    """Composite onto white. The slides are light and a JPEG has no alpha."""
    im = im.convert("RGBA")
    out = Image.new("RGBA", im.size, (255, 255, 255, 255))
    out.alpha_composite(im)
    return out


def prepare(src: Path) -> Path:
    name = src.stem
    im = flatten(trim(Image.open(src)))

    scale = OPTICAL.get(name, 1.0)
    if scale != 1.0:
        # Scaling the CANVAS, not the image: the deck fixes the height, so
        # padding the box is how a mark is made to render smaller.
        pad = int(im.height * (scale - 1) / 2)
        boxed = Image.new("RGBA", (im.width, im.height + 2 * pad),
                          (255, 255, 255, 255))
        boxed.paste(im, (0, pad))
        im = boxed

    m = int(im.height * MARGIN)
    out = Image.new("RGBA", (im.width + 2 * m, im.height + 2 * m),
                    (255, 255, 255, 255))
    out.paste(im, (m, m))

    # 600 px on the long edge is the floor logos/README.md asks for; upscaling a
    # small source would only add blur, so this only ever shrinks.
    if max(out.size) > 1400:
        r = 1400 / max(out.size)
        out = out.resize((round(out.width * r), round(out.height * r)),
                         Image.LANCZOS)

    dst = HERE / f"{name}.png"
    out.convert("RGB").save(dst, "PNG", optimize=True)
    return dst


def main() -> None:
    if not SOURCE.is_dir():
        sys.exit(f"{SOURCE} does not exist. Put the original marks there, named "
                 "cosmos / vinuni / isima / uca, in any raster format.")
    files = sorted(p for p in SOURCE.iterdir()
                   if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp"})
    if not files:
        sys.exit(f"No image files in {SOURCE}.")
    for src in files:
        dst = prepare(src)
        w, h = Image.open(dst).size
        print(f"  {src.name:24} -> {dst.name:14} {w}x{h}")
    print("\nThe deck prefers <name>.pdf over <name>.png. Delete any leftover "
          "placeholder PDFs or they will shadow these.")


if __name__ == "__main__":
    main()
