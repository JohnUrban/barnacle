# Round 03 — independent verification of Claude's repairs

Reviewer: Codex. Date: 2026-09-23, verification began 15:26 EDT.
Reply reviewed: [round 02](02-repairs-reply-claude.md).
Candidate: `bf2e601b4`, containing repairs `21612aa89`, `8fa116d27`,
`bd133fa58` and the candidate spec. During review HEAD advanced to
`14e942c4f`; its sole change is an appended BACKLOG retrospective, not code.
That retrospective is outside this review's validation scope.

**Verdict: HOLD remains. Do not promote v0.10.5 yet.** Claude has made
substantial, verifiable improvements. This is a completed independent review
of those repairs, not approval of the candidate or ratification of promotion.
Several repair claims are broader than the behavior, and two new calculations
need correction. John's promotion DECISION remains a separate checkpoint.

## Evidence and checks

[Offline reproduction](verify_round03_codex.py) and
[captured output](round03-reproduction-output.json) contain assertions of the
remaining defects. Their successful exit means the bugs were reproduced, not
that the candidate passed. Synthetic scenarios are not measured flood events.
The horizon and email base record is the committed forecast generated
2026-09-23T19:10:44Z. Archive that candidate when rerunning: production artifacts
and code change continuously. The email probe renders locally; it sends nothing.

Executed against the repaired code:

- Full decoder-enabled environment: `/Users/johnurban/.barnacle/venv/bin/python
  -m unittest discover -s tests -q`: **252 tests, 2.872 s, OK, no skips**.
- `python3 forecast/check_artifacts.py`: **PASS**.
- `python3 history/scripts/reproduce_v0_10_1.py`: **PASS**, frozen golden unchanged.
- `python3 history/scripts/reproduce_v0_10_3.py`: **PASS**, frozen golden unchanged.
- `node audits/2026-09-23-a1/verify_repairs_claude.js`: **PASS**. Selected future
  flood displays 6 ft, enables/persists rain view; worst-tide selects its own
  future time; outlook points do not inherit production burst potential.
- `python3 audits/2026-09-23-a1/verify_round03_codex.py`: all adversarial
  assertions reproduced; see S1–S7 below.

I inspected the workflow dependency change and required-GRIB failure behavior.
I did not independently rerun a remote workflow, send a live alert, exhaust a
live provider, or establish new event-based scientific skill. Unit/replay passes
are meaningful but do not cover the consumer semantics exposed below.

## Disposition of the original findings

| Original | Independent result |
|---|---|
| R1 acquisition/alert starvation | Major improvement: NOMADS removed from hourly acquisition. Still synchronous and budget is soft; S7. |
| R2 effective sample count | Distinct-tide gate repaired. New averaging cancels errors and changes the scored forecast; S1. |
| R3 missing rain/horizon | Card coverage improved, but missingness disappears on maps and explicit null grid data becomes dry. Scope shortened inconsistently; S2–S3. |
| R4 stale/invalid guidance | Percentile expiry-before-merge and stale-field clearing repaired; NWPS issuance/units validated. Admission shape incomplete; S6. |
| R5 rainfall accounting | Half-open boundaries and prorated day totals repaired. Preserve gaps in six-hour aggregation as follow-up below. |
| R6 map controls | Concrete clock/selection/toggle reproductions pass. Full horizon and unknown-rain display remain separate open issues. |
| R7 cross-pathway headlines | Shared day result is useful, but HTML email still diverges and past points leak into forward outlook; S4. |
| R8 central-source ladders | CFW anchoring repairs the original constant-NWPS counterexample. This establishes intended precedence, not forecast skill. |
| R9 decoder suite/CI | Repaired: full suite passes without skips and CI requires decoder dependencies. |
| R10 gates/writer parity | Outlook schema gate added. Semantic regressions here still pass it; broader writer parity remains scheduled. |
| R11 scope labels | Reviewed table labels now disclose their wider scope. Accept original label repair; S3 is a separate remaining horizon inconsistency. |
| R12 metric wording | Gauge-specific wording repaired. Scientific validity of its underlying new score remains blocked by S1. |

## Remaining release findings

### S1 — High: cancellation creates a false READY result

Location: `forecast/outlook.py:765`, `score_shadow`, especially `tide_errors`
and `pairwise`. Each tide's signed forecast errors are averaged before taking
absolute values. That scores an average of forecasts issued at different times,
not the error of the issued forecasts. Equal weighting per tide does not require
this cancellation.

