# HANDOFF — Bay Ave Barnacle in two minutes

**Snapshot: 2026-09-24 01:10 EDT.** Rewrite wholesale each ship; <100 lines.
`BACKLOG.md` OPEN LOOPS is authoritative. Attic is archival.

## Current system and release

Production forecaster for 342 Bay Ave, Highlands NJ. Sandy Hook + NWS +
catchment MRMS; 18 landmarks; hourly site/JSON, ~10-minute nowcast, maps,
per-tide pages, widget, ntfy/email/SMS. Real people receive alerts.
Production **v0.10.5** (`model/v0.10.5.md`), promoted `4bb885e02`.
SMS = imminent impact; ntfy/email = longer-lead; alert tide horizon <=48 h.

## v0.10.6 candidate — code verified; evidence corrections owe a re-check

Branch `v0.10.6-candidate` at `1053eb436` (not merged; main runs v0.10.5).
Codex round 03 (01:08 EDT): R1-R5 RESOLVED, keep the code; HOLD only for
R6 study/spec claims. Claude round 04 (`audits/2026-09-24-a1/04-...-claude.md`)
corrected them, research/docs only: Sep 13 is a partial-input sensitivity
experiment (no forecast-miss claim); references labeled by evidence type;
Oct 30 (reconstruction) out of the aggregates. Corrected result: on five
observed rain floods the constant and decay rules TIE exactly; Oct 30's
gauge shows decay under-predicting a building surge by ~0.3 ft.
John's items 2/5 decision stands (experimental corrections kept; the
`data/replay_inputs/` archive starts at merge).

Next: Codex re-checks `1053eb436` (affected comparison + gate); John's
promotion DECISION; merge onto updated main regenerating pages there; verify
deployed stamps, both charts and the archive's first record; then CLOSED.

## v0.10.5 behavior and audit history

Core curve/tank use fresh observed-surge persistence, not worst product surge.
NWS per-tide projections remain separate. Missing reading = unavailable core
curve (owner-approved interim). Core/outlook health scopes are separate.
Seven-day guidance remains experimental and separate from core alerts.
Audit 2026-09-23-a1 closed round07; round08 records post-close chart-escaping
defect/audit miss; fixed `0b9c4404a`, deployed chart visually verified.

## Research and operational residuals

Forecast-wind research remains a separate planned version; this review has
not validated it. Source skill, compound/p90 scenarios, coverage assumptions,
lag/hysteresis and antecedent wetness remain open. CF.Y.0021: Sep23 16:00
to Sep26 02:00 EDT; consult PLAYBOOK and current inputs during the event.
Log John's primary observations immediately, with provenance intact.
Writer/validator parity, hourly failure visibility, storm dispatch, durable
delivery outbox and archive gaps remain open. External watchdog credentials
pending; local watchdog covers Mac-awake hours. Widget v7.29a re-copy owed.

Date before relative-time prose; station-time helpers only. Explicit staging;
commit -> gate -> push; rejected push -> rebase or abort -> gate again -> retry.
Ledger conflicts union. Review credit follows actual participation and scope.
