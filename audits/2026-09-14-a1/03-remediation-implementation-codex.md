# Remediation implementation — phases 1–4

**Author:** OpenAI Codex (5.6 Sol High), original round-01 auditor and
implementer

**Review basis:** Claude Fable 5's independent round-02 confirmation

**Implementation commits:** `cdaaf2d98` (Phase 1), `6717d6b37` (Phase 2),
`88ae53e38` (Phase 3), plus the Phase 4 commit carrying this report

**Status:** IMPLEMENTED WITH EXPLICIT RESIDUALS — independent verification
and close-out are still required

## Result

The demonstrated production correctness failures are repaired without changing
the v0.10.2 formulas or constants. Alert delivery now consumes the producer's
real schema, retries per channel, distinguishes SMS from long-lead cap state,
rejects stale gauge inputs, and fails visibly if immediate workflow dispatch
cannot start. Publication surfaces share generation/schema/model stamps and
required outputs fail closed. The local scheduler is recoverable and
observable, and a GitHub-independent watchdog is ready for owner deployment.

No audit finding is silently dismissed. Scientific model questions remain an
explicit v0.11 assessment queue, and work needing external credentials or a
provider-level idempotency contract remains open in `BACKLOG.md`.

## Finding disposition

### High severity

- **H1 — implemented.** One shared nowcast schema/key contract now feeds every
  consumer. The SMS path requires a valid schema, active and healthy radar,
  fresh source data, and the established falling-pool semantics for projected
  impact. Actual current street water remains actionable. A real
  producer-payload round-trip regression test replaces the hand-built shape
  that concealed the defect; freshness is one documented 20-minute constant.
- **H2 — implemented, with the reply's cap expansion.** Delivery
  acknowledgement is per event and per rail. Failed rails retry even when a
  sibling succeeds; radar redispatch keys on confirmed SMS delivery rather
  than observed risk. Imminent SMS sends and base ntfy/email sends have
  separate cap accounting. Tests cover partial base and imminent failures,
  no-delivery persistence, retries, and escalation.
- **H3 — implemented.** NWS and radar intent consolidate into one bounded,
  post-publication workflow dispatch. Exhausted retries fail the job. A parsed
  workflow-structure test guards step order, uniqueness, and fail-closed
  behavior.
- **H4 — implemented.** Gauge timestamp and age travel with the value.
  Bay-head use is limited to 30 minutes and surge persistence to 60 minutes;
  stale data falls back to astronomy and reports degraded health. Tests use
  stale-but-nonempty NOAA payloads.
- **H5 — code hardened; external activation remains open.** The launchd tick
  uses a PID/age-aware lock, takes over stale locks, returns nonzero for real
  failures, rotates structured JSONL outcomes, installs pinned dependencies,
  self-tests, and coalesces quiet publication. The misleading “half-B” plan is
  renamed as trigger redundancy. A stdlib watchdog can monitor public artifact
  and workflow freshness from outside GitHub and notify ntfy. Deploying that
  watchdog/trigger and provisioning local alert secrets require owner-controlled
  infrastructure and credentials; the code does not pretend otherwise.
- **H6 — implemented at the publish boundary.** Required rendering failures
  are fatal; file replacement is atomic; landing, details, forecast JSON, and
  current tide pages share generation/schema/model stamps; the artifact gate
  rejects disagreement before commit or push. Tests exercise the stamp and
  required-surface contracts.

### Medium severity

- **M1 — implemented.** The immutable 09Z archive remains the as-issued morning
  product. A new append-only hourly `day_risk_log.csv` supplies honest
  within-day maxima, with pre-cutover fallback explicitly described.
- **M2 — implemented for the demonstrated gaps.** The ship gate now validates
  event ordering/domain rules, finite accuracy and radar values, alert-state
  shape, active-nowcast completeness, unique day-risk generations, and
  cross-surface stamps. Adversarial fixtures cover the failures.
- **M3 — implemented without relabeling history.** Numeric uncertainty uses
  empirical within-label q80 rather than MAE presented as a range. The
  unverified NWS parser is capped at medium, the one legacy blank is explicitly
  grandfathered, and the non-discriminating labels are recorded in
  `history/reports/confidence-calibration-2026-09-14.md`.
