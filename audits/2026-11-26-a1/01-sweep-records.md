<!-- audits/2026-11-26-a1 supporting file for 01-full-audit-claude-fable-5-2.md -->
> **Sweep report: documents, data ledgers and tests (finding IDs DD-n).** Written 2026-11-26 by a read-only
> subagent of the lead auditor's session (Claude Fable 5.2), filed unedited except
> that scratch paths were rewritten to `audits/2026-11-26-a1/01-probes/records/` (scripts only; large
> data dumps were not committed) and, in the records sweep, one line of personal
> context was redacted. It is evidence for report 01, not an independent review:
> the lead re-checked only the items listed in report 01's verification table.

# Slice report: documentation truthfulness, data-ledger integrity, test coverage (2026-11-26)

All work was read-only. `git status --short` was `?? del` before and after every run. Scratch evidence is in `audits/2026-11-26-a1/01-probes/records/`:
- `tests_v.txt` — verbose suite run
- `probe.json` — suite run with the network blocked and repo file access logged
- `prof.json` — suite run under a profiler recording every production function entered

Baseline (RAN): 511 tests OK, 1 skipped; `forecast/check_artifacts.py` reports "publish gate: clean"; `check_observation_episodes.py` reports 37 episodes, 296 indexed rows, 0 needing review.

Row numbers below are CSV line numbers (header is line 1), matching the repo's own convention.

## Findings (ranked)

### DD-1 — Observation ledger has three coexisting correction regimes; its README and enforcing test describe only one
- **Severity: high.** A reader or consumer cannot tell which row is authoritative, and the README states things that are false.
- **Evidence:**
  - `data/labeled_observations_README.md:178` says "Rows are NEVER rewritten"; `:186` says "consumers treat the latest erratum for a row as authoritative".
  - No code reads errata: `grep -rn "ERRATUM\|correction record" forecast/*.py bin/*.py history/scripts/*.py` returns nothing. Row 281 still carries 8.106; its correction (row 282, 8.113) has no machine effect.
  - Regime 1, `ERRATUM`-labelled rows: 157, 158, 176, 177, 186.
  - Regime 2, free-form `landmark_key=none` rows with no `ERRATUM` label: 264–268 and 282. `tests/test_csv_ledgers.py:237` checks only `label == "ERRATUM"`, so these bypass the convention test.
  - Regime 3, in-place edits: commit `ab7e41c59` (13+/17−, rows 285/286/292 edited, 4 rows deleted) and `b0868df37` (2026-08-03, 2+/1−; row 157 itself says "corrected in place this commit").
  - The same day used two regimes: the e01 gauge misentry was left as correction row 282, while e02 errors were edited in place.
  - Row deletion shifted numbering: `assets/observations/2026-11-26/e01/README.md:19` cites "ledger row 297" for the morning recollection, which is now row 296 (297 is the 21:54 e02 reading).
- **Verified:** RAN (grep, row dump, `git log --numstat`). **Confidence:** high.
- **Fix direction:** owner picks one regime; rewrite README lines 176–194 to match, add a machine-readable `corrects` field or sidecar, and extend the test to every `none` row.

### DD-2 — Charter rule 2 names three files, mixes two classes, and nothing enforces append-only
- **Severity: high.** The rule is unenforceable as written and has been contradicted by owner decision.
- **Evidence:** `AGENTS.md:23-26` claims enforcement "by gate + CI (tests/test_csv_ledgers.py)". That test and the gate check only strict CSV shape and semantics; no test or gate compares a ledger with its git history.
- **Inventory of `data/`:**

