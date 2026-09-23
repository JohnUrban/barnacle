# HANDOFF — Bay Ave Barnacle in two minutes

**Snapshot: 2026-09-23 09:09 EDT.** Rewrite wholesale each ship; <100 lines.
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
- **Quiet-hours exemption fixed (2026-09-23 ~09:00 EDT):** since the GMT
  migration the pre-07:00-tide exemption never fired (strptime on an
  offset stamp, swallowed). Now uses parse_station_local_time; 5 tests.

## 7-DAY OUTLOOK ARC (opened 2026-09-23; BACKLOG top loop)

- John's decisions today: alerts stay <=48 h (Phase 0 filter); the
  outlook is a NEW field + page, honest astronomy layer plus labeled
  guidance layer; widget unchanged; email link-only; confidence labels
  to be phased out for error stats (separate sweep); v0.11 queue is not
  a blocker; versioning rule for input/ladder changes to be proposed.
- GREENLIT 09:07: rain amounts = NBM (NOMADS subset) primary, WPC
  fallback, non-NOAA cross-check as click-to-reveal/column, occurrence
  first; NWPS gauge forecast in SHADOW with promotion scoring on the
  page; rule 5 change classes adopted. Phase 0 shipped: ALERT_WINDOW_HOURS
  = 48. Saturday must be readable on the site by end of day.
- Guidance reach verified 2026-09-23: NWS grid QPF 72 h; NWS grid wind /
  gust / PoP 7 d; NWPS SDHN4 hourly forecast 72 h; P-ETSS station text
  (e10/e90, hourly, 102 h) on NOMADS over HTTPS; STOFS netCDF 180 h.

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
- Alerts: real-payload/freshness contracts, per-rail retry/cap, one
  fail-closed dispatch. Local scheduler + Mac watchdog (awake hours).
- NOAA transport uses GMT; storage preserves station offsets. Legacy
  naive timestamps use fold=0.
- Widget source v7.29a (driveway rung removed) needs John to re-copy into
  Scriptable; installed v7.26a last confirmed 2026-09-14.
- v0.10.4: `driveway_central` REMOVED from the ladder (18 landmarks); the
  driveway is a documented PROXY; numerically identical to v0.10.3.
- CI: pinned linters; strict mypy on two seams; DOM gate. Replays: `history/scripts/reproduce_v0_10_{1,3}.py`.

## Residuals and operating rules

- Open: storm-path dispatch unverified in production; 24/7 external
  trigger needs owner credentials; delivery favors duplicate over missed;
  surge-tendency/expiry contract needs an independent compound event.
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
