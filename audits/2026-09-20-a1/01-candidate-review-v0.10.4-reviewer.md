# 01 — Candidate review: v0.10.4 (driveway_central removed from the landmark ladder)

**Author:** Independent reviewer agent (Claude, cold-context subagent) — not the candidate's author.
**Status:** OPEN — round 01; awaiting the author's `02-` reply per `audits/README.md`.
**Reviewed:** branch `v0.10.4-candidate`, commit `a7369fef8` (parent `11d6746f0` = the BACKLOG DECISION commit, 2026-09-20 20:10:41 EDT; candidate 20:15:10 EDT). `origin/main` at review time = `11d6746f0` (0 commits ahead).
**Date:** 2026-09-20.
**Method:** all commands run by the reviewer in the review worktree; no file other than this one was created or modified (`git status --short` clean after every run).

---

## VERDICT: PROMOTE WITH FIXES

The technical claim verifies: both frozen replays PASS, the only code hunks are the driveway constant / row / label and the version stamp + one comment, 170 tests OK, gate clean, every regenerated arm shows 18 rungs and no driveway key, ledgers are append-only, `alert_state.json` is byte-identical. What is NOT done is the documentation lockstep on three current-state surfaces. Required in (or before) the promoting commit:

1. **HANDOFF.md** — rewrite (AGENTS registry: "every ship — REWRITE WHOLESALE"). It currently says 19 landmarks, model v0.10.3, widget v7.28a, and "`driveway_central` is the 4.67-ft cross-fit corner-stage threshold" (F1).
2. **data/labeled_observations_README.md** — line 6 links the moved spec `model/v0.10.3.md` (dangling); line 58 still says "the current 19" (F2).
3. **BACKLOG.md** — open loop line 20 still says re-copy widget **v7.28a**; must say v7.29a. Add the DONE ledger line for the promotion citing this review and the DECISION line (F3).
4. **history/scripts/reproduce_v0_10_3.py** line ~150 — hard-coded `verification: PASS (production v0.10.3)` contradicts its own first line under the new stamp (F4). One-line fix.

Items 5–11 below are LOW / residual and do not block.

---

## Findings

### F1 — HANDOFF.md untouched; asserts the pre-candidate state as current. **Severity: MUST FIX (lockstep).**
- Not in `git diff origin/main..HEAD --stat` (42 files; HANDOFF absent). Commit body lists "README, AGENTS, ledger README, predictions-log README, event READMEs and the v0.11 plan" — HANDOFF is not claimed, and not done. Snapshot line reads `2026-09-20 18:30 EDT`, i.e. before the 19:07 decision.
- Evidence (`grep -n "v0.10.3\|19 landmark\|driveway\|v7.2" HANDOFF.md`):
  ```
  9:NWS + MRMS produce depth at 19 landmarks, hourly site/JSON, best-effort
  11:Model **v0.10.3** (`model/v0.10.3.md`). SMS carries imminent street impact;
  57:- Widget source v7.28a needs John to re-copy into Scriptable; installed
  59:- `driveway_central` is the 4.67-ft cross-fit corner-stage threshold;
  60:  `driveway_road_central` is the separate 4.11-ft map-topography point.
  98:ledger writer (BACKLOG). Owner: widget v7.28a re-copy; external trigger PAT.
  ```
- Why it matters: HANDOFF is the second document in the cold-start read order; line 59 states the exact proposition v0.10.4 retracts, and line 11 is a dangling path once `model/v0.10.3.md` is archived. `tests/test_model_version.py` checks README and the predictions-log README for the stamp but not HANDOFF/AGENTS/PLAYBOOK — which is how this slipped (see F11).

### F2 — Ledger README: dangling spec link and stale "current 19". **Severity: MUST FIX (rule 5).**
- `data/labeled_observations_README.md:6`: `refine the flood model (current spec: \`model/v0.10.3.md\`).` — file now lives at `model/archive/v0.10.3.md`.
- `data/labeled_observations_README.md:58`: `…see LANDMARKS in \`forecast/flood_forecast_daily.py\` for the current 19` — the author edited the very next line (the parenthetical) and left "19" on the context line above it.
- The rest of the README's driveway treatment is correct (see checklist 7).

