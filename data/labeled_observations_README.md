# Labeled Observations — model calibration log

Append-only log of empirical water-depth observations at named landmarks
near 342 Bay Ave. Each row is "what John (or another observer) actually saw
at a given time at a given landmark." Used to validate, calibrate, or
refine the v0.5 flood model.

## Why this exists

The v0.5 model's `+0.40 ft` local enhancement was calibrated from four
flood events at the curb and above (Apr 17/18 2026, Dec 19 2025,
Oct 30 2025). Whether the same enhancement applies at:

- The lowest road corner across Bay (3.64 NAVD88 / SH 6.06) — across the
  Bay, not on the user's property
- The gutter at walkway (3.78 NAVD88 / SH 6.20) — sub-curb sentinel
- The front porch first step (5.08 NAVD88 / SH 7.50) — above lawn

...is genuinely uncertain. Each sentinel has its own micro-hydraulic
context. This log accumulates empirical observations so we can:

1. Verify the +0.40 enhancement applies at sub-curb / sentinel
   landmarks (currently assumed but not validated)
2. Catch systematic over- or under-prediction at any specific landmark
3. Provide calibration data for future model refinements without
   needing another major flood event

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
`intersection`, `lawn_step`, `porch_step`.

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
water_navd88 = sh_obs_mllw_actual + 0.40 - 2.82
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
