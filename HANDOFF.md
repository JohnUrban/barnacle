# HANDOFF — Bay Ave Barnacle in two minutes

**Snapshot: 2026-09-23 23:33 EDT.** Rewrite wholesale each ship; <100 lines.
`BACKLOG.md` OPEN LOOPS is authoritative. Attic is archival.

## System and completed release

Production hyperlocal flood forecaster for 342 Bay Ave, Highlands NJ.
Sandy Hook + NWS + catchment MRMS; 18 surveyed landmarks; hourly JSON/site,
best-effort ~10-minute nowcast, town map, per-tide pages, widget, ntfy/email/SMS.
Model **v0.10.5** (`model/v0.10.5.md`), promoted by `4bb885e02`.
SMS is imminent impact; ntfy/email longer-lead watches. Tide alert horizon <=48 h.

**Audit 2026-09-23-a1 CLOSED**, Codex round 07:
`audits/2026-09-23-a1/07-close-out-codex.md` + adjacent verification JSON.
Codex reviewed Claude rounds 01/03/05; Claude round06 passed Codex recovery;
John approved promotion 23:22 EDT; Codex independently verified promotion.
No v0.10.5 release blocker remains. Do not confuse later research with release work.

Verified: 266 decoder-enabled tests, unchanged frozen replays, artifact gate,
archive/link/stamp consistency, append-only ledgers, promotion CI and Pages.
Public forecast/index/details/outlook matched promoting commit exactly.
Minor spec/cutover wording corrected in close-out, no production-code change.
First v0.10.5 generation: 2026-09-24T03:24:52Z (Sep23 23:24:52 EDT), one minute
before promoting commit. Earlier v0.10.4-stamped policy rows remain unchanged.

## Current behavior

The 30-h curve/tank use fresh observed-surge persistence, not the worst product
tide's surge. Product rows retain their individual high tides. water_series_input
records actual source/value/time/age; current_surge_ft keeps worst-tide meaning.
Missing observed surge = no continuous curve, visibly unavailable (INTERIM).
Codex confirms round06 F1: this outage policy was new, not purely restoration;
it is included in the class-(b) spec and accepted by the owner for v0.10.5.

Seven-day outlook is separate and experimental. Core degraded_inputs excludes
unused outlook failures; outlook_degraded_inputs scopes those, full input_health
retained. Outlook/map warnings remain visible. Widget source unchanged; no new
copy needed for curve repair. Existing v7.29a re-copy obligation remains.

## Next: v0.10.6 and research

Owner decisions 2026-09-23: fresh AND stale surge decay toward trailing-365-d
mean, candidate tau ~36 h, observation-age labels, outage ladder, labeled snap
to the typical offset. NOT implemented by v0.10.5. Plan:
`history/plans/2026-09-23-surge-decay-plan.md`.
New formula/goldens and independent review + promotion DECISION required.
Conditions-driven decay research is separate; do not treat its scientific
claims as independently verified by the v0.10.5 close-out.

Compound/p90 rain scenarios, NWPS/P-ETSS skill, source transition differences,
persistence and absent-grid-interval assumptions remain tracked validation work.
No rain/tide retune or new surge formula was smuggled into this promotion.

## Live advisory and operations

CF.Y.0021 advisory: September 23 16:00 -> September 26 02:00 EDT.
Read PLAYBOOK for event work; immediately log John's primary observations.
Use latest forecast/product for current projections; score against observed peaks.
Parser success is not skill. Driveway remains a proxy, not a landmark.

Prior 09-14/18/20 audits closed; prior model approvals stand.
42-hour publishing outage fixed; missing archives, writer/validator parity and
hourly failure visibility remain open. Optional outlook fetch bounded at 75 s
but still precedes alerts; moving it out of that path is separate work.
Nowcast storm dispatch needs live validation; watchdog covers Mac-awake hours;
external trigger awaits credentials. Durable delivery outbox remains open.

Run date before relative-time prose; use station-time helpers. Preserve primary
provenance and append-only data. Explicit staging; commit -> gate -> push;
rejected push -> rebase or abort -> gate -> retry. Ledger conflicts union.
Review credit follows actual scope/participation. New model promotion requires
independent review and owner DECISION; do not re-ask for completed approvals.
