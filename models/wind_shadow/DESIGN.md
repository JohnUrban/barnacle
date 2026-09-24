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

## c2 (audit 2026-09-24-a3 repairs; c1 retired before any official record)
The construction rule and route outcome above are unchanged (route A). Changes:
- Mean policy (R4): replays forecast/surge_mean.py: verified hourly_height
  minus predictions over the last 364 calendar days, as returned (verified end
  ~24 d before issuance, measured once: an assumption for history). The c1
  wording ("364-day window ending ~21 days back", a shifted 364-d window) was
  wrong, as was the plan's; the difference to c1's construction is 0.0055 ft
  mean, 0.021 ft max over the fit span.
- Pressure (R4, R5): QC = finite and all three flags 0; anomaly over the 720
  hourly values in [t0 - 30 d, t0), >= 480 required (live and training);
  current value = the issuance-hour value, else the latest 6-min value within
  60 min, with the basis recorded (a declared live-only substitution). Raw
  CO-OPS responses, hashes, retrieval times and rejected-row counts are stored
  per record. Training uses the hourly product with flags (re-pulled).
- Targets: nominal UTC hours t0 + h from the issuance hour t0; the training
  reading is the 6-min value at t0, the live reading <= 60 min old (production
  metadata, recorded). A declared approximation.
- Run selection (R5): the 6-h-rule cycle is used ONLY if provider metadata
  confirms it available by the issuance time; otherwise fallback (no older
  substitute, so live equals training). Historical availability is an
  assumption (one metadata observation: 5.6 h); the trial checks it.
- Frozen baseline (R6): the decay uses the manifest's tau, not production's;
  the actual production curve is recorded separately as a comparator.
- Records (R2, R6, R7): identity (candidate_id, manifest and runtime SHA-256,
  collection, GitHub run id) in every record; the baseline is built before any
  network call so timeouts keep it; complete records are validated before a
  single O_APPEND write; invalid ones go to data/wind_shadow/quarantine/.
- Publication (R7): the shadow log is NOT part of the fatal publish gate
  (check_artifacts prints warnings); CI enforces its validity and binding.

## Trial identity and start (R8)
- Official records: written only by the production workflow step that sets
  `BARNACLE_WIND_SHADOW_TRIAL=1`, into `data/wind_shadow/YYYY-MM.jsonl`,
  `collection: "official"`. Local runs collect nothing unless
  `BARNACLE_WIND_SHADOW_PREVIEW_DIR` is set (preview records, excluded).
- The trial starts at the first official record of the frozen c2 bundle after
  the branch is merged. Before that, review changes update FREEZE.md; after it,
  any change to a frozen file needs a new candidate id and a new period.

## Round-03 repairs (audit 2026-09-24-a3 round 03; appended before any official record)
Supersedes the two bullets above where they differ.
- Trial start (R8, R6): merging only ENABLES the production workflow. The
  trial starts at the nominal hour of the FIRST durable (committed) official
  record of wind-shadow-c2, whatever its status. Disabled or unbound records
  after that count as missed opportunities; they never move the start.
- Bundle enforcement (R6): before an official record the runtime hashes every
  FREEZE-listed file, the manifest it actually loaded and itself; any mismatch
  writes a `disabled` record (reason, hashes; no fetch, no values). Every
  record carries `bundle_sha256` (the canonical FREEZE id/table hash). The
  evaluator refuses to score (exit 3) unless every bundle file matches AND the
  trial log's first official record binds the same bundle; `--unfrozen`
  scores but labels the report NON-OFFICIAL. CI checks the same first-record
  binding, so editing a file and its FREEZE entry after the start fails.
- Execution mode (R8): the opt-in makes a record official only when the parsed
  mode is known and is neither --no-send nor --dry-run.
- Rain (R3): each record stores production's AS-ISSUED tank inputs: the 30-min
  series from its start (storage empty there, as production), its bay, the
  surge it used per point, the QPF rate per point (production's hour lookup)
  and its pluvial line. The evaluator runs the FROZEN tank
  (models/wind_shadow/rain_ref.py + stage_storage_curve.csv copy, equal to
  production at freeze) from that start. Before and at issuance both variants
  share production's bay; after it, bay = production bay + (variant surge -
  production surge), the candidate correction linear between whole-hour leads.
  Scored: peak depth and hours above every flood-window landmark.
- Guidance (R3): raw NWPS (gauge forecast minus hourly astronomy, no advisory
  correction) and the P-ETSS hourly mid are stored per target with issue and
  retrieval provenance, apart from Barnacle's final outlook (renamed
  `barnacle_outlook_surge`, its own comparator by source).
- Run availability (R5): the selected run is accepted only if metadata shows it
  (or a newer run: in-order publication assumed) available by issuance.
- Pressure (R5): returned current values must satisfy 0 <= issuance - t <=
  60 min; the anomaly counts distinct hourly timestamps; the 31-day hourly
  response is kept losslessly (gzip + base64) with its SHA-256 and the
  rejected rows.
- Water-level QC (R5): VALID = finite, four integer flags [O,F,R,L], F = R =
  L = 0. O is CO-OPS's count of 1-s samples outside a 3-sigma band, not a
  tolerance failure; requiring O = 0 would drop elevated-surge hours
  preferentially (fit span: 7.9 % of 1.0-1.5 ft hours vs 1.8 % below 0.5 ft).
  The fit's OUTCOMES pass this QC from a flagged re-pull (values identical to
  the training table); the reading and the mean mirror production (no flag QC).
