# HANDOFF — Bay Ave Barnacle in two minutes

**Snapshot: 2026-09-24 00:27 EDT.** Rewrite wholesale each ship; <100 lines.
`BACKLOG.md` OPEN LOOPS is authoritative. Attic is archival.

## Current system and release

Production forecaster for 342 Bay Ave, Highlands NJ. Sandy Hook + NWS +
catchment MRMS; 18 landmarks; hourly site/JSON, ~10-minute nowcast, maps,
per-tide pages, widget, ntfy/email/SMS. Real people receive alerts.
Production model **v0.10.5** (`model/v0.10.5.md`), promoted `4bb885e02`.
SMS = imminent impact; ntfy/email = longer-lead; alert tide horizon <=48 h.

## v0.10.6 candidate — repaired (round 02), independent verification owed

Branch `v0.10.6-candidate` at `ce2f898c8` (not merged; main runs v0.10.5).
Spec on branch `model/v0.10.6.md`: decay toward the trailing mean (tau 36 h)
from the reading's time, outage ladder, hourly P-ETSS, last-guidance decay,
labeled source boundaries, advisory markers, new golden; old replays unchanged.
Codex round 01 (HOLD, R1-R6): `audits/2026-09-24-a1/01-...-codex.md`.
Claude round 02 (all six confirmed and repaired, evidence per finding):
`audits/2026-09-24-a1/02-repairs-reply-claude.md`. 298 tests, three replays,
gate, both 7-day charts visually checked. Codex's probe now reports the
repaired behaviour for R1, R3, R4 and R5.

John's decision on items 2 and 5 (00:31 EDT): Codex's recommendations. Done
on the branch: advisory corrections kept as EXPERIMENTAL; prospective
replay-input archive `data/replay_inputs/YYYY-MM.jsonl` (raw NWPS, advisory
rows, astronomy, corrected output, QPF as issued, surge state, tank init);
bounded rain comparison `history/reports/2026-09-24-v0.10.6-rain-comparison.txt`.
Honest result: on six measured rain floods (MRMS rain) the constant rule did
slightly better (one building compound storm); history over ~13,900
rising-surge readings still favors decay. Residual deferred by John:
multi-event as-issued rain-flood skill (the archive collects its inputs).

Next: Codex verifies `ce2f898c8`; John's promotion DECISION; then merge onto
updated main with pages regenerated there (the branch's generated pages are
stale by design; a rebase conflicts only in generated pages and HANDOFF).

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
