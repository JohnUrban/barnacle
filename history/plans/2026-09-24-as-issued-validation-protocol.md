# As-issued validation protocol: advisory corrections (Study A) and rain/tide street forecasts (Study B)

Author: Claude (Opus 5.5), 2026-09-24, branch `research/as-issued-validation`.
Brief: [2026-09-24-as-issued-validation-handoff.md](2026-09-24-as-issued-validation-handoff.md) (Codex).
**Committed before any forecast-versus-outcome error is computed.** The
readiness inventory and replay-fidelity checks below compare published outputs
with archived INPUTS only; no observation was read to produce them.
Evaluator code implementing these rules is committed separately, after this file.
Production, alerts and the frozen wind-shadow c2 bundle are untouched.

## 0. Disclosure: what the author has already seen
- The prior bounded rain comparison (history/reports/2026-09-24-v0.10.6-rain-
  comparison-r2.txt: five observed-reference radar-rain events tie; July 6
  canonical +15.4 in; 2025-10-30 is a reconstruction; the Sep 13 partial-QPF
  experiment is sensitivity only). Those findings stand and are NOT reused as
  as-issued evidence.
- The observation ledger's rows, including depths and notes, were read to write
  the classification rules in section 4. No published forecast was compared
  with any of them.
- The published advisory/NWS values of the 37 outlook issuances (all equal, see
  section 2) and today's surge (~+2 ft) were seen during the inventory.
- The wind-shadow c2 fit and trial (separate identity) are not used here.
Everything recorded after this file's commit is RESERVED for confirmatory
evaluation under these rules; nothing is tuned on it.

## 1. Estimands
- **A (advisory corrections):** on the seven-day outlook's NWPS-supported
  hourly line (sources `nws_product`, `nwps`; v0.10.6 estimator), paired
  error of the CORRECTED line (published) versus the UNCORRECTED raw NWPS
  hourly level at the same issuance and target, against the observed Sandy
  Hook level. Phase: high/mid/low from astronomy. The core 30-h
  `water_series` ignores corrections and is not this surface. P-ETSS, guidance
  decay and fallback hours are excluded (not raw-NWPS rows). A correction
  propagated into a guidance tail would be a separate estimand; none is
  evaluated in this pass.
- **B1 (v0.10.6 residual):** at the same issuance, street water at an observed
  landmark time from the v0.10.6 DECAY arm (reading decaying toward the mean,
  tau 36 h) versus the v0.10.5 PERSISTED-READING arm (the same reading held
  constant: flood_forecast_daily at v0.10.5, `build_water_series(persisted_surge)`),
  with identical astronomy, datum, rain, tank and empty-storage start.
- **B2 (coupling diagnostics):** with the same as-issued rain, the decay arm's
  combined line versus (i) TIDE-ONLY (the decay bay, no tank) and (ii) a
  FIXED-LOW-BAY TANK (the tank run with the bay held at 2.50 ft NAVD88, below
  the 3.00 full-drain level, combined as max(decay bay, that tank)). These
  isolate mechanisms; they are not deployable models.
- **B0 (published product, descriptive):** the actually published combined
  line `water_navd88` of whichever version was live, at each observation. This
  is genuine as-issued output, cohorted by model version; it is not a v0.10.6
  claim and not a comparison between rules.
- **Conditional burst scenarios** (`pluvial_risk` burst estimates,
  `potential_low_tide_navd88`) are conditional, not unconditional hourly
  forecasts or probabilities: listed beside observed peaks when a burst was
  observed, never scored as hourly skill.

## 2. Archive and replay-fidelity classes (inputs only; results already known)
Sources: every committed `docs/forecast.json` (blob SHA-1 identity; 2,694
commits, 2,688 distinct generations, 6 unparsable blobs) and
`data/replay_inputs/*.jsonl` (line identity: file, line, SHA-256). A replay
record joins its generation's forecast blob by `generated_utc`; the blob holds
the half-hourly core bay/rain/street line and live gauge levels, so the core
astronomy and the first core hour are recoverable even though the replay
record's outlook array starts later.
Astronomy: NOAA 30-min, 6-min and high/low predictions fetched after the fact
(deterministic), raw bodies kept under their SHA-256
(history/data/as_issued/astronomy/).
- **F1 astronomy:** published bay minus (astronomy - 2.82) equals each
  version's declared surge within 0.001 ft in every issuance with a bay line
  except 5 pre-v0.10.1 issuances flagged `tide_predictions_stale` (astronomy
  synthesized during an outage): EXCLUDED from counterfactual arms.
