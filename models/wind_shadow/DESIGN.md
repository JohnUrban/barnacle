# Wind-shadow candidate c1 — construction and coefficient-route rule

Written before the equivalence comparison below was computed (see git time).
Plan: `history/plans/2026-09-24-wind-term-candidate-plan.md` (owner decision
BACKLOG `wind-shadow-open-meteo`). Shadow only; production stays v0.10.6.

## Feed and run selection (live AND training, identical)
- Open-Meteo Single Runs API, `models=gfs_seamless` (the endpoint resolves it
  to NOAA GFS 0.13 deg, `ncep_gfs013`), variables `wind_speed_10m` (kn),
  `wind_direction_10m` (deg FROM), `pressure_msl` (hPa), hourly, at
  40.4669, -74.0094 (Sandy Hook station; the API returns grid point
  40.461933, -74.00509, recorded per response).
- Run rule: the latest 00/06/12/18Z cycle with init <= issuance - 6 h
  (LATENCY_H = 6). Measured on 2026-09-24: availability 5.6 h after init
  (`ncep_gfs013` meta.json). Live, the run must also be confirmed available
  (meta `last_run_initialisation_time` >= that init); otherwise the previous
  cycle is used and the record says so. Meta times are logged every run so
  the 6-h rule can be checked prospectively.

## Features (issuance t, lead h = 1..48 h)
- W_h = mean of spd * |spd| * cos(dir - 70 deg) over valid hours (t, t+h]
  from the selected run; ALL h hours required (complete windows; missing is
  not zero).
- dP_h = forecast pressure at t+h (selected run) minus OBSERVED station air
  pressure at t (CO-OPS `air_pressure`, latest reading <= 60 min old).
- P_anom = observed pressure at t minus its trailing 30-day mean (>= 20 days
  of hourly values required).

## Baseline and candidate
- Baseline = production v0.10.6: mean + (s_obs - mean) exp(-(t+h - t_obs)/36 h)
  with the production mean policy (364-day verified window ending ~3 weeks
  back, cached by the warm job). In training this policy is replayed: mean =
  mean surge over [t - 21 d - 364 d, t - 21 d).
- Candidate = baseline + c_h, c_h = b1_h W_h + b2_h dP_h + b3_h P_anom + a_h,
  fitted separately for EVERY integer lead 1..48 (no lead interpolation).
  |c_h| capped at 3.0 ft (flagged). Beyond 48 h: no correction (labeled).
- The candidate runs only with a FRESH reading (<= 60 min) and complete
  inputs; otherwise the record carries the baseline and a fallback reason.

## Coefficient route (decided by this rule, before the comparison is seen)
Two ways to fit: (A) on the ~5 months of single runs (the exact live
construction), (B) on the longer previous-runs archive (2024-02 on), whose
construction differs (valid-time stitching of day1/day2 runs).
Rule: compute W_h from both constructions over their overlap for h = 12,
24, 30 h. If for all three the Pearson correlation >= 0.95 AND the
through-origin slope is within 0.9-1.1, the constructions are declared
equivalent for this purpose and route (B) is used (more storms, winter
included), fitted with the replayed production mean and purged split, and
applied to single-run features live. Otherwise route (A) is used. The
outcome and numbers are recorded in `manifest.json`.

## As built (appended after the fit; the rule above was applied unchanged)
- Route outcome: NOT equivalent (W_12 r = 0.943; W_30 r = 0.857, slope
  1.47), so route A: coefficients fitted on single runs only (issuances
  2026-04-02 .. 2026-09-20, 4,098 hours; spring and summer only, no winter
  storms: a stated limitation). Numbers in `manifest.json`.
- Forecast hours requested: 0..60 (a run chosen with the 6-h rule can be up to
  11 h older than the issuance hour, and leads reach 48 h).
- Observed pressure at issuance: the 6-min `air_pressure` value AT the
  issuance hour, else the latest value <= issuance and <= 60 min old (the
  hourly product publishes the top-of-hour value too late for the run). The
  30-day anomaly uses the hourly product's values in [t - 30 d, t).
- A non-fresh reading, any incomplete window, missing pressure, or a feed
  error -> the record carries the baseline and the reason (never zeros).