### F3 — BACKLOG not updated for the widget bump / candidate. **Severity: MUST FIX at promotion.**
- `git diff origin/main..HEAD -- BACKLOG.md | wc -l` → `0`.
- `BACKLOG.md:20`: `- [ ] Re-copy widget source v7.28a into Scriptable.` — widget is now `v7.29a` (`docs/barnacle-widget.js:42`). Rule 8: every widget edit requires John to re-copy; the OPEN loop is the vehicle that tells him which version.
- No DONE/FACT line exists for the candidate work. Acceptable for a CANDIDATE commit, but the promoting commit must add the ledger line and cite this artifact (`audits/2026-09-20-a1/01-…`) plus the DECISION line (rule 12).

### F4 — `reproduce_v0_10_3.py` prints a self-contradicting PASS line. **Severity: MEDIUM (honesty of a reproduction record).**
- Output under HEAD:
  ```
  v0.10.4 production fill: reference error 1.07e-14 in; maximum production correction 0.090 in
  …
  verification: PASS (production v0.10.3)
  ```
- Source: the final `print("verification: PASS (production v0.10.3)")` is a literal; the first line uses `result['model_version']`. Fix: print the fixture version as "fixture v0.10.3" or interpolate the stamp.

### F5 — Two assertions became tautologies; lineage guard is permanently satisfied. **Severity: LOW (test weakening, documented by the author's own comment).**
- `tests/test_model_assessment.py:87` and `tests/test_model_reproduction.py:21` now assert `result["model_version"] == ff.CURRENT_MODEL_VERSION`; both replay functions return exactly `ff.CURRENT_MODEL_VERSION` (`reproduce_v0_10_1.py:345`, `reproduce_v0_10_3.py` return dict). They cannot fail. The literal pin survives only in `tests/test_model_version.py:13` (`"v0.10.4"`).
- `reproduce_v0_10_3.py` (new) and `reproduce_v0_10_1.py:295-308` (pre-existing, v0.10.2) accept any future stamp so long as `model/archive/<fixture-version>.md` exists — which is now permanently true for both. The constants-equality and hindcast checks remain the real guards, as the comment says; but the "undocumented restamp" error path is now unreachable. Suggest also requiring `model/{ff.CURRENT_MODEL_VERSION}.md` to exist (mirrors `test_current_spec_and_readmes_match_source_stamp`), or drop the two tautological asserts.

### F6 — Spec wording and pre-dated promotion date. **Severity: LOW.**
- `model/v0.10.4.md:46-47`: "Eighteen surveyed landmarks, ascending, unchanged from v0.10.1 except for the removal above" — relative to v0.10.1 nothing was removed; v0.10.1 had exactly these 18 (`model/archive/v0.10.2.md:5`: "the existing 18 landmarks is identical to v0.10.1"). Say "identical to the v0.10.1 ladder (the v0.10.2 addition reverted)".
- `model/v0.10.4.md:3` asserts **Promotion date: 2026-09-20** before promotion. Rule 3: the promoting agent must confirm the calendar date at promotion time (it was 20:15 EDT at commit; a post-midnight promotion makes this false).

### F7 — Two event READMEs still call 4.67 the "model threshold" in the present tense. **Severity: LOW (historical narration, but reads as current).**
- `assets/observations/2026-06-15/README.md:114`: "…renamed 2026-09-18 to distinguish the 4.11-ft road point from the 4.67-ft model threshold".
- `assets/observations/2026-06-14/README.md:217`: "…renamed 2026-09-18 to distinguish it from the 4.67 flood threshold".
- Both narrate the 09-18 rename, so classification (a) is defensible; an appended "(removed v0.10.4)" would remove the ambiguity. The author did update 2026-08-27 and 2026-09-13 READMEs but not these two.

### F8 — `LANDMARK_SHORT_LABELS` lacks `sidewalk_under_walkway_lawn_step`. **Severity: LOW, PRE-EXISTING (not caused by this candidate).**
- HEAD: 17 labels / 18 landmarks. origin/main: 18 labels / 19 landmarks (same key missing). `.get(key, key)` falls back to the raw key in the compact per-tide table and the highest-exceeded strip (`flood_forecast_daily.py:1400, 3286`) if that rung is ever the highest exceeded. Queue as a separate loop; do not fold into v0.10.4.

### F9 — Stale workflow comment. **Severity: LOW, PRE-EXISTING.**
- `.github/workflows/nowcast.yml:8`: "run the v0.10.2 tank" — stale since v0.10.3. Comment only.

