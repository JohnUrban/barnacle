# Round 11 — Curlew candidate approved for merge

Reviewer: Codex. **2026-09-27**, review started 22:26 EDT.
Reviewed candidate **6e9fe57cb** on `audit/2026-09-27-a1-reply`, including
implementation 6e0e433e0 and round10. Candidate incorporates main through
feae83311. Approval covers the cumulative implementation reviewed in
rounds05/07/09 and the final round10 repair.

**APPROVED for merge and deployment verification. No outstanding code-change
request from this review.** Round09 R1 is resolved for the source-backed
and regression cases. Candidate is still unmerged at this review's
publication; audit 2026-09-27-a1 remains OPEN for the ship/verification step.
This is not a claim that the changes are live or that the scientific
follow-ups have been completed.

## Evidence

- Independent isolated archive of **6e9fe57cb**: **443 tests OK, one skip**
  with `BARNACLE_REQUIRE_GRIB=1`. Skip is absent local training input.
- All three read-only frozen replays PASS (v0.10.1, v0.10.3, v0.10.6);
  seven frozen wind hashes match. Artifact gate clean.
- Observation, predictions and forecast-accuracy ledgers byte-identical to
  incorporated main feae83311. Model specs and frozen model data unchanged.
- Re-ran the independent round09 probes against this candidate, rather than
  only accepting updated implementation tests. Actual row238 no longer
  acquires an invented crossing at the marked curb; the full site/HTML email
  retains the “over the curb elsewhere” qualification. Short/widget forms
  quote an opening excerpt and mark its truncation.
- “Not dry; water above the SW grate” remains quoted as reported, and its
  model claim remains visible and unverified. Mixed-location observations
  and unknown-depth reports retain claims; actual row191 remains uncertain
  in time. Valid tape and clear timed whole-intersection negatives retain
  the intended coverage behavior.
- Rendered the complete landing page and subject/plain/HTML email from a
  copied forecast snapshot with the row238 and negation payloads. Rendering
  succeeded and the source distinctions survived those actual renderers.
  Widget text executed through node; **native Scriptable layout was not
  executed** and remains a deployment check.
- Prior repairs stand: delivery-error privacy; exit75 plus fresh matching
  receipt; source-based intervals; station-specific Battery datum; distinct
  incremental/total-water maxima; timestamp and episode handling; escaped
  HTML; order-invariant plot whiskers.

[Verification receipt and reproduced outputs](11-verification-results.json).
The reused probe is [round09's script](09-review-probes.py), invoked with
this candidate's isolated archive path. Its historical hardcoded candidate
label is corrected in this receipt; the executed code was 6e9fe57cb.

The relevant owner authorization is already recorded in the candidate's
BACKLOG `sofar-line-empirical-wins` DECISION (Sep27 18:20/18:24). This review
does not ask for the same decision again, approve a new gate formula or
alter the frozen wind trial. Current model version remains v0.10.6.

## Ship handoff — remaining work, not another development round

1. Merge the approved branch against **then-current main**, preserving all
   newer bot outputs, event notes, raw notes, episode references and ledger
   rows. Reconcile HANDOFF/BACKLOG semantically; union append-only history.
   Preserve rounds04/06/08/10 from the candidate and rounds05/07/09/11 from
   main. Cite this review and the existing owner DECISION in the merge/ship
   record, with accurate attribution.
2. Regenerate affected pages on the combined code/data state, gate and
   inspect the results. Use no-send/isolation for review rendering; do not
   send review alerts or replace live ledger files with stale saved copies.
   Keep generated-at/source stamps honest. Regeneration must not overwrite
   newer bot publications with old candidate snapshots.
3. Follow commit → gate → push, and rebase/abort → gate again on a rejected
   push. Verify the deployed site/JSON/widget asset, including evidence
   labels, rejected-max handling and current version stamps. Record the
   actual cutover of the retrospective line; distinguish ship verification
   from a real-world test of an alert-transport outage.
4. Widget source is **v7.32a**. Check its medium-widget long-report and
   model-claim layout on a real Scriptable surface before treating native
   readability as verified. John re-copies the final deployed asset, not
   a branch copy. Write the deployment verification/close-out as **round12**
   once those checks are complete; keep any remaining owner-only check
   explicitly pending rather than claiming it passed.

No further Curlew implementation revision is requested before this ship
step. Heron's evaluator and Tern's social work remain separately owned.
No permission is implied to alter model physics or social posting.

## Retained research/record follow-ups

The four-window study ends at Sep27 AM; subsequent evening records must not
be lost or implied covered. Photos, a calibrated gate-transfer explanation,
verified-versus-as-seen NOAA follow-up, historical census/hindcasts and
Heron's episode-aware as-issued evaluation remain documented work. An
implementation audit close-out must not turn these into completed science.

Chronology note: round10's author header says “22:20–22:35”; its actual
commits are 6e0e433e0 at **22:25:38-04:00** and 6e9fe57cb at
**22:26:25-04:00**, and this review began before 22:35. Use those primary
commit timestamps, not the header's future endpoint, for the work chronology.
