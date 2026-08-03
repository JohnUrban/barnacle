# AGENTS.md — Bay Ave Barnacle charter (all agents read this FIRST)

Bay Ave Barnacle is **production software**: a hyperlocal flood
forecaster for 342 Bay Ave, Highlands NJ (Sandy Hook gauge + NWS +
MRMS radar → water depth at 18 surveyed landmarks). An hourly GitHub
Actions bot and a ~10-min radar nowcast publish continuously; real
people receive its alerts. Current model: **v0.10.1**
(`model/v0.10.1.md`). The human is John (technically capable; offer
trade-offs, not tutorials; the barnacle mascot voice is intentional).

**Read order (cold start):** this file → `HANDOFF.md` (2-minute
snapshot) → `audits/` (an open report with no independent reply is a
live obligation) → `BACKLOG.md` OPEN LOOPS. On a flood event:
`PLAYBOOK.md` first. After any context compaction: reread this file.

## Hard rules

1. **Production first.** The bots commit every few minutes. Never
   `git add -A`; add explicit paths. Always rebase-with-gate before
   push: commit → `python3 forecast/check_artifacts.py` → push ‖
   (pull --rebase ‖ abort) → GATE AGAIN → retry. Never
   `pull --rebase || true`. Ledger/log conflicts resolve by UNION.
2. **Append-only ledgers.** `data/labeled_observations.csv`,
   `data/predictions_log.csv`, `data/forecast_accuracy.csv`: append,
   never rewrite. Strict CSV enforced by gate + CI
   (`tests/test_csv_ledgers.py`).
3. **Station time.** Never hand-construct station-local times; use
   `parse_station_local_time()` / `hours_until_station_time()` /
   `_station_local_now()`. This bug family shipped four times.
   Run `date` before writing any relative-time word (yesterday/
   today/tomorrow) — 4 incidents, including same-day drift.
4. **Provenance or it didn't happen.** A "measured" claim in any
   ranking/table/README must cite its primary record (ledger row,
   dictation file, gauge pull). Numbers first appearing in narrative
   summaries are `[INFERRED]` until traced — a fabricated event
   survived 16 days in prose (retracted 2026-08-03, see
   `assets/observations/2026-07-18/README.md`). Confidence tags:
   `[VERIFIED]` / `[STATED]` / `[INFERRED]`.
5. **Model versioning.** Real changes (constants/formula/landmarks)
   = new `model/v0.X.md`, old spec to `model/archive/`, code stamp
   (`CURRENT_MODEL_VERSION`) + log README updated in the SAME
   commit. Document mis-stamps honestly; never rewrite history.
6. **Rain DNA.** Rain modeling is the project's value-add — never
   defer it; ship crude-but-directionally-right and label
   uncertainty. Never reason "tide is low, so no flood risk."
   Radar sampling region = the catchment (CATCH_* constants), never
   a house-centered box.
7. **Unavailable ≠ zero.** Every input carries health status;
   degraded inputs surface loudly (input_health in forecast.json).
8. **Surfaces.** Widget edits: bump the version footer EVERY edit;
   John must re-copy into Scriptable. Any text that updates during a
   drag gesture must live in layout that cannot resize from content
   (two label-reflow incidents). Site changes: regenerate + gate
   before commit. Alert texts lead with the WARNING; daily cap
   ALERT_DAILY_CAP applies.
9. **attic/ = archival, never read** as instructions. To use
   something, consciously move it out.
10. **Audits** (`audits/README.md`): reviewer ≠ author; an open
    report needs an independent reply before close-out; confirm
    criticism of your own work rather than defending it.

## How John works

Event-driven rhythm: floods trigger intense 1–2 day sessions, then
weeks of autonomous bot operation. He green-lights per arc, then the
agent ships (commit AND push). Thinking-out-loud ≠ a directive —
he'll say "you don't need to do anything yet." Report failures with
evidence; don't over-caveat; don't oversell. His field observations
are data — log them immediately, verbatim where possible.

## Living-documents registry (a change isn't done until these reflect it)

| Document | Update when |
|---|---|
| `HANDOFF.md` | every ship — REWRITE WHOLESALE, <100 lines, self-dating |
| `BACKLOG.md` | any thread opens/closes/changes; ledger line per decision/fact/done |
| `AGENTS.md` (this) | a standing rule changes (slow-moving) |
| `PLAYBOOK.md` | an event teaches an operational lesson |
| `model/v0.X.md` | any model change (with version bump) |
| ledger CSVs | observations/predictions/outcomes as they occur |
| event `README.md`s | during/after each event |
| `audits/` | per protocol |