### F10 — Candidate carries pre-promotion regenerated surfaces and ledger rows stamped v0.10.4. **Severity: LOW (ship mechanics / stamp honesty).**
- `data/predictions_log.csv` +6 rows at `2026-09-21T00:13:35Z` stamped `v0.10.4`; `data/day_risk_log.csv` +1 row at `2026-09-21T00:13:30Z` stamped `v0.10.4`; `docs/forecast.json`, `docs/index.html`, `docs/details.html`, six `docs/tides/2026-09-2*/` dirs, `docs/tides/index.html`, `data/tide_predictions_cache.json` regenerated in the worktree.
- Bots on `main` keep appending `v0.10.3` rows with later timestamps until promotion; after UNION merge the log will hold v0.10.4 rows time-ordered before later v0.10.3 rows. Numerically harmless (identical outputs) but rule 5 says document mis-stamps honestly: the promoting BACKLOG line should say these rows came from the candidate's no-send regeneration, or (better) drop them and regenerate on the rebased tree at promotion via the rebase-with-gate ritual.

### F11 — Test coverage gap that let F1 through; cosmetic. **Severity: LOW.**
- `tests/test_model_version.py::test_current_spec_and_readmes_match_source_stamp` checks `README.md` and `data/predictions_log_README.md` only. Extend to `HANDOFF.md`, `AGENTS.md`, `PLAYBOOK.md` (`model/{version}.md` pointer) and to `data/labeled_observations_README.md` — three of those four are stale or dangling in this candidate.
- `docs/barnacle-widget.js:47` comment now ~120 chars wide; cosmetic.

---

## Checklist (per the review brief)

### 1. Numeric identity — **PASS**
```
$ python3 history/scripts/reproduce_v0_10_1.py
v0.10.1 frozen production vector (current production stamp v0.10.4): K=1296000, gamma=0.78, k_out=3.50/h, lag=15 min
fit replay: RMS 1.316778 in over 24 points (reported 1.32 in)
jul6 +14.6 @11:38 · jul9 +19.0 @16:14 · oct30 +20.9 @15:24 · dec19 +14.2 @07:34 (obs-time +11.0) · jul18 +15.8 @15:50 · aug3 +13.4 @10:42
verification: PASS (read-only; no production files written)          EXIT=0

$ python3 history/scripts/reproduce_v0_10_3.py
v0.10.4 production fill: reference error 1.07e-14 in; maximum production correction 0.090 in
jul6 +14.578 · jul9 +18.972 · oct30 +20.943 · dec19 +14.254 · jul18 +15.850 · aug3 +13.423
verification: PASS (production v0.10.3)                              EXIT=0   ← string stale, see F4
```
`git diff origin/main..HEAD -- forecast/flood_forecast_daily.py` = exactly 5 hunks: (a) `-DRIVEWAY_CENTRAL = 4.67` + its continuation comment; (b) `-("driveway_central", "Driveway-entry threshold [cross-fit]", DRIVEWAY_CENTRAL, 7.49)`; (c) comment `currently v0.10.3` → `v0.10.4`; (d) `CURRENT_MODEL_VERSION = "v0.10.3"` → `"v0.10.4"`; (e) `-"driveway_central": "Driveway-entry threshold [cross-fit]"` in `LANDMARK_SHORT_LABELS`. No tank constant, `_pluvial_fill`, stage-curve, or pathway hunk. `len(ff.LANDMARKS) == 18`; key order verified ascending. `forecast/rendering.py`: no diff.

### 2. Rule-5 lockstep — **PASS with two misses (F1, F2)**
- `model/v0.10.4.md` exists; title `Flood Prediction Model v0.10.4`.
- `model/v0.10.3.md` → `model/archive/v0.10.3.md` (git rename, similarity 95%); four relative links repaired (`v0.10.2.md`, `../../history/scripts/reproduce_v0_10_3.py`, `../data/v0.10.3-reproduction.json`, `v0.10.2.md`).
- `python3 -m unittest tests.test_document_links -v` → `test_repaired_local_markdown_links_resolve … ok` (paths list now includes `model/v0.10.4.md` and `model/archive/v0.10.3.md`).
- `CURRENT_MODEL_VERSION == "v0.10.4"`; `check_artifacts.source_model_version()` agrees (test passes).
- `data/predictions_log_README.md:58` stamp sentence updated (v0.10.4 since 2026-09-20; 18 landmarks; historical rows retain v0.10.3 and earlier).
- README (`18 named landmarks`, `model/v0.10.4.md`), AGENTS (`18 surveyed landmarks`, `model/v0.10.4.md`), PLAYBOOK step 1 (`model/v0.10.4.md`) updated.
- MISSES: HANDOFF.md (F1); `data/labeled_observations_README.md:6` dangling `model/v0.10.3.md` and `:58` "current 19" (F2).

