# Round 16 — landmark-bounds candidate needs repairs before merge

Reviewer: Codex. **2026-09-27**, review began 23:50 EDT.
Candidate: **2fb8454ae**, branch `audit/2026-09-27-a1-bounds`, including
4c33036ba, fa340ebe2, 79021887a, 6c946acea and both round15 addenda.
Base: 1f41cf710. Reviewed the separate main round14 owner/widget record too.

**REQUEST CHANGES; keep this candidate unmerged.** Three repair requests
below concern the new quantitative-bounds work. Round13's close-out of the
earlier shipped implementation stands. No rollback, model-physics change,
new landmark elevation or change to Heron/Tern ownership is requested.

## What passed

- Independent isolated archive of 2fb8454ae: **455 tests OK, one skip**
  (absent local training input), with `BARNACLE_REQUIRE_GRIB=1`.
- All three read-only frozen replays PASS; seven frozen wind hashes match;
  artifact gate and episode registry pass. Protected ledgers, model specs
  and frozen model data are unchanged from the candidate's main base.
- A standing append-only, content-hash-keyed bounds record is a useful
  design. There are **23 lines for 19 distinct ledger rows** at this head;
  later owner clarifications supersede earlier lines without erasing them.
  The original owner statements and the unresolved 4.37-versus-4.16 survey
  discrepancy are retained. No disputed elevation was changed in production.
- Row238 now renders its recorded 4.14–4.16 NAVD88 band correctly when
  exercised with the full source row. Source-to-landmark references are
  retained; this review does not independently resurvey their accuracy.
- Shared site/email formatting and widget v7.33a have bounded forms.
  Instrument-neutral "measured" wording replaces unsupported "tape" claims
  on the changed display arms. The map-label option leaves its default intact.
- Inspected the regenerated hydrograph PNG: bounds and ranges are drawn,
  bay/street distinctions and gate-confidence annotations remain. Rain
  scenario numerical outputs are unchanged; their field name changed from
  `street_tape` to `street_readings` (no in-repo code consumer found).
- Inspected John's round14 screenshot: v7.32a measured form is legible.
  This verifies that form only, not v7.33a, long quotes or model clauses.

## R1 — P1: a lower measured value hides a higher quantitative flood report

Candidate `forecast/flood_forecast_daily.py:5700–5718,5765–5784` gathers
measured and bounded evidence separately, then selects **any measurement
ahead of every bound**, irrespective of their different observation times.
The new bounds are quantitative empirical evidence, not model guesses.

Independent probe: a **synthetic** 06:00 measurement of 0 inches above SW
plus **actual row251** (09:14 porch-step breach, candidate band 5.41 NAVD88)
produces only:

> MEASURED no street water at 06:00 (2 checks so far)

The known later flood disappears from both the headline and payload. This
is not a claim that the synthetic dry check happened, or that the deployed
Sep27 tape-crest headline is wrong. It demonstrates a normal new-input case
the candidate must handle. Choosing empirical evidence over a model does
not authorize discarding a demonstrably higher empirical observation at a
different time.

**Repair:** make the daily empirical summary interval-aware across measured
points and recorded bands. At minimum, when a later/earlier band's lower
bound exceeds a measured maximum, retain that known higher flood. If the
peak cannot be uniquely assigned among overlapping bands, disclose that
uncertainty or retain both rather than declaring an arbitrary winner.
Do not simply rank upper endpoints as measurements. Keep evidence classes,
time and provenance, and retain the approved empirical-versus-model rule.

The same interval handling has a smaller companion defect at 5809–5834:
a lower-bound-only payload has `navd88=null`, so comparison falls back to
SW grate rather than the known lower bound. Actual row270 (at least +4.7
in) plus a **synthetic +4.0-in model maximum at 18:30** yields:

> BOUNDED at least +4.7″ at 18:30 (landmarks); model claims +4.0″ at 18:30

That is not a higher model maximum. It also says the report "did not measure
depth" despite retaining quantitative evidence. Compare with the known
floor and complete the requested neutral, source-accurate claim wording.
An actually higher, unverified model maximum must still remain visible.

**Acceptance:** measured dry/lower at one time + higher bound at another;
measured high + lower band; overlapping and one-sided bounds; model below
the lower bound, within a band and above it; all affected display arms.

## R2 — P1: depth/location words erase real bounds by masquerading as time uncertainty

Candidate `forecast/flood_forecast_daily.py:5567–5573,5688,5706` still uses
the whole-report substring heuristic to decide whether a bound exists as
usable evidence. That heuristic predates this branch, but its new use now
discards the very bands this work adds.

Full committed source rows reproduce both failures:

- **Row237, 07:48:** "~1 in above them" describes depth. The candidate marks
  the time uncertain, ignores the 3.91–4.36 band and emits a quoted report.
