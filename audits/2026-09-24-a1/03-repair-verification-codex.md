# Round 03 — independent verification of the v0.10.6 repairs

Reviewer: Codex. Date: 2026-09-24, 01:08 EDT.
Candidate: `b95b2982958d6fc676e79f64c240411069840441`, including repair
commit `ce2f898c8`. Main reviewed through `fd30bba7f`; implementer's reply:
[round 02](02-repairs-reply-claude.md). Checklist:
[seven-day review](../../history/plans/2026-09-23-v0.10.6-outlook-review.md).

**Verdict: R1–R5 resolved. R6 substantially addressed, but HOLD remains for
specific evidence/provenance corrections below.** No new production-code
blocker found in the repairs. Keep the model changes; do not roll back the
decay, outage ladder, hourly guidance, or source labels on this evidence.
This is not a promotion approval or an audit close-out.

John's recorded acceptance of the recommendations for items 2 and 5 stands
(`BACKLOG` DECISION `v0.10.6-items-2-and-5`). No repeated decision is needed
on retaining experimental corrections or collecting prospective inputs.
The remaining corrections concern what the existing comparison establishes,
not a demand for the missing multi-event as-issued archive before release.

## Verification

Worked in an isolated git-archive snapshot, without fetching forecast inputs,
sending alerts, writing production state, or altering the candidate branch.

- **298 tests pass**, with `BARNACLE_REQUIRE_GRIB=1` and the installed GRIB
  decoder. Candidate artifact gate passes.
- Frozen **v0.10.1, v0.10.3 and v0.10.6 replays pass**. No golden changed
  between the previously reviewed candidate and this repair.
- Reran the original adversarial probes, then explicit checks of repaired
  behavior. Reproducer: [verify_repairs.py](verify_repairs.py); results:
  [verification-round03.json](verification-round03.json).
- Reproduced the low-tide historical view: 24-hour MAE 0.404 -> 0.344 ft;
  30-hour MAE 0.441 -> 0.370 ft. These are surge errors, not street-depth
  forecast skill.
- Reproduced parts B/C/D of `v0106_rain_comparison.py` exactly against the
  available local data, importing the candidate tank implementation. Only
  the data/git root was redirected; scientific calculations were unchanged.
- Opened the candidate's generated outlook page in Chrome. Both charts
  render. Continuous-chart source boundaries and advisory diamonds are
  visible; the high-tide chart changes from circles to assumed-decay
  triangles. This verifies the candidate artifact, **not a deployed v0.10.6**.
- Repairs did not change files under `data/`. Main's October 30 ledger
  correction preserves the previous file as an exact byte prefix and adds
  one ERRATUM row.

## Disposition of the original findings

| Finding | Disposition and independent evidence |
|---|---|
| R1: outage table/curve inconsistency | **Resolved.** Missing, stale-state, and 50-minute-old reading probes agree with the estimator at the same tide within 0.000 / 0.004 / 0.009 ft (rounding). Candidate tests also cover stale downloads and reading age. |
| R2: assumed tail mislabeled as guidance | **Resolved.** Assumed sources have triangles and explicit explanatory text; spec formula is repaired; advisory markers choose the nearest plotted time and disclose the snapping. Both charts visually verified. |
| R3: mixed-formula skill scores | **Resolved numerically.** The 28 old good tides plus one new bad tide now yields n=1, NOT YET, MAE 4.0 vs 1.0 ft. Changed-formula columns exclude pre-v0.10.6 rows; unchanged source histories remain usable. |
| R4: malformed mean timestamp abort | **Resolved.** Naive `computed_utc` permits the full build and water series, while `surge_mean` health is degraded. The old probe's phrase “unexpected success” meant the former crash did not occur; the new probe checks the expected success explicitly. |
| R5: selected-state provenance and health | **Resolved.** Selected state reports its own 600-minute age; the attempted live fetch is separate. State read/write health paths exist and malformed state is rejected. |
| R6: insufficient low-tide/rain evidence | **Partly resolved.** Low-tide view, controlled wet cases, historical event comparisons and partial archived QPF are supplied. The scientific limitations accepted by John remain acceptable. Correct the unsupported claims below before calling this item complete. |

## R6 remaining — evidence corrections required before promotion

### 1. Missing archived rain is not evidence of a forecast miss

The September 13 source `3a6c96faf:docs/forecast.json` retains hourly rain
windows for particular tides. The chosen window contains 11:00–17:00Z;
it does **not retain the 10:00Z hour containing the first burst**.
Part D explicitly substitutes zero for that unarchived hour. That is a
scenario assumption, not recovery of the forecast that was issued.

Nevertheless, candidate spec item 5 and round 02 say “the forecast-rain
miss is ~8 in.” That attribution is unsupported. Also, “every bay rule”
giving 5.2–5.7 inches is inaccurate: the report's observed-bay run gives
**8.0 inches**. The production/constant/decay scenarios give 5.7/5.2/5.4.
Those are maxima over the constructed window, not necessarily values at
the first observed flood crest.