| File | Class | Named in rule 2 | Should be | Code behaviour |
|---|---|---|---|---|
| `labeled_observations.csv` | primary record | yes | yes, with an entry-error clause | `bin/append_observation.py` uses `O_APPEND`; hand edits happened in 8 commits with deletions (latest `ab7e41c59`) |
| `labeled_events.csv` | primary, frozen legacy | no | yes (frozen) | no writer; no commit with deletions |
| `observation_bounds.jsonl` | derived interpretation keyed to primary rows | no | own clause | append tool, latest record per hash wins; edited in place in `ab7e41c59` (2+/2−) although `check_artifacts.py:570` calls it append-only |
| `predictions_log.csv` | as-issued prediction | yes | yes | `open(...,"a")` at `flood_forecast_daily.py:1277`; `heal_tree.py:79-112` rewrites and sorts it when conflict markers are found |
| `day_risk_log.csv` | as-issued prediction | no | yes | `"a"` at `:1313`; `merge=union` in `.gitattributes` |
| `outlook_log.csv` | as-issued (shadow) | no | yes | `"a"` at `outlook.py:869` |
| `replay_inputs/*.jsonl`, `wind_shadow/*.jsonl` | as-issued inputs / frozen trial log | no | yes | `"a"` at `replay_archive.py:147` |
| `forecast_accuracy.csv` | derived score | yes ("never rewrite") | no; regenerate with old values kept | `"a"` at `:1170`; `history/scripts/rescore_forecast_accuracy.py:280` replaces the whole file (`da16cd11c`, 109+/109−) |
| `observed_peaks_cache.csv`, `observed_peaks_backfill.json`, tide and low-tide caches | derived cache | no | no | `"w"` at `:3278`, `:6522`, `:6594`, `:374` |
| `nowcast_heartbeats.csv` | operational log, rolling 30 days | no | no | rewritten `"w"` at `nowcast.py:208` each tick; `merge=union` |
| `alert_state.json`, `alert_delivery_health.json`, `surge_state.json`, `surge_mean.json`, `outlook_guidance.json` | operational state | no | no | atomic replace |
| `nowcast_daymax_rejections.json` | operator record ("append-only" in its own text) | no | owner's call | hand-edited JSON |
| `merged_hourly.csv`, `floods_by_month*.tsv`, `top10_highest_tides.tsv`, `raw/` | derived analytics / raw pulls | no | no | regenerated by history scripts |

- The largest historical rewrite of `predictions_log.csv` (`97c82674d`, 312+/302−) is CRLF-to-LF normalisation of 302 rows plus 10 appended; content is unchanged.
- **Verified:** RAN and READ. **Confidence:** high.
- **Fix direction:** reword rule 2 by class (primary / as-issued / derived / state) and add a CI check that as-issued and primary files only gain lines relative to the merge base.

### DD-3 — Published "Outcome-depth accuracy" table silently drops every recorded under-prediction
- **Severity: high.** A public skill statement is one-sided by construction.
- **Evidence:**
  - `_load_outcome_depth_rows` (`flood_forecast_daily.py:3208-3238`) keeps a row only if `float(model_predicted_depth_in)` succeeds.
  - Rows 75–94 (2026-07-06) carry `0 (v0.8 predicted dry — architectural gap + QPF miss)` against observed depths up to 10.25 in; all 20 fail the parse and vanish.
  - `docs/details.html` shows "N = 21 … Mean error +5.3″ … mean |error| 5.3″, worst |error| 7.2″". Mean equals mean-absolute, so all 21 errors are over-predictions.
  - The column is numeric in 21 rows (last is row 95, 2026-07-09), free text in 74, and blank after row 183 (2026-09-13). The September storm and both November floods are absent.
  - The function is never entered by any test (`prof.json`).
  - The page note (`rendering.py:812-821`) discloses "history, not current-model skill" but not the exclusion.
- **Verified:** RAN. **Confidence:** high.
- **Fix direction:** retire the block, or compute predicted depth from archived as-issued values instead of a hand-typed column.

### DD-4 — "Six measured peak anchors" counts two reconstructions; the wording is published and pinned by a test
- **Severity: medium.** A rule-4 provenance breach on the landing page and in the spec.
- **Evidence:**
  - `model/v0.10.6.md:446-447` lists December 19 and October 30, 2025 among "Measured peak anchors: six", and `:449` reuses the same two as "Independent peak checks".
  - Ledger rows 51–52 (2025-12-19) say "Reconstruction from model/archive/v0.4.md language", with depth pinned mid-band.
  - Rows 49–50 (2025-10-30) are a photo plus tide-decay reconstruction. Row 186 withdraws the "floor" reading; row 266 records the owner saying the evidence was memory and post-peak photos.
  - The phrase is in `flood_forecast_daily.py:7074`, rendered once in `docs/index.html`, and asserted by `tests/test_model_reproduction.py:54,70,71`. The fixture is `model/data/v0.10.1-reproduction.json:178`.
  - BACKLOG scientific follow-up (1) already calls the Oct 30 peak "a reconstruction, not an observed validation hit".
