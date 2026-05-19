# assets/

Editable source files for committed binary artifacts. Right now: the
map annotation workflow.

## Map annotation workflow

The goal: produce `docs/icons/map_annotated.png` (the canonical
labeled map of landmarks + topography around 342 Bay Ave) from a
data-driven source rather than by hand-editing each time.

Three files, all in this directory:

| File | Role |
|---|---|
| `map_points.csv` | data source: label, value, category, x, y per point |
| `pick_coords.py` | interactive picker: opens `docs/icons/map_raw.png`, you click each point, x/y written to CSV |
| `render_map.py`  | renderer: reads CSV + `map_raw.png`, writes `docs/icons/map_annotated.png` |

### CSV schema

```
label,value,category,x,y
lowest_sentinel_grate,3.60,landmark,123.4,456.7
extra_corner_1,4.20,extra,234.5,567.8
```

- `label`: machine-readable identifier (snake_case)
- `value`: human-readable label that appears on the map (typically the
  NAVD88 elevation as a string, e.g. `"3.60"`)
- `category`: `landmark` (one of the 9 canonical model landmarks —
  rendered in blue) or `extra` (additional topography / spot height —
  rendered in red)
- `x`, `y`: pixel coordinates in `map_raw.png` (top-left origin,
  matplotlib convention). Decimal pixels fine.

The CSV is committed and pre-seeded with the 9 canonical landmarks
(values matching `model/v0.6.md`). On first use, their x/y are empty —
the picker will guide you through placing each.

### Typical workflow

**First-time setup (one-time, ~5 min):**

```sh
# 1. Open the picker. It walks you through each landmark in order,
#    showing the map and prompting you to position your cursor and
#    press SPACE for each. U undoes the last placement; ESC quits.
python assets/pick_coords.py

# 2. After the pre-seeded landmarks are placed, the same SPACE-to-
#    place workflow lets you add extra topography spot heights —
#    after each placement, terminal prompts for label + value.

# 3. Generate the final PNG.
python assets/render_map.py
# -> writes docs/icons/map_annotated.png

# 4. Commit
git add assets/map_points.csv docs/icons/map_annotated.png
git commit -m "map: place landmarks + add N extras"
```

**Picker keys:**
- `SPACE` — place a point at the current cursor position
- `U` — undo the last placement
- `ESC` — quit (or just close the window)

**Why keyboard placement instead of click:** macOS trackpad tap-to-click
plus matplotlib's click handler caused spurious placements when moving
the cursor or cmd+tabbing away to look up values in a PDF. SPACE-to-
place eliminates that — only deliberate keypresses register.

**Adding or moving points later:**

Two paths, pick whichever's faster:

a. **Manually edit `map_points.csv`** — open in any text editor,
   tweak x/y, change a value or label, add a row. Then re-run
   `render_map.py` + commit.

b. **Re-pick interactively** — `python assets/pick_coords.py` will
   skip rows that already have x/y. To replace existing coords, use
   `--redo` to clear them all first.

### Why this exists

Earlier in the project (before 2026-05-19) the annotated map was
hand-edited in macOS Preview as a PNG. Pros: visual, immediate. Cons:
inconsistent styling, hard to update, easy to misplace points, no way
to add a new point without redoing the whole image.

The CSV-driven workflow gives:

- Consistent rendering (white-haloed bold labels, distinct colors for
  landmarks vs extras, identical dot size and positioning logic)
- Easy edits — change a value or move a point in the CSV → rerender
- Diff-able history — every coord change shows up in `git diff`
- Reusable across future iterations (heat-map overlays, depth
  visualizations, etc.) — all the data is in the CSV

### Dependencies

- Python 3 (any version on the user's Mac)
- `matplotlib` (for both scripts — also used by the historical-stats
  analysis scripts; if not installed, `pip install matplotlib`)

The scripts only run locally on your Mac — they don't run in the
GitHub Actions workflow (which doesn't need to regenerate the map).
The committed PNG is what production uses.

### Related future work

See `HANDOFF.md` section 9 item 27c — the same CSV is the natural
input for the future depth heat-map overlay (predicted water depth
tinted onto the map). More topography points in the CSV → smoother
heat-map surface.
