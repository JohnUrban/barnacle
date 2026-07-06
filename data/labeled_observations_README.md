# Labeled Observations — model calibration log

Append-only log of empirical water-depth observations at named landmarks
near 342 Bay Ave. Each row is "what John (or another observer) actually saw
at a given time at a given landmark." Used to validate, calibrate, or
refine the flood model (current spec: `model/v0.9.md`).

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
  worth revisiting. The local-enhancement offset at that specific
  landmark may differ from the +0.40 calibrated at the curb.
- **10+ observations across landmarks:** good basis for refining the
  per-landmark offsets in `predict_landmark_depths`. Could also fit
  a per-landmark error model rather than treating +0.40 as universal.

When making a model change driven by observations:
1. Don't delete or rewrite past rows — append new ones
2. Note the model-version change in `model/v0.5.md` (or its successor)
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