- **Verified:** READ and RAN (grep count). **Confidence:** high on the wording conflict; I did not assess the effect on calibration.
- **Fix direction:** rename the category (for example "four measured, two reconstructed") in spec, renderer and test together; the frozen fixture can keep its key with a note.

### DD-5 — As-issued ledgers are appended by any local run, carry no provenance, and their writers are untested
- **Severity: medium.** A manual regeneration can add non-production rows to the "as-issued" record, and a writer regression would reach production unseen.
- **Evidence:**
  - `_main_core` appends unconditionally at `flood_forecast_daily.py:8628-8633` (predictions, day-risk, outlook); the scorer runs inside `build_forecast` (`:3075`). `--no-send` and `--dry-run` do not gate either.
  - `PLAYBOOK.md:102-105` instructs exactly such a local run with no warning. BACKLOG line "landmark-bounds-ship" shows the convention is manual: "local-run ledger appends not committed, as before".
  - `predictions_log.csv` has no arm, run or official column, unlike the wind-shadow log (`wind_shadow.py:594-602`).
  - `append_predictions_log` (88 lines) and `append_day_risk_log` (30) are never entered by the suite (`prof.json`).
  - The BACKLOG loop "Writer/validator parity" (`BACKLOG.md:312-316`, opened 2026-09-20, 67 days) is accurately still open.
- **Verified:** RAN and READ. **Confidence:** high. Whether any local-run row was ever committed: not determined.
- **Fix direction:** skip ledger appends unless the run is official, or add a provenance column; add round-trip tests for both writers.

### DD-6 — Page renderers and the production entry point are never executed by tests
- **Severity: medium.** A rendering or orchestration bug passes CI and first shows as a failed production publish.
- **Evidence (`prof.json`, 511 tests):** never entered:
  - Entry point and publishing: `_main_core` (288 lines), `write_per_tide_pages`, `_write_tides_archive_index`, `_atomic_write_text`, `send_email`.
  - Rendering: `rendering.render_html_page` (487), `render_per_tide_page` (417), `render_details_page`, `_render_flood_peaks_section` (431), `_render_oscillation_section` (285), `_client_map_section_html` (668), `_render_equation_widget_html` (377).
  - Public skill numbers: `_summarize_accuracy` ("last 30"), `_compute_leadtime_accuracy` (by-lead), `_load_accuracy_rows`, `_load/_save_observed_peaks_cache`, `_fetch_actual_peak_around` (always mocked).
  - State and tooling: `_refresh_alert_state_from_origin` (53), `history/scripts/check_observation_episodes.py::validate`, `bin/append_observation_bound.py::main`.
  - In `flood_forecast_daily.py`, 59 of 166 functions (3,336 of 7,895 function lines) are never entered.
  - `tests/test_html_accessibility.py` reads the committed `docs/*.html`, `docs/forecast.json` and `docs/tides/*` instead of rendering.
- **Verified:** RAN. **Confidence:** high for "never entered"; a function entered once is not thereby well tested.
- **Fix direction:** one offline end-to-end test that calls `_main_core` with stubbed fetchers into a temp directory and runs the gate on the output.

### DD-7 — Two public skill surfaces score the same tide against different "observed" values
- **Severity: medium.** The peaks cache freezes preliminary gauge readings permanently, and tonight's noisy crest will be frozen the same way.
- **Evidence:**
  - `data/observed_peaks_cache.csv:252` has `2026-09-26 08:01-04:00,8.667`.
  - `data/forecast_accuracy.csv:123-124` has 8.805 for the same tide (the verified value per BACKLOG FACT `sep26-verified-bay-peak`).
  - A join of 182 tides finds 2 that differ (4 ledger rows): this one (0.138 ft) and 2026-07-09 15:39 (6.18 vs 6.228).
  - The code comment at `flood_forecast_daily.py:3250-3252` says "old entries never expire".
  - `2026-11-26 08:28-05:00,8.267` is already cached as preliminary.
