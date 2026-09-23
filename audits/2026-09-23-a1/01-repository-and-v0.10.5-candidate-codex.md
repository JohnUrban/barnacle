# Repository audit and v0.10.5 candidate review

Author: Codex (GPT-6), independent of Claude's implementation.
Review opened: **2026-09-23 12:51:57 EDT**.
Candidate examined: **ece4c2314dbafb2dce2e4f4f09015200bdda51a0**.
Review completed: **2026-09-23 13:05 EDT**.
Target window: **2026-09-22 12:51:57 through 2026-09-23 12:51:57 EDT**.
Status: **OPEN — HOLD v0.10.5 promotion pending repairs and independent verification.**
This is a completed review of that candidate, not approval of a later revision.
No production code, model, alert state, or observational ledger was changed by this audit.

## Decision for John and Claude

The direction is sound: preserve the calibrated physics, separate the longer
outlook from alert eligibility, show source provenance, and include rain. The
candidate is **not ready to receive a clean promotion verdict**. Nine release
findings below need correction (R1–R9); R10–R12 describe broader engineering,
measurement, and display debt. Some release findings expose inherited behavior
that the new requirements now promise to fix; those are identified explicitly.

Most urgent: **isolate optional outlook acquisition from alert delivery** (R1).
The page is display-only in its data policy, but its synchronous fetch chain is
inside the production alert job. That distinction matters during the advisory.
Do not disable the whole rain pathway or revert the successful CFW parser repair.

The new inputs and alert policy are already on main and already publishing as
v0.10.4. A v0.10.5 commit will formalize and repair an existing deployment, not
introduce an entirely unshipped candidate. Record this cutover honestly. Existing
owner decisions to build the outlook stand; this report neither reopens them nor
supplies the outstanding owner promotion DECISION.

Suggested order: R1 + R9, then rain availability/freshness/accounting (R3–R5),
then scoring and surface consistency (R2, R6–R8). Claude should reply finding by
finding as round 02, with commits and regression evidence. An independent reviewer
must verify the repaired candidate; John then decides promotion. Do not describe
this HOLD report as a passing implementation review.

## Scope and evidence method

Read AGENTS, HANDOFF, audit protocol/index and prior closeouts, BACKLOG open loops,
PLAYBOOK, current model spec, architecture notes, CI/publication workflows, and
relevant production/test seams. No earlier report lacks a reply. The old audits
remain closed; this report does not reopen their accepted owner-gated residuals.

Reviewed all **11 human-authored commits** in the window, attributed by their
actual trailers to **Claude Fable 5.1**, not merely by Git author JohnUrban:

| Commit | Work reviewed |
|---|---|
| `8e8e5cfcd` | Raw KPHI CFW acquisition, station-block parsing, health wiring |
| `9fea73d47` | Offset-aware overnight tide exemption |
| `8e686a4f1`, `0227e8b2c` | 48-hour alert window and repair of the red assertion |
| `bfd39b533` | Source adapters, outlook builder/page, ledger, shadow scoreboard |
| `11f40342a` | Shared chart frame and landmark lines |
| `82551c950` | Rain pathway, longer maps, worst-pathway policy |
| `97c3c2c4d` | Restored high-tide band chart |
| `4f2c8aeba` | Confidence-label phase-out and measured error presentation |
| `c9e5fc5a5`, `ece4c2314` | NBM percentile acquisition, merge, warm-job scheduling |

Also examined inherited alert delivery/state/retry coverage, nowcast dispatch and
watchdog contracts, writer/gate coverage, version/provenance discipline, protected
ledger conservation, DOM contracts, and the live landing/map/outlook surfaces.
This is a risk-based production audit, not a claim to have proved every line or
every historical observation correct. No real alert was sent and no workflow was
dispatched. No model calibration was refitted. The untracked `.claude/worktrees/`
was left untouched.

Primary reproducibility artifacts:

- [Offline probes](reproduce_findings.py), run with
  `python3 audits/2026-09-23-a1/reproduce_findings.py`.
- [Captured probe results](reproduction-output.json). Inputs marked synthetic in
  the script are adversarial examples, **not measured flood observations**.
