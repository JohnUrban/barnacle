# As-issued validation: results of the first development pass

Author: Claude (Opus 5.5), 2026-09-24. Branch `research/as-issued-validation`.
Brief: history/plans/2026-09-24-as-issued-validation-handoff.md (Codex).
Protocol, committed before scoring: history/plans/2026-09-24-as-issued-validation-protocol.md
(e81d26618; Amendment 1 in 568158bac; evaluators and tests in d34bddb77, all
before the first outcome run). For independent Codex review before any merge.
No production forecast, alert or frozen wind-shadow file was changed.

## Verdicts

| Question | Result | Why |
|---|---|---|
| A. Do advisory corrections improve the outlook's NWPS hourly line (high/mid/low)? | **NOT YET EVALUABLE** | No nonzero correction exists in any archived issuance; no target is 48 h old yet. |
| B1. Does v0.10.6 decay beat the v0.10.5 persisted reading at the street? | **NOT YET EVALUABLE** | Zero EXACT pairs: every street observation predates the complete input archive. |
| B2. Does bay height change rain flooding, against observations (tide-only and fixed-low-bay ablations)? | **NOT YET EVALUABLE** | Zero EXACT wet pairs: as-issued hourly rain is not archived before 2026-09-23. |
| B0. How did the actually published street line do? | Descriptive only | Genuine as-issued output of v0.10.1-era versions; see table below. |

These are findings about evidence, not unfinished implementation: the
evaluators run end to end on the real archive and are tested on synthetic
fixtures (mechanics only).

## What is replayable (inputs only; no outcomes)

Archive: 2,694 committed `docs/forecast.json` versions (2,688 distinct
generations, 6 unparsable) and 12 replay-input records (v0.10.6, from
2026-09-24T05:46:59Z). Report: `readiness-summary.json`, per-issuance
`readiness-fidelity.json`.

- **Astronomy.** The published bay line minus NOAA astronomy equals each
  version's declared surge within 0.001 ft in all 1,848 issuances with a bay
  line, except 5 flagged `tide_predictions_stale` (the 2026-07-18 NOAA outage,
  when astronomy was synthesized from cached extremes).
- **Readings.** Production's observed-surge reading (gauge level minus
  hourly-interpolated astronomy) reproduces exactly wherever it is published,
  and in 1,771 of 1,804 earlier persistence issuances. The other 33 are
  excluded from counterfactual arms.
