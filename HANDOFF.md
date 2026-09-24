# HANDOFF — Bay Ave Barnacle in two minutes

**Snapshot: 2026-09-24 10:47 EDT.** Rewrite wholesale each ship; <100 lines.
`BACKLOG.md` OPEN LOOPS is authoritative; attic is archival.

## Immediate obligation — wind-shadow c2 awaits Codex verification; HOLD merge

Claude replied to audit `2026-09-24-a3` (all of R1–R8 confirmed) and repaired
branch `wind-shadow` at `fe7e1ebc9`:
`audits/2026-09-24-a3/02-repairs-reply-claude.md`. c1 is RETIRED before any
official record; the candidate is `wind-shadow-c2` (models/wind_shadow/FREEZE.md).
Next: Codex independently verifies fe7e1ebc9 (branch probe
`audits/2026-09-24-a3/verify_repairs_claude.py`; Codex's own a3 probes target
c1 interfaces). Merge only after that; merging = first official record = trial start.

Collection is opt-in: official only with BARNACLE_WIND_SHADOW_TRIAL=1 (set in the
production workflow only); preview via BARNACLE_WIND_SHADOW_PREVIEW_DIR; otherwise
nothing is fetched or written (--no-send/--dry-run: 0 invocations). The shadow
log is outside the fatal publish gate; CI checks FREEZE hashes and log validity.
Smoke tests: two local c1 records were deleted by Claude's cleanup, never
committed; identified and reconstructed in models/wind_shadow/SMOKE_TESTS.md;
EXCLUDED test output. Branch checks: 322 tests, 3.11 syntax scan, gate clean.
Limits carried: spring/summer-only fit; historical availability assumed.

## Approved wind scope and prior research

John approved Open-Meteo gfs_seamless wind AND pressure for shadow only:
BACKLOG DECISION `wind-shadow-open-meteo`, plan
`history/plans/2026-09-24-wind-term-candidate-plan.md`.
No displayed curve, map, widget, rain headline or alert changes. at least 60 days AND
five eligible completed storms; fixed endpoint, paired baseline/guidance,
high/low/plug, large-underprediction and rain checks; no outcome-driven refit.
Before first official record, review corrections update the freeze. Afterward,
changes require a new identity/period. No automatic production promotion.

Research audit `2026-09-24-a2` is CLOSED: Claude `142907573` + Codex round03;
UTC alignment, target-time masks, purged fitting and honest exploratory claims.
Historical skill supports research, not demonstrated live/street-flood gains.
Candidate route A uses spring/summer single runs; no winter training. NDFD probe
reports archive availability but unresolved coastal mapping; no feed substitution.
The candidate audit did not independently rerun that mapping experiment.

## Production — v0.10.6 live and CLOSED

Spec model/v0.10.6.md; promotion `75a9933ff`, reviewed candidate `1053eb436`,
prior owner decision `b999ea1d0`. Audit 2026-09-24-a1 closed after 298 tests,
three replays, gate/CI/Pages and 18 public artifacts/chart rendering verified.
Replay-input archive is active. Scoreboard cohort explanation `2e609b47f`.
Current audit changes documentation/evidence only; no production model bump.

Decay uses tau 36 h from observation time with cached verified mean and fallback
ladder. Seven-day hourly P-ETSS/guidance tails and advisory corrections remain
experimental. As-issued rain skill is not established: five observed-reference
rain events tie; Oct 30 reconstruction is not observed validation; Sep 13 partial
QPF is sensitivity only. Keep those limitations alongside scientific claims.

## Separate social planning

John approved local practice posts → Facebook only → optional later expansion.
Branch plan/social-broadcast, sibling barnacle-social-plan, local commit `be0365541`.
Tern's review reply/reconciled plan remains next; docs 06/07 record findings/scope.
Practice output stays local, outside deployment; wording clarity includes evidence
type, timing, depth reference and conditional scenarios across relevant arms.
No provider selected, public posting or account setup done by Codex. Keep separate.

## Operations

18 landmarks; hourly site/JSON; ~10-min radar nowcast; widget v7.29a re-copy
planned by John, completion unconfirmed. Only change since 7.28a removes driveway
proxy; curve updates arrive from JSON. SMS imminent impact; ntfy/email longer lead;
alert tide horizon 48 h, seven-day guidance experimental. Read PLAYBOOK and current
inputs for flood operations; don't infer live conditions from this snapshot.

Log observations with primary provenance. Date before relative-time prose.
Explicit staging; commit → gate → push; rejection → rebase or abort → gate →
retry. Union ledgers; never replace newer main files with an older worktree copy.
