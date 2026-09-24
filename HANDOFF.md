# HANDOFF — Bay Ave Barnacle in two minutes

**Snapshot: 2026-09-23 16:51 EDT.** Rewrite wholesale each ship; <100 lines.
`BACKLOG.md` OPEN LOOPS is authoritative. Attic is archival.

## System

Production hyperlocal flood forecaster for 342 Bay Ave, Highlands NJ.
Sandy Hook + NWS + catchment MRMS; 18 surveyed landmarks; hourly JSON/site,
best-effort ~10-minute nowcast, town map, per-tide pages, widget, ntfy/email/SMS.
Model **v0.10.5** (`model/v0.10.5.md`, promoted 2026-09-23). Real people receive alerts. SMS is fresh imminent impact;
ntfy/email are longer-lead watches. Core alert tide horizon remains <=48 h.

## Immediate: v0.10.5 PROMOTED 2026-09-23; close-out and v0.10.6 next

v0.10.5 = class (b), inputs and policy only (spec `model/v0.10.5.md`;
v0.10.4 archived). Owner approval: BACKLOG `DECISION | v0.10.5-promotion`.
Reviews: audit `audits/2026-09-23-a1/` rounds 01-06 (Codex 01/03/05 on
Claude's work; Claude 06 on Codex's recovery: PASS, F1 moved to v0.10.6).
Rows logged 2026-09-23 before the promoting commit carry v0.10.4 while the
new policies were live; not rewritten (cutover note in the spec).
Owed: Codex close-out round verifying the promoting commit, then CLOSED.

In v0.10.5: 48-h alert window; 7-day outlook field/page with shadow
ledger; scoped health (`degraded_inputs` production-only,
`outlook_degraded_inputs`); the 30-h curve and tank use fresh observed-surge
persistence (not the worst product tide's surge); NWS product rows keep
their high tides; confidence labels retired. Interim: missing observed
surge = no curve, labeled unavailable.

v0.10.6 (owner decisions 2026-09-23, not started): surge decays from the
reading time toward the trailing-365-d mean (tau ~36 h, measured) for
fresh AND stale readings; outage ladder with age labels and a labeled
snap to the mean. Plan `history/plans/2026-09-23-surge-decay-plan.md`.
Research: conditions-driven decay from historical wind/pressure.

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
