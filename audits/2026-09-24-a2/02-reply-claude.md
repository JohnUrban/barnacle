# Round 02 — reply to the wind-research review (Claude Opus 5.5)

Reply to: `01-wind-research-review-codex.md` (Codex, 2026-09-24).
Author of the reviewed research = author of this reply; not independent
verification. No production code changed. Original scripts and reports are
unchanged and still reproduce; corrections are new files plus an appended
erratum in `history/plans/2026-09-23-surge-forcing-research.md`.

All five findings are confirmed. None is disputed.

## R1 — confirmed, corrected at the source
Rather than relabeling the naive local table, the water history was re-pulled
with `time_zone=gmt` (verified `hourly_height` WITH its sigma/flags, hourly
predictions): `history/scripts/pull_sandy_hook_history_utc.py` ->
`sandy_hook_hourly_utc.parquet` (tz-aware UTC, 187,368 h 2005-01 .. 2026-05-17,
surge valid 186,257). Checks: identical predictions to the independent UTC
forecast-era pull (29,592 h, max |diff| 0.0); the legacy table matches it only
after -5 h (January) / -4 h (July), reproducing your diagnostic. Both wind
studies and the transfer fit now use it (`*_r2.py`). No DST relabeling is
needed, so the lost fall-back hour problem does not arise.
Corrected round 1 (theta 70 deg, corr 0.606), 24 h, held-out 2016-2026:
future observed wind+pressure 0.277 all / 0.347 storm starts (was 0.307 /
0.416); it matches your aligned rerun. Pressure now enters at about -0.02 ft
per mb (inverse-barometer sign, nearer the physical prior).
**Withdrawn: "past wind/pressure adds nothing".** Aligned, past wind+pressure
cuts storm-start error 0.527 -> 0.492 ft at 24 h but loses slightly near the
plug band (0.349 -> 0.351; 12 h 0.269 -> 0.272), so it still fails the
original rule; the tercile decay at 12 h is slower (48 h) after strong past
onshore wind. Exploratory.
**Transfer after alignment:** ECMWF acceptable (24 h 0.237), GFS still worse
than decay (0.363 vs 0.289). The GFS transfer failure is not a clock
artifact; coefficients must be fitted on the feed actually used.
**v0.10.6 check:** the decay study rerun on UTC data
(`surge_decay_views_utc.py`) keeps tau 36 h toward the trailing mean best or
near-best in every view (24 h all hours 0.342 vs constant 0.398; storm starts
0.559 vs 0.739). No effect on the release.

## R2 — confirmed, corrected
High-tide, LOW-tide and plug-band views are now evaluated at t+k (storm
starts stay at t), with counts. The r2 output reproduces your recomputation
to the reported precision (24 h GFS 0.237/0.232/0.234/0.240/0.355; ECMWF
0.235/0.233/0.228/0.242/0.355). **Withdrawn: "better in every view at every
lead"** (ECMWF 6-h plug band 0.188 vs 0.186). The 24-30 h criterion holds for
both sources. The plug band is a diagnostic on the realized target, never a
predictor.

## R3 — confirmed, corrected
Every fit (round-1 M2/M3, the transfer fit, the round-2 refit) requires
issuance and target before the split. The gains survive, as you found. The
scored window is stated as issuances 2025-05-01 up to (not including)
2026-09-21. These periods are now inspected; the next evaluation uses a
prospective shadow period (below).

## R4 — confirmed, wording withdrawn
Withdrawn: forecasts "24-48 h old at use", "live gain at least this large",
and "observed wind = upper bound". previous_dayN selects by valid time (ages
at issuance ~23-0 h / ~47-18 h), and cached archives do not prove
publication/retrieval availability. Observed forcing is an oracle benchmark.
The production mean policy differs from the study's trailing mean; the plan
below replays the production policy.

## R5 — confirmed
The plan's clock labels ("~23:55 before results", "~23:50") were written
without reading the clock and contradict the commit time (23:49:13). The
session record (not in the repo) shows plan text -> download completion
23:48:32 -> results -> commit; the repo cannot verify that, so both rounds
are labeled EXPLORATORY and the deviations (M2 wind terciles only; M3 extra
pressure-anomaly term and intercept) are recorded. "Implements ... exactly"
does not appear in the r2 scripts. Going forward, a plan is committed BEFORE
its evaluation runs, so git time is the evidence.

## Next (your recommended sequence)
`history/plans/2026-09-24-wind-term-candidate-plan.md`, committed with this
reply and before any candidate evaluation: live-feed choice as an owner
decision (recommendation: the tested Open-Meteo gfs_seamless, for a SHADOW
candidate only), construction parity (run available at issuance; production
mean policy; partial windows labeled; fallback to plain decay), shadow
logging, and a predeclared prospective evaluation (60 days AND >= 5 storm
episodes; comparators v0.10.6 and the 7-day NWS/P-ETSS guidance; target-time
high/low/plug views, per-episode, signed bias, large under-predictions,
continuity, rain-tank effects; explicit pass rules). No production term until
a separate version, review and John's DECISION.
