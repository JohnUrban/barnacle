# Round 06 — v0.10.6 release close-out

**Audit 2026-09-24-a1: CLOSED.** Codex, 2026-09-24 01:53 EDT.
Promoting merge: `75a9933ffc854496f9e1f5e2c3c58b4e96c15ca7`.
Candidate: `1053eb436`; independent implementation review rounds01/03/05,
with implementer replies02/04. John's approval was recorded before promotion
in `b999ea1d0`, BACKLOG DECISION `v0.10.6-promotion`.

Codex reviewed Claude's implementation, performed the approved integration,
and verified deployment. This close-out verifies that integration and
release; it does not claim another independent author reviewed Codex's
promotion documentation. Runtime, tests and replay fixtures are byte-for-byte
identical to the independently reviewed candidate.

## Release verification

- All six audit findings are resolved. Final R6 calculations reproduce as
  recorded in [round05](05-candidate-approval-codex.md). Accepted limitations
  for items2/5 remain explicit; no additional owner decision was required.
- **298 tests PASS**, with `BARNACLE_REQUIRE_GRIB=1` and the decoder installed.
  The first integrated run caught a missing model-spec link in the rewritten
  HANDOFF; it was repaired and all 298 passed on the final tree.
- Frozen **v0.10.1, v0.10.3 and v0.10.6 replays PASS**; goldens unchanged
  from the reviewed candidate. Artifact gate PASS before and after commit.
- Current source/spec/README stamps are v0.10.6. The v0.10.5 spec is archived,
  with its relative links verified from the archive directory. Current spec
  links also resolve. The cutover note distinguishes review previews,
  regeneration, commit and deployment; earlier ledger stamps are untouched.
- Regenerated on integrated main at **2026-09-24T05:46:59Z** using
  `--no-send`. Every old byte is retained in the five canonical ledgers:
  predictions +6 rows, day-risk +1, outlook +14; observations and accuracy
  unchanged. Existing production per-tide evolution rows all survive;
  those derived slices are regenerated from the canonical ledger, so
  candidate-preview-only rows are not invented as production history.
  `alert_state.json` is unchanged; manual generation sent no notifications.
- First replay-input archive is committed at `data/replay_inputs/2026-09.jsonl`,
  same generation and model: 72 raw NWPS hours, 82 production QPF hours,
  six advisory rows, hourly astronomy/corrected outlook, fresh selected
  reading and mean, and tank initialization. Local validation passes and
  GitHub returns the identical blob `8300f03cbacec4cfc15a5919e6dc360e773254b0`.
- [CI](https://github.com/JohnUrban/barnacle/actions/runs/35961701365) and
  [Pages deployment](https://github.com/JohnUrban/barnacle/actions/runs/35961700525)
  **SUCCESS for the promoting commit**.
- All **18 checked public artifacts match the promotion bytes**: forecast
  JSON, landing/details/outlook/town-map pages, tide index, and six current
  tide HTML/JSON pairs. The live landing page visibly reports v0.10.6.
- In Chrome, independently inspected the deployed landing curve and both
  seven-day plots. All render; advisory diamonds, guidance-source boundaries,
  and assumed-tail triangles are visible. Outlook generation matches the
  release. The NBM age warning is visible and scoped to the outlook; core
  inputs are healthy. This is expected input degradation, not a hidden zero.

Machine-readable verification: [close-out-verification.json](close-out-verification.json).

## What remains outside this release

Advisory corrections between high tides remain experimental. Prospective
collection has started; it has not yet established low-tide correction skill
or multi-event as-issued rain-flood skill. The corrected historical rain
sample does not distinguish the two rules; October30's unknown crest is not
validation. The last-guidance tail is explicitly an assumption.

Forecast-wind work, compound/p90 scenario validation, other research and
operational backlog items remain separate. The scoring-cohort explanation
on the page remains a recorded nonblocking follow-up. This release did not
edit the Scriptable widget, so it adds no new widget re-copy requirement;
the pre-existing v7.29a obligation remains.

No outstanding v0.10.6 release blocker or undecided acceptance item remains.