- **Verified:** RAN. **Confidence:** high.
- **Fix direction:** store a quality flag and retrieval time with each cached peak and refresh unverified entries after NOAA verification.

### DD-8 — `model/elevations.md` is cited as the survey source but does not source 6 of the 18 landmarks and contradicts itself
- **Severity: medium.** Band provenance and PLAYBOOK step 3 point at a document that cannot back the numbers.
- **Evidence:**
  - Sourced tables (`:49-100`) have no row for `grate_SW` 3.52, `grate_SE` 3.60, `grate_NE`/`grate_NW` 3.80, `grate_bay_ave_upstream` 3.64 or `sidewalk_under_walkway_lawn_step` 4.33. These appear only in the derived "what gets wet" table (`:113-129`).
  - `:100` gives the corner storm grate as "3.91–4.22"; `:120`, the code (`GRATE_NE = 3.80`) and `assets/map_points.csv:9` say 3.80.
  - `data/observation_bounds.jsonl` cites `"source": "model/elevations.md"` for `grate_SW` 3.52 and `sidewalk_under_walkway_lawn_step` 4.33.
  - The open discrepancy (crossing 4.37 vs curb 4.16) is absent from the file. 4.37 exists only as `central_north_middle_1` (`assets/map_points.csv:28`); the alternate intersection value 4.51 only as `intersection_center` (`:23`) against 4.54 in code.
  - No entry exists for the second porch step (derived 6.08 from `assets/porch-measurements.txt`, which has no date, author or method), the garage floor, or the tide gate.
  - `:149` still lists the "events we've modeled" as of spring.
  - AGENTS.md:5 and the spec (`model/v0.10.6.md:379`) say "18 surveyed landmarks", but the same file marks lawn step and porch ladder as cross-fit or taped.
  - BACKLOG OPEN `central-crossing-vs-curb-inconsistency` (2026-09-27, 60 days) has no next step beyond "needs a field re-check of both".
- **Verified:** READ and RAN. **Confidence:** high.
- **Fix direction:** one sourced row per landmark (survey / cross-fit / taped, with date), a "disputed / unsurveyed" section, and correct "surveyed" to "reference" in the charter.

### DD-9 — BACKLOG OPEN LOOPS: done items listed open, duplicates, stale pointers
- **Severity: medium.** The file declared authoritative misstates what is unfinished.
- **Done or overtaken but still `[ ]`:**
  - `:333-337` "Re-copy deployed widget source v7.32a": superseded; ledger FACT `widget-v7.35a-owner-copied` (2026-09-28).
  - `:390-392` and `:524-528`: two WATCH items for the same `nowcast.yml` dispatch path, both "until the next radar trigger". Triggers occurred 2026-10-11 and 2026-11-12, found two defects, fixed 2026-11-17 (`9f36fca41`).
  - `:430-441` passive collector (c): the 2026-11-26 FACT `storm-tide-skill-by-era` already scores the NWS product (n=12).
- **Stale pointers:**
  - `:20` "The third is the next item": the next item is now the 2026-11-26 queue, and the third defect is fixed at `:77`.
  - `:14` and `:227` "Heron checkpoint: October 9" (see DD-10).
  - `:359-360` still cites the "duration-explicit V=C·(R−D)·T upgrade" that `PLAYBOOK.md:85-87` declares obsolete.
  - `:269` cites `history/plans/2026-09-24-social-broadcast/28-codex-repair-closeout.md`, which is not on main.
- **Duplicates:**
  - Borough inquiry appears three times (`:61-63`, `:425`, ledger line 870).
  - Storm-communication parity (`:138`) overlaps the "one day-headline across arms" item in the new queue (`:23-31`).