### 3. Rule-8 parallel arms — **PASS on every generated/code arm; two prose arms stale (F1, F2)**
Grep: `driveway_central|DRIVEWAY_CENTRAL` and `19 landmark|19 named|(19 as of|nineteen|19 surveyed|19-landmark|19 rung` over the worktree excluding `.git attic/ model/archive/ docs/archive/ audits/ history/` and the two append-only CSVs. Every hit, classified:

| Hit | Class |
|---|---|
| `BACKLOG.md:194` (closed checkbox 2026-09-03), `:321`, `:323`, `:328`, `:359`, `:376` | (a) ledger rows / closed loop describing the past truthfully |
| `HANDOFF.md:9` "19 landmarks"; `HANDOFF.md:59` "driveway_central is the 4.67-ft … threshold" | **NEITHER — stale current-state claims → F1** |
| `tests/test_model_version.py:52,63,67` | absence assertions (legitimate) |
| `docs/tides/<47 past tides>/forecast.json` (`"driveway_central": 0.0`) and their `index.html` | (a) frozen per-tide snapshots, stamped `v0.10.3`/earlier (spot-checked `2026-09-20T15-38`: model_version v0.10.3, 1 driveway row). Regenerating them would rewrite history. |
| `model/v0.10.4.md:12,39` | (b) the spec |
| `data/predictions_log_README.md:58` | (b) |
| `data/labeled_observations_README.md:59,131,135` | (b) proxy documentation — but `:58` "current 19" is stale → F2 |
| `model/archive/v0.10.3.md:39` "19-landmark ladder" | archive (excluded; historical) |
| `assets/observations/2026-09-01/README.md:6` "Nineteen EXIF-timed photos" | false positive |

Zero hits (verified individually): `docs/index.html`, `docs/details.html`, `docs/tides/2026-09-21T04-15 … 2026-09-23T18-19/index.html` (all six), `docs/tides/index.html`, `docs/forecast.json` (0 × `driveway_central`, 0 × `Driveway`), `docs/nowcast.json` (0; tracked; unchanged vs origin), `docs/barnacle-widget.js`, `forecast/rendering.py` (0 × `driveway` any case), `forecast/flood_forecast_daily.py` (0 × `driveway` any case), `LANDMARK_SHORT_LABELS` (no key), `assets/map_points.csv` (`driveway_road_central` present, `driveway_central` absent — test-asserted).
Widget: row removed; `WIDGET_VERSION = "v7.29a"`; comment now "(18 as of v0.10.4 — the driveway is a documented proxy, not a rung)"; `LANDMARKS` array = 18 entries.
Arms with objective exemption: SMS/ntfy carry no landmark label (BACKLOG:359, confirmed — `evaluate_sms_gate` is regime/depth based); email/charts render from `LANDMARKS` via `rendering.py:1487-1488, 2645`, so they inherit the 18 automatically; town map reads `assets/map_points.csv` (no driveway_central row).

### 4. Tests and gate — **PASS**
```
$ python3 -m unittest discover -s tests
Ran 170 tests in 0.798s
OK
$ python3 forecast/check_artifacts.py
publish gate: clean                                                   EXIT=0
```
`tests/test_model_version.py::test_driveway_is_a_documented_proxy_not_a_landmark` asserts: no `driveway_central` in `ff.LANDMARKS`; `len(ff.LANDMARKS) == 18`; `PROXIES vs LANDMARKS` in PLAYBOOK; `driveway_road_central` present / `driveway_central` absent in map_points; `WIDGET_VERSION = "v7.29a"`; `driveway_central` not in widget. `grep -rn "cross-fit\|Driveway\|v7\.28" tests/` → no hits (no test asserts the old label or widget version). The only `v0.10.3` literals left in tests are archive-path existence checks and a comment; `model/data/v0.10.3-reproduction.json` legitimately stays `"model_version": "v0.10.3"`. Vacuous-assert note: F5.