- [Verification record](verification.md), including full-environment test failure,
  GitHub run IDs, ledger checks, browser observations, and limits.

## Findings

### R1 — P1 / release blocker: optional outlook fetches can prevent alerts and publication

Evidence: `forecast/outlook_sources.py:625–654,767–798`,
`forecast/flood_forecast_daily.py:805–837,2573–2583,7561`;
`.github/workflows/daily_forecast.yml:35`.

`build_forecast()` synchronously calls `gather()` before returning to `main()` and
before delivery. The outer exception handler only helps after acquisition returns.
NBM discovery alone tries seven candidates with a 60-second timeout each; then up
to 27 additional subsets, followed by WPC fallback (up to twelve 90-second requests).
Other sources are sequential too. There is no aggregate deadline or cancellation.
The whole hourly job, including installation and publishing, has **300 seconds**.

Probe H1 confirms a possible **420 seconds in NBM discovery alone**, with simulated
timeouts and no wall-clock waiting. This is a demonstrated budget violation, not
a claim that the current healthy 12-second forecast run timed out. A stalled
optional vendor can kill the process before imminent alerts, including alerts
triggered by the nowcast dispatch, are evaluated/delivered.

Repair: move expensive outlook acquisition to a separately budgeted producer and
consume bounded-age snapshots, or enforce a true end-to-end deadline leaving
protected capacity for the core forecast, alerts, and publication. Source-local
socket timeouts and a larger job timeout alone are insufficient isolation.
Test cold cache + repeated timeouts + partial success + stale fallback with a
controlled clock, and prove core alert evaluation remains reachable within budget.

### R2 — P1 / release blocker: one observed tide can satisfy the promotion threshold

Evidence: `forecast/outlook.py:636–713`; `forecast/outlook_page.py:449–462`.

`score_shadow()` counts forecast **rows**, not distinct observed tides, when
reporting `n` and deciding READY. An hourly forecaster produces many correlated
rows for one target. Probe H2 feeds 28 different issuances for **one** observed tide
and gets `n=28, READY: candidate beats baseline`. The page explicitly promises
28 scored tides. This can approve an input source after a tiny number of events;
extra dispatches also change the weighting. The comment equating 28 tides with
about one week is inaccurate for roughly two high tides per day.

Repair: report `n_forecasts` and `n_unique_tides` separately; gate on at least the
intended number of distinct outcomes. Predeclare a lead-stratified, paired sampling
or per-tide aggregation rule so frequent runs do not dominate skill. Preserve
identical candidate/baseline support, expose coverage, and keep promotion human-gated.
Test repeated issuances, duplicated rows, unequal source availability, and distinct
outcomes. One target must never unlock READY irrespective of row count.

### R3 — P1 / release blocker: unavailable rain still produces a dry model path and an apparently complete horizon

Evidence: `forecast/outlook.py:375–420,423–486,490–513`;
`forecast/outlook_sources.py:625–660,784–790`; `forecast/outlook_page.py:150–158`.

The raw point preserves `rain_in_hr=None`, but `build_series()` substitutes **0.0**
into the tank, then emits a definite `water_navd88`. `add_rain_pathway()` emits zero
peak/6-hour rain and `tank_regime=burst_regime='dry'` when rain is absent. A warning
sentence on a wholly missing day does not undo the no-rain assumption in maps,
charts, or worst-water selection. Partial days are called available when **any**
rate exists; deleting missing rates also lets a six-element sum span a longer gap.

This is not only hypothetical: the committed/public **16:14:10Z** forecast has
**10 future hourly points without rain input, September 30 03:00–12:00 EDT**, while
NBM and the aggregate outlook are `ok`. NBM fetches only through cycle+168 hours,
not now+168; its publication/cache lag removes the tail. WPC is skipped whenever
NBM is generally `ok`, even with missing buckets. Seven calendar cards end on
September 29 while the rolling series continues into September 30; that tail has
no daily burst potential even if a future source supplies rain there.

