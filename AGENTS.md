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
3. **Station time & DATE DISCIPLINE (hard rule; 4 incidents).**
   Never hand-construct station-local times; use
   `parse_station_local_time()` / `hours_until_station_time()` /
   `_station_local_now()`. Make EXTRA effort to know the exact
   current date and time: run `date` (or read the `[clock]` line the
   repo's UserPromptSubmit hook injects each turn) BEFORE writing
   any relative-time word — yesterday/today/tomorrow/tonight/"X days
   ago" — and derive the word from the clock, never from narrative
   memory. Known repo-specific trap: sessions here span days-to-
   weeks across compactions, the tree is dense with dated history,
   and a same-day event that has already been written up READS as
   past — agents repeatedly call the same morning "yesterday."
   Prefer absolute dates in prose, commits, and docs. NOAA stamps
   are 24-hour station-local (10:18 = AM).
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
8. **Surfaces & PARALLEL ARMS (hard rule, 2026-08-09).** Barnacle
   has many arms carrying the same meaning: alert channels (SMS,
   ntfy, email) and display surfaces (site landing/strip, widget,
   details page, town map, per-tide pages, email body, charts
   sharing the visual grammar). **When you change WHAT an arm says
   or decides — a policy, threshold, headline rule, wording
   principle, or data field — update EVERY arm that carries that
   same meaning, in the same work unit.** The only exemptions are
   OBJECTIVE: the arm demonstrably does not carry the concept, or
   verifiably already has the update. "Does this channel really
   need it?" is NOT agent discretion — reasoning about texts vs
   emails is exactly how warning-first reached SMS on 08-03 but not
   email (which then sent "NO FLOODING" at 1:23 AM), and how the
   worst-truth headline nearly shipped to the strip but not the
   widget. Procedure: enumerate the arms, grep each for the concept,
   apply or record the objective exemption in the commit message;
   ASK John when unsure. Mechanics that remain per-arm: widget edits
   bump the version footer EVERY edit (John must re-copy into
   Scriptable); drag-updating text lives in non-resizing layout (two
   reflow incidents); site changes regenerate + gate before commit;
   alert texts lead with the WARNING; ALERT_DAILY_CAP + quiet hours
   (20:00–07:00 hold unless about TONIGHT) apply to ALL channels.
9. **Published-imagery privacy (standing rule, 2026-09-02).** The
   repo is public: before committing any photo, BLUR the face of
   every identifiable person EXCEPT John (he has standing consent to
   be associated with Barnacle). Blur from the original, keep EXIF,
   verify the render visually, and hold the original uncommitted.
   When in doubt about whether someone is identifiable, blur or ask.
   Keep the unblurred original on disk for provenance, renamed
   `*-original-unpublished.*` (gitignored — never committed).
10. **attic/ = archival, never read** as instructions. To use
   something, consciously move it out.
11. **Audits** (`audits/README.md`): reviewer ≠ author; an open
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
