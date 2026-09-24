# Forecast-wind surge term — approved shadow candidate and evaluation plan

Initial plan committed in `142907573` at 2026-09-24 09:19:45 EDT, before any
candidate evaluation. Updated 2026-09-24 after John's approval of Codex's
recommendation and Claude's shadow-only proposal. BACKLOG DECISION
`wind-shadow-open-meteo` is the owner authorization. Research corrections:
[audit round03](../../audits/2026-09-24-a2/03-close-out-codex.md).
**Status: development and shadow collection approved; no shadow implementation
or evaluation has started. Production remains v0.10.6.**

## Authorized scope and selected source

Use Open-Meteo `gfs_seamless` for the first candidate, with wind AND pressure
inputs specified together. Compute/log hourly in shadow: no change to displayed
forecasts, maps, widget, headline selection, rain predictions, or any alert.
A successful trial permits consideration for promotion; it never promotes
itself. Production requires its own version, replays, independent review and
John's separate DECISION. This approval does not purchase a subscription.

This selects a candidate source, not a permanent provider commitment. The
existing research uses fixed-lead previous-runs data; the freshest live API
is not automatically the same construction. Transferred coefficients cannot
be assumed valid; equivalence can be demonstrated or the model can be refit.
GFS transfer from the station fit still loses after the clock repair.

Alternatives remain available:
- Direct NOAA GFS: more extraction/maintenance work, with equivalence testing
  or refitting before switching. Do not equate the name GFS with identical
  values, grid selection, processing or initialization.
