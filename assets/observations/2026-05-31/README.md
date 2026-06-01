# 2026-05-31 — PM tide spot-check, 4 grates measured

Second event in the v0.7-calibration series. Cleanly measured at all
four grates within a 5-minute post-peak window. The data is a tight
internal check (four independent water-level estimates from four
different grate-top elevations) AND a strong external check on the
v0.6 model.

---

## TL;DR

- **NOAA Sandy Hook observed peak: 6.17 ft MLLW at 20:42 ET** (vs
  predicted astronomical 5.422 at 20:44; surge +0.75, time delay
  −2 min — barnacle's best-timed peak forecast yet).
- **Final logged barnacle forecast (T−4.27 h, made 2026-05-31 20:27
  UTC)**: SH peak 6.046 → "street" regime → "brief water at the storm
  grate, nothing at the curb." Under-predicted SH by 0.12 ft. Final
  forecast accuracy was the best on record for any tide we've logged.
- **Observed: water never breached any grate.** All four grates were
  4–7.25 inches below the water line. The "street" prediction was a
  false positive.
- **Implied water at 342 Bay: ~3.20 ft NAVD88** (four measurements
  agree within ~0.6″ — beautifully consistent).
- **Implied local enhancement at SH 6.15 MLLW: −0.13 ft.** Same sign
  and magnitude as the 2026-05-18 finding. *Two consecutive events
  now contradict the +0.40 constant.*
- User stance on the "street" false positive: tolerable. "Our errors
  should err in the over-sensitive direction. False positives are
  better than false negatives here." Agreed — but v0.7's
  surge-dependent enhancement work now has two independent data
  points showing the +0.40 is wrong at SH ~6.

## Measurements

All measurements are water line *below* the top of the grate, in
inches, taken from photos with a tape measure laid into the grate slot
or against the grate top.

| Grate | Folder | Depth below grate top | Photo timestamps (ET) |
|---|---|---|---|
| `grate_bay_ave_upstream` | `grate-bay-ave-upstream/` | **−7 to −8″** (best single: −7.0; max −7.5) | 20:50:17, 20:51:41, 20:51:59 |
| `grate_NE` (user's corner) | `grate-NE-user-corner/` | **−7.25″** | 20:52:40, 20:53:00 |
| `grate_SE` (across Bay, proximal) | `grate-SE-proximal/` | **−5″** | 20:53:42, 20:54:47 |
| `grate_SW` (across Bay, distal) | `grate-SW-distal/` | **−4″** | 20:55:11, 20:55:31 |

Photos taken in this exact order; user confirmed. SH was essentially
flat at 6.15 ft MLLW across the 5-minute window (peak 6.17 was 8–13
min before the earliest photo; bay was at a post-peak plateau, dropping
0.02 ft over the photo window — negligible for inferring level).

### Tape-reading convention (for future viewers of these photos)

- The line for an inch marker comes **after** the printed number, not
  at the number's position. If you see "7", the 7-inch line is just
  past the digit, on the side away from the start of the tape.
- 2D photo geometry + camera angle distort tape readings; precise
  reading from photo alone is hard without being there.
- TODO (future session): take a high-resolution reference photo of
  ~12″ of the tape so the precise number/line mapping is on file.

## Per-grate water-level estimate (cross-check)

Water surface at 342 Bay = grate_top_elevation − (depth_below / 12).
This should give the same answer at every grate (water is level).

| Grate | Elev (NAVD88) | Depth below | Implied water_NAVD88 |
|---|---|---|---|
| upstream | ~3.76 | −7.0 (range −7 to −7.5) | **3.18 ft** |
| NE | 3.80 | −7.25 | **3.20** |
| SE | 3.60 | −5 | **3.18** |
| SW | ~3.55–3.58 | −4 | **3.23** |
| **mean** | | | **3.20 ft** |
| **spread** | | | 0.05 ft (~0.6″) |

The 0.6″ spread is within tape-reading precision. SW's value sits a
bit high; if the other three are correct that the water level was
3.18 ft NAVD88, then **grate_SW top is closer to 3.51 ft NAVD88** than
the 3.55–3.58 placeholder we had. One more careful SW elevation check
in a future spot-check would close this out.

## v0.6 model vs observation

At observed SH 6.15 MLLW, the v0.6 model predicts:

| Variant | water_NAVD88 | grate_SE depth | grate_SW depth | Verdict |
|---|---|---|---|---|
| **+0.40 enhancement (as-deployed)** | 3.73 ft | +1.6″ (over) | +2.0″ (over) | **WRONG — predicted "street"** |
| **0 enhancement** | 3.33 ft | −3.2″ | −2.8″ | Correct (dry), but still over by ~2″ |
| **−0.13 enhancement (fitted to today)** | 3.20 ft | −4.8″ | −4.3″ | Matches observation almost exactly |

Implied enhancement values from each grate independently:

| Grate | Implied enh = water_at_342 − SH − datum |
|---|---|
| upstream | −0.15 |
| NE | −0.13 |
| SE | −0.15 |
| SW | −0.10 |
| **mean** | **−0.13 ft** |

The four independent estimates of enhancement agree to within ±0.025 ft.

## Cross-event picture so far

| Event | SH peak | Implied enhancement | Notes |
|---|---|---|---|
| 2026-05-18 22:12 peak | 6.58 MLLW | ~−0.01 to −0.13 across measurements | First spot-check; 22 photos |
| 2026-05-31 20:42 peak | 6.17 MLLW | **−0.13** (mean of 4 measurements) | This event |

Two events, both at moderate SH magnitude (6.17–6.58), both with
enhancement near zero or slightly negative. **The v0.6 constant
+0.40 ft is wrong at this magnitude class.** The HANDOFF hypothesis
that +0.40 may be a saturated value that only develops at higher SH
or with stronger surge gains more support — but we still don't have an
event in the saturated regime to fit it. Until then, v0.7 should at
minimum drop the constant +0.40 and either zero it out or make it
surge-dependent.

## Photos

- `grate-bay-ave-upstream/` — 3 photos (barnacle_20260531 - 1.jpeg ..
  3.jpeg). Tape reading: ~7–8″. Two pics show the tape but it was
  hard to hold steady. Treat -7.0 as best single estimate; the
  upstream grate's uneven top (~3.74–3.78 NAVD88 from 5/18 work) may
  also contribute to reading variance.
- `grate-NE-user-corner/` — 2 photos (barnacle_20260531 - 4.jpeg,
  5.jpeg). Tape reading: ~7.25″.
- `grate-SE-proximal/` — 2 photos (barnacle_20260531 - 6.jpeg,
  7.jpeg). Tape reading: ~5″.
- `grate-SW-distal/` — 2 photos (barnacle_20260531 - 8.jpeg,
  9.jpeg). Tape reading: ~4″.
