# HANDOFF — Bay Ave Barnacle in two minutes

**Snapshot: 2026-09-23 15:35 EDT.** Rewrite wholesale each ship; <100 lines.
`BACKLOG.md` OPEN LOOPS is authoritative. The attic is archival.

## System

Production flood forecaster for 342 Bay Ave, Highlands NJ: Sandy Hook,
NWS, MRMS; 18 surveyed landmarks; hourly site/JSON, best-effort ~10-minute
nowcast, nine-town map, per-tide pages, widget, ntfy/email/SMS.
Model **v0.10.4** (`model/v0.10.4.md`). SMS = fresh imminent street impact;
ntfy/email = longer-lead watches. Real people receive these alerts.

## Immediate: v0.10.5 HOLD after independent repair verification

Audit folder: `audits/2026-09-23-a1/`.
Round 01 reviewed the original candidate and Claude's 24-hour work window.
Claude confirmed all twelve findings in round 02 and shipped repairs A/B/C.
Codex's round 03 independently reviews repaired candidate `bf2e601b4`:
`03-repaired-candidate-verification-codex.md`. Reproduction script/output
are beside it. Review complete; candidate NOT approved; audit stays OPEN.

Verified: full decoder suite **252 OK, no skips**; artifact gate and both
frozen replays PASS; repaired map-control probe PASS. Distinct-tide counting,
expiry-before-merge, rain interval/proration, map controls, CFW anchoring,
and decoder CI have concrete repairs. Remaining findings:

- S1: signed errors cancel before MAE, producing false READY; pairing differs.
- S2: unknown rain disappears from map/chart; null grid values count as dry.
- S3: declared 168 hours exceeds continuous horizon while table goes farther.
- S4: email HTML WORST panel disagrees with subject; past points leak into
  forward day_worst headlines.
- S5: compound scenario chart uses a different potential than map points.
- S6: missing bucket duration passes admission and crashes its consumer.
- S7: optional acquisition still synchronous; shared deadline is soft.

Next: Claude's numbered response and fixes, independent candidate PASS,
then John's explicit promotion DECISION. Neither earlier build green lights
nor this completed review constitute promotion approval. Candidate spec
`model/v0.10.5-candidate.md` needs to reflect the repaired behavior.

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
