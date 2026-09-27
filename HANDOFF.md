# HANDOFF — Bay Ave Barnacle in two minutes

**Snapshot: 2026-09-27 14:55 EDT.** Rewrite wholesale each ship; <100 lines.
`BACKLOG.md` OPEN LOOPS is authoritative; attic is archival.

## EVENT #10 — nor'easter coastal surge, 2026-09-25 → 27 (storm winding down)
Folders: `assets/observations/2026-09-26/` (rounds 0–2 + figure) and
`2026-09-27/` (round 3); verbatim `flood-measurements.txt` in each; all
readings in `data/labeled_observations.csv` (observer john).
- Crests: **9/26 AM 5.70 NAVD88 (+26.2 in, largest measured flood)**; 9/27 AM
  5.62. Garage flooded both mornings. 9/25 PM dry; 9/26 PM late + minor (~4.22).
- **Snug Harbor tide gate CLOSED** (seen 9/26 18:19, ~21:58; 9/27 ~08:30),
  police-operated. Gated corner: below ~5.0–5.3 bay it stays dry or floods late
  and small; above it fills fast (~15 in/hr) and nears the bay; drains slowly
  (~5–6 in/hr) behind the gate. Figure: `2026-09-26/analysis/corner_vs_gauge.png`.
- Gauge forecast was good (9/25: NWS coastal product, err −0.07 ft — first
  real `nws_surge_parser` validation); the miss is gauge→corner (no gate input).
- Rain added ~2.4 in at the 9/26 crest (drains shut; 08:36–08:48 burst).
- Live fixes: ntfy latin-1 header crash (hourly runs had stopped);
  near-term chart tape dots now every reading at true time (were max-per-slot).
- Queued (BACKLOG): gate-aware model (gate state input + leak/overtop term,
  full rule-12 review); garage-entry warning at first-porch-step top (user PREF,
  all arms); 9/27 rain check; Borough gate inquiry; gate photo to add;
  user rule — gate closed for tides, OPEN for rain floods.
- Outlook: surge fell +3.1 → +1.9 ft by 14:00 9/27; 9/27 20:58 and 9/28 09:15
  bays ~3.8–4.2 → little at the corner unless the surge rebounds.

## Wind-shadow c2 audit CLOSED — official trial collecting

Report `audits/2026-09-24-a3/07-close-out-codex.md`; merged `8d5f6535e`
(shadow-only, John-approved); first official record bot `5d281b19c`
(2026-09-24T16:14Z). Frozen bundle 82d156a6…; changes need a new identity.
No production forecast/alert wind correction.
## Approved wind scope and prior research
John approved Open-Meteo gfs_seamless wind AND pressure for shadow only:
BACKLOG DECISION `wind-shadow-open-meteo`, plan
`history/plans/2026-09-24-wind-term-candidate-plan.md`.
No displayed curve, map, widget, rain headline or alert changes. At least 60 days
AND five eligible scored completed storms; fixed endpoint, paired baseline/
guidance, high/low/plug, underprediction and rain checks; no outcome-driven refit.
No new feed decision or production promotion authorized by this review.

Research audit a2 CLOSED (spring/summer fit only; no winter evidence).

## Production — v0.10.6 live and CLOSED

Spec model/v0.10.6.md; promotion `75a9933ff`, reviewed candidate `1053eb436`,
prior owner decision `b999ea1d0`. Audit a1 closed after 298 tests, three replays,
gate/CI/Pages and 18 public artifacts/chart rendering verified. Replay-input
archive active; scoreboard cohort explanation `2e609b47f`.
Decay tau 36 h; cached verified mean and fallback ladder. Seven-day guidance
tails/advisory corrections remain experimental. As-issued rain skill is not
established: five observed-reference events tie; Oct30 reconstruction is not
observed validation; Sep13 partial QPF is sensitivity only.

## Deferred validation — evaluator audit a4 CLOSED; science awaits data
Close-out `audits/2026-09-24-a4/09-close-out-codex.md` (Heron `cd17a5a14`).
Research unmerged, ready for a separate integration step. A/B1/B2 NOT YET
EVALUABLE; archive logging live. Revisit 2026-10-09 or after an informative
event — Event #10 may qualify; checkpoint
history/plans/2026-09-25-heron-validation-checkpoint.md.

## Social rehearsal — local-only; John's copy/geography acceptance open
Tern repairs closed (sibling barnacle-social-plan/.../28-codex-repair-closeout.md).
No accounts/posts, production copy/model changes, merge or push of social branch.

## Future owner task — neutral reference landmarks
John will identify/map/measure candidate features at the VFW (SE) and parking
lot (SW), serving the same role as house steps if he later moves. Details in
BACKLOG `john-neutral-landmark-survey`; no elevations or equivalence established.
Existing landmarks stay; this adds no requirement to Tern's current work.

## Operations
Storm check 2026-09-25: NWS/tide tables show serious weekend flooding; core
Saturday curve ~1 ft lower. Offline email TODAY LIGHT vs day_worst MODERATE.
Sanitized weekend-assessment report in history/reports/ has evidence. Actionable
plan: history/plans/2026-09-25-storm-followup-handoff.md (arms, tests, order).
Next: day-headline parity including widget; guidance-first candidate and SMS
policy are separate reviews. Test-isolation fix only; no production change.
18 landmarks; hourly site/JSON; ~10-min radar nowcast; widget v7.29a re-copy
planned by John, completion unconfirmed. Only widget change since 7.28a removes
driveway proxy; forecast curves arrive through JSON. SMS imminent impact;
ntfy/email longer lead; alert tide horizon 48 h. Read PLAYBOOK and current
inputs for flood operations; do not infer live conditions from this snapshot.

Log observations with provenance. Date before relative-time prose. Explicit
staging; commit → gate → push; rejection → rebase or abort → gate → retry.
Union ledgers; never replace newer main files with an older worktree copy.
