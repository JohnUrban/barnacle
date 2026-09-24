# Round 01 — wind/pressure research needs revision; candidate remains promising

Codex, 2026-09-24. **Audit OPEN; independent reply required.**
Reviewed Claude's `6c203ef4e` and `3bb7f74d1` research against main
`c6566b4a2`, the retained local input files, and the vendors' documented
contracts. This is a research review, not approval of a production wind term.
The v0.10.6 release audit remains CLOSED. No production formula changes here.

**Assessment: Needs revision. Coverage partial: both studies reviewed; historical issuance availability
and raw-source quality flags remain unverified.** Both original reports reproduce byte-for-byte, but reproducibility
alone hides a serious clock mismatch and a scoring-mask error. Independent
corrected round2 calculations still favor a forecast-forcing candidate at
24–30 hours. Preserve the work, correct it, then test a deployable candidate.

## Prioritized findings and proposed fixes

### R1 — P1: round1 joins station-local water to UTC weather

`history/scripts/pull_sandy_hook_history.py` requests `lst_ldt`; its naive
local timestamps survive `build_dataset.py` into the historical parquet.
`pull_sandy_hook_met.py` requests `gmt`. Both research scripts reindex the
weather directly onto the historical water timestamps without conversion.
This affects round1 and round2's **transferred coefficients** (not round2's
forecast-era refit, whose water/weather/forecast timestamps are all UTC).

[VERIFIED] Overlap against the UTC round2 archive establishes the offset
numerically: January astronomical predictions differ by MAE **2.692 ft** at
identical clock labels and agree exactly after +5 h; July differs by **2.382 ft**
and agrees exactly after +4 h. Example: legacy `2025-01-15 00:00` astronomy
1.278 ft is UTC `2025-01-15 05:00`, not UTC midnight (3.784 ft).

The attached [alignment diagnostic](check_time_alignment.py) uses the station
time helper, explicit legacy fold=0, drops nonexistent spring wall times,
and purges cross-split targets before rerunning round1. It does not repair the
raw archive or recover the lost second fall-back hour. Its
[output](round1-aligned.txt) keeps theta=70°, but changes the 24-h future-observed
model's MAE from **0.307 to 0.277 ft overall**, **0.416 to 0.347 ft in storm
starts**. Pressure coefficients also change substantially. The signal becomes
stronger; the original numerical/physical interpretation is still invalid.

**Fix (Proposed):** canonical UTC water/weather join with explicit time metadata
and winter/summer/DST checks; rerun round1 and the transferred model. Retrieve
GMT source history where exact DST recovery matters. Append an erratum; retain
original reports. Do not infer that poor transfer is solely a station-versus-grid
problem until the misaligned coefficients are replaced. This does not establish
a production v0.10.6 clock bug: its live transport uses GMT and its simple decay
has no wind/pressure join. The older decay study's local-hour DST limitations
are a separate historical-data qualification, not evidence to revert the release.

### R2 — P1: round2 high-tide and plug-band views classify the wrong hour

`surge_forecast_wind_test.py` scores `s.shift(-k)` using unshifted `hi` and
`plug` masks. These are conditions at issuance t, unlike round1's target t+k
views and the intended drain-band question. Storm-start selection at t is
correct and should remain there.

[VERIFIED] The independent [recomputation](recompute.py), with explicit forward
wind windows and no imports of either study's helpers, gives the following
**target-time, purged-training** MAE in ft for 24 h:

| View | Decay baseline | GFS refit | ECMWF refit |
|---|---:|---:|---:|
| All hours | 0.2892 | 0.2369 | 0.2349 |
| High tide at target | 0.2825 | 0.2315 | 0.2330 |
| Low tide at target (additional exploratory view) | 0.2935 | 0.2342 | 0.2280 |
| Plug band at target | 0.2845 | 0.2401 | 0.2420 |
| Surge >=1 ft at issuance | 0.4771 | 0.3549 | 0.3552 |

The 24–30 h success criterion still holds for both sources. However, **“better
in every view at every lead” is false**: ECMWF's 6-h target plug-band MAE is
**0.1882 vs 0.1860 ft**. This is a tiny loss, not a catastrophic failure, but
it defeats that categorical claim. GFS's 6-h plug-band gain is only 0.0046 ft.
The plug-band subset is diagnostic conditioning on the realized target; it
must not become a predictor requiring future observations.