### 5. Generated surfaces — **PASS**
- `docs/forecast.json`: `model_version = v0.10.4`; `depths_in` (top level and each of `all_tides[0..5]`) = 18 landmark keys + `regime`; 0 driveway keys. The single `4.67` in the file is a gauge sample (`"value_mllw": 4.674` at 13:18) — not the driveway.
- `docs/index.html`: `<meta name="barnacle-model-version" content="v0.10.4">`; landmark table = 19 `<tr` = 1 header + **18 body rows** (SW distal grate 3.52 … Porch deck 8.08; no driveway). Diff shows the driveway `<tr>` removed from the "Landmarks today" section and the per-tide tables.
- `docs/details.html`: JS `var L = [...]` = 18 entries; 0 driveway; v0.10.4 × 4.
- Six regenerated per-tide pages: `model_version v0.10.4`, `driveway` absent, one 18-row table each.
- `git diff origin/main..HEAD -- data/alert_state.json | wc -l` → `0`.

### 6. Ledger integrity — **PASS**
- `git diff origin/main..HEAD -- data/labeled_observations.csv | wc -l` → `0`.
- `git diff origin/main..HEAD -- data/predictions_log.csv` → hunk `@@ -15058,3 +15058,9 @@`, six `+` rows only (`2026-09-21T00:13:35Z`, six target tides, `v0.10.4`), no `-` lines.
- `data/forecast_accuracy.csv` unchanged; `data/day_risk_log.csv` +1 row (append). See F10 for the pre-promotion stamp note.

### 7. Documentation honesty — **PASS on the two named documents; stale peer-language elsewhere (F1, F7)**
- PLAYBOOK "PROXIES vs LANDMARKS" (lines 37-47): "always as a RANGE with its provenance attached, never displayed as a peer of the landmarks … corner stage ≈ +13.7–13.9″ in events #6, #8, #9 and 8/27 — a weak lower bound [INFERRED], not a rung". ✔ range, ✔ [INFERRED], ✔ weak lower bound.
- Ledger README driveway entry (lines 135-160): "a documented PROXY, not a landmark … 4.67 is not the elevation of any locatable point … corner stage ≈ +13.7–13.9″ … [INFERRED]; weak lower bound only". ✔. It correctly calls 4.67 a "CORNER STAGE", never an elevation.
- Spec `model/v0.10.4.md:22`: "4.67 ft is not the elevation of any locatable point". ✔
- Still presenting it as a current threshold / peer: `HANDOFF.md:59-60` (lists it beside `driveway_road_central` as two current facts) — F1; `assets/observations/2026-06-15/README.md:114` and `2026-06-14/README.md:217` ("4.67-ft model threshold" / "4.67 flood threshold") — F7. `assets/observations/2026-08-03/README.md:3` "(water ≈ 4.67 NAVD88)" is a water level, fine.

### 8. Anything else — F4, F5, F8, F9, F10, F11 above. Also verified: DECISION commit (20:10:41) precedes the candidate (20:15:10); the DECISION line quotes John and is tagged `[STATED by user 19:07]`; the spec's provenance bullets (#6 mud-negative, #8 photo, 8/27 witness, #9 lower ramp at +13.7″) match the 2026-08-27 and 2026-09-13 READMEs and the ledger README at the summary level (not re-derived from ledger rows here). Archived specs carry no "superseded-by" banner — consistent with v0.10.1/v0.10.2 practice, not a new gap.

---

## Residuals for the promoting agent / John

- Promote via the rule-1 ritual on a fresh rebase; bots have almost certainly moved `main` since `11d6746f0`. Prefer regenerating surfaces on the rebased tree over carrying the candidate's regenerated artifacts (F10).
- The promoting commit must cite this artifact (`audits/2026-09-20-a1/01-candidate-review-v0.10.4-reviewer.md`, scope: candidate review) and `BACKLOG DECISION v0.10.4-driveway-removal`. Attribution per rule 12: this is a completed review of that work.
- Confirm the calendar date in `model/v0.10.4.md` at promotion (F6).
- John: re-copy widget **v7.29a** into Scriptable (last confirmed installed: v7.26a, 2026-09-14).
- Queue separately (not v0.10.4): F8 missing short label; F9 workflow comment; F11 test extension to HANDOFF/AGENTS/PLAYBOOK/ledger-README stamps.
- Reply owed: `02-…` by the candidate's author, finding by finding (confirm / dispute / already-addressed), before close-out.
