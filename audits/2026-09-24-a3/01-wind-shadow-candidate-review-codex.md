# Wind-shadow candidate review — HOLD before merge / trial start

**Audit:** 2026-09-24-a3 — OPEN, independent author reply required.
**Reviewer:** Codex, with independent Codex fit and evaluator checks.
**Reviewed candidate:** `wind-shadow` at `d82a82970`; construction rule `f66c077d5`.
**Production at review:** `01881501b`, v0.10.6.
**Date:** 2026-09-24 EDT. **Readiness:** Needs revision.
**Completeness:** targeted code/fit/evaluator review complete; historical publication
availability and the NDFD mapping experiment remain unverified as noted below.

Do not merge or start the official trial yet. Keep the candidate and repair the
trial machinery. This is not a rejection of the wind signal or a request to
change the approved feed. John already approved shadow development. No candidate
code, coefficients, trial data, production forecasts or alerts were changed by
this review. The separate social plan is unrelated.

## Findings, in decision order

### R1 — P1: the evaluator can conclude PASS without the agreed storm evidence

In `history/scripts/evaluate_wind_shadow.py:98–123`, missing/invalid hours are
skipped while accumulating both six high-surge hours and 48 quiet hours. The
approved plan requires **consecutive valid** hours. The existing test explicitly
expects five high hours, a gap, then one high hour to count as an episode.
At lines 184–190, completion is reconstructed as last-high plus 48 hours instead
of the actual completion time. This can move the fixed cutoff backward across a
missing-data interval.

Independently reproduced in [evaluator-results.json](evaluator-results.json):

- Five high hours + one missing hour + one high hour incorrectly qualifies.
- Twenty-four quiet hours + a missing hour + twenty-four quiet hours incorrectly
  completes a storm's quiet tail.
- A synthetic fifth storm's cutoff becomes December 8 instead of December 17.
- A separate case reports **FINAL PASS from 30 records in 1,464 opportunities**,
  with 1,434 opportunities missing and only **one scored storm** at 24/30 hours.
  Five storms occurred in the gauge history; that is not five adequately evaluated
  candidate episodes. `episodes_completed` alone unlocks final status.

**Fix (Proposed):** reset qualifying counters across gaps, retain actual
`completed_at`, and derive the deterministic cutoff from that value and the
60-day minimum. Freeze scorable-episode/coverage requirements before collection;
require adequate paired evidence from at least five eligible completed episodes
for the primary storm decision. Insufficient evidence is INCONCLUSIVE. Correct
the contrary test and cover gap, maturity and cutoff boundaries. Preserve the
rule that the end date cannot be selected for favorable performance.

### R2 — P1: unavailable inputs and invalid observations can distort scoring

`forecast/wind_shadow.py:290–295` writes timeout/error records with null baseline,
candidate and lead arrays. `pairs()` then drops them. Thus a slow feed does not
produce the specified baseline fallback in the primary comparison, although the
production anchor was available. The normal explicit-fallback path does retain
baseline values; the timeout path must do the same when the anchor is usable.

The observation parser (`evaluate_wind_shadow.py:91–93`) treats missing flags as
zeros, filters malformed flag text away, and accepts a nonfinite water value as
valid. The active-hour opportunity count also excludes an hour whose record it
includes: four records through 03:00 evaluated at 03:30 yields three opportunities
and **missing_or_error = -1**. These are demonstrated synthetic failures, not a
claim that NOAA is currently returning malformed rows.

