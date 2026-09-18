# HANDOFF — Bay Ave Barnacle in two minutes

**Snapshot: 2026-09-18 13:37 EDT.** Rewrite wholesale each ship; <100 lines.
`BACKLOG.md` OPEN LOOPS is authoritative. The attic is archival.

## System

Production flood forecaster for 342 Bay Ave, Highlands NJ. Sandy Hook +
NWS + MRMS produce depth at 19 landmarks, hourly site/JSON, best-effort
~10-minute nowcast, per-tide pages, nine-town map, widget, ntfy/email/SMS.
Model **v0.10.3** (`model/v0.10.3.md`). SMS carries imminent street impact;
ntfy/email carry longer-lead watches. Real people receive these alerts.

## Audit and attribution state

- Audit `2026-09-14-a1` remains CLOSED.
- Audit `2026-09-18-a1` remains OPEN for Claude Fable 5.1's round-03
  verification/close-out. Codex's round-02 reply confirms the unsupported
  implementation-review trailers and missing promotion review checkpoint.
- John explicitly ratified v0.10.3 on 2026-09-18. BACKLOG records this as a
  retrospective DECISION; round 01 supplies independent technical review.
- BACKLOG names the twelve false review trailers in an append-only erratum.
  Earlier chat requested credit for Claude's audit/planning help; Codex
  incorrectly generalized that into implementation review on later commits.
- Rule 12 now requires cited evidence and scope for reviewer attribution.
  No fixed reviewer/model identity is carried across sessions. Planning
  advice is credited as planning. Model promotion requires independent
  candidate review and an owner decision recorded before the commit.
- Round 02 adds a legacy spring-forward gap regression and documents its
  pre-transition-offset interpretation; rounds the correction golden to
  0.09. Production formulas and time conversion are unchanged.
- Round 01's minor driveway-overlay visual check remains pending; it has
  not been represented as browser-verified.

## Production and evidence

- Alerts have real-payload/freshness contracts, age-bounded NOAA fallbacks,
  per-rail retry/cap accounting, and one fail-closed post-publish dispatch.
- Local scheduler has stale-lock recovery, explicit outcomes/heartbeats,
  quiet publication coalescing, and an armed Mac watchdog (awake hours).
- NOAA transport uses GMT; storage preserves station offsets, including
  both fall-back hours. Legacy naive timestamps use fold=0.
- Widget source v7.28a needs John to re-copy into Scriptable; installed
  v7.26a was last confirmed 2026-09-14.
- `driveway_central` is the 4.67-ft cross-fit corner-stage threshold;
  `driveway_road_central` is the separate 4.11-ft map-topography point.
- CI has checksum-pinned actionlint/ShellCheck; strict mypy covers
  `station_time` and `html_contract`. Static DOM/accessibility checks gate
  current HTML surfaces; full browser runtime accessibility remains open.
- v0.10.3 corrects only sub-bin stage-storage inversion: sampled correction
  <=0.090 inch, compound peaks +0.014/+0.063 inch, no peak clock changes.
  Constants, landmarks, forcing, lag, and alert policy are unchanged.
- Event #9's 07:01:23 EDT lawn-step crest on 2026-09-13 was 10–13 minutes
  earlier than the fixed-lag hindcast. Its overnight forecast warned ahead,
  but QPF put the first flood ~3.5h late; the later compound window hit.
  Event-time nowcast is unscorable because both production arms were dark.
- Offline assessment rejects a single replacement lag, universal point/max
  forcing, standalone persistence, and tide-bias retuning. Moving astronomy
  plus constant surge helps Oct 30 but not Dec 19: candidate HELD.
- Legacy reproduction: `history/scripts/reproduce_v0_10_1.py`.
  Production reproduction: `history/scripts/reproduce_v0_10_3.py`.

## Residuals and operating rules

- Next real radar trigger must verify storm-path dispatch in production.
- External 24/7 triggering and secret-bearing local alert redundancy need
  owner credentials/security choices; sleeping-Mac coverage remains open.
- Exactly-once delivery requires provider idempotency or a durable service;
  current crash policy favors duplicate over missed alerts.
- Model research needs a predeclared surge-tendency/expiry contract and an
  independent compound event. Event 9 round-2 radar was not archived.
- Field map clicks, browser-runtime tests, and typing beyond the two seams
  remain queued; see BACKLOG for the full list.
- Read PLAYBOOK for flood work. Use station-time helpers; run `date` before
  relative-time prose. Preserve provenance and append-only ledgers.
- Explicit staging only. Commit → gate → push; rejection → fetch/rebase
  or abort → gate again → retry. Ledger conflicts resolve by union.
- Protect transactional alert state during local generation. Keep model
  spec/code/log stamps and every affected display/alert arm in lockstep.

## Immediate next step

Claude Fable 5.1 verifies round 02 and records round-03 disposition.
Owner ratification is supplied; do not ask John to approve v0.10.3 again.
