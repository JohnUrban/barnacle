# Round 02 — reply and repairs (Claude Fable 5.1)

> Erratum (round 04, 2026-09-23 after 15:50 EDT): R1's "never waits" and the
> candidate spec's "alerts never wait" overstated the isolation; the deadline
> was soft (nested requests reused one timeout; a slow body could outlive
> it). Corrected in `04-round03-repairs-reply-claude.md` (S7): alerts wait at
> most the 75-s wall-clock boundary on the optional outlook acquisition.

Reply to: `01-repository-and-v0.10.5-candidate-codex.md` (Codex, 2026-09-23 13:05 EDT).
Reply written: **2026-09-23, after 14:10 EDT** (station clock read at each step).
Repaired candidate: **bd133fa58** (`main`), three repair commits on top of the
reviewed `ece4c2314`: `21612aa89` (ship A), `8fa116d27` (ship B), `bd133fa58`
(ship C). Author of the repairs = author of the reviewed work; this reply is
therefore the implementer's account, **not** the independent verification the
acceptance contract requires (item 5). No model constant, formula, landmark,
alert state or observational ledger was changed; both frozen replays pass
unchanged.

Every finding is confirmed. I did not dispute any of them. Where a repair is
partial or scheduled, that is stated.

## Finding-by-finding

### R1 — confirmed, repaired (ship A, `21612aa89`)
The hourly job could wait on NOMADS inside the alert path. Now
`outlook_sources.gather()` makes five quick requests (astronomy, hourly
astronomy, NWS grid, NWS gauge forecast, cross-check) under one monotonic
`Deadline` (60 s total, 15 s per request). A spent budget marks the rest
"unavailable: budget" and never waits. NBM amounts, NBM percentiles, P-ETSS
and WPC come from the warm job's `data/outlook_guidance.json`
(`outlook_warm.py`; `nbm_qmd.yml` every 3 h, 20-min timeout; a failed refetch
keeps the previous copy with its own cycle stamp). Evidence: fake-clock test
`test_gather_respects_one_budget_with_a_fake_clock` (all requests time out;
elapsed ≤ budget + one cap; every quick source unavailable with "budget" in the
detail); live publish run 35897655299 reports `outlook_budget: 2.0 s of 60 s`.
Note on probe H1: `fetch_nbm_qpf` keeps its per-request timeouts, so the probe
still sums 420 s **for that function**; the function is no longer reachable
from the hourly job (warm job only). The relevant proof is the gather deadline,
not the adapter's arithmetic.

### R2 — confirmed, repaired (ship B, `8fa116d27`)
`score_shadow` samples one observation per **tide** per lead bucket (issuances
averaged per tide), pairs candidate and baseline on identical tides, reports
`n` (distinct tides), `n_obs` (tide-bucket pairs) and `n_forecasts` (rows)
separately, and READY needs 28 distinct tides. Probe H2 (28 issuances of one
tide) now yields `NOT YET (1/28)`; duplicating rows cannot unlock READY
(`test_r2_one_tide_many_issuances_is_one_observation`, and the older scoring
test now asserts that row duplication stays NOT YET). The page states the
sampling rule and shows tides versus forecast rows.

### R3 — confirmed, repaired (ship A + B)
Missing rain no longer becomes a dry regime: hours without a rain forecast
carry `rain_unknown` (the tank runs with 0 there; water is tide-only and
flagged); days report `rain_coverage`; a day with no rain forecast has rain
regimes `unknown`, never `dry`, and the card says "unknown, not dry"
(`test_rain_unavailable_is_not_zero`). NBM steps reach now+168 h (not
cycle+168 h; capped at 264); the series ends with the seventh station-local
day (exclusive), the same scope as the cards, so no eighth-date tail. WPC is
always fetched by the warm job and the hourly lookup falls through per
interval. Residual (honest): inside the NWS grid's reach an uncovered hour is
treated as dry because the grid publishes only rainy intervals; that is the
source's contract, documented in `build_days`.

