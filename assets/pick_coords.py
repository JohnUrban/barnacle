#!/usr/bin/env python3
"""Interactive picker for map_points.csv coordinates — KEYBOARD-DRIVEN.

Opens docs/icons/map_raw.png in a matplotlib window. For each landmark
in map_points.csv that still has empty x/y, prompts you to position
the cursor over the spot, then press SPACE to place. Press U to undo
the last placed point. Press ESC or close the window to quit.

Why keyboard placement instead of click: macOS trackpad tap-to-click
+ matplotlib's click handler caused spurious placements when moving
the cursor or cmd+tabbing away to look up values in a PDF. SPACE-to-
place eliminates that — only deliberate keypresses register.

Usage:
    python assets/pick_coords.py
    python assets/pick_coords.py --redo   # clear existing coords first

Keys:
    SPACE  — place a point at the current cursor position
    U      — undo the last placed point
    ESC    — quit (saves CSV; resume any time)
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

import matplotlib
# Force TkAgg backend on macOS. The default `macosx` backend hides the figure
# window when its process loses focus (e.g., cmd+tab to a PDF reader), which
# breaks the picker workflow. TkAgg renders the window as a normal OS window
# that persists in the background and z-orders normally with other apps.
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import matplotlib.patheffects as PathEffects

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
DEFAULT_CSV = HERE / "map_points.csv"
DEFAULT_IMG = REPO_ROOT / "docs" / "icons" / "map_raw.png"

LANDMARK_COLOR = "#1f6feb"
EXTRA_COLOR    = "#d2444a"
PENDING_COLOR  = "#ff9800"  # not currently used; reserved for future
FIELDS = ["label", "value", "category", "x", "y"]


# ============================================================
# CSV I/O
# ============================================================
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
            r = {k: ("" if r.get(k) in (None, "") else r[k]) for k in FIELDS}
            w.writerow(r)


def has_coords(row):
    return row.get("x") not in ("", None) and row.get("y") not in ("", None)


# ============================================================
# Plot helpers
# ============================================================
def redraw(ax, img, rows):
    """Clear axes and replot everything from the current rows state."""
    ax.clear()
    ax.imshow(img)
    ax.set_axis_off()
    for r in rows:
        if not has_coords(r):
            continue
        try:
            x = float(r["x"]); y = float(r["y"])
        except (ValueError, TypeError):
            continue
        color = LANDMARK_COLOR if r.get("category") == "landmark" else EXTRA_COLOR
        ax.plot(x, y, "o", color=color, markersize=7,
                markeredgecolor="white", markeredgewidth=1.5, zorder=10)
        txt = ax.annotate(
            r.get("value", "?"), (x, y), color=color, fontsize=10,
            fontweight="bold", xytext=(7, -4), textcoords="offset points",
            zorder=11,
        )
        txt.set_path_effects(
            [PathEffects.withStroke(linewidth=2.5, foreground="white")]
        )


# ============================================================
# Main loop
# ============================================================
def main():
    ap = argparse.ArgumentParser(
        description="Pick (x,y) coordinates on map_raw.png for "
                    "map_points.csv. Keyboard-driven; SPACE to place, "
                    "U to undo, ESC to quit.",
    )
    ap.add_argument("--csv",   default=str(DEFAULT_CSV))
    ap.add_argument("--image", default=str(DEFAULT_IMG))
    ap.add_argument("--redo",  action="store_true",
                    help="Clear x/y on every row before starting")
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
        save_rows(csv_path, rows)

    img = mpimg.imread(img_path)
    fig, ax = plt.subplots(figsize=(13, 10))
    redraw(ax, img, rows)

    # Shared state between event handlers and the main loop
    state = {
        "cursor_x": None,        # latest cursor x in image coords
        "cursor_y": None,
        "pending":  None,        # 'place', 'undo', 'quit'
        "history":  [],          # stack: [{idx, was_new}, ...]
        "closed":   False,
    }

    def title_for(idx, msg=""):
        if 0 <= idx < len(rows):
            r = rows[idx]
            label = r["label"]; value = r["value"]; cat = r["category"]
            return (f"NEXT: {label}  ({value} {cat})    "
                    f"|  SPACE=place  U=undo  ESC=quit"
                    + (f"     |  {msg}" if msg else ""))
        return (f"Add extras (no more pre-seeded rows)    "
                f"|  SPACE=place + prompt  U=undo  ESC=quit"
                + (f"     |  {msg}" if msg else ""))

    def next_pending_idx():
        """Index of the next pre-seeded row with empty coords, or len(rows) if all placed."""
        for i, r in enumerate(rows):
            if not has_coords(r):
                return i
        return len(rows)

    def update_title():
        idx = next_pending_idx()
        msg = ""
        if state["cursor_x"] is not None:
            msg = f"cursor=({state['cursor_x']:.0f}, {state['cursor_y']:.0f})"
        ax.set_title(title_for(idx, msg), fontsize=12)
        fig.canvas.draw_idle()

    def on_motion(event):
        if event.inaxes == ax:
            state["cursor_x"] = event.xdata
            state["cursor_y"] = event.ydata
            update_title()

    def on_key(event):
        k = (event.key or "").lower()
        if k == " " or k == "space":
            state["pending"] = "place"
        elif k == "u":
            state["pending"] = "undo"
        elif k in ("escape", "esc"):
            state["pending"] = "quit"

    def on_close(event):
        state["closed"] = True

    # Suppress matplotlib's default 'q' quit so user can use it if they want;
    # we use ESC. (Keep 'q' available for matplotlib's own quit too.)
    fig.canvas.mpl_connect("motion_notify_event", on_motion)
    fig.canvas.mpl_connect("key_press_event", on_key)
    fig.canvas.mpl_connect("close_event", on_close)

    update_title()
    plt.show(block=False)

    print("\n=== pick_coords.py — keyboard-driven ===")
    print("Move cursor over a target, press SPACE to place.")
    print("U to undo, ESC (or close window) to quit. CSV saves after every action.\n")

    while not state["closed"]:
        # Use canvas.start_event_loop instead of plt.pause: plt.pause calls
        # show(block=False) every iteration, which on macOS re-raises the
        # window to the front and blocks cmd+tab to a reference PDF.
        fig.canvas.start_event_loop(0.05)

        action = state["pending"]
        if action is None:
            continue
        state["pending"] = None

        if action == "quit":
            break

        if action == "undo":
            if not state["history"]:
                print("  (nothing to undo)")
                continue
            last = state["history"].pop()
            idx = last["idx"]
            if last["was_new"]:
                removed = rows.pop(idx)
                print(f"  ✗ Undid: {removed['label']} (was a new extra)")
            else:
                rows[idx]["x"] = ""
                rows[idx]["y"] = ""
                print(f"  ✗ Undid: {rows[idx]['label']} (cleared coords)")
            save_rows(csv_path, rows)
            redraw(ax, img, rows)
            update_title()
            continue

        # action == "place"
        if state["cursor_x"] is None or state["cursor_y"] is None:
            print("  (cursor not on map — move it inside the image first)")
            continue
        x = round(float(state["cursor_x"]), 2)
        y = round(float(state["cursor_y"]), 2)

        idx = next_pending_idx()
        if idx < len(rows):
            # Place in the next pre-seeded landmark row
            rows[idx]["x"] = str(x)
            rows[idx]["y"] = str(y)
            state["history"].append({"idx": idx, "was_new": False})
            save_rows(csv_path, rows)
            redraw(ax, img, rows)
            update_title()
            print(f"  ✓ {rows[idx]['label']} placed at ({x}, {y})")
        else:
            # Extras mode — prompt for label/value in terminal
            print(f"\nExtra point at ({x}, {y}).")
            try:
                label = input("  Label (or empty to cancel): ").strip()
            except EOFError:
                continue
            if not label:
                continue
            value = input("  Value (e.g., 4.20): ").strip()
            cat = input("  Category [extra]: ").strip() or "extra"
            new_row = {"label": label, "value": value, "category": cat,
                       "x": str(x), "y": str(y)}
            rows.append(new_row)
            state["history"].append({"idx": len(rows) - 1, "was_new": True})
            save_rows(csv_path, rows)
            redraw(ax, img, rows)
            update_title()
            print(f"  ✓ Added {label}.")

    save_rows(csv_path, rows)
    placed = sum(1 for r in rows if has_coords(r))
    print(f"\nDone. {placed}/{len(rows)} rows have coords. Saved to {csv_path}")
    print("Run `python assets/render_map.py` to regenerate "
          "docs/icons/map_annotated.png")


if __name__ == "__main__":
    main()