Evidence: [isolation-results.json](isolation-results.json),
[evaluator-results.json](evaluator-results.json). NOAA documents distinct quality
flags and preliminary/verified status; preserve their meaning and the declared
eligibility rule. [NOAA response schema](https://api.tidesandcurrents.noaa.gov/api/prod/responseHelp.html).

**Fix (Proposed):** construct baseline targets before network work and retain them
on bounded failures; distinguish impossible baseline computation from unavailable
wind. Require finite values and the exact declared QC schema, retaining explicit
exclusion reasons. Use one consistent hourly opportunity index and report counts
for missing issuance, immature target, missing/invalid outcome and fallback at
each lead. Never obtain a cleaner primary sample by dropping difficult feed hours.

### R3 — P1: the frozen evaluator omits required comparisons and rain checks

The evaluator scores only `candidate_surge_ft` against `baseline_surge_ft`.
`nws_outlook_surge` and `production_model_version` are not read by its scoring
code. Logging a comparator is not evaluating it. The following approved outputs
are absent:

- Actual as-issued production curve and NWS/P-ETSS comparisons with matched
  targets, coverage and production/source cohorts.
- Per-episode MAEs and an equal-episode mean (only counts/wins are emitted).
- Hourly continuity and source/fallback transitions.
- Paired rain-tank/landmark sensitivity under identical as-issued rain inputs,
  with the stipulated descriptive treatment when fewer than three wet events
  exist. Absence of current observations is not a reason to omit this evaluator.

The available replay-input archive is a useful starting point, but the current
code neither joins it nor proves it retains all required as-issued comparators.
Bias and large-absolute-error output also lacks the baseline counterpart.

**Fix (Proposed):** implement and freeze these comparisons and their joins,
eligibility rules and missing-input reports before collection. Show the distinction
between a published ~30-hour core curve and the offline 48-hour decay extension.
Use synthetic fixtures to exercise the reports without pretending to have live
trial results. A scope deferral would need to be explicit; do not describe this
as the completed evaluator for the approved plan.

### R4 — P1: “exact production mean replay” is incorrect

`fit_wind_shadow_c1.py:35` uses a full 364-day rolling mean shifted back 21 days.
That reaches about 385 days into the past. Actual `forecast/surge_mean.py:38–40`
requests the **last 364 calendar days**, then averages the paired verified data
returned within that request. Its end depends on actual verified-data availability;
it does not shift the entire 364-day window backward by 21 days.

The approved plan itself described this inaccurately. That wording came through
the earlier planning/review process; this is not solely an implementation error.
Correct the plan, DESIGN, manifest and fitting construction together.

Training also uses six-minute-on-hour history instead of the verified hourly
product used by the production mean. A same-series window-only sensitivity reaches
0.01783 ft; that is an illustration of the window mismatch, **not** a complete
measurement of the actual production baseline discrepancy.
[Independent fit results](fit-results.json).

There is a smaller pressure-window mismatch: for a sub-hourly issuance, the live
lower bound `issuance - 30 days` excludes the oldest whole-hour value, generally
leaving 719 hours; the fitting window uses 720. The live selection can substitute a
later six-minute observation when the issuance-hour reading is absent. Such
fallbacks must be explicit construction choices, not described as unconditional
identity with the top-of-hour training features.

**Fix (Proposed):** reproduce the actual production mean policy as far as source
availability permits; state and quantify any unavoidable historical approximation.
Align the pressure window boundaries and define nominal UTC-hour targets versus
actual sub-hourly issuance. Refit and update the pretrial hash table after those
choices are resolved. Reproducibility of the existing fit does not establish
correctness of its target construction.

### R5 — P1: availability and pressure provenance are incomplete

`select_run` subtracts only one cycle when metadata reports an older available
run. If metadata is multiple cycles behind, the chosen run can still be newer
than the latest confirmed run. The code retains but does not check
`last_run_availability_time` against issuance. Forecast-generation time is used
as the shadow issuance although shadow inputs are fetched afterward; keep the
information cutoff and retrieval times honest.

Historical forecasts were retrieved retrospectively. A six-hour lag inferred
from one metadata observation is a declared assumption, not proof that every
historical run was available at each simulated issuance. Open-Meteo explicitly
distinguishes initialization from availability and describes typical global-model
latency, not a universal guarantee. [Single Runs documentation](https://open-meteo.com/en/docs/single-runs-api).

Both CO-OPS pressure responses are discarded after computing the current value
and anomaly. Their raw values, flags, retrieval times and eligible denominator
cannot be recovered from the shadow record. Training pressure/surge tables lack
QC columns, and their dataset hashes are not bound into the frozen manifest.
The Open-Meteo raw response archive, by contrast, is preserved and verifies.

**Fix (Proposed):** enforce a run-selection rule bounded by confirmed availability,
issuance and an explicit maximum age; otherwise fall back. Record the historical
availability limitation honestly and resolve its treatment before the trial.
Archive pressure responses/flags and all input retrievals with hashes; freeze
training-data identities and the pressure/QC eligibility rules. Retain observation
responses and QC decisions used for each evaluation report as well. The advertised
`--obs-json` option is not implemented; add an actual offline outcome-replay path.

### R6 — P1: frozen identity and baseline are not enforced in the records/scorer

All **five recorded FREEZE hashes match**, but the evaluator filters only on
`candidate_id`; two different manifest hashes under the same ID are pooled.
Records do not establish which runtime/evaluator source hashes produced them.
`baseline_surge()` reads `tau_h` from current production metadata rather than the
frozen candidate policy, so a future production change can alter the reference
while it is still called frozen v0.10.6. No version-cohort scoring catches this.

**Fix (Proposed):** bind evaluable records and reports to the reviewed manifest
and runtime/evaluator bundle; enforce that binding and define controlled treatment
of error records with missing identity. Keep a truly frozen baseline separate from
the actual production comparator. Preserve old bundles when creating a new ID;
never silently combine identities. Check invariants in CI and before trial writes.
Pre-first-record corrections can update this candidate's freeze; after collection
begins, retain the agreed new-identity/new-period rule.

### R7 — P1: a shadow failure can still block production publication

The normal production core is unchanged except for exporting a holder to the new
wrapper; independently comparing its AST confirms this. The wrapper deep-copies
the forecast and catches exceptions, and the slow-feed unit check confirms a
bounded wait. These are sound protections for forecast numbers and alerts.

However, `check_artifacts.py:728–738` adds shadow-log errors to the shared fatal
publish result. In an isolated mirror, the production artifact gate passes before
a malformed shadow line and fails afterward. A partial append after a write
failure can leave such a line even though `run()` catches the exception and
returns “not written.” The same shared gate is used by normal publication.

**Fix (Proposed):** ensure failed shadow writes/validation cannot stop otherwise
valid production publication. Validate complete records before durable writes,
retain failed evidence/health, and give shadow failures an isolated commit/gate or
quarantine path. Do not solve this by silently deleting bad evidence or ignoring
canonical production checks. Add end-to-end isolation tests that include the
publish gate, not only dictionary equality and exception handling.

### R8 — P1: local regeneration can start or contaminate the official trial

The wrapper defaults `BARNACLE_WIND_SHADOW` to enabled and runs whenever JSON was
written, including `--no-send` and `--dry-run`. A mocked-I/O execution of the actual
main flow confirms one shadow invocation for each mode with `--write-json`.
It would use the checkout's normal shadow directory unless separately disabled.
That contradicts the claim that the first record necessarily follows merge and
can admit test/replay/regeneration opportunities into the official period.
[Reproduction](dry-run-results.json).

The existing BACKLOG `wind-shadow-c1-built` entry already describes a live
`--no-send` check that produced a candidate record and quotes its 30-hour values.
No `data/wind_shadow/` directory exists in the candidate checkout at this review.
That absence does not prove no earlier record existed. Preserve and identify the
smoke-test record, its output path, timestamp and freeze vintage. Establish whether
it was excluded test output or the first evaluable trial record; if the latter,
honor the new-identity rule rather than retroactively erasing the trial start.

**Fix (Proposed):** make official collection an explicit production-job opt-in,
separate preview output, and record a trial identity/start policy. Offline tests,
manual regeneration and historical replay must not consume an official opportunity
or mutate the trial log. This is especially important because changes after the
first official record require a new identity. No official record was written by
this review.

## Verified strengths and limits

The independent rebuild matches all 48 coefficient vectors within their eight-
decimal rounding (maximum difference 4.98e-9), all fitted sample counts and rounded
MAEs, and the declared equivalence statistics. Route A is correctly selected:
12-hour correlation fails the 0.95 rule; the 30-hour correlation/slope also fail.
All 698 successful raw run hashes validate and all 42,578 extracted rows match
those responses; grid and units are consistent. The shorter spring/summer-only
training period is stated and must remain a limitation, not a claimed winter test.

The 310-test suite passes with required GRIB decoding, including the existing
reproduction/golden tests. The committed artifact gate passes. Main forecasting
formulas and display/alert functions are unchanged by the diff. Numerical fallback
rows are paired correctly when their arrays exist; target-time high/low/plug views,
issuance-time storm-start views, a 48-hour maturity rule, separate healthy-feed
views and descriptive interim labels are implemented. Those strengths do not
cover the demonstrated boundary failures above.

The NDFD probe is a bounded feasibility note and does not switch the approved
source. Its numerical coastal-mapping experiment was not independently rerun in
this review; retain that limitation. No real prospective storm record was scored,
no live collection was started, and no skill or promotion claim is made here.

## Coverage and evidence

Counts below refer to the scoped component inventory in [coverage.json](coverage.json),
not every input row or a percentage of correctness. Categories overlap. Visual
checks are not applicable: this candidate adds no public display. Detailed findings
and tests are the authority; a passing count does not certify prospective skill.

Candidate usefulness and clarity:

| Category | Observed defects | Assessment |
|---|---|---|
| Plan completeness | 3 / 3 | Production isolation, live/training agreement and complete trial evaluation each need repair. |
| Analytical clarity | 2 / 3 | In-sample fit limits are honest; exact-construction and trial-start claims require correction. |
| Visual/interaction consistency | N/A | No public display or interactive artifact changed. Not applicable: No public display or interactive artifact changed. |

Analytical correctness and robustness:

| Category | Observed defects | Assessment |
|---|---|---|
| Source authority/confidence | 1 / 2 | Forecast raw data verifies; pressure/outcome provenance and historical availability remain incomplete. |
| Calculation accuracy | 3 / 4 | Fit and route reproduce; baseline construction, episode and eligibility rules have demonstrated errors. |
| Within-chart agreement | N/A | No charts in this candidate. Not applicable: No charts in this candidate. |
| Complete source-detail surfaces | N/A | No dashboard source-detail surfaces; provenance is reviewed under source authority. Not applicable: No dashboard source-detail surfaces; provenance is reviewed under source authority. |
| Cross-artifact consistency | 4 / 4 | Approved plan, manifest/runtime baseline, and evaluator diverge. |
| Data-quality controls | 5 / 5 | Reproduced missingness, QC, frozen-identity and collection-boundary defects. |
| Conclusion support | 1 / 2 | Historical fit numbers reproduce; prospective PASS can be issued on insufficient evidence. |

## Reproduction and author handoff

Evidence scripts are read-only with respect to the candidate and write only to
explicit scratch outputs. Run against `d82a82970` in a separate checkout:

```bash
python3 audits/2026-09-24-a3/verify_isolation.py --repo /path/to/candidate --out /tmp/isolation.json
python3 audits/2026-09-24-a3/verify_dry_run.py --repo /path/to/candidate --out /tmp/dry-run.json
python3 audits/2026-09-24-a3/verify_evaluator.py --repo /path/to/candidate --out /tmp/evaluator.json
python3 audits/2026-09-24-a3/verify_fit.py --repo /path/to/candidate --out /tmp/fit.json
```

The fit script needs NumPy/pandas and the retained local training archives;
others use synthetic inputs and mocked networking. The evaluator reproduction
reduces bootstrap repetitions only in the synthetic pass case; confidence intervals
do not control its Boolean verdict. See [verification-summary.json](verification-summary.json)
for environment and scope. No full forecast/network run is required to reproduce
the defects.

Claude should reply in **02-…**, disposition R1–R8 independently, repair the
candidate and its tests, and refresh the pretrial freeze. Then Codex verifies the
repaired branch before merge/collection. The user does not need to choose another
feed or reconsider the approved shadow direction. A material proposed scope
reduction or methodological exception must remain explicit rather than being
silently accepted as a fix. Audit remains OPEN until an independent reply and
verification resolve the findings.
