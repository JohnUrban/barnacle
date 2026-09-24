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
