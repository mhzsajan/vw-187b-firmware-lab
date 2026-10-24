#!/usr/bin/env python3
"""Generate a Desay-compatible start-screen PPM from any 800x480 PNG.

Desay format (verified on SW0317 rootfs, /usr/share/rvc/logo/*.ppm):
    "P6\\n800 480\\n255\\n"  (15 bytes)
    + 800*480*3 = 1,152,000 bytes RGB
    + 384,000 bytes zero padding
    = 1,536,015 bytes total

Usage:
    python make_startscreen_ppm.py input.png -o Startscreen_Normal.ppm
    python make_startscreen_ppm.py input.png -o build/ --all-slots   # emit all 13 names
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys

try:
    import numpy as np
    from PIL import Image
except ImportError:  # pragma: no cover
    sys.exit("numpy and Pillow are required: pip install numpy pillow")

HEADER = b"P6\n800 480\n255\n"
W, H = 800, 480
PIXELS = W * H * 3          # 1,152,000
TOTAL = 1_536_015           # 15 + 1,152,000 + 384,000
PAD = TOTAL - len(HEADER) - PIXELS

SLOTS = [
    "Startscreen_Alltrack", "Startscreen_Beats_Audio", "Startscreen_Blue_Motion",
    "Startscreen_Dynaudio", "Startscreen_E_Golf", "Startscreen_Family", "Startscreen_GTD",
    "Startscreen_GTE", "Startscreen_GTI", "Startscreen_Normal", "Startscreen_R",
    "Startscreen_R_Line", "Startscreen_Twin_Drive",
]


def build(png_path: str) -> bytes:
    im = Image.open(png_path).convert("RGB")
    if im.size != (W, H):
        im = im.resize((W, H), Image.LANCZOS)
    rgb = np.array(im, dtype=np.uint8).tobytes()
    assert len(rgb) == PIXELS, len(rgb)
    blob = HEADER + rgb + bytes(PAD)
    assert len(blob) == TOTAL, len(blob)
    return blob


def verify(blob: bytes, out_png: str) -> bool:
    back = Image.frombytes("RGB", (W, H), blob[len(HEADER):len(HEADER) + PIXELS], "raw", "RGB")
    back.save(out_png)
    return True


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("png")
    ap.add_argument("-o", "--out", required=True, help="output .ppm file, or a directory with --all-slots")
    ap.add_argument("--all-slots", action="store_true",
                    help="write all 13 Startscreen_*.ppm names (recommended: makes the unit show the "
                         "screen regardless of the logo index)")
    ap.add_argument("--verify-png", default=None, help="decode the result back to a PNG for visual check")
    a = ap.parse_args()

    blob = build(a.png)
    md5 = hashlib.md5(blob).hexdigest()
    print(f"payload: {len(blob):,} bytes  md5={md5}")

    if a.all_slots:
        os.makedirs(a.out, exist_ok=True)
        for slot in SLOTS:
            p = os.path.join(a.out, slot + ".ppm")
            with open(p, "wb") as f:
                f.write(blob)
        print(f"wrote {len(SLOTS)} slot files into {a.out}")
        target = os.path.join(a.out, SLOTS[9] + ".ppm")
    else:
        with open(a.out, "wb") as f:
            f.write(blob)
        print(f"wrote {a.out}")
        target = a.out

    if a.verify_png:
        verify(open(target, "rb").read(), a.verify_png)
        print(f"verification image: {a.verify_png}")


if __name__ == "__main__":
    main()
