#!/usr/bin/env python3
"""Interactive picker for map_points.csv coordinates.

Opens docs/icons/map_raw.png in a matplotlib window. For each landmark
in map_points.csv that still has empty x/y, asks you to click on the
map. After the canonical landmarks are placed, accepts additional
"extra" topography points (clicking + answering label/value prompts in
the terminal). Updates map_points.csv on exit.

Usage:
    python assets/pick_coords.py
    python assets/pick_coords.py --redo   # clear existing coords first
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import matplotlib.patheffects as PathEffects

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
DEFAULT_CSV = HERE / "map_points.csv"
DEFAULT_IMG = REPO_ROOT / "docs" / "icons" / "map_raw.png"

LANDMARK_COLOR = "#1f6feb"   # blue
EXTRA_COLOR    = "#d2444a"   # red
FIELDS = ["label", "value", "category", "x", "y"]


def load_rows(path: Path):
    rows = []
    if path.exists():
        with open(path) as f:
            for r in csv.DictReader(f):
                rows.append({k: r.get(k, "") for k in FIELDS})
    return rows


def save_rows(path: Path, rows):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            # Normalize empty values
            r = {k: ("" if r.get(k) in (None, "") else r[k]) for k in FIELDS}
            w.writerow(r)


def has_coords(row):
    return row.get("x") not in ("", None) and row.get("y") not in ("", None)


def draw_existing(ax, img, rows):
    """Redraw image + any already-placed points."""
    ax.clear()
    ax.imshow(img)
    ax.set_axis_off()
    for r in rows:
        if not has_coords(r):
            continue
        try:
            x, y = float(r["x"]), float(r["y"])
        except (ValueError, TypeError):
            continue
        color = LANDMARK_COLOR if r.get("category") == "landmark" else EXTRA_COLOR
        ax.plot(x, y, "o", color=color, markersize=6,
                markeredgecolor="white", markeredgewidth=1.5, zorder=10)
        txt = ax.annotate(
            r.get("value", "?"), (x, y), color=color, fontsize=10,
            fontweight="bold", xytext=(7, -4), textcoords="offset points",
            zorder=11,
        )
        txt.set_path_effects(
            [PathEffects.withStroke(linewidth=2.5, foreground="white")]
        )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv",   default=str(DEFAULT_CSV))
    ap.add_argument("--image", default=str(DEFAULT_IMG))
    ap.add_argument("--redo",  action="store_true",
                    help="Clear x/y on every row before starting "
                         "(re-pick from scratch)")
    args = ap.parse_args()

    csv_path = Path(args.csv)
    img_path = Path(args.image)
    if not img_path.exists():
        print(f"ERROR: image not found: {img_path}", file=sys.stderr)
        sys.exit(1)

    rows = load_rows(csv_path)
    if args.redo:
        for r in rows:
            r["x"] = ""
            r["y"] = ""

    img = mpimg.imread(img_path)
    fig, ax = plt.subplots(figsize=(12, 9))
    draw_existing(ax, img, rows)
    plt.show(block=False)

    # ---- Phase 1: fill landmarks missing coords ----
    print("\nPhase 1: place the canonical landmarks.")
    print("Click on the map. Close the window or right-click to cancel.\n")
    for r in rows:
        if r.get("category") != "landmark" or has_coords(r):
            continue
        title = f"Click on: {r['label']}  ({r['value']} NAVD88)"
        ax.set_title(title, fontsize=14)
        plt.draw()
        try:
            pts = plt.ginput(n=1, timeout=0, mouse_stop=3)
        except Exception:
            print("Cancelled.")
            break
        if not pts:
            print(f"  Skipped {r['label']} (no click).")
            continue
        r["x"], r["y"] = f"{pts[0][0]:.2f}", f"{pts[0][1]:.2f}"
        draw_existing(ax, img, rows)
        plt.draw()
        print(f"  ✓ {r['label']} placed at ({r['x']}, {r['y']})")
        save_rows(csv_path, rows)  # save progress after each click

    # ---- Phase 2: add extra topography points ----
    print("\nPhase 2: add extra topography points.")
    print("Click on the map, then answer label/value in this terminal.")
    print("Close the window or right-click to finish.\n")
    while True:
        ax.set_title(
            "Add extra point — close window or right-click when done",
            fontsize=14,
        )
        plt.draw()
        try:
            pts = plt.ginput(n=1, timeout=0, mouse_stop=3)
        except Exception:
            break
        if not pts:
            break
        x, y = pts[0]
        print(f"\nClicked at ({x:.2f}, {y:.2f})")
        label = input("  Label (or empty to skip): ").strip()
        if not label:
            continue
        value = input("  Value (e.g., 4.20): ").strip()
        cat = input("  Category [extra]: ").strip() or "extra"
        rows.append({
            "label": label, "value": value, "category": cat,
            "x": f"{x:.2f}", "y": f"{y:.2f}",
        })
        draw_existing(ax, img, rows)
        save_rows(csv_path, rows)
        print(f"  ✓ Added {label}.")

    save_rows(csv_path, rows)
    print(f"\nSaved {len(rows)} rows to {csv_path}")
    print("Next: run `python assets/render_map.py` to regenerate "
          "docs/icons/map_annotated.png")


if __name__ == "__main__":
    main()