- NWS grid wind: conduct a bounded archive feasibility check, not an assumed
  multi-month wait. [NOAA's NDFD archive](https://www.ncei.noaa.gov/products/weather-climate-models/national-digital-forecast-database)
  exists. Verify Sandy Hook-area wind speed/direction, issuance/valid-time
  metadata, temporal/spatial mapping to Barnacle's gridpoint API, usable
  coverage and a compatible pressure source. A small extraction/comparison
  should establish feasibility before a bulk download. Record the result;
  do not silently substitute this feed into the approved candidate.

## Candidate construction and the freeze before collection

v0.10.6 surge(t) = mean + (s_obs - mean) exp(-(t - t_obs)/36 h). Candidate
family: that decay plus b1 * W + b2 * dP + b3 * P_anom + c. W is forecast
ENE (70 deg) wind stress, dP the forecast pressure change, P_anom the
observed 30-day pressure anomaly. Corrected research at 24 h: all-hours
MAE 0.289 -> 0.237 ft, storm-start MAE 0.477 -> 0.355 (gauge skill, not
street-flood skill). These historical periods have been inspected.

Before the FIRST evaluable shadow record, commit a versioned candidate
manifest, fitted coefficients and the evaluator. It must freeze:

1. Exact endpoint/model, wind/pressure variable definitions and units,
   coordinates/grid selection, interpolation, and run-selection rule.
   [Previous Runs](https://open-meteo.com/en/docs/previous-runs-api) and
   [Single Runs](https://open-meteo.com/en/docs/single-runs-api) have different
   semantics and coverage. Verify and report usable training coverage first.
2. Initialization, publication (when exposed), retrieval and valid times.
   Keep unknown publication time unknown. Fit on forecasts demonstrably
   available by simulated issuance, with a documented latency rule; nominal
   initialization alone is insufficient. Preserve raw responses and hashes.
3. The production mean policy (corrected 2026-09-24 per audit a3 R4; the
   earlier wording "364-day verified window ending roughly three weeks back"
   was wrong): forecast/surge_mean.py averages verified hourly_height minus
   predictions over the LAST 364 CALENDAR DAYS as returned, which ends at the
   verified-data end (~3 weeks before the run); cached by the warm job. Not
   the research t-1 trailing mean. Retain input health,
   observation age, state/fallback rung and production version per issuance.
4. Reading time versus issuance time, treatment of the interval already elapsed
   since a stale reading, wind-window coverage and pressure-anomaly history.
   Resolve lead interpolation (including 0–6 h), start anchoring, correction
   limits and behavior beyond supported leads before observing trial results.
   An hour's correction must use only information available at issuance.
5. Observation/QC eligibility, target-time matching, high/low/plug definitions,
   duplicate/retry handling, missing-observation rules, episode allocation,
   and comparison denominators. Use the station-time helpers and UTC transport.
   Historical retained flags are not proof that every value is fit to score.
6. Bounded request deadlines and freshness/coverage requirements. Unavailable,
   stale, invalid or incomplete required inputs produce the v0.10.6 baseline
   candidate plus an explicit shadow fallback reason. The conservative initial
   contract requires complete required wind/pressure windows; any relaxed
   partial-window policy needs its own declared experiment. Missing is not zero.

Freeze the fitted candidate for the trial. Do not refit or choose a winner
using its held-out outcomes and continue calling the same period untouched.
A changed model gets a new identity and prospective period; preserve every
prior row and report implementation/data errors honestly. Failed or unavailable
shadow opportunities must be counted, not silently omitted. Finalize the
remaining implementation details in the manifest before starting the clock.

## Build order and production isolation

1. Offline: source/archival feasibility checks, fetcher, raw-input archive,
   source-matched fit and deterministic evaluator. Compare to the live-policy
   baseline and available guidance using the same issuance and target.
2. Test isolation, then hourly SHADOW: log candidate output with the production
   and NWS/P-ETSS comparators and their provenance. Prefer a dedicated
   append-only shadow record linked to the existing replay inputs; finalize
   schema/retention before writing. Validate writer/gate round trips.
   Test that missing/bad/slow wind inputs and shadow exceptions cannot alter
   production forecast bytes, alert decisions/state, or delay normal publishing
   beyond the bounded budget. Failure must be visible in shadow health/logs.
3. Archive NWS inputs prospectively as well; implement the bounded NDFD probe
   above. Provider failure must remain tolerable. Open-Meteo's free service has
   [no uptime guarantee](https://open-meteo.com/en/pricing); no paid-service
   assumption is part of this plan.
4. Only after evaluation: review the intended production insertion point,
   obtain the separate promotion decision, and follow model-version rules.
   Plain-decay gains alone never justify replacing existing NWS/P-ETSS guidance.

## Prospective evaluation and decision rules

Start at the first record from the frozen candidate. End the primary issuance
window at the first UTC day boundary after BOTH 60 elapsed days and at least
five completed eligible storm episodes. Wait for all included target outcomes
through 48 h and the declared observation/QC maturity before final scoring.
No rolling search for a favorable end date. Interim reports are descriptive.

A storm episode requires surge >= +1 ft for at least six consecutive valid
hourly observations. Separate episodes require at least 48 consecutive valid
hours below +1 ft; merge shorter breaks. Missing observations do not prove
that an episode ended or supply the six-hour requirement. Record exclusions.
Finalize deterministic episode assignment in the evaluator before collection.

Score leads 6/12/24/30/48 h. Comparators: (i) the frozen v0.10.6 decay
estimator, (ii) the actual as-issued production curve where it exists, and
(iii) NWS/P-ETSS outlook guidance where available at the same issuance/target.
The published core curve reaches about 30 h: label any 48-h v0.10.6 estimator
extension as an offline baseline, not a published 48-h core prediction.
If production changes during the trial, retain its version and score its
cohorts separately while retaining the frozen v0.10.6 comparison.

Use one eligible issuance per scheduled hourly opportunity, deterministic
retry selection, matched candidate/baseline targets and equal issuance weights
within each lead. Report coverage and eligible counts for each comparison;
NWS/P-ETSS absence does not become zero. Score candidate fallback hours in
the primary comparison and also report healthy-feed-only results. Missing
outcomes remain unscored with counts; missing candidate opportunities remain
visible and cannot manufacture a clean sample.

Views: all hours; high/low tides and plug-band hours at TARGET time; storm
starts at issuance (observed surge >= +1 ft); per-episode MAE with episodes
weighted equally; signed bias (prediction minus observation); large absolute
errors >1 ft and large underpredictions (prediction minus observation < -1 ft);
missing-feed fallback; hourly continuity and source/feed transitions.
Report dependence-aware uncertainty, not hourly samples as independent storms.

Pass criteria retained from the initial plan, with denominators made explicit:
- Lower MAE than frozen v0.10.6 at BOTH 24 and 30 h, in all hours AND storm starts.
- No MAE loss >0.01 ft in the target plug band at ANY tested lead.
- No increase in large-underprediction rate versus the paired baseline at
  ANY tested lead (same eligible issuance-target denominator).
- Lower per-episode MAE in a strict majority of eligible episodes, separately
  at 24 and 30 h. Ties do not count as wins. Report equal-episode mean as well.
- A required empty/insufficient comparison means INCONCLUSIVE, not PASS.

Evaluate rain-tank water and landmark depths using identical as-issued rain
inputs under baseline versus candidate bay levels on wet events. Keep scenario
sensitivity separate from observed street-depth skill. With fewer than three
wet events these results are descriptive, not a rain-skill pass/fail; with
three or more, report the paired evidence for independent review. Passing
surge criteria never establishes improved rain-flood skill by itself.

The criteria above qualify the candidate against plain decay. NWS/P-ETSS
comparisons must establish where, if anywhere, the candidate warrants use
when that guidance exists; there is no blanket authorization to replace it.
Any proposed production promotion must explicitly address low-tide/drain/rain
behavior and material operational regressions. Failing or inconclusive is a
valid result. Sixty days and five episodes are minimum evidence, not a
calendar promise to ship.

## Reconciliation with candidate c2 (appended 2026-09-24 after audit 2026-09-24-a3)
Candidate c1 (d82a82970) was retired before any official record; its only
records were two local smoke tests (models/wind_shadow/SMOKE_TESTS.md,
excluded). The candidate for the trial is **wind-shadow-c2**; its frozen
bundle is listed in models/wind_shadow/FREEZE.md. The requirements below are
frozen in `history/scripts/evaluate_wind_shadow.py` (declared rules in its
docstring) and supersede any looser reading of this plan:
- Official records only from the production workflow with
  BARNACLE_WIND_SHADOW_TRIAL=1; records bound to c2's manifest and runtime
  hashes; other identities, previews and hash mismatches excluded and counted.
- Opportunities: one per UTC hour; missing, error, fallback and immature
  counts reported per lead; fallback hours keep the frozen baseline.
- Episodes use CONSECUTIVE valid hours for both the 6-h onset and the 48-h
  quiet tail; the endpoint uses each episode's actual completion time.
- FINAL requires coverage (candidate or fallback slots / opportunities) >=
  0.80 and >= 5 SCORABLE completed episodes at 24 h and at 30 h (>= 6 matured
  valid pairs covering >= 50 % of the episode's valid hours); otherwise the
  verdict is INCONCLUSIVE.
- Comparators: frozen v0.10.6 baseline (primary), the actual production curve
  within its ~30-h reach (cohorts by production version), NWS/P-ETSS by
  source; leads beyond 30 h compare with an OFFLINE 48-h baseline extension.
- Rain-tank sensitivity joins the replay archive's as-issued hourly QPF and
  astronomy; descriptive with fewer than 3 wet events.
- Observation QC: finite value and exactly four zero flags; raw responses
  saved with hashes; offline replay via --obs-json.
