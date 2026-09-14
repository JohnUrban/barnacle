# Comprehensive repository audit — 2026-09-14

**Author:** OpenAI Codex (5.6 Sol High)

**Status:** OPEN — awaiting independent reply from a different agent

**Audit snapshot:** production source through commit
6f90326f6edfcd7b31482598c8950628eef1c6d6; data/artifact snapshot
753bb1e79617be69cf34b42c87a3e5e8c0157e4f, generated through
2026-09-14 13:51 UTC. GitHub Actions health was checked through
2026-09-14 14:14 UTC.

This is a read-only audit. No production code, model constants,
artifacts, ledgers, or operational state were changed. Findings should
not be closed or remediated until an independent reviewer has checked
the evidence in accordance with audits/README.md.

## Executive summary

Bay Ave Barnacle is serious, evidence-driven production flood-warning
software rather than a demonstration project. It combines two distinct
flood mechanisms:

- Tide-driven flooding from NOAA Sandy Hook astronomical tides,
  observed surge persistence, and NWS coastal projections.
- Rain-driven flooding from NWS QPF and MRMS radar through a dynamic
  stage-storage tank with rainfall-delivery lag, head-dependent
  drainage, and recession.

It translates those mechanisms into predicted water depth at 342 Bay
Avenue across 19 landmarks: 18 surveyed or established landmarks plus
the cross-fit driveway_central threshold observable. The current frozen
model is v0.10.2; its physics are unchanged from v0.10.1.

The project has unusually rich empirical history: tape measurements,
photographs with EXIF timing, radar reconstructions, append-only as-run
predictions, field observations, and event postmortems. Nine measured
flood events are now discussed, while the frozen v0.10.1 fit retains
six formal anchors.

The hydrologic core is thoughtfully documented and protected by useful
regression fixtures. The most consequential defects are in the newly
changed alert and scheduler boundary. Several demonstrated bugs can
cause a missed imminent SMS, conceal a failed workflow dispatch, or
treat obsolete gauge data as current. The 2026-09-13 outage hardening
repaired the immediate stale-commit failure but did not create genuine
scheduler independence or failure visibility.

## What the repository contains

- Production Python application with an hourly forecast and
  approximately ten-minute radar nowcast.
- Public Pages site, JSON APIs, iOS Scriptable widget, per-tide pages,
  archives, charts, and a nine-town street map.
- ntfy, email, and email-to-SMS alert rails with deduplication, caps,
  quiet hours, and an imminent-impact SMS policy.
- Tide pathway: NOAA astronomy plus observed surge persistence or an
  NWS coastal projection.
- Rain pathway: NWS QPF for forecast guidance and MRMS radar for live
  nowcasting.
- Dynamic pluvial tank calibrated with field observations, a fixed
  15-minute lag, and approximately 17-minute reservoir e-folding.
- Nineteen property landmarks ranging from the lowest grate to porch
  elevation.
- Strong provenance culture: append-only ledgers, photographs, event
  reports, frozen reproductions, and independent audit protocol.
- 1,495 tracked files and an approximately 348 MB checked-out tree,
  dominated by approximately 208 MB of photographic assets.
- Existing formal audits are closed and have independent replies. No
  pre-existing unmatched report was found.

Data snapshot:

- data/labeled_observations.csv: 184 rows.
- data/predictions_log.csv: 14,348 rows representing 2,506 runs.
- data/forecast_accuracy.csv: 112 rows.
- data/labeled_events.csv: 42 rows.
- data/observed_peaks_cache.csv: 227 rows.
- data/nowcast_heartbeats.csv: 336 rows.
- docs/archive/: 113 daily JSON/HTML snapshot pairs.

At the snapshot, the live forecast was v0.10.2 with no degraded inputs.
The radar nowcast was fresh, healthy, and inactive.

## Verification performed

- Python compilation passed for forecast, tests, history/scripts, and
  analysis.
- All workflow YAML parsed.
- All repository shell scripts passed Bash syntax checking.
- git diff --check passed.
- forecast/check_artifacts.py passed.
- history/scripts/reproduce_v0_10_1.py reproduced the frozen constants,
  24-point RMS, six hindcasts, and version cutover exactly.
- All 111 unit tests passed.
- A coverage run measured approximately 35 percent statement coverage
  across forecast/. flood_forecast_daily.py was approximately 35
  percent, rendering.py 16 percent, nowcast.py 62 percent, and
  nws_surge_parser.py zero percent.
