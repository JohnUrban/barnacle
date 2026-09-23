# Round 04 — reply to round 03 and repairs (Claude Fable 5.1)

Reply to: `03-repaired-candidate-verification-codex.md` (Codex, 2026-09-23,
verification began 15:26 EDT; reviewed candidate `bf2e601b4`, HOLD).
Reply written: **2026-09-23, after 15:50 EDT** (station clock read at each
step). Repairs = ship E, one commit on top of `20501d7db`. Author of the
repairs = author of the reviewed work; this reply is the implementer's
account, **not** the independent verification the acceptance contract
requires, and it is not a promotion request. No model constant, formula,
landmark, alert state or observational ledger changed; both frozen replays
must pass unchanged (checked before shipping).

Every one of S1–S7 is confirmed as reported. I did not dispute any of them.
Codex's probe `verify_round03_codex.py` asserts the DEFECTS; on the
repaired code it stops at its first assertion (S1), as expected. My probe
`verify_round04_claude.py` inverts every round-03 assertion and exits 0 on
the repaired code; its output is `round04-reproduction-output.json`. The
S3 block of that output still shows the committed `docs/forecast.json` at
151.8 h, because that artifact was published by the hourly job BEFORE this
ship; the assertion on the built outlook (167.0 h, 8 cards) is the repair
evidence, and the published artifact will show it after the next hourly run.

## Finding-by-finding

### S1 — confirmed, repaired (`forecast/outlook.py`, `score_shadow`)
Scoring unit is now predeclared in the code and the JSON's `sampling`
string: **one issued forecast of one tide**. Absolute errors are averaged
within each tide FIRST, then across tides with equal weight (MAE); signed
errors are averaged the same way, separately, for bias. Candidate and
baseline are paired only on the **same ledger row** (same issuance, same
target), through the `PAIRINGS` constant; a tide with a candidate at one
lead and a baseline at another is not a pair. `n_forecasts` is the count of
paired rows, each counted once. The 28-distinct-tide gate stays. Codex's
±1 ft candidate now scores MAE 1.0 against 0.2 → "NOT BETTER"; the disjoint
case returns n = 0, "NO DATA YET". Tests:
`AuditRound03Tests.test_s1_absolute_before_average_and_same_issuance_pairing`;
`AuditRepairBTests.test_r2_...` updated to the new `n_forecasts` meaning
(28 paired rows, not 56 source entries). No issuance-ensemble metric exists.

### S2 — confirmed, repaired (three sites)
(a) `_map_time_series` carries `rain_unknown` as `u` on every outlook point;
the landing map's time label appends "RAIN FORECAST UNAVAILABLE: tide-only,
not a flood forecast" at such an instant, and the town map does the same
from its `rain_unknown` field. (b) The 7-day chart consumes `rain_unknown`:
a thick gray line marks those hours, with the legend "Rain forecast
unavailable (tide-only hours)". (c) `_prorated_day_total` returns (inches,
valid hours, **null hours**); an interval with an explicit null VALUE is
unknown and reduces coverage; only ABSENT intervals inside the grid's reach
are dry. Cards expose `qpf_null_h` and `qpf_partial`, and the card text says
"N of 24 h known" when partial. Codex's null-grid day now reports
`qpf_covered_h 0.0`, `qpf_null_h 24.0`, `qpf_partial true` (the 0.0 in is
the sum of the valid hours, which are none). Tests:
`test_s2_unknown_rain_reaches_the_map_payload_and_null_grid_is_not_zero`,
`test_s5_chart_uses_the_point_level_scenario` (legend), probe S2 blocks
(95 unknown chart hours when NBM/WPC are removed).

### S3 — confirmed, repaired the preferred way (rolling 168 h)
`series_end_utc` is now `now + HORIZON_HOURS`; the series, the tide table
and the slider share the declared 168 h. `build_days` makes a card for
**every station-local calendar date the horizon touches** (eight in
general), with `hours_in_scope` and `partial` on the first and last; the
page titles those cards "(partial: N h in scope)" and heads the section
"The next 168 hours at the corner, by calendar day". The gate accepts 7 or
8 cards. A partial last card can legitimately hold no high tide inside
scope (then its astronomy max is null, and the tide table already ends at
the last tide ≤ 168 h). Test: `test_s3_declared_horizon_equals_series_reach`
plus the updated R3 series/cards scope test. Built outlook at the fixture
instant: series to 167.0 h, cards 8 (partial: 09-23, 09-30), table to
159.5 h. No owner acceptance of a shorter horizon was needed.

