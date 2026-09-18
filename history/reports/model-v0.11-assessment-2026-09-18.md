# Model v0.11 offline assessment — 2026-09-18

**Disposition: HOLD production v0.10.2.** The assessment and follow-on
time-varying-head prototype found physically real corrections, but no
evidence-supported v0.11 package ready to ship. Moving astronomy materially
improves one compound-event head replay and is neutral-to-slightly-worse in
the other because the surge itself evolves; treating issue-time surge as a
constant is therefore not yet a safe universal replacement. A single shorter
lag, a house-pixel forcing switch, standalone persistence, or a tide-bias
adjustment would likewise overfit or answer the wrong problem.

All numbers below are rerunnable with:

```text
python3 history/scripts/assess_model_v0_11.py --json
```

The command is read-only. Its primary inputs are the frozen
[v0.10.1 reproduction fixture](../../model/data/v0.10.1-reproduction.json),
the committed [MRMS extraction](../data/mrms/mrms_extracted.csv), Events
[7](../../assets/observations/2026-08-07/README.md),
[8](../../assets/observations/2026-09-01/README.md), and
[9](../../assets/observations/2026-09-13/README.md), the append-only
[prediction log](../../data/predictions_log.csv), and the
[observed-peak cache](../../data/observed_peaks_cache.csv). The follow-on head
replay additionally uses 102 official NOAA six-minute astronomical/observed
rows in
[`noaa_head_replay_fixture.json`](../data/noaa_head_replay_fixture.json),
refreshed by
[`fetch_noaa_compound_head_fixture.py`](../scripts/fetch_noaa_compound_head_fixture.py).

## Decision table

| Audit item | Finding | Disposition |
|---|---|---|
| G1 fixed lag | Across the nine photo-timed points, Event 8 favors **10 min** (2.62″ point RMSE) while Event 9 round 1 favors **3 min** (1.53″). The present 15 min gives 4.97″ and 11.52″ respectively. | **Reject a new single fixed lag.** Prototype a bounded distributed/dynamic lag only after defining an out-of-sample rule. |
| G2 near-core peak/recession | At the current lag, replacing catchment mean with the house pixel changes peak error from **+1.48″ to +2.35″** for Event 7, **−1.87″ to −0.53″** for Event 8, and **−1.49″ to −1.18″** for Event 9 round 1. | **Keep catchment mean as primary.** A universal point or max switch is contradicted by Event 7. Preserve point/max as diagnostics for a future spatial-delivery feature. |
| G3 stateless nowcast | With current `k_out=3.5/h` and the production two-minute Euler step, only **2.4%** of storage survives 60 dry minutes. | **Do not ship persistence alone.** It adds little under current decay and creates restart/state hazards. Reassess with a long-tail or antecedent reservoir candidate. |
| G4 antecedent wetness | Double pulses establish the mechanism qualitatively, but the archive has no independent soil/wetness state and Event 9 round-2 radar forcing is absent. | **Not identifiable yet.** Add an observable antecedent covariate before fitting a second reservoir. |
| G5 fixed bay head | In the 204-point cached astronomical sample, the largest 45-minute change is **−0.837 ft**, larger than the entire 0.52-ft drainage transition. Moving astronomy + constant issue-time surge cuts Oct 30 head RMSE **0.340→0.157 ft**, but Dec 19 is **0.249→0.251 ft** because surge evolves against the falling tide. A standardized 1.0 in/hr tank moves **+0.82″ rising / −0.49″ falling**. | **Prototype complete; HOLD production.** Astronomy must evolve, but constant-surge projection is not universally better. Define surge tendency/expiry and degraded-tail semantics before a production proposal. |
| G6 simplified drainage/delivery | Events 7–9 again show fast rise, over-held recession, tilted pooling, and spatially different grate behavior, but available observations cannot separately identify delivery tail, head-dependent `k_out`, recirculation, and micro-basins. | **Do not fit all structures together.** Test one mechanism at a time; start with evolving head, then asymmetric recession. |
| G7 forecast input vs tank skill | Event 9's hourly QPF peak was 17–22× below MRMS while its untimed burst proxy was within 5% of catchment mean. | **Keep scorecards separate.** No tank constant should absorb NWS forcing error. |
| G8 `_pluvial_fill` | Correct inversion removes a sampled worst onset defect of **0.090″**. Frozen peaks move 0 for four events, **+0.014″** for Dec 19, and **+0.063″** for Oct 30; no peak clock changes. | **Accept as a correctness candidate, not an emergency bump.** Include in the next versioned candidate and update goldens in lockstep. |
| G9 driveway threshold | The model spec correctly calls 4.67 NAVD88 a cross-fit threshold observable; production surfaces now say so, and the separate 4.11-ft road point is `driveway_road_central`. | **Resolved 2026-09-18 (`ea9e282bb`).** The stable model/API/ledger key remains `driveway_central`; no physics changed. |
| G10 tide bias | The legacy one-row/day log has **+0.320 ft** mean bias over 116 rows. The joined hourly log instead has **−0.037 ft** over 14,695 predictions / 235 tides; v0.10.2 alone is **+0.027 ft** over 1,981 predictions / 29 tides. | **Reject a tide-bias retune.** The legacy aggregate is cadence/version confounding, not a current constant estimate. |

