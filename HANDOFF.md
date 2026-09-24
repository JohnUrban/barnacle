# HANDOFF — Bay Ave Barnacle in two minutes

**Snapshot: 2026-09-24 10:59 EDT.** Rewrite wholesale each ship; <100 lines.
`BACKLOG.md` OPEN LOOPS is authoritative; attic is archival.

## Immediate obligation — wind-shadow c2 re-reviewed; HOLD merge

Codex independently reviewed Claude's `wind-shadow` at `fe7e1ebc9`.
Audit `2026-09-24-a3` round03 remains OPEN:
`audits/2026-09-24-a3/03-c2-verification-codex.md`. Claude reply04/repairs next.
All 48 coefficient sets, sample counts, fit MAEs and five dataset hashes
reproduce; 698 raw runs verify; 322 tests pass (one expected absent-log skip),
including frozen replays. Episode/sparse-evidence, timeout/QC and mean-window
repairs verified. c1 retired; c2 has no official records.

Remaining: actual publish-gate CLI crashes on non-object shadow JSON;
freeze checks do not prevent changed-bundle collection/scoring; rain comparison
restarts empty, losing prior rainfall/storage; NWS comparison counts Barnacle
fallback; availability/raw-pressure/training-QC gaps; no-send/dry-run exclusion
fails with trial env inherited. All counterexamples are synthetic, isolated,
network-mocked; no candidate edits or actual trial records from this review.

Branch freeze: models/wind_shadow/FREEZE.md. Pretrial corrections can update c2;
after its first official record, any frozen change needs a new identity/period.
Merging enables collection; it is not itself a record or trial-start timestamp.
Two deleted local c1 smoke records are honestly documented/reconstructed in
SMOKE_TESTS.md; their original bytes are unavailable. Production remains v0.10.6.

## Approved wind scope and prior research

John approved Open-Meteo gfs_seamless wind AND pressure for shadow only:
BACKLOG DECISION `wind-shadow-open-meteo`, plan
`history/plans/2026-09-24-wind-term-candidate-plan.md`.
No displayed curve, map, widget, rain headline or alert changes. At least 60 days
AND five eligible scored completed storms; fixed endpoint, paired baseline/
guidance, high/low/plug, underprediction and rain checks; no outcome-driven refit.
No new feed decision or production promotion authorized by this review.

Research audit a2 CLOSED: corrected UTC alignment, target-time masks, purged
fitting and exploratory claims. Candidate fit uses spring/summer single runs;
no winter evidence. Historical availability and verified-data lag are stated
assumptions. NDFD coastal mapping experiment was not independently rerun here.

## Production — v0.10.6 live and CLOSED

Spec model/v0.10.6.md; promotion `75a9933ff`, reviewed candidate `1053eb436`,
prior owner decision `b999ea1d0`. Audit a1 closed after 298 tests, three replays,
gate/CI/Pages and 18 public artifacts/chart rendering verified. Replay-input
archive active; scoreboard cohort explanation `2e609b47f`.
Decay tau 36 h; cached verified mean and fallback ladder. Seven-day guidance
tails/advisory corrections remain experimental. As-issued rain skill is not
established: five observed-reference events tie; Oct30 reconstruction is not
observed validation; Sep13 partial QPF is sensitivity only.

## Separate social planning

John approved local practice posts → Facebook only → optional later expansion.
Separate `plan/social-broadcast`, sibling barnacle-social-plan, local `6e673072f`:
Tern's reply reviewed in doc 10; Stage B gallery can proceed with R1–R5
failure cases. John settled W9: AM/PM public event prose, 24-hour internal
records. Practice output stays local. Tern recommended as developer; Codex
independent reviewer. No provider selected, accounts connected or posts sent.
Merge narrow doc changes when adopting; do not overwrite newer living docs.

## Operations

18 landmarks; hourly site/JSON; ~10-min radar nowcast; widget v7.29a re-copy
planned by John, completion unconfirmed. Only widget change since 7.28a removes
driveway proxy; forecast curves arrive through JSON. SMS imminent impact;
ntfy/email longer lead; alert tide horizon 48 h. Read PLAYBOOK and current
inputs for flood operations; do not infer live conditions from this snapshot.

Log observations with provenance. Date before relative-time prose. Explicit
staging; commit → gate → push; rejection → rebase or abort → gate → retry.
Union ledgers; never replace newer main files with an older worktree copy.
