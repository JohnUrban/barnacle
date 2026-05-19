#!/usr/bin/env python3
"""Render docs/icons/map_annotated.png from map_raw.png + map_points.csv.

Annotation style:
  - Filled colored dot at exact (x, y) — blue for landmarks, red for
    extra topography points
  - Bold value label with a white halo (PathEffects.withStroke)
  - Small offset between dot and label so dots stay visible

Usage:
    python assets/render_map.py
    python assets/render_map.py --out /tmp/preview.png   # write somewhere else
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import matplotlib.patheffects as PathEffects

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
DEFAULT_CSV = HERE / "map_points.csv"
DEFAULT_IMG = REPO_ROOT / "docs" / "icons" / "map_raw.png"
DEFAULT_OUT = REPO_ROOT / "docs" / "icons" / "map_annotated.png"

LANDMARK_COLOR = "#1f6feb"   # blue
EXTRA_COLOR    = "#d2444a"   # red


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv",   default=str(DEFAULT_CSV))
    ap.add_argument("--image", default=str(DEFAULT_IMG))
    ap.add_argument("--out",   default=str(DEFAULT_OUT))
    ap.add_argument("--dpi",   type=int, default=200,
                    help="DPI for the output PNG (default 200)")
    args = ap.parse_args()

    img = mpimg.imread(args.image)
    h, w = img.shape[:2]
    fig, ax = plt.subplots(figsize=(w / 100, h / 100), dpi=args.dpi)
    ax.imshow(img)
    ax.set_axis_off()

    n_landmark = 0
    n_extra = 0
    n_skipped = 0
    with open(args.csv) as f:
        for r in csv.DictReader(f):
            try:
                x = float(r["x"]); y = float(r["y"])
            except (ValueError, KeyError, TypeError):
                n_skipped += 1
                continue
            cat = r.get("category", "extra")
            color = LANDMARK_COLOR if cat == "landmark" else EXTRA_COLOR
            ax.plot(x, y, "o", color=color, markersize=6,
                    markeredgecolor="white", markeredgewidth=1.5, zorder=10)
            txt = ax.annotate(
                r.get("value", "?"), (x, y), color=color, fontsize=11,
                fontweight="bold", xytext=(8, -4),
                textcoords="offset points", zorder=11,
            )
            txt.set_path_effects(
                [PathEffects.withStroke(linewidth=2.5, foreground="white")]
            )
            if cat == "landmark":
                n_landmark += 1
            else:
                n_extra += 1

    plt.savefig(args.out, bbox_inches="tight", pad_inches=0, dpi=args.dpi)
    plt.close(fig)
    print(f"Wrote {args.out}")
    print(f"  {n_landmark} landmarks (blue) + {n_extra} extras (red); "
          f"{n_skipped} rows skipped (no coords yet)")


if __name__ == "__main__":
    main()