## What the quantitative checks establish

### 1. Lag is event-dependent, not merely “too long”

The nine photo-timed rise/recession points in Events 8 and 9 falsify the
15-minute constant, but they do not identify one replacement:

| Catchment-mean forcing | 3 min | 5 min | 10 min | 15 min |
|---|---:|---:|---:|---:|
| Event 8 point RMSE | 4.14″ | 3.75″ | **2.62″** | 4.97″ |
| Event 8 peak-clock error | −1 min | +1 min | +5 min | +11 min |
| Event 9 round-1 point RMSE | **1.53″** | 2.21″ | 4.86″ | 11.52″ |
| Event 9 peak-clock error | +0.6 min | +2.6 min | +6.6 min | +12.6 min |

Peak magnitude does not change with a pure lag shift; the current tank remains
1.87″ low for Event 8 and 1.49″ low for Event 9 round 1. A shorter lag repairs
timing only. Selecting 3 or 10 minutes globally from these two events would be
look-ahead overfit. A defensible candidate needs a predeclared driver such as
storm-core position, distributed travel time, or a directly observable rise
trigger, then must replay the other measured floods unchanged.

### 2. Spatial forcing cannot be selected by whichever pixel wins

At the current 15-minute lag:

| Event | Catchment mean error | House-point error | Box-max error |
|---|---:|---:|---:|
| 7 | **+1.48″** | +2.35″ | +2.00″ |
| 8 | −1.87″ | **−0.53″** | −1.39″ |
| 9 round 1 | −1.49″ | −1.18″ | **−0.42″** |

The point/max fields explain why near-core events can outrun a catchment mean,
but choosing the best field after observing the flood is not a forecast rule.
Event 7 supplies the needed counterexample: the same switch makes its existing
high-side miss worse. The catchment box therefore remains the production
forcing region; spatial ratios are candidate explanatory features, not
replacement truth.

### 3. The fill defect is genuine but operationally small

The present helper charges the entire first 0.1-inch stage bin even when the
tidal base begins partway through it. With tiny positive storage, the returned
stage can start below the base. Starting the first interval at
`max(base_stage, previous_bin)` is the physically correct inversion.

The exhaustive sampled base/budget grid found a 0.090-inch maximum correction.
Pure-pluvial frozen events begin at the zero-inch grid and do not move. Only
the non-grid high-bay cases move: Oct 30 by +0.063″ at peak and Dec 19 by
+0.014″ at peak (+0.020″ at its observation). Those changes are far below
measurement uncertainty and do not change event rank or peak time. This is a
safe candidate, but model-version discipline still applies because output
changes.

### 4. Persisted state and long-tail delivery are different hypotheses

The current one-hour radar window loses only 2.4% of a dry-decaying tank under
the present `k_out`. Persisting that same state would barely change a normal
run after the old burst ages out, while adding a transactional state file and
restart semantics. The field evidence for a one-hour hillside tail instead
questions the single exponential reservoir itself. Persistence should be
tested only with the structural candidate it is meant to preserve, including
outage/restart and stale-state replays.

### 5. Time-varying bay head is material, but constant surge is insufficient

The current nowcast holds one bay value through its 45-minute projection. In
the committed four-day cache slice, astronomy alone can move 0.837 ft in that
window. That exceeds the model's full-drain-to-blocked transition (3.00–3.52
NAVD88), and the moving tide also changes the street-water base when grates
are submerged.

The follow-on prototype replays every possible 45-minute issue window in two
compound calibration events. “Moving” means future astronomical tide plus
the observed-minus-astronomical anomaly at issue time; it fits no parameter.
Each event contributes 43 issue windows and 344 scored future points:

| NOAA head replay | Fixed-head RMSE | Moving-astronomy RMSE | Fixed 45-min endpoint RMSE | Moving endpoint RMSE |
|---|---:|---:|---:|---:|
| 2025-10-30 | 0.340 ft | **0.157 ft** | 0.497 ft | **0.198 ft** |
| 2025-12-19 | **0.249 ft** | 0.251 ft | 0.368 ft | 0.368 ft |