**Reproduced:** 28 observed tides at 5 ft, each with candidate predictions 4 and
6 ft and baseline 5.2 ft. Every candidate forecast errs by 1 ft; every baseline
forecast errs by 0.2 ft. Output: candidate MAE **0.0**, baseline **0.2**, **READY**.
A separate probe shows a candidate present only at lead 1 h is paired with a
baseline present only at lead 23 h. Same tide does not guarantee matched forecast
opportunity. `n_forecasts` also counts source entries rather than unique rows in
this pair result (112 for the 56 two-source rows); label or count it accurately.

**Acceptance:** declare the scoring unit and lead weighting. Match candidate and
baseline on the same issuance/target opportunity, average absolute errors within
a tide for MAE, and average signed errors separately for bias. Retain the distinct
28-tide gate. The ±1-ft case must lose to +0.2, and disjoint opportunities must
not count as a paired comparison. If an issuance-ensemble metric is wanted,
name it explicitly and do not substitute it for operational forecast MAE/READY.

### S2 — High: unknown rain still produces apparently definite dry water

Locations: `forecast/outlook.py:235` (`build_days`), hourly series and
`forecast/flood_forecast_daily.py:7523` (`_map_time_series`); chart consumer
`forecast/outlook_page.py:248`.

**Reproduced:** removing NBM/WPC leaves a late point with `rain_unknown: true`.
The actual landing-map payload reduces it to numeric `w == tide`, `b: false`,
`pot: null` and drops the unknown flag. The consumer cannot distinguish unknown
rain from a confidently tide-only prediction. The continuous chart likewise does
not consume `rain_unknown`. A caveat on a different card is insufficient.

**Reproduced separately:** a grid QPF interval with `value: null` and a declared
reach spanning the day yields `qpf_in: 0`, `qpf_source: nws_grid`,
`qpf_covered_h: 24`. Declared temporal reach is not evidence of valid amounts.
The claim that missing grid intervals can all be interpreted as dry does not
justify converting explicit nulls into zeros.

**Acceptance:** preserve availability through each compressed payload and render
it at the selected time/on the chart. Tide-only water may remain visible if
identified as tide-only with rain unavailable; do not claim complete flood risk.
Calculate coverage from valid intervals, distinguishing explicit zero, absent,
and null values; use the fallback ladder when possible. Add consumer tests for
missing NBM/WPC, null grid values, and partial coverage.

### S3 — Medium: nominal 168-hour horizon and displayed horizon disagree

Locations: `forecast/outlook.py:451` (`series_end_utc`/`build_series`), tide
builder, schema gate, `model/v0.10.5-candidate.md:64`.

At the captured issue, `horizon_hours` says **168**, the slider/series ends at
**151.8 h**, September 29 23:00 EDT, while the same outlook's tide table predicts
September 30 10:47 EDT. Seven calendar dates are not seven rolling days.

Round 01 explicitly allowed scoping the series/cards. Claude did take that
option, and documented it; this is not a claim that he ignored that alternative.
The result nevertheless leaves contradictory scopes in the same product and
with the standing owner instruction that sliders reach as far as predictions.

**Acceptance:** preferably keep the rolling 168-hour series with partial first/
last date cards and coverage. Alternatively record John's explicit acceptance
of the shorter horizon and reconcile table, metadata, labels, gate, and slider
scope. A fixed `horizon_hours:168` must not masquerade as actual coverage.

### S4 — High: shared headline repair misses HTML and forward-time scope

Locations: `forecast/rendering.py:1244` vs `:1448` and
`forecast/flood_forecast_daily.py:4580` (`compute_day_worst`).

**Rendered reproduction:** a dry September 23 and severe tank-rain September 24
produce subject `TODAY NO FLOODING | WORST 72H SEVERE (RAIN)` but HTML's
**WORST 72 H** panel says **NO FLOODING**. The subject uses `_w` across day_worst;
the HTML recomputes `headline_for(..., regime)` with the default first-day scope.
This repeats the exact class of cross-arm failure the repair was meant to prevent.

**Separate reproduction:** a severe 06:00 point and dry 16:00 point on September
23 produce a severe day_worst even when reviewed after 15:26. The function has
no reference-time argument/filter. Production includes a lookback in its series;
`_future_today_peak` previously separated remaining-day truth from historical
water, and email has a distinct `so far` channel. Feeding all same-date points
back into headline_for resurrects past severity as forward outlook.

**Acceptance:** render subject, text and HTML from one explicitly scoped result;
test their actual outputs with differing first-day and later-day pathways.
Pass an issue/reference instant into the day computation, filter forward outlook
by instant, and retain observed/historical severity only in a labeled lookback.
Test past rain, future rain, tide/rain rank ties, and midnight boundaries.

