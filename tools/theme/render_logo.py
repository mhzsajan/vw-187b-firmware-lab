#!/usr/bin/env python3
"""Convert a VW 187B (NoName platform) boot splash blob to PNG.

The community "Skoda theme" packs ship `script/logo.bin`: an 800x480 raw framebuffer
image (4 bytes/pixel, BGRA on the analysed unit) prefixed by 4 header bytes,
total 1,536,004 bytes, which the update script writes with
`dd if=.../logo.bin of=/dev/mtdblock5`.

Usage:
    python render_logo.py logo.bin -o skoda.png
    python render_logo.py logo.bin -o out.png --width 800 --height 480 --offset 4
    python render_logo.py logo.bin -o out.png --channel-order rgbx   # if colours look wrong

Reverse direction (PNG -> logo.bin) is a roadmap item.
"""
from __future__ import annotations

import argparse
import sys

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    sys.exit("Pillow is required: pip install pillow")

RAW_MODES = {
    # PIL raw decoder identifier : bytes per pixel order
    "bgra": "BGRA",
    "rgba": "RGBA",
    "argb": "ARGB",
    "rgbx": "RGBX",
    "bgrx": "BGRX",
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", help="logo.bin from a logo/theme overlay tar")
    ap.add_argument("-o", "--out", default="logo.png", help="output PNG path")
    ap.add_argument("--width", type=int, default=800)
    ap.add_argument("--height", type=int, default=480)
    ap.add_argument("--offset", type=int, default=4, help="bytes before the pixel data (4 in known packs)")
    ap.add_argument("--channel-order", default="bgra", choices=sorted(RAW_MODES),
                    help="byte order of the pixel data; try 'rgbx'/'rgba' if colours are swapped")
    ap.add_argument("--force-alpha", action="store_true",
                    help="set alpha to opaque (known packs store 0 in the alpha byte)")
    a = ap.parse_args()

    raw = open(a.path, "rb").read()
    px_len = a.width * a.height * 4
    payload = raw[a.offset:]
    if len(payload) < px_len:
        sys.exit(f"need {px_len} bytes of pixels, file has {len(payload)} after offset {a.offset}")
    pixels = bytearray(payload[:px_len])
    if a.force_alpha:
        for i in range(3, px_len, 4):
            pixels[i] = 0xFF

    img = Image.frombytes("RGBA", (a.width, a.height), bytes(pixels), "raw", RAW_MODES[a.channel_order])
    if not a.force_alpha:
        img = img.convert("RGB")
    img.save(a.out)
    print(f"wrote {a.out}  {a.width}x{a.height}  from {a.path} "
          f"(offset={a.offset}, order={a.channel_order}, alpha_forced={a.force_alpha})")


if __name__ == "__main__":
    main()
