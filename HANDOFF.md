# HANDOFF — Bay Ave Barnacle in two minutes

**Snapshot: 2026-09-24 08:55 EDT.** Rewrite wholesale each ship; <100 lines.
`BACKLOG.md` OPEN LOOPS is authoritative; attic is archival.

## Current release — v0.10.6 live and CLOSED

Production spec `model/v0.10.6.md`; promotion `75a9933ff`, reviewed candidate
`1053eb436`, prior John DECISION `b999ea1d0`. Audit `2026-09-24-a1` CLOSED at
round06: R1-R6 resolved, 298 required-decoder tests, three replays, gate, CI,
Pages and deployed charts verified. First replay-input archive committed.
The present cleanup changes scoreboard explanation and documentation only;
forecast numbers, canonical ledgers, alert state and widget source are unchanged.
The scoreboard now explains version cohorts and identifies its outlook count.

## Live obligation — wind research audit 2026-09-24-a2 OPEN

John requested independent review, not production wind implementation.
Read `audits/2026-09-24-a2/01-wind-research-review-codex.md`; Claude owes the
finding-by-finding independent reply and corrected study. Both original reports
reproduce but contain material errors: round1 local-water/UTC-weather join,
round2 high/plug masks at issuance instead of target, cross-split training
labels, overstated forecast-age/live-gain claims and inconsistent predeclaration
timestamps. Original scripts/reports retained; plan has an erratum pointer.
Corrected independent round2: 24-h GFS MAE 0.2892->0.2369 ft overall,
0.4771->0.3549 storm starts; target low/plug improve. UTC-aligned round1 is
stronger. Keep the research; repair and validate the exact live input first.
Audit includes reproducible scripts, outputs and input hashes. Raw flags and
historical publication availability are not certified. No production wind term.
Next candidate needs matching issued forecasts, current-production comparison,
storm/low-tide/rain-tank checks, its own bump/replays/review and John DECISION.

## Accepted limitations and operations

v0.10.6 surge decays toward the trailing mean with tau36 from the reading's
own time. Missing-input ladder: fresh/stale-download/stale-state/typical offset.
Seven-day outlook uses hourly P-ETSS and a labeled assumed guidance tail;
advisory corrections remain experimental, with prospective input logging.
Core does not spread the worst advisory surge over every low tide.
Five observed-reference rain events tie; Oct30 peak reconstruction is outside
aggregates; Sep13 partial QPF is sensitivity only. As-issued rain skill and
between-high-tide advisory corrections remain accepted research limitations.
BACKLOG's scientific follow-ups now describe current behavior, not the old
48-h/constant-persistence policies or retired confidence labels.

Production serves 342 Bay Ave, Highlands NJ: 18 landmarks, hourly site/JSON,
~10-min radar nowcast, maps, per-tide pages, widget, ntfy/email/SMS.
SMS is imminent impact; ntfy/email longer lead; alert tide horizon <=48 h.
Seven-day guidance is experimental and separate from core alerts.
CF.Y.0021 Sep23 16:00 to Sep26 02:00 EDT: consult PLAYBOOK and current inputs.
Source skill, compound/p90 scenarios, lag/hysteresis and antecedent wetness
remain open. Writer/gate parity, failure visibility, durable outbox and
external-watchdog credentials remain open; local watchdog is Mac-awake only.
John plans to copy widget v7.29a (asks relative to v7.28a); not yet confirmed.
Only widget change since v7.28a: remove driveway proxy from landmark ladder.
Backend curve updates reach either widget version through forecast JSON.

Log primary observations with provenance. Date before relative-time prose;
station-time helpers only. Explicit staging; commit -> gate -> push; rejected
push -> rebase or abort -> gate again -> retry. Ledger conflicts union.
