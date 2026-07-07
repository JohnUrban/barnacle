# 2026-06-14 — PM tide spot-check, 5 grates × multiple measurements

Third dense-measurement event in the v0.7/v0.8 calibration series, and
**the first at high SH (≥ 7.0)**. 19 tape readings across all 5 grates
spanning ~45 minutes of the rising-and-peaking tide. Cross-grate
water-level consistency is the tightest we've ever logged. The
implied enhancement at SH 7.13 is **the same value as at SH 6.17 and
SH 6.58** — which directly contradicts the v0.7 piecewise heuristic
and forces a material revision to the v0.7 enhancement spec.

---

## TL;DR

- **NOAA Sandy Hook observed peak: 7.161 ft MLLW at 20:12 ET** (vs
  predicted astronomical 6.386 at 19:58; surge +0.78, time delay
  +14 min).
- **Final logged barnacle forecast (T−4.40 h)**: SH 7.351, regime
  "severe." Over by 0.19 ft — within typical surge-persistence noise.
- **5 grates measured at 4 separate moments** across the
  19:41–20:25 ET window. 4-corner water-level cross-fit consistency:
  0.2–0.6″ spread at every timestamp.
- **Mean implied water level at 342 Bay: 4.20 ft NAVD88 at SH 7.13** →
  **implied enhancement = −0.13 ft.**
- **Three events now at SH 6.17, 6.58, and 7.13 all give the SAME
  enhancement (~−0.13 ft).** This contradicts the v0.7 piecewise
  heuristic (which predicts +0.40 at SH ≥ 7.0) and the original 4-event
  +0.40 calibration. The +0.40 hypothesis is no longer tenable as
  written. See "Major finding" section below.
- **`grate_bay_ave_upstream` elevation refined**: low-point reference
  at the user's measurement spot is **3.64 NAVD88** (was 3.76
  placeholder; range 3.64–3.78 reflects 1.7″ of grate-top unevenness).

## Measurements

All measurements are water line **above** the top of the grate, in
inches, taken from photos with a tape measure laid into the grate slot
or against the grate top. (See
[`../0-measuring-tape/README.md`](../0-measuring-tape/README.md) for
tape-reading conventions.) Photo timestamps in each grate subfolder
correspond ±1 min to the measurement time.

| Time (ET) | Grate | Depth above grate top | SH (interpolated) |
|---|---|---:|---:|
| 19:41 | upstream | +6.0″ | 7.10 |
| 19:43 | NE | +4.0″ | 7.11 |
| 19:45 | SE | +6.75″ | 7.12 |
| 19:47 | SW | +7.25″ | 7.13 |
| 19:49 | NW | +4.5″ | 7.14 |
| 19:55 | NE | +4.5″ | 7.15 |
| 19:56 | upstream | +6.5″ | 7.15 |
| 19:58 | SE | +7.0″ | 7.14 |
| 20:00 | SW | +7.75″ | 7.14 |
| 20:05 | upstream | +6.75″ | 7.15 |
| 20:07 | NE | +5.0″ | 7.16 |
| 20:08 | SE | +7.75″ | 7.16 |
| 20:10 | SW | +8.125″ | 7.16 |
| 20:12 | NW | +5.15″ | 7.16 (peak) |
| 20:14 | NE | +5.0″ | 7.15 |
| 20:16 | upstream | +7.0″ | 7.15 |
| 20:20 | SE | +7.5″ | 7.13 |
| 20:23 | SW | +8.0″ | 7.11 |
| 20:25 | NE | +4.75″ | 7.10 |

### Non-grate measurements (new candidate landmarks)

