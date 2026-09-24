# As-issued validation: results after audit 2026-09-24-a4 round 03 (r3)

Author: Heron (Claude Opus 5.5), 2026-09-24. Branch `research/as-issued-validation`.
Supersedes the [r2 narrative](2026-09-24-as-issued-validation-report-r2.md); the
[r1 report](2026-09-24-as-issued-validation-report.md) and all r1/r2 outputs are
kept unchanged. Review record: audits/2026-09-24-a4 rounds 01-04. Rules:
protocol Amendments 2 and 3 are **post-review** changes made after earlier
outcome runs, not predeclared. Code at 837b0eb40; outputs carry `-r3`. The r3
numbers equal r2: the round-03 gates exclude no additional real pair.

## Verdicts

| Question | Result |
|---|---|
| A. Advisory corrections, high/mid/low | **NOT YET EVALUABLE**: 804 pairs, all zero-correction; none matured |
| B1. Decay vs persisted reading at the street | **NOT YET EVALUABLE**: 0 EXACT pairs |
| B2. Rain-tide coupling (tide-only, fixed-low-bay ablations) | **NOT YET EVALUABLE**: 0 EXACT wet pairs |
| B0. The published street line | Descriptive only |

The evidence gap needs future events. The admission and reporting repairs from
rounds 01 and 03 are complete in this revision and await Codex verification.

## Admission contract (Amendments 2-3)
EXACT and NEAR require all of the following:
- a control replay of the issuance's own published rule. The bay must be
  within 0.0015 ft for the decay rule and for constant-reading rules alike.
  The tank must show no presence mismatch and differ by at most 0.002 ft. The
  combined line must equal the maximum of bay and pluvial within 0.002 ft;
- a supported tank fingerprint;
- a gap-free grid;
- rain for every hour through the observation.

Required numbers are validated before any arithmetic. A null rain hour is
unavailable. Negative or non-finite values are excluded with a reason, never a
crash. Study A additionally rebuilds the anchors and reconstructs the
corrections, and requires finite inputs and outcomes. Real records all pass or
fail exactly as in r2.

## Populations

| Study B pairs | Count |
|---|---|
| Total | 235 |
| Primary | 224: 33 APPROX-TIDE and 191 EXCLUDED |
| Sensitivity-only | 11, from superseded rows 159 and 178 and the low-confidence row 165; all EXCLUDED |

Primary exclusions:
- 165 because the rain was not archived and the window was not a dry tidal
  window;
- 26 because of outage astronomy or a reading mismatch.

The observation manifest has 83 entries: 64 POINT, of which 53 are tape
with ±0.5 in, 5 live reports, 5 photo and 1 second observer; 6 INTERVAL; 9
LOWER; 4 UPPER. Eighty are primary.

## Study B diagnostics (APPROX-TIDE, descriptive)
- **Paired point errors.** They exist for one event only, 2026-07-13 (tape).
  Decay's event MAE is 0.2222 ft against persistence's 0.2423 ft, which
  supports no inference.
- **Tolerance and bracket pairs.** For the 23 pairs, the mean distance
  outside the bracket is 0.165 ft for decay and 0.189 ft for persistence.
- **Photo lower bounds.** Of the 10 NE-corner-wet bounds, decay fell short in
  7 and persistence in 4.

## B0, the published line (primary pairs)
Level bias is forecast minus observed level in NAVD88 ft. Each lead bin shows
the MEAN bias with the pointwise range in brackets. Cells follow the declared
threshold rule. "Highest sampled" is the largest logged point, or a bracket's
lower edge; the established peak comes from the primary records.