- The latest 300 GitHub Actions runs spanned approximately 17 hours 20
  minutes: 102 CI, 61 nowcast, 18 forecast, 117 successful Pages, and
  two cancelled Pages runs. No run in that sample failed.
- Targeted adversarial fixtures demonstrated the producer/consumer
  field mismatch and validation gaps described below.

## High-severity findings

### H1. Projection-only imminent SMS alerts are disconnected

**Evidence**

- forecast/nowcast.py:443-446 writes peak_proj_in.
- forecast/flood_forecast_daily.py:4439-4458 reads
  projected_peak_in.
- tests/test_sms_policy.py:19-21 constructs projected_peak_in directly
  instead of consuming a real nowcast document.

The nowcast producer and SMS adapter use different names for the same
field. I reproduced the consequence: a real-shaped nowcast with
street_now_in=3 and peak_proj_in=14 is adapted to a null projection and
the SMS gate remains quiet. Supplying the test-only
projected_peak_in=14 makes the same gate send at lawn-step class.

**Impact**

The production projection-only imminent-impact policy does not work.
SMS waits until actual modeled street depth crosses the curb.

The adapter also omits active, radar_quality, and trend. Once the name
is repaired, it would count a falling projection that both the radar
dispatcher and site headline deliberately reject as a known
stateless-window overshoot.

Freshness policy is inconsistent: the public site hides radar after 20
minutes, radar dispatch accepts 25 minutes, and SMS accepts 30 minutes.

**Recommendation**

- Adopt one canonical nowcast schema and key name.
- Test the full nowcast.run → JSON → _nowcast_snapshot →
  evaluate_sms_gate contract.
- Require active=true, radar_quality=ok, valid schema version,
  acceptable source age, and rising trend before using a projection.
- Continue allowing actual current street water during a falling
  trend.
- Reconcile the three freshness limits or document why they differ.

### H2. A failed SMS can lose its immediate retry when another rail succeeds

**Evidence**

- forecast/flood_forecast_daily.py:7135-7154 returns successfully when
  any delivery rail succeeds, while sms_event advances only when SMS
  succeeds.
- forecast/nowcast.py:529-543 decides that a radar class has already
  been handled by looking at the general observed sig, not successful
  SMS delivery state.

Failure sequence:

1. Radar dispatches the forecast.
2. ntfy or email succeeds, but SMS fails.
3. The radar signature is committed without an sms_event.
4. Subsequent nowcast runs see the signature and do not redispatch.
5. The next hourly run may be too late because the radar source is no
   longer fresh.

**Impact**

This violates the explicit policy that imminent SMS is the one message
that must get through.

A related base-alert issue exists: ntfy/email delivery is acknowledged
globally after either rail succeeds. last_sent_channels records the
partial result, but alert evaluation never uses it to retry a failed
rail. If email fails while ntfy succeeds, email never receives that
event.

**Recommendation**

- Track acknowledgement per event, class, and channel.
- Make radar redispatch depend on successful sms_event state, not
  merely observed risk.
- Preserve household-level cap accounting while retrying only failed
  rails.
- Add integration tests for ntfy-success/SMS-failure and
  email-failure/ntfy-success.

### H3. Both immediate workflow-dispatch paths can report green after losing dispatch

**Evidence**

In .github/workflows/nowcast.yml:

- Lines 101-107 attempt to surface steps.dispatch.outcome before the
  dispatch step has executed.
- Lines 133-151 give the actual alert-ingest dispatch
  continue-on-error: true.
- Lines 166-174 convert radar dispatch failure into success with
  a non-fatal echo.
- NWS and radar checks can independently dispatch the same workflow
  during one nowcast run.

**Impact**

The job can finish green after failing to start the forecast workflow
that performs immediate alert evaluation. This contradicts HANDOFF and
BACKLOG claims that dispatch-failure visibility and retry were fixed.

**Recommendation**

- Compute a single consolidated dispatch intent.
- Perform one bounded retrying dispatch after publication.
- Make final dispatch failure fail the job visibly.
- Put outcome inspection after the dispatch step.
- Add workflow-structure tests or an actionlint-equivalent CI check.

### H4. NOAA gauge observations have no age limit

**Evidence**