| Time | Location | Reading |
|---|---|---|
| 19:51 | `driveway-central` (middle of width) | water 0.5″ above road; sidewalk lip "a little more than 0.5″" above road, just barely dry |
| 19:53 | `fire-hydrant-central` (between NE corner and driveway, user's side) | water 3.5″ above road; just barely above sidewalk, so sidewalk ≈ 3.5″ above road there |
| 20:26 | `fire-hydrant-central` | water 3.75″ above road; water 0.25″ above sidewalk |
| 20:29 | `driveway-central` | water 1″ above road; **breached sidewalk** |

Edge-of-water photo subfolders (`NE-central-ave-edge`, `NW-bay-ave-edge`,
`NW-central-edge-cross-central-neigbors-driveway`, `SW-bay-ave-edge`,
`bay-ave-farther-upstream`) document the spatial extent of flooding at
the times the corresponding tape measurements were taken. Each edge
point's location, combined with the concurrent measured water level,
constrains the ground elevation at that point — a form of free
topographic data. Encoding these as `flood_edge` category points in
`assets/map_points.csv` is a queued todo.

## Cross-grate water-level consistency

Water is level across a connected surface; the four corner grates
should agree on water height at any single moment. We measured them
in tight time clusters during this rising tide:

| Cluster (ET) | 4-corner mean (NAVD88) | Spread |
|---|---:|---:|
| 19:41–19:49 (NE, SE, SW, NW) | **4.149** | 0.05 ft (0.6″) |
| 19:55–20:00 (NE, SE, SW)     | **4.175** | 0.02 ft (0.2″) |
| 20:05–20:14 (NE×2, SE, SW, NW) | **4.221** | 0.05 ft (0.6″) |
| 20:16–20:25 (NE, SE, SW)     | **4.202** | 0.04 ft (0.5″) |

All four clusters agree on water height to within 0.6″ — within tape
precision. This is the cleanest cross-grate validation we have.

## `grate_bay_ave_upstream` elevation refinement

Cross-fit using the 4-corner cluster mean as the true water level at
each timestamp:

| Cluster | Cluster water | Upstream reading | Implied upstream elev |
|---|---:|---:|---:|
| 19:41–19:49 | 4.149 | +6.0″ (4.210) | **3.649** |
| 19:55–20:00 | 4.175 | +6.5″ (4.252) | **3.633** |
| 20:05–20:14 | 4.221 | +6.75″ (4.272) | **3.659** |
| 20:16–20:25 | 4.202 | +7.0″ (4.293) | **3.619** |
| **Mean / spread** | | | **3.640 ± 0.04 ft** |

So at the user's tape spot tonight, upstream grate top = **3.64 NAVD88**.

The 5/31 measurement implied 3.78 NAVD88. The grate top is uneven — the
2026-05-18 notes already called this out as a 3.74–3.78 range at the
high points. **The full grate-top range is now characterized as
3.64 (low) to 3.78 (high) = 1.7″ of unevenness.** Both prior readings
were correct; they just referenced different points on the grate.

**Convention going forward**: measure tape from the lowest visible
point of the grate top (the elevation at which water first overtops,
hydrologically meaningful). Tonight's reading is treated as a
low-point reference.

## Implied enhancement (THE major finding)

The local enhancement is the residual after subtracting the datum
offset and the SH peak from the measured water level:

```
enhancement = water_at_342_NAVD88 − SH_MLLW − (−2.82)
```

Computed from the 4-corner cluster means at each timestamp (upstream
excluded because of grate-elevation uncertainty):

| Cluster | SH (mean) | Enhancement (mean) | n | σ |
|---|---:|---:|:-:|---:|
| 19:41–19:49 | 7.126 | **−0.157** ft | 4 | 0.021 |
| 19:55–20:00 | 7.144 | **−0.149** ft | 3 | 0.010 |
| 20:05–20:14 | 7.158 | **−0.117** ft | 5 | 0.018 |
| 20:16–20:25 | 7.111 | **−0.089** ft | 3 | 0.011 |
| **Event mean** | **7.13** | **−0.13 ft** | 15 | — |

### Cross-event summary

| Event | SH peak | n grates | Implied enhancement |
|---|---:|:-:|---:|
| 2026-05-18 22:12 | 6.58 | 5 | −0.01 to −0.13 |
| 2026-05-31 20:42 | 6.17 | 4 | −0.13 (σ=0.02) |
| **2026-06-14 ~20:00** | **7.13** | **15** | **−0.13** (σ=0.02 cluster-to-cluster) |

**Three events at three different SH magnitudes (6.17, 6.58, 7.13) all
give the same enhancement: ≈ −0.13 ft.**

## Implications for v0.7 / v0.8

The v0.7 piecewise heuristic (HANDOFF 9c.3 as written 2026-05-31)
predicts:

| SH | v0.7 heuristic enhancement |
|---|---:|
| ≤ 6.6 | 0 |
| 7.0 | +0.40 (full) |
| 7.13 | **+0.40** (saturated) |

Measured: **−0.13** ft. The heuristic over-predicts by **0.53 ft** at
SH 7.13 — about 6.4″ on the depth at every landmark. **At SH 7.0 the
v0.7 heuristic was supposed to be the safe-bias high-end estimate;
the data shows it's the *wrong* direction by 6 inches.**

The +0.40 enhancement from the original 4-event calibration (Apr 17,
Apr 18, Oct 30 2025, Dec 19 2025) was probably absorbing something the
v0.6 rain term undersized. All four of those events had rain. v0.6
rain: `rain_add = 8 · tanh(peak_rain_rate)` (inches). Oct 30 had
1.45 in/hr at peak → tanh adds ~7.3″. With +0.40 enhancement, model
predicts ~12″ at curb (matches observation). With the data-true
enhancement of −0.13, model predicts ~7″ at curb — under by 5″ — so
the rain term would need to be ~5″ bigger.

In short: **the +0.40 enhancement and the v0.6 rain term were
co-fit**; dropping the enhancement requires re-fitting the rain term.

### Recommended v0.7 revision (proposed)

Change 9c.3 from the piecewise heuristic to **`enhancement = −0.13 ft`
constant** (the 3-event mean). Rationale:

- Matches all 3 high-quality spot-check events (σ very small across
  events and across SH magnitudes 6.17–7.13)
- The "safety bias" rationale for the piecewise +0.40 is now disproven
  at the only SH where we could check it (7.13)
- Eliminates a 6.4″ over-prediction at high SH

**Required v0.7 caveat**: the v0.6 rain term (`8 · tanh(rate)`) likely
under-predicts rain-flood events without the +0.40 to compensate. Document
this prominently as a **known v0.7 limitation**, with the rain
recalibration explicitly deferred to v0.8 (9d.2). Concrete impact:
events similar to Oct 30 2025 will likely be under-predicted by ~5″ at
the curb until the rain term is re-fit.

This is a meaningful change to the v0.7 spec. **Awaiting user
review/approval before HANDOFF 9c.3 is updated.**

### v0.8 implication

The 6/14 event was supposed to be the high-surge unblocker for v0.8
9d.1 (the fitted enhancement form). But the answer turned out to be:
*the +0.40 hypothesis doesn't recover at high SH*. So v0.8 9d.1 is
*also* changed: instead of "fit f(surge)", the work becomes "verify
−0.13 holds at even higher SH (say, ≥ 7.5)" — a much lighter check.

## Open todos from this event (2026-06-15 session — backlog)

- [x] **STAGED 2026-07-07** — `fire_hydrant_central` (3.85, cross-fit
      6/14+6/15, used 7/6) and `driveway_central` (4.11) added to
      `assets/map_points.csv` with empty x/y; `pick_coords.py`
      prompts for them (with location hints). `cross_central_driveway`
      was never given a measurement — the flood-edge point at the
      neighbors' driveway covers that location instead.
- [x] **STAGED 2026-07-07** — `flood_edge` category (teal) added to
      `pick_coords.py` + `render_map.py`; all five edge-photo
      locations staged in the CSV at ~4.15 NAVD88 (the 6/14 water
      band), awaiting user clicks.
- [ ] Establish a permanent reference point on
      `grate_bay_ave_upstream` for future tape measurements (low-point
      convention agreed 6/14).
- [ ] Cross-fit `lawn_step` and `porch_step` elevations from any
      tonight's photos that show water at those features. (HANDOFF
      section 7 item 4.) Likely possible since SH 7.13 + −0.13
      enhancement = water at 4.20 NAVD88, which is at the lawn-step
      level (4.58 placeholder → may be lower).
- [ ] **Discuss v0.7 spec revision with user**: drop the piecewise
      heuristic, set `enhancement = −0.13 ft` constant, document the
      rain-undercount caveat. Update HANDOFF 9c.3 + 9d.1.
- [ ] Log 6/14 measurements (19 rows) to
      `data/labeled_observations.csv`. Defer until the v0.7-revision
      conversation is settled so we don't churn the file.

## Photos

- `grate-NE-user-corner/` — multiple photos across the event
- `grate-NW-across-central/` — 2+ photos
- `grate-SE-proximal/` — multiple
- `grate-SW-distal/` — multiple
- `grate-bay-ave-upstream/` — multiple
- `gutter-at-walkway/` — gutter status
- `driveway-central/` — 2 measurements at 19:51 and 20:29
- `fire-hydrant-central/` — 2 measurements at 19:53 and 20:26
- `NE-central-ave-edge/`,
  `NW-bay-ave-edge/`,
  `SW-bay-ave-edge/`,
  `NW-central-edge-cross-central-neigbors-driveway/`,
  `bay-ave-farther-upstream/` — documentary flood-extent photos
  (no tape measurements, but locations + concurrent water-level
  measurements imply ground elevation at each edge point)
