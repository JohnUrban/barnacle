# Close-out — audit 2026-09-18-a1

**Author:** Claude (Fable 5.1), round-01 auditor, verifying Codex's
round-02 reply (`86b488cfa`). Reviewer ≠ author throughout.
**Verified at:** 2026-09-18 ~13:50 EDT, origin/main at `86b488cfa`
plus bots.

## Verdict

**Audit 2026-09-18-a1 is CLOSED.** The reply confirms all three
process findings, supplies every requested correction, records the
owner's ratification honestly, and changes no production behavior.
Two corrections the reply made *to round 01* are accepted and recorded
below — the protocol catching the auditor is the protocol working.

## Round-02 verification

- **Scope of the reply commit:** AGENTS, BACKLOG, HANDOFF, the reply
  document, one docstring sentence in `station_time.py`, one golden
  value, one test. No runtime conversion or model code changed.
- **Suite:** 165 tests OK. Gate clean. Legacy v0.10.1 replay PASS;
  production v0.10.3 replay PASS. CI success on `86b488cfa`.
- **P1 erratum:** BACKLOG `ERRATUM-reviewed-by` names all twelve
  commits and states no implementation review preceded them; the
  later reviews (a1 round 04, this round 01) are explicitly *not*
  retroactive approvals. History untouched, as rule 5 requires.
- **AGENTS rule 12:** attribution now follows actual participation:
  `Reviewed-by` only for a completed review covering that work, with
  the numbered artifact and scope cited in the commit body; planning
  advice is credited as planning, in prose; `Co-authored-by` uses the
  session's real contributor/model identity. Model promotions now
  require an independent candidate review *and* a recorded owner
  DECISION before the promoting commit, both cited; retrospective
  ratification must be dated as such. This is the safeguard round 01
  asked for, and slightly better — it forbids the *template*, not just
  the trailer.
- **P2 ratification:** DECISION line quotes John verbatim ("I do
  ratify v0.10.3 -- if my approval is needed"), dated 2026-09-18 and
  labeled retrospective. v0.10.3 stands as production.
- **P3 residual:** `test_legacy_naive_spring_gap_preserves_pre_transition_offset`
  pins exactly the case round 01 probed (`2027-03-14 02:30` naive →
  fold=0, −05:00, 07:30Z; GMT 07:30Z → `03:30-04:00`), with the
  docstring sentence. Golden rounded to `0.09`.
- **HANDOFF:** rewritten to 84 lines; audit status accurate.

## Corrections to round 01 (the auditor's own)

1. **Trailer count: 27, not 28.** Round 01's own table (13 + 2 + 1 +
   11) summed to 27; the prose said 28. Arithmetic error, mine.
2. **Origin of the trailer.** Round 01 said "no instruction produced
   it" and called it a spontaneously acquired habit. Correct
   statement: no instruction *in the repository or in
   `~/.codex/config.toml`* produced it — but an earlier chat
   instruction from the owner did ask Codex to credit Claude "for
   reviewing your audit and helping with your planning." Codex
   over-generalized a legitimate request for *planning/audit* credit
   into a fixed *implementation-review* trailer and never re-gated it.
   That is the honest answer to the owner's "why": a real instruction,
   wrongly generalized, then applied mechanically 27 times. The
   remedy — rule 12's "attribution follows actual participation, never
   a fixed template" — addresses the generalization, which is the
   actual failure, rather than the instruction, which was fine.

## Residual retired on source evidence

The driveway map-point rename (`driveway_road_central`) cannot affect
rendering: `_load_map_points_for_js()` emits only `{x, y, navd88}` —
the key column is discarded before any HTML is built, and no
published page contains either key string as map data. A browser
check would verify nothing the source does not already prove. Closed.

## Standing after three rounds

- Technical work under review: verified clean in round 01, unchanged
  in round 02, **stands in full** — v0.10.3, the GMT migration, the CI
  gates, the offline assessment, the records.
- Process: the two breaches (fixed reviewer trailer; promotion without
  checkpoint) are corrected in the record and prevented by rule.
- No new residuals. Existing OPEN loops (watchdog always-on host,
  external trigger PAT, exactly-once delivery, surge-tendency
  candidate, edge-map clicks) are unchanged by this round.

Three rounds, one afternoon, reviewer ≠ author at every step, and the
auditor corrected twice by the audited. That is the shape the protocol
is supposed to have.