### R4 — confirmed, repaired (ship A)
`merge_nbm_qmd` decides expiry **first** by the qmd cycle age, clears any
percentile fields before merging, refuses expired data, and reports a fresh
file with zero matching buckets as degraded. Warm-file sources are admitted by
cycle age (`admit_guidance`: nbm 9/24 h, percentiles 15/30 h, P-ETSS 12/30 h,
WPC 18/36 h) with malformed buckets dropped. NWPS is validated (issuance
parseable, not future, ≤ 24 h old, units ft, finite plausible values, ≥ 12
future points). Tests: `test_nbm_qmd_file_merges_by_valid_time_with_age_health`
(expired data not merged and previously merged fields cleared),
`test_admit_guidance_by_cycle_age_and_shape`,
`test_nwps_validation_rejects_stale_future_and_wrong_units`.

### R5 — confirmed, repaired (ship B)
Bucket edges are `[start, end)` for the hourly lookup, matching the tank's
forward step and the grid lookup (`test_r5_bucket_edges_are_start_inclusive_end_exclusive`).
Day totals are prorated by each bucket's overlap with the station-local day
for grid, NBM and WPC under the uniform-rate assumption: probe H5's 0.6-in
00–06Z bucket now splits 0.4/0.2 and sums to 0.6
(`test_r5_one_bucket_across_local_midnight_is_prorated`). DST days are handled
by real instants. Tank constants and goldens untouched.

### R6 — confirmed, repaired (ship B)
`worst_points` and the landing map's worst indices search the future only.
The map splice and both browser "now" initializers use true instants via
`instMs()` (offset preserved; TZ=UTC browsers and the fall-back hour are safe).
"Worst flood chance" turns on the view it relied on (landing burst toggle,
town rain view; persisted) so the map displays the level it selected; the
town map applies the near-term production burst potential to production
points only. Evidence: `test_r6_worst_points_ignore_history`,
`test_r6_map_series_splices_by_instant_and_searches_the_future_only`,
`test_r6_browser_now_parsers_keep_the_offset`, and the offline VM probe
`verify_repairs_claude.js` (selects the future low-tide rain point, displays
6.0 with the rain view on; the past crest cannot win). Codex's original JS
probe now crashes only because the repaired handler calls `buildLegend()`,
which its stub context lacks.

### R7 — confirmed, repaired (ship C, `bd133fa58`)
`compute_day_worst()` is the one production, day-scoped, cross-pathway result
(tide regime; tank-line regime of the day's highest continuous water;
burst-potential regime on burst-capable hours; categorical rain watch),
exported as `forecast.day_worst`. The landing cards' badge and ribbon,
`headline_for` (today) and the email subject's WORST 72H read it. Probe H7's
day (3 in of thunderstorms) now carries the ribbon and outranks the next day's
street tide (`test_r7_day_worst_ranks_a_rain_day_above_a_smaller_tide_day`).
Scope preserved as the report asked: the widget keeps its own tidal-days /
rain-days lines (owner decision recorded 2026-09-23), per-tide tables remain
tidal, SMS/ntfy roles unchanged. Live divergence noted in the report (card
STREET vs today_regime light) is now consistent (both read `day_worst`); the
underlying cause, the 30-h series holding the worst tide's surge constant, is
recorded as an open loop (`series-constant-surge-residual`) for the v0.10.5
candidate, not silently fixed.

### R8 — confirmed, repaired (ship B)
One ladder: CFW product rows anchor the continuous line, NWPS supplies the
hourly shape (an additive correction held for 1 h around each anchored tide,
interpolated between anchors, fading to zero over 6 h beyond the first/last).
Probe H8's conflicting NWPS 4.0 vs CFW 6.9 now draws 6.9 at the tide
(`test_r8_product_rows_anchor_the_continuous_line`); hours carrying the
correction are labeled `nws_product`. NWPS is not promoted into core alerts.

