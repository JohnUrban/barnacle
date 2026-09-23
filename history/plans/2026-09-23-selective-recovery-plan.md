# Barnacle: selective recovery and v0.10.5 plan

Prepared by Codex, 2026-09-23. Reviewed tree: `54cf87291`.
Status: **proposal, not implementation or approval**. John requested an
investigation and plan to retain intended improvements and repair or undo
regressions. Production remains v0.10.4; promotion HOLD remains in force.
This is not round-05 audit closeout. No production code, model constants,
forecast artifacts, alert state or scientific ledgers changed for this plan.

## Recommendation

Keep the useful work. Undo the connection that spreads a later tide's forecast
surge across the entire near-term curve, then complete independent verification
before promoting. Do not wholesale revert September 23, disable the NWS parser,
or rush the experimental seven-day curve into the production series.

The immediate restoration should use **fresh, despiked observed-minus-astronomical
surge** for the production continuous series, while retaining NWS coastal-product
projections for their individual high tides. This restores the operating input
policy seen before the parser began succeeding; it does not freeze the curve at
an earlier number. Observe source age and failure explicitly. The long-term
choice of a time-varying surge curve remains a separate evaluated change.

## What the evidence establishes

The parser repair `8e8e5cfcd` at 07:32 EDT activated real NWS product rows. The
existing call `build_water_series(worst['surge_ft'], qpf_result)` in
`forecast/flood_forecast_daily.py` then supplied the worst tide's surge to every
hour. `build_water_series` adds that offset to astronomy and uses the resulting
bay curve as input to the rain tank. Site chart and widget share `water_series`;
the near-term map and day_worst also consume it. The widget source itself was
unchanged. The recorded plug-level investigation request is at 13:17 EDT,
later than the parser repair; that request is not the cause of the uplift.

Primary records: `32d065b67a:docs/forecast.json` (11:11:23Z) and
`d17aa402e:docs/forecast.json` (20:13:00Z). All 55 overlapping tide-curve points
rose 0.838 ft, about 10.1 inches. For the 13 points with later gauge overlays,
10:00–16:00 EDT, average absolute gauge differences were 2.88 inches for the
earlier curve and 10.61 for the raised curve. Values and provenance are in
[recovery-evidence.json](2026-09-23-recovery-evidence.json).

Limit: the later curve redraws elapsed hours. This is a useful consistency check,
not a prospective skill score, an intersection flood-depth measurement, or proof
that persistence wins during every storm. It cannot reject NWS forecasts for
future high tides. At 20:13Z the observed surge was **+1.424 ft**, age 7.1 minutes,
whereas the series used **+2.5 ft**. Restoring fresh persistence at that issue
would lower its tide-only curve by 1.076 ft (12.9 inches), not necessarily the
10.1-inch difference from the earlier issue. Never hard-code either correction.

The current pluvial risk record has zero forecast rain over its next 24 hours.
Thus the captured uplift exists without rain. The existing model already has a
head-dependent drain response (`model/v0.10.4.md`, bay 3.0–3.52 ft NAVD88);
exploring compound rain/tide effects does not require lifting astronomy or
inventing higher bay water. No new drain constants should be fitted in this repair.

## Disposition by change

