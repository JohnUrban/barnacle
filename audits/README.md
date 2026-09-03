# audits/ — independent adversarial review channel

Formalizes the practice that already earned its keep here (the
2026-07-21 Codex audit found four critical production bugs;
cross-review caught a fabricated event and a test flake). Reports
live here rather than being pasted between chat sessions.

## Protocol
- One folder per audit: `YYYY-MM-DD-aN/`.
- Report: `01-<topic>-<author>.md` — findings with evidence paths.
- **Reply (a DIFFERENT agent than the author, mandatory):**
  `02-<topic>-<author>.md` — check the evidence, then
  confirm / dispute / already-addressed / needs-more-evidence,
  finding by finding.
- Further rounds `03-…`; never reuse or overwrite an index (list the
  dir first). Close-out `N-close-out-<author>.md` only after an
  independent reply exists.

## Rules
- On startup, list this directory. An `01-…` with no reply is a
  **live obligation**.
- Reply honestly — confirm criticism of your own work rather than
  defending it. Keep disagreements visible; never quietly delete a
  disputed finding.
- Verify against primary records (ledgers, dictation, gauge pulls,
  git history) — the 7/13 phantom event survived 16 days because
  narrative prose went unchecked.

Known index collision (noted 2026-09-03, audit sweep):
`2026-08-03-a2/` contains two `03-` files (implementation-review
and remediation-implementation) — it predates strict enforcement
of the never-reuse-an-index rule above. Committed reports are
never renumbered; the collision stands as a documented exception.