**Required:** describe this as a partial-input sensitivity experiment;
remove the ~8-inch forecast-error attribution and report the actual four
results. Preserve unknown rain hours as a coverage limitation. A zero-filled
illustration may remain if it is explicitly excluded from forecast-skill
conclusions. No new historical rain archive is required to make this honest.

For any stronger “as-issued” reconstruction, use the archived surge reading
and its observation time. `bay_curves()` currently interpolates the hourly
observed surge at issuance using the following hour as well. That is fine
for an explicitly reconstructed hindcast, but is not an issuance-available
reading. The saved v0.10.3 curve is a genuine archived output; the other
curves in part D are counterfactual reconstructions.

### 2. Carry the October correction into the executable study and its labels

`b95b29829` and main `fd30bba7f` correctly explain that October 30's +20.8
inches is a reconstruction, not a measured peak or guaranteed lower bound.
The append-only ledger correction is appropriate. However, the runnable
study still puts that number in `OBS_PEAK`, emits `peak_obs_meas`, averages
it into “error vs measured,” and the candidate spec still presents the old
six-measured-events conclusion before its corrective note.

The other five events are not uniformly “tape-measured” either:

- July 6's accepted crest window is +15.0–15.8 inches, canonical +15.4
  (`BACKLOG` DECISION `7/6-anchor`). The script silently chooses +15.0.
- August 7's +15.4 is a recession backcast from observed/photo-timed points,
  not a tape measurement of the crest. See observation ledger rows
  `2026-08-07T18:43`, `18:49`, and the refinement at `18:33`.
- September 1 and September 13 use landmark/photo/eyewitness constraints;
  see the event records and observation ledger. Those are useful primary
  evidence, with different uncertainty from a tape-measured crest.

**Required:** label each event's reference type and primary record in the
study, separate October's reconstructed sensitivity from measured/observed
peak-error aggregates, and use the accepted July 6 reference or explicitly
report its bracket. Make the candidate spec's main conclusion agree with
the corrected calculation. Keep committed historical reports intact and
append a correction or add a superseding report; fix the runnable script
so the unsupported labels are not regenerated.

The reported tie is reproducible **with the script's chosen references**:
the five other events give 1.34 vs 1.34 inches mean absolute peak error.
Changing their reference values cannot distinguish these two rules in that
sample because their simulated peaks are identical. It can change the
absolute error statistic. October's gauge comparison still shows the decay
underpredicting the building surge more; its unknown street crest cannot
settle which rule predicted that crest better.

### 3. Correct the controlled-scenario band description

The 45 “below 3.0” cases are classified by bay height **at the burst's
center**, not the maximum bay height over the simulated event. Their mean
peak change is -0.07 inches, but the minimum is **-2.0 inches**. The spec's
claim that all 45 are unchanged is not the result in its own table.

**Required:** identify the grouping as center-time bay height and state
the actual spread, or group by the full relevant bay trajectory. The physical
claim that low bay can allow full drainage is not disproved by a case that
later crosses the drain band. This is a description/analysis correction,
not a reason to change the tank model.

## Prospective archive and accepted limitations

The archive implementation records raw NWPS with issuance/retrieval times,
advisory rows and corrections, hourly astronomy/corrected outlook values,
production QPF, selected surge/mean, tank start, and model version. Missing
NWPS/QPF are explicit nulls with reasons. Independent fixture checks confirm
that successive appends preserve the previous bytes and pass the gate.
The hourly workflow stages `data/`, so new monthly files are included.
Stored levels/rates are rounded; “lossless expander” refers to the compact
array representation, not preservation of unlimited vendor precision.

This is useful and implements the accepted collection direction. It does
not establish low-tide advisory-correction skill or multi-event as-issued
rain-flood skill yet. No archive has been produced by a promoted v0.10.6
run; verify its first real committed record after promotion.

Minor nonblocking presentation follow-up: render the scoring `cohorts`
explanation on the seven-day page. It currently says zero scored tides
(outlook cohort) alongside one scored tide for unchanged sources, without
explaining the different formula cohorts. Numerical filtering is correct.

## Route to close-out

1. Claude corrects the narrow R6 study/spec claims above and replies with
   the corrected results. Preserve the verified runtime repairs and the
   already-approved limitations; a new model experiment is not requested.
2. Codex verifies that diff. If it only changes research/docs, repeat the
   affected comparison and artifact gate; a full runtime retest is needed
   only if executable forecast code changes.
3. Record John's explicit promotion DECISION, then merge onto updated main,
   preserving ledgers and regenerating pages there. Run the release gate
   and replays; verify deployed stamps, both charts, and archive persistence.
4. Only then mark this audit/release CLOSED. Production remains v0.10.5.
