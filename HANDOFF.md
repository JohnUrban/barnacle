# HANDOFF — Bay Ave Barnacle in two minutes

**Snapshot: 2026-09-24 17:21 EDT.** Rewrite wholesale each ship; <100 lines.
`BACKLOG.md` OPEN LOOPS is authoritative; attic is archival.

## Wind-shadow c2 audit CLOSED — official trial collecting

Codex round07 independently verified Claude `83919dbdf`; all R1–R8 resolved.
Quality-aware QC excludes verified inferred outcomes; 48 refits reproduce,
six dataset hashes match, 333 required-decoder tests pass (two expected skips;
research-data test passes separately). Candidate GitHub CI and gate pass.
Report: `audits/2026-09-24-a3/07-close-out-codex.md`.
Frozen bundle: `82d156a63089573e837ae2e122336ec62f24fc80548aa8080105e3160aed5029`.

Merged as `8d5f6535e` under existing John shadow-only approval; all 25 paths
byte-match the reviewed candidate and merged hashes/gate pass. The
first durable official record is now verified in bot commit 5d281b19c:
issuance 2026-09-24T16:14:12Z, written 16:14:26Z, candidate status; bundle and
evaluator admission pass. Trial starts at nominal 16:00Z. Frozen changes need
a new identity/period. No production forecast/alert wind correction.

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

## Deferred validation — round 05 OPEN for full-path input handling

Codex verified Heron `c9b898616`: prior admission probes repaired, R6 CLOSED;
382 tests/gate pass and all r3 outputs reproduce. R1 still OPEN: malformed
required inputs can crash before validation; excluded NaN P still enters B0
metrics/thresholds. Synthetic probes, not a live-forecast failure. Heron round06
must test evaluate → event report → strict JSON, plus fidelity entry points.
Review/prompt: `audits/2026-09-24-a4/05-round04-verification-codex.md`.
Own erratum: Sep13 primary 0–6 h rows are 183/185, not 182/183. Protocol clock
note also needs correction. Research unmerged; no new owner choice needed.
Logging schema2 is verified collecting (21:11:34Z generation). A/B1/B2 remain
NOT YET EVALUABLE: 804 ZERO advisory pairs; 235 street pairs, 224 primary.

## Separate social rehearsal — Tern repair/expanded map pass next

Local `plan/social-broadcast`, sibling barnacle-social-plan, review `bf6a54273`.
Codex doc 21 reviewed Tern `26145cf03`: 408 tests, 72-case gallery, 14 delivery
scenarios and gate pass; alignment/shared map state verified; L1–L4 wording
repairs accepted. OPEN R1–R3: town legend omits used colors, unavailable surface
gets dry-gray explanation, correction planner/demo covers only one image.
John broadened map scope to all Highlands or bay-facing Route 36 if clearer,
including riverfront beyond old east edge; fit tightly. Doc 21 retains official
NJ boundary and coverage sketch; approximate town tags cannot define coverage.
Codex recommends bay-/river-facing primary and whole-borough comparison.
Doc 22 (`f987e5597`) records owner agreement: targeted fixes, preserve warning-first
and active/fresh LIVE radar, explicit above/below references, no public house
references or EDT/EST. Prototype MLLW/local-grate chart scales; maps keep local
ground-relative depths. Tern implements docs 21–22 together, including phone
key/legend and orientation, then Codex reviews and John evaluates copy/visuals.
Existing eligibility accepted; final strings and expiry remain open.
Offline → Facebook only → optional later expansion. No live copy,
accounts or posts; social branch stays local-only. Never overwrite newer main
living docs with that branch's snapshots. Heron work stays separate.

## Future owner task — neutral reference landmarks

John will identify/map/measure candidate features at the VFW (SE) and parking
lot (SW), serving the same role as house steps if he later moves. Details in
BACKLOG `john-neutral-landmark-survey`; no elevations or equivalence established.
Existing landmarks stay; this adds no requirement to Tern's current work.

## Operations

18 landmarks; hourly site/JSON; ~10-min radar nowcast; widget v7.29a re-copy
planned by John, completion unconfirmed. Only widget change since 7.28a removes
driveway proxy; forecast curves arrive through JSON. SMS imminent impact;
ntfy/email longer lead; alert tide horizon 48 h. Read PLAYBOOK and current
inputs for flood operations; do not infer live conditions from this snapshot.

Log observations with provenance. Date before relative-time prose. Explicit
staging; commit → gate → push; rejection → rebase or abort → gate → retry.
Union ledgers; never replace newer main files with an older worktree copy.
