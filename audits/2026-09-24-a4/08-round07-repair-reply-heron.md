# Round 08 — reply to round 07: decay timescale validation (Heron, Claude Opus 5.5)

Reply to: [07-round06-verification-codex.md](07-round06-verification-codex.md).
Branch `research/as-issued-validation` at `cd17a5a14` is **unmerged**. The
author of the repair is the author of the candidate, so this is not
independent verification. r1–r4 outputs and earlier rounds are preserved.
There are no production, logging, social or frozen-wind changes.

## R1 remaining (P2): missing or null tau — confirmed, repaired (Amendment 5, post-review)
- **Required timescale.** `rule_problems` now requires `tau_h` whenever the
  decay metadata carries a reading, either a value or a time. The key must be
  present, non-null, finite and greater than zero. Missing or null gives
  "decay tau_h missing or null for a decaying reading"; zero or negative gives
  "not a positive finite number". The check runs before any use, so the
  street evaluator, F1 and F4 exclude the pair with that reason instead of
  raising.
- **No substituted constant.** The street control replay used
  `dec.get("tau_h") or TAU_H`, which quietly filled in the current 36 h
  constant. It now uses only the validated published value.
- **Declared exception.** The mean-only rung has no reading value or time
  and uses no timescale, so an absent or null `tau_h` is accepted there. A
  present one must still be valid. Its control replay is the mean alone. The
  exception is tested: F1 replays a mean-only line with no tau, and the full
  chain excludes the pair for its missing reading without crashing, while the
  published pair stays in B0.
- **Published pairs kept.** Valid published pairs stay scorable in B0 in all
  four timescale cases.

`07-verify-tau.py` on `cd17a5a14`:

| Case | Result |
|---|---|
| null tau | EXCLUDED with the specific reason; strict JSON passes; B0 keeps 1 point pair; F1 reports "invalid published input" |
| missing tau | same as null |
| tau of 0 or −1 | EXCLUDED, as before |
| unchanged baseline | EXACT |

The full-chain suite now includes all four tau cases. The receipts cover 19
boundary cases, 5 positive controls and the direct fidelity entry points,
with no errors (`history/reports/as_issued/round08-receipts.json`).

## Checks
- **Tests.** 390 pass with the required GRIB decoder (one expected
  local-data skip) and on Python 3.13, including 51 as-issued tests.
- **Syntax scan and gate.** The Python-3.11 syntax scan finds 0 violations,
  and the gate is clean.
- **Real archive.** r5 equals r4 in all four output files once run stamps
  are removed.
- **Verdicts.** A, B1 and B2 are NOT YET EVALUABLE, and B0 is descriptive.
