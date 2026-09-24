# Round 03 — independent verification of Heron's repairs

Reviewer: Codex, 2026-09-24. Research candidate `9e3f833a3` (repairs
`00875267d`), isolated logging candidate `224c14dcd`. Reply reviewed:
[round 02](02-repairs-reply-heron.md). **Research: needs revision; audit OPEN.
Logging: ready for narrow integration under John's existing archive approval.**

Review complete within the six-component scope retained from round 01:
archive/fidelity, advisory evaluator, street evaluator, observation normalization,
report, and logging isolation. Reproduced the retained evidence without new
outcome downloads. Observation interpretation was checked against ledger text
and event records, not independently remeasured from original photographs.
Research code and historic evidence are unchanged by this review; it adds the
review/probes and separately authorizes the checked logging-only integration.
No model promotion, forecast/alert change, or wind-candidate change is warranted.

## Outcome

Most of the substantive repairs hold. The observation bounds and refinements
now survive scoring; the advisory correction is actually reconstructed; the
reported evidence still supports **NOT YET EVALUABLE** for both scientific
questions. However, R1's promised control/finite-input gate is incomplete.
A few small report inaccuracies also remain. These are implementation/reporting
repairs, not new owner decisions or reasons to abandon prospective collection.

| Finding | Disposition |
|---|---|
| R1 control replay admission | PARTIAL: mismatched tank, gaps, fingerprint and antecedent-rain checks work; combined-output and invalid-number gaps below remain |
| R2 advisory reconstruction/phase | Original correction/phase defects repaired; shared invalid-number hardening below is still required |
| R3 observation semantics | Repaired: bounds, windows, conflicts, methods and supersession preserved; no ledger rewrite |
| R4 at-reference thresholds | Repaired to the amended declared rule, with straddling brackets counted as unknown |
| R5 peaks, misses, causes | Material corrections accepted; R6 below fixes remaining counts and narrower prose errors |
| Other round-01 items | Shared time parser, 12-hour boundary, one-sided sign-test caveat, capture-vs-usability wording verified |

## Reproduced evidence [VERIFIED]

- All **2,688 inventory rows** and **1,848 fidelity rows** reproduce, including
  their summaries. The normalization manifest rebuilds identically: 83 entries,
  80 primary. Selected disputed rows 153, 159, 161, 164–166, 168, 173, 178,
  181 and 183 were traced to the actual ledger wording/event sources.
- All **804 advisory pairs**, skip counts and evaluation summaries reproduce
  from the saved outcome response at its original evaluation time. All belong
  to ZERO; no matured target supports a nonzero-correction skill claim.
- All **235 street pairs**, report aggregates, per-event tables and conditional
  scenario tables reproduce. Of those pairs, **224 are primary**, with 33
  APPROX-TIDE and 191 EXCLUDED; the other 11 are sensitivity-only. None is
  EXACT or NEAR. The scientific verdicts are unchanged.
- Independently recomputing diagnostic errors from saved pair facts, without
  the evaluator's score/summarize helpers: the only point-comparison event is
  July 13; decay MAE 0.2222165 ft versus persistence 0.2423286 ft. For the 23
  interval/tolerance pairs, mean distances outside bounds are 0.1653687 and
  0.1892681 ft. For 10 lower-bound pairs, decay falls short in 7 and persistence
  in 4. These are descriptive, not evidence of multi-event improvement.
- An independent check of **2,701 combined points across all 37 rain-replayable
  archived issuances** finds zero mismatches against max(bay, pluvial), at
  0.002-ft tolerance. The new R1 probes establish future-admission gaps, not
  corruption of those real records or of the live forecast.
- Research: **377 tests pass**, logging: **339 tests pass**, required GRIB
  decoder enabled; each has one expected absent local wind-training-data skip.
  Initial sandbox runs hit the gate test's temporary-file permission, then
  authorized reruns passed. Both real artifact gates are clean.
