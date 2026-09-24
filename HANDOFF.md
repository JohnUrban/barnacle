# HANDOFF — Bay Ave Barnacle in two minutes

**Snapshot: 2026-09-24 09:32 EDT.** Rewrite wholesale each ship; <100 lines.
`BACKLOG.md` OPEN LOOPS is authoritative; attic is archival.

## Current production — v0.10.6 live and CLOSED

Spec `model/v0.10.6.md`; promotion `75a9933ff`, candidate `1053eb436`, prior
John DECISION `b999ea1d0`. Audit `2026-09-24-a1` CLOSED at round06: 298
required-decoder tests, three replays, gate, CI, Pages and deployed charts
verified. Raw replay-input collection is active. Scoreboard cohort explanation
shipped `2e609b47f`. No runtime/data/page change in the present research review;
only the model spec's research-evidence wording is clarified, with no bump.

## Wind research CLOSED; shadow development APPROVED

Audit `2026-09-24-a2` CLOSED at Codex round03, independently verifying Claude
`142907573`/reply02. R1-R5 resolved: canonical UTC water, target-time masks,
purged fitting, withdrawn bounds and honest exploratory chronology.
All three report bodies reproduce; 50 refit/view MAEs agree with independent
calculations within 1.2e-16 ft; 29,592 overlapping astronomical predictions
match the separate UTC pull exactly. Originals remain intact. Retained flags
are not a quality-filtered evaluation; actual historical availability remains
unverified. Corrected signal supports research, not live or street-flood skill.

John approved Open-Meteo `gfs_seamless` wind AND pressure for a SHADOW-only
candidate (BACKLOG DECISION `wind-shadow-open-meteo`). Read the updated plan
`history/plans/2026-09-24-wind-term-candidate-plan.md`. No repeated feed-choice
approval needed.
BUILT (Claude, 2026-09-24) on branch `wind-shadow` (d82a82970; CI green; NOT
merged, no evaluation record yet): design + route rule committed first
(f66c077d5); 698 single runs archived with hashes; equivalence failed ->
route A (fit on single runs only, spring/summer: no winter storms); frozen
manifest/evaluator (`models/wind_shadow/FREEZE.md`); shadow runs after all
production outputs and alerts, 25-s bounded, append-only `data/wind_shadow/`.
NDFD probe done (`history/reports/2026-09-24-ndfd-feasibility.txt`): no
pressure element; house coastal cell does not map to the API.
Next: independent review of the branch, then merge = first record = trial
start. Review changes before the merge only update FREEZE.md.
Nothing changes displayed forecasts, rain predictions, maps, widget or alerts.
Minimum evaluation: 60 days AND five completed storms, target high/low/plug,
underprediction and rain-tank checks, production and NWS/P-ETSS comparators.
Fallback is v0.10.6 with an explicit shadow reason; missing/slow candidate
inputs cannot damage or unboundedly delay production. No test-set refitting.
A live term still needs a new version, replays, independent candidate review
and separate John DECISION. No subscription purchase or automatic cutover.

## Accepted limitations and operations

v0.10.6 surge decays toward the trailing mean with tau36 from the reading's
own time; UTC historical rerun supports keeping this policy. Missing-input
ladder: fresh/stale-download/stale-state/typical offset. Seven-day outlook uses
hourly P-ETSS and a labeled assumed guidance tail; between-high-tide advisory
corrections remain experimental with prospective input logging.
Five observed-reference rain events tie; Oct30 reconstructed peak is outside
aggregates, Sep13 partial QPF is sensitivity only. As-issued rain skill and
advisory-correction calibration remain accepted research limitations.

Production: 18 landmarks, hourly site/JSON, ~10-min radar nowcast, maps,
per-tide pages, widget, ntfy/email/SMS. SMS is imminent impact; ntfy/email
longer lead; alert tide horizon <=48 h. Seven-day guidance is experimental.
CF.Y.0021 Sep23 16:00 to Sep26 02:00 EDT: PLAYBOOK and current inputs.
Source/compound/p90 skill, lag/hysteresis, antecedent wetness, writer/gate
parity, failure visibility, durable outbox and external watchdog remain open.
John plans widget v7.29a re-copy (references v7.28a); completion unconfirmed.
Only widget change: remove driveway proxy from landmark ladder. Curve updates
arrive via forecast JSON with either version.

Log primary observations with provenance. Date before relative-time prose;
station-time helpers only. Explicit staging; commit -> gate -> push; rejected
push -> rebase or abort -> gate again -> retry. Ledger conflicts union.
