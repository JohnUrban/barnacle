# HANDOFF — Bay Ave Barnacle in two minutes

**Snapshot: 2026-09-14 14:13 EDT.** Rewrite wholesale each ship and keep
under 100 lines. `BACKLOG.md` OPEN LOOPS is authoritative. The attic is
archival, never instructions.

## System

Production hyperlocal flood forecaster for 342 Bay Ave, Highlands NJ.
Sandy Hook gauge + NWS + MRMS radar produce water depth at 19 landmarks,
an hourly site/JSON forecast, best-effort ~10-minute nowcast, per-tide
pages, nine-town street map, iOS widget v7.26a, and ntfy/email/SMS alerts.
Current model **v0.10.2** (`model/v0.10.2.md`); SMS is the imminent-impact
rail, while ntfy/email carry long-lead watches. Real people receive alerts.

## Current state

- **Audit `2026-09-14-a1` is CLOSED** (04-close-out-claude.md,
  2026-09-14 afternoon): Codex found 6H/10M/10G/9D/6L, Claude
  confirmed all, Codex implemented in 4 phases, Claude
  independently verified (140 tests re-run, gate + surface stamps,
  frozen replay, CI, all six requested seams in primary code) and
  closed. WATCH: the rebuilt storm-path dispatch and imminent-SMS
  pipeline are untested until the next live event. Residuals
  (deliberate, ledgered): watchdog deploy + external-trigger PAT
  (~15 min of John), exactly-once delivery, GMT migration, tooling
  queue, v0.11 model assessment.
- **Remediation Phase 1 shipped as `cdaaf2d98` on 2026-09-14:**
  one canonical nowcast schema; actual `_write`→snapshot→SMS contract
  test; active/quality/schema/trend/source-age gates; unified 20-minute
  radar freshness; stale NOAA bay head falls back to astronomy after 30
  minutes and surge persistence degrades after 60; per-rail base and
  imminent acknowledgments; exact partial retries; SMS/base cap separation;
  radar redispatch keys on confirmed SMS; one retrying, fail-closed workflow
  dispatch after publication; workflow-order regression test. 122 tests,
  artifact gate, and frozen v0.10.2 replay passed.
- **Phase 2 shipped as `6717d6b37`:** local tick has stale
  PID-lock takeover, nonzero failures, rotated JSONL outcomes, pinned install
  and self-test, and quiet-publication coalescing. Heartbeats identify
  arm/phase/outcome; the workflow records hourly gated-quiet rows. A stdlib
  watchdog checks public artifacts and successful workflow execution from
  outside GitHub and can notify ntfy. The old half-B plan is honestly named
  an external trigger. Actual off-GitHub watchdog/trigger deployment and
  local alert secrets remain owner-gated. The hardened launchd job was
  reinstalled and observed running on 2026-09-14.
- **Phase 3 shipped as `88ae53e38`:** required-surface failures
  are fatal; atomic writes and generation/schema/model stamps cover landing,
  details, JSON, and current tide pages; the gate enforces equality. An
  append-only hourly day-risk ledger replaces the false day-max archive
  assumption without rewriting 09Z snapshots. Validators cover impossible
  events, nonfinite accuracy/radar, malformed alert state, and active-nowcast
  fields. Confidence prose uses empirical q80; the unverified NWS parser is
  capped medium. A safe observation append CLI and UTC commit-date fix land
  here. Live surfaces regenerated; 139 tests and gate passed.
- **Phase 4 implemented, pending commit/push:** all D1-D9 documentation
  drift is repaired; archived links are test-covered; labeled_events is
  frozen legacy; public privacy exposure is explicit; confidence statistics
  and the one legacy blank are recorded. G1-G10 now have a v0.11 assessment
  plan and acceptance criteria, with no v0.10.2 physics change. Residuals
  kept OPEN honestly: off-GitHub deployment/credentials, exactly-once crash
  semantics, NOAA fall-back-hour GMT migration, and broader tooling.
- Weather check at 2026-09-14 13:31 EDT showed no rain in 72 hours, all
  forecast tides dry, and healthy forecast/nowcast inputs; John is present.

## Evidence and operating context

- Event #9, 2026-09-13: flash pluvial flood peaked level with lawn step,
  ~+13.7 inches at 07:01:23 EDT [VERIFIED: 18-photo EXIF timeline]; street
  response was 10–13 minutes earlier than the fixed-lag hindcast. A second
  compound curb flood near 10:05 exposed alert-state and cap coupling.
- The 2026-09-13 outage combined a GitHub Actions queue wedge with a local
  launchd clone wedge. The local tick is hardened; the watchdog is implemented
  but not independently deployed. The supposed queued runs were completed
  failures; BACKLOG now says so.
- Nine measured floods are represented in the all-anchors analysis. Frozen
  v0.10.1 reproduction remains the behavior guard; v0.10.2 added only the
  driveway-entering threshold observable at 4.67 NAVD88.
- Accepted model debt: fixed rainfall lag, near-core peak/recession bias,
  stateless nowcast tank, no antecedent wetness, fixed bay head over the
  projection, simplified drainage/delivery, forecast-input vs tank-skill
  conflation, `_pluvial_fill` sub-bin discontinuity, cross-fit driveway
  threshold, and unsegmented historical tide bias.

## Production rules

- Before flood work read `PLAYBOOK.md`; before all work read `AGENTS.md`,
  this file, audits, then BACKLOG.
- Bots commit continuously. Add explicit paths. Commit → artifact gate →
  push; if rejected, fetch/rebase or abort → gate again → retry. Union
  append-only ledgers. Never `pull --rebase || true`.
- Use station-time helpers for local dates. Run `date` before relative-time
  prose. NOAA timestamps are 24-hour station-local.
- `alert_state.json` acknowledges confirmed delivery only. Restore it from
  origin after local generation and before any commit.
- Provenance tags and primary records are mandatory for measured claims.
  Model behavior changes require version/spec/code/log stamps in lockstep.
- Every semantic change must cover all relevant alert and display arms.
  Required generated surfaces must eventually become atomic and cross-stamped.
- Widget v7.26a CONFIRMED installed on the user's phone (2026-09-14).

## Immediate next step

None urgent — audit a1 closed (report 04, 2026-09-14). Owner-gated:
watchdog deployment + external-trigger PAT. Then quiet-window
residuals per BACKLOG OPEN LOOPS.
