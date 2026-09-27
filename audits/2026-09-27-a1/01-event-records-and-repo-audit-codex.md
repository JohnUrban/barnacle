# September 25–27 flood records and repository audit

Author: Codex (GPT-6). Date: 2026-09-27. **Status: OPEN — independent reply required.**
Reviewed main `10ea6c2a29a9a9be1869adf78665b29c1685e96a`; recent-change baseline
`fa3e041c5dd634d038a7b92e2db2baa599237df9`. No production behavior changed by
this audit. Findings include both new work and pre-existing weaknesses exposed
by it; they are not all regressions introduced by the event-support agent.

## Assessment

The measurements are substantially preserved, the two production fixes are
reasonable, and no model coefficient or frozen wind candidate was changed.
The event work is nevertheless **not complete enough to close**. Live raw-note
capture did not follow the existing instructions. Some scientific statements
are stronger than their evidence, the standard post-event work is unfinished,
and downstream aggregation does not reliably preserve each flood episode.

The gate evidence explains why a good bay forecast can be a poor street timing
forecast. It does not establish that every Barnacle surface was correct, that
the gauge had no bad samples, or that a gate formula is ready for production.
Retain the observations and the useful fixes; do not revert the week wholesale
or fit a gate threshold from these few episodes alone.

## Scope and checks

Read the charter, playbook, living documents, recent audits, both new event
folders and plot code, recent production/test diffs, ledger consumers,
hourly publication/alert flow, and the unmerged as-issued evaluator's event
classification/reporting. Compared the event measurements against the
repo-specific private conversation record to distinguish receipt time from
measurement time. That private transcript is **not published** here. The
canonical measurements and file creation commits are public primary records.
Social implementation was not re-reviewed; its previous local-only status is
unchanged. This is not an exhaustive security audit or a new model calibration.

- Full main test discovery in an isolated archive: **342 tests OK, one skip**.
  Skip: `test_retained_verified_inferred_rows_are_excluded_R5_Q1`, because the
  gitignored local training re-pull is absent. No production fixture writes.
- Read-only replays `reproduce_v0_10_1.py`, `reproduce_v0_10_3.py`, and
  `reproduce_v0_10_6.py`: **PASS**. Artifact gate: **clean**.
- All seven frozen wind files match the hashes in
  [the previous review receipt](../2026-09-24-a4/frozen-files.json).
