# HANDOFF — Bay Ave Barnacle in two minutes

**Snapshot: 2026-09-23 23:55 EDT.** Rewrite wholesale each ship; <100 lines.
`BACKLOG.md` OPEN LOOPS is authoritative. Attic is archival.

## System and current release

Production forecaster for 342 Bay Ave, Highlands NJ. Sandy Hook + NWS +
catchment MRMS; 18 landmarks; hourly site/JSON, ~10-minute nowcast, maps,
per-tide pages, widget, ntfy/email/SMS. Real people receive alerts.
Model **v0.10.5** (`model/v0.10.5.md`), promoted `4bb885e02`.
SMS = imminent impact; ntfy/email = longer-lead; alert tide horizon <=48 h.

## Post-close correction: seven-day plot

John found a blank top plot after audit close-out. The generated burst label
contained an unescaped apostrophe, causing a JavaScript syntax error and stopping
the continuous-chart script. Data existed; lower chart was independent.
Fixed the JS quote; regenerated outlook.html from the existing forecast.
New test executes both rendered scripts in Node and asserts chart initialization.
No forecast, model, ledger or alert-state change. Model stays v0.10.5.
Report: `audits/2026-09-23-a1/08-post-close-chart-rendering-fix-codex.md`.
Codex explicitly acknowledges the prior audit missed browser execution.

## Release/audit record

Audit 2026-09-23-a1 closed in round07 (promotion/stamps/ledgers/replays);
round08 records the subsequent display defect and correction honestly.
Codex reviewed Claude work; Claude round06 independently passed Codex recovery.
John approved promotion 23:22 EDT. First v0.10.5 generation 03:24:52Z Sep24
(23:24:52 EDT Sep23), before commit 03:25:52Z. Earlier v0.10.4 rows unchanged.
266 tests at release, frozen replays/gate PASS, CI/Pages green. The new rendering
regression test extends that coverage; matching deployed bytes alone is not
proof that embedded JavaScript renders.

## Current behavior and next work

Production curve/tank use fresh observed-surge persistence, not worst product
surge. NWS projections retain their individual high tides. water_series_input
records source/value/time/age; current_surge_ft retains worst-tide meaning.
Missing observed surge = no continuous curve, visibly unavailable (INTERIM).
Codex confirms round06 F1 is a changed outage policy, not pure restoration;
owner accepted it in v0.10.5 while assigning replacement to v0.10.6.

Core/outlook health split keeps unused outlook failures out of widget warnings;
full input_health retained. Seven-day guidance remains experimental, separate
from core alerts. This chart fix needs no widget source copy.

v0.10.6: fresh/stale surge decay toward trailing-365-d mean, candidate tau ~36 h,
age labels, outage ladder and labeled snap. NOT in v0.10.5. Plan:
`history/plans/2026-09-23-surge-decay-plan.md`.
New formula/goldens, independent review + promotion DECISION required.
Conditions-driven decay research remains separate, not validated by release audit.
Compound/p90 scenarios, source skill, source seams and grid assumptions remain
tracked scientific validation. No rain/tide retune in this correction.

## Added v0.10.6 release scope (John, 23:55 EDT)

Fold the seven-day curve review into Claude's current v0.10.6 work. Checklist:
`history/plans/2026-09-23-v0.10.6-outlook-review.md`.
Show source boundaries; review NWS product corrections at low tides, hourly
P-ETSS use and the transition into mean-reverting decay. Check rain tank/maps
and every affected surface. Resolve or record owner-approved deferrals before
close-out; independent candidate review and promotion DECISION still required.
This authorizes scope, not advance approval of an unseen implementation.

## Live advisory and operational residuals

CF.Y.0021: Sep23 16:00 -> Sep26 02:00 EDT. Read PLAYBOOK for event work;
log John's primary observations immediately; use latest forecast for projections.
Prior 09-14/18/20 audits closed. Missing archives, writer/validator parity,
hourly failure visibility, optional outlook off the alert path, nowcast storm
dispatch validation and durable delivery outbox remain open. Watchdog covers
Mac-awake hours; external trigger awaits credentials. Existing widget v7.29a
re-copy obligation remains; driveway is a proxy, not a landmark.

Run date before relative-time prose; station-time helpers only. Preserve primary
provenance and append-only data. Explicit staging; commit -> gate -> push;
rejected push -> rebase or abort -> gate again -> retry. Ledger conflicts union.
Review credit follows actual scope/participation; no new promotion without
independent review and owner DECISION.
