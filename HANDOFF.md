# HANDOFF — Bay Ave Barnacle in two minutes

**Snapshot: 2026-09-24 01:53 EDT.** Rewrite wholesale each ship; <100 lines.
`BACKLOG.md` OPEN LOOPS is authoritative; attic is archival.

## Current release — v0.10.6 live and CLOSED

Production spec `model/v0.10.6.md`; promoted `75a9933ff` from reviewed
candidate `1053eb436`. John approved before promotion (BACKLOG DECISION
v0.10.6-promotion, `b999ea1d0`). Audit `audits/2026-09-24-a1/` CLOSED at
round06: independent reviews01/03/05 and Claude replies02/04; R1-R6 resolved.
298 tests with required GRIB decoder, all three frozen replays, gate, CI and
Pages PASS. Eighteen public artifacts match promotion bytes; landing curve
and both seven-day charts visually verified. Generation 2026-09-24T05:46:59Z.
Ledgers retain every prior byte (predictions +6, day-risk +1, outlook +14;
observations/accuracy unchanged). No manual notifications; alert state intact.
First `data/replay_inputs/2026-09.jsonl` record verified locally and on GitHub.

## What changed and accepted limitations

Surge decays toward the trailing mean with a 36-h time constant, from the
reading's time. Missing-input ladder: fresh/stale-download/stale-state/typical
offset. Seven-day outlook uses hourly P-ETSS and a labeled last-guidance
assumed tail; advisory predictions remain inspectable. Core does not spread
the worst advisory surge over every low tide. Widget consumes the updated
series without a widget-code change in this release.
John accepted experimental advisory corrections with prospective raw/output
logging, and deferral of residual multi-event as-issued rain-flood skill.
Collection has started; neither claim is scientifically validated yet.
Corrected rain study: five observed-reference events tie; Oct30 peak is a
reconstruction outside aggregates; Sep13 partial QPF is sensitivity only.
Historical low-tide surge evidence supports decay; it is not street skill.
Scoring-cohort explanation on the page is a nonblocking BACKLOG follow-up.

## Operations and residual work

Production serves 342 Bay Ave, Highlands NJ: 18 landmarks, hourly site/JSON,
~10-min radar nowcast, maps, per-tide pages, widget, ntfy/email/SMS.
SMS is imminent impact; ntfy/email longer lead; alert tide horizon <=48 h.
Seven-day guidance is experimental and separate from core alerts.
CF.Y.0021 Sep23 16:00 to Sep26 02:00 EDT: use PLAYBOOK and current inputs.
At release verification core inputs healthy; aged NBM warning outlook-only.
v0.10.5 audit also closed; chart-escaping repair `0b9c4404a` retained.
Forecast-wind research is a separate planned version, not validated here.
Source skill, compound/p90 scenarios, lag/hysteresis and antecedent wetness
remain open. Operational visibility, storm dispatch, durable outbox, archive
gaps and external-watchdog credentials remain open; local watchdog is
Mac-awake only. Existing widget v7.29a re-copy owed; no new re-copy obligation
from v0.10.6. Driveway remains a proxy, not a landmark.

Log primary observations with provenance. Date before relative-time prose;
station-time helpers only. Explicit staging; commit -> gate -> push; rejected
push -> rebase or abort -> gate again -> retry. Ledger conflicts union.