- Main CI [36342005204](https://github.com/JohnUrban/barnacle/actions/runs/36342005204)
  passed on the reviewed head. Recent Pages and nowcast runs were succeeding;
  one superseded Pages run was cancelled. The hourly failure at
  [36237940041](https://github.com/JohnUrban/barnacle/actions/runs/36237940041)
  coincides with the documented September 26 ntfy incident.
- Parsed CSV comparison: observations **185 → 262 (+77)**, predictions
  **15,790 → 16,105 (+315)**, accuracy **119 → 123 (+4)**. All old rows remain
  in order; no exact duplicate among the 77 new observation rows.
- Inspected the four-panel PNG visually. Its basic contrast between bay and
  local measurements is useful, subject to R4/R5 below.

Reproduce deterministic probes with
`~/.barnacle/venv/bin/python audits/2026-09-27-a1/probes.py`.
[Results](probe-results.json), [source excerpts](source-excerpts.json), and
[notebook companion](audit-probes.ipynb) preserve the supporting calculations.
The probes pin the reviewed commits; they do not fetch changing observations.

## R1 — Live raw-note capture and handoff discipline were missed (medium)

**Existing rule, not a newly invented expectation.** [PLAYBOOK.md](../../PLAYBOOK.md)
live-support mode requires each report immediately in both the ledger and
`flood-measurements.txt`; its post-event recipe explicitly requires rain forcing,
gauge sanity against The Battery, analyses and plots. AGENTS also requires
prompt observation capture and current living documents.

The ledger was populated during the event. September 26's README first appeared
in `7014329dd` at 12:56 local. Both raw-note files, September 27's README and
the first four-panel plot arrived in `ebacf9e50` at 10:51 local September 27,
after the owner's request at 10:49. HANDOFF was not rewritten until `10ea6c2a2`.
Thus “nothing was recorded” would be unfair, but “the prescribed workflow was
followed” would be false.

**Receipt-time qualification:** the September 26 evening batch arrived at
22:41 local and was committed at 22:42 (`dde559104`); the September 27 morning
batch arrived at 10:43 and was committed at 10:44 (`65b84fcd9`). Do not charge
the agent with the elapsed time before those messages arrived. Sampling the
raw notes against those messages found the substantive readings preserved.
This is not a claim that every sentence or attachment has been reconciled.

The raw files say “VERBATIM as relayed live,” but are retrospectively assembled,
combine messages and normalize at least one AM/PM typo. Preserve the original
wording and identify normalization/assembly date; distinguish observation time,
receipt time, and uncertain time. Do not manufacture a contemporaneous record.
The dry September 25 check is held in the September 26 folder with a clear
heading; that is workable with an index and does not require arbitrary moves.

**Acceptance:** source-to-ledger reconciliation table, explicit provenance for
retrospective notes, and a short event checklist used at handoff. Follow the
existing rule rather than relying on agents to infer the pattern. Improve the
playbook's stale step 6 wording: it still says duration is not explicit, although
the production model now has a dynamic tank.

## R2 — Rain and gate hypotheses were promoted into facts (high)

[September 26 README](../../assets/observations/2026-09-26/README.md) labels the
rain calculation `[INFERRED]`, appropriately. The reviewed HANDOFF instead said
“Rain added ~2.4 in,” and presents a gate threshold/rate narrative with much
less qualification. The BACKLOG rain ledger entry calls the crest approximately
“tide 23.8 + rain 2.4.” That partition is **not an observation**.

The originating calculation held the base at **5.3 or 5.7 ft NAVD88** and drain
at **zero for the entire window**, applying the tank's 15-minute lag to sampled
rain. The audit independently reproduces peak increments **2.465 and 2.452 in
at 09:02** from the committed CSV. This verifies the sensitivity calculation,
not the inferred cause of the measured crest or post-gauge-peak rise. It does
not simulate the observed changing bay, gate state, local storage and drainage.
The 1.259-inch rain total is a six-minute rectangular sum of 65 samples; the
14:24Z frame is missing from an expected 66. The missing late frame does not
explain the computed 09:02 peak, but coverage and integration assumptions belong
in the analysis. The original analysis script was temporary; these probes now
make the simplified calculation inspectable.

Gate state is directly reported at September 26 18:19; the later report and
September 27 ~08:30 report say **almost certainly**. September 25 PM and
September 26 AM closure are inferred. Rising/falling hysteresis supports a
local hydraulic restriction; it does not by itself identify the gate's physical
overtopping elevation. The suggested 5.0–5.3-ft band also depends on uncertain
first-water time, gauge revisions, rain and other flow paths.

[September 27 README](../../assets/observations/2026-09-27/README.md) and the plot
say first porch-step top **equals** garage entry, then infer a 5.36–5.41-ft range.
Keep this as an event-derived proxy until a fixed feature is surveyed, following
the existing landmark rule. No new elevation constant is justified yet.

**Acceptance:** qualify these claims everywhere, preserve historical prose with
an erratum, commit the actual analysis, and compare explicit competing scenarios.
Obtain gate operation/geometry evidence where available; do not convert a
visual association into a calibrated leak/overtopping formula. This audit
corrects HANDOFF prospectively and appends a BACKLOG qualification; the event
author should respond before rewriting the event analysis.

## R3 — Three floods are retained in the ledger but not represented consistently (high)

“Event #10, rounds 1–3” has a historical precedent: September 13's Event #9
also has rounds. The label itself does not discard data. The missing piece is
an explicit, machine-readable distinction between **storm** and **flood episode**.

| Proposed episode alias | Observation status | Peak derived from existing landmark rows |
|---|---|---|
| 2026-09-25-pm | Negative observation window; no local flooding reported | No measured water level; not a fourth flood |
| 2026-09-26-am | Flood, Event #10 round 1 | 5.701 ft NAVD88 |
| 2026-09-26-pm | Flood, Event #10 round 2 | About 4.223 ft NAVD88; curb-depth range represented by midpoint |
| 2026-09-27-am | Flood, Event #10 round 3 | 5.618 ft NAVD88 |

Retain Event #10 as a storm alias and both dated folders. Add stable episode
IDs and explicit observation windows, peak intervals, source rows and gate
confidence in a sidecar registry. Do not renumber historical events or alter the
append-only CSV schema casually. One storm can contain three floods and an
informative dry window. These are separately recorded floods, **not automatically
three statistically independent storms** for the wind trial.

Concrete downstream issues:

1. `_flood_peaks_chart_data` in
   [the production renderer](../../forecast/flood_forecast_daily.py) takes the
   maximum per **calendar day**. September 26 AM therefore hides September 26 PM.
   This predates the new labels, but confirms the owner's underrepresentation
   concern. Label a daily maximum as such and provide episode-level points or
   drilldown; don't silently imply every flood is represented.
2. Heron's unmerged `cd17a5a14` classifier accepts 63 new rows and groups them
   into **one** cluster using consecutive gaps of at most 12 hours. Storm
   clustering can be right for uncertainty estimates. Its per-event reporting
   also looks up established peaks by the first observation date, however;
   adding one date-keyed peak would not describe these three episodes. Keep
   separate cluster and episode identities when extending evaluation.
3. All 77 new `model_predicted_depth_in` fields are blank. Consequently **zero**
   new rows qualify for `_load_outcome_depth_rows`' paired depth-accuracy view.
   This is preferable to inventing predictions, but logging alone has not
   completed as-issued evaluation. Join immutable issuance archives to measured
   outcomes in a derived, provenance-bearing table; never backfill a hindcast
   as though it had been issued.
4. `history/data/342_bay_flood_events.csv` is a historical gauge-derived catalog,
   not the local measured-episode registry. The old `data/labeled_events.csv`
   and frozen calibration lists serve other purposes. Do not blindly append
   these episodes to every file named “events” or change frozen fit goldens.

**Acceptance:** registry plus consumer inventory; tests must retain the smaller
September 26 PM episode, identify the negative window, and keep storm counts
distinct. Revisit Heron's October 9 checkpoint early for this informative event,
without assuming its archive coverage is sufficient or its science is closed.

## R4 — Gauge provenance and lag statements are inconsistent (high)

The September 26 README says a revised gauge peak of **5.83 ft at 08:54** and
a street crest about **15 minutes later**. Its committed plot cache instead
peaks at **5.852 ft at 08:36**. Relative to the reported 09:06–09:13 street
plateau, that is **30–37 minutes**. These are different source versions or
interpretations; the report must identify which one it uses. Sampling resolution
and flat peaks also limit any precise lag claim.

There really were suspect preliminary gauge values as well as local gate
effects. [Preserved NOAA excerpts](source-excerpts.json) from Codex's September
26 diagnosis, converted with the unchanged -2.82-ft datum offset, compare with
the later committed cache as follows:

| Local time Sep26 | Initial preliminary gauge, ft NAVD88 | Later cached gauge, ft NAVD88 |
|---|---:|---:|
| 05:30 | 4.633 | 4.225 |
| 05:36 | 4.856 | 4.216 |
| 06:30 | 5.368 | 5.036 |
| 06:42 | 7.074 | 5.072 |

The original rows carry NOAA preliminary `q=p` and sample-quality fields;
the event cache strips them, retains neither retrieval time nor original
response, and uses station-local transport instead of the required GMT.
Later cached values must not be called final verified NOAA data merely because
they differ. Exact retrieval time of the earlier temporary pull was not retained
either; that is a limitation of my own earlier diagnosis, now explicitly recorded.

The event plot uses raw cached values without despiking and contains no
committed Battery comparison. Earlier conversational checks are not a
reproducible event-wide sanity analysis. PLAYBOOK explicitly requires this check.

**Acceptance:** preserve raw and quality-controlled gauge versions, retrieval
metadata and Battery comparison; distinguish as-seen input from later outcomes;
recompute peak/lag intervals consistently. Never erase the as-issued history
with a revised download or use bad early samples to fit gate behavior.

## R5 — Public meaning and plot conventions still overclaim street observations (high)

`_render_water_series_section` still says the gray bay line is a true
observation and, via “the drains' proven bay-coupling,” tide-pathway street
water. The gate observations invalidate unconditional bay-to-street equivalence.
The station measures the bay; local depth/timing is an estimate. Audit that
meaning across the website, widget, maps and alert descriptions under rule 8,
with the same forecast numbers until a separately reviewed model change.

The new event PNG places **all** qualitative known-landmark reports at the SW
grate line, including reports of water over higher landmarks. Its legend calls
them qualitative, but that marker position and “e.g. no flooding” legend can
make wet reports look dry. Use a separate report-time strip or correctly marked
bounds. The global “gate closed” title and “seen ~21:58” overstate some reports;
carry their individual confidence. Add the prescribed rain panel and measured
street/bay/quality distinction; the four-panel overview is useful supplementary
work, not the whole required analysis.

The public nowcast receipt at **2026-09-27T18:56:25Z** retains a daily maximum
of **39.0 inches at 06:40Z (02:40 local)**. It is a model-derived maximum, not
the later tape-measured ~25.2-inch crest. `nowcast.py` retains maxima from prior
local and published artifacts, so a contaminated value can survive correction
of the underlying series. This audit has not established the origin of that
particular 02:40 value: trace its inputs before calling it a confirmed sensor
spike or deleting it. Do not present it as a measured street maximum.

**Acceptance:** clear source labels on all relevant arms, truthful confidence
in the event figure, traceable daily maxima with a repair policy for rejected
inputs. No silent conversion of gauge observations into street measurements.

## R6 — Timestamp and range handling are not robust (medium)

All 77 new ledger rows use naive local timestamps despite the offset-bearing
rule. The chart repair truncates offsets/seconds and compares strings against
offset-bearing series endpoints. An actual renderer probe supplies readings at
07:00 and 07:18 with a series beginning 07:00-04:00: **only 07:18 is plotted**.
The observation exactly on the left boundary disappears. The new regression
test uses naive times and misses this case.

The event plotting script directly compares naive bounds to parsed ledger
times: a conforming offset-bearing row raises `TypeError: can't compare
offset-naive and offset-aware datetimes`. Its current success depends on the
new rows violating the timestamp convention. Use the shared station parser for
both bounds and observations; test offset inputs, boundaries and DST handling.

Several uncertain observations are encoded as precise scalar times/depths with
uncertainty only in prose: 1.4–1.5 becomes 1.45; 0.5–1 becomes 0.75; a 21:20–21:40
onset window becomes 21:30; the September 25 negative check uses a gauge-peak
time while explicitly admitting its observation time is unconfirmed. That can
be a storage compromise, but downstream classification/scoring must preserve
intervals and surrogate-time status rather than treating midpoints as exact.

**Acceptance:** parser repairs plus additive normalized interval/provenance
records. Preserve the original ledger; do not rewrite 77 historical rows merely
to make their format look compliant. New entries should use offset-bearing times.

## R7 — Alert failure can still block forecast publication (high, pre-existing)

The ntfy Latin-1 title fix in `1a52c4f22` is justified and tested. It addresses
the specific header-encoding failure without altering the model or UTF-8 body.
The tape-dot fix in `54044b231` also correctly removes max-per-slot displacement,
subject to R6. Both fit the documented no-bump bug-fix class.

However, `main()` still exits with code 2 when no requested alert channel
succeeds. The hourly workflow's gate and commit steps require normal prior-step
success. Thus an alert transport failure can still prevent already-generated
forecast artifacts from publishing. Retaining retry eligibility is good; making
forecast freshness depend on transport success is not. The specific ntfy repair
does not close this broader operational failure mode.

**Acceptance:** separate delivery health/retry status from validated forecast
publication. Test complete and partial channel failures, state persistence and
publication eligibility. Do not simply mask all errors or mark alerts delivered.
This deserves a focused operational fix and independent review.

## What remains and who should do it

1. **Independent responder:** answer R1–R7 individually with evidence. Correct
   immediate source/confidence wording and establish the episode index first.
2. **Event analyst:** finish the source reconciliation, gauge/Battery QC, rain
   forcing for both mornings, standard hydrographs, episode-specific peak/onset/
   recession comparisons, and issuance-time versus hindcast evaluation. Mark
   unavailable inputs explicitly. A new all-anchors plot may be descriptive;
   adding a calibration anchor requires separate justification.
3. **Implementation agent:** targeted timestamp and alert/publication fixes;
   update every relevant arm for any meaning change, regenerate and visually
   verify affected pages, then gate/test. No model bump for a restoration fix;
   a gate model, new input or alert policy follows the version/review rules.
4. **Owner/field follow-up:** operating history and gate geometry/photograph
   provenance, when available; survey neutral fixed landmarks or garage lip
   separately. Do not ask the owner to reconstruct measurements already present.
5. **Model research only after the evidence pass:** compare ungated baseline
   against explicit gate scenarios across all four windows, including the dry
   one. The September 25 guidance-first proposal remains an offline candidate:
   better bay guidance cannot alone fix local gate timing. No blanket rollback,
   gate formula, new warning policy or wind-trial change is authorized here.

The prior Codex same-input replay finding remains narrow: older implementations
also produced the high bay-derived curve for the September 26 snapshot. That
does not validate local timing, and later flooding does not make the earlier
dry/below-curb reports erroneous. Preserve both; their disagreement is useful
evidence about the transfer from bay level to street water.

This audit updates discovery documents so a cold-start agent sees the open
work. It does not close itself, and passing tests must not be used as a
substitute for the independent reply or the missing scientific evaluation.