- forecast/nowcast.py:299-325 requests a three-hour water-level window
  and accepts its last row as observed without checking the row time.
- forecast/flood_forecast_daily.py:515-549 accepts any nonempty recent
  response.
- forecast/flood_forecast_daily.py:552-621 computes surge from the last
  row without checking age.
- forecast/flood_forecast_daily.py:1910-1925 reports surge_observation
  ok whenever a numeric surge exists.
- forecast/flood_forecast_daily.py:2212-2224 reports live_gauge ok when
  any usable row exists in the 24-hour query.

**Impact**

A stalled NOAA feed can be used as current bay head, corrupting
head-dependent drainage and surge persistence while being reported as
healthy. A row almost 24 hours old can keep the live-gauge input green.

**Recommendation**

- Carry observation timestamp and age with every gauge-derived value.
- Establish maximum ages for drainage, surge persistence, and display.
- On stale nowcast gauge data, use astronomical bay level with a
  clearly degraded bay_source.
- On stale forecast gauge data, use the existing
  astronomical-only-degraded pathway.
- Add stale-but-nonempty NOAA response tests.

### H5. Scheduler redundancy is not independent and still fails silently

**Evidence**

bin/local_nowcast_tick.sh uses set -u, not set -e, and exits zero for:

- Missing clone or interpreter.
- Failure to acquire its persistent directory lock.
- Failed update/reset.
- nowcast failure.
- artifact-gate failure.
- rebase conflict.
- exhausted push retries.

The lock is ~/.barnacle/tick.lock, a persistent directory. A kill,
crash, or power interruption can leave it behind; all later ticks then
exit zero indefinitely.

The local arm publishes nowcast JSON but does not perform radar-alert
dispatch. The public Pages update still depends on GitHub's deployment
queue.

history/plans/external-cron-scheduler.md calls half-B external, but it
only asks a third-party scheduler to dispatch the same GitHub Actions
workflow. It protects against unreliable GitHub cron, not against the
wedged GitHub Actions queue that darkened the 2026-09-13 event.

**Impact**

launchd can report successful execution while the arm is permanently
dark. Neither proposed redundant arm fully preserves imminent alerts
and public delivery through a GitHub Actions control-plane outage.

**Recommendation**

- Return nonzero status for operational failures.
- Replace the directory lock with PID-aware locking or flock and add
  stale-lock recovery.
- Add structured failure logs and log rotation.
- Add an external watchdog that checks each arm and public-artifact
  freshness.
- Decide whether the independent arm must also deliver imminent
  alerts and publish outside GitHub Actions/Pages.
- Rename half-B as external trigger unless execution actually moves
  outside the GitHub failure domain.

### H6. Required display arms can silently remain stale

**Evidence**

- forecast/flood_forecast_daily.py:7019-7026 catches details.html
  generation failure and only warns.
- Lines 7028-7035 do the same for per-tide pages.
- forecast/check_artifacts.py checks that old required files exist but
  does not establish that they were regenerated from the same forecast.

**Impact**

A workflow can ship a fresh landing page and forecast.json alongside a
stale details page or stale/partial per-tide set, while both the gate
and workflow remain green. This is particularly dangerous under the
repository's parallel-arms policy.

**Recommendation**

- Treat required-surface generation failures as fatal.
- Generate into a temporary tree, validate it, then atomically replace
  the publish tree.
- Stamp each surface with forecast generation, schema, and model
  identifiers.
- Gate equality of those stamps across landing, details, widget data,
  and per-tide products.

## Medium-severity findings

### M1. The historical day-max chart assumes archive behavior that no longer exists

**Evidence**

- forecast/flood_forecast_daily.py:5240-5248 says the daily archive is
  the day's last run and treats its day-max values as day-wide.
- .github/workflows/daily_forecast.yml:93-99 archives only the 09:00
  UTC run.
- All 52 recent-format daily archive JSON files were generated around
  09:00 UTC, approximately 05:00 EDT.

**Impact**

day_max fields continue accumulating in docs/forecast.json during
later hourly runs but are not saved at day-end; they disappear when the
station-local calendar rolls over. Historical risk-day markers can
omit stronger guidance issued after approximately 05:00 EDT.

The 09:00 UTC file remains a valid as-issued morning forecast and
should not be overwritten if it is used for skill scoring. It is not a
full-day maximum record.

**Recommendation**

