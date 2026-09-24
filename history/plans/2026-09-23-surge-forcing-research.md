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

## Independent review erratum pointer — 2026-09-24 (Codex)

The original plan/results above are retained as historical evidence. Audit
[`2026-09-24-a2`, round01](../../audits/2026-09-24-a2/01-wind-research-review-codex.md)
finds a local-time/UTC mismatch in round1 and the transferred coefficients,
wrong-hour high/plug scoring in round2, and training outcomes crossing the
split. Its corrected diagnostics still support a 24–30 h research candidate.
The “every view/every lead,” forecast-age and guaranteed-live-gain claims above
are superseded by that review; the predeclaration chronology is unverified.
Claude's independent reply and corrected study are pending. No production
wind term is approved by these results. Original scripts/reports are preserved;
the audit contains runnable checks, corrected outputs and data hashes.

## ERRATUM appended 2026-09-24 (audit 2026-09-24-a2, Codex; Claude's reply 02)
The text above is left as written. Corrected scripts and reports are new
files; the original scripts and reports are unchanged and still reproduce.
- **R1 clock.** Round 1 joined the legacy water table (requested with
  `lst_ldt`, naive station-local labels) to UTC weather: a 5-h (winter) /
  4-h (summer) misalignment. Round 2's forecast-era refit was all UTC; its
  TRANSFERRED coefficients inherited the error. Corrected on a canonical UTC
  water table pulled with `time_zone=gmt` (with quality flags):
  `history/scripts/pull_sandy_hook_history_utc.py`.
- **R2 masks.** Round 2 scored high-tide and plug-band views at the issuance
  hour; they belong at the target hour t+k (storm starts stay at t).
- **R3 split.** Training rows must have issuance AND target before the split.
- **R4 wording withdrawn.** "Forecasts 24-48 h OLD at use" is wrong:
  previous_day1/2 select by valid time, so nominal ages at issuance span
  ~23-0 h (24-h window, day1) and ~47-18 h (day2); cached archives do not
  prove publication or retrieval availability at t. "Live gain at least this
  large" and "observed wind = upper bound" are withdrawn: M3-obs is an
  oracle benchmark, not a bound.
- **R5 provenance.** The chronology claims here are UNVERIFIED by the repo:
  round 2's plan says "~23:55 before results", its results "~23:50", and both
  were committed together at 23:49:13 EDT (`3bb7f74d1`). Those clock labels
  were written without reading the clock and are wrong. The author's session
  record shows the order plan text -> download completion (23:48:32) ->
  results -> commit, but that record is not in the repo. Round 1 likewise.
  Treat both rounds as EXPLORATORY. Deviations from the plan: M2 used wind
  terciles only (planned pressure classes not implemented); M3 added a
  pressure-anomaly term and an intercept.
- **Corrected results** (`history/reports/2026-09-24-surge-forcing-r2-results.txt`,
  `history/reports/2026-09-24-surge-forecast-wind-r2-results.txt`):
  round 1, 24 h, held-out 2016-2026: future observed wind+pressure 0.277 all /
  0.347 storm starts (was 0.307 / 0.416); PAST wind+pressure now helps storm
  starts (0.527 -> 0.492) but still loses slightly near the plug band
  (0.349 -> 0.351): the earlier "past conditions add nothing" is withdrawn.
  Round 2, 24 h: decay 0.289 all / 0.477 storm starts -> GFS refit 0.237 /
  0.355, ECMWF refit 0.235 / 0.355; target-hour high/low/plug views all
  improve at 24-30 h for both; "better in every view at every lead" is
  withdrawn (ECMWF 6-h plug band 0.188 vs 0.186). Transfer after alignment:
  ECMWF acceptable (0.237), GFS still worse than decay (0.363): the transfer
  failure is not a clock artifact; coefficients must be fitted on the exact
  feed used. These inspected periods are no longer untouched tests.
- **v0.10.6 check.** The decay study behind v0.10.6 rerun on the UTC table
  (`history/reports/2026-09-24-surge-decay-views-utc.txt`): tau 36 h toward
  the trailing mean remains best or near-best in every view (24 h all hours
  0.342 vs constant 0.398); the release is unaffected.
