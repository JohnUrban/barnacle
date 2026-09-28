# Round 21 — landmark-bounds ship and deployment verification

Author: Claude Fable 5.1 ("Curlew"). Times are actual (EDT, 2026-09-28).
Authorization: Codex round 20 (`20-candidate-approval-codex.md`, candidate
`648c7db8d`); owner PREFs `observations-are-quantitative` and
`measurement-wording`; DECISION `sofar-line-empirical-wins`. Model stays
v0.10.6. Attribution: implementation and this record by Claude Fable 5.1
("Curlew"); independent review rounds 16/18/20 by Codex (GPT-6).

## Ship record

| Step | Result |
|---|---|
| Merge then-current main | `f815877cb` (11:26): `origin/main` `4309dcc3c` (Codex round 20 + bot publishes) into the candidate; BACKLOG ledger union, Codex's open-loop text kept; registry clean (31 episodes, 270 rows, 0 pending); 487 tests OK, one skip; gate clean |
| Regenerate pages | `--write-html --write-json --no-send` on the merged tree at 15:36:54Z; no alert sent (the evaluation said WOULD SEND for tonight's 21:40 tide — the hourly bot decides that on its own run); local-run ledger appends and the observed-peaks cache NOT committed (docs only, as before) |
| Ship commit | `7248c500d` (11:37:07 EDT) with HANDOFF rewritten wholesale and a BACKLOG ship line; main fast-forwarded; pushed on the first attempt |
| Pages | run 36445097941 success; live by 15:39Z |
| **CI** | run 36445097545 **failed**: `test_current_tide_pages_are_derived_from_forecast_payload` asserted exactly six per-tide pages; the regenerated payload legitimately carried five tides in its window (the 14:00Z bot run had six; the 09:15 tide had dropped out by 15:36Z). Every derived page existed and the gate had passed — a time-dependent constant in the test, not a defect in the shipped code or artifacts. Fixed in `ad2b66a52` (11:50:08 EDT): the test compares against the payload's own tide list with a sanity range. CI run 36446596736 on the fix: **success**; Pages 36446596325 success |
| Live site | `barnacle-widget.js` serves `WIDGET_VERSION = "v7.35a"`; `forecast.json` generated 15:36:54Z, model v0.10.6, `today_lookback.evidence = bay` (+10.7″ at 09:30, no readings today), `degraded_inputs = []`, no `input_health.observation_bounds` entry (the committed record read cleanly); landing page shows `SO FAR: BAY PEAK +10.7″ at 09:30 (gauge; corner not measured)`; no "(tape" wording on landing or details pages |
| Widget native layout | **PENDING, owner-only**: re-copy the DEPLOYED v7.35a and inspect the bounded, disputed-cap, long-report and model-claim forms on a real Scriptable surface. Only the v7.32a measured form was confirmed on screen (round 14). |

## What is live now

The append-only bounds record `data/observation_bounds.jsonl` with its
writer and the shared contract `forecast/observation_bounds.py` (gate-
validated; missing or unreadable file = degraded input); the interval-aware
"so far today" line (highest known floor across measured points and recorded
bands; higher possibilities disclosed; disputed caps shown but never used to
dismiss a model claim; local pools labeled; time certainty from the record,
prose fallback reads clocks only); "measured" wording where the instrument is
unstated; widget v7.35a. Today's live payload contains no bounds (no report
rows yet today), so the bounded and disputed forms are verified by the
offline fixtures and tests, not by a live occurrence.

## Status and follow-ups

Bounds work unit: **shipped and verified**, with the owner-only widget check
pending. Not closed by this record: the survey conflict
`central-crossing-vs-curb-inconsistency`, gate-transfer physics, high-base
tank, verified-vs-as-seen NOAA series, photos, historical census/hindcasts,
and Heron's episode-aware as-issued evaluation. The bounds record covers the
Sep 25–27 rows registered so far; new reports are recorded live with the
writer, and bands the agent cannot compute are questions to John.
