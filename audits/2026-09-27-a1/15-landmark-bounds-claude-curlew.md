# Round 15 — landmark-relation bounds work unit, for Codex review

Author: Claude Fable 5.1 ("Curlew"), 2026-09-27 23:35 EDT. Branch
`audit/2026-09-27-a1-bounds` (worktree `../barnacle-bounds`), based on main
`1f41cf710`, **unmerged for review**. Implementation commit **`4c33036ba`**.
Authorization: BACKLOG PREF `observations-are-quantitative` (John, 22:44)
and PREF `measurement-wording` (23:02–23:07); Codex round 13 item 2.

## What it does

1. **Standing bounds record.** `data/observation_bounds.jsonl`, append-only,
   one JSON line per band keyed by the ledger row's content hash, with
   lo/hi in ft NAVD88, `basis` (stated_landmarks / stated), the landmarks
   used (key, elevation, relation, survey source), the agent's text, who
   recorded it and when. Writer `bin/append_observation_bound.py`
   validates and fsyncs; the publish gate validates every line (strict
   JSON, fields, lo ≤ hi, hash matches a current ledger row). Prose is never
   parsed; an agent computes each band from `model/elevations.md` and
   `assets/map_points.csv` and records it. 19 bands recorded for Sep 25–27.
2. **Production.** `_today_lookback` evidence order is now measured >
   **bounded** > reported > bay > modeled. A band's upper bound covers a
   same-hour model claim that exceeds it; a lower-bound-only band cannot
   suppress; uncertain-time rows still never cover. New payload fields:
   `lo_/hi_rel_grate_in`, `lo_/hi_navd88`, `band_text`, `basis`. All five
   site/email arms and the widget (v7.33a) render the band.
3. **Analysis.** The interval sidecar takes landmark bands from the same
   record (single source; basis stated_landmarks); the hydrograph draws
   them (e.g. 07:15 Sep 26 4.16–4.66; the six "still no flooding" reports as
   upper bounds at 3.52; 09:14 Sep 27 as the 5.41 point).
4. **Wording.** "measured" replaces "tape" on every arm where the instrument
   is not stated; never "stick"/"ruler"; historical "tape" kept where the
   record says so. PLAYBOOK carries both owner rules.

## Bands recorded (ft NAVD88) and the open questions

| Row | Report (short) | Band | Landmarks |
|---|---|---|---|
| 188 | over the curb; near top of lawn step | 4.16–4.66 | curb, lawn step |
| 231 | <1 cm below the walkway curb; over the curb at the upstream grate | 4.14–4.16 | upstream sidewalk (approx.), curb |
| 238 | nearly to curb level; over the curb elsewhere (upstream) | 4.14–4.16 | same |
| 241 | Bay Ave crossed at the upstream grate; NW–SW bridged | ≥ 4.32 | Bay Ave middle at corner |
| 251 | breached over the first porch step | 5.41 | porch step 1 top (owner rule) |
| 224–229 | still NO flooding at the intersection | ≤ 3.52 | SW grate (first-water sentinel) |
| 191, 236 | negatives with unconfirmed times | ≤ 3.52 | SW grate (production ignores: time uncertain) |
| 187 | across Central SE–SW and over the other grates ("around 7") | ≥ 3.80 | NE/NW grates |
| 230 | spans SE to SW; north side not connected | ≥ 3.91 | Central middle at far corner |
| 237 | across Central SE–SW, minor, cars drive fine | 3.91–4.36 | Central far middle, Bay Ave middle |
| 222 | roads virtually clear | ≤ 4.36 | Bay Ave middle |
| 269 | jetting NE/NW grates, local flooding, not connected | ≥ 3.80 | NE/NW grates |
| 270 | spans SE–SW and NE–NW | ≥ 3.91 | Central far middle |

**Questions for John (bands left one-sided rather than guessed):**
(a) the elevation of the Central crossing between the NE and NW corners at
the intersection — the survey's "middle of Central 4.44" is between the
corner and the hydrant, and your 18:33 curb reading (4.16) three minutes
after "NE to NW connected" says that crossing is at or below 4.16; (b) the
upper bound for "local flooding around the NE/NW grates, not connected"
(below the corner pavement at 3.91?); (c) whether "near top of the lawn
step" should tighten row 188's upper bound below 4.66.

## Verification

455 tests OK, one skip (12 new in `tests/test_observation_bounds.py`;
writer validation, gate rejection of orphan/malformed lines, committed file
passes and cites landmarks, precedence, band coverage, one-sided bands,
uncertain-time bands ignored, every arm incl. node-rendered widget); gate
clean; three frozen replays PASS; seven frozen wind hashes match; ledgers
untouched; hydrograph regenerated and inspected. Native Scriptable layout of
the new band line is an owner check, as before.

## Addendum (23:35 EDT) — owner answers to Q2/Q3; Q1 candidates

John's verbatim answers are in
`assets/observations/2026-09-27/analysis/owner-band-clarifications.txt` and
were recorded as NEW lines in `data/observation_bounds.jsonl` (basis
`stated`, `owner_confirmed: true`; the earlier lines stand as history):

- Row 188 (07:15 Sep 26, "near top of lawn step"): means the lawn-step
  height, possibly ~1 cm under → **4.63–4.66** (supersedes 4.16–4.66).
- Row 269 (18:18 Sep 27, "local flooding around the NE/NW grates, not
  connected"): "only one or a couple (at most a few) inches above those
  grates" → **3.80–4.05**, local pools; must also be consistent with the
  NE–NW crossing not yet made (Q1).

Q1 remains open pending John's read of the labeled map
(`python assets/render_map.py --label name`). Candidate points near the
NE–NW connection across Central, from `assets/map_points.csv`:
`central_north_middle_1` 4.37 (Central crown nearest Bay Ave),
`central_north_proximal_1` 3.87 / `central_north_distal_1` 4.05 (edges),
`nw_crosswalk_distal` 3.91, `cross_bay` 3.75, `intersection_center` 4.51.
The 18:33 curb reading (4.16) three minutes after "NE to NW connected"
rules out the 4.37 crown as the connecting path; the survey PDFs are
`model/elevations.pdf` and `model/HLND2303-Road-Reconstruction-Supplement-Set-2024.05.06.pdf`.
