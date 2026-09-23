# HANDOFF — Bay Ave Barnacle in two minutes

**Snapshot: 2026-09-23 13:05 EDT.** Rewrite wholesale each ship; <100 lines.
`BACKLOG.md` OPEN LOOPS is authoritative. The attic is archival.

## System

Production flood forecaster for 342 Bay Ave, Highlands NJ: Sandy Hook,
NWS, MRMS; 18 surveyed landmarks; hourly site/JSON, best-effort ~10-minute
nowcast, nine-town map, per-tide pages, widget, ntfy/email/SMS.
Model **v0.10.4** (`model/v0.10.4.md`). SMS = fresh imminent street impact;
ntfy/email = longer-lead watches. Real people receive these alerts.

## Immediate: independent audit HOLD on v0.10.5

Codex reviewed `ece4c2314`, all 11 Claude commits in the 24-hour window
ending 2026-09-23 12:51:57 EDT, and broader production contracts.
Report: `audits/2026-09-23-a1/01-repository-and-v0.10.5-candidate-codex.md`.
Reproductions and verification record are beside it. No production fixes
or promotion in the audit commit. Claude owes round-02 reply.

- R1: optional outlook fetches can starve the 5-minute alert job; isolate.
- R2: shadow READY counts forecast rows, not independent tides.
- R3–R5: missing rain becomes zero inside the tank; horizon gaps; expired
  percentile data still drives scenarios; rain boundary accounting is wrong.
- R6–R8: map future/time/pathway semantics; landing/email still tide-first;
  CFW-first cards and NWPS-first continuous guidance need reconciliation.
- R9: default suite 238 OK / 3 skipped; full GRIB environment FAILS one
  budget test. CI skips the decoder tests. Both frozen replays + gate PASS.
- R10–R12 follow-ups: semantic gates/writer parity, mislabeled day/window
  tables, gauge-specific error-statistics wording. See full acceptance list.
- Recommendation: fix R1–R9, independently verify candidate, then John's
  promotion DECISION. This HOLD is not an owner decision or a review PASS.

## Live event: coastal advisory CF.Y.0021

Advisory window 2026-09-23 16:00 -> 2026-09-26 02:00 EDT.
Captured 08:28Z CFW Sandy Hook projections: Sep 23 PM 6.9, Sep 24 PM
7.2, Sep 25 AM 7.2, Sep 25 PM 7.5 ft MLLW. Score against observed peaks
as the event passes (BACKLOG collector c); parser success is not skill.
Raw KPHI CFW repair `8e8e5cfcd` fixes alerts-API table truncation and
next-gauge leakage. Public 16:14:10Z forecast uses the repaired source.
Read PLAYBOOK for event support; log John's reports immediately.
Quiet-hours pre-07:00 tide exemption now uses the station-time helper.

## 7-day outlook arc: shipped, repairs pending

Owner decisions recorded 2026-09-23: separate outlook field/page; core
alerts <=48 h; NBM amounts with WPC fallback; non-NOAA cross-check only;
NWPS in shadow; widget unchanged; email link-only for new 7-day content.
No tidal supremacy: compare tide, tank and burst pathways; maps open NOW.

Modules outlook_sources / outlook / outlook_page, shadow outlook_log.csv,
NBM qmd warm job/file, continuous hourly series and map sliders to +168 h,
measured error-by-lead in place of human confidence labels are on main.
The inputs/policy shipped stamped v0.10.4; document this honestly at bump.
Confidence JSON remains for ledger compatibility; final removal is open.
Class-(b) bump needs Inputs & policy spec, unchanged replay goldens, atomic
spec/archive/code/docs stamps, independent review and owner DECISION.
No v0.10.5 promotion approval is implied by the earlier build green lights.

## Prior audits and operational residuals

Audits 09-14-a1, 09-18-a1, 09-20-a1 CLOSED. v0.10.3 ratified 09-18;
v0.10.4 promoted 09-20 with review + DECISION. Do not re-ask.
42-hour 09-19/20 publishing outage fixed; missing daily archives remain.
Writer/validator parity and hourly-failure visibility remain open.
Nowcast storm-path dispatch still needs live validation. Watchdog covers
Mac-awake hours; external 24/7 trigger awaits owner credentials.
Delivery favors duplicate over missed until a durable outbox exists.
Moving-head/surge-tendency work requires an independent compound event.
Widget source v7.29a needs re-copy (installed v7.26a per 09-14 record).
Driveway is a PROXY, not a landmark; never restore it to the ladder.

## Operating rules

Run `date` before relative-time prose; use station-time helpers. Preserve
primary provenance, append-only ledgers, and transactional alert state.
Explicit staging only: commit -> gate -> push; rejected push -> rebase or
abort -> gate again -> retry. Ledger conflicts resolve by union.
Review attribution must name actual participation and scope. No audit
closeout before an independent reply; no model promotion without DECISION.