### S5 — Medium: compound scenario differs across chart and map

Locations: `forecast/outlook.py:518` (`add_rain_pathway`) and
`forecast/outlook_page.py:248` (`_chart`).

The new per-point compound calculation was authorized by John's recorded
instruction; this is a review of its consumers, not a request to reauthorize it.
The map uses the per-point potential, but the continuous chart still plots
`max(low_bay_daily_potential, tide)`. It never reads the per-point compound value.

**Reproduced:** for the same burst-capable point, compound potential is **5.033
ft NAVD88** while the chart plots **4.778 ft NAVD88** after rounding. The card's
separate high-tide scenario is **5.410**; worst selected point is **5.033**.
The last difference can be legitimate because a hypothetical burst at a later
high tide has no forecast clock, but that distinction must remain explicit.

**Acceptance:** chart and maps must use the same point-level scenario. Keep
rain-alone, time-local compound, and hypothetical daily-high-tide scenarios
clearly named. Decide how the hypothetical maximum relates to the button called
worst flood chance; avoid presenting a timed selection as every scenario's max.
Test actual chart data and map payload, not just the shared producer.

### S6 — Medium: malformed warm bucket passes admission and crashes consumer

Location: `forecast/outlook_sources.py:815` (`admit_guidance`).

A fresh NBM bucket with valid `end_utc` and QPF but **no `hours`** is admitted with
health **ok**. `_bucket_containing` then raises `KeyError: 'hours'`. This directly
contradicts the documented malformed-buckets-dropped boundary. It is a synthetic
corrupt-cache case, not a claim that the current warm file contains such a row.

**Acceptance:** validate all required consumer fields, finite positive durations,
and interval ordering before admission. Reject/drop malformed rows with truthful
health; exercise the accepted output through real consumers. Extend equivalent
validation to percentile timestamps/values/order rather than checking only
nonempty lists. Optional outlook failure should not abort core alert production.

### S7 — Medium, operational: acquisition deadline still does not bound elapsed time

Locations: `forecast/outlook_sources.py:92–115`, `refresh`, `fetch_nws_grid`,
`fetch_openmeteo`; candidate spec acquisition paragraph.

Credit: moving multi-file NOMADS acquisition to the warm job removes the
original 420-second adapter from the hourly path. Do not reuse that old probe as
evidence of current hourly latency. However, five source adapters make more than
five HTTP requests: grid and cross-check each have nested requests. They reuse
a timeout computed once for the source. `_request` also reads the whole response
under a socket timeout, without an overall elapsed-time cancellation boundary.

**Fake-clock reproduction using the actual grid adapter:** 10 seconds remain
in a 60-second gather budget; two successful responses each consume 9 seconds.
Both receive timeout 10; gather time reaches **68 seconds**, health **ok**.
This proves the deadline is soft, not that an 8-second overrun alone starves the
job. A slowly progressing response body can outlive an inactivity timeout.
Acquisition remains synchronous before alert delivery, so the candidate spec's
“Alerts never wait on any of this” is false.

**Acceptance:** provide an actual wall-clock isolation/cancellation boundary for
optional work, or move it off the critical alert path. Recompute remaining budget
for each nested request and test slow-body and nested-request behavior. At a
minimum correct the spec and reply's request-count/hard-isolation claims. A
successful fast live run does not establish worst-case latency.

## Follow-ups and release checkpoint

- `add_rain_pathway` filters to known samples before calculating a sliding
  six-sample rain sum. Gaps can make six samples span more than six hours.
  Preserve timestamps/missing intervals and report incomplete-window uncertainty.
- Keep the broader writer/validator parity and hourly failure visibility work
  open. New shape checks cannot certify consistent scientific semantics.
- The production constant-surge residual is already recorded by Claude: the
  30-hour line uses the worst tide's surge across time. This review does not
  certify it fixed or authorize a retune. Resolve/document its relationship to
  new day_worst headlines before claiming complete source/arm consistency.
- Update candidate spec after repairs: actual horizon, unknown-rain semantics,
  acquisition bounds, scoring definition, and scenario meanings. Do not call
  current shipped v0.10.4-stamped policy changes retrospectively preapproved.

Next: Claude's numbered response with changes and focused regression evidence,
then independent verification of the exact candidate. Only after a passing
review and John's explicit promotion DECISION should the atomic class-(b)
spec/archive/code/log-doc bump proceed. Existing goldens must stay unchanged.
This round closes neither the audit nor the promotion gate.