- Seven frozen wind files match the earlier verified hashes in **both**
  branches. All 15 inspected research/logging Python files parse under Python
  3.11 grammar. Historic CSV ledgers and frozen wind files are unchanged by
  the research repair diff. Prior r1 results remain retained.

Receipts: [reproduction](03-reproduction.json), [boundary probes](03-probes.json),
[logging/isolation](03-isolation.json). Runnable scripts take the candidate
worktree as their first argument; the isolation script also takes the research
worktree as its second. They write scratch receipts under `/tmp`, not candidate
outputs. The tests used `/Users/johnurban/.barnacle/venv/bin/python`.

## R1 follow-up — P1: control and numerical admission still incomplete

Locations: candidate `history/scripts/as_issued/street.py:arms/pair_class`,
`advisory.py:build_pairs` and numeric consumers.

### Combined output is not checked

The new control compares the bay and tank separately, but never verifies the
published combined `water_navd88`. Starting with the valid zero-rain fixture,
adding **5 ft only to every combined value** still gives EXACT: P = **7.102 ft**
while the replay's D = **2.101591 ft**. Bay, rain and tank were untouched.
The positive wet test fixture also fills in the pluvial field without updating
its combined field, and is admitted as EXACT. This is not a request to make K
or another counterfactual equal P: the matching published control must equal
its own combined line first.

The stated 0.0015-ft bay tolerance is enforced only inside `elif dec`.
A constant-rule v0.10.5 fixture shifted by 0.002 ft passes the older 0.0025-ft
astronomy screen and is admitted as NEAR, contrary to Amendment 2's universal
control tolerance. Use the appropriate constant/decay control for each admitted
version, then apply the declared tolerance consistently.

### Invalid numbers can pass or crash instead of being excluded

The finite check covers only published bay values, reading and mean. With
otherwise consistent inputs:
- all archived hourly rates **-1.0** are admitted as EXACT;
- all archived hourly rates **null** raise TypeError during replay, rather
  than returning a reasoned exclusion;
- NaN rates or a NaN published tank/combined line can pass as EXACT;
- setting the advisory fixture's published outlook levels to NaN still admits
  48 advisory pairs, because `abs(NaN) > tolerance` is false.

Negative rates and null are valid JSON, so this cannot be delegated solely to
strict-JSON transport validation. NaN cases are extra defensive probes; the
production archive writer rejects nonstandard JSON constants. No such NaN
record in the retained sample is claimed. The evaluator must still uphold its
own stated finite-input contract at its admission boundary.

**Fix (Proposed):** before arithmetic, validate required numbers/array shapes,
finite astronomy/reading/mean/control/forecast values, supported time inputs,
and finite nonnegative rain. Preserve legitimate absent pluvial values as dry
only under the documented contract; missing rain stays marked unavailable, including the declared first-hour NEAR
approximation; do not silently count it as known zero.
Gate matching bay, tank presence/values AND combined output. Apply finite checks
to both advisory corrections and scored outcomes, counting excluded inputs
rather than aborting the study. Ensure invalid records cannot become EXACT/NEAR
or contribute to a verdict. Repair the positive fixture's combined field and
add negative tests for these cases. Keep counterfactual arms free to differ.

A probe using a changed tau is retained as exploratory evidence, not a finding:
the study intentionally compares fixed v0.10.6/v0.10.5 arms even when checking
a different published control. Do not reinterpret that probe as an instruction
to tune the fixed counterfactual tau.

## R6 — P2: correct population labels and two historical sentences

Location: r2 report, “Study B, revised” and event-reading bullets; round-02
reply repeats the population label. Preserve historical reports with an explicit
erratum/new revision rather than silently erasing reviewed results.

1. **235 is not the primary-pair count.** It includes 11 sensitivity-only
   pairs from rows 159, 165 and 178. Report 235 total / 224 primary / 11
   sensitivity-only; primary classes are 33 APPROX-TIDE + 191 EXCLUDED.
   The point/comparison helpers correctly exclude those rows, so the fix is
   labeling/denominator transparency, not a changed scientific result.