Keep the immutable morning snapshot and create a separate append-only
or end-of-day day_summary product for the maximum risk seen during the
local day.

### M2. Artifact and ledger validation is substantially narrower than described

**Evidence**

- forecast/check_artifacts.py:91-189 has no semantic branch for
  data/labeled_events.csv.
- I demonstrated that invalid dates, negative rain, negative duration,
  and an arbitrary label pass.
- I demonstrated that a forecast_accuracy row containing nan, invalid
  times, invalid regime, and invalid confidence passes.
- A nowcast with a negative rain rate, no nowcast_schema_version, and
  missing active-only projection fields passes.
- An alert state with string rank, malformed signatures, bogus
  channels, and invalid sms_event also passes.

Other missing invariants include:

- Finite numeric values and domain ranges.
- Known model versions.
- Frame sorting, nonnegative rate, and coverage arithmetic.
- Alert rank, signature, and channel types.
- sms_event timestamp/class structure.
- Forecast maximum staleness.
- Cross-field model arithmetic.
- Landmark-key taxonomy or an explicit historical-key allowance.

**Impact**

Current files pass and appear structurally coherent. The issue is that
the gate cannot prevent several plausible future corruptions despite
being described as semantic protection.

**Recommendation**

Add focused validators and adversarial tests for each producer-consumer
contract. Explicitly reject nonfinite CSV values.

### M3. Confidence labels do not discriminate observed accuracy

**Evidence**

Across 112 data/forecast_accuracy.csv rows:

- Mean absolute error: 0.417 ft.
- Root mean squared error: 0.544 ft.
- Mean signed error: +0.332 ft, historical overprediction.
- Maximum absolute error: 1.621 ft.
- Low-confidence MAE: 0.420 ft across 71 rows.
- Medium-confidence MAE: 0.417 ft across 40 rows.

Low and medium confidence have essentially identical observed error.

forecast/flood_forecast_daily.py:2412-2462 displays mean absolute error
as a roughly plus/minus uncertainty. MAE is not a calibrated prediction
interval.

No prediction-log row has ever been high confidence. Yet
forecast/flood_forecast_daily.py:3111-3137 automatically assigns high
confidence to an NWS coastal product, while BACKLOG.md:72-78 states
that nws_surge_parser.py has never seen a real coastal product.

**Impact**

The confidence word does not currently separate forecast quality, and
the numeric range can be interpreted as having a coverage guarantee it
does not possess. The only automatic high-confidence source is an
unvalidated production parser path.

**Recommendation**

- Measure empirical interval coverage.
- Test whether confidence classes separate error distributions.
- Segment by model version, lead time, surge source, and regime.
- Use residual quantiles or conformal intervals for within-plus/minus
  statements.
- Keep the first live NWS parser event medium or degraded until its
  parsed projection is independently verified.

### M4. Important operational logging can disappear silently

**Evidence**

- forecast/flood_forecast_daily.py:6945-6950 catches
  append_predictions_log failure and only warns.
- forecast/nowcast.py:133-156 catches every heartbeat append exception
  and does nothing.

**Impact**

A published run can remain green without its canonical prediction or
heartbeat record. That conflicts with provenance and cadence-monitoring
goals.

**Recommendation**

Forecast availability can remain fail-open, but the run should be
marked degraded and an independent observability check should fail
visibly when canonical operational records cannot be written.

### M5. The heartbeat ledger cannot prove either scheduler arm is healthy

**Evidence**

data/nowcast_heartbeats.csv records only generation time, active flag,
and source age. It does not identify:

- Runner or scheduler arm.
- Start or result phase.
- Exit outcome.
- Publication outcome.
- Alert-dispatch outcome.

It is written only when the Python program reaches the heartbeat
writer. If the scheduler never starts, there is no heartbeat, and the
stopped scheduler cannot alert on its own absence.

The 336-row snapshot contains 39 active-radar rows, a median interval
of 10.25 minutes, an eight-day gap from 2026-09-04 to 2026-09-12, and
a 468-minute gap across the 2026-09-13 flood period.

**Recommendation**

Record arm identity and phase/outcome, and monitor it from a system
outside the execution and publication failure domains.

### M6. Action volume is amplified by quiet local ticks

**Evidence**

The most recent 300 GitHub Actions runs covered approximately 17 hours
20 minutes:

