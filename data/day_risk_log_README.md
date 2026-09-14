# Day-risk guidance log

Append-only, one row per forecast run. This records the maximum rain-risk
guidance issued during each station-local day so historical charts can take
the maximum across all hourly runs.

It deliberately does not replace or overwrite `docs/archive/YYYY-MM-DD.json`.
That file is the immutable forecast issued around 09:00 UTC and remains the
correct artifact for as-issued morning skill scoring. Rows before this log's
2026-09-14 cutover fall back to those morning snapshots and are not described
as full-day maxima.

The key is `generated_utc`; `local_day` is derived through the station-time
conversion. `potential_navd88` is the higher as-issued pluvial potential from
the production pair, not a measured outcome. Merge conflicts resolve by union,
and the publish gate rejects duplicate generation keys or invalid values.
