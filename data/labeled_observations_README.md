# Labeled Observations — model calibration log

Append-only log of empirical water-depth observations at named landmarks
near 342 Bay Ave. Each row is "what John (or another observer) actually saw
at a given time at a given landmark." Used to validate, calibrate, or
refine the flood model (current spec: `model/v0.10.1.md`).

## Why this exists (updated 2026-07-06; original rationale below is history)

This log is the calibration backbone of the model. It's what killed
the v0.6 `+0.40` enhancement (three tape-measured events all implied
~−0.13; a fourth storm event implied 0), what pinned the grate
elevations by cross-fit, what re-anchored the porch ladder, and what
calibrated the pluvial model. The workflow: measure depth at a
landmark with a known elevation → implied water level → compare
across landmarks (water is level in tide floods) and against the
Sandy Hook gauge.

Original v0.5-era rationale (preserved): the `+0.40 ft` enhancement
was calibrated from four memory-based flood events; whether it
applied at sub-curb sentinels was uncertain. (Resolved: it didn't
apply anywhere — it was over-fit to memory-based depths. Enhancement
is 0.00 as of v0.8.)

What the log enables:

1. Cross-fit elevation refinement for unsurveyed landmarks
2. Catching systematic over-/under-prediction at any landmark
3. Model recalibration without waiting for a survey crew

## What to record

When you see water (or noticeably no water when you expected some) at
one of the named landmarks, append a row with as many fields as you
have. Even partial rows are useful.

Don't make this a chore — sparse, honest observations beat dense
fabricated ones. A few dozen observations over months would be plenty.

## Columns

| Column | Meaning | Example |
|---|---|---|
| `observation_time_local` | ISO 8601 local time when you observed (lst_ldt, treat as America/New_York) | `2026-05-18T21:58` |
| `landmark_key` | Machine key from `forecast/flood_forecast_daily.py` LANDMARKS list | `lowest_road_corner` |
| `landmark_label` | Human-readable label for the same landmark | `Lowest road corner across Bay` |
| `observed_depth_in` | Eye-estimated depth in inches; blank if not estimated | `1.5` or `0` (= no water) |
| `observed_qualitative` | Short word description: `no water` / `wet pavement` / `puddle` / `~half inch` / `ankle deep` / etc. | `puddle` |
| `sh_obs_mllw_actual` | Sandy Hook observed water level (MLLW, ft) at the observation hour — fill in from NOAA `water_level` product. Leave blank if not pulled yet. | `6.19` |
| `model_predicted_depth_in` | What the v0.5 model predicts at this landmark given `sh_obs_mllw_actual` (not the forecast). Lets us separate forecast error from model error. | `1.6` |
| `weather_in_window` | Rain rate, wind direction/strength, anything notable in ±2h | `calm, no rain` |
| `observer` | Who recorded it. Default `john` | `john` |
| `notes` | Free text — context, doubts, photo references, anything | `Saw from upstairs window; light coming from streetlight` |

`landmark_key` should match one of the keys defined in
`forecast/flood_forecast_daily.py` LANDMARKS:
`lowest_road_corner`, `gutter_walkway`, `curb`, `road_middle`,
`intersection_highpoint`, `lawn_step`, `porch_step_base`, etc. — see LANDMARKS in `forecast/flood_forecast_daily.py` for the current 18.

## How `sh_obs_mllw_actual` and `model_predicted_depth_in` get filled in

These two columns come from NOAA, not from the observer's eyes. After
recording the observation, pull the Sandy Hook hourly observed water
level for that hour:

```
https://api.tidesandcurrents.noaa.gov/api/prod/datagetter
  ?station=8531680&product=water_level&datum=MLLW
  &time_zone=lst_ldt&units=english
  &begin_date=YYYYMMDD%20HH:MM&end_date=YYYYMMDD%20HH:MM
  &format=json
```

Then compute the model's prediction at this landmark using the actual
gauge reading:

```python
water_navd88 = sh_obs_mllw_actual + 0.00 - 2.82   # enhancement 0.00 since v0.8
predicted = max(0, (water_navd88 - landmark_navd88)) * 12  # inches
```

Recording both columns lets us decompose any miss into "forecast was
wrong" (the gauge ended up different from the forecast) vs "model is
wrong at this landmark" (the gauge was right but the depth prediction
was off).

