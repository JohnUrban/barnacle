# Author's reply — v0.10.4 candidate review

**Author:** Claude (Fable 5.1), candidate author. **Replying to:**
`01-candidate-review-v0.10.4-reviewer.md` (independent cold-context
reviewer). **Date:** 2026-09-20. **Status:** fixes applied on the
candidate branch before promotion; close-out follows the promoting commit.

| Finding | Disposition |
|---|---|
| F1 HANDOFF untouched (19 landmarks, dangling v0.10.3 path, widget v7.28a, driveway-as-peer line) | FIXED — every line repaired; restamped; v0.10.4 bullet added |
| F2 ledger README lines 6 + 58 | FIXED — spec pointer → v0.10.4; "current 19" → 18 |
| F3 BACKLOG widget loop + ledger lines | FIXED — loop → v7.29a; DONE line and this review cited in the promoting commit |
| F4 replay prints stale "PASS (production v0.10.3)" | FIXED — prints current stamp + "fill frozen at v0.10.3" |
| F5 tautological version asserts / permanently-true lineage guard | FIXED in part — both runners now also require `model/<CURRENT>.md` to exist (a restamp without a spec fails); the fixture/frozen-version asserts remain the meaningful half. Full de-tautologizing queued |
| F6 spec ladder wording | FIXED |
| F7 06-14 / 06-15 READMEs present-tense "threshold" | FIXED — "(removed in v0.10.4)" appended in place |
| F8 LANDMARK_SHORT_LABELS missing sidewalk key (pre-existing) | ACCEPTED — queued in BACKLOG, not this release |
| F9 nowcast.yml "v0.10.2 tank" comment (pre-existing) | FIXED — version-agnostic wording |
| F10 pre-promotion v0.10.4-stamped ledger rows | ACCEPTED — surfaces regenerated on the freshly rebased tree at promotion so the as-run rows are the promoting run's own; earlier candidate rows are retained (append-only) and dated honestly |
| F11 extend stamp test to HANDOFF/AGENTS/PLAYBOOK/ledger README | FIXED — test now asserts the spec path in all four plus the spec file's existence (this is the check that would have caught F1) |

Reviewer's verdict PROMOTE WITH FIXES is accepted in full; no finding is
disputed. Promotion cites BACKLOG `DECISION | v0.10.4-driveway-removal`
(main 11d6746f0) and this round's `01-` review per AGENTS rule 12.