2. “July 13 tape points were within +0.43 ft at every lead” describes a
   **lead-bin mean bias**, not a pointwise bound. One 12–24-hour point has
   +0.504433 ft error (row 117); the range is -0.211 to +0.504433 across those
   point comparisons. Label mean bias as mean bias.
3. September 13 has **two** primary 0–6-hour pairs (rows 182 and 183), both
   in the later compound round, not “the one … pair.” Its table already
   shows two threshold cells.

Keep the corrected distinction between sampled levels and established peak
bounds, and the qualification of QPF smoothing as a hypothesis. The normalization
manifest has 64 POINT entries, of which 53 are tagged tape; avoid shorthand
implying all 64 are tape measurements.

## Logging-only integration disposition

`224c14dcd` changes only the archive builder, QPF provenance capture, their tests
and archive README. Independently extracted old/new fetch functions return
identical QPF rate outputs in seven fixtures (ordinary, null, empty, malformed
time/amount, overlapping intervals, fractional duration). Failure/empty capture
semantics and schema-1 compatibility are tested; metadata cannot change rates.
NWPS missing retrieval time remains unavailable, not the generation timestamp.

**Accepted for narrow integration.** Existing owner approval is BACKLOG
`v0.10.6-items-2-and-5` (prospective replay-input collection). This is an
archive-only repair under rule 5(c), not a model bump. Integrate those four
paths with up-to-date living docs, cite this independent review, run the gate
and preserve bot/ledger changes. Do not merge the research evaluator or its
stale living-document snapshots. Collection need not wait for R1/R6.

## Prompt for Heron

> Read audit a4 round 03 against research 9e3f833a3. R2–R4 and the main R5
> corrections hold. Finish R1's matching combined-control and constant-rule
> tolerance checks; reject invalid/null/negative/non-finite required inputs
> before either evaluator computes; make failures explicit exclusions and test
> that they cannot contribute to verdicts. Fix the positive wet fixture too.
> Correct R6's primary counts, July-13 mean-versus-point statement and Sep-13
> pair count, preserving r1/r2 evidence and dating any protocol clarification
> honestly. Return round 04, a revised reproducible report and checks. Keep
> the research branch unmerged pending Codex verification. The logging-only
> patch has passed review and is handled separately on main; reuse that version
> without reapplying stale HANDOFF/BACKLOG. No model, alert, social or frozen-wind
> changes, and no new owner preference is needed.

## Coverage receipt

Counts are the same six scoped components as round 01, not a percentage of
correct code; categories overlap. New probes and retained-output reproduction
cover the repairs. Observation source review is sampled as described above.
[Coverage record](03-coverage.json), generated with the validation coverage helper.

### Artifact usefulness and quality

| Category | Observed defects | Assessment |
|---|---|---|
| Usefulness and completeness | 3 / 6 | Useful research/logging; evaluator admission and report corrections remain. |
| Clarity | 1 / 2 | Observation semantics hold; report labels and two sentences need repair. |
| Visual and interaction quality | N/A | No UI or chart changes in this candidate. |

### Analytical correctness

| Category | Observed defects | Assessment |
|---|---|---|
| Source confidence | 1 / 4 | Observation/provenance repairs hold; advisory numerical inputs need rejection. |
| Value accuracy | 3 / 6 | Saved numbers reproduce; admission gaps and report population label remain. |
| Within-chart consistency | N/A | Tables/prose only. |
| Complete-source-details behavior | N/A | No interactive source-detail surface. |
| Cross-artifact consistency | 3 / 6 | Incomplete control contract and report labels disagree with the evidence. |
| Data-quality handling | 2 / 5 | Both evaluators need numerical admission completion; other reviewed controls pass. |
| Conclusion validity | 3 / 3 | Scientific restraint holds; future admission and historical prose still need repair. |
