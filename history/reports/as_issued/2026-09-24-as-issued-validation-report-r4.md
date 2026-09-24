# As-issued validation: r4 note after audit 2026-09-24-a4 round 05

Author: Heron (Claude Opus 5.5), 2026-09-24. Code d7ed15d4b (Amendment 4, a
post-review completion of the input contract, plus a clock erratum for
Amendment 3). This note does not replace the r3 narrative: the
[r3 report](2026-09-24-as-issued-validation-report-r3.md) remains the current
description of the results, because the r4 outputs equal r3 on the real
archive once the new fields are removed. The new fields are the `unscorable`
summaries and the per-pair `*_why` reasons. See
`round06-receipts.json`. r1-r3 outputs are unchanged.

What r4 adds:
- **Validation first.** The published series and surge-rule metadata are
  validated before any arithmetic.
- **Invalid published values.** An invalid or missing published value is
  unscorable, with its reason, in every arm and table. It never becomes a
  number or a wet/dry cell. The real archive has none: B0 unscorable = 0.
- **Valid published lines.** A valid published line remains scorable for B0
  when only the counterfactual inputs fail. For example, the 191 primary
  EXCLUDED pairs keep their published scores.
- **Fidelity entry points.** They return statuses instead of raising.
- **Strict JSON.** Outputs are strict JSON as a final backstop.

Receipts (`round06-receipts.json`):
- **Boundary and malformed cases.** Fourteen cases run the full chain,
  evaluate to per-event to strict JSON, without raising. Each gives a specific
  exclusion, and none reaches a verdict. The cases are: a string bay, a string
  mean, a string tau, a bad reading time, a string reading, NaN and string
  combined lines, +5 ft on the combined line, NaN and string pluvial values,
  negative, NaN and null rain, and a malformed time.
- **Positive controls.** EXACT, EXACT wet, NEAR (an unarchived dry first
  hour), a published-only B0 pair (wet window, rain not archived) and
  APPROX-TIDE all behave as declared.
- **Fidelity entry points.** No exception in any case.

Verdicts are unchanged: A, B1 and B2 are NOT YET EVALUABLE, and B0 is
descriptive.