| Work | Recommended disposition | Reason / condition |
|---|---|---|
| Raw coastal-product parser and gauge-section boundaries (`8e8e5cfcd`) | Keep | Repairs real missing data. Retain per-tide source/issuance and validate against product rows; parser correctness is not skill proof. |
| Worst-tide surge fed to the whole production series | Repair first | Unintended consequence with observed evidence of poor near-term fit. Restore fresh observed-surge input with explicit fallback health. |
| Quiet-hours station-time repair (`9fea73d47`) | Keep | Restores intended pre-07:00 exemption; preserve documented SMS role and other channel rules. |
| 48-hour alert filter (`8e686a4f1` + test repair) | Keep | Explicit owner policy prevents longer outlooks broadening core alerts. Verify end-to-end isolation. |
| Separate seven-day field/page, NBM/WPC inputs, source bands | Keep as labeled outlook | Useful added horizon, not validated replacement for the production forecast or an alert input. Missingness/freshness must be visible. |
| Maps open NOW, separate worst-tide / worst-flood selectors, full horizon | Keep | Intended usability improvements. Preserve correct time, pathway, and source labels across the 30-hour source boundary. |
| Cross-pathway headlines/day_worst | Keep principle; recompute after curve repair | Rain must remain represented. A shared summary can consistently repeat an inflated input; consistency alone does not establish accuracy. |
| Human confidence-label removal and gauge-error wording | Keep | Intended communication change. Show sample size and no-data honestly; do not imply gauge skill validates street depth. |
| Shadow scorer, warm-cache validation, rain accounting, CI decoder tests | Keep repairs, independently verify | Round 04 addresses concrete defects; passing author probes is evidence, not complete acceptance. |
| Actual-bay compound burst, p90 rain scenario, NWPS/P-ETSS/decay | Retain as explicitly experimental outlook scenarios | No immediate promotion into core water_series, notifications or definitive flood probability. Keep scenario meanings separate. |
| Outlook failures mixed into production degraded_inputs | Repair next | Current `outlook_petss` warning reaches widget despite that source not driving its forecast. Scope health to consumers without hiding failures. |
| Uniform historical rollback / wholesale commit reverts | Reject | Would lose parser, time, rainfall and safety repairs and entangle generated bot data. Use small explicit behavior diffs. |

## Execution order and acceptance

### 1. Contain the near-term curve regression

Make one narrowly reviewed change to series input selection in build_forecast.
Use the existing `persisted_surge` value already acquired, despiked and age-gated;
leave per-tide NWS projections and their warning behavior intact. Record separate
series source/value/observation time/age. The existing `current_surge_ft` names the
worst tide's value, not necessarily current observed surge: audit its readers and
introduce unambiguous metadata instead of silently changing its meaning.

For missing or stale observations, expose unavailable/degraded status. A useful
astronomical line can remain visible as astronomical-only, but must not be passed
off as a complete flood forecast or feed a definitive tank prediction without
valid bay forcing. Do not quietly reinstate the maximum future surge, use stale
observations without limits, or call missing surge a measured zero. Settle this
fallback contract in the patch and tests before deployment.

Required demonstrations on the same frozen inputs:

- Extreme Friday product surge cannot lift Wednesday/Thursday continuous water;
  Friday's own per-tide NWS forecast still appears and remains alert-eligible only
  within the declared alert window.
- Fresh positive and negative observed surge propagate correctly; stale/missing
  gauge data shows the documented fallback and health, never false certainty.
- Changing product surge alone cannot change the persistence-driven tank series.
  Rain-only and compound synthetic cases still reach the tank; none is suppressed
  merely because the tide is low. Do not lower the burst warnings wholesale.
- Widget curve, site near-term chart, near-term map, flood windows, today regime,
  day_worst, and email all consume the restored field consistently. Per-tide
  product cards may differ from a persistence curve; identify that source
  distinction rather than falsely forcing them to agree.
- Evaluate alert decisions and rendered bodies separately. `compute_alert_level`
  uses per-tide/rain/radar inputs, not day_worst directly: a lower display curve
  does not authorize turning off valid official/radar warnings or resetting state.
  Nowcast's astronomy fallback explicitly calls build_water_series with surge 0;
  preserve that caller's contract and the observed-bay radar path.

Use the full production chain with frozen/mocked external inputs and no delivery,
then regenerate + gate. Validate the deployed JSON and actual page payload, not
just a successful edit or green unit tests. No widget re-copy should be required
for a pure backend series fix; if widget source actually changes, bump its footer
and explain the required re-copy. Preserve logs/state and label historical mis-stamps.

Classify this explicitly under charter rule 5: restoring the intended legacy
behavior can be a documented class-(c) fix; introducing a new fallback or source
policy is class-(b). Do not use an emergency fix label to bypass review/versioning.
The already-pending v0.10.5 class-(b) scope remains separate.