- **M4 — implemented.** Canonical prediction/day-risk ledger publication is
  required rather than warn-only. Optional operational heartbeat failure marks
  degraded outcome instead of disappearing as success.
- **M5 — implemented in schema and code; off-host observation activation is
  open.** Heartbeats identify scheduler arm, phase, and outcome, including
  `gated-quiet`. The external watchdog distinguishes artifact and workflow
  freshness but must be deployed outside GitHub to provide independent proof.
- **M6 — materially mitigated.** Quiet local runs coalesce publication and
  heartbeat-only commits use `[skip ci]`, removing the prior every-tick CI
  amplification. Moving all operational state off the content branch and
  sparse checkout remain lower-priority engineering options.
- **M7 — implemented.** Commit dates derive from UTC rather than slicing the
  station-local timestamp; regression coverage includes the affected hours.
- **M8 — implemented.** A single locked, schema-checked, fsynced observation
  append command replaces write-mode/manual-CSV live guidance and is covered by
  tests.
- **M9 — lifecycle resolved, unevenness retained honestly.**
  `labeled_events.csv` is declared frozen legacy. New truth belongs in the
  append-only observation ledger plus provenance-backed event README; no weak
  historical rows were rewritten.
- **M10 — partial failure fixed; exactly-once residual explicit.** Per-rail
  acknowledgement closes ordinary sibling-success loss. A crash after provider
  acceptance but before state commit remains duplicate-over-miss; a durable
  outbox needs provider idempotency or an external delivery service.

### Model concerns

- **G1–G10 — confirmed and queued, not retuned.**
  `history/plans/model-v0.11-assessment.md` sequences lag, forcing,
  persistence, antecedent state, evolving bay head, drainage/delivery,
  sub-bin continuity, cross-fit landmark treatment, and segmented tide-bias
  work. Acceptance requires timing, recession, and false-alert comparisons
  across all nine observed floods—not peak RMSE alone—and a full model version,
  spec, stamp, frozen-replay, and surface update for any accepted change.

### Documentation and lower severity

- **D1–D9 — implemented.** Landmark count, widget version, spec pointer,
  cadence/accuracy prose, HANDOFF size/state, stale BACKLOG loops, workflow
  header, archive-relative links, and space-bearing image links are corrected.
  A link regression test and archive checklist rule prevent recurrence.
- **L1 — targeted contract breadth implemented; broad tooling remains open.**
  The producer/consumer and workflow-order seams that escaped statement
  coverage now have end-to-end tests. actionlint, shellcheck, browser and
  accessibility smoke tests remain in the engineering queue.
- **L2 — open, lower priority.** Incremental typing remains appropriate as the
  monolith is further separated; no false clean-typing claim is made.
- **L3 — implemented.** The leaking test file handle is closed.
- **L4 — implemented.** Local installation consumes the pinned nowcast
  requirements and runs an import self-test.
- **L5 — risk made explicit; GMT migration remains open.** Naive NOAA LST/LDT
  fall-back timestamps explicitly choose legacy `fold=0`. This removes implicit
  behavior but cannot recover missing offset information; GMT transport and
  storage migration is parked before the 2026 fall transition.
- **L6 — owner posture documented.** The README explicitly records that this
  public single-residence project exposes the address and timestamped evidence,
  that John accepts that exposure, and that every identifiable person other
  than John must be blurred before publication.

## Verification

- Full unit suite: **140 tests pass**.
- `python3 forecast/check_artifacts.py`: pass.
- `python3 history/scripts/reproduce_v0_10_1.py`: frozen constants, 24-point
  RMS, six hindcasts, and version cutover reproduce.
- Changed Python compiles and `git diff --check` is clean.
- The hardened local launchd job was reinstalled and observed running.
- Production `data/alert_state.json` was restored from `origin/main` after
  local generation; append-only ledger rows created by as-run generation were
  retained rather than rewritten.

## Independent-review request

This report is an implementation claim by the original auditor, not close-out.
An independent reviewer should inspect the four implementation commits, rerun
the verification, and write the next unused audit index. In particular, verify
the per-rail state transitions, workflow dispatch failure path, stale-gauge
fallback, cross-surface stamp enforcement, scheduler failure exits, and that
each residual above remains visible in `BACKLOG.md`.
