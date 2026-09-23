# HANDOFF — Bay Ave Barnacle in two minutes

**Snapshot: 2026-09-23 07:32 EDT.** Rewrite wholesale each ship; <100 lines.
`BACKLOG.md` OPEN LOOPS is authoritative. The attic is archival.

## System

Production flood forecaster for 342 Bay Ave, Highlands NJ. Sandy Hook +
NWS + MRMS produce depth at 18 landmarks, hourly site/JSON, best-effort
~10-minute nowcast, per-tide pages, nine-town map, widget, ntfy/email/SMS.
Model **v0.10.4** (`model/v0.10.4.md`). SMS carries imminent street impact;
ntfy/email carry longer-lead watches. Real people receive these alerts.

## LIVE EVENT: nor'easter, Coastal Flood Advisory CF.Y.0021

- Advisory 2026-09-23 16:00 EDT -> 2026-09-26 02:00 EDT (Eastern
  Monmouth), Wind Advisory NE 25-35 mph gusts 50, High Surf 6-12 ft.
- NWS Sandy Hook projections (CFW KPHI issued 2026-09-23 08:28Z; Minor
  at 6.7 ft MLLW): Wed PM 6.9 (+1.8), Thu AM 6.4, Thu PM 7.2 (+1.9),
  Fri AM 7.2 (+2.1), Fri PM 7.5 (+2.2). Worst tide Fri 19:40 EDT.
- **Parser first real event.** Every hourly run 2026-09-22 21:00Z ..
  2026-09-23 10:00Z published `nws_coastal_product` DEGRADED ("No Sandy
  Hook section") and used surge persistence (+1.48 ft), 0.3-0.6 ft
  under NWS. Cause: the alerts API `description` carries only the
  bulleted narrative; the tide table sits after the segment's `&&`,
  which the API drops. Fix: parser reads the raw KPHI CFW product
  (alert's own issuance first, newest-first, <=24 h). Block ends at
  the next gauge header (Watson Creek shares the `&&` block). Success
  path now sets `nws_status`. Fixture + 17 tests; 187 tests, gate
  clean; live no-write build_forecast sources all six tides from NWS.
- Confidence rule deliberately caps NWS-product tides at MEDIUM until
  the first real event is scored (BACKLOG collector c: NWS projections
  vs observed peaks for the 09-23 PM .. 09-25 PM tides).
- Per PLAYBOOK live-support: log John's reports immediately; verify the
  nowcast is publishing; capture radar for the event README.

## Audit and attribution state

- Audits `2026-09-14-a1`, `2026-09-18-a1`, `2026-09-20-a1` are CLOSED.
- v0.10.3 ratified by John 2026-09-18 (retrospective, labeled so);
  v0.10.4 promoted 2026-09-20 with owner DECISION + independent
  candidate review recorded first. Do not ask John to re-approve either.
- AGENTS rule 12: attribution follows actual participation; `Reviewed-by`
  only for a cited completed review; model promotions need independent
  review + owner DECISION before the commit.

## Production and evidence

- OUTAGE 2026-09-19 04:12Z -> 2026-09-20 21:10Z (42 h) FIXED b66297bbc:
  gate accepts naive or offset stamps, writer canonicalizes, real-writer
  -> real-gate test guards it. Daily archives 09-19/09-20 are missing.
  Codex owes writer/validator parity tests for every ledger writer.
- Alerts have real-payload/freshness contracts, age-bounded NOAA
  fallbacks, per-rail retry/cap accounting, one fail-closed dispatch.
- Local scheduler has stale-lock recovery, heartbeats, quiet coalescing,
  and an armed Mac watchdog (awake hours only).
- NOAA transport uses GMT; storage preserves station offsets. Legacy
  naive timestamps use fold=0.
- Widget source v7.29a (driveway rung removed) needs John to re-copy into
  Scriptable; installed v7.26a last confirmed 2026-09-14.
- v0.10.4: `driveway_central` REMOVED from the ladder (18 landmarks); the
  driveway is a documented PROXY; numerically identical to v0.10.3.
- CI: checksum-pinned actionlint/ShellCheck; strict mypy on `station_time`
  and `html_contract`; static DOM/accessibility gate on current surfaces.
- Event #9 (2026-09-13) crest was 10-13 min earlier than the fixed-lag
  hindcast; offline assessment rejects a single replacement lag, universal
  point/max forcing, standalone persistence, and tide-bias retuning.
- Reproductions: `history/scripts/reproduce_v0_10_1.py` (legacy),
  `history/scripts/reproduce_v0_10_3.py` (production).

## Residuals and operating rules

- Next real radar trigger must verify storm-path dispatch in production.
- External 24/7 triggering and secret-bearing local alert redundancy need
  owner credentials; sleeping-Mac coverage remains open.
- Exactly-once delivery needs provider idempotency; current crash policy
  favors duplicate over missed alerts.
- Model research needs a predeclared surge-tendency/expiry contract and an
  independent compound event.
- Read PLAYBOOK for flood work. Use station-time helpers; run `date` before
  relative-time prose. Preserve provenance and append-only ledgers.
- Explicit staging only. Commit -> gate -> push; rejection -> fetch/rebase
  or abort -> gate again -> retry. Ledger conflicts resolve by union.
- Protect transactional alert state during local generation. Keep model
  spec/code/log stamps and every affected display/alert arm in lockstep.

## Immediate next step

Watch the first hourly run after this ships: `input_health.nws_coastal_product`
must read `ok` with the CFW issuance stamp, `surge_source`
`nws-coastal-flood-product`. Then score the event (collector c). Codex:
writer/validator parity tests. Owner: widget v7.29a re-copy; external PAT.