Repair: represent rain coverage per interval and propagate unknown/degraded state
through derived values and displays. A tide-only lower-bound curve may remain,
but must not be labeled complete flood guidance. Fill per-interval gaps from the
fallback ladder, fetch sufficient forecast hours relative to **now**, and compute
burst scenarios for every represented date (or explicitly scope the series/cards).
Test whole-source failure, a missing wet interval, a partial day, warm-cache lag,
and rain dominating during the rolling horizon's eighth calendar date.

### R4 — P1 / release blocker: expired or incomplete guidance is usable while health says unavailable/ok

Evidence: `forecast/outlook_sources.py:123–155,599–622,767–798`;
`forecast/flood_forecast_daily.py:813–816`.

`merge_nbm_qmd()` copies percentile values **before** checking expiry. Probe H4
shows a multi-day-old file marked `unavailable` still supplying `p90_in=3.0`.
Merged fields mutate the NBM cache object, which is subsequently saved; if a later
qmd file is missing, returning early does not remove old cached percentile fields.
`ok` is also returned for a fresh file with zero matching buckets. General `refresh()`
measures retrieval age rather than forecast issue/cycle age and accepts partial
NBM/WPC results as healthy without assessing requested-horizon coverage. NWPS
`issuedTime` and units are exposed but not validated before use.

Repair: validate source issuance, validity coverage, units, finite values, and
future timestamps before admission. Keep percentile data/provenance separate from
the deterministic cache or clear derived fields before each merge. Expired data
must not drive the active scenario. Report partial/no-match coverage and fall back
per interval. Tests should cover expiry after prior successful merge, missing file,
future-dated file, fresh download of an old issuance, and partial valid coverage.

### R5 — P1 / release blocker: rain amounts and timing are not conserved across day/hour boundaries

Evidence: `forecast/outlook.py:88–97,192–236,321–342,429–436`;
`forecast/flood_forecast_daily.py:4273–4319`.

`build_days()` adds each overlapping grid accumulation in full to each local day.
Probe H5 puts a **single 0.6-inch UTC 00–06 bucket** across local midnight; both
September 23 and 24 report 0.6 inches (1.2 total). Under the code's uniform-rate
assumption the split should be 0.4/0.2. NBM day selection assigns whole six-hour
buckets by end time; WPC picks a 24-hour bucket whose end may fall 12 hours into
the following date, without defining a local-day accumulation interval.

The hourly forcing has a separate off-by-one: `_bucket_containing()` uses
`(start,end]`, while `simulate_pluvial_series()` treats each supplied rate as a
forward step. A 00–06 six-hour bucket starts feeding at 01:00 and remains selected
at 06:00. NWS-grid lookup uses start-inclusive intervals. This shifts rainfall
relative to the tide/drain head and can change flood timing and height.

Repair: use an explicit common interval contract; prorate day totals by actual
UTC overlap with station-local day boundaries, and use start-inclusive/end-exclusive
rates for forward integration. Preserve gaps, handle 23/25-hour DST days, and label
WPC's native period if not converted. Test mass conservation, boundary instants,
source seams, a pulse across midnight, and a pulse near a tide crest. Do not change
tank constants or replay goldens to compensate for forcing-time errors.

### R6 — P2 / release blocker: new map controls can select history or display the wrong pathway

Evidence: `forecast/outlook.py:490–513`;
`forecast/flood_forecast_daily.py:6331–6344,6461–6483,7422–7468`;
`docs/highlands.html:775–823,894–915`.

Three contract failures:

1. The outlook worst selector and both map selectors search the entire series,
   including historical context. Probe H6 makes a -2-hour crest win “next 7 days.”
   Context may stay on the slider; future-risk buttons must exclude it.
2. Both “Now” initializers regex the wall clock out of offset-bearing stamps and
   construct a browser-local `Date`. Under `TZ=UTC`, `2026-09-23 13:00-04:00` becomes
   13:00Z rather than 17:00Z. This inherited parser now drives the newly promised
   NOW default. Fall-back-hour order is also unsafe when strings are compared.
3. Town “Worst flood chance” selects using rain-inclusive water, but `syncScrub()`
   displays tide-only water if the rain checkbox is off (its markup default).
   Landing has the analogous burst-toggle ambiguity. Town also falls back to the
   near-term global `POT` on later outlook days with no day potential, unlike the
   landing's deliberate `pt.o ? null : MS.potential` rule.

