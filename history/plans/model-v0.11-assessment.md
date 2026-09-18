# Model v0.11 assessment queue — initial offline pass complete

The 2026-09-14 audit and independent reply confirmed ten scientific gaps in
v0.10.2. The initial read-only assessment is recorded in
[`history/reports/model-v0.11-assessment-2026-09-18.md`](../reports/model-v0.11-assessment-2026-09-18.md)
and reruns through `history/scripts/assess_model_v0_11.py`. It rejected a
single replacement lag, a universal house-pixel forcing switch, standalone
state persistence, and a tide-bias retune. The follow-on head prototype uses
the committed NOAA compound-event fixture: moving astronomy helps Oct 30
strongly but is neutral/slightly worse on Dec 19 when surge evolves against
the tide. `_pluvial_fill` continuity is now frozen as an offline v0.10.3
candidate with exact goldens and an independent reference inversion. This
document remains a queue, not a model spec, and does not authorize a version
bump by itself.

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
5. **PROTOTYPED / HOLD:** moving astronomy + constant issue-time surge changes
   standardized 1.0 in/hr tank endpoints +0.82 inches rising / −0.49 inches
   falling and cuts Oct 30 head RMSE 0.340→0.157 ft, but Dec 19 is
   0.249→0.251 ft because surge evolves. Define a bounded observable surge
   tendency and explicit age-expiry/degraded-tail contract before production.
6. Test explicit duration, delivery, and drainage structure without treating
   forecast-QPF error as tank-physics error.
7. **FROZEN OFFLINE v0.10.3 CANDIDATE:** correction is at most 0.090 inch
   on the sampled grid; frozen peaks move 0–0.063 inch and clocks do not move.
   The candidate matches volume-at-base reference arithmetic to 1.07e-14 inch
   (`history/scripts/reproduce_v0_10_3_fill_candidate.py`).
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