- **No owner or next step:** `:426` SMTP migration; `:462` peaks-chart A/B (since 7/07, 142 days); `:551` tanh placeholder.
- **Ledger OPEN lines:** 47 exist; 41 have no later line under the same topic. Several are plainly done (v0.10.5 audit hold, v0.10.6 review, the wind-shadow reviews, `event-#10-gate-photo`, which was committed 2026-11-10).
- **Older than 60 days with no recorded movement (development is paused by owner choice since 2026-09-28):**
  - Ledger: `event-#7-analysis` (08-07), `model-session-menu` (08-09), `writer-validator-parity` (09-20), `rain-flood-retrospective-low-tide-assumption`, `compound-validation`, `conditional-surge-decay-research` (09-23), `event-#10-study`, `event-#10-rain-attribution`, `event-#10-infrastructure-inquiry` (09-26), `ledger-metadata-rows`, `gauge-ingest-no-battery-check`, `central-crossing-vs-curb-inconsistency` (09-27).
  - OPEN LOOPS: durable outbox, town-map features, antecedent wetting, stateless tank window, surge-tendency candidate, `edge_20260901` and `edge_20260913` clicks, ponding-dip drive, datum line, script split.
- **Verified:** READ, plus a scripted topic scan. **Confidence:** high on the listed items; "no movement" means no ledger line, not that nobody thought about it.
- **Fix direction:** one sweep — tick the done items, merge duplicates, and give every remaining loop an owner and a next trigger.

### DD-10 — Two dated obligations lapsed with no record
- **Severity: medium.** The trial and evaluation cannot close if nobody is prompted.
- **Evidence:**
  - Heron checkpoint 2026-10-09 (`history/plans/2026-09-25-heron-validation-checkpoint.md:6`): there are no ledger lines at all between 2026-09-28 and 2026-11-10, and none mention it after. Three flood episodes have occurred since (2026-11-12-e02, 2026-11-26-e01 and e02).
  - Wind-shadow trial minimum "60 days AND five eligible scored completed storms" (`audits/2026-09-24-a3/07-close-out-codex.md:78-81`): it started at the 2026-09-24 16:00Z slot, so 60 days elapsed on 2026-11-23. No count of storms is recorded. Collection continues (`data/wind_shadow/2026-11.jsonl`, 628 records).
  - `episodes.json` has `storm_id: null` for all four November flood and check episodes, although HANDOFF says the two 2026-11-26 floods are one storm.
- **Verified:** READ and RAN. **Confidence:** high that nothing is recorded; whether five storms qualify is not determined.
- **Fix direction:** ledger line for each (met / not met / rescheduled) and assign storm IDs for November.

### DD-11 — Seven post-September reports have neither a depth nor a band; episode 2026-11-26-e01 has no machine-readable level
- **Severity: medium.** PLAYBOOK says every report yields an exact or banded level and to ask the owner otherwise (`PLAYBOOK.md:139-146`).
- **Evidence:** rows 274, 276, 278, 279, 280, 281 and 296 have an empty `observed_depth_in` and no record in `observation_bounds.jsonl`.
  - Row 275, the same kind of negative report, did get a band (≤ 3.52).
  - Row 296 ("about the level of the lawn step") is the only crest evidence for e01.
- **Verified:** RAN. **Confidence:** high.
- **Fix direction:** add bands for the computable rows (negatives ≤ 3.52; presence ≥ a grate) and ask the owner about row 296.

### DD-12 — `labeled_observations_README.md` describes a schema the ledger no longer has
- **Severity: low-medium.** Misleads anyone logging or reading rows.
- **Evidence:**
  - `:45` and `:57` give `lowest_road_corner` as a key; it is not in `LANDMARKS`.
  - `:47` says "eye-estimated"; `:50` says "what the v0.5 model predicts".
  - `:130` says "Four keys live only here"; six non-model keys are in use: `driveway_central` ×6, `pocket_SE_retention` ×5, `tide_gate_snug_harbor` ×5, `fire_hydrant_central` ×4, `porch_step` ×1, `garage_floor` ×1. The gate key and the garage key are undocumented.
  - `landmark_label` is empty in 100 rows, including every row since 274.
  - `sh_obs_mllw_actual` and `weather_in_window` have no reader in `forecast/`, `bin/` or `history/scripts/`.
