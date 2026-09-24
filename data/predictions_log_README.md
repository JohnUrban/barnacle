# Predictions Log — master historical record of model output over time

Append-only CSV. One row per `(prediction_made_at, target_tide_time)` pair.
Each row captures everything the model said about one upcoming high tide
*at the moment the prediction was generated*. HANDOFF section 9b.3.

## Why this file exists

The original daily forecast wrote only the *final* prediction for each
day to `docs/archive/YYYY-MM-DD.json` and a coarse one-row-per-day
accuracy log to `data/forecast_accuracy.csv`. That suffices for "did
yesterday's daily forecast match observed?" but is too coarse for:

- Plotting how each tide's prediction *evolved* in the 12 hours leading
  up to it (HANDOFF 9b.4(a))
- Asking "did the prediction get better as the tide approached?"
  (HANDOFF 9b.8 lead-time-axis accuracy)
- Reconstructing the heat-map for any past prediction event (HANDOFF
  9b.4(c) — the map scrubber)

This log is the canonical source for all three.

## The one-number principle

From a single row's `water_navd88_predicted` plus the static
`assets/map_points.csv`, every landmark depth, regime, and map visual
can be reconstructed by re-applying the model formula. So the storage
burden is small even at hourly cadence — and the website renders all
heat-maps *client-side* from these numbers (HANDOFF 9b.10).

## Update cadence

| Phase | Rows per day | Trigger |
|---|---|---|
| Before hourly rollout (historical) | 2-4 | daily GitHub Actions workflow |
| Current production | ~48-96 | hourly GitHub Actions workflow |

Each workflow run appends one row per upcoming high tide in
`forecast["all_tides"]`. With 2 tides per day visible at any time, that's
~2 rows per run.

## Columns

| Column | Meaning |
|---|---|
| `prediction_made_at` | ISO UTC timestamp when this row was written (`YYYY-MM-DDTHH:MM:SSZ`) |
| `target_tide_time` | High-tide identifier. Rows written from the 2026-09-18 GMT cutover use offset-bearing station-local ISO (`YYYY-MM-DD HH:MM-04:00` or `-05:00`), derived from NOAA GMT transport. Older rows retain naive NOAA `lst_ldt` (`YYYY-MM-DD HH:MM`) and are interpreted with legacy `fold=0`. |
| `hours_until_peak` | Signed hours from `prediction_made_at` to `target_tide_time`. Positive = future tide; negative = predicting a tide that already happened (legitimate in the hour or two after peak when we still have NOAA data). |
| `predicted_mllw_astronomical` | NOAA hilo astronomical-only prediction at the tide time (no surge component) |
| `surge_ft_predicted` | Signed surge in ft. Positive = water above astronomical. |
| `surge_source` | `nws-coastal-flood-product` (active event, parser used) or `surge-persistence` (no active event, applied current observed surge forward) |
| `sh_peak_mllw_predicted` | Predicted Sandy Hook peak in MLLW ft (= astronomical + surge). **Not** cold-lockout-aware. |
| `peak_rain_in_hr_predicted` | Peak rainfall rate (in/hr) in the ±90 min window around the high tide |
| `water_navd88_predicted` | Predicted water level at 342 Bay in NAVD88 ft (= `sh_peak_mllw + local_enhancement + (MLLW→NAVD88 offset)`). **Empty when cold lockout suppresses flooding.** This is the canonical number for map reconstruction. |
| `regime_predicted` | `dry` / `street` / `light` / `moderate` / `severe` / `cold_lockout` |
| `cold_lockout` | `true` / `false` — whether the cold-weather drain-backflow suppression applies |
| `confidence_level` | `high` / `medium` / `low` — forecast-stability label; displayed numeric ranges use the empirical 80th-percentile absolute error for the label when enough rows exist |
| `model_version` | Model spec used for that as-run prediction. Current production stamp is `v0.10.6` (surge decays toward the trailing mean, tau 36 h: `surge_ft_predicted` is the decayed value at each tide, and `surge_source` may be `typical-offset-degraded`; physics otherwise unchanged). `v0.10.5` (since 2026-09-23; inputs and policy only: 48-h alert window, 7-day outlook, scoped input health, observed-surge curve, confidence labels retired; no physics change). `v0.10.4` (2026-09-20) removed `driveway_central` from the landmark ladder. Earlier as-run rows carry `v0.10.4` although the new inputs and policies were live; the promoting commit includes the first `v0.10.5` generation at 2026-09-24T03:24:52Z (September 23 23:24:52 EDT); they are not rewritten. Historical rows intentionally retain their original versions. |

## Append-only convention

- **Never rewrite or sort existing rows.** The order rows appear in the
  file is the order they were written; consumers sort or filter as
  needed.
- **Never delete rows** even if a prediction turns out to be wildly
  off. The whole point is to preserve the model's beliefs at each
  point in time.
- **Adding new columns requires a small schema migration** — append them
  at the end of `PREDICTIONS_LOG_FIELDS` in
  `forecast/flood_forecast_daily.py`, extend the header, and add an empty
  trailing value to historical rows. Values and row order remain untouched.
  The writer and publish gate now reject a stale header or uneven row width
  instead of silently corrupting the ledger.
- **Never remove or rename existing columns** without a deliberate
  migration pass (touch every consumer first).

## How accuracy gets computed against this

The website accuracy section joins this log against
NOAA observed water levels at each `target_tide_time` and computes
three modes of accuracy (peak-magnitude, outcome-depth, binary
classifier). With `hours_until_peak` as a grouping axis, we can also
plot "does accuracy improve in the last 3 / 6 / 12 hours before
peak?" — the key question that hourly cadence (HANDOFF 9b.1) is
designed to answer.

The legacy one-row-per-day `data/forecast_accuracy.csv` is the
degenerate version of this; it stays frozen as a historical artifact
once the new log is in production.

## Related

- `data/labeled_observations.csv` — empirical observations *of* water
  levels (this log is *predictions*; that log is *what happened*)
- `data/forecast_accuracy.csv` — legacy one-row-per-day version
- `docs/archive/YYYY-MM-DD.json` — daily snapshot of the full forecast
  dict (also legacy v1 storage; superseded by this log + the per-tide
  pages)
- `data/day_risk_log.csv` — append-only hourly rain-risk guidance used
  for day-maximum markers; the daily archive remains an as-issued 09Z snapshot