Oct 30 behaves like the intended hypothesis: the surge anomaly is relatively
stable while astronomy rises and falls, so moving astronomy removes more than
half the error. Dec 19 is the counterexample. Around 12:42Z the observed head
continues rising while astronomy falls; 45 minutes later fixed head misses by
0.083 ft, while constant-surge moving astronomy misses low by 0.577 ft. The
surge tendency, not astronomy, dominates that interval. This falsifies
“moving astronomy + constant surge” as a universal production rule.

The mechanism is nevertheless operationally material. With a standardized
1.0 in/hr rain rate and 3.26-ft NAVD88 starting bay, the largest cached
astronomical rise adds **0.82 inches** to the tank endpoint relative to fixed
head; the largest fall removes **0.49 inches**. This uses production constants
and the two-minute integration step, changing only the head path.

Age semantics are also incomplete. A 45-minute projection stays inside the
existing 60-minute surge-validity limit only when the initial observation is
at most 15 minutes old, while `current_bay()` accepts head observations up to
30 minutes old. A production design must mark or shorten the degraded tail,
or use an explicit conservative fallback; it must not silently equate an
expired anomaly with healthy zero surge.

### 6. The apparent historical tide bias does not survive segmentation

Prediction-log results at the assessment cut:

| Segment | Predictions | Tides | Bias | MAE |
|---|---:|---:|---:|---:|
| v0.10 | 1,521 | 28 | −0.015 ft | 0.277 ft |
| v0.10.1 | 5,719 | 90 | −0.053 ft | 0.217 ft |
| **v0.10.2** | **1,981** | **29** | **+0.027 ft** | **0.240 ft** |
| 0–3 h lead, all versions | 330 | 113 | +0.013 ft | 0.113 ft |
| 48–120 h lead, all versions | 5,140 | 231 | −0.036 ft | 0.282 ft |

The hourly record improves strongly toward the tide and the current version is
nearly unbiased. The six `astronomical-only-degraded` rows are, as expected,
low by 0.875 ft on average; they are explicitly degraded and are not evidence
for moving the normal surge correction. The 38 historical “severe” rows are
all old v0.6/v0.9 episodes, including known bad surge/gauge periods; there is
no current-version severe sample from which to retune.

## Evidence gaps that block a production v0.11

- Event 9 round 2 has photo/ledger bounds, but the committed MRMS extraction
  stops at 11:42Z (07:42 EDT), hours before its 10:03–10:12 EDT compound
  crest. Its rain forcing cannot be reconstructed honestly from this archive.
- Only Events 8 and 9 supply the nine minute-resolution points targeted by the
  lag assessment; that is enough to reject 15 minutes, not enough to fit and
  validate a new rule on independent events.
- The archive lacks a measured antecedent-soil state. “Wet” versus “dry” is a
  post-hoc narrative category unless a reproducible rainfall-memory feature is
  defined before fitting.
- Recession observations are spatially tilted and sometimes landmark bounds,
  not a single level pool. A scalar `k_out` fit cannot be treated as direct
  proof of grate hydraulics.
- There is no representative v0.10.2 severe-tide sample and the NWS coastal
  surge parser still has no real product validation.
- Two compound head replays are enough to reject fixed astronomy and constant
  surge as universal rules, but not enough to select a surge-tendency model.
  The next rule needs a predeclared recent-surge feature and an independent
  event; choosing whichever of fixed, constant, or trend wins each event is
  look-ahead overfit.
- End-to-end false-alert evaluation needs dry convective near-misses as well
  as the nine floods; peak RMSE alone is not an acceptance criterion.

## Recommended next development order

1. **DONE:** clarify the driveway threshold label/key semantics on every
   consuming surface; no physics changed (`ea9e282bb`).
2. **PROTOTYPED / HOLD:** moving astronomy is necessary, but constant
   issue-time surge is not sufficient. Specify a bounded observable surge
   tendency and explicit expiry/degraded-tail contract, then reserve the next
   compound event for validation.
3. Add the `_pluvial_fill` continuity repair to a versioned candidate and
   regenerate frozen goldens; do not ship it silently in v0.10.2.
4. Define a dynamic/distributed lag from an observable predictor and reserve
   at least one event for validation. Do not choose a constant from Events 8
   and 9 after seeing both scores.
5. Only then test asymmetric recession or a two-layer antecedent reservoir,
   one structural change at a time, with persisted-state restart/outage tests.
6. Require all-nine peak errors, Events 8/9 rise and recession timing,
   false-alert behavior, and end-to-end forecast/alert skill before accepting
   a new model version.

No production formula, constant, landmark value, model stamp, or historical
ledger row was changed by this assessment or follow-on prototype.