- 102 CI runs.
- 61 nowcast runs.
- 18 hourly forecasts.
- 117 successful and two cancelled Pages deployments.

The local scheduler commits even an inactive nowcast heartbeat every
ten minutes. Those user-authenticated pushes trigger CI and Pages,
unlike commits made with a repository GITHUB_TOKEN.

The checked-out tree is approximately 348 MB, including 208 MB of
photographs that the cheap trigger check does not need.

**Impact**

Quiet weather produces approximately 17 Actions runs per hour and
repeated full-tree checkout/deployment work. This adds load to the same
control plane that recently wedged. It is a risk amplifier, not proof
of the queue outage's cause.

**Recommendation**

- Do not redeploy Pages for heartbeat-only changes.
- Add safe CI path filters for generated heartbeat/nowcast commits.
- Store heartbeat state outside the content branch if practical.
- Use sparse checkout for nowcast jobs.
- Coalesce quiet publications while retaining an independent
  liveness signal.

### M7. Evening hourly commit messages use the wrong UTC date

**Evidence**

.github/workflows/daily_forecast.yml:54-68 combines station-local
today with UTC hour and uses the pair in lines 159-163.

Examples:

- Commit 2b40dd3bc, made 2026-09-13 20:35 EDT, is titled hourly update
  2026-09-13 00:00 UTC. The UTC date was 2026-09-14.
- The 01:00, 02:00, and 03:00 UTC commits carried the same wrong date.

**Impact**

Forecast calculations are unaffected, but audit provenance is wrong
for four evening hours in EDT and five in EST.

**Recommendation**

Use distinct local_date and utc_date outputs.

### M8. The live-event playbook contains unsafe CSV instructions

**Evidence**

PLAYBOOK.md:38-58:

- References missing current-path model/v0.10.1.md instead of
  model/v0.10.2.md.
- Says to append PLAIN TEXT lines only.
- Says csv.DictWriter truncates the file. Opening in write mode
  truncates it; DictWriter itself does not.
- Claims legacy unquoted commas even though strict CSV is enforced.

**Impact**

Following the playbook during a live flood can corrupt quoting or row
widths in the canonical observation ledger.

**Recommendation**

Replace manual comma-line entry with one safe append-only helper using
append mode, newline handling, DictWriter, schema validation, and the
publish gate.

### M9. Data is structurally valuable but analytically uneven

**Evidence**

data/labeled_observations.csv:

- All 184 rows have an outcome.
- 95 rows populate model_predicted_depth_in, but only 28 values are
  machine-numeric; 67 are status or explanatory prose.
- 175 rows populate sh_obs_mllw_actual, but only 127 are numeric.
- Consumers generally skip nonnumeric content via float-conversion
  exceptions.

data/labeled_events.csv:

- 38 of 42 rows remain unlabeled.
- The last row is 2026-05-10 despite substantial later event history.
- The file has numerous date descents and no semantic gate.

data/predictions_log.csv:

- 14,348 rows and 2,506 unique forecast runs.
- No duplicate composite keys were found.
- Six rows from the 2026-08-14T23:06:14Z run lack rain values.
- Six rows use astronomical-only-degraded; every other row uses
  surge-persistence.
- 9,357 rows are low confidence and 4,991 medium; none are high.

Daily archives:

- 113 of 120 calendar days are present.
- Missing dates: 2026-06-15, 2026-06-16, 2026-06-22, 2026-07-20,
  2026-08-27, 2026-08-28, and 2026-09-13.
- The especially important 2026-09-13 event has no daily snapshot
  because the 09:00 UTC workflow was wedged.

Evaluation:

- The daily accuracy table measures Sandy Hook tide peaks, not
  rain-driven street depth or alert skill.
- Mixed historical model versions are correctly preserved, but
  aggregate accuracy is not current-model validation.

**Recommendation**

- Introduce additive status, evidence, and version columns rather than
  rewriting historical rows.
- Declare labeled_events.csv maintained or legacy/frozen and define
  its grain and label taxonomy.
- Build separate tide, pluvial-depth, timing, and alert-decision
  scorecards.
- Document archive coverage and event-day gaps.

### M10. Alert delivery is only partially durable

**Evidence**

Alerts are delivered before alert state is committed and pushed.
If delivery succeeds but local persistence or the later git push
fails, the next run can redeliver the event. This produced the
2026-09-13 duplicate-text incident.

