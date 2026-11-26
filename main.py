#!/usr/bin/env python3
"""Copy entry.png byte-for-byte into $MAKEFUN_OUTPUT_DIR (default: "out").

Standard library only; runs fully offline.
"""
import os
import shutil
import sys


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(here, "entry.png")
    if not os.path.isfile(src):
        sys.exit("entry.png not found next to main.py (run render.py first)")
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "out"
    os.makedirs(out_dir, exist_ok=True)
    shutil.copyfile(src, os.path.join(out_dir, "entry.png"))


if __name__ == "__main__":
    main()
