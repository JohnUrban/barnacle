# v0.10.3 candidate — stage-storage fill continuity

**Status: offline candidate, not production.** Production remains v0.10.2.
This candidate changes no fitted constant, landmark, input, or clock. It only
repairs the stage-storage inverse when tidal base stage begins inside a
0.1-inch curve bin.

## Defect and correction

Production `_pluvial_fill()` skips bins whose upper edge is below the base,
but charges the first surviving bin from its lower edge. For a non-grid base,
tiny positive rain storage can therefore return a stage below the tide-set
base. The candidate starts that first interval at
`max(base_stage, previous_bin_edge)`.

The independent reference calculation is:

```text
candidate_stage = inverse_curve(volume_at(base_stage) + rain_storage)
```

Across base stages 0.00–24.00 inches at 0.01-inch spacing and 13 storage
budgets from zero through 2,000,000 cell-inches, the candidate matches that
reference to floating-point precision (worst error 1.07e-14 inch). The largest
correction relative to production is +0.090 inch at a base partway through a
stage bin and near-zero added storage.

## Frozen candidate differences

The six retained hindcasts keep every peak clock unchanged. Four pure-pluvial
peaks are bit-identical. Only the non-grid compound bases move:

| Event | v0.10.2 peak | Candidate peak | Delta |
|---|---:|---:|---:|
| 2025-10-30 | 20.8802″ | 20.9431″ | +0.0629″ |
| 2025-12-19 | 14.2400″ | 14.2542″ | +0.0142″ |

The December 19 observation-time stage moves 11.0077→11.0279 inches
(+0.0202 inch), still inside the 10.1–12.2-inch observed band. Fit constants,
the 24-point RMS, and the six-event evidence set are unchanged.

## Reproduction and promotion contract

Run from any directory:

```text
python3 history/scripts/reproduce_v0_10_3_fill_candidate.py
```

The command verifies the reference equivalence and
[`v0.10.3-fill-candidate.json`](../../model/data/v0.10.3-fill-candidate.json)
goldens while asserting production is still v0.10.2. A later promotion must
be atomic: archive the v0.10.2 spec with repaired links; create the v0.10.3
spec; replace the production helper; update `CURRENT_MODEL_VERSION`, the
prediction-log README, tests, and generated surfaces; then gate and frozen
replay. Do not bundle the held time-varying-head rule or any retuning.
