# HANDOFF — Bay Ave Barnacle in two minutes

**Snapshot: 2026-09-24 00:27 EDT.** Rewrite wholesale each ship; <100 lines.
`BACKLOG.md` OPEN LOOPS is authoritative. Attic is archival.

## Current system and release

Production forecaster for 342 Bay Ave, Highlands NJ. Sandy Hook + NWS +
catchment MRMS; 18 landmarks; hourly site/JSON, ~10-minute nowcast, maps,
per-tide pages, widget, ntfy/email/SMS. Real people receive alerts.
Production model **v0.10.5** (`model/v0.10.5.md`), promoted `4bb885e02`.
SMS = imminent impact; ntfy/email = longer-lead; alert tide horizon <=48 h.

## v0.10.6 candidate — independent review HOLD

Claude's branch `v0.10.6-candidate`, reviewed at `ba57f53d5` (not merged).
Spec on branch: `model/v0.10.6.md`. Decay toward recent mean (tau 36 h),
fresh/stale outage ladder, hourly P-ETSS, last-guidance decay tail, source
boundaries and advisory markers. New golden; old frozen replays unchanged.
Codex completed review against the owner-agreed seven-day checklist:
`history/plans/2026-09-23-v0.10.6-outlook-review.md`.
Report: `audits/2026-09-24-a1/01-v0.10.6-candidate-review-codex.md`.
Read-only probes + JSON results are beside it. Audit OPEN; Claude reply owed.

290 tests (required GRIB decoder), gate and all three replays PASS. Historical
surge study rerun supports basic decay. Both candidate outlook charts render
in browser. These checks do not waive the six findings:
- R1: stale/missing-guidance tide table can use astronomy while curve uses
  aged reading/typical offset; fixture discrepancy up to 1.624 ft.
- R2: lower chart marks assumed tail as NWS/P-ETSS; intro/spec stale.
- R3: shadow skill/readiness mixes different model versions.
- R4: parseable naive mean timestamp aborts whole build instead of fallback.
- R5: water_series_input top-level age/time are not from selected state;
  state admission/write health not surfaced as specified.
- R6: separate low-tide/compound comparisons incomplete; partial historical
  issuance-time rain windows DO exist (Sep13 pre-event commit 3a6c96faf).

Next: Claude repairs/replies, Codex verifies the completed candidate, John
records promotion DECISION, then merge/rebase preserving bot rows and
regenerate pages on updated main. Do not merge the stale generated pages.
No production numerical/alert/ledger changes were made in this review.

## Owner decisions still pending

Item 2: John says prospective NWPS logging sounds sensible. Codex recommends
conditional temporary retention of advisory corrections as experimental,
with raw/corrected hourly forecast logging and all-tide-phase scoring.
A captured +0.4 ft is not a universal bound or proof of negligible impact.
Item 5: recommend bounded checks using partial archived QPF and wet synthetic
scenarios, then explicit deferral of residual multi-event skill while full
issuance inputs are archived. Plug-band surge MAE is not rain-flood validation.
These are recommendations, not recorded waivers or promotion approval.

## v0.10.5 behavior and audit history

Core curve/tank use fresh observed-surge persistence, not worst product surge.
NWS per-tide projections remain separate. Missing reading = no core curve,
visibly unavailable (owner-approved interim, replacement in v0.10.6).
Core/outlook health split prevents unused outlook failures warning the widget.
Seven-day guidance remains experimental and separate from core alerts.
Audit 2026-09-23-a1 closed round07 (stamps/ledgers/replays). Round08 records
post-close chart escaping defect and audit miss; fixed `0b9c4404a`, 267 tests,
CI/Pages green and live chart visually verified. No model change for that fix.

## Research and operational residuals

Forecast-wind research remains separate planned version; candidate review
has not independently validated it. Source skill, compound/p90 rain scenarios,
grid coverage assumptions, lag/hysteresis and antecedent wetness remain open.
CF.Y.0021: Sep23 16:00 -> Sep26 02:00 EDT; consult PLAYBOOK and latest inputs.
Log John's primary observations immediately, provenance intact.
Writer/validator parity, hourly failure visibility, nowcast storm dispatch,
durable delivery outbox and missing archives remain open. External watchdog
trigger awaits credentials; local watchdog covers Mac-awake hours.
Widget v7.29a re-copy obligation remains; driveway is a proxy, not a landmark.

Date before relative-time prose; station-time helpers only. Explicit staging;
commit -> gate -> push; rejected push -> rebase or abort -> gate again -> retry.
Ledger conflicts union. Review credit follows actual participation and scope.