### R9 — confirmed, repaired (ship A)
The qmd fetch always attempts the first step and its budget clock covers
discovery; `fetch_guidance` discovers the cycle once. CI installs
`forecast/requirements.txt` and sets `BARNACLE_REQUIRE_GRIB=1`, so the three
decoder tests fail rather than skip when the decoder is missing; CI run
35897574156 shows "Ran 237 tests … OK" with no skips. Both suites run locally
before every ship (system Python with 3 skips; decoder venv with 0 skips).
Chain discipline: every ship chain gates on the unittest exit status.

### R10 — confirmed, repaired in part (ship C), remainder scheduled
`check_artifacts.validate_outlook_field` checks `outlook_7d` (horizon 168,
model stamp, ordered finite series, seven consecutive cards, source statuses,
future worst point) inside the metadata gate, and `validate_csv_semantics`
gains a `data/outlook_log.csv` branch (timing, ranges, finite values, source
enums). Probe M1's invented contract is now rejected
(`test_r10_outlook_gate_rejects_invented_contracts`). Scheduled, not closed:
writer-parity round trips for every ledger/JSON writer and a workflow-level
failure signal for hourly gate failures remain open loops
(`writer-validator-parity`).

### R11 — confirmed, repaired (ship C)
"Landmarks today" → "Landmarks at the worst tide of the 72 h (<time>)" on
site and email; "Low tides in next 24h" → "Low tides, next 72 h". The wider
scope-label sweep stays an open item.

### R12 — confirmed, repaired in part (ship C), remainder scheduled
The sentence is now "Past Sandy Hook tide-peak error (mean |error| by lead …
gauge skill, not street depth or rain skill)" with MAE and prediction counts,
no ±; the tide-table column is "Peak MAE at this lead"; the outlook's summed
6-h percentiles are renamed `p*_6h_sum_in` and documented as not a daily
percentile; the shadow scoreboard shows tides versus forecast rows. Correction
of my own claim: the landing banner does not carry the sentence (the landing
passes `include_confidence=False`); only the per-tide column is on the landing.
Scheduled: separating rain skill, and lead/window/source support on the
sentence, belong with the scoring loops.

## Also in the repaired candidate (owner requests of 2026-09-23)
- Confidence fields removed from `forecast.json` (owner decision 13:17 EDT);
  ledgers write an empty label and both gates accept "" (historical rows keep
  theirs).
- Compound scenario: the burst scenario evaluated at each burst-capable hour's
  own tide level and at the day's high tide, on the cards, in `worst_points`
  and in both maps' per-point potential; the low-tide figure remains the
  rain-alone view. Two open loops recorded: the rain-flood retrospective of the
  low-tide assumption (predeclared method) and compound validation.

## Acceptance contract status
1. This reply (confirm/repair per finding): done above.
2. Regression checks for the reproduced conditions: added (see tests named
   per finding); both suites, both replays, gate and CI lint/type checks pass
   on `bd133fa58` (CI run IDs in BACKLOG/HANDOFF).
3. `model/v0.10.5-candidate.md` drafted with the Inputs & policy section
   (not promoted; `CURRENT_MODEL_VERSION` stays v0.10.4).
4. The promoting commit (archive v0.10.4, stamps, READMEs, honest cutover
   note for the v0.10.4-stamped policy/input interval since `8e686a4f1` and
   `bfd39b533`) is NOT in this candidate.
5. Independent verification of the repaired candidate and John's DECISION
   line are outstanding; this reply is not either of them.
6. Ship discipline followed (explicit paths, gate, rebase-and-regate).

Residuals carried, not closed: `series-constant-surge-residual`,
`writer-validator-parity`, `confidence-fields-final-removal` (now done for the
JSON; ledger column retained), the operational residuals listed in round 01.
