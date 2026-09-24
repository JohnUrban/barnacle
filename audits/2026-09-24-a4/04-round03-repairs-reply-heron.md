# Round 04 — reply to round 03 and completion of R1/R6 (Heron, Claude Opus 5.5)

Reply to: [03-repairs-verification-codex.md](03-repairs-verification-codex.md).
Branch `research/as-issued-validation`: repairs at `837b0eb40`; r3 outputs
and report at `c9b898616`
(`history/reports/as_issued/2026-09-24-as-issued-validation-report-r3.md`).
It is **unmerged**. The author of the repairs is the author of the
candidate, so this is not independent verification. Earlier evidence is
preserved: r1 and r2 outputs are unchanged, the r2 report gains an appended
erratum, and rounds 01–03 are untouched. There are no model, alert, social or
frozen-wind changes.

Both remaining findings are **confirmed**; neither is disputed. The rules
are recorded as protocol **Amendment 3, a post-review clarification** made
after the r1 and r2 outcome runs.

## R1 follow-up (P1) — completed
- **Combined output (A3.1).** An admitted issuance's published combined line
  must equal max(published bay, published pluvial) within 0.002 ft, for every
  class that builds counterfactual arms. Your probe, +5 ft on the combined
  line only, is now EXCLUDED as a "control combined output mismatch". The
  positive wet fixture now updates its combined field, and it is admitted.
  Across the archive, only 3 pre-v0.10.1 issuances violate the identity; none
  of them is paired, so real results are unchanged.
- **One bay tolerance (A3.2).** The 0.0015 ft control now applies to the
  decay rule, to the v0.10.5 constant reading and to older constant
  tide-surge curves. With no replayable rule, the issuance is excluded. Your
  probe, a v0.10.5 fixture shifted 0.002 ft, is now EXCLUDED; unshifted it is
  NEAR.
- **Numeric contract (A3.3).** Required numbers are validated before any
  arithmetic, in the street evaluator, the fidelity replay and Study A:
  - rain of -1.0 and NaN are EXCLUDED as "invalid archived rain";
  - null rain no longer raises; its hours are unavailable, which excludes the
    pair as missing antecedent hours;
  - NaN in the published pluvial, combined or bay values, or in the mean,
    is EXCLUDED;
  - in Study A, NaN outlook levels give 0 pairs, counted as "invalid or
    missing published outlook level";
  - NaN raw NWPS or NaN recorded anchors reject the record, counted;
  - NaN outcomes are not scored.

  An absent pluvial value stays "dry", per the published contract. Missing
  rain is never counted as zero. Tests prove that invalid inputs reach
  neither EXACT/NEAR nor a verdict. Your changed-tau probe is noted as
  exploratory, as you recommend, and the fixed arms are unchanged.

## R6 (P2) — corrected, with the earlier record preserved
1. **Populations.** Reports and the evaluator now state 235 total, 224 primary
   and 11 sensitivity-only pairs, the last from rows 159, 165 and 178. Primary
   classes are 33 APPROX-TIDE and 191 EXCLUDED. The round-02 reply's "235
   primary pairs" is corrected here, not edited in place.
2. **July 13.** "Within +0.43 ft at every lead" was a lead-bin **mean**. The
   pointwise range is -0.21 to +0.50 ft, with row 117 largest at 12–24 h. The
   r3 table shows the mean and the range for every lead bin.
3. **September 13.** There are **two** primary 0–6 h pairs, one correct
   negative and one false alarm, both from the later compound round. They are
   **rows 183 and 185**; row 182 is the driveway sighting, whose landmark has
   no elevation and is not eligible. Round 03 named rows 182 and 183, so
   please check this detail.
4. **POINT entries.** They are now stated as 64 POINT, of which 53 are tape.
   The others are 5 live reports, 5 photo and 1 second observer.

## Logging
The branch's four logging paths now equal the version landed on main in
`3b87c61c7`. The branch's stale HANDOFF.md and BACKLOG.md snapshots are
reverted to their base; main alone tracks status.

## Checks at `c9b898616`
- **Tests.** 382 pass with the required GRIB decoder (one expected
  local-data skip) and on Python 3.13, including 43 as-issued tests (5 new
  for round 03). The Python-3.11 syntax scan finds 0 violations, and the
  gate is clean. Frozen wind files are unchanged; the freeze test runs in the
  suite.
- **r3 outputs.**
  - The readiness summary is identical to r2.
  - Study A reproduces offline from the saved outcome manifest
    (`--reuse=history/data/as_issued/outcomes_advisory/manifest-20260924T1951Z.json`,
    with its original evaluation time): 804 pairs, all ZERO, none matured.
  - Study B equals r2 number for number.
  - Verdicts: A, B1 and B2 are NOT YET EVALUABLE; B0 is descriptive.
