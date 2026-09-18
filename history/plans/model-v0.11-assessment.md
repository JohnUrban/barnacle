# Model v0.11 assessment queue — initial offline pass complete

The 2026-09-14 audit and independent reply confirmed ten scientific gaps in
v0.10.2. The initial read-only assessment is recorded in
[`history/reports/model-v0.11-assessment-2026-09-18.md`](../reports/model-v0.11-assessment-2026-09-18.md)
and reruns through `history/scripts/assess_model_v0_11.py`. It rejected a
single replacement lag, a universal house-pixel forcing switch, standalone
state persistence, and a tide-bias retune. It accepted time-varying bay head
and `_pluvial_fill` continuity as the next offline candidates. This document
remains a queue, not a model spec, and does not authorize a version bump.

1. **ASSESSED:** the nine minute-resolution observations reject 15 minutes,
   but favor different replacements (Event 8: 10; Event 9: 3). Define an
   observable distributed/dynamic-lag rule before another fit.
2. **PARTIAL:** point/max forcing helps Events 8/9 but worsens Event 7; retain
   catchment mean. Event 9 round-2 MRMS forcing is absent from the archive.
3. **DEFERRED:** only 2.4% of current tank storage survives 60 dry minutes.
   Prototype persistence only with a long-tail/antecedent structure and replay
   failure/outage restarts before considering production state.
4. Compare a two-layer antecedent reservoir with the current memoryless tank;
   reject any design that delays Event 9's bone-dry response excessively.
5. **NEXT CANDIDATE:** evolve bay head through the 45-minute projection using
   astronomical tide plus age-bounded surge rather than holding one value.
6. Test explicit duration, delivery, and drainage structure without treating
   forecast-QPF error as tank-physics error.
7. **QUANTIFIED / ACCEPTED FOR CANDIDATE:** correction is at most 0.090 inch
   on the sampled grid; frozen peaks move 0–0.063 inch and clocks do not move.
8. Keep `driveway_central` a cross-fit threshold observable, never relabel it
   as surveyed elevation.
9. Segment historical tide residuals by model version, lead time, surge source,
   regime, and wind before changing the tide bias.
   **ASSESSED except wind:** current v0.10.2 bias is +0.027 ft and 0–3 h bias
   is +0.013 ft; no bias retune is supported. Wind remains unavailable in the
   prediction log and is not needed to reject the aggregate adjustment.
10. Require a new `model/v0.X.md`, archived prior spec with repaired links,
    code/log stamps, frozen replay/goldens, and surface regeneration in one
    commit for any accepted formula or constant change.

Candidate changes compete against v0.10.2 on peak error, onset timing,
recession timing, false-alert behavior, and all nine observed floods. A lower
peak RMSE alone is not sufficient.
