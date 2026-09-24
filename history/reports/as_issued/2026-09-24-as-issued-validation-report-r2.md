# As-issued validation: revised results after audit 2026-09-24-a4 (r2)

Author: Heron (Claude Opus 5.5), 2026-09-24. Branch `research/as-issued-validation`.
Supersedes the narrative of [the first report](2026-09-24-as-issued-validation-report.md)
(kept unchanged, with its r1 outputs). Review: audits/2026-09-24-a4/01 (Codex);
reply: audits/2026-09-24-a4/02 (Heron). The revised rules are **Amendment 2 of
the protocol, made after review and after the first outcome run**; they are
not predeclared. Repairs in 00875267d; outputs carry the suffix `-r2`.

## Verdicts (unchanged in substance)

| Question | Result |
|---|---|
| A. Advisory corrections, high/mid/low | **NOT YET EVALUABLE**: 804 pairs, all zero-correction; no matured target |
| B1. Decay vs persisted reading at the street | **NOT YET EVALUABLE**: 0 EXACT pairs |
| B2. Rain-tide coupling (tide-only, fixed-low-bay ablations) | **NOT YET EVALUABLE**: 0 EXACT wet pairs |
| B0. The published street line | Descriptive only |

There are two separate gaps. The **evidence gap** is real and needs future
events: no archived nonzero correction, and no street observation after the
complete input archive began (2026-09-24 05:46Z). The **implementation gaps**
Codex found (admission checks, observation semantics, threshold rule, report
claims) are repaired in this revision and need independent verification. The
first-round "not unfinished implementation" wording was wrong on the second
point and is withdrawn.

## What changed in the evaluation (Amendment 2)
- **EXACT/NEAR are now gated** on a control replay of each issuance's own
  published rule (bay, tank presence and values, supported tank fingerprint,
  gap-free grid, finite inputs, antecedent rain). Interpolation never crosses
  a gap. No real pair changed class: none were EXACT or NEAR before.
- **Study A admission** rebuilds the anchors from the advisory rows and raw
  NWPS, reconstructs the hourly correction, and requires agreement and label
  consistency; phase needs astronomy coverage. All 804 real pairs pass; all
  12 records' anchors rebuild; the control residual is 0.000 ft by source.
- **Observations** come from an auditable manifest (83 rows, keyed by row
  hash): tape points with +-0.5 in, photo brackets and bounds, stated time
  windows, superseded and low-confidence rows as sensitivity only, and
  recorded numeric/text conflicts (rows 153, 164).
- **Thresholds** follow protocol 4.6 (a point at the landmark is dry);
  straddling brackets are counted as UNKNOWN.

## Study B, revised