- **Verified:** RAN and READ. **Confidence:** high.
- **Fix direction:** rewrite the Columns and Non-model keys sections from the file as it is.

### DD-13 — `predictions_log_README.md` drift, and five ledgers have no README
- **Severity: low-medium.**
- **Evidence:**
  - `:5, 15, 17, 19, 29, 84` cite "HANDOFF 9b.x" sections that now exist only in `attic/HANDOFF-through-2026-08-03.md`. The same dangling references appear 33 times in `flood_forecast_daily.py` and 19 in `rendering.py`.
  - `:88` says `forecast_accuracy.csv` "stays frozen"; it gains a row daily (183 rows, last run date 2026-11-25) and was rescored.
  - `:62` says "never rewrite or sort"; `heal_tree.py:106` sorts by key, and the file is not in key order now (line 15084 goes back from 03:16Z to 00:13Z).
  - `:48` describes negative `hours_until_peak`; the minimum in 24,419 rows is 0.0.
  - `:57` gives `high/medium/low`; the column has been blank since 2026-09-24 (8,916 rows).
  - `cold_lockout` is `false` in every row.
  - `:40` says about 2 rows per run; the last 200 runs wrote 5 or 6.
  - No README exists for `outlook_log.csv`, `nowcast_heartbeats.csv`, `forecast_accuracy.csv`, `observed_peaks_cache.csv` or `observation_bounds.jsonl`.
- **Verified:** RAN. **Confidence:** high.
- **Fix direction:** refresh the column table and add a short `data/README.md` index with one paragraph per file.

### DD-14 — SMS retirement did not reach every arm; other top-level statements are stale
- **Severity: low-medium.**
- **Evidence:**
  - `README.md:17` still says "optional email-to-SMS alerts fire". The ship line `sms-retired-and-dispatch-fixed` claims a grep found no surface naming SMS as live.
  - `.github/workflows/daily_forecast.yml:75` has the comment "ntfy/email/SMS", and `:89` still passes `ALERT_SMS_TO`.
  - `AGENTS.md:77` lists SMS among the alert channels before the retirement paragraph.
  - `README.md:51` says the widget is "v7.28a as of 2026-09-18"; `docs/barnacle-widget.js:42` is v7.35a.
  - `assets/observations/README.md:7` "Current witnessed-flood benchmark — updated 2026-09-27" names 5.70 ft as the benchmark and tells readers to consult it; tonight's 6.08 supersedes it. `:52` counts 35 episodes; there are 37.
  - `HANDOFF.md:3` is stamped 21:55 EST but describes the 22:06 corrections (commit `ab7e41c59` at 22:07).
- **Verified:** READ. **Confidence:** high.
- **Fix direction:** fix the listed lines and add README.md to the rule-8 arm list for channel changes.

### DD-15 — Rule 5 change class for the SMS retirement is ambiguous; three production commits since the stopping point have no independent review
- **Severity: low-medium.** A charter ambiguity, not a proven violation.
- **Evidence:**
  - `AGENTS.md:57-61`: "alert-policy changes ALSO bump … keep the rule-12 review-plus-DECISION checkpoint".
  - `9f36fca41` (2026-11-17) removed a channel and made the radar alert check run on every scheduled run. It shipped as class (c), no bump (`model/v0.10.6.md:323-326` gives the reasoning). An owner DECISION exists; no review does.
  - `988e8197c` and `da16cd11c` (2026-11-10) are class (c) too. `audits/` has no folder after 2026-09-27-a1; `git log` shows no `Reviewed-by` on the three.
- **Verified:** READ and RAN. **Confidence:** high on the facts; the classification is the owner's call.
- **Fix direction:** state in rule 5 whether removing a channel or changing dispatch cadence is class (b), and have the current audit review the three commits.

