# v0.10.3 — stage-storage fill continuity

**Status: promoted to production on 2026-09-18.** This release changes no
fitted constant, landmark, input, or clock. It only
repairs the stage-storage inverse when tidal base stage begins inside a
0.1-inch curve bin.

## Defect and correction

The v0.10.2 `_pluvial_fill()` skipped bins whose upper edge was below the base,
but charges the first surviving bin from its lower edge. For a non-grid base,
tiny positive rain storage could therefore return a stage below the tide-set
base. v0.10.3 starts that first interval at
`max(base_stage, previous_bin_edge)`.

The independent reference calculation is:

```text
v0.10.3_stage = inverse_curve(volume_at(base_stage) + rain_storage)
```

Across base stages 0.00–24.00 inches at 0.01-inch spacing and 13 storage
budgets from zero through 2,000,000 cell-inches, v0.10.3 matches that
reference to floating-point precision (worst error 1.07e-14 inch). The largest
correction relative to v0.10.2 is +0.090 inch at a base partway through a stage
bin and near-zero added storage.

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
python3 history/scripts/reproduce_v0_10_3.py
```

The command verifies the reference equivalence and
[`v0.10.3-reproduction.json`](../../model/data/v0.10.3-reproduction.json)
goldens while asserting production is v0.10.3. Promotion was atomic: the
v0.10.2 spec was archived with repaired links; the production helper,
`CURRENT_MODEL_VERSION`, prediction-log README, tests, goldens, and generated
surfaces moved together. The held time-varying-head rule and all retuning were
excluded.
