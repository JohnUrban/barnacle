# HANDOFF — Bay Ave Barnacle in two minutes

**Snapshot: 2026-09-18 11:51 EDT.** Rewrite wholesale each ship and keep
under 100 lines. `BACKLOG.md` OPEN LOOPS is authoritative. The attic is
archival, never instructions.

## System

Production hyperlocal flood forecaster for 342 Bay Ave, Highlands NJ.
Sandy Hook gauge + NWS + MRMS radar produce water depth at 19 landmarks,
an hourly site/JSON forecast, best-effort ~10-minute nowcast, per-tide
pages, nine-town street map, iOS widget source v7.27a, and ntfy/email/SMS
alerts.
Current model **v0.10.2** (`model/v0.10.2.md`); SMS is the imminent-impact
rail, while ntfy/email carry long-lead watches. Real people receive alerts.

## Current state

- **Audit `2026-09-14-a1` is CLOSED.** Codex reported 6 high, 10 medium,
  10 model, 9 documentation, and 6 lower-severity findings. Claude Fable 5
  confirmed every item, Codex implemented four phases, and Claude
  independently verified 140 tests, the artifact gate, surface stamps,
  frozen replay, CI, and six critical seams before closing round 04.
- Phase 1 (`cdaaf2d98`) repaired the real-payload nowcast/SMS contract,
  projection health/trend/freshness gates, stale NOAA fallbacks, per-rail
  retry and cap state, and consolidated fail-closed workflow dispatch.
- Phase 2 (`6717d6b37`) hardened the local scheduler with stale-lock
  takeover, nonzero failures, structured outcomes, pinned install/self-test,
  quiet coalescing, explicit arm heartbeats, and an independent watchdog.
- Phase 3 (`88ae53e38`) made required surfaces and ledgers fail closed,
  added atomic writes and cross-surface stamps, introduced the append-only
  day-risk log, strengthened semantic validation, corrected uncertainty
  prose, capped the unverified NWS parser, and added safe observation append.
- Phase 4 (`5aea881d9`) repaired D1–D9, froze the legacy event classifier,
  documented public privacy and confidence calibration, and queued G1–G10
  for a separate v0.11 assessment without changing v0.10.2 physics.
- The Mac watchdog was deployed and notification-armed on 2026-09-14. Its
  2026-09-15 noise repair added quiet-mode-aware limits, stable issue-class
  deduplication, cooldown, and two-tick debounce. A sleeping Mac remains a
  sleeping watchdog; an always-on host is still an open option.
- NOAA GMT migration shipped in this work unit: every CO-OPS request uses
  GMT, while stored tide and gauge stamps carry the station offset and human
  displays retain ordinary local clock labels. The repeated fall-back hour is
  distinct; legacy naive rows use fold=0. Tide caches canonicalize legacy and
  current identifiers so the cutover cannot duplicate chart points.
- Widget v7.26a was confirmed installed on John's phone on 2026-09-14.
  Source v7.27a understands offset-bearing timestamps and awaits re-copy.

## Evidence and operating context

- Event #9, 2026-09-13: flash pluvial flood peaked level with lawn step,
  ~+13.7 inches at 07:01:23 EDT [VERIFIED: 18-photo EXIF timeline]; street
  response was 10–13 minutes earlier than the fixed-lag hindcast. A second
  compound curb flood near 10:05 exposed alert-state and cap coupling.
- The rebuilt storm-path dispatch and imminent-SMS pipeline remain WATCH
  items until the next production radar trigger exercises them.
- Nine measured floods are represented in the all-anchors analysis. Frozen
  v0.10.1 reproduction remains the behavior guard; v0.10.2 added only the
  driveway-entering threshold observable at 4.67 NAVD88.
- Accepted model debt includes fixed rainfall lag, near-core
  peak/recession bias, stateless nowcast storage, no antecedent wetness,
  fixed projection bay head, simplified drainage/delivery, forecast-input
  versus tank-skill conflation, a sub-bin discontinuity, the cross-fit
  driveway threshold, and unsegmented historical tide bias.

## Open residuals

- External 24/7 trigger needs owner credentials; it protects against cron
  failure, not a wedged GitHub execution domain.
- Local alert execution redundancy remains owner/security-gated.
- Exactly-once delivery needs provider idempotency or an external outbox.
- Tooling breadth and the separately versioned v0.11 model assessment remain
  queued in `BACKLOG.md`.

## Production rules

- On flood work read `PLAYBOOK.md`; otherwise read `AGENTS.md`, this file,
  audits, then BACKLOG.
- Add explicit paths. Commit → gate → push; on rejection fetch/rebase or
  abort → gate again → retry. Union append-only ledgers.
- Use station-time helpers and run `date` before relative-time prose.
- Restore `data/alert_state.json` from origin after local generation and
  before commit. Provenance and primary records are mandatory.
- Model behavior changes require version/spec/code/log stamps in lockstep.
  Semantic changes must cover every relevant alert and display arm.

## Immediate next step

No audit close-out work remains. Next autonomous work: pinned workflow/shell
checks, then Event 9 scoring and offline v0.11 assessments.