- **F4 reading:** production's reading (gauge level minus hourly-interpolated
  astronomy) reproduces exactly (0.0000 ft) in every issuance that publishes
  one (v0.10.4 partial, v0.10.5, v0.10.6) and in 1,771 of 1,804 earlier
  persistence issuances; the other 33 are EXCLUDED from counterfactual arms;
  product-driven issuances get a rebuilt, unverified reading (label kept).
- **F2 tank:** the published pluvial line is reproduced within 0.0011 ft with
  no presence mismatch in the 37 issuances whose as-used hourly rain is
  archived (12 replay records; 25 via the outlook's hourly grid rain, whose
  first core hour is not covered). One tank source fingerprint across all 37.
  Before 2026-09-23 14:43Z the tank's hourly rain is NOT archived (only +-3 h
  tide windows and daily totals).
- **F3 advisory:** raw NWPS + recorded correction equals the published
  corrected line exactly in all 12 replay records; every recorded correction
  is ZERO. In all 37 outlook issuances the per-tide `nws_product` and `nwps`
  fields are equal; for v0.10.4/v0.10.5 their semantics are not established
  as raw NWPS, so they are not used as raw evidence. The nonzero 03:57Z
  capture (history/reports/2026-09-24-v0.10.6-advisory-and-petss.txt) is a
  summary of a local candidate run without raw NWPS: not replayable.

Pair classes: **EXACT** (astronomy, reading, mean and complete as-used rain all
archived or exactly reproduced); **NEAR** (as EXACT but the first core hour's
rain is not archived: outlook-rain issuances); **APPROX-TIDE** (astronomy and
reading exact, rain not archived, observation dry by rule 4.4 and the
published forecast has no pluvial water at the observation: arms compared on
the bay only, the tank assumed silent in both); **EXCLUDED** (reasons counted).
The mean for pre-v0.10.6 arms is reconstructed with production's policy
(verified hourly_height minus predictions over the 364 calendar days to the
verified end, lag assumed 24 d): an approximation, so pre-v0.10.6 pairs are at
best NEAR/APPROX. Only EXACT pairs can support B1/B2 verdicts; NEAR and
APPROX-TIDE are reported as diagnostics.

## 3. Study A rules
- Unit: (issuance with a replay record, target hour) where the outlook hour's
  source is `nws_product` or `nwps` and raw NWPS covers it. Corrected =
  published outlook level (MLLW); uncorrected = raw NWPS level (MLLW); the
  correction at the hour = their difference, checked against the recorded
  corrections (tolerance 0.006 ft: NWPS stored to 0.01).
- Cohorts: ZERO (|correction| < 0.005 ft; parity control: errors identical by
  construction, never evidence that corrections help or are harmless) and
  NONZERO.
- Outcome: CO-OPS 6-min water level at the target hour, quality-aware QC
  (q=p [O,F,R,L] valid iff F=R=L=0; q=v [I,F,R,T] valid iff all 0; missing or
  unknown q invalid; inferred never an observation). Raw bodies kept with
  SHA-256; status and flags kept per hour; a target is scored once >= 48 h old;
  a re-run after data are verified is recorded as a new evaluation.
- Phase at target: HIGH if within 1.5 h of an astronomical high (NOAA hilo),
  LOW if within 1.5 h of an astronomical low, else MID. Lead bins (h): (0,6],
  (6,24], (24,48], (48,72].
- Metrics per phase and lead bin: n, unique targets, issuances, episodes;
  paired MAE, bias, underprediction rate (error < -0.25 ft); landmark
  implications: for each flood-window landmark, the count of targets where the
  corrected and uncorrected levels (NAVD88 = MLLW - 2.82) fall on opposite
  sides of its elevation, and which side the observation was on.
- Episodes: nonzero-correction issuances form one episode while consecutive
  issuances are < 12 h apart; episodes are weighted equally; uncertainty is a
  90 % bootstrap over episodes (2,000 draws, seed 20260924).
- Adequacy: a phase is EVALUABLE only with >= 5 independent nonzero-correction
  episodes having matured valid outcomes in that phase (5 is the smallest count
  at which a unanimous episode-level sign test reaches p < 0.05). A phase
  "improves" only if the episode-bootstrap 90 % interval of (corrected MAE -
  uncorrected MAE) is below 0; "harms" if above 0; else INCONCLUSIVE. No
  pooled claim may be reported without the per-phase results beside it.
  Zero nonzero episodes = NOT YET EVALUABLE.

