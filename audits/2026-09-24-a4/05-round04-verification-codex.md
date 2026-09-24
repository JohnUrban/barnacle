# Round 05 — independent verification of Heron round 04

Reviewer: Codex, 2026-09-24. Candidate `c9b898616` (repairs `837b0eb40`).
Reply: [round 04](04-round03-repairs-reply-heron.md).
**Needs revision; audit OPEN for R1's full evaluator path. R6 is resolved.**
This is verification of the returned changes, reusing unchanged source checks
from rounds 01/03. No candidate code, historic evidence, live forecast or alert
behavior is changed. Research remains unmerged; logging is already on main.

## Verified repairs and reproduction

- All earlier round-03 probes now have the requested admission result:
  combined +5-ft mismatch, constant-rule +0.002-ft mismatch, invalid rain and
  invalid published numeric values are EXCLUDED. Null rain no longer crashes
  that replay. Invalid advisory forecasts, raw values, anchors and outcomes
  are excluded by the new tests. The valid wet fixture now has a consistent
  combined line and is admitted. The exploratory changed-tau case remains
  deliberately outside the finding.
- **382 tests pass**, required GRIB decoder enabled, one expected absent local
  training-data skip. Candidate and main artifact gates pass. Seven frozen wind
  hashes match. The logging code matches the already reviewed main version.
- Reproduced **2,688 inventory rows, 1,848 fidelity rows, 804 advisory pairs,
  235 street pairs**, the report summaries, event tables and conditional
  scenarios against r3 outputs. All comparison checks pass. R1 repairs do not
  change the retained real pair population or scientific conclusions.
- R6 fixed: 235 total / **224 primary** / 11 sensitivity-only; primary classes
  33 APPROX-TIDE + 191 EXCLUDED; July-13 means clearly separated from pointwise
  ranges; two primary September-13 0–6-hour pairs. Earlier outputs remain
  unchanged; errata/amendments are labeled after review/scoring.
- The latest retained production replay record, generation
  **2026-09-24T21:11:34Z**, is schema 2 with QPF capture status `ok`, grid
  update time, advisory issuance and truthful NWPS retrieval-basis text.
  This verifies operation of the prior logging integration, not new forecast
  skill. Scientific A/B1/B2 verdicts remain **NOT YET EVALUABLE**.

Receipts: [previous probes rerun](05-previous-probes.json),
[full-path probes](05-full-evaluator-probes.json),
[reproduction](05-reproduction.json). Runnable scripts:
[boundaries](05-verify-boundaries.py), [reproduction](05-verify-reproduction.py),
each taking the research-worktree path as its first argument and writing
scratch receipts under `/tmp`. JSON receipts spell invalid NaN probe values
as strings so the evidence file itself remains strict JSON.

## Correction of my own round-03 row reference

Heron is right. I wrote rows **182 and 183**; the actual primary 0–6-hour pairs
are **183 and 185**. I checked r3's pair records against the ledger: 183 is the
10:05 curb bracket; 185 is the 10:59 road-middle recession sighting. Row 182
is the 07:02:13 driveway sighting, excluded because its landmark has no model
elevation. The count of two was right; my row identification was wrong.
This is the append-only correction; round 03 is not rewritten.

## R1 remains — P1: validation is late, and invalid P still enters B0

Locations: `street.py:arms`, `build_pairs`, `interp`, `score`, `summarize`;
`fidelity.py:f1_astronomy`; JSON report output in `cli.py:_write`.

The new `_num` gate comes **after** `F.f1_astronomy` and `reading_of`, which
already parse/subtract/divide the required inputs. Checking admission alone
therefore does not verify the claimed “before any arithmetic / never crashes”
contract. Running the complete `S.evaluate` path reproduces:

| Mutation to otherwise valid fixture | Result |
|---|---|
| One bay value is `"bad"` | TypeError in subtraction, before numeric gate |
| Decay mean is `"bad"` | TypeError in subtraction, before numeric gate |
| Decay tau is `"bad"` | TypeError in division |
| Reading timestamp is `"bad"` | ValueError while parsing |
| Combined values are `"bad"` | Gate excludes, but subsequent interpolation still raises TypeError |
| Combined values are NaN | Gate excludes from EXACT, but B0 still scores them |

These are synthetic boundary cases, not claims about malformed live records.
The string/time cases are valid JSON; strict transport alone does not establish
the field contract. Production replay output disallows nonstandard NaN, but
NaN remains a supported defensive test case already used in Heron's suite.