Repair: compare real instants using the offset or UTC field, restrict future
selection to the current clock, and make the named action display the water level
it selected (with clear pathway/toggle state). Do not carry a near-term burst to
an unrelated later day. Test browser time zones, DST repeated hours, old artifacts,
a past crest exceeding future water, and a future low-tide rain/burst maximum with
both toggles initially off. Current live tide-dominated buttons working does not
exercise these counterexamples.

### R7 — P1 / release blocker: “no tidal supremacy” did not reach the existing headline arms

Evidence: `forecast/rendering.py:111–241,1199–1218`;
`forecast/flood_forecast_daily.py:3578–3598`.

The landing ribbon still ranks `(tide_rank, rain_boolean)`, so **any** tidal street
water outranks even an elevated rain-only day. Probe H7 makes a three-inch,
three-inch/hour thunderstorm day lose to the following day's street tide. The
landing badges never compare against the new tank/scenario maxima. `headline_for()`
only substitutes rain when the tide regime is `dry`; the email's `WORST 72H`
headline still uses the tide-keyed peak. These are existing consumers of the
changed meaning, not objective exemptions under rule 8.

Live evidence of the underlying divergence: the 16:14:10Z landing card says
STREET/+6.7 inches for September 23, while the production `today_regime` is `light`
and the continuous curve reaches +11.5 inches. This particular difference is not
proof of rain flooding; it demonstrates that the headline is not consuming the
same worst-water result as the curve.

Repair: one shared, day-scoped worst-pathway result should feed the landing
headline/ribbon and applicable email summaries, while tide-specific tables remain
explicitly tidal. Inventory ntfy, imminent SMS, widget, per-tide pages, details,
and charts; preserve their owner-defined horizons/roles. John's explicit
“widget unchanged” and “email link-only” decisions exempt the new **seven-day
content**, not silently all pre-existing worst-risk semantics. If applying the
standing cross-pathway rule requires changing that deliberate widget boundary,
record the precise scope for John rather than assuming permission to redesign it.
Test a rain-only day against a smaller tidal day and an already-wet compound day;
verify rendered arms, not just `outlook_7d` or an internal helper.

### R8 — P2 / release blocker: daily cards and continuous guidance use different central-source ladders

Evidence: `forecast/outlook.py:120–158,395–406`; `outlook_page.py` chart description.

Per-tide guidance prefers CFW over NWPS. The continuous line always prefers NWPS
where an hourly point exists, ignoring a matching CFW anchor. Probe H8 yields a
CFW card/table peak of **6.9 MLLW** and an hourly central value of **4.0 MLLW** at
18:00 from conflicting synthetic NWPS data. This is an intentional-looking code
choice, but neither the day headline nor the worst selector reconciles it; a daily
headline can disagree with the risk level on its own continuous curve/map. The
page separately describes both ladders, which is not the same as explaining a
source conflict or defining one operational central truth.

Repair: define and document a single anchor/shape policy, or explicitly show the
two alternatives and compute the headline from their chosen, labeled semantics.
Preserve CFW precedence if that remains the adopted ladder. Test conflicting
CFW/NWPS values, expiry, missing hourly points, and transitions to P-ETSS and
persistence. Do not silently promote NWPS into core alerts as part of this repair.

### R9 — P1 / release blocker: the production-dependency suite fails; CI masks it with skips

Evidence: `tests/test_outlook.py:186–205`, `forecast/outlook_sources.py:561–585`,
`.github/workflows/ci.yml:66–79`; [verification record](verification.md).

System Python: **238 tests, OK, skipped=3**. With the installed Barnacle venv
(which has eccodes): **238 tests, FAILED, errors=1**, no skips. The negative-budget
qmd test expects the first bucket to run, but the implementation skips every
bucket then raises `RuntimeError: NBM qmd: no buckets decoded`.

CI installs type-check dependencies, not the production GRIB decoder, despite the
skip message claiming “CI installs it.” GitHub CI run **35890370985** is green
with exactly the same three skips. Therefore “238 tests green” does not establish
the tested decoder/budget path. The decoder's two fixture parsing tests do pass
when actually executed; this is not evidence that all GRIB decoding is broken.