### 2. Restore the boundary between core and outlook

Split production health from outlook health; preserve the full health record and
show outlook problems on every surface using that outlook. Identify each widget,
email, site and map consumer before changing a shared field. The widget should
not warn about an unused P-ETSS source; a long-range map should warn if it needs
that missing source. Existing explicit owner preferences keep widget UI scope
unchanged unless John chooses otherwise.

Add a controlled comparison with outlook enabled vs unavailable. Core tide/rain
inputs, production series, imminent SMS eligibility and alert-window tide set
must be identical. Test alert message rendering too, not just eligibility. Scope
outlook-only failures to the outlook and verify the wall-clock bound. As a later
operational improvement, remove optional acquisition from the alert critical path
entirely; do not combine that architecture change with the first curve fix.

At the map's production/outlook splice, check for a jump at identical/adjacent
instants. Do not hide a disagreement by changing the core curve. Label the source
transition and include it in the independent review; decide on blending only as
an explicit forecast-policy change with comparison evidence.

### 3. Complete exact-candidate review and release

Round 04 and subsequent Python-3.11 hotfixes must be independently reviewed on the
final tree including the curve repair. In this planning pass, the local full
suite returned **261 tests OK**, Claude's round-04 probe exited successfully,
and the artifact gate passed. This supports retaining the repairs; it does not
close the audit. The 20:09Z failed publish is recorded honestly, not erased by a
later green run.

Acceptance matrix: different-day rain/tide headlines; past-vs-future scope;
missing/null rain at each consumer; partial first/last dates and full 168 hours;
MAE/bias/paired readiness; malformed/stale warm data; compound chart/map equality;
nested and slow-response deadlines; supported Python 3.11 import/compile and full
decoder tests. Both frozen model replays must remain unchanged. Review actual
outputs across the surfaces, not source-string assertions alone.

Then independent PASS + John's recorded promotion DECISION, followed by the
atomic specification/archive/link/code/log-doc bump. The candidate spec must
state actual production vs experimental input ladders and fallback policies.
Source-adapter deployment does not count as validated scientific improvement.

### 4. Evaluate improvements without putting them straight into production

Compare three explicit surge policies on identical issue times and target times:
(A) observed persistence, (B) the current worst-tide constant as the regression
baseline, (C) time-varying product/NWPS guidance. Reusing outlook anchoring is a
candidate, not an automatic repair: it imports an unscored input and interpolation
assumptions. The code change may be small; the behavioral change is not.

Score issued forecasts against later despiked observations by lead, high/low tide,
and rising/falling phase. Include more than the thirteen elapsed points above.
Do not rebuild old forecasts with later information and call them forecasts. Use
matched support, bias and MAE separately, peak timing and threshold crossings;
predeclare comparisons before scoring. Keep official high-tide total, astronomical
prediction and derived residual consistent; do not double-count surge or local
adjustments when constructing anchors.

For the plug-level hypothesis, separately compare existing fixed-low-bay and
actual-bay rain scenarios on primary event records. Separate radar-forced nowcast
skill from QPF-driven burst forecast skill, and calibration cases from independent
validation. Retain observed depth ranges and uncertain rain forcing. The two
compound-event anecdotes do not establish a universal plug height. Select and
justify a later model change only after this comparison; do not retune to make
this advisory's curve look right.

## If a repair fails

Stop the affected production ship, retain the last validated core behavior, and
repair the isolated diff. If the new outlook itself disrupts publishing or
notifications, temporarily disable its integration with an explicit unavailable
message while retaining collected guidance and shadow logs; re-enable after
verification. Do not wipe append-only data, reset delivery state, overwrite the
whole facade from an old copy, or revert unrelated reliability fixes.

## Decision for John

Recommended first implementation scope: **restore observed-surge production
series + scoped input health + dependent-surface verification**, preserving the
per-tide NWS product and useful seven-day additions. Time-varying surge and new
rain calibration remain separate research/promotion decisions. This document
records the recommendation; it does not record John's approval to execute it.