## 4. Study B rules
4.1 Observations: `data/labeled_observations.csv`, times America/New_York
(DST by zoneinfo), landmark elevations = current production LANDMARKS
(NAVD88 ft). Excluded (counted): correction records (`none`), keys without a
current elevation (pocket_SE_retention, fire_hydrant_central, porch_step,
driveway_central), rows before the first published bay line
(2026-07-06T19:35Z) or with no eligible issuance.
4.2 Level type, from depth and wording (case-insensitive):
- depth > 0: POINT, level = elevation + depth/12.
- depth < 0: POINT below the landmark, level = elevation + depth/12.
- depth = 0: POINT at the elevation if the wording contains "level with",
  "exactly level", "at the bottom", "at base", "clearly at base", "hit" or
  "at the lawn"; UPPER BOUND (level <= elevation) if it contains "at/below",
  "no water", "dry", "exposed", "receded", "below"; otherwise UPPER BOUND
  (the README defines 0 as "no water").
- blank depth: UPPER BOUND only with explicit dry wording ("receded",
  "driveable", "exposed", "no water", "dry"); otherwise EXCLUDED.
4.3 Evidence type (first match): RECONSTRUCTION ("inferred", "backcast",
"hindcast", "reconstruct"; excluded from point aggregates, listed separately);
PHOTO ("photo", "exif"); SECOND OBSERVER (observer other than john/claude/
codex, or "second-observer"); otherwise OBSERVER ESTIMATE. The +13.5 in
2025-10-30 photo bound and the July 6 +15.4 in canonical crest precede the
archive and are not used.
4.4 Dry window: weather wording contains "clear", "calm" or "no rain" and none
of "downpour", "thunder", "drizzle", "shower", "burst", "heavy rain",
"light rain", "moderate rain", "rain continuing", "rain tail", "rain over".
4.5 Pairing: forecast street level at the observation time = linear
interpolation of the arm's half-hourly line. Issuances with generation time
before the observation and lead in (0, 30] h (core horizon; the extended
outlook is a separate horizon, reported only as counts). Lead bins (h):
(0,6], (6,12], (12,24], (24,30]. PRIMARY pairs: per observation and lead bin,
the LATEST eligible issuance in that bin (hourly repeats are not independent).
4.6 Metrics: POINT: error = forecast - observed level (ft): MAE, bias, and
|error| > 0.25 ft rate. UPPER BOUND: exceedance = max(0, forecast - elevation)
(a false wet call if > 0). Threshold at the landmark: forecast wet (level >
elevation) versus observed wet (POINT above elevation) or dry (BOUND or POINT
at/below): hits, misses, false alarms, correct negatives. Timing is not scored
(no observed crest time is exact enough across events); depth brackets from
the ledger notes are listed, not scored as exact.
4.7 Events: observations with times within 12 h of each other form one event;
events are weighted equally (mean of per-event MAE); uncertainty: 90 % event
bootstrap (2,000 draws, seed 20260924).
4.8 Adequacy and verdicts: B1 and B2 are EVALUABLE only on EXACT pairs from
>= 5 independent events with POINT observations (B2 additionally wet: as-issued
rain >= 0.25 in/h within 6 h before the observation, or a published pluvial
line at it); with 3-4 such events results are DESCRIPTIVE; fewer = NOT YET
EVALUABLE. A B1 verdict "decay better" needs a lower event-weighted MAE, a
strict majority of events won, AND the event-bootstrap 90 % interval of the
difference below 0; "worse" symmetric; otherwise INCONCLUSIVE. NEAR and
APPROX-TIDE results are diagnostics and can never produce a verdict. B0 is
descriptive only, by version cohort.

## 5. What would resolve each gap (stated before scoring)
- A: nonzero advisory corrections in >= 5 independent NWS coastal-flood
  episodes with matured gauge outcomes, archived by v0.10.6+ replay records.
- B1: >= 5 independent observed street events (any weather) after 2026-09-24
  05:46Z, when every input is archived; tidal evenings count.
- B2: >= 3 (descriptive) or >= 5 (verdict) observed wet street events with
  archived as-issued rain.
Insufficient evidence is a result, distinct from unfinished implementation.

