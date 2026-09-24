# Surge decay toward the recent average — plan (2026-09-23)

Status: **plan, not implemented, not promoted.** Owner decisions recorded in
BACKLOG (`missing-surge-ladder`, `missing-surge-ladder-decay`,
`fresh-surge-decay`). Evidence: `history/scripts/surge_persistence_decay.py`,
`history/scripts/surge_decay_views.py`, output in
`history/reports/2026-09-23-surge-decay-views.txt`.

## Why
Every forecast of a future hour guesses that hour's surge from the latest
reading. The gap between the reading and the target hour is the forecast
lead, whether the gauge is healthy (fresh reading, target 20 h out) or silent
(stale reading). Holding the surge constant is the current rule for the 30-h
curve, the rain tank, and per-tide persistence. Twenty years of Sandy Hook
data say a surge that decays toward the recent average is more accurate.

## One formula for fresh and stale readings
    surge(t) = mean + (s_obs - mean) * exp(-(t - t_obs) / tau)
- `s_obs`, `t_obs`: the latest valid observed surge and ITS observation
  time (not the run time). A fresh reading and a gauge outage are the same
  formula; an outage only makes `t - t_obs` larger.
- `mean`: trailing 365-day mean observed surge (currently about +0.5 to
  +0.75 ft; sea level above the 1983-2001 tidal epoch). Zero is biased low.
- `tau`: 36 h (measured; see below).

## Measured (MAE ft, toward the trailing 365-d mean)
| View | lead 12 h const -> tau 36 | 24 h | 30 h |
|---|---|---|---|
| All hours (curve, tank) | 0.296 -> 0.273 | 0.399 -> 0.343 | 0.449 -> 0.369 |
| High tides (per-tide peaks) | 0.291 -> 0.267 | 0.394 -> 0.335 | 0.453 -> ~0.36 |
| Bay near the plug band (2.5-3.8 ft NAVD88) | 0.283 -> 0.273 | 0.385 -> 0.356 | 0.446 -> 0.390 |
| Storm starts (reading >= +1 ft) | 0.502 -> 0.436 | 0.739 -> 0.559 | 0.827 -> 0.574 |
- tau 24-48 h are all close; 36 h is best or near-best in every view and
  in both halves of the record (2006-2015 and 2016-2026 agree).
- Decaying toward ZERO is worse than constant in the plug-band view; toward
  the mean it wins there too. The mean matters most where rain matters.

## Outage ladder (owner decision)
1. Fresh reading (<= 60 min): the formula above.
2. Reading older than 60 min but in the 6-h download: same formula, label
   "surge from N h ago".
3. Older: last good `(s_obs, t_obs)` from a small state file, same formula,
   label with its age.
4. After a snap threshold: surge = mean exactly, label "surge unavailable,
   using the typical offset". Threshold to be set where the decayed departure
   is negligible (e.g. |s_obs - mean| * exp(-age/tau) < 0.1 ft) or a fixed
   age, whichever comes first; to be decided in the spec.

## Precedence unchanged
NWS product rows still win for their high tides. Decay replaces only the
held-constant observed surge (30-h curve + tank, per-tide persistence rung,
outlook persistence rung, whose unscored tau 48 h toward zero becomes this).

## Versioning
Class (a): formula change. New `model/v0.X.md`, NEW replay goldens, rule-12
independent review + owner DECISION before production. Sequencing with the
held v0.10.5 (class b) is the owner's call: promote v0.10.5 first and make
this v0.10.6, or fold both into one reviewed version.

## Next research (not in the simple model)
John's idea: let conditions drive the decay rate (tau -> long when the
forcing persists; tau then reflects confidence, not physics).
- First history test (past surge only): storms already elevated >= +1 ft
  for 24 h are MORE predictable (lower error) but their best tau is NOT
  longer (24-36 h, same as fresh spikes). Past persistence alone does not
  predict slower decay.
- So the signal must come from the FUTURE forcing: forecast wind speed and
  direction (onshore NE/E fetch), pressure, NWS/P-ETSS surge guidance,
  Ekman setup, river flow. Data to pull: historical wind at Sandy Hook
  (CO-OPS `wind`, `air_pressure`) against surge persistence; then forecast
  wind from the NWS grid for live use.
- Every hourly run re-anchors on the newest reading, so the decay only
  governs how far the forecast drifts between readings and the target.
