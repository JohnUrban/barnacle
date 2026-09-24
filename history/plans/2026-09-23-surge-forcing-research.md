# Does wind and pressure change how fast surge decays? — research plan

Written 2026-09-23 ~23:40 EDT, BEFORE any wind/pressure result was seen.
Owner request (John, 23:15 and 23:30 EDT): let conditions such as wind and
weather influence the decay rate; a persisting storm should decay slowly
(the decay then reflects confidence, not physics). Baseline to beat: the
v0.10.6 plan's simple model, surge(t+k) = m + (s_t - m) exp(-k/36 h),
m = trailing 365-day mean surge (`history/plans/2026-09-23-surge-decay-plan.md`).

## Data
Sandy Hook 8531680, hourly, 2006-01-01 .. 2026-05-17:
- surge = observed - predicted (`history/data/sandy_hook_hourly_history.parquet`);
- wind speed (kn), direction FROM (deg true), gust; air pressure (mb)
  (`history/scripts/pull_sandy_hook_met.py` -> `sandy_hook_met_hourly.parquet`).

## Two information sets (never mixed up)
- **A. Available live now:** wind and pressure observed at or before t.
  A result here can ship without any forecast input.
- **B. Perfect prognosis:** OBSERVED wind/pressure over (t, t+k]. This is
  an upper bound on what a wind FORECAST could add; a live system would use
  NWS grid forecast wind, which has its own error, so live gains are smaller.
  A B result alone justifies only a further test with archived forecasts.