Repair: choose the intended exhausted-budget behavior and test it consistently;
install the decoder dependency in an appropriate offline CI job and fail if
required adapter tests skip. Also budget discovery itself: qmd discovery occurs
outside the request-loop timer and warm.main may perform it twice. Run the full
production-dependency suite before citing a passing candidate.

### R10 — P2 / follow-up: artifact semantics and writer/gate parity remain incomplete

Evidence: `forecast/check_artifacts.py:36–44,314–372,574–610`;
`tests/test_csv_ledgers.py`, `tests/test_outlook.py:430–450`; BACKLOG parity loop.

The outlook ledger has a header/width gate but no dedicated numeric/timing/source
semantic branch. `validate_forecast_metadata()` ignores `outlook_7d`: probe M1
substitutes a negative horizon, invented model stamp, and a string for the series,
and the metadata gate reports no errors. General strict JSON catches syntax/NaN,
not wrong scientific contracts. `data/outlook_cache.json` and qmd inputs are not
subject to the strict docs JSON pass. Existing writer parity work remains only
partial; the original 42-hour outage lesson is still open. A fresh-looking artifact
is not equivalent to healthy source coverage.

Add a focused outlook schema/semantic gate and real-writer round trips covering
JSON and ledgers, canonical timestamps/DST, duplicate identity, finite values,
source health, and interval/horizon consistency. This can be staged after release
repairs if those repairs carry direct regression tests. Add a workflow-level
failure signal for hourly gate failures; the existing external watchdog checks
forecast age and nowcast workflow health, not each hourly workflow failure.
Keep append-only history and documented residual outage windows intact.

### R11 — P2 / inherited follow-up: “Landmarks today” actually describes the worst 72-hour tide

Evidence: `forecast/flood_forecast_daily.py:3601–3627,3669–3710`;
`forecast/rendering.py:1162–1178`; live landing and committed forecast at 16:14:10Z.

`_unified_landmark_rows()` takes `forecast.depths_in`, which belongs to the overall
peak. The public September 23 table says “Today” and **13.9 inches at SW grate**,
but that value is the **September 25 19:40** tide; the September 23 tide row is
6.7 inches and the September 23 continuous maximum is 11.5 inches. A calendar
label is asserting the wrong scope. This predates the reviewed commits.

Repair by using the actual station-day worst-water result or labeling the table
with its explicit target date/window. Update site and email copies together and
test a higher peak two days later. The “LOW TIDES IN NEXT 24H” block similarly
contains lows through September 26 in the observed September 23 page; scope labels
should come from the actual filter. These are concrete examples for the wider
scope-label sweep, not reasons to change model constants.

### R12 — P2 / measurement follow-up: error statistics are gauge skill, not general flood uncertainty

Evidence: `forecast/flood_forecast_daily.py:2810–2860,3107–3211`;
`forecast/rendering.py:3119–3125,3338–3348`; `outlook.py:249–254`.

The new error line is derived from predicted Sandy Hook peak MLLW versus observed
gauge peaks. It does **not** score rain-driven street depth, burst scenarios, or
the new outlook inputs; the forecast rows span historical model/input regimes.
The page's generic “Forecast error so far” and `±MAE` can read like a forecast
interval even though MAE supplies no coverage probability. Hourly issuances are
correlated; the long sentence distinguishes tides from rows but table `n` does not.
Removing low/medium labels is reasonable; replacing them does not validate the new
rain/surge guidance. The landing also explicitly disables the summary line with
`include_confidence=False`, contrary to the commit's landing-banner claim (the
per-tide error column is present).

Use “past Sandy Hook tide-peak MAE,” identify n as predictions/distinct tides,
and keep rain skill separate. Prefer `MAE 0.xx ft` over an unexplained ± interval;
show lead/window/source support. Do not present summed six-hour NBM percentiles as
a calibrated daily percentile: `p90_day_in` is a sum of marginal percentiles, not
the percentile of a daily sum. That field is currently not the displayed high-end
scenario, which correctly uses a six-hour maximum. Preserve that distinction and
rename/document the crude aggregate before exposing it.

