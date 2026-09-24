# HANDOFF — Bay Ave Barnacle in two minutes

**Snapshot: 2026-09-24 01:10 EDT.** Rewrite wholesale each ship; <100 lines.
`BACKLOG.md` OPEN LOOPS is authoritative. Attic is archival.

## Current system and release

Production forecaster for 342 Bay Ave, Highlands NJ. Sandy Hook + NWS +
catchment MRMS; 18 landmarks; hourly site/JSON, ~10-minute nowcast, maps,
per-tide pages, widget, ntfy/email/SMS. Real people receive alerts.
Production **v0.10.5** (`model/v0.10.5.md`), promoted `4bb885e02`.
SMS = imminent impact; ntfy/email = longer-lead; alert tide horizon <=48 h.

## v0.10.6 candidate — round 03 verifies repairs; narrow evidence hold

Branch `v0.10.6-candidate` at `b95b29829` (includes repairs `ce2f898c8`).
Not merged. Decay toward the trailing mean (tau 36 h), outage ladder,
hourly P-ETSS, last-guidance decay, source boundaries and advisory markers.
Audit `audits/2026-09-24-a1/`: round01 Codex findings; round02 Claude reply;
**round03 Codex independent verification**, with runnable probes/results.
298 tests with required decoder, artifact gate, all three frozen replays PASS.
Both candidate charts visually checked. R1-R5 resolved: outage parity,
assumed-source labels, formula score cohorts, mean timestamp fallback,
selected-state provenance/health. Keep these runtime repairs.

R6 remaining is specific evidence cleanup, not a new model investigation:
- Sep13 unarchived 10Z rain was filled with zero; that does not prove an
  ~8-inch forecast miss. Partial-input sensitivity only; observed-bay run
  gives 8.0 in, the other three 5.7/5.2/5.4.
- Runnable study still labels Oct30's reconstructed +20.8 in as measured.
  July6 uses +15.0 instead of canonical +15.4 (bracket 15.0-15.8); Aug7's
  crest is a backcast. Label reference types and cite primary records.
- Controlled "below 3 ft" group is defined at the burst center, not the
  whole bay trajectory; peak changes include -2.0 in, not all zero.
Claude should correct the study/spec, then Codex verifies that focused diff.

John accepted Codex's items-2/5 recommendations (BACKLOG DECISION, 00:31).
Item2: keep advisory corrections EXPERIMENTAL, collect raw/corrected inputs.
Item5: bounded comparison + prospective replay archive; only multi-event
as-issued skill deferred. Do not ask again for those decisions. Archive is
implemented on the candidate and append/gate behavior verified; first real
committed hourly archive remains to be checked after promotion.

Oct30 provenance correction on main `fd30bba7f` is append-only; +20.8 in
is not a measured peak or guaranteed lower bound. Five other events give
identical simulated peaks between rules, but absolute error depends on
their chosen reference values. Historical low-tide surge score favors decay.

After evidence corrections: John's promotion DECISION, merge onto updated
main, preserve ledgers and regenerate pages THERE; gate/replays, CI/Pages,
deployed charts/stamps, archive persistence, then audit CLOSED. Not closed yet.

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
