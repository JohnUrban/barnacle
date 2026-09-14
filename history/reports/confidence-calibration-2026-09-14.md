# Confidence-label calibration check — 2026-09-14

Source: all 112 immutable rows in `data/forecast_accuracy.csv` at the audit
cut. Absolute Sandy Hook peak error by label:

| Label | n | MAE (ft) | empirical 80th percentile (ft) | max (ft) |
|---|---:|---:|---:|---:|
| low | 71 | 0.420 | 0.722 | 1.621 |
| medium | 40 | 0.417 | 0.774 | 1.247 |
| empty legacy row | 1 | 0.174 | 0.174 | 0.174 |

`low` and `medium` do not discriminate magnitude error in this sample; the
medium q80 is slightly worse. These words remain input/stability labels, not
calibrated probability claims. Production numeric uncertainty now uses the
within-label empirical 80th-percentile absolute error rather than presenting
MAE as a plus/minus interval. Segmentation by model version, lead time, surge
source, and regime remains necessary before redesigning the labels.

The first real NWS coastal-product parser event is capped at medium until its
parsed projection is independently verified. The single empty confidence cell
is the immutable first pre-column row and is explicitly grandfathered by the
gate; history was not rewritten.
