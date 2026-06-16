# 2026-06-15 — PM tide storm-condition event (v0.8 calibration anchor)

**The event that drove v0.8.** Worst flooding at 342 Bay so far this
month, exceeded only by Apr 18 and Oct 30 in our records. Caught
everyone by surprise — the Highlands meteorologist who runs
ShorelySafe sent a police officer to take official photos when
flooding reports came in, because his model showed no flooding at
this intersection.

## TL;DR

- **NOAA Sandy Hook observed peak: 7.289 ft MLLW at 21:00 ET**
  (predicted astronomical 6.381 at 20:51; **surge +0.91 ft**, +9 min
  late).
- **v0.7 (live before this event) under-predicted by 1.3″
  structurally at curb** (predicted water 4.34 NAVD88 vs observed
  4.45); **3.5″ at curb operationally** because the SH forecast also
  undershot the actual peak by 0.20 ft (surge persistence didn't
  catch the late wind veer).
- **Peak water at 342 Bay: 4.449 NAVD88** (4-grate cross-fit at 9:08–
  9:14 PM cluster, water lags SH by ~10 min due to bay propagation;
  spread 0.4″ — tightest cross-grate consistency we've logged).
- **Implied enhancement at peak: 0.00 ft** (vs −0.13 for the 3
  prior tape-measured regular-tide events). This is the
  storm-condition signal v0.7 didn't have.
- **Why**: late wind veer at the gauge from offshore (NW afternoon,
  315–330°) to onshore (NNE at peak, 357–8°) ~1 hour before peak.
  Onshore winds pile water into the SE corner of Sandy Hook Bay
  where Highlands sits. NWS surge forecasts under-predicted as a
  result.
- **v0.8 promotion (same-night, this commit)**:
  - Main enhancement constant: 0 (conservative; matches storm
    conditions, errs ~1.5″ over on regular tides — within tape
    precision and aligned with user's "false positives over
    negatives" preference).
  - Wind-direction adjustment reported as a separate "expected
    actual" line: when forecast wind at peak is in the offshore
    sector (S/SSW/SW/WSW/SSE), apply −0.13 ft as the v0.7 estimate.
  - New landmark: `sidewalk_under_walkway_lawn_step` at 4.33 NAVD88
    (cross-fit from 3 measurements tonight).
- **User commentary**: *"While I was taking measurements I talked
  to a police officer who was sent to take photos by the Highlands
  meteorologist guy who runs the ShorelySafe dashboard for highlands
  flooding. His model has no flooding over in my intersection, so
  when he got reports of flooding he sent out people to get official
  pics — probably wants to update his own model."*

## Event context

- Wind direction at peak: 357–8° (N/NNE). All afternoon was NW
  (315–330°, offshore). Late veer at ~19:30 ET.
- Rain: minimal at peak hour. Some afternoon rain but not coincident
  with tide peak.
- Atmospheric: low pressure system; user notes "tonight's flooding
  was the worst this month so far."
- Antecedent: the previous evening (6/14) had a high-SH event of
  similar surge magnitude (+0.78) but offshore winds at peak.

## Measurements

Tape readings recorded as text only (per user preference established
in last session; photos kept for spatial-extent context, not for
each tape reading). All measurements are water line ABOVE the top of
the grate, in inches.

### Grate measurements (17 readings, 9:39–9:26 PM ET span)

| Time | Grate | Depth | SH (interpolated) | Implied water at 342 |
|---|---|---:|---:|---:|
| 8:39 PM | NE | +5.5″ | 7.20 | 4.258 |
| 8:41 PM | SE | +8.5″ | 7.21 | 4.308 |
| 8:42 PM | SW | +9.0″ | 7.22 | 4.270 |
| 8:45 PM | NW | +6.25″ | 7.25 | 4.321 |
| 8:47 PM | NE | +6.375″ | 7.27 | 4.331 |
| 8:49 PM | SE | +9.0″ | 7.28 | 4.350 |
| 8:53 PM | SW | +9.75″ | 7.28 | 4.332 |
| 8:57 PM | SW | +10.0″ | 7.28 | 4.353 |
| 8:59 PM | SE | +9.6″ | 7.29 | 4.400 |
| **9:07 PM** | **upstream** | **+10.0″** | **7.27** | **4.473** |
| **9:08 PM** | **SE** | **+10.25″** | **7.27** | **4.454** |
| **9:10 PM** | **SW** | **+10.875″** | **7.27** | **4.426** |
| **9:12 PM** | **SE** | **+10.3″** | **7.27** | **4.458** |
| **9:14 PM** | **NE** | **+7.875″** | **7.26** | **4.456** |
| 9:24 PM | NE | +7.5″ | 7.19 | 4.425 |
| 9:25 PM | SE | +10.0″ | 7.18 | 4.433 |
| 9:26 PM | SW | +10.375″ | 7.17 | 4.385 |

### Sidewalk-under-lawn-step measurements (new landmark cross-fit)

| Time | Depth on sidewalk | Implied sidewalk elev (cross-fit) |
|---|---:|---:|
| 9:05 PM | 1.25″ | 4.336 |
| 9:15 PM | 1.5″ | 4.335 |
| 9:21 PM | 1.5″ | 4.305 |
| **Mean** | | **≈ 4.33 NAVD88** |

These three independent estimates pinned the sidewalk elevation at
where it meets the lawn-step face of the user's walkway. **New
landmark added to v0.8: `sidewalk_under_walkway_lawn_step` at 4.33
NAVD88.** Note: lawn_step itself (top of the step, at 4.58 NAVD88)
was NOT reached tonight — water peaked at 4.45 NAVD88, **1.5″ below
the lawn-step top.**

### Non-grate observations on Central Ave

| Time | Location | Reading | Inferred ground elev (using cross-fit water) |
|---|---|---|---:|
| 9:01 PM | driveway-central (middle) | water 4″ above road | road ~4.11 NAVD88 (consistent with 6/14 estimate) |
| 9:03 PM | fire-hydrant-central | water 6.75″ above road | road ~3.85 NAVD88 (consistent with 6/14 estimate) |

These two locations were previously inferred from 6/14 data; tonight
provides a second anchor at consistent values. Pending addition to
`assets/map_points.csv` as `driveway_central` and
`fire_hydrant_central`.

### Edge-of-water photo locations (no tape, spatial context)

13 sub-folders contain photos at named locations documenting the
flood extent. Photo organization is less formalized than 6/14:

- `NE-central-edge`, `NW-central-edge` — water's edge along Central Ave
  (each has a brief `README.txt` describing what's visible)
- `NE-grate-from-lawn-step`, `SE-corner-from-SW-corner` — angle shots
- `across-bay-ave-from-lawn-step`,
  `central-between-SE-and-SW-grates`,
  `eastern-bay-ave-from-intersection`,
  `eastern-bay-ave-from-lawn-step`,
  `western-bay-ave-from-intersection`,
  `western-bay-ave-from-lawn-step` — extent shots
- `driveway-central`, `grate-bay-ave-upstream`, `intersection` —
  named-location photos

## Peak water reconstruction

The 9:08–9:14 PM cluster (water at 342 peaks ~10 min after the SH
gauge peak due to bay propagation):

| Grate | Time | Depth | Water at 342 |
|---|---|---:|---:|
| SE | 9:08 PM | +10.25″ | 4.454 |
| SW | 9:10 PM | +10.88″ | 4.426 |
| SE | 9:12 PM | +10.30″ | 4.458 |
| NE | 9:14 PM | +7.88″ | 4.456 |
| **Mean** | | | **4.449 NAVD88** |
| **Spread** | | | **0.032 ft (0.4″)** |

**Peak curb depth: 3.5″.** Peak gutter_walkway depth (3.78): 8.0″.
Peak corner_NE depth (3.91): 6.5″. Lawn step (4.58) NOT reached
(stayed dry by 1.5″). Porch step (5.08) NOT reached (8″ below).

## v0.7 (the model that was live going in) vs observed

| Metric | v0.7 prediction | Observed | Δ |
|---|---:|---:|---:|
| Water at 342 at peak | 4.339 NAVD88 | 4.449 | +1.3″ structural under |
| Final logged SH forecast | 7.087 MLLW | 7.289 actual | +2.4″ at curb from SH miss |
| Reported regime (operational) | "street" | "light" actual | one step too tame |

The 1.3″ structural gap = exactly the v0.7 enhancement constant
−0.13 ft. **Setting enhancement to 0 would have given the peak
prediction within 0.2″ at this event.**

## Implied enhancement varied within the event

| Phase | Time | Implied enhancement |
|---|---|---:|
| Rising tide | 8:39–8:53 PM | **−0.12 to −0.13** (matches our 3-event mean) |
| Near peak | 9:07–9:14 PM | **0.00 to +0.02** ("storm bump") |
| Post-peak | 9:24–9:26 PM | **+0.04 to +0.08** (post-peak hysteresis — water at 342 drains slower than SH at gauge) |

The "storm bump" specifically appeared at peak when the wind was
fully onshore. On the rising tide while wind was still transitioning
through NNW, enhancement matched the offshore-wind baseline.

## v0.8 design decision (user + Claude, 2026-06-15)

User articulated the wind asymmetry: *"N/NW means more flooding,
but the opposite direction also might mean less flooding."* Decision:

- **Main model uses enhancement = 0** (the conservative / over-predict
  value).
- **Wind adjustment reported as a separate "expected actual" line**:
  when NWS forecast wind at peak ± 1 hour is in the offshore sector
  (S/SSW/SW/WSW/SSE), apply −0.13 ft adjustment alongside the main.
- **Bumped to v0.8** per the versioning rule (constants change ⇒ new
  version).

User preference noted: *"I think we can already implement those wind
terms, but report the adjusted expectation separately. It can note
that given the current wind, the actual observed level could be Z
instead of X."* — matches what landed in
`compute_wind_adjustment()` + `_render_wind_adjustment_html()`.

## Wind-direction calibration data (the v0.8 anchor)

| Event | Wind direction at peak | Sector | Enhancement |
|---|---|---|---:|
| 6/14 20:12 ET | S/SSW (172–191°), 12–16 kt | offshore | **−0.13** |
| 6/15 21:00 ET | N/NNE (357–8°), 8–10 kt | onshore | **0.00** |

Same property, similar SH magnitude (7.16 vs 7.29 — within 0.13 ft),
fundamentally different wind sector at peak → fundamentally different
enhancement. The v0.8 wind rule was calibrated against this
back-to-back pair.

## Cross-references

- Model spec: `model/v0.8.md`
- Wind adjustment function:
  `forecast/flood_forecast_daily.py:compute_wind_adjustment()`
- Per-photo notes (less formalized than 6/14): subfolder READMEs
- Previous regular-tide spot-check (offshore wind, enh −0.13):
  `assets/observations/2026-06-14/README.md`
- Previous storm-condition photo anchor:
  `assets/observations/2025-10-30/README.md`
