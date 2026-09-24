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

## Wind research audit 2026-09-24-a2 — Claude replied; verification + feed decision owed

Codex round 01 found R1-R5 (clock join, target-hour masks, split leakage,
overstated bounds, unverified predeclaration). Claude round 02
(`audits/2026-09-24-a2/02-reply-claude.md`) confirmed all five: canonical UTC
water history re-pulled with `time_zone=gmt`; corrected r2 scripts/reports as
new files (originals kept); erratum appended to the research plan. Corrected
24-h gauge result: decay 0.289 -> forecast-wind term ~0.236 ft all hours,
0.477 -> 0.355 storm starts (exploratory; inspected periods). Past wind now
helps storms modestly but not the plug band. v0.10.6 tau reconfirmed on UTC.
Next: Codex verifies round 02; John picks the live wind feed
(`history/plans/2026-09-24-wind-term-candidate-plan.md`, predeclared
prospective shadow evaluation). No production wind term.

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
