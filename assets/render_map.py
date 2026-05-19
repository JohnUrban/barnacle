#!/usr/bin/env python3
"""Render docs/icons/map_annotated.png from map_raw.png + map_points.csv.

Annotation style:
  - Filled colored dot at exact (x, y) — blue for landmarks, red for
    extra topography points
  - Bold value label with a white halo (PathEffects.withStroke)
  - Small offset between dot and label so dots stay visible

With --water-level W (NAVD88 feet), additionally renders a smooth
semi-transparent blue overlay showing predicted water depth: shallower
areas get light, transparent blue; deeper areas get darker, more opaque
blue. Uses matplotlib's Delaunay triangulation across the CSV points
(no scipy dep needed). Dry triangles (all corners above water) render
transparent.

Usage:
    python assets/render_map.py
    python assets/render_map.py --water-level 3.85
    python assets/render_map.py --water-level 3.85 --out docs/icons/map_today.png
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import matplotlib.patheffects as PathEffects
import matplotlib.tri as mtri
from matplotlib.colors import LinearSegmentedColormap

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
DEFAULT_CSV = HERE / "map_points.csv"
DEFAULT_IMG = REPO_ROOT / "docs" / "icons" / "map_raw.png"
DEFAULT_OUT = REPO_ROOT / "docs" / "icons" / "map_annotated.png"

LANDMARK_COLOR = "#1f6feb"   # blue
EXTRA_COLOR    = "#d2444a"   # red


def make_blue_alpha_cmap(n=256):
    """Transparent at depth=0, deepening blue + opacity for larger depths."""
    blues = plt.cm.Blues(np.linspace(0.25, 1.0, n))
    blues[:, 3] = np.linspace(0.0, 0.85, n)  # alpha 0 -> 0.85
    return LinearSegmentedColormap.from_list("BluesAlpha", blues)


def load_points(csv_path):
    """Returns (rows, points_xy, elevs) where points_xy/elevs are the
    rows with all of x, y, value numeric."""
    rows = []
    points_xy = []
    elevs = []
    with open(csv_path) as f:
        for r in csv.DictReader(f):
            rows.append(r)
            try:
                x = float(r["x"]); y = float(r["y"])
                v = float(r["value"])
            except (ValueError, TypeError, KeyError):
                continue
            points_xy.append((x, y))
            elevs.append(v)
    return rows, points_xy, elevs


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv",   default=str(DEFAULT_CSV))
    ap.add_argument("--image", default=str(DEFAULT_IMG))
    ap.add_argument("--out",   default=str(DEFAULT_OUT))
    ap.add_argument("--dpi",   type=int, default=200,
                    help="DPI for the output PNG (default 200)")
    ap.add_argument("--water-level", type=float, default=None,
                    help="Predicted water level (ft NAVD88). When set, "
                         "renders a smooth blue depth overlay.")
    ap.add_argument("--title", default=None,
                    help="Optional title for the figure (only used with "
                         "--water-level by default).")
    ap.add_argument("--show-labels", action="store_true",
                    help="When --water-level is set, also draw the labeled "
                         "elevation dots on top of the overlay. Off by "
                         "default in heat-map mode (the NAVD88 labels can "
                         "be mistaken for predicted depths).")
    args = ap.parse_args()

    img = mpimg.imread(args.image)
    h, w = img.shape[:2]
    fig, ax = plt.subplots(figsize=(w / 100, h / 100), dpi=args.dpi)
    ax.imshow(img)
    ax.set_axis_off()

    rows, points_xy, elevs = load_points(args.csv)

    heatmap_mode = args.water_level is not None and len(points_xy) >= 3

    # === Heat-map overlay (only when water level supplied) ===
    if heatmap_mode:
        xs = np.array([p[0] for p in points_xy])
        ys = np.array([p[1] for p in points_xy])
        depths_ft = np.array(
            [max(0.0, args.water_level - e) for e in elevs]
        )
        triang = mtri.Triangulation(xs, ys)
        cmap = make_blue_alpha_cmap()
        # Cap at 2 ft so a single very-low pocket doesn't squash the
        # palette for the everywhere-else gradient
        max_d = max(0.5, min(float(depths_ft.max()), 2.0))
        levels = np.linspace(0.0, max_d, 30)
        ax.tricontourf(triang, depths_ft, levels=levels, cmap=cmap,
                       zorder=5, extend="max")
        title = args.title or (
            f"Predicted water level — {args.water_level:.2f} ft NAVD88"
        )
        ax.set_title(title, fontsize=14, fontweight="bold")
    elif args.title:
        ax.set_title(args.title, fontsize=14, fontweight="bold")

    # === Dots and labels ===
    # In heat-map mode the labels are NAVD88 elevations, which read as
    # "predicted depths" against a depth-encoded overlay — confusing.
    # Hide labels in heat-map mode unless --show-labels is set.
    draw_labels = (not heatmap_mode) or args.show_labels
    n_landmark = 0
    n_extra = 0
    n_skipped = 0
    if draw_labels:
        for r in rows:
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
    else:
        # Still count for the summary line, but don't render
        for r in rows:
            try:
                float(r["x"]); float(r["y"])
            except (ValueError, KeyError, TypeError):
                n_skipped += 1
                continue
            cat = r.get("category", "extra")
            if cat == "landmark":
                n_landmark += 1
            else:
                n_extra += 1

    plt.savefig(args.out, bbox_inches="tight", pad_inches=0, dpi=args.dpi)
    plt.close(fig)
    print(f"Wrote {args.out}")
    print(f"  {n_landmark} landmarks (blue) + {n_extra} extras (red); "
          f"{n_skipped} rows skipped (no coords yet)"
          + ("" if draw_labels else " — labels HIDDEN (heat-map mode)"))
    if args.water_level is not None:
        print(f"  Heat-map overlay rendered for water level "
              f"{args.water_level:.2f} ft NAVD88")


if __name__ == "__main__":
    main()