## Amendment 1 (2026-09-24, before any scoring; commit precedes the evaluator's first outcome run)
Why: implementing 4.2/4.3 mechanically (ledger read-through, no forecast
compared) misclassified wording that the rules did not anticipate: "WATER OVER
... GRATES", "CROWN COVERED" and "water over the sidewalk" are LOWER bounds,
not upper bounds; "water at bottom of first porch step", "street full up to
~sidewalk TOP", "just APPEARING at NE+NW corners" and "back LEVEL with" are
points; and 4.3 read the NOTES, which often mention a separate hindcast, so
genuine observations were labeled reconstructions. Replacement rules:
- 4.2' Level type for depth 0 or blank, first match in the QUALITATIVE text:
  (1) UPPER BOUND (level <= elevation): "at/below", "no water", "dry",
  "receded", "exposed", "driveable"; (2) POINT at the elevation: "level",
  "at bottom", "at the bottom", "at base", "hit", "up to", "appearing";
  (3) LOWER BOUND (level >= elevation): "over ", "covered", "covering";
  (4) otherwise depth 0 = UPPER BOUND (README), blank = EXCLUDED. Nonzero
  depths are unchanged (POINT at elevation + depth/12).
- 4.3' Evidence type from the QUALITATIVE text only: RECONSTRUCTION ("inferred",
  "backcast", "hindcast", "reconstruct"); PHOTO ("photo", "exif"); SECOND
  OBSERVER (observer field or "second observer"); else OBSERVER ESTIMATE.
- 4.6' LOWER BOUND metric: deficit = max(0, elevation - forecast) (a missed wet
  call if > 0); threshold: observed wet.

## Amendment 2 (2026-09-24 ~16:00 EDT) — POST-REVIEW and POST-SCORING
Status, stated plainly: these changes follow Codex audit 2026-09-24-a4 round 01
(audits/2026-09-24-a4/01-as-issued-validation-codex.md) and were made AFTER the
first outcome run (results at 292cb3188 had been computed and read). They are
therefore not predeclared. The first-round outputs are preserved unchanged
(history/reports/as_issued/study-*.json, readiness-*.json and the r1 report);
revised outputs carry the suffix `-r2`. No threshold or rule below was chosen
by comparing its effect on the results; each responds to a specific audit
finding. The verdict vocabulary and adequacy floors are unchanged.
- **A2.1 Admission gates (R1).** EXACT/NEAR require a control replay of the
  issuance's own published rule: bay within 0.0015 ft of the published bay
  (stored 0.001); with rain, the tank re-run on the published bay matches the
  published pluvial line (no presence mismatch, <= 0.002 ft); tank source
  fingerprint in the supported set (verified equal to the frozen reference);
  gap-free half-hour grid; finite inputs; rain for every hour from the series
  start through the observation (NEAR: only the first core hour missing).
  Interpolation never crosses a gap > 30 min. Counterfactual arms are not
  required to equal the published line.
