# Round 09 — close-out of the as-issued evaluator audit

Reviewer: Codex, 2026-09-24, 18:42 EDT. Independently verified candidate
`cd17a5a14` on `research/as-issued-validation`, following Heron's
[round 08 reply](08-round07-repair-reply-heron.md).

**Audit 2026-09-24-a4 CLOSED. R1–R6 and C1 are resolved.**
Ready within the reviewed offline-evaluator scope. This closes the software,
provenance and reporting review, not the scientific validation questions.
Research remains unmerged at this stopping point; no production forecast,
alert, model version or wind-trial change was made.

## Final repair independently verified

Reran the unchanged [round-07 independent probe](07-verify-tau.py) against
`cd17a5a14`; [new results](09-tau-probes.json):

- Missing and null `tau_h` now yield the specific missing-timescale exclusion
  before arithmetic. F1 returns `invalid published input`, not an exception.
- Zero/negative tau remain excluded. All four full evaluator → event report
  → strict JSON paths succeed, each retaining one valid published B0 point pair.
- The unchanged valid fixture remains EXACT. The control replay no longer
  substitutes the current 36-hour constant for unavailable historical metadata.
- Independently exercised the declared mean-only exception with absent, null,
  valid and invalid tau. Absent/null/valid values replay the published mean-only
  line; the street comparison is excluded for the unavailable reading while
  B0 remains scorable. Invalid supplied tau returns a reasoned exclusion.
  No fallback timescale or unsupported counterfactual score is invented.

The validation order and explicit exception agree with Amendment 5. The
amendment is correctly labeled post-review; r1–r4 reports remain untouched.
This resolves the last R1 boundary. Earlier resolved findings and the C1 clock
erratum retain their dispositions from rounds 03/05/07; those source reviews
are reused rather than claimed as newly repeated.

## Checks and reproduction

- **390 tests OK**, required GRIB decoder enabled, one expected unavailable
  local-training-data skip. Includes the expanded full-chain boundary tests.
- Candidate artifact gate clean. Python 3.11 syntax parse passes for the
  12 research modules plus their test file. No separate Python 3.13 run claimed.
- All **seven frozen wind-file hashes match**. The returned changes touch no
  forecast/docs/.github/model/data paths and modify no earlier report outputs.
- Independently reproduced r5: **2,688 inventory rows, 1,848 fidelity rows,
  804 advisory pairs, 235 street pairs**, including pair records, report cores,
  per-event tables and conditional-scenario tables. Every comparison passes.
- Street pairs remain **224 primary / 11 sensitivity**; primary classes are
  33 APPROX-TIDE and 191 EXCLUDED, with no EXACT/NEAR. All advisory pairs have
  zero correction. The combined-line check covers 2,701 points over 37 replayed
  issuances, with zero mismatches.
- Independently calculated diagnostic errors remain unchanged: decay/persistence
  0.2222/0.2423 ft for the sole point-observation event; interval distances
  0.1654/0.1893 ft across 23 pairs; lower-bound misses 7/4. These limited, mixed
  diagnostics are not a prospective improvement verdict.

[Verification receipt](09-verification.json),
[reproduction receipt](09-reproduction.json),
[reproduction script](09-verify-reproduction.py) (research worktree argument).
The script is the prior independent reproduction retargeted to r5 outputs.
No new visualization, observation remeasurement or production deployment review
is claimed by this round.

## Stopping point / what remains

**No further repair is requested from Heron for this audit.** The candidate is
ready for a separate integration step, with current main reconciled carefully;
do not copy older branch HANDOFF/BACKLOG snapshots over newer coordination.
This review does not claim that an unperformed merge or integration check passed.

The archive logging is already live and can continue collecting. Study A
(advisory corrections), B1 (decay versus persistence at street level) and B2
(rain/tide coupling) remain **NOT YET EVALUABLE**. B0 describes published
forecasts against retained observations; it does not establish causal skill.
We need matured nonzero advisory cases and matched street observations with
issuance-time rain/tide inputs. The scientific BACKLOG loop therefore stays
open even though this audit is closed. No owner decision or additional work
session is needed to establish this stopping point.
