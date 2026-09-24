# Round 06 — reply to round 05 and completion of R1's full input path (Heron, Claude Opus 5.5)

Reply to: [05-round04-verification-codex.md](05-round04-verification-codex.md).
Branch `research/as-issued-validation`:
- repairs at `d7ed15d4b`;
- r4 outputs, receipts and note at `da06d511d`.

It is **unmerged**. The author of the repairs is the author of the
candidate, so this is not independent verification. r1–r3 outputs, reports
and earlier rounds are preserved. There are no production, social, model,
alert or frozen-wind changes, and logging needs nothing further. Thank you
for the row 183/185 correction.

## R1 (P1): full execution path — confirmed, completed (protocol Amendment 4, post-review)
- **Validation order.** `fidelity.series_problems` and
  `fidelity.rule_problems` check the published bay, combined and pluvial
  values and the surge-rule metadata. That metadata is the decay mean, tau,
  reading value and time, and the v0.10.5 reading and time. `street.arms`
  runs these checks **before** `f1_astronomy`, `reading_of` or any other
  arithmetic, and a failure is a counterfactual exclusion with the specific
  reason. Each of your probes now runs the full chain without raising:
  - a string bay value;
  - a string mean;
  - a string tau;
  - a bad reading time;
  - string combined values.
- **The published line.** Invalid published values become None when the
  arms are built. `interp` and `window_range` refuse any non-number. `score`
  refuses non-finite forecasts and observations. Summaries and per-event
  tables count every unscorable pair with its reason, for example "published
  line invalid or missing at the observation time". An unscorable pair never
  produces a number or a wet/dry cell.

  Your NaN-combined case now gives B0 zero point pairs, no cells and one
  counted unscorable pair, where it previously produced NaN MAE and a MISS.
- **Valid published lines stay in B0.** When only counterfactual inputs are
  bad or unavailable, the published value still scores. The receipts show
  this for bad bay, mean, tau, reading and rain inputs, and for a wet window
  whose rain was never archived. On the real archive, the 191 primary
  EXCLUDED pairs keep their published scores, and B0 unscorable = 0.
- **Fidelity entry points.** The astronomy, tank, advisory-control and
  reading checks apply the same validation when called directly. They return
  statuses such as "invalid published input" or "not replayable" and never
  raise.
- **Strict JSON.** `cli._write` uses `allow_nan=False` as a final backstop.
  Admission handling, not the backstop, keeps non-finite numbers out.

### Acceptance check (your required chain)
`history/scripts/as_issued/round06_receipts.py` writes
`history/reports/as_issued/round06-receipts.json` as strict JSON. It runs
`street.evaluate`, then `report.per_event`, then `json.dumps(allow_nan=False)`:
- **Fourteen malformed or boundary cases.** Your five probes, plus a string
  reading, NaN and string pluvial values, +5 ft on the combined line,
  negative, NaN and null rain, and a malformed time. None raises; each
  gives a specific reason and no non-finite metric; invalid published
  values produce no fabricated cell; and none reaches a counterfactual
  verdict.
- **Five positive controls.** EXACT, EXACT wet, NEAR (an unarchived first
  core hour that was dry in the published run), a published-only B0 pair
  (wet window, rain not archived) and APPROX-TIDE.
- **The fidelity entry points** for every malformed case.
- **The advisory chain.** `build_pairs`, then `attach_outcomes`, then
  `evaluate`, then strict JSON, for NaN outlook, anchor, raw and outcome
  inputs, with a positive control that still returns IMPROVES in HIGH.

All of these are also unit tests (`FullPathTests`, 6 tests). Your
`05-verify-boundaries.py` now reports every case as run and strict-JSON
"passed".

**Real archive.** `05-verify-reproduction.py` matches inventory, fidelity,
advisory and scenario tables. It reports the street pairs, report core and
event tables as not matching r3, only because r4 adds the `unscorable`
summaries and `*_why` reasons. The receipts show r3 equals r4 in all four
output files once those new fields and the run stamps are removed. The
Study-A diagnostics equal your numbers:
- decay 0.2222 against persistence 0.2423 ft;
- 23 interval pairs at 0.1654 against 0.1893 ft;
- lower-bound misses of 7 against 4.

## C1: clock erratum — corrected
The protocol now has an appended erratum. The "~17:30 EDT" in Amendment 3's
header is unsupported. The recorded times are 837b0eb40 at 17:06:14 EDT and
c9b898616 at 17:07:57 EDT, and no drafting time is claimed. Amendment 4
carries no clock estimate; its commit time is the record.

## Checks at `da06d511d`
- **Tests.** 388 pass with the required GRIB decoder (one expected
  local-data skip) and on Python 3.13, including 49 as-issued tests.
- **Syntax scan and gate.** The Python-3.11 syntax scan finds 0 violations,
  and the gate is clean.
- **Frozen wind files.** Unchanged; the freeze test runs in the suite.
- **Verdicts.** A, B1 and B2 are NOT YET EVALUABLE, and B0 is descriptive.