- **Tank.** Where the as-used hourly rain is archived (37 issuances: 12 replay
  records, 25 via the outlook's grid rain), the published pluvial line
  reproduces within 0.0011 ft with no presence mismatch. Before 2026-09-23
  14:43Z only +-3 h tide windows and daily totals were published, so the tank
  cannot be replayed for any earlier storm.
- **Mean.** Production's trailing mean, replayed from retained raw verified
  heights, equals the published v0.10.6 value (0.5311 ft) with the real
  verified-data end. Earlier issuances need an assumed 24-day lag (0.5316 ft
  on the same day): an approximation.
- **Advisory control.** Raw NWPS plus the recorded correction equals the
  published corrected line exactly in all 12 replay records. The first core
  hour, missing from the replay record's outlook array, is recoverable from
  the same generation's published blob.
- **Not raw evidence.** The per-tide `nws_product` and `nwps` fields are
  equal in all 37 outlook issuances, including v0.10.4/5 issuances made when
  a local candidate captured corrections of +0.1 to +0.4 ft. Their v0.10.4/5
  semantics are not raw NWPS, so they were not used. That 03:57Z capture
  survives only as a summary without raw NWPS: not replayable.

## Study A

804 corrected/uncorrected pairs from the 12 replay records; every pair is in
the ZERO cohort (parity control: identical errors by construction). No target
had matured (>= 48 h) at evaluation; gauge responses were fetched and kept
(`history/data/as_issued/outcomes_advisory/`). Excluded as not raw-NWPS rows:
930 guidance-decay and 298 P-ETSS hours. Resolution needs nonzero corrections
in >= 5 independent coastal-flood episodes with matured gauge outcomes, per
phase.

## Study B

185 ledger rows; 82 eligible after the predeclared rules (79 predate the first
published bay line; correction records, keys without an elevation and
unclassifiable blank depths excluded). 231 primary pairs (latest issuance per
observation and lead bin) across 11 events.

| Pair class | Pairs |
|---|---|
| EXACT | 0 |
| NEAR | 0 |
| APPROX-TIDE (dry tidal window, rain not archived) | 33 |
| EXCLUDED: rain not archived and not a dry tidal window | 172 |
| EXCLUDED: outage astronomy / reading mismatch | 26 |

**Diagnostic only (APPROX-TIDE, 5 dry tidal evenings, 33 point pairs; the tank
is assumed silent and pre-v0.10.6 means are reconstructed).** Event-weighted
MAE of the street level: persisted reading 0.201 ft, decay 0.185 ft; decay
lower in 3 of 5 events; event-bootstrap 90 % interval of the difference
-0.044 to +0.015 ft. Under the protocol this class cannot produce a verdict;
even as a diagnostic it would read INCONCLUSIVE. Both arms sit about +0.09 ft
above the observed street level on average.

**B0, the published line (descriptive; genuine as-issued output).** Bias is
forecast minus observed street level (NAVD88 ft), primary pairs:

| Event (local) | Weather | Obs | Observed peak NAVD88 | Version | Bias at lead 0-6 h | Bias at 6-12 h | Bias at 12-24 h | Wet calls 0-6 h (hit/miss/false) |
|---|---|---|---|---|---|---|---|---|
| 2026-07-09 14:28 | rain | 22 | 5.08 | pre-v0.10.1 | +1.96 ft | -1.40 ft | -1.28 ft | 20/0/1 |
| 2026-07-13 19:21 | dry tidal | 7 | 3.807 | pre-v0.10.1 | +0.20 ft | -0.06 ft | +0.43 ft | 6/0/1 |
| 2026-07-18 14:28 | rain | 27 | 5.18 | pre-v0.10.1 | -0.52 ft | -5.93 ft | n/a | 3/14/1 |
| 2026-08-03 10:26 | rain | 5 | 4.66 | v0.10.1 | -2.08 ft | -1.51 ft | -1.78 ft | 0/2/0 |
| 2026-08-07 18:32 | rain | 8 | 4.763 | v0.10.1 | -4.23 ft | -3.83 ft | -4.14 ft | 0/2/0 |
| 2026-08-10 18:23 | dry tidal | 1 | 3.91 | v0.10.1 | +0.07 ft | -0.42 ft | +0.01 ft | 0/0/0 |
| 2026-08-11 18:56 | dry tidal | 1 | 3.723 | v0.10.1 | +0.25 ft | -0.06 ft | +0.19 ft | 1/0/0 |
| 2026-08-12 19:56 | dry tidal | 1 | 3.993 | v0.10.1 | +0.20 ft | -0.15 ft | +0.03 ft | 1/0/0 |
| 2026-08-13 21:09 | dry tidal | 1 | 3.993 | v0.10.1 | +0.12 ft | -0.14 ft | -0.07 ft | 1/0/0 |
| 2026-09-01 19:16 | rain | 4 | 4.681 | v0.10.1 | -4.59 ft | -4.79 ft | -4.79 ft | 0/3/0 |
| 2026-09-13 06:57 | rain | 5 | 4.66 | v0.10.2 | n/a | -3.67 ft | -3.57 ft | 0/0/0 |

- Dry tidal evenings: the published line was within a few tenths of a foot
  and called most landmark crossings correctly.
- Convective rain floods: the unconditional line missed the street water at
  every lead, by about 1.3 to 4.9 ft, because the hourly QPF it used smears
  bursts. The exception is the 2026-07-18 0-6 h issuances, whose published
  pluvial line was present at 26 of 27 observations.
- Two archive-evidenced input faults, not inferred from errors: the
  2026-07-09 19:34Z issuance used a gauge malfunction (published levels up to
  9.62 ft MLLW; despike added the same day in b10568276), which explains its
  +1.96 ft; the 2026-07-18 13-18Z issuances used outage-synthesized astronomy,
  which explains the -5.93 ft at 6-12 h. Both are listed in
  `study-b-events.json`.

**Conditional burst scenarios (published `pluvial_risk`; conditional, not
hourly forecasts or probabilities).** Last issuance before each rain event's
first observation:

| Event (local) | Issuance lead | Scenario level | Burst estimate in/h (day max) | Conditional water NAVD88 (day max) | Observed peak NAVD88 | Flood alert |
|---|---|---|---|---|---|---|
| 2026-07-09 14:28 | 0.03 h | possible | 0.74 (0.74) | 4.43 (4.43) | 5.08 | Flood Watch |
| 2026-07-18 14:28 | 0.12 h | elevated | 3.0 (3.0) | 5.01 (5.01) | 5.18 | Flood Watch |
| 2026-08-03 10:26 | 1.33 h | elevated | 2.04 (2.04) | 4.82 (4.82) | 4.66 | Flood Watch |
| 2026-08-07 18:32 | 0.32 h | none | 0.03 (2.04) | None (4.82) | 4.763 | none |
| 2026-09-01 19:16 | 0.1 h | elevated | 0.34 (3.0) | 4.13 (5.01) | 4.681 | none |
| 2026-09-13 06:57 | 7.71 h | elevated | 3.0 (3.0) | 5.01 (5.01) | 4.66 | Flood Watch |

The day-maximum conditional water (4.43 to 5.01 ft) was in the range of the
observed peaks (4.66 to 5.18 ft): above the observed peak in 4 rain events and
below it in 2 (2026-07-09, a burst on the high tide; 2026-07-18). That is a
description of a conditional scenario, not calibrated skill, and is not scored.

## Logging repairs (built on this branch, need review before merge)

Narrow, archive-only; forecasts, alerts and the frozen wind bundle unchanged.
359 tests pass, including the frozen v0.10.1, v0.10.3 and v0.10.6 replays.
1. **QPF provenance.** `fetch_nws_qpf` leaves the grid `updateTime`,
   retrieval time, unit and raw (validTime, mm) intervals in the replay
   channel; the returned rates are unchanged (tested). The replay record
   gains `qpf_source`.
2. **NWPS retrieval.** `nwps.retrieved` is never replaced by the generation
   time; `retrieved_basis` states it is the outlook gather's run time.
3. **Advisory issuance.** `advisory.issued_utc` is parsed from the status,
   null with a reason when absent.
Schema 2; schema-1 rows stay valid. One line of `_main_core` changes (the
call passes `qpf_meta`): the wind review's "main unchanged apart from
holder exports" check will see it.

Proposed, not built: store a hash of the published blob's core line in the
next generation's record, so a replay can prove its join without Git.

## What would resolve each gap

- A: nonzero corrections in >= 5 independent episodes, archived from now on.
- B1: >= 5 independent observed street events after 2026-09-24 05:46Z (tidal
  evenings count), when every input is archived.
- B2: >= 3 (descriptive) or >= 5 (verdict) observed WET street events with
  archived rain.

**Field checklist for John (no new survey).** Per sighting: exact time (photo
EXIF preferred); which named landmark; depth above it, or "level with",
"below by", or "dry at"; a wet/dry note for nearby landmarks; rain on or off.
A quick "dry at the curb" at a forecast crossing is as useful as a flood photo.

## Questions for the reviewer
1. Is Amendment 1 (qualitative wording rules), made before scoring and
   motivated by a ledger read-through, acceptable? Rows 159 and 178 mention
   photos without being photo-verified and are labeled PHOTO under the rule.
2. Is APPROX-TIDE (tank assumed silent in dry tidal windows) acceptable as a
   labeled diagnostic, or should it be dropped?
3. Should the provenance repairs merge now (touching `fetch_nws_qpf` and one
   `_main_core` line) or wait for a production version?
4. Are the adequacy counts (5 episodes/events; 3 for descriptive wet results)
   justified for these exposures?
5. B0 shows the unconditional line missing every convective street flood.
   Is any product-framing change wanted? Owner's choice; none proposed here.

## Reproduce
```
python3 history/scripts/as_issued/cli.py readiness
python3 history/scripts/as_issued/cli.py advisory     # fetches gauge outcomes (raw kept)
python3 history/scripts/as_issued/cli.py street
python3 -m unittest tests.test_as_issued_validation tests.test_replay_archive_provenance
```
Inputs are pinned by Git blob SHA-1 and by SHA-256 manifests under
`history/data/as_issued/`. The observation ledger hash is in `study-b-street.json`.
Everything observed after the protocol commit is reserved for confirmatory evaluation.

---
Appended 2026-09-24 (after audit 2026-09-24-a4): parts of this narrative are superseded by
[the r2 report](2026-09-24-as-issued-validation-report-r2.md) (peak, miss and cause statements;
the dry-tidal diagnostic; "not unfinished implementation"). This file and its r1 outputs are kept unchanged above.
