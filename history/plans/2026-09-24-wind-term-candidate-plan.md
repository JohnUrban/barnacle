# Forecast-wind surge term — candidate plan and PREDECLARED evaluation

Written 2026-09-24 (see this file's git commit time; no candidate evaluation
has been run). Follows audit 2026-09-24-a2 (Codex round 01, Claude reply 02).
Status: plan only. No production code, no shadow code yet.

## What would change
v0.10.6 surge(t) = mean + (s_obs - mean) exp(-(t - t_obs)/36 h). Candidate:
the same decay PLUS an additive forcing term b1 * W + b2 * dP + b3 * P_anom + c,
W = mean forecast ENE (70 deg) wind stress over (t_obs, t], dP = forecast
pressure change, P_anom = observed 30-day pressure anomaly, coefficients per
lead band, fitted on the EXACT live feed. Research basis (exploratory, not
untouched): corrected round 2, 24 h, all hours 0.289 -> 0.237 ft, storm
starts 0.477 -> 0.355 (gauge surge error, not street-flood skill).

## Owner decision needed before any code: the live wind feed
The coefficients do not transfer between feeds (GFS transfer was worse than
plain decay even after the clock fix), so the feed IS the model.
- (a) Open-Meteo `gfs_seamless` (NOAA GFS/HRRR redistributed): the tested
  feed; live forecast API; archive for refitting. A third-party production
  dependency (so far Open-Meteo is display cross-check only).
- (b) NOAA GFS directly (NOMADS GRIB live; AWS/NCEI archive for fitting):
  NOAA-hosted; heavier engineering; must be re-tested (not the tested feed).
- (c) NWS gridpoint wind (already fetched hourly): no easy archive, so a
  long shadow period before any fit.
Claude's recommendation: (a) for a SHADOW candidate, because it is the tested
feed; revisit before any production promotion.

## Construction parity (Codex R4)
Training must replay the live policy: the run actually available at issuance
(initialization + publication latency), not valid-time "previous_dayN"
stitching; check the Single Runs / historical archive's coverage first and
report the usable span. Replay the production mean policy (the warm job's
364-day verified window ending ~3 weeks back), not a t-1 trailing mean.
Partial wind windows (< 100 % coverage) are labeled and tested; a missing
feed falls back to plain v0.10.6 decay, visibly.

## Build order
1. Offline: fetcher + archive of raw forecasts with initialization,
   publication (if exposed), retrieval and valid times; fit script.
2. SHADOW: the hourly run computes the candidate surge and logs it next to
   production in `data/replay_inputs/` (no display, no alerts).
3. Only after the evaluation below: a separate model version with replay
   goldens, every surface, independent review, John's DECISION.

## Predeclared evaluation (prospective shadow period = the untouched test)
Period: from the first shadow record until BOTH (i) 60 days and (ii) at least
5 distinct storm episodes (surge >= +1 ft for >= 6 h, episodes separated by
>= 48 h). Scored against later gauge observations at leads 6/12/24/30/48 h.
Comparators: production v0.10.6 decay (the 30-h curve) AND, where it exists,
the 7-day outlook's NWS/P-ETSS guidance at the same hour.
Views: all hours; high, low and plug-band hours at the TARGET time; storm
starts at issuance; per-episode MAE (episodes weighted equally); signed bias;
large errors (|err| > 1 ft) and large UNDER-predictions separately; missing-
feed fallback hours; hourly continuity at source/feed transitions; rain-tank
water and landmark depths on any wet event in the period (reported, not a
pass/fail when fewer than 3 wet events occur).
Pass (all required): lower MAE than v0.10.6 at 24 and 30 h in all hours and
in storm starts; no loss > 0.01 ft in the plug band at any lead; no increase
in the rate of large under-predictions; per-episode MAE better in a majority
of episodes. Anything else is reported as found; failing is a valid outcome.
