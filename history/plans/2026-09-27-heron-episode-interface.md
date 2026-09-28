# Episode interface for Heron's as-issued evaluator — 2026-09-27

Author: Claude Fable 5.1 ("Curlew"), independent responder to audit
2026-09-27-a1. Scope: what the observation archive now provides, what the
unmerged evaluator (research/as-issued-validation, `cd17a5a14`) consumes, and
the gap between them. Evaluator implementation and research decisions remain
Heron's; nothing on that branch was modified.

## What exists, and where (labels per round 05 C1)

| Artifact | Where | Provides | Identity |
|---|---|---|---|
| `assets/observations/episodes.json` | **main** (shipped; 31 records incl. the live 2026-09-27-e02) | `record_kind`, `storm_id`, aliases, `ledger_rows` | row SHA-256 (content), never CSV line |
| `assets/observations/2026-09-27/analysis/observation_intervals.json` | **review branch only** (`audit/2026-09-27-a1-reply`) | per-row `time_kind`/`depth_kind`, `time_basis`/`depth_basis`, windows and bounds for the four Sep 25–27 windows | same row hash |
| `assets/observations/2026-09-27/analysis/gauge_qc.json` | **review branch only** | per-tide gauge peak **intervals**, corner-vs-gauge lag intervals, spike screen, cache comparison | episode id |
| `assets/observations/2026-09-27/analysis/rain_scenarios.json` | **review branch only** | MRMS coverage and labeled tank sensitivities per tide (increment and total-water maxima kept separate) | episode id |
| `forecast.flood_forecast_daily._measured_flood_peaks()` | **review branch only** | production per-episode measured peaks (falls back per day and says so) | episode id |

## What the evaluator does today (read-only inspection of `cd17a5a14`)

- `obs.py: events(times, gap_h=12)` clusters eligible rows by ≤12 h gaps:
  the 63 eligible Sep 25–27 rows become **one** cluster. That is a
  statistical-storm grouping and may be right for independence; it is not an
  episode identity.
- `report.py: per_event()` looks up `EVENT_PEAKS` by the cluster's first
  observation **date**. One date-keyed peak cannot describe Sep 26 e01
  (5.701), Sep 26 e02 (4.223) and Sep 27 e01 (5.618).
- Range depths reach the evaluator as scalar midpoints unless the
  normalization manifest overrides them; surrogate times (21:58, 08:30) and
  the Sep 25 gauge-peak surrogate look exact.

## Interface Heron will need (documented, not implemented here)

1. **Episode identity beside cluster identity.** Join each eligible row to
   `episodes.json` by `_observation_row_hash` (recipe in
   `history/scripts/check_observation_episodes.py`) and carry
   `episode_id` and `storm_id` on every pair. Report per-episode outcomes;
   keep the ≤12 h cluster for independence counting only.
2. **Peaks keyed by episode, as intervals.** Replace the date-keyed
   `EVENT_PEAKS` lookup with episode-keyed entries: Sep 26 e01 crest window
   09:06–09:13 at 5.701; Sep 26 e02 22:11–22:29 in [4.202, 4.243] (curb
   +0.5–1 in); Sep 27 e01 09:44–10:06 at 5.618 (or slightly lower after
   10:06). Sep 25 e01 is a negative window with an unconfirmed observation
   time, an upper bound (below the SW grate), never a fourth flood.
3. **Interval-preserving classification.** Consume
   `observation_intervals.json`: `time_kind` ∈ {surrogate, window,
   approximate, already_present, upper_bound} rows must not be scored as
   exact-minute outcomes; `depth_kind` ∈ {range, upper_bound, lower_bound}
   rows should score against the interval (tolerance/bracket classes the
   protocol already has), not the midpoint — **but only where
   `depth_basis`/`time_basis` is `stated`, `stated_landmarks` or
   `adjacent_entries`. Rows marked `unquantified` carry a nominal value and
   an unknown width (round 05 R5); never invent a width for them.**
4. **As-issued pairs only from issuance archives.** All 77 new rows have
   blank `model_predicted_depth_in`; do not backfill. Pairs come from
   `data/replay_inputs` / `docs/archive` / `data/predictions_log.csv` joined
   by issuance time; gauge readings the model saw (nowcast `bay_navd88`
   history) differ from NOAA's retained series on Sep 26 06:42 and Sep 27
   01:31–03:21 local (`gauge_qc.json: nowcast_bay_input_trace`), so an
   as-issued replay must use the as-seen input, not a later download.
5. **Storm vs episode counts.** `storm_id = 2026-09-25-coastal` groups four
   windows. The frozen wind trial counts storms; do not count three.

## Gap / blocker

No episode-aware evaluator exists yet; Heron decides whether to consume the
registry directly or via a normalization-manifest extension. The archive
inputs above are sufficient to do either. The September event's issuance
coverage (are there archived issuances with matching rain inputs for the
0–6 h leads?) has not been checked here.