_refresh_alert_state_from_origin narrows the race but cannot recover an
acknowledgement that never reached git.

**Impact**

The system remains exposed to duplicate alerts around state-write and
publication failure. The current design prefers duplicate over miss,
but the residual is neither transactional nor externally idempotent.

**Recommendation**

Use a durable outbox or idempotency key outside the content publication
transaction, or record this as an explicit monitored product
trade-off. Per-channel acknowledgement should be part of the design.

## Model concerns and false assumptions

These are primarily known structural limitations, not accidental
regressions. They should be changed only under a new model version with
the frozen v0.10.1 reproduction retained.

### G1. Fixed rainfall lag is falsified by Event 9

Event 9 observed street response in approximately 3-7 minutes. The
hindcast peak was approximately 10-13 minutes late under the fixed
15-minute lag. This is the cleanest current evidence against a single
fixed delivery lag.

### G2. Near-core peak and recession bias remain

The same event was approximately 1.5 inches low near the peak and held
recession too long. The later compound round overread by approximately
four inches.

### G3. The nowcast tank is stateless across runs

Each run reintegrates only its recent window from V=0. When an earlier
burst ages out, stored hillside or street water is understated.
day_max memory protects the headline maximum but not current tank
state.

### G4. Antecedent catchment wetness is absent

The model is memoryless about soil and hillside priming. Double-pulse
events are therefore not represented mechanistically.

### G5. Bay head is fixed through a projection

The current bay level is held through short integration and projection
instead of using time-varying tidal head. Drainage can therefore be
wrong on rapidly rising or falling tides.

### G6. Drainage and delivery structures remain simplified

Unresolved structures include bidirectional drainage, hysteresis,
grate recirculation, a tilted recession pool, the sidewalk swale
micro-basin, and a long hillside delivery tail.

### G7. Forecast rain input skill is not tank skill

NWS hourly QPF can smear or entirely omit convection. Successful
hindcasts with observed MRMS forcing do not establish end-to-end
forecast or alert performance.

### G8. _pluvial_fill has a known sub-bin discontinuity

A non-grid base begins at the preceding 0.1-inch stage bin, so tiny
positive storage can calculate up to approximately 0.08 inch below the
base. This is correctly identified in BACKLOG as version-worthy debt
and must not be silently patched.

### G9. driveway_central is not a surveyed elevation

The 4.67 ft NAVD88 value is a cross-fit threshold observable on a ramp,
not a surveyed point. model/v0.10.2.md documents this honestly. It
should remain labeled as such on every consuming surface.

### G10. Historical tide bias needs segmentation before retuning

The +0.332 ft mean signed error across 112 daily rows warrants
investigation, but the rows mix versions, regimes, forecast lead
conditions, and surge-persistence behavior. It does not by itself
justify moving a current model constant.

**Model recommendation**

After operational repairs, compare all nine measured events using
candidate variable or distributed short lag, persistent tank state,
an antecedent reservoir, distinct rising/recession dynamics, and
time-varying bay head. Keep operational corrections and hydrologic
retuning in separate changes.

## Documentation and living-state drift

### D1. Landmark count

README.md:3-10 says 18 landmarks, while current production and
v0.10.2 use 19.

### D2. Widget version

README.md:51-53 advertises widget v7.25a; HANDOFF and the widget source
say v7.26a.

### D3. Observation-spec link

data/labeled_observations_README.md:1-6 points to current
model/v0.10.1.md, which has moved to model/archive/. Current production
is v0.10.2.

### D4. Prediction-log cadence and plans

data/predictions_log_README.md:31-40 calls hourly logging planned and
the 2-4-row daily phase current. Hourly logging is already production.
Lines 79-89 describe accuracy work as future even though much of it is
implemented.

### D5. HANDOFF violates its own registry contract

HANDOFF.md:

- Says it is a less-than-approximately-100-line wholesale snapshot but
  is 167 lines.
- Is stamped 2026-09-13 08:05 EDT while incorporating work performed
  later on 2026-09-13.
- Says Phase 2 is awaiting independent review even though audit a2 is
  closed.
- Says 100 tests in one section and 111 later.

### D6. BACKLOG has stale open loops

BACKLOG.md still says:

- Event 9 photographs, peak pin, and nine-anchor work are pending,
  although HANDOFF says they are complete.
