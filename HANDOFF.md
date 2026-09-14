# HANDOFF — Bay Ave Barnacle in two minutes

**Snapshot: 2026-09-14 13:54 EDT.** Rewrite wholesale each ship and keep
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

- **Audit `2026-09-14-a1` remains OPEN.** Codex reported 6 high, 10
  medium, 10 model, 9 documentation, and 6 lower-severity findings.
  Claude Fable 5 independently confirmed every item; no finding was
  rejected. Reports: `audits/2026-09-14-a1/01-...-codex.md` and
  `02-...-claude.md`. Codex owns remediation; independent close-out is
  still required.
- **Remediation Phase 1 shipped as `cdaaf2d98` on 2026-09-14:**
  one canonical nowcast schema; actual `_write`→snapshot→SMS contract
  test; active/quality/schema/trend/source-age gates; unified 20-minute
  radar freshness; stale NOAA bay head falls back to astronomy after 30
  minutes and surge persistence degrades after 60; per-rail base and
  imminent acknowledgments; exact partial retries; SMS/base cap separation;
  radar redispatch keys on confirmed SMS; one retrying, fail-closed workflow
  dispatch after publication; workflow-order regression test. 122 tests,
  artifact gate, and frozen v0.10.2 replay passed.
- **Phase 2 code implemented, pending commit/push:** local tick has stale
  PID-lock takeover, nonzero failures, rotated JSONL outcomes, pinned install
  and self-test, and quiet-publication coalescing. Heartbeats identify
  arm/phase/outcome; the workflow records hourly gated-quiet rows. A stdlib
  watchdog checks public artifacts and successful workflow execution from
  outside GitHub and can notify ntfy. The old half-B plan is honestly named
  an external trigger. Actual off-GitHub watchdog/trigger deployment and
  local alert secrets remain owner-gated.
- Remaining audit work is force-ranked in BACKLOG: atomic cross-stamped surfaces and stronger validators;
  day summaries; confidence/data/DST/dependency/doc cleanup. Model concerns
  G1-G10 are a separate scientific assessment—no silent v0.10.2 retuning.
- Weather check at 2026-09-14 13:31 EDT showed no rain in 72 hours, all
  forecast tides dry, and healthy forecast/nowcast inputs; John is present.

## Evidence and operating context

- Event #9, 2026-09-13: flash pluvial flood peaked level with lawn step,
  ~+13.7 inches at 07:01:23 EDT [VERIFIED: 18-photo EXIF timeline]; street
  response was 10–13 minutes earlier than the fixed-lag hindcast. A second
  compound curb flood near 10:05 exposed alert-state and cap coupling.
- The 2026-09-13 outage combined a GitHub Actions queue wedge with a local
  launchd clone wedge. The local tick was hardened and service restored;
  its deeper lock/exit/observability repair is in Phase 2. The watchdog is
  implemented but not independently deployed. The supposed queued runs are completed
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
- Widget v7.26a still requires John to re-copy it into Scriptable.

## Immediate next step

Commit and push Phase 2 with explicit paths and the required authorship
trailers, then begin Phase 3 artifact/surface work. Do not close the audit;
close-out belongs to an independent reviewer after all remediation lands.