| Event (local) | Weather | Obs (primary) | Highest sampled | Established peak | Version | 0-6 h: mean level bias [range] / cells | 6-12 h: mean bias [range] / cells | 12-24 h: mean bias [range] / cells |
|---|---|---|---|---|---|---|---|---|
| 2026-07-09 14:28 | rain | 22 (22) | 5.08 | 5.04-5.12 | pre-v0.10.1 | +1.96 [+0.23, +2.88] / correct negative 1, false alarm 1, hit 20 | -1.40 [-1.77, +0.37] / correct negative 2, miss 20 | -1.28 [-1.64, +0.34] / correct negative 2, miss 20 |
| 2026-07-13 19:21 | dry tidal | 7 (7) | 3.807 | 3.73-3.81 | pre-v0.10.1 | +0.20 [+0.12, +0.28] / false alarm 1, hit 6 | -0.06 [-0.21, +0.06] / correct negative 1, hit 4, miss 2 | +0.43 [+0.35, +0.50] / false alarm 1, hit 6 |
| 2026-07-18 14:28 | rain | 27 (27) | 5.18 | 5.14-5.22 | pre-v0.10.1 | -0.52 [-1.09, +1.06] / correct negative 9, false alarm 1, hit 3, miss 14 | -5.93 [-6.08, -5.27] / correct negative 5, miss 12 | no pair |
| 2026-08-03 10:26 | rain | 5 (5) | 4.66 | 4.66-4.68 | v0.10.1 | -2.10 [-2.10, -2.10] / correct negative 2, miss 2, unknown 1 | -1.52 [-1.52, -1.52] / correct negative 2, miss 2, unknown 1 | -1.79 [-1.79, -1.79] / correct negative 2, miss 2, unknown 1 |
| 2026-08-07 18:32 | rain | 8 (6) | 4.763 | >= 4.76 | v0.10.1 | -4.23 [-4.33, -4.08] / correct negative 4, miss 2 | -3.84 [-3.93, -3.68] / correct negative 4, miss 2 | -4.15 [-4.25, -3.99] / correct negative 4, miss 2 |
| 2026-08-10 18:23 | dry tidal | 1 (1) | 3.91 | n/a | v0.10.1 | no point pair / hit 1 | no point pair / miss 1 | no point pair / hit 1 |
| 2026-08-11 18:56 | dry tidal | 1 (1) | 3.64 | n/a | v0.10.1 | no point pair / unknown 1 | no point pair / unknown 1 | no point pair / unknown 1 |
| 2026-08-12 19:56 | dry tidal | 1 (1) | 3.91 | n/a | v0.10.1 | no point pair / hit 1 | no point pair / miss 1 | no point pair / hit 1 |
| 2026-08-13 21:09 | dry tidal | 1 (1) | 3.91 | n/a | v0.10.1 | no point pair / hit 1 | no point pair / miss 1 | no point pair / hit 1 |
| 2026-09-01 19:16 | rain | 4 (4) | 4.662 | 4.66-4.70 | v0.10.1 | -4.42 [-4.42, -4.42] / correct negative 1, miss 3 | -4.62 [-4.62, -4.62] / correct negative 1, miss 3 | -4.62 [-4.62, -4.62] / correct negative 1, miss 3 |
| 2026-09-13 06:57 | rain | 6 (5) | 4.66 | 4.66 | v0.10.2 | no point pair / correct negative 1, false alarm 1 | -3.68 [-3.77, -3.60] / correct negative 4, miss 1 | -3.63 [-3.71, -3.54] / correct negative 4, miss 1 |

Reading the table:
- **Dry tidal evenings.** On 2026-07-13 the tape points' mean bias by lead is
  +0.20, -0.06 and +0.43 ft. Pointwise, errors run from -0.21 to +0.50 ft;
  the largest is row 117 at 12-24 h. On the August photo evenings the
  NE-corner threshold was called at 0-6 h and 12-24 h but missed at 6-12 h on
  three of four evenings. The 2026-08-11 bracket straddles the corner, so its
  cells are unknown.
- **2026-07-09.** At 0-6 h the line was high by +1.96 ft on average, with 20
  hits. That issuance used a +4.28 ft surge from a gauge malfunction, with
  published levels up to 9.62 ft MLLW; despike was added that day in
  b10568276. Those hits are not skill. At 6-24 h the mean bias was -1.3 to
  -1.4 ft, with 20 misses.
- **2026-07-18.** At 0-6 h: 3 hits, 14 misses and a mean bias of -0.52 ft.
  The 6-12 h issuances used outage-synthesized astronomy.
- **2026-08-03, 08-07 and 09-01.** Threshold misses at every lead, with mean
  level bias of -1.5 to -4.6 ft.
- **2026-09-13.** Misses at 6-24 h, with a mean bias of about -3.6 ft. There
  are **two** primary 0-6 h pairs, rows 183 and 185, both from the later
  compound round: one correct negative and one false alarm. Neither is a
  point, so there is no level bias.
- **Cause.** QPF smoothing of convective bursts is a plausible mechanism, but
  it is a hypothesis: the as-used hourly rain is not archived for these events.

**Conditional burst scenarios.** These are conditional scenarios, not hourly
forecasts or probabilities. The day maximum from the last issuance before each
rain event, against the established peak:

| Event (local) | Lead | Day-max conditional water NAVD88 | Established peak | Comparison | Flood alert |
|---|---|---|---|---|---|
| 2026-07-09 14:28 | 0.03 h | 4.43 | 5.04-5.12 | below the established peak | Flood Watch |
| 2026-07-18 14:28 | 0.12 h | 5.01 | 5.14-5.22 | below the established peak | Flood Watch |
| 2026-08-03 10:26 | 1.33 h | 4.82 | 4.66-4.68 | above the established peak | Flood Watch |
| 2026-08-07 18:32 | 0.32 h | 4.82 | >= 4.76 | indeterminate (peak bounded below only) | none |
| 2026-09-01 19:16 | 0.1 h | 5.01 | 4.66-4.70 | above the established peak | none |
| 2026-09-13 06:57 | 7.71 h | 5.01 | 4.66 | above the established peak | Flood Watch |

## Reproduce
```
python3 history/scripts/as_issued/normalization.py
python3 history/scripts/as_issued/cli.py readiness
python3 history/scripts/as_issued/cli.py advisory --reuse=history/data/as_issued/outcomes_advisory/manifest-20260924T1951Z.json
python3 history/scripts/as_issued/cli.py street
python3 -m unittest tests.test_as_issued_validation tests.test_replay_archive_provenance
```
