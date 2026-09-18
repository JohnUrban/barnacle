# HANDOFF — Bay Ave Barnacle in two minutes

**Snapshot: 2026-09-18 12:18 EDT.** Rewrite wholesale each ship and keep
under 100 lines. `BACKLOG.md` OPEN LOOPS is authoritative. The attic is
archival, never instructions.

## System

Production hyperlocal flood forecaster for 342 Bay Ave, Highlands NJ.
Sandy Hook gauge + NWS + MRMS radar produce water depth at 19 landmarks,
an hourly site/JSON forecast, best-effort ~10-minute nowcast, per-tide
pages, nine-town street map, iOS widget source v7.28a, and ntfy/email/SMS
alerts. Current model **v0.10.2** (`model/v0.10.2.md`); SMS is the
imminent-impact rail, while ntfy/email carry long-lead watches. Real people
receive alerts.

## Current state

- Audit `2026-09-14-a1` is CLOSED. Claude Fable 5 independently confirmed
  all findings, the test/gate/frozen-replay remediation, and six critical
  seams. No unanswered audit report remains.
- Alert delivery has real-payload contracts, quality/freshness gates,
  age-bounded NOAA fallbacks, per-rail retry/cap state, and one fail-closed
  post-publish dispatch. SMS is fresh-nowcast imminent impact only.
- Local scheduling has stale-lock takeover, structured outcomes, quiet
  coalescing, explicit arm heartbeats, and an independent Mac watchdog.
  Sleeping-Mac coverage and external trigger credentials remain open.
- NOAA transport uses GMT; stored tide/gauge stamps carry station offsets.
  Repeated fall-back hours are distinct and legacy naive rows remain readable.
- Widget v7.26a was confirmed installed 2026-09-14. Source v7.28a retains
  exact offset parsing and identifies the driveway entry as cross-fit; John
  must re-copy it into Scriptable.
- The 4.67-ft `driveway_central` model/API/ledger key is explicitly a
  cross-fit corner-stage threshold. The separate 4.11-ft road-topography
  point is `driveway_road_central`; no model physics or stamp changed.
- CI checksum-pins actionlint 1.7.12 and ShellCheck 0.11.0. Required
  artifacts fail closed, writes are atomic, and ledgers are semantically
  validated.

## Evidence and model state

- Event #9, 2026-09-13, peaked level with the lawn step at ~+13.7 inches at
  07:01:23 EDT [VERIFIED: 18-photo EXIF timeline]. Response was 10–13 minutes
  earlier than the fixed-lag hindcast; a second compound curb flood followed.
- Its last overnight forecast is a qualified split-pathway hit: elevated
  pluvial risk 7h47 ahead and a near-magnitude burst proxy, but hourly QPF
  put the first flood ~3.5h late. Event-time nowcast is unscorable because
  both production arms were dark.
- The v0.11 offline assessment rejects one replacement lag, universal
  point/max forcing, standalone persistence, and tide-bias retuning. It
  advances time-varying nowcast bay head and `_pluvial_fill` continuity as
  offline candidates. Production remains v0.10.2.
- Nine measured floods are in the all-anchors analysis. Frozen v0.10.1
  reproduction remains the behavior guard; v0.10.2 added only the driveway
  threshold observable.
- Report: `history/reports/model-v0.11-assessment-2026-09-18.md`.

## Open residuals

- Observe the rebuilt storm-path dispatch at the next production radar
  trigger; local watchdog coverage is awake-hours only.
- External 24/7 triggering and local secret-bearing alert redundancy require
  owner credentials/security decisions.
- Exactly-once provider delivery needs idempotency or a durable external
  outbox; current policy deliberately favors duplicate over missed alerts.
- Browser DOM/accessibility tests, incremental typing, edge-map clicks, and
  separately versioned model-candidate development remain queued.

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

Prototype the time-varying nowcast bay-head candidate offline, compare it
with the frozen scalar-head behavior, and do not change production physics
without a separately accepted model version.