**Fix (Proposed):** shift high/plug masks to t+k, retain storm masks at t,
include target low tides, report counts and correct all dependent tables/prose.
The review's [JSON](recomputed.json) contains every lead and both sources,
including the original-mask reproduction for comparison.

### R3 — P1 methodology, small measured effect: training labels cross the split

Both scripts select training by the starting hour alone. The last k training
issuances use outcomes in the scoring period; this is not a fully held-out
boundary. Future-observed training features cross it too.

[VERIFIED] In round2, purging target times >=2025-05-01 removes exactly
6/12/24/30/48 fitted rows at the respective leads. Corrected gains survive;
this leakage does **not** explain the reported improvement. Round1's alignment
sensitivity also purges the corresponding 2016 boundary.

**Fix (Proposed):** enforce train start AND target < split, including conditional
tau fitting and the transfer fit. State scoring dates as issuance dates with an
exclusive end (`2026-09-21` means through September20); future targets may extend
past that issuance cutoff. The baseline tau was already selected using broader historical comparisons;
this is a split for the fitted forcing coefficients, not an untouched evaluation
of the entire model-development process. Freeze a genuinely new evaluation period for further
model/source selection; these inspected periods are no longer untouched tests.

### R4 — P1: forecast age and guaranteed live improvement are overstated