## Models (each predicts surge at t+k from information at t)
- M0 constant: s_t.
- M1 baseline: m + (s_t - m) exp(-k/36).
- M2 conditional decay (John's framing): tau chosen per forcing class
  (onshore wind terciles; pressure falling / steady / rising), fitted on
  the training decade.
- M3 additive forcing: M1 + b1 * W + b2 * P, W = mean onshore wind-stress
  proxy (speed x |speed| x cos(dir - theta*)), P = pressure change; linear
  least squares on M1's residual, training decade only.
- theta* (the onshore direction) is the direction maximizing the correlation
  of W with surge in the TRAINING decade; physical prior NE-E (45-90 deg).
  Inverse barometer prior: ~0.033 ft of surge per mb of pressure drop.

## Scoring (predeclared)
- Fit on 2006-2015, score on 2016-2026-05 only (held-out decade).
- Leads k = 6, 12, 24, 30, 48 h. MAE in ft.
- Views: all hours (curve, tank), high-tide hours, bay near the plug band
  (2.5-3.8 ft NAVD88 observed), storm starts (s_t >= +1 ft).
- A model "helps" only if it beats M1 on the held-out decade in the storm
  view AND does not lose in the all-hours or plug-band views.
- Missing wind or pressure: the row is scored with M1 (no silent drops that
  flatter a model); the fraction affected is reported.

## Results (2026-09-23 ~23:40 EDT; output `history/reports/2026-09-23-surge-forcing-results.txt`)
Data: wind 82 % / pressure 79 % valid overall; the station's met sensors
were out from Hurricane Sandy (2012-10-29) into 2015; the test decade is
99 % / 97 % complete. theta* = 70 deg FROM (ENE), corr 0.62 with surge;
the physical prior (NE-E) holds.

Held-out 2016-2026 MAE (ft), 24-h lead [all hours / high tides / plug band / storm starts]:
- M0 constant            0.400 / 0.396 / 0.376 / 0.679
- M1 baseline tau 36     0.345 / 0.339 / 0.350 / 0.527
- M2 A past wind         0.345 / 0.339 / 0.350 / 0.527  (no gain)
- M3 A past wind+press.  0.345 / 0.338 / 0.351 / 0.502  (fails: loses in plug band at 12 h)
- M2 B future wind       0.342 / 0.336 / 0.341 / 0.489
- M3 B future wind+press 0.307 / 0.302 / 0.299 / 0.416  (helps in every view, every lead 6-48 h)

Readings:
1. Information set A (what the gauge already saw) adds nothing: a storm
   having persisted does not tell you it will keep persisting. Consistent
   with the earlier past-surge test.
2. Information set B (the wind that actually came) cuts storm error by
   ~20 % at 24-30 h and helps in all three views. This is a PERFECT-FORECAST
   upper bound; a real wind forecast has error.
3. John's intuition is visible in M2 B: the fitted tau is ~48 h when the
   coming onshore (ENE) wind is strong and ~18-24 h when it is weak or
   offshore. But adding the wind as its own term (M3) beats changing the
   decay rate (M2): wind pushes water, it does not only slow the decay.
4. Pressure enters with the inverse-barometer sign (falling pressure ->
   higher surge) at ~0.008-0.013 ft/mb, smaller than the 0.033 prior
   because wind absorbs most of the shared storm signal.

Criterion outcome (predeclared): A fails; B passes (as an upper bound).
Next test before any production use: replace observed future wind with
ARCHIVED FORECAST wind at the matching lead (e.g. Open-Meteo previous-runs
archive of GFS/other models for Sandy Hook, 2021+), refit on part and
score on the rest. Live source would be the NWS grid wind the outlook
already fetches. That result decides whether v0.10.6 (or a later version)
adds a wind term; the simple decay (M1) stands on its own either way.

## Round 2 plan: archived FORECAST wind (written 2026-09-23 ~23:55 EDT, before results)
Question: how much of round 1's perfect-forecast gain survives when the
future wind comes from a real forecast issued before the forecast time?
- Forecasts: Open-Meteo previous-runs archive at the station, models
  gfs_seamless (from 2024-02) and ecmwf_ifs025 (from 2024-03).
  `_previous_day1` = the value from the run ~24 h before that hour;
  `_previous_day2` = ~48 h before. For lead k <= 24 h every hour in
  (t, t+k] uses previous_day1; for 24 < k <= 48 h, previous_day2. So every
  forecast value used was issued at or before t. Live runs would have
  FRESHER forecasts, so this is conservative (a lower bound on the gain).
- Surge 2023-01 .. 2026-09-22 rebuilt from CO-OPS 6-min water_level on the
  hour minus hourly predictions (the verified hourly product lags).
- Split: fit 2024-02-01 .. 2025-04-30; score 2025-05-01 .. 2026-09-20.
- Models on the scored period, leads 6/12/24/30/48 h, same four views:
  M1 (tau 36 toward trailing-365-d mean); M3-obs (observed future wind +
  pressure, refit on the fit period: this period's upper bound);
  M3-fcst-refit (forecast features, coefficients fitted on the fit period);
  M3-fcst-transfer (round-1 coefficients fitted on 2006-2015 OBSERVED wind,
  applied unchanged to forecast features: no refit on the short period).
  theta fixed at round 1's 70 deg. Pressure change = forecast p(t+k) minus
  observed p(t); pressure anomaly = observed, trailing 30 d.
- Success (predeclared): a forecast-wind model is worth building if it beats
  M1 in storm starts at 24-30 h and does not lose in all-hours or plug band,
  for at least one model source. Storm-start counts are reported; with
  ~16 months scored, differences under ~0.02 ft are treated as noise.

## Round 2 results (2026-09-23 ~23:50 EDT; `history/reports/2026-09-23-surge-forecast-wind-results.txt`)
Scored 2025-05-01 .. 2026-09-21 (1,591 storm-start hours, autocorrelated:
far fewer independent storms). MAE ft [all hours / plug band / storm starts]:

| Lead | M1 decay | M3 forecast wind, refit (GFS) | same (ECMWF) | M3 observed wind (upper bound) |
|---|---|---|---|---|
| 12 h | 0.235 / 0.226 / 0.362 | 0.206 / 0.191 / 0.281 | 0.204 / 0.191 / 0.281 | 0.200 / 0.181 / 0.266 |
| 24 h | 0.289 / 0.274 / 0.477 | 0.237 / 0.228 / 0.355 | 0.235 / 0.229 / 0.355 | 0.228 / 0.210 / 0.327 |
| 30 h | 0.315 / 0.305 / 0.494 | 0.258 / 0.233 / 0.374 | 0.263 / 0.235 / 0.387 | 0.252 / 0.229 / 0.343 |
| 48 h | 0.329 / 0.315 / 0.457 | 0.277 / 0.274 / 0.393 | 0.281 / 0.285 / 0.394 | 0.268 / 0.256 / 0.341 |

Readings:
1. Real forecasts keep most of the gain: at 24 h, forecast wind recovers
   ~85 % of the perfect-knowledge improvement in all hours and storm starts
   (storm error 0.477 -> 0.355 ft, -26 %). GFS and ECMWF agree.
2. These forecasts were 24-48 h OLD at use (previous_day1/2); live runs
   would use fresher ones, so the live gain should be at least this large.
3. Coefficients must be fitted to the forecast source: the round-1
   coefficients (fitted on the station anemometer) transferred poorly to
   GFS at 12-24 h (worse than M1) though acceptably to ECMWF. A live wind
   term needs coefficients fitted on the SAME forecast product it uses.
4. Predeclared criterion: PASS for both sources (beats M1 in storm starts at
   24-30 h; better in all hours and plug band at every lead 6-48 h).

Consequence: a forecast-wind term is worth building, AFTER v0.10.6's simple
decay (it adds an input source and fitted coefficients: its own version and
review). Open design question for John: which live forecast. The NWS grid
wind Barnacle already fetches has no easy archive to fit on; GFS (a NOAA
model) is available live and archived through Open-Meteo, or from NOMADS
directly (heavier). Fit period is short (15 months); refit as data accrue.