### DD-16 — CI runs the same command but not the same checks
- **Severity: low.**
- **Evidence:**
  - The command matches (`ci.yml`: `BARNACLE_REQUIRE_GRIB=1 python -m unittest discover -s tests -q`). CI and both GitHub workflows use Python 3.11; the local venv and the launchd production arm use 3.15.2.
  - Node is not provisioned in CI. Widget tests guard on `shutil.which("node")` (`test_widget_sofar.py:52`, `test_bounds_round16.py:84`, `test_observation_bounds.py:180`, `test_report_end_to_end.py:20`) and would skip, not fail.
  - `test_wind_shadow.py:514` (R5-Q1) skips whenever the git-ignored parquet is absent, so it never runs in CI and did not run here.
  - `test_py311_syntax.py:51,59` skip on 3.11.
  - `ci.yml:5` says generated bot commits stay quiet, but local-arm pushes trigger CI (run for `bf81d6726`, "nowcast … (local tick)"). With `cancel-in-progress`, the run for human commit `f5e227809` was cancelled.
  - `test_wind_shadow.py:340-353` writes a truncated `zz-gate-probe.jsonl` into the real `data/wind_shadow/` and runs the whole gate against the live tree.
  - `check_observation_episodes.py` is in neither CI, the gate, nor any test.
  - `tests/test_csv_ledgers.py:255` has `unittest.main()` above its last test class, and running the file as a script fails with `ModuleNotFoundError`. `python3 -m unittest tests.test_csv_ledgers` works (22 tests).
  - No test touched the network: all 511 pass with sockets blocked (`probe.json`).
- **Verified:** RAN. **Confidence:** high.
- **Fix direction:** add `BARNACLE_REQUIRE_NODE`, run the episode checker in CI, and point the gate test at a temp root.

### DD-17 — Personal data to review (file and line only, not quoted)
- **Severity: low.** Owner's judgement.
- **Evidence:**
  - An email address inside a User-Agent string: `forecast/nowcast.py:55`; `assets/observations/2026-09-27/analysis/fetch_event_gauges.py:24`; and in `history/scripts/`: `fetch_noaa_compound_head_fixture.py:25`, `fit_wind_shadow_c2.py:78,96`, `mrms_point_rain.py:67`, `nowcast_tank.py:28`, `pull_gfs_single_runs.py:19`, `pull_sandy_hook_history.py:38`, `pull_sandy_hook_history_utc.py:23`, `pull_sandy_hook_met.py:30`, `pull_surge_forecast_test_data.py:31`. At least six look like a personal address; I did not confirm each.
  - A named Borough official's work email: `model/elevations.md:165`, `model/archive/v0.5.md:284`, `model/archive/v0.6.md:285`.
  - One further item of personal context was reported to the owner directly and is not listed in this public file (redacted by the lead auditor).
  - No phone numbers found (the only pattern hits are NWS zone codes). No note of an unblurred face. No tracked `*-original-unpublished.*` file.
- **Verified:** RAN (pattern scan of tracked text). **Confidence:** medium; photos were not inspected.
- **Fix direction:** the owner decides; if the address should go, read it from the `USER_AGENT` environment variable as `flood_forecast_daily.py:186` already does.

### DD-18 — PLAYBOOK drift and every PENDING marker with its age
- **Severity: low.**
- **PLAYBOOK drift:**
  - `:88-90` saves plots to `YYYY-MM-DD/analysis/`, but episode homes are `YYYY-MM-DD/eNN/` (`:113-118`).
  - `:75-76` gives a hand-built venv recipe, superseded by `bin/ensure_local_venv.sh`.
  - `:123` "run tests/test_csv_ledgers" does not say how (see DD-16).
  - `:5` says "battle-tested on events #4–#6".
- **PENDING markers:**
  - `assets/observations/2026-09-26/README.md:12` "analysis PENDING" — 61 days; points at three OPEN ledger topics with no closing line.
  - `assets/observations/2026-09-27/README.md:48` "Pending: rain check…; the event-wide study" — 60 days.
  - `HANDOFF.md:72` widget native readability — 59 days.
  - `assets/observations/2026-11-12/e02/README.md:73` gauge pull, rain, plots — event 14 days ago, noted 9 days ago.
  - `assets/observations/2026-11-26/e02/README.md:98` — today.
  - `assets/observations/2026-11-26/e01/README.md` has "OPEN:" but no PENDING line, which checklist item 5 (`PLAYBOOK.md:156-158`) requires.