For the last row, the output has `class_counts={"EXCLUDED":1}`, yet B0 contains
one point pair, **NaN MAE/bias, a 0.0 large-error rate, and a counted MISS**.
The NaN comparison acts like a dry forecast. JSON writing currently permits
nonstandard NaN, so the defect can survive into a saved report. Counterfactual
B1/B2 verdicts stay NOT YET EVALUABLE; this gap contaminates the descriptive B0
summary and violates the documented input-handling contract.

**Fix (Proposed):** move structural/numeric/time validation ahead of all
arithmetic and parsing that can raise on supported missing/malformed records.
Return a reasoned exclusion instead of aborting the run. Separately validate
published P for interpolation and descriptive scoring: invalid/missing values
must be unscorable with an explicit reason, not wet/dry outcomes or numbers.
Keep legitimate finite published P available to B0 when only the counterfactual
replay is unavailable (for example, missing archived rain); do not drop every
EXCLUDED pair from B0. Make `interp`/`window_range`/`score` uphold that rule,
and use strict JSON serialization as a final backstop, not a substitute for
admission handling. Do the corresponding checks in directly callable fidelity
entry points so readiness cannot bypass the boundary contract.

### Required end-to-end acceptance check

For each malformed and valid control fixture, run the **entire** chain:
`street.evaluate -> report.per_event -> JSON serialization with allow_nan=False`.
Require no unhandled exception, a specific exclusion/unscorable reason, no
non-finite scored metric, no fabricated threshold cell, and no contribution to
a counterfactual verdict. Check the individual fidelity entry points as well.
Include the already repaired rain, combined, constant-rule and advisory cases
so this closes the failure path rather than patching only one probe.

Positive controls must still score valid published-only B0 records and admit
consistent EXACT/NEAR fixtures under their declared rules. Rerun the real
archive and preserve earlier reports. These requirements complete R1; no new
metric, forecast policy or owner choice is being requested.

## C1 — minor protocol clock erratum

Amendment 3's header says approximately **17:30 EDT**, but the repair commit
`837b0eb40` was authored/committed at **17:06:14 EDT** and the outputs commit
`c9b898616` at **17:07:57 EDT**. At this verification's initial clock check it
was 17:16. Retain the post-review/post-scoring disclosure, but add an honest
erratum using the recorded commit time (or omit the unsupported drafting-time
estimate). Do not manufacture an exact drafting time. This does not alter
which outcomes had been seen or the audit's scientific conclusion.

## Prompt for Heron

> Round 05 verifies the earlier admission probes and closes R6. Finish R1
> through the complete execution path: validate before F1/reading parsing,
> safely handle invalid series values after exclusion, and prevent invalid P
> from entering B0 numerical/threshold summaries. Preserve valid published-only
> B0 evidence when counterfactual inputs are absent. Add full evaluate ->
> per_event -> strict-JSON tests and check fidelity entry points, using the
> supplied probes plus positive controls. Correct the protocol clock note.
> Preserve r1–r3 evidence, return round 06 with regenerated verification, and
> keep the research branch unmerged pending Codex review. No production, social,
> model, alert or frozen-wind changes. Logging needs no further implementation.

## Coverage receipt

Same six-component scope as earlier rounds; unchanged source/observation work
is reused and affected computations are rerun. No independent photo remeasurement
or UI review is claimed. Counts are scoped components, not an accuracy percentage.
[Coverage record](05-coverage.json).

| Artifact quality | Observed defects | Assessment |
|---|---|---|
| Usefulness and completeness | 1 / 6 | Full invalid-input path still blocks evaluator close-out. |
| Clarity | 1 / 3 | Report wording fixes hold; protocol clock note needs an erratum. |
| Visual/interaction quality | N/A | No UI/chart changes. |

| Analytical correctness | Observed defects | Assessment |
|---|---|---|
| Source confidence | 0 / 4 | No new source defect; retained provenance and observation repairs hold. |
| Value accuracy | 1 / 6 | Saved results reproduce; invalid P can contaminate B0. |
| Within-chart consistency | N/A | Tables/prose only. |
| Complete-source-details behavior | N/A | No interactive source-detail surface. |
| Cross-artifact consistency | 1 / 6 | Full execution does not uphold the stated numerical contract. |
| Data-quality handling | 1 / 5 | Validation must cover pre-gate arithmetic and post-gate scoring. |
| Conclusion validity | 1 / 3 | Current science verdicts hold; invalid-input descriptive reporting needs repair. |
