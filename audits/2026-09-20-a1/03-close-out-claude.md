# Close-out — candidate review 2026-09-20-a1 (model v0.10.4)

**Author:** Claude (Fable 5.1), candidate author, closing after the
independent reviewer's round 01 and the author's round 02.
**Promoted at:** main `3d71ab281`, 2026-09-20 21:2x EDT.

## Verdict

**Round CLOSED; v0.10.4 promoted.** The rule-12 sequence held in
order: owner DECISION recorded on main (11d6746f0, 19:07) → candidate
built on a branch → independent cold-context review (01: PROMOTE WITH
FIXES) → all must-fixes and the cheap lows applied and answered (02) →
surfaces regenerated on the freshly rebased tree → promoting commit
citing both artifacts.

## What the reviewer caught that the author had missed

Four registry/stamp drifts (HANDOFF untouched with a dangling spec
path and the retracted "driveway is a threshold" line; two dangling
pointers in the ledger README; BACKLOG's widget loop; a stale PASS
string) plus a permanently-true lineage guard. None affected numbers;
all affected the record. The stamp test now checks four cold-start
documents, which would have caught the largest of them.

## Standing

- 18 landmarks; `driveway_central` is a documented proxy (PLAYBOOK
  "PROXIES vs LANDMARKS", ledger README); numerically identical to
  v0.10.3; both frozen replays pass; 170 tests; gate clean; CI green.
- Queued from the review: F8 `LANDMARK_SHORT_LABELS` missing the
  sidewalk key (pre-existing); full de-tautologizing of the version
  asserts (F5, partial).
- Owner: widget v7.29a re-copy (the driveway rung is gone; v7.26a
  still renders correctly meanwhile).