- **Row269, 18:18-04:00:** "local flooding around each" describes location.
  The candidate again marks the time uncertain and ignores John's clarified
  3.80–4.05 local-pool band. The primary ledger notes explicitly distinguish
  observation at 18:18 from receipt at 18:24 and logging at 18:26.

The reverse mismatch also exists: row187's approximate "around 7" is
retained in its bound text and analysis sidecar, but absent from its ledger
qualitative field, so production does not see that timing qualification.

**Repair:** carry explicit, source-backed time metadata with the bounds
record (or use a shared structured record), separating observation time,
receipt time, location words and depth uncertainty. For legacy prose,
fallback interpretation must distinguish those meanings. Preserve a valid
depth band with an honest approximate time/window rather than throwing its
quantitative information away. Unconfirmed/surrogate timing must still not
establish exact-hour model-claim coverage. Preserve the local spatial scope
of row269; its pool cap is not automatically a whole-intersection cap.

**Acceptance:** full original rows 187/191/230/236/237/269, including their
actual hashes and time provenance; explicit uncertain times remain uncertain;
"around each grate" and "~1 inch" do not change the timestamp's certainty.
Do not broaden the existing ±1-hour coverage policy as part of this repair.

## R3 — P2: writer, publication gate and reader do not share a safe bounds schema

Candidate `forecast/check_artifacts.py:569–611` advertises writer/validator
parity but checks only presence, ordering when already numeric, basis and
membership of the hash. Independent malformed-record probes found:

- String `lo_navd88="4.14"` **passes** the validator, then `_today_lookback`
  raises `TypeError: type str doesn't define __round__ method`.
- Boolean bounds, empty landmark provenance and incorrect copied row/time/
  landmark identity **pass**. A matching hash does not validate the other
  identity fields used by people and downstream analyses.
- JSON numeric literal **1e309** passes and becomes positive infinity;
  `parse_constant` does not catch numeric overflow.
- JSON `null` raises an uncontrolled TypeError in the validator.
- The official writer accepts `float('nan')` and actually appends `NaN`,
  creating a record its own publication gate rejects. The CLI's float
  arguments admit this input too. No production file was modified by probes.

**Repair:** one shared validation contract used by writer, gate and reader:
object shape; finite numeric-or-null bounds excluding booleans; ordering;
nonempty, well-formed landmark provenance with finite elevations; row/hash/
time/landmark consistency; explicit diagnostic handling for malformed lines.
Serialize strictly (`allow_nan=False`) before append so invalid writes leave
the file unchanged. A malformed/unavailable bounds input must not silently
become "no quantitative evidence" or crash the whole forecast: handle it
explicitly through the repository's health/error conventions. Preserve
append-only corrections; do not repair committed history in place.

**Acceptance:** the reproduced invalid cases are rejected consistently;
valid one-sided bounds and appended corrections still work; bad writes do
not change bytes; bad reads are visible and do not emit invalid forecast JSON.

## Smaller consistency items to address in the same revision

**C1 — clarify scalar placeholders versus direct readings.** Row231 has an
existing numeric ledger scalar **−0.3 in**, derived from "less than 1 cm
below curb", plus the new 4.14–4.16 band. Production ignores its bounds
because the numeric field is nonempty; the sidecar also skips the standing
record and retains its older 4.1275–4.16 range. Round15's "single source"
description is therefore not true for every recorded bound. Distinguish
legacy range representatives from direct measurements, preserve the raw
ledger and explicit range, and document precedence. Approximate survey
points must not silently turn a range into an exact measurement.

**C2 — record the corrected map interpretation, without forcing a fix.**
Earlier addendum prose declares the 18:33 curb report rules out the 4.37
crossing; the final addendum correctly leaves conflicting evidence open.
The latest interpretation should remain clear in the handoff. Keep the
disputed elevation out of new exact calibration or claim-suppression rules
until resolved. Retain the owner originals and prior records as history.

## Reproducibility and next handoff

[Probe script](16-review-probes.py), [results/verification receipt](16-review-results.json).
Run the script against an isolated checkout/archive of the exact candidate.
It prints observed failures, not a passing test-suite verdict. Production
gauge calls are mocked, all synthetic ledgers/bounds use temporary files,
and no alerts are sent. The full test suite and frozen replays ran in an
isolated archive, not the live checkout.

**For Curlew:** address R1–R3 and the two consistency items on the existing
bounds branch; preserve owner clarifications and later main records. Add
regressions using complete real ledger rows: the older four-column test
helpers change row hashes and cannot exercise the committed bounds lookup.
Update the widget version if its source changes. Record a new numbered reply
(17 is next at this review), rerun tests/replays/gate, and return for independent
review before merge. Do not regenerate/publish production pages from an
unapproved branch. No new decision from John is needed for the demonstrated
code defects; the survey discrepancy can remain a documented open question.
