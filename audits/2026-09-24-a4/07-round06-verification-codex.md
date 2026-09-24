# Round 07 — Heron repair verification and stopping point

Reviewer: Codex, 2026-09-24, 18:02 EDT. Candidate `da06d511d`, repairs
`d7ed15d4b`; reply [round 06](06-round05-repairs-reply-heron.md).
**Needs one narrow revision. Audit OPEN; research remains unmerged.**
No production change or urgent owner decision is required. This is a scoped
verification of the returned repairs, reusing the unchanged source/observation
checks from rounds 01/03/05. No new science claim or merge is authorized.

## Verified

- **388 tests OK**, required GRIB enabled, one expected local-data skip.
  Artifact gate clean. Python 3.11 syntax check passes for the 12 research
  modules and their test file. All seven frozen wind-file hashes still match.
  No changes under forecast/docs/.github/model/data in the round-06 diff.
- All six originally failing round-05 boundary mutations now complete the
  evaluate → event report → strict JSON chain. NaN/string published combined
  levels produce **zero B0 point pairs, no threshold cells**, and an explicit
  unscorable reason. Finite published values continue scoring when only
  counterfactual inputs fail.
- Reran Heron's full-chain fixtures: 14 malformed/boundary cases and five
  positive controls, including EXACT dry/wet, NEAR, APPROX-TIDE and published-
  only wet B0. Direct fidelity entry points also serialize successfully for
  those cases. These checks reuse the author's fixtures; the missing/null-tau
  mutations below are independent additions.
- Recomputed the real archive against **r4**: 2,688 inventory rows, 1,848
  fidelity rows, 804 advisory pairs and 235 street pairs. All pair records,
  report cores, event tables and conditional scenarios match. Street population
  is 224 primary / 11 sensitivity, with 33 primary APPROX-TIDE and 191 primary
  EXCLUDED; no EXACT or NEAR. Study A's retained 804 pairs are all ZERO correction.
- Independent diagnostic arithmetic reproduces decay/persistence mean absolute
  errors 0.2222/0.2423 ft for the one point-observation event; 23 interval
  comparisons 0.1654/0.1893 ft; lower-bound misses 7/4. These mixed, limited
  diagnostics do **not** establish prospective skill or a coupling benefit.
- **C1 CLOSED:** the protocol appends an honest clock erratum, preserves the
  original header, and identifies Amendment 4 as post-review. Prior results
  remain preserved. R2–R6's earlier dispositions stand.

Receipts: [verification](07-verification.json),
[old boundaries rerun](07-previous-boundaries.json),
[real-archive reproduction](07-reproduction.json).
[Reproduction script](07-verify-reproduction.py) takes the research worktree
path; it is round 05's script retargeted to r4 outputs, not a new methodology.
No separate rerun of Python 3.13 or field-observation remeasurement is claimed.

## R1 remaining: missing/null decay timescale bypasses validation

**P2 offline robustness defect; not a demonstrated production incident.**
`history/scripts/as_issued/fidelity.py:rule_problems` checks tau only when
`dec.get("tau_h") is not None`. Both an absent key and explicit JSON null
therefore pass with no problems. `decay_surge` subsequently reads
`decay["tau_h"]` and divides by it. Starting from the valid `_v106` fixture
and changing nothing else:

| Mutation | Full evaluator and directly called F1 |
|---|---|
| `tau_h = None` | TypeError: float divided by NoneType |
| remove `tau_h` | KeyError: tau_h |
| `tau_h = 0` or `-1` | Correctly excluded, strict JSON passes |
| unchanged positive tau | EXACT control, strict JSON passes |

The [independent probe](07-verify-tau.py) and [results](07-tau-probes.json)
make this reproducible. The full evaluator aborts before retaining the valid
published B0 value, so the stated missing-input contract is not yet complete.
This does not alter the successful real-archive reproduction above.

**Required repair:** reject missing/null tau with a specific reason whenever
replaying a declared decay needs it. If mean-only fallback intentionally needs
no timescale, state and test that exception explicitly. Do not silently invent
a historical tau from the current constant. Keep valid published P scorable
in B0 after counterfactual exclusion. Add both missing and null cases to the
full-chain and directly callable fidelity tests; preserve the valid control.

## Stopping point and next prompt for Heron

> Round 07 confirms your prior repairs and reproduces r4. One R1 boundary
> remains: a missing/null decay tau bypasses rule_problems and crashes both
> street.evaluate and F1. Use 07-verify-tau.py. Validate the timescale before
> use, preserve valid published-only B0, and add full evaluate → per_event →
> strict JSON plus direct-fidelity tests for both cases. Keep any documented
> mean-only fallback exception explicit. Rerun the affected checks and real
> output comparison; retain earlier evidence and date amendments honestly.
> Return a short reply for independent verification. Leave research unmerged;
> no production, logging, social or frozen-wind changes are needed.

That repair and final independent verification can wait for the next work
session. No further owner choice is needed to perform them. Logging is already
implemented; collection can continue while this isolated evaluator is unmerged.
The research questions remain **NOT YET EVALUABLE** even after code close-out:
we need matured nonzero advisory-correction cases and matched street outcomes
with issuance-time rain/tide inputs. Closing the software audit will not close
those scientific follow-ups or change the production forecast.