- **A2.2 Study A admission (R2).** Anchors are rebuilt from the record's
  advisory rows and raw NWPS (total minus the larger NWPS value of the
  advisory hour and the next) and must match the recorded anchors; the hourly
  correction is reconstructed from the recorded anchors per the v0.10.6 spec
  (linear between anchors, full within 1 h outside the first/last, fading to
  zero over 6 h; cross-checked against production); published minus raw must
  equal it within 0.011 ft, replacing section 3's 0.006 ft, which ignored the
  0.01-ft storage of anchors (NWPS +-0.005, anchors +-0.005, outlook +-0.0005);
  the `nws_product` label must coincide with anchoring. Phase requires a NOAA
  extremum on each side within 13 h; otherwise UNAVAILABLE, counted and
  excluded, never MID. Episodes: a gap of exactly 12 h starts a new episode
  (section 3's "< 12 h apart").
- **A2.3 Observations (R3).** Rules 4.2'/4.3' are replaced for scoring by an
  auditable normalization manifest (history/data/as_issued/
  observation_normalization.json, built by history/scripts/as_issued/
  normalization.py) keyed by ledger row and the SHA-256 of the parsed row, and
  verified against the ledger at every run. Each entry records a POINT (tape
  rows: +-0.5 in, from the 2026-07-13 record's "within tape precision"),
  INTERVAL (a bracket stated in the row or event record), UPPER or LOWER
  bound; an optional time window; the method from the event record (tape,
  photo bound, photo, live report, second observer); primary or
  sensitivity-only use (superseded rows 159 and 178; the 50-60 % second
  observer, row 165); and unresolved numeric/text conflicts (rows 153, 164),
  where the row's explicit wording bound is used and the conflict is recorded.
  Row 183's stated bracket (+7.2-7.5 in) is now used. Brackets are scored by
  interval error (distance from the forecast, or its range over the time
  window, to the bracket; 0 inside); their midpoint error is sensitivity only.
  B1/B2 paired comparisons use primary POINT rows; bracket rows are reported
  beside them. The ledger is not edited.
- **A2.4 Thresholds (R4).** Section 4.6 is implemented as written: a POINT at
  or below the elevation is dry. A bracket is wet when lo > elevation, dry
  when hi <= elevation, otherwise UNKNOWN, reported in the denominator.
  UPPER: dry when hi <= elevation; LOWER: wet when lo >= elevation.
- **A2.5 Peaks and narrative (R5).** "Highest sampled water" is reported apart
  from the event peak, which is taken only from the primary records (tape
  peak, photo bracket, or a lower bound when the crest was missed; inferred
  backcasts are not used). A conditional scenario is "above"/"below" a peak
  only when outside its bracket; with a lower bound only, "above" is
  indeterminate. Error causes (e.g. QPF smoothing) are hypotheses unless an
  as-used input attribution exists.
- **A2.6 Adequacy, clarified.** Five unanimous episode/event signs give a
  ONE-sided sign-test p = 1/32 = 0.031 (two-sided 0.0625). Five is a
  provisional floor for starting an event-level comparison, not adequate power;
  it assumes independent events (storms separated by the declared gaps), and a
  five-event bootstrap interval is coarse. There is no correction for testing
  three phases; any phase verdict must be read with the others.
- **A2.7 Times.** Ledger times use the shared station-time helper (offset-bearing
  values kept; legacy ambiguous fall-back hours fold=0).

## Amendment 3 (2026-09-24 ~17:30 EDT) — POST-REVIEW clarification (audit a4 round 03)
Status: after Codex round 03 (audits/2026-09-24-a4/03-repairs-verification-codex.md)
and after the r1 and r2 outcome runs; not predeclared. r1 and r2 outputs are
kept unchanged; revised outputs carry `-r3`. These rules complete what
Amendment 2 A2.1 already promised (a control replay and finite inputs); no
threshold was chosen by its effect on results.
- **A3.1 Combined-output control.** An admitted issuance's published combined
  line must equal max(published bay, published pluvial) within 0.002 ft at
  every point (checked for every class that builds counterfactual arms).
- **A3.2 One bay tolerance for every rule.** The 0.0015-ft control applies to
  the decay rule, to the v0.10.5 constant (the published reading) and to older
  constant curves (the published tide surge the curve implies, within
  0.002 ft); with no replayable rule the issuance is excluded.
- **A3.3 Numeric admission contract.** Before any arithmetic: published bay
  and combined values, astronomy, reading and mean must be finite numbers;
  published pluvial must be finite or absent (absent = no water above the
  street base, the published contract); archived rain must be finite and
  >= 0; a null rain hour is UNAVAILABLE (it counts against EXACT; only the
  declared first-hour NEAR case tolerates one), never zero. Study A requires
  finite raw NWPS, advisory totals, recorded anchors, published outlook levels
  and outcomes. Every failure is a counted exclusion with its reason; none can
  raise, become EXACT/NEAR or reach a verdict.
- **A3.4 Reporting populations.** Reports state total, primary and
  sensitivity-only pairs and their class counts separately; lead-bin figures
  are labeled as means, with the pointwise range beside them.

## Erratum to Amendment 3's header (audit a4 round 05, C1)
The header's "~17:30 EDT" was an unsupported estimate. The recorded times are
the repair commit 837b0eb40 at 2026-09-24 17:06:14 EDT and the r3 outputs commit
c9b898616 at 17:07:57 EDT; Amendment 3 was committed with 837b0eb40. No drafting
time is claimed. The post-review/post-scoring disclosure is unchanged.

## Amendment 4 — POST-REVIEW completion of the input contract (audit a4 round 05)
Committed with the repair; its commit time is the record of when. Not
predeclared; r1-r3 outputs are kept unchanged and revised outputs carry `-r4`.
- **A4.1 Validation order.** The published core series (bay, combined, pluvial)
  and the surge-rule metadata (decay mean, tau, reading value and time; the
  v0.10.5 reading and time) are validated BEFORE the astronomy check, the
  reading parse or any other arithmetic. Failures are counterfactual
  exclusions with the specific reason; nothing raises.
- **A4.2 Published line.** An invalid or missing published value is UNSCORABLE
  (counted with its reason) in every arm and summary: never a number, never a
  wet/dry cell. A valid published line stays scorable for B0 whenever only the
  counterfactual inputs are invalid or unavailable.
- **A4.3 Fidelity entry points** (astronomy, tank, advisory control, reading)
  apply the same checks when called directly and return a status, not an
  exception.
- **A4.4 Outputs** are written as strict JSON (non-finite numbers refused) as a
  final backstop, not as the admission mechanism.
