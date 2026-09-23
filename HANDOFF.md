# HANDOFF — Bay Ave Barnacle in two minutes

**Snapshot: 2026-09-23 16:36 EDT.** Rewrite wholesale each ship; <100 lines.
`BACKLOG.md` OPEN LOOPS is authoritative. The attic is archival.

## System

Production flood forecaster for 342 Bay Ave, Highlands NJ: Sandy Hook,
NWS, MRMS; 18 surveyed landmarks; hourly site/JSON, best-effort ~10-minute
nowcast, nine-town map, per-tide pages, widget, ntfy/email/SMS.
Model **v0.10.4** (`model/v0.10.4.md`). SMS = fresh imminent street impact;
ntfy/email = longer-lead watches. Real people receive these alerts.

## Owner-requested recovery plan (proposal, not implementation)

John noticed the lifted widget/site curve. Codex's keep/repair/revert plan:
`history/plans/2026-09-23-selective-recovery-plan.md` (evidence JSON beside it).
Recommended: restore fresh observed-surge series, keep per-tide NWS projections,
scope core/outlook health, then verify all consumers. Preserve useful additions;
evaluate time-varying surge separately. No implementation DECISION given.

## Immediate: v0.10.5 HOLD; round-04 repairs shipped, independent pass owed

Audit folder: `audits/2026-09-23-a1/`. Round 01 (Codex) reviewed the
candidate; round 02 (Claude) confirmed R1-R12 and shipped repairs A/B/C;
round 03 (Codex) verified those at `bf2e601b4` and found S1-S7 (HOLD);
round 04 (Claude, ship E) repaired all seven and the 6-h-window follow-up:
`04-round03-repairs-reply-claude.md`, probe `verify_round04_claude.py`
(inverts every round-03 assertion; exit 0) and its JSON output beside it.

What changed in ship E: shadow scoring uses absolute errors per issued
forecast, paired on the same ledger row; unknown rain reaches both maps
and the chart, and null grid intervals are unknown hours; the outlook is a
rolling 168 h with partial first/last cards (8 cards); one function feeds
the email subject, text and HTML worst panel, and day_worst looks forward
from the run instant; the chart's burst band is the maps' per-point
compound value with the three scenarios named; warm-file admission checks
every consumer field and downgrades on any dropped row; nested requests
recompute their timeout and a 75-s wall clock bounds the outlook fetch
(spec and reply now say "at most 75 s", never "never").

Ship E (`017ab4a63`) was red on the 3.11 workflows (PEP 701 f-string;
one hourly run published nothing at 20:09Z); hotfix `aba853908` and
guard `tests/test_py311_syntax.py` followed, CI green at `c5a761147`.
The 20:13Z publish on the repaired code verified: series to 167.8 h,
8 cards, `u` in the map payload, one email headline, gate clean.

Next: Codex verifies this exact candidate (round 05), then John's explicit
promotion DECISION, then the atomic class-(b) bump. No round is approval.
`model/v0.10.5-candidate.md` reflects the repaired behavior.

## Live event: coastal advisory CF.Y.0021

Advisory window 2026-09-23 16:00 -> 2026-09-26 02:00 EDT.
Captured 08:28Z CFW Sandy Hook projections: Sep 23 PM 6.9, Sep 24 PM
7.2, Sep 25 AM 7.2, Sep 25 PM 7.5 ft MLLW. Score against observed peaks
as the event passes (BACKLOG collector c); parser success is not skill.
Raw KPHI CFW repair `8e8e5cfcd` fixes alerts-API table truncation and
next-gauge leakage. Read PLAYBOOK for event support; log John's reports
immediately. Quiet-hour pre-07:00 exemption uses station-time helper.

## Outlook arc and scientific residuals

Owner decisions: separate outlook field/page; core alerts <=48 h; NBM amounts
with WPC fallback; non-NOAA cross-check only; NWPS in shadow; widget unchanged;
email link-only for new seven-day content. No tidal supremacy: compare tide,
tank and burst pathways; maps open NOW and expose the forecast horizon.

Confidence JSON removal and compound scenarios shipped in repairs. Production
still stamps v0.10.4 despite shipped inputs/policy changes: document honestly
at the class-(b) bump. Keep old replay goldens unchanged; archive/spec/code/
log-doc updates are atomic. Do not retune based on this audit.

Claude recorded a rain/tide retrospective in BACKLOG (`14e942c4f`), outside
round-03 validation. Compound behavior still needs independent event evidence.
Production 30-hour series still uses the worst tide's surge as a constant;
this residual affects new day_worst headlines and remains unresolved.

## Prior audits and operations

Audits 09-14-a1, 09-18-a1, 09-20-a1 CLOSED; prior model approvals stand.
42-hour 09-19/20 publishing outage fixed; missing daily archives remain.
Writer/validator parity and hourly-failure visibility remain open.
Nowcast storm-path dispatch needs live validation; watchdog covers Mac-awake
hours; external 24/7 trigger awaits owner credentials. Delivery favors duplicate
over missed until a durable outbox exists. Moving-head/surge-tendency work
requires independent compound-event evidence. Widget v7.29a needs re-copy
(installed v7.26a per 09-14 record). Driveway is a PROXY, not a landmark.

## Operating rules

Run `date` before relative-time prose; use station-time helpers. Preserve
primary provenance, append-only ledgers, and transactional alert state.
Explicit staging only: commit -> gate -> push; rejected push -> rebase or
abort -> gate again -> retry. Ledger conflicts resolve by union.
Attribution must name actual participation and scope. No audit closeout
without independent reply; no model promotion without review + DECISION.
