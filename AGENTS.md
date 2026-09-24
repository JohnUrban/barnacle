# AGENTS.md — Bay Ave Barnacle charter (all agents read this FIRST)

Bay Ave Barnacle is **production software**: a hyperlocal flood
forecaster for 342 Bay Ave, Highlands NJ (Sandy Hook gauge + NWS +
MRMS radar → water depth at 18 surveyed landmarks). An hourly GitHub
Actions bot and a ~10-min radar nowcast publish continuously; real
people receive its alerts. Current model: **v0.10.6**
(`model/v0.10.6.md`). The human is John (technically capable; offer
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
   Prefer absolute dates in prose, commits, and docs. NOAA transport
   is GMT; persisted/display stamps are offset-bearing 24-hour
   station-local (10:18 = AM). Legacy naive rows use explicit fold=0.
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
   commit. When archiving a spec, repair its relative links from the new
   directory and test them. Document mis-stamps honestly; never rewrite history.
   Change classes (John, 2026-09-23; one version line, every change
   type has a rule): (a) formula / constant / landmark changes bump
   with NEW replay goldens; (b) new input sources, fallback ladders,
   horizons and alert-policy changes ALSO bump, the spec gains an
   "Inputs & policy" section, and the existing replay goldens must PASS
   UNCHANGED; (c) bug fixes that restore intended behavior and
   documentation take a BACKLOG ledger line and no bump. Both bump
   classes keep the rule-12 review-plus-DECISION checkpoint.
6. **Rain DNA.** Rain modeling is the project's value-add — never
   defer it; ship crude-but-directionally-right and label
   uncertainty. Never reason "tide is low, so no flood risk."
   Radar sampling region = the catchment (CATCH_* constants), never
   a house-centered box.
   **No tidal supremacy (John, 2026-09-23):** every surface's headline
   and every "worst case" is the worst across PATHWAYS (tide, the rain
   tank line, a burst scenario), never "the worst tide"; rain floods can
   exceed tidal floods at low tide because the drains' output rate is
   finite. Default views show NOW; "worst tide" and "worst flood
   chance" are separate buttons. Sliders run as far as we predict:
   never gate-keep a horizon we have.
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
   USER-SET CHANNEL ROLES (2026-09-13, not agent discretion to
   "fix"): SMS is the imminent-impact channel — fresh-nowcast
   street impact only, one text per event (re-arm 6h or class
   escalation), single-segment present-tense body, exempt from
   quiet-hours/cap SUPPRESSION (still counts); long-lead watch
   prose is ntfy/email territory (`evaluate_sms_gate`).
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
11. **Edit-batch integrity (6 incidents).** A multi-edit script
    must make the ENTIRE ship chain fail when any edit fails: apply
    all edits in one script that writes only after every anchor
    asserts, never chain regenerate/commit/push as separate
    statements that run regardless, and when a batch is rebuilt
    after a failure, diff it against the failed batch so no edit is
    silently dropped (a dropped listener shipped 2026-09-02; four
    earlier no-op commits carried messages claiming unapplied
    changes). Verify the DEPLOYED artifact, not the edit script's
    claims. In conflict-ritual recoveries, NEVER reapply a change by
    copying a whole saved file over the reset tree — a stale copy
    reverts other landed work invisibly while tests stay green
    (incident #6, 2026-09-02: a saved pre-seam-2 facade copy
    silently un-extracted 3,460 lines under a 2-line commit
    message). Reapply the intended DIFF, then prove file identity:
    `git diff origin/main -- <file>` must show ONLY the intended
    edits before commit.
12. **Audits** (`audits/README.md`): reviewer ≠ author; an open
    report needs an independent reply before close-out; confirm
    criticism of your own work rather than defending it. Before a production
    model promotion, obtain independent review of the candidate and record
    John's approval in a BACKLOG DECISION line; cite both in the promoting
    commit. Existing explicit approval counts; do not ask again for a
    decision already given. A retrospective review or ratification must be
    dated honestly and never described as pre-commit approval.
    **Attribution follows actual participation, never a fixed template.**
    Use `Reviewed-by` only for a completed review covering that work; cite
    the numbered audit artifact (or other primary review record) and its
    scope in the commit body. Audit/planning advice alone is acknowledged
    as such in prose, not as implementation review. Omit reviewer credit
    when no such review exists. `Co-authored-by` credits actual authors;
    use the contributor/model identity established for that session, never
    a previous session's default. Keep Codex's co-author trailer last when
    present. Correct false historical claims with an append-only erratum;
    do not rewrite shared history to manufacture earlier review.

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