The plan says forecasts were “24–48 h OLD at use” and live improvement should
be at least this large. The [Open-Meteo Previous Runs contract](https://open-meteo.com/en/docs/previous-runs-api)
describes lead offsets relative to **valid time**, not age at Barnacle issuance.
For a 24-h window using day1, nominal ages at t range from 23 h to 0 h;
for a 30-h window using day2, 47 h to 18 h. Each window combines different
forecast origins. The documented semantics support nominal initialization
no later than t, but the cached values do not prove actual publication or
retrieval availability at that instant. No post-t initialization leak is
established here; operational availability remains unproven.

Fresher guidance need not improve this particular fitted predictor, especially
when the feature construction and product change. Observed-future scores are
an oracle-style benchmark, not a mathematical upper bound on every forecast
model's skill. Retire both guaranteed-bound claims.

**Fix (Proposed):** distinguish model initialization, publication, retrieval
and valid time; replay the precise live source and window-selection policy,
including latency/outage behavior. The [Single Runs API documentation](https://open-meteo.com/en/docs/historical-forecast-api)
describes run-preserving data and its shorter coverage, so check availability
before promising the existing training span. Do not silently replace the tested
`gfs_seamless` or `ecmwf_ifs025` with NWS grid wind, direct GFS, another ECMWF
product or a fresher stitched feed. Also replay the production mean policy: the study uses a trailing 365-day
mean through t-1, while live v0.10.6 uses a cached 364-day verified-data window
ending roughly three weeks back. Source-specific refitting remains sensible,
but the current transfer comparison also needs R1 repaired.

### R5 — P1 provenance: the claimed predeclaration has conflicting timestamps

The same plan says round2 was written **23:55 before results**, labels results
**23:50**, and was committed in `3bb7f74d1` at **23:49:13 EDT**, both author
and committer time. This cannot establish the claimed chronology. Round1's
plan/results first appear together as well; a narrative assertion is not an
independently timestamped preregistration. This is an evidence problem, not
proof about the author's intent or which work actually happened first.

**Fix (Proposed):** append an honest correction with primary session evidence
if available; otherwise label the timing unverified and the research exploratory.
Record the next plan before looking at its evaluation results. Also record the
actual deviations: M2 uses wind terciles only (not the planned pressure classes),
and M3 includes a pressure-anomaly term and intercept in addition to wind stress
and pressure change. “Implements ... exactly” currently overstates fidelity.

## Robustness, evidence limits and next implementation gate

[VERIFIED] The forecast-era files have no duplicate timestamps. Their forecast
columns have no missing values within their own archived spans; weather
observations do have gaps. The study falls back to M1 on unavailable feature
vectors and keeps those eligible outcomes in scores. Its wind average accepts
as little as 75% of a window (rounded down); this partial-window policy needs
explicit live labeling and testing. Retained parquet SHA256/coverage/null counts
are in `recomputed.json`. Fetchers discard weather/water quality flags and do
not retain issue/publication metadata; this review does not certify every raw
NOAA/Open-Meteo measurement. The [NOAA API contract](https://api.tidesandcurrents.noaa.gov/api/prod/)
and fetch parameters support the stated units/time conventions, not universal
quality of returned values. Recent round2 water includes preliminary values.

There are **12,192 scored issuance hours**, **1,591 with surge >=1 ft**,
not 1,591 independent storms. Additional, explicitly post-hoc checks in this
review use fixed seven-day resampling blocks: GFS's 24-h mean absolute error
gain is 0.0523 ft overall (exploratory interval 0.0368–0.0686), 0.1222 ft in
storm starts (0.0556–0.1892). These intervals describe this retained sample and
block choice, not guaranteed future performance. Monthly means occasionally
lose (GFS May2026 at 24/30 h; ECMWF June2026 at 24 h). No storm-event attribution,
rare-tail safety, independent wet-street validation, or new untouched holdout is
claimed. Pressure-versus-wind causal contributions are not isolated by this fit.

Recommended sequence for Claude:

1. Reply finding-by-finding and correct R1–R5 with immutable corrected reports,
   preserving this audit and the original evidence. Reproduce the attached
   diagnostics independently. Recheck transferred coefficients after alignment.
2. Specify a live source with a matching archived construction; archive raw
   forecasts with issue/retrieval times. GFS is a reasonable first engineering
   candidate, but the tiny GFS/ECMWF differences do not establish a universal winner.
3. Predeclare the next evaluation: target high/low/plug bands, rain-tank effects,
   storm episodes, signed underprediction and large errors, missing-source
   fallback, full hourly continuity and transitions. Compare against current
   production as well as M1: the seven-day view already uses NWS/P-ETSS guidance;
   beating simple decay does not justify replacing that guidance wholesale.
4. Build offline/shadow first. A live formula/input change gets a separate model
   version, replay goldens, all relevant surfaces, independent candidate review
   and John's DECISION before promotion. No fresh owner choice is needed merely
   to correct this research.

## Cleanup accompanying this review

BACKLOG now reflects the 36-h v0.10.6 policy, corrected rain evidence, retired
confidence labels, remaining scientific questions and the actual widget-copy
status. The outlook scoreboard renders its existing cohort metadata, explains
why source counts differ, and labels its overall count as the outlook line.
Numerical forecasts, ledgers, alert state and widget source are untouched.
Only the outlook page carries this scoreboard; other display/alert arms have
no cohort comparison to update. Widget v7.28a -> v7.29a removes the driveway
proxy from the landmark ladder, as shown by `96c9a0f50`; no curve-code change.

## Coverage and reproducibility

Scope units are the two research studies, not individual hours. Counts overlap
across categories and do not represent an accuracy percentage. Original reports
were rerun exactly; round2's refit was independently implemented; round1's UTC
run is a focused sensitivity rerun using the original fitting code. Source
quality and actual availability limits above remain explicitly unverified.
Original research scripts/reports remain unchanged; the plan gains an erratum
pointer and this review supplies corrected diagnostic artifacts.

### Research quality

| Category | Observed defects | Assessment |
|---|---|---|
| Research usefulness and completeness | 2 / 2 | Both studies support continued research, but require R1–R5 before deployment claims. |
| Analytical clarity | 2 / 2 | Original timing, cohort and bound wording needs correction. |
| Visual/interaction consistency | N/A | N/A: the research artifacts are text tables and scripts. Not applicable: N/A: the research artifacts are text tables and scripts. |

### Analytical correctness and robustness

| Category | Observed defects | Assessment |
|---|---|---|
| Source authority and confidence | 2 / 2 | Time provenance is defective; full raw-source quality and publication availability remain unverified. Partial review: 2 scoped items have incomplete or stale evidence (round1; round2). |
| Value accuracy | 2 / 2 | Original outputs reproduce; R1 clock alignment and R2 target masks change the intended comparisons. |
| Within-chart agreement | N/A | N/A: no research charts. Not applicable: N/A: no research charts. |
| Complete source details | 2 / 2 | Missing clock/quality/issuance metadata limits the retained research evidence. |
| Cross-artifact consistency | 2 / 2 | Plan, code and prose disagree on chronology/features or scoring views. |
| Data-quality controls | 2 / 2 | R1 timezone mismatch and R3 boundary leakage; corrected gains survive. |
| Conclusion support | 2 / 2 | Both studies overstate bounds; round2 still supports a 24–30 h candidate after correction. |