## What passed and should be retained

- Both frozen numerical replays pass unchanged. Tank constants, fill correction,
  calibration set, and 18-landmark ladder remain intact. Class-(b) treatment is
  appropriate if repairs correct input/policy behavior without retuning physics.
- CFW raw-product repair parses the real captured September 23 bulletin and cuts
  off before the next gauge. Acquisition failures remain explicit. Committed/live
  core source is `nws-coastal-flood-product`, with the 08:28Z issuance recorded.
  This verifies parser operation, **not** forecast skill before the event is scored.
- Overnight exemption uses the station helper; its direct and delivery tests pass.
  Alert-window tests keep day-six outlook tides out of core alert rank/text.
  SMS retains its independently gated imminent-impact role.
- Existing alert retry/partial-success, freshness, nowcast actual-writer-to-consumer,
  dispatch fail-closed, station-time, DOM/accessibility, escaping, and model tests
  passed in both suite runs apart from the identified qmd-budget failure.
- Publish gate and both replay commands pass. Protected CSVs lost no prior row:
  observations 184→184; predictions 15,315→15,485; accuracy 117→117.
- No new photos in the reviewed diff; no tracked `*-original-unpublished.*` or
  credential-shaped `.env/.pem/.key/.p12/credentials.json` paths in the filename
  check. This is not a comprehensive secrets or historical-photo audit.
- Live landing, town map and outlook load. Both worst buttons function for the
  current tide-dominated event; measured error columns, source labels, high-end
  band descriptions and shadow scoreboard are visible. No console error was
  observed on the town map. Static accessibility gate passes. Browser tests did
  not simulate a storm, change host time zone, or test the actual Scriptable app.
- GitHub CI, hourly forecast, nowcast and warm job sampled successfully. A healthy
  run is evidence of recovery and ordinary-path operation, not failure-path proof.

## Promotion acceptance contract

1. Claude's independent reply must confirm/dispute each R1–R12 with evidence.
   R1–R9 need repair and candidate verification before a PASS recommendation.
   R10–R12 may be explicitly scheduled follow-ups; do not silently mark them closed.
2. Add meaningful regression checks for the reproduced failure conditions. Run the
   full suite with production decoder dependencies, both unchanged goldens, the
   artifact gate, and CI's pinned lint/type checks. Verify generated and deployed
   artifacts, including low-tide rain and degraded-source cases on both maps.
3. Prepare `model/v0.10.5.md` with Inputs & policy: all sources/units/validity,
   source precedence for cards/curves/maps, cache/source-age bounds, partial-input
   handling, 168-hour coverage, rain interval/burst/p90 assumptions, shadow sample
   definition and promotion policy, and the 48-hour alert boundary. Preserve
   owner-defined channel roles and the distinction between scenario and probability.
4. In the promoting commit, archive v0.10.4 and repair its relative links; update
   CURRENT_MODEL_VERSION, tests' version expectations, README, ledger README,
   AGENTS/HANDOFF/PLAYBOOK pointers and other live references. Keep historical
   ledger rows and model fixtures unchanged. Explicitly document the already-live
   v0.10.4-stamped policy/input interval starting with `8e686a4f1` (and outlook
   `bfd39b533`); never rewrite it to imply prior approval.
5. Obtain the repaired candidate's independent review and record John's promotion
   DECISION. Cite their actual scope and chronology in the promotion commit.
   No final v0.10.5 spec/cutover commit exists in this reviewed candidate, so this
   audit cannot verify their eventual atomicity or links in advance.
6. Commit → gate → push; on race, rebase or abort → gate again → retry. No mass
   staging, ledger replacement, alert-state reset, or unrelated worktree changes.

Open operational residuals remain as recorded: live storm-path dispatch validation,
24/7 external trigger/awake-hours watchdog limits, duplicate-over-miss delivery
without a durable outbox, writer/gate parity, widget re-copy, and independent
compound-event testing. They do not license retuning during this event. Keep the
NWS-versus-observed event collector active; do not lift source validation claims
on the basis of parser success or a broken READY counter.