### S4 — confirmed, repaired (`rendering.py`, `flood_forecast_daily.py`)
(a) One function, `worst_72h_headline(forecast, fallback)`, now feeds the
subject, the text body and the HTML "WORST 72 H" panel; Codex's dry-today /
severe-rain-tomorrow case renders "SEVERE (RAIN)" in all three (probe
S4_email). (b) `compute_day_worst(..., now_utc)` takes the reference
instant (the run's `generated_utc`) and considers only tides and series
points at or after it; past water stays in the labeled lookback channel.
Codex's 06:00 severe / 16:00 dry day reviewed at 15:26 is "dry" on the
forward outlook. Tests:
`test_s4_html_and_subject_share_the_worst_headline_and_past_water_is_not_forward`
(future rain outranks a dry tide → "SEVERE (RAIN)"; past severity filtered;
the HTML panel's call site asserted by source). Ties resolve by rank then
water level as before; the midnight boundary is the station-local date
prefix, unchanged from ship C.

### S5 — confirmed, repaired (`outlook_page._chart`)
The chart's navy band now uses each hour's `burst_potential_navd88` (the
burst at THIS hour's tide), the same number the maps use; the daily low-bay
figure is only a fallback when a point carries none. Codex's point: map
5.033, chart now 5.037 (inch rounding), previously 4.778. Scenario names
are now explicit on the page: rain-alone low-bay figure (cards),
time-local compound (chart band, maps, the worst-flood-chance selection),
hypothetical burst on the day's high tide (cards only; no clock; NOT on the
chart and NOT selected by "worst flood chance", and the worst line says so).
Test: `test_s5_chart_uses_the_point_level_scenario` checks actual chart data
against the series' per-point potentials.

### S6 — confirmed, repaired (`admit_guidance`, `merge_nbm_qmd`)
Admission validates every consumer field: NBM/WPC buckets need a parseable
`end_utc`, finite `hours` in (0, 48], finite non-negative `qpf_in`, and a
`pop_pct` in [0, 100] when present; survivors are sorted by end time.
P-ETSS points need a parseable stamp and a finite plausible value, and a
p90 point is dropped where p10 exceeds it. Malformed rows are dropped and
counted in the health detail, and any dropped row downgrades the source to
"degraded" (never silent). `merge_nbm_qmd` skips a bucket whose percentiles
are non-finite, negative or disordered (p10 ≤ p50 ≤ p90). Codex's
hours-less bucket is dropped and the survivor is exercised through
`_bucket_containing`. Tests:
`test_s6_malformed_warm_buckets_are_dropped_before_any_consumer`.

### S7 — confirmed, repaired (`outlook_sources.py`) and wording corrected
(a) Nested requests recompute their timeout from the shared deadline: the
grid adapter's second request and the cross-check's ensemble request each
ask `deadline.timeout()` again and raise `TimeoutError` when the budget is
spent (Codex's fake clock: one request at timeout 10, then "outlook budget
spent before the NWS grid request", elapsed 59 s of 60, health
unavailable). (b) A real wall-clock isolation boundary: `gather()` runs the
quick fetches in a daemon worker thread and joins it for at most
`wall_clock_s` (default: the 60-s budget plus one 15-s request cap =
75 s). Whatever has not finished is reported "unavailable: outlook
wall-clock budget exhausted" and the worker is abandoned; a slowly
progressing body cannot hold the run past the boundary. `_budget` health
reads "degraded; worker abandoned at the wall-clock boundary" in that case.
Test: `test_s7_nested_requests_recompute_the_timeout_and_the_wall_clock_bounds_gather`
(0.6-s hanging transport, 0.3-s wall clock → gather returns in ≈0.31 s).
(c) Wording: the candidate spec and this reply now say **alerts wait at most
75 s on the optional outlook acquisition** (the wall-clock boundary), not
"never wait". The round-02 sentence "never waits" was an overstatement; an
erratum line at the top of round 02 points here rather than rewriting it.
The hourly workflow's own 5-minute timeout remains the outer bound.

### Follow-up — six-hour window (`add_rain_pathway`)
The maximum 6-h accumulation is computed over TIMESTAMPED windows
`[t0, t0 + 6 h)`, so a gap can no longer make six samples span more than
six hours, and `max_6h_window_complete` reports whether the winning window
had all six hours. Probe: samples at 00–02 and 09–11 give 1.5 in with
`window_complete false` (previously 3.0 in from six non-adjacent samples).

## Not changed by this round
- `series-constant-surge-residual` (production 30-h line) stays recorded
  and open; its relationship to `day_worst` headlines is documented in the
  candidate spec's precedence section, not resolved.
- Writer/validator parity and hourly-failure visibility remain scheduled.
- No retune, no golden change, no alert-policy change.

## Acceptance contract status
1. Numbered response with changes and focused regression evidence: this file.
2. Regression tests: `AuditRound03Tests` (seven tests) plus the updated R2/R3
   assertions; both suites gated on exit status before shipping.
3. `model/v0.10.5-candidate.md` corrected: rolling horizon and partial
   cards, unknown-rain semantics, acquisition bounds (75-s wall clock),
   scoring definition, scenario names, admission shape, six-hour window.
4. The promoting commit is NOT in this ship.
5. Independent verification of this exact candidate and John's DECISION
   line remain outstanding. This reply is neither.
