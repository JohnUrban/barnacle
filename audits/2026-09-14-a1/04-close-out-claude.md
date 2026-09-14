# Close-out — audit 2026-09-14-a1

**Author:** Claude (Fable 5), round-02 independent reviewer,
verifying the round-03 implementation by Codex (the round-01
auditor). Reviewer ≠ implementer holds for every item.
**Verified at:** repo state 5aea881d9 + live ticks, 2026-09-14
~15:15 EDT.

## Verdict

**Audit 2026-09-14-a1 is CLOSED.** All four implementation phases
verify against the round-01 findings and the round-02 amendments.
No dispute was raised in round 02 and none arises here. Explicit
residuals (below) are visible in BACKLOG and are deliberate,
owner-gated or provider-gated work — not silent dismissals.

## Independent verification performed

System-level, re-run by me at HEAD:

- Full suite: **140 tests, OK** (was 111 pre-remediation).
- `forecast/check_artifacts.py`: clean — now including
  `validate_surface_stamps` (H6) wired at line 567.
- `history/scripts/reproduce_v0_10_1.py`: **PASS** — frozen
  constants, RMS, six hindcasts, cutover intact; no retuning.
- CI: success on the phase commits.
- Live production observed healthy through the remediation window:
  local ticks continuous, including the new `[skip ci]`
  gated-quiet heartbeat form (M6) in actual use at 18:06Z.

The six seams round 03 asked to be verified by hand, each checked
against primary code:

1. **Per-rail state (H2):** `base_sends_today` / `sms_sends_today`
   split exists (the round-02 cap-conflation expansion,
   implemented); persist semantics state that after a partial
   ntfy/email success only the failed rail remains pending, with
   independent event markers for imminent sms/ntfy. Migration from
   the legacy `sends_today` key is handled in place.
2. **Dispatch failure path (H3):** one consolidated dispatch step
   (`adc || rac`), positioned after the publish/commit step,
   3-attempt bounded retry, `exit 1` on exhaustion — job goes red.
   The stale watchdog step is gone rather than reordered, which is
   the cleaner fix. `tests/test_workflow_contracts.py` guards step
   order and fail-closed behavior — the regression guard round 02
   required in the same commit is present.
3. **Stale-gauge fallback (H4):** `station_observation_age_min` +
   `GAUGE_HEAD_MAX_AGE_MIN` bound the bay-head read; stale data
   falls to astronomy with the distinct source label
   `astronomical-fallback-stale-gauge`, so degradation is visible,
   not silent.
4. **Cross-surface stamps (H6):** stamp equality enforced by the
   gate before any commit/push.
5. **Scheduler failure exits (H5):** the tick script now has
   distinct nonzero exit codes per failure phase, a
   `LOCK_STALE_SECONDS=300` takeover (the crash-wedge fix), and
   structured JSONL phase/outcome logging with rotation —
   `~/.barnacle/logs/tick-status.jsonl`. The installer consumes
   pinned `nowcast-requirements.txt` with `pip check` and a
   `py_compile` self-test (L4).
6. **Residual visibility:** BACKLOG carries the watchdog
   deployment, external trigger, outbox/idempotency, GMT
   migration, tooling queue, and v0.11 assessment as open loops.

Spot-verified beyond the requested six:

- **H1, the decisive one:** the phantom `projected_peak_in` has
  **zero occurrences** in production code; a single canonical
  `NOWCAST_PEAK_PROJ_KEY = "peak_proj_in"` feeds both consumers.
  And the test that was missing now exists in exactly the right
  form: `test_actual_writer_payload_round_trips_to_gate` calls the
  real `nowcast._write` and pushes its actual JSON through
  `_nowcast_snapshot` into `evaluate_sms_gate`. The methodological
  failure that concealed H1 (hand-built dicts) is structurally
  prevented for this contract.
- **M1:** `data/day_risk_log.csv` exists with union-merge
  gitattributes; the immutable 09Z archive is untouched.
- **M7:** `utc_date=$(date -u +%Y-%m-%d)` — commit titles now
  carry the true UTC date.
- **M8:** `bin/append_observation.py` exists with test coverage;
  PLAYBOOK live guidance updated.
- **M3:** q80-based uncertainty with the calibration report at
  `history/reports/confidence-calibration-2026-09-14.md`; NWS
  parser capped at medium pending first real product.
- **D5:** HANDOFF at 99 lines, restamped — back inside its own
  contract.
- **G1–G10:** untouched in production, correctly queued in
  `history/plans/model-v0.11-assessment.md` with the
  all-nine-events, timing-and-recession acceptance criteria round
  02 asked for.

## Residuals at close (all deliberate, all ledgered)

1. Watchdog deployment off-GitHub (owner infrastructure) — code and
   tests shipped; activation is John's.
2. External trigger (renamed from "half-B") — John's ~10-minute
   PAT task; correctly relabeled as trigger, not execution,
   redundancy.
3. Exactly-once delivery — duplicate-over-miss residual stands as
   a documented trade-off pending provider idempotency or an
   external delivery service.
4. GMT transport migration — parked before the 2026 fall-back
   transition (L5's fold now explicit).
5. actionlint/shellcheck/browser/accessibility tooling, incremental
   typing (L1/L2) — engineering queue.
6. Model v0.11 assessment — weather-windowed, John-present,
   separate from all operational work, per doctrine.

## Note for the record

Round 01 found the defects, round 02 confirmed all of them
including the reviewer's own, and round 03 repaired them the same
day with the round-02 amendments incorporated — cap accounting
split, workflow guard in the same commit, watchdog built first,
registry lockstep maintained, and the frozen model untouched. The
storm-path dispatch and the imminent-SMS pipeline both now await
their first live exam under the new code; the WATCH loops remain
open until a real event exercises them.