235 primary pairs (row 183's stated bracket now included) across 11 events:
33 APPROX-TIDE, 202 EXCLUDED (176 rain not archived outside dry tidal
windows; 26 outage astronomy or reading mismatch).

**The dry-tidal diagnostic no longer supports a five-event comparison.** The
four August evenings are photo bounds, not tape points, so paired point
errors exist for one event only (2026-07-13, tape): decay's event MAE is
0.020 ft lower than persistence, which supports no inference. Against the 23
tolerance or bracket pairs, the mean distance outside the bracket is 0.165 ft
(decay) vs 0.189 ft (persistence). Against the 10 photo lower bounds (NE
corner wet), decay fell short in 7 and persistence in 4. These are
descriptive and cannot decide B1.

**B0, the published line (primary pairs; level bias = forecast minus observed
level, NAVD88 ft; depth bias = forecast minus observed depth above the
landmark, in; cells per the declared threshold rule).** "Highest sampled" is
the largest logged level; the established peak comes from the primary records.

| Event (local) | Weather | Obs (primary) | Highest sampled | Established peak (basis) | Version | 0-6 h: level bias / depth bias / cells | 6-12 h: level bias / cells | 12-24 h: level bias / cells |
|---|---|---|---|---|---|---|---|---|
| 2026-07-09 14:28 | rain | 22 (22) | 5.08 | 5.04-5.12 | pre-v0.10.1 | +1.96 ft / +23.4 in / correct negative 1, false alarm 1, hit 20 | -1.40 ft / correct negative 2, miss 20 | -1.28 ft / correct negative 2, miss 20 |
| 2026-07-13 19:21 | dry tidal | 7 (7) | 3.807 | 3.73-3.81 | pre-v0.10.1 | +0.20 ft / +2.1 in / false alarm 1, hit 6 | -0.06 ft / correct negative 1, hit 4, miss 2 | +0.43 ft / false alarm 1, hit 6 |
| 2026-07-18 14:28 | rain | 27 (27) | 5.18 | 5.14-5.22 | pre-v0.10.1 | -0.52 ft / -1.5 in / correct negative 9, false alarm 1, hit 3, miss 14 | -5.93 ft / correct negative 5, miss 12 | no pair |
| 2026-08-03 10:26 | rain | 5 (5) | 4.66 | 4.66-4.68 | v0.10.1 | -2.10 ft / +0.0 in / correct negative 2, miss 2, unknown 1 | -1.52 ft / correct negative 2, miss 2, unknown 1 | -1.79 ft / correct negative 2, miss 2, unknown 1 |
| 2026-08-07 18:32 | rain | 8 (6) | 4.763 | >= 4.76 | v0.10.1 | -4.23 ft / -0.6 in / correct negative 4, miss 2 | -3.84 ft / correct negative 4, miss 2 | -4.15 ft / correct negative 4, miss 2 |
| 2026-08-10 18:23 | dry tidal | 1 (1) | 3.91 | n/a | v0.10.1 | n/a / n/a / hit 1 | n/a / miss 1 | n/a / hit 1 |
| 2026-08-11 18:56 | dry tidal | 1 (1) | 3.64 | n/a | v0.10.1 | n/a / n/a / unknown 1 | n/a / unknown 1 | n/a / unknown 1 |
| 2026-08-12 19:56 | dry tidal | 1 (1) | 3.91 | n/a | v0.10.1 | n/a / n/a / hit 1 | n/a / miss 1 | n/a / hit 1 |
| 2026-08-13 21:09 | dry tidal | 1 (1) | 3.91 | n/a | v0.10.1 | n/a / n/a / hit 1 | n/a / miss 1 | n/a / hit 1 |
| 2026-09-01 19:16 | rain | 4 (4) | 4.662 | 4.66-4.70 | v0.10.1 | -4.42 ft / +0.0 in / correct negative 1, miss 3 | -4.62 ft / correct negative 1, miss 3 | -4.62 ft / correct negative 1, miss 3 |
| 2026-09-13 06:57 | rain | 6 (5) | 4.66 | 4.66 | v0.10.2 | n/a / n/a / correct negative 1, false alarm 1 | -3.68 ft / correct negative 4, miss 1 | -3.63 ft / correct negative 4, miss 1 |

Reading the table, event by event and lead by lead:
- **Dry tidal evenings.** The 2026-07-13 tape points were within +0.43 ft at
  every lead. On the August photo evenings the NE-corner threshold was called
  at 0-6 h and 12-24 h but missed at 6-12 h on three of four evenings. The
  2026-08-11 bracket straddles the corner, so its cells are unknown.
- **2026-07-09.** At 0-6 h the line was 1.96 ft HIGH with 20 hits. That
  issuance carried a +4.28 ft surge from a gauge malfunction (published gauge
  levels up to 9.62 ft MLLW; despike added that day in b10568276), so those
  hits are not evidence of skill. At 6-24 h it was 1.3-1.4 ft low with 20
  misses.
- **2026-07-18.** At 0-6 h: 3 hits, 14 misses, level bias -0.52 ft. The
  6-12 h issuances used outage-synthesized astronomy (-5.93 ft).
- **2026-08-03, 08-07, 09-01.** Threshold misses at every lead with level bias
  -1.5 to -4.6 ft.
- **2026-09-13.** Misses at 6-24 h, -3.6 ft. The one 0-6 h pair was the later
  compound round.
- **Depth error.** It is near zero wherever the observation sits at a
  landmark, so the level error is the informative measure there.
- **Cause.** Smoothing of convective bursts by the hourly QPF is a plausible
  mechanism and a known limitation, but it is a **hypothesis**: the as-used
  hourly rain for these events is not archived, so the errors cannot be
  attributed.

**Conditional burst scenarios (not hourly forecasts or probabilities).** Day
maximum from the last issuance before each rain event, against the established
peak:

| Event (local) | Lead | Day-max conditional water NAVD88 | Established peak | Comparison | Flood alert |
|---|---|---|---|---|---|
| 2026-07-09 14:28 | 0.03 h | 4.43 | 5.04-5.12 | below the established peak | Flood Watch |
| 2026-07-18 14:28 | 0.12 h | 5.01 | 5.14-5.22 | below the established peak | Flood Watch |
| 2026-08-03 10:26 | 1.33 h | 4.82 | 4.66-4.68 | above the established peak | Flood Watch |
| 2026-08-07 18:32 | 0.32 h | 4.82 | >= 4.76 | indeterminate (peak bounded below only) | none |
| 2026-09-01 19:16 | 0.1 h | 5.01 | 4.66-4.70 | above the established peak | none |
| 2026-09-13 06:57 | 7.71 h | 5.01 | 4.66 | above the established peak | Flood Watch |

Above the established peak in three events, below it in two, indeterminate
where the crest was missed (2026-08-07). This describes a conditional
scenario; it is not calibrated skill and is not scored.

## Logging repairs
Unchanged in function from r1 and reviewed as isolated by Codex. Added: a
test and documentation that `qpf_source.status` is a capture status, not
QPF usability. Offered separately on branch `logging/replay-provenance` (off
main) so it can be reviewed and merged without the evaluator.

## Reproduce
```
python3 history/scripts/as_issued/normalization.py   # rebuilds the observation manifest (verified vs ledger)
python3 history/scripts/as_issued/cli.py readiness
python3 history/scripts/as_issued/cli.py advisory
python3 history/scripts/as_issued/cli.py street
python3 -m unittest tests.test_as_issued_validation tests.test_replay_archive_provenance
```

---
Erratum appended 2026-09-24 (audit 2026-09-24-a4 round 03, R6): "235 primary pairs" should read 235 total / 224 primary /
11 sensitivity-only (primary: 33 APPROX-TIDE + 191 EXCLUDED); "within +0.43 ft at every lead" describes lead-bin MEAN bias
(pointwise -0.21 to +0.50 ft); 2026-09-13 has two primary 0-6 h pairs (rows 183 and 185). Corrected in
[the r3 report](2026-09-24-as-issued-validation-report-r3.md). Text above is kept unchanged.
