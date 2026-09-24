# Wind-shadow smoke tests before any official record (audit 2026-09-24-a3 R8)

Two LOCAL `--no-send` runs of the hourly job in Claude's `wind-shadow` worktree
on 2026-09-24 wrote wind-shadow records to that worktree's
`data/wind_shadow/2026-09.jsonl` using candidate **wind-shadow-c1** (then
uncommitted; the c1 manifest was the one later frozen in d82a82970). Both were
DELETED by Claude's cleanup (`rm -rf data/wind_shadow`) right after inspection;
they were never committed, pushed or written by the production workflow.

| # | issuance (forecast generated_utc) | status | what survives |
|---|---|---|---|
| 1 | shortly before 14:02Z (exact time lost: its forecast JSON was overwritten by run 2) | fallback: "observed pressure unavailable (ValueError: latest pressure 13:00Z older than 60 min)" | the session output only; this failure motivated the 6-min pressure fix |
| 2 | 2026-09-24T14:02:36Z (files written 10:02:50 EDT) | candidate | the forecast JSON and run log in Claude's session scratch directory; a deterministic RECONSTRUCTION, `smoke_tests/2026-09-24T1402Z-reconstructed.json` |

Reconstruction of #2: rebuilt with the c1 code at d82a82970 from the
surviving forecast JSON, the archived 06Z single run (same run init; archived
copy retrieved 14:00:39Z, SHA-256 4c6dea0a...), and the pressure values
printed at the time (1030.4 hPa at 13:54Z, 30-day anomaly +10.982 hPa). All
five values printed at the time (leads 6/12/24/30/48 h: baseline, candidate,
correction) match the reconstruction to 0.01 ft. It is NOT the original bytes.

## Trial status: EXCLUDED test output, not the first trial record
- Official collection is defined as records written by the production
  workflow with `BARNACLE_WIND_SHADOW_TRIAL=1` into the repository's
  `data/wind_shadow/` (DESIGN, "Trial identity and start"). These were local
  developer runs in a worktree, never in the official log.
- Candidate **c1 is retired** without any official record. The repaired
  candidate is **wind-shadow-c2** (new id, new manifest, new freeze), so no
  record of any vintage can be confused with a c2 trial record. The c2
  evaluator scores only records bound to c2's frozen manifest and runtime
  hashes with `collection == "official"`.
