# Round 07 — independent promotion verification and close-out

**Audit 2026-09-23-a1: CLOSED for v0.10.5.**
Reviewer: Codex. Verified 2026-09-23, 23:30–23:33 EDT.
Promotion reviewed: `4bb885e021c0d84144dd95d18abef575c9c468fd` (Claude).

**Verdict: PASS, with documentation corrections included in this close-out.**
The promotion correctly publishes the reviewed inputs/policy release as
v0.10.5. No production-code, model-constant, landmark or numerical correction
was needed. This is an independent post-promotion verification, honestly dated;
it is not represented as pre-commit approval.

## Review and approval chain

- Codex rounds 01/03 audited Claude's work; round 05 verified the targeted
  repairs and separately recorded Codex's recovery implementation.
- Claude round 06 independently reviewed `eb8e79475` + `3fc6be082`, passed the
  recovery and percentile fix, and raised F1 on missing observed surge.
- I **confirm F1**: returning no curve on unavailable surge was a behavior change
  from the former degraded-astronomy tank, not wholly a class-(c) restoration.
  My earlier blanket classification was too broad. No-defense correction: the
  behavior is now expressly included in this class-(b) spec and owner decision.
- BACKLOG `DECISION | v0.10.5-promotion` records John's 23:22 EDT authorization
  to promote the reviewed state as-is and put the newer ideas in v0.10.6. It
  explicitly retains the labeled no-curve interim behavior. This precedes the
  23:25:52 EDT promoting commit; the commit cites approval and actual reviews.
- F1 is **resolved for this release by the owner-approved interim policy and
  separate v0.10.6 scope**, not falsely described as an implemented outage ladder.

## Verification results

| Requirement | Result and primary evidence |
|---|---|
| Spec complete and code-consistent | Full Inputs & policy, production/outlook distinction, validity, scope, rain scenarios, scoring, health, 18 landmarks, tide pathway, dynamic/static tank and limitations present. Current source selection and missing-surge behavior agree. Exact wording corrections below. |
| Atomic model stamp | The only production Python change in the promotion is CURRENT_MODEL_VERSION v0.10.4 -> v0.10.5 and its comment. No numerical behavior changed at promotion. |
| Archive and current spec | Old top-level v0.10.4 spec moved to model/archive; candidate replaced by full model/v0.10.5.md; neither obsolete top-level path remains. Archive changes are relative references, not rewritten model history. |
| Documentation stamps | AGENTS, README, PLAYBOOK, HANDOFF, predictions-log README and observations README point to current v0.10.5. Historical mentions correctly retain older versions. |
| Links | Existing documentation-link tests pass. Also repaired one inline archived-spec reference that Markdown-link tests had not covered. |
| Generated surfaces | Forecast JSON, nested outlook and 16 changed HTML/JSON surfaces checked for v0.10.5. Gate validates generation/schema/model consistency across current surfaces. Static widget/town map have no per-release model stamp; historical pages keep their original stamps. |
| Public deployment | Public forecast.json, index.html, details.html and outlook.html bytes exactly matched 4bb885e02 during review. |
| Ledgers | Every earlier byte preserved. Promotion adds 6 prediction rows, 1 day-risk row and 14 outlook rows; labeled observations and accuracy rows unchanged. Also verified prefixes back to round-01 candidate ece4c2314. |
| Alert and widget state | alert_state.json and Scriptable source unchanged by promotion. No messages sent by this review. |
| Frozen goldens | Both reproduction JSONs byte-identical to parent; v0.10.1 and v0.10.3 replay scripts PASS with v0.10.5 stamp. |
| Full suite | 266 tests OK, BARNACLE_REQUIRE_GRIB=1, installed decoder, no skips locally. |
| Artifact gate | PASS. |
| Remote promotion checks | Barnacle CI 35951416953 and Pages 35951416268 both SUCCESS for 4bb885e02. |

Machine-readable evidence: [round07-promotion-verification.json](round07-promotion-verification.json).
Commands: decoder-enabled unittest discovery; forecast/check_artifacts.py;
history/scripts/reproduce_v0_10_1.py; history/scripts/reproduce_v0_10_3.py;
Git object/CSV-prefix inspection and deployed-byte comparison.

Replay results retain RMS **1.316778 inches** on the frozen v0.10.1 fit and
**1.07e-14 inches** reference error / **0.090 inches** maximum fill correction
on the v0.10.3 replay. These verify unchanged arithmetic; they do not validate
new forecast inputs or every experimental scenario scientifically.

## Documentation corrections made before close-out

These are explanatory corrections, not changes to the running forecast:

1. **Cutover precision.** Replaced approximate incorrect commit times with
   13:14:14Z for 8e686a4f1 and 13:55:23Z for bfd39b533. Commit timestamps are not
   claimed to be deployment timestamps. First v0.10.5 generation in promotion
   is **2026-09-24T03:24:52Z = September 23 23:24:52 EDT**, preceding the
   promoting commit by one minute. Thus the old phrase “all rows before the
   promoting commit carry v0.10.4” was too broad: the promotion itself appends
   correctly stamped v0.10.5 rows generated before commit. Spec and ledger
   README now say this precisely. No CSV history rewritten.
2. **Tide equation.** The inherited shorthand could imply astronomy plus a
   complete NWS forecast. The code selects the matching NWS product TOTAL;
   only the persistence fallback adds observed residual to astronomy. Spec
   now explicitly states the branches, including astronomical-only degradation.
3. **Outlook versus production.** Qualified the outlook ladders and hourly
   anchoring text, including the bracketing-hour maximum used for correction,
   interior interpolation and first/last-anchor hold/fade. It is an approximate
   hourly rule, not exact sub-hourly peak reconstruction.
4. **Horizon/coverage.** 168 h is the requested boundary; hourly sampling may
   stop less than one hour short. QPF partial coverage uses actual local-day
   duration and a half-hour tolerance, not a universal 24 h. The absent-grid
   interval treatment is identified as the implementation's day-total assumption,
   not an independently verified provider guarantee. Explicit nulls remain unknown.
5. **Archive/reference cleanup.** Corrected the archived v0.10.4 inline reference
   to v0.10.3 and removed “removed above” from the current landmark description.
6. HANDOFF and BACKLOG are refreshed so the completed recovery review, promoted
   release and audit closure no longer appear outstanding.

## Scope remaining open outside this release

- v0.10.6: fresh/stale surge decay and age-labeled outage ladder, with separate
  implementation, new golden requirements where applicable, independent review
  and promotion decision. The current no-curve-on-outage behavior remains until
  that work ships. The research's scientific claims were not audited here.
- Experimental compound/p90 rain scenarios, NWPS/P-ETSS skill, source transition
  differences, persistence assumptions and absent-grid-interval assumptions need
  ongoing evaluation. Closure is not a blanket declaration of scientific accuracy.
- Broader writer/validator parity, hourly-failure visibility, off-critical-path
  outlook acquisition, nowcast dispatch validation and durable delivery outbox
  remain separate BACKLOG items. Existing widget re-copy obligation remains.

All required v0.10.5 release review and close-out steps are complete. No open
v0.10.5 promotion blocker remains; do not reopen the completed release merely
because v0.10.6 and explicitly tracked research/operations work are unfinished.