- **Verified:** READ and RAN (grep). **Confidence:** high.
- **Fix direction:** align steps 5 and 7 with the current layout and close or re-date the two September PENDINGs.

## Checked and found sound
- **`observation_bounds.jsonl`:** 32 lines, 22 distinct row hashes, every hash matches a current ledger row at the stated `csv_row`; no drift (strict and hash locators both clean).
- **Episode registry:**
  - All 37 episodes have a directory, an episode README, a date README and an `EPISODES.md` entry.
  - All 285 associated rows match by hash; the 11 excluded rows are exactly the `none` rows; none is unassigned or double-assigned.
  - `indexed_through_csv_row` is 297, the last line.
- **Observation timestamps:** rows 2–264 are naive, 265–297 offset-bearing, with no naive row after the first offset row and none unparseable. No exact duplicate rows, no duplicate (time, landmark) keys, no non-numeric depths.
- **Implied levels:** the highest is row 293 (5.41 + 8.0 in = 6.08 ft); its note says the depth is derived. Cross-landmark disagreements within 3 minutes occur only in fast pluvial rises (rows 99–101, 172–173, 240–242).
- **`predictions_log.csv`:** 24,419 rows, no duplicate keys, one UTC format. `water = sh − 2.82` fails only for the 2,896 v0.6/v0.7 rows, as the enhancement history predicts. The longest gap since late July is the known 42-hour outage of 2026-09-19/20.
- **`forecast_accuracy.csv`:** 183 rows, no duplicate run dates, every row has an archive, and no observed time lies more than 1.5 h from the predicted peak. The nine missing run dates have no archive file.
- **`day_risk_log.csv`, `outlook_log.csv`, `nowcast_heartbeats.csv`:** no duplicate keys; the GitHub arm has no heartbeat gap over 90 minutes since 2026-11-10.
- **Charter references:** rule numbers cited across docs and code match AGENTS.md 1–12. Every symbol and CLI flag the charter and PLAYBOOK name exists (`evaluate_sms_gate`, `IMMINENT_CHANNELS = ("ntfy",)`, `ALERT_DAILY_CAP`, `CATCH_*`, `--write-html/--write-json/--no-send`, the station-time helpers, the clock hook in `.claude/settings.json`).
- **Paths:** every path cited in AGENTS, HANDOFF, PLAYBOOK, README, the spec and the data READMEs exists; the only miss is `BACKLOG.md:269`.
- **Landmarks:** 18 in code, spec, HANDOFF and README; code elevations equal `assets/map_points.csv` for all 18.
- **Audits:** all 11 folders have an independent reply and a close-out; no `01-` report is unanswered. Close-out residuals for 2026-09-14-a1, 2026-09-24-a1 and 2026-09-27-a1 are tracked in OPEN LOOPS.
- **BACKLOG ledger:** one date-order inversion (line 938) and no ledger line deleted or edited since 2026-09-01.

## Could not determine
- **`forecast/nowcast.py` test coverage.** A privacy control declined a static-analysis script that named that file, so its never-entered function list is missing. I did not work around it.
- **Local-run rows in the as-issued ledgers.** Whether any was ever committed; the file has no provenance column.
- **Wind-shadow storm count.** Whether five storms now qualify.
- **Second-step riser.** Whether it is 8 in where the owner reads; the 21:00 "approx 7 in, almost level" note suggests slightly less. Owner measurement is open.
- **The 4.37 vs 4.16 discrepancy.** Which value is wrong needs a field check.
- **Local-arm heartbeat gap, 2026-11-26 16:51Z–20:28Z (11:51–15:28 EST, between the two floods).** I saw it but did not establish whether the Mac was asleep.
- **Photo privacy.** I did not view images, so rule-9 compliance of committed photos is unverified here.
