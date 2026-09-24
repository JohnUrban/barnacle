# HANDOFF — Bay Ave Barnacle in two minutes

**Snapshot: 2026-09-23 16:51 EDT.** Rewrite wholesale each ship; <100 lines.
`BACKLOG.md` OPEN LOOPS is authoritative. Attic is archival.

## System

Production hyperlocal flood forecaster for 342 Bay Ave, Highlands NJ.
Sandy Hook + NWS + catchment MRMS; 18 surveyed landmarks; hourly JSON/site,
best-effort ~10-minute nowcast, town map, per-tide pages, widget, ntfy/email/SMS.
Model **v0.10.4** (`model/v0.10.4.md`). Real people receive alerts. SMS is fresh imminent impact;
ntfy/email are longer-lead watches. Core alert tide horizon remains <=48 h.

## Immediate: recovery reviewed (PASS + F1); v0.10.5 HOLD

John noticed the uniformly raised widget/site curve and authorized Codex's
selective recovery plan. Report + evidence:
`audits/2026-09-23-a1/05-round04-review-and-recovery-codex.md` and adjacent JSON.
Plan: `history/plans/2026-09-23-selective-recovery-plan.md`.

- Curve/tank now use fresh observed-surge persistence; no longer the worst
  future product tide's surge. Individual NWS high-tide projections stay intact.
- `water_series_input` records actual source/value/observation time/age/status.
  `current_surge_ft` keeps its legacy worst-tide meaning.
- Missing observed surge: no definite continuous/tank curve; visible unavailable
  status. Explicit zero remains valid for nowcast astronomy-only helper.
- `degraded_inputs` is production-only; `outlook_degraded_inputs` scopes outlook.
  Full input_health retained. Outlook/map warnings remain visible; unused
  P-ETSS no longer marks the widget's core forecast degraded. Widget unchanged.
- Maps identify persistence/outlook transition; no hidden blending introduced.
- Rule-5(c) corrective restoration; no formula/constant/landmark/golden changes.
  This does not promote the existing class-(b) work into v0.10.5.

No-send generation 20:43:29Z: +1.4752 ft observed surge (16:36 EDT, 7.5 min old)
vs retained +2.5 ft worst product surge. Curve 1.025 ft lower at 72 common points
than 20:13Z. Six official high-tide totals unchanged. Core health clear;
outlook_petss degraded. Browser chart verified; no alerts sent by verification.

## Audit state

01 Codex broad audit -> 02 Claude repairs -> 03 Codex HOLD S1-S7 ->
04 Claude ship E -> 05 Codex review + recovery implementation.
Round-04 targeted probes pass; source review supports repairs. One extra S6
issue fixed here: strictly reject/count crossed P-ETSS percentile points.
266 decoder-enabled tests OK, no skips; both frozen replays and gate PASS;
round04 probe + JS map-control probe PASS. Python-3.11 hotfix preserved.
All original ledger bytes preserved; normal generation appends retained.
First recovery CI failed a missing HANDOFF spec link (Codex omission after
local tests); link restored. Production artifact deployment was unaffected.

06 Claude (Opus 5.5) reviewed the recovery: PASS as restoration, one finding
F1 = missing observed surge now yields NO curve/tank (pre-today: tank on
astronomy, degraded). John chooses (a) keep or (b) labeled astronomy-only
curve (reviewer recommends b). Then John's promotion DECISION before the
atomic class-(b) spec/archive/code/log-doc bump.
The 20:09Z Python-3.11 failed publish stays honestly recorded.

## Live advisory / scientific limits

CF.Y.0021 advisory: September 23 16:00 -> September 26 02:00 EDT.
Read PLAYBOOK for event work and log John's observations immediately.
Latest generated official peaks: Sep23 PM 7.0, Sep24 AM 6.4 / PM 7.1,
Sep25 AM 7.0 / PM 7.9, Sep26 AM 7.9 ft MLLW. Score actual observed peaks;
parser success is not skill. Raw KPHI parser remains repaired.

Seven-day outlook stays separate, labeled and experimental: NBM/WPC amounts,
NWPS shadow, P-ETSS bands, decay assumption, compound/p90 burst scenarios.
Persistence itself is an approximation. Compare time-varying alternatives on
matched issued forecasts before replacing core. Rain/tide plug-level research
is separate; existing head-dependent drainage remains, no retune. Claude's
retrospective `14e942c4f` still needs independent scientific validation.

## Operations / standing residuals

Prior 09-14/18/20 audits closed; prior model approvals stand.
42-hour publishing outage fixed; missing archives, writer/validator parity and
hourly failure visibility remain open. Optional outlook fetch bounded at 75 s
but still precedes alerts; moving it out of that path is separate work.
Nowcast storm dispatch needs live validation; watchdog covers Mac-awake hours;
external trigger awaits credentials. Durable delivery outbox remains open.
Widget v7.29a re-copy obligation remains (v7.26a installed per 09-14 record),
but this backend curve repair needs no new source copy. Driveway stays a proxy.

Run date before relative-time prose; use station-time helpers. Preserve primary
provenance and append-only data. Explicit staging; commit -> gate -> push;
rejected push -> rebase or abort -> gate -> retry. Ledger conflicts union.
Review credit must name actual scope/participation; no model promotion without
independent review and owner DECISION.