## When to act on the data

- **1 observation, 1 landmark:** log it, change nothing. Single data
  points don't justify model changes — too many sources of noise
  (lighting, eyeball estimate error, NOAA gauge minor variation).
- **3+ observations at one landmark, all biased the same direction:**
  worth revisiting. Check the landmark elevation and model structure;
  do not resurrect the retired +0.40 ft enhancement without new evidence.
- **10+ observations across landmarks:** good basis for testing the
  shared-water-level assumption and refining uncertain landmark elevations.
  Tidal water should remain level across connected landmarks unless field
  evidence establishes a real hydraulic separation.

When making a model change driven by observations:
1. Don't delete or rewrite past rows — append new ones
2. Note the model-version change in the current `model/v0.X.md` spec
3. Reference the specific row(s) that drove the change in the commit
   message

## Relation to `data/labeled_events.csv`

That file tracks **rain events** (storm-time windows with rain rate,
duration, and flood label). This file tracks **landmark observations**
(specific water-depth readings at specific landmarks at specific
times). They're complementary:

- `labeled_events.csv` answers "was there a flood event in this storm,
  yes or no?"
- `labeled_observations.csv` answers "exactly how high was the water at
  this specific spot at this specific moment?"

The Oct 30 / Apr 17 / Apr 18 / Dec 19 events in `labeled_events.csv`
could be re-decomposed into multiple landmark observations and added
here — useful if the precision becomes load-bearing for some future
refinement, not blocking otherwise.

## Non-model landmark keys (documented 2026-09-03; audit-sweep loop)

`landmark_key` values in this ledger are NOT limited to the 18
registered model landmarks (`ff.LANDMARKS`). Four keys live only
here, with the elevation context this section carries:

- **`driveway_central`** — Central Ave driveway apron (mid-width),
  the mud-tracer/extent reference. **Cross-fit elevation: threshold
  13.8–13.9″ above the SW grate ≈ 4.67 ft NAVD88** [INFERRED,
  bracket]: event #6 (peak +13.8″) left the driveway mud-NEGATIVE;
  event #8 (peak ~+13.9″) photographed water entering it (and the
  2026-08-27 residue + witness accounts concur). Corroboration: the
  bracket lands within 0.01 ft of the independently surveyed
  `porch_step_base` (4.68 NAVD88, walkway grade) — driveway apron
  and walkway sit at the same grade, as they visibly do on site.
  Registration in `ff.LANDMARKS` is DEFERRED to the next model
  version bump (a landmark addition is a versioned model change,
  AGENTS rule 5); until then rows keep the key and this section is
  the elevation record.
- **`fire_hydrant_central`** — qualitative extent reference near the
  Central Ave hydrant; no surveyed elevation; used for residue and
  photo-extent narratives, never for depth arithmetic.
- **`pocket_SE_retention`** — the SE retention pocket
  (`assets/map_points.csv`), outside the 18-landmark corner set.
- **`porch_step`** — LEGACY v0.5-era key (5.08 NAVD88) retracted in
  v0.9 ("corresponded to no physical step"; replaced by
  `porch_step_base` 4.68 / `porch_step1_top` 5.41). The
  2025-10-30T14:54 row retains it for provenance — see its erratum
  row; the observation itself (water at the porch first-step area)
  stands.

## Erratum convention (codified 2026-09-02; audit a2 residual)

Rows are NEVER rewritten. A correction is a new appended row:

- `landmark_key` = `none`, `landmark_label` = `ERRATUM`
- `observed_qualitative` begins `correction record (<source>): row
  with timestamp <YYYY-MM-DDTHH:MM> ...` and states exactly what was
  wrong and what is right, citing primary evidence
- the referenced timestamp must match an EARLIER row in this file
  (enforced by tests/test_csv_ledgers.py)
- consumers treat the latest erratum for a row as authoritative;
  the original row stands as-written for provenance

Cite the corrected row's CURRENT timestamp (the one now in the
file), naming the erroneous value in prose if relevant. Enforced for
errata dated 2026-09-02 onward; the two 2026-08-03 originals (which
cite the erroneous 22:26 value, since corrected to 10:26 by the
audit-a2 M1 repair) predate the convention and stand grandfathered —
they are the precedent this convention formalizes.