- Two outage-era Actions runs are stuck queued. Both are completed
  failures:
  - 34737703470 completed 2026-09-13 11:46 UTC.
  - 34737375383 completed 2026-09-13 11:45 UTC.
- Dispatch reorder was shipped, although its current failure-surfacing
  order is broken.

### D7. Nowcast workflow header is stale

.github/workflows/nowcast.yml:3-10 says the v0.10.1 tank and
docs/nowcast.json only. v0.10.2 is current and
data/nowcast_heartbeats.csv is also committed.

### D8. Archived v0.10.1 spec has broken relative links

model/archive/v0.10.1.md still uses relative destinations appropriate
to its former parent directory:

- archive/v0.10.md from inside model/archive/.
- ../assets and ../history rather than ../../assets and ../../history.
- data/v0.10.1-reproduction.json rather than ../data/.

### D9. Measuring-tape README links are malformed

assets/observations/0-measuring-tape/README.md:33 and 38 use link
destinations containing unescaped spaces without angle brackets or
percent encoding.

## Lower-severity engineering findings

### L1. Test breadth is much narrower than test count suggests

All 111 tests pass, but total forecast statement coverage is
approximately 35 percent. rendering.py is approximately 16 percent and
nws_surge_parser.py is completely uncovered.

There are no workflow-level tests, browser/DOM tests, automated
accessibility checks, actionlint, or shellcheck gates. The SMS field
mismatch and invalid workflow step ordering are exactly the kinds of
cross-boundary failures that unit tests did not exercise.

### L2. Static typing is not clean

An optional mypy run reports 95 diagnostics, mostly caused by fallback
imports, duplicate definitions, and facade re-exports. This is
maintenance debt rather than evidence of 95 runtime defects. The
planned module seams should improve it when weather permits.

### L3. Unit test leaks a file handle

tests/test_sms_policy.py:100 calls json.load(open(path)) without closing
the file, producing a ResourceWarning during the otherwise successful
suite.

### L4. Local scheduler dependencies are not reproducibly installed

bin/install_local_scheduler.sh:5-12 installs latest xarray, cfgrib, and
eccodes directly rather than using
forecast/nowcast-requirements.txt. The local redundant arm can
therefore diverge from the pinned GitHub environment or break on a
future reinstall.

The clone should be synchronized first, followed by installation from
the checked-in requirements file and a self-test.

### L5. DST repeated-hour ambiguity remains

NOAA lst_ldt timestamps are naive. parse_station_local_time attaches
America/New_York with the default fold. During the fall-back transition
the repeated 01:xx hour has two possible instants, but tests cover only
nonambiguous transition times. Prediction target keys also omit UTC
offset.

Prefer NOAA GMT internally or explicitly disambiguate fold and retain
the offset in canonical identifiers.

### L6. Repository and supply-chain posture

- No obvious committed secret, API token, or private key was found.
- GitHub actions are pinned by commit SHA.
- Python packages are pinned but not hash-locked.
- CDN resources reviewed were versioned and protected with SRI.
- The public repository intentionally exposes an exact residence,
  observation times, and GPS-bearing imagery. Recent event records say
  no identifiable people are present. The cumulative privacy exposure
  should remain an explicit owner decision.

## Recommended remediation order after independent review

1. Fix and integration-test the imminent SMS schema, trend/health
   gating, and retry semantics.
2. Repair both workflow dispatch paths so failures are visible and
   fatal.
3. Add NOAA observation-age handling.
4. Harden the local scheduler and define a genuinely independent alert
   and publication failure domain.
5. Make required-surface generation atomic and enforce cross-surface
   stamps.
6. Strengthen nowcast, alert-state, and CSV semantic contracts.
7. Separate morning forecast archives from full-day maximum-risk
   summaries.
8. Repair HANDOFF, BACKLOG, PLAYBOOK, and data README drift.
9. Improve confidence calibration and rain-event evaluation.
10. Only then evaluate a new model version; do not mix hydrologic
    retuning with operational corrections.

## Independent-review request

The reviewer should check each H, M, G, D, and L item against primary
code, data, git history, and live workflow state and mark it:

- confirmed;
- disputed;
- already addressed;
- or needs more evidence.

The reviewer must not edit this report. The response belongs at:

audits/2026-09-14-a1/02-comprehensive-repository-audit-<reviewer>.md

No close-out should be created until that independent reply exists and
any disputes are preserved.
