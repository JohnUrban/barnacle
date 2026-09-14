# Model v0.11 assessment queue — no parameter change authorized

The 2026-09-14 audit and independent reply confirmed ten scientific gaps in
v0.10.2. This document keeps them in one testable sequence; it is not a model
spec and does not authorize a version bump.

1. Fit response lag against the nine minute-resolution rise observations from
   Events 8 and 9; preserve Event 9's dry-catchment rapid response as a bound.
2. Test near-core point/box forcing and compound superposition against Event
   9's two rounds, reporting rise, crest, and recession separately.
3. Prototype persisted nowcast storage with decay; replay every measured event
   and failure/outage restart before considering production state.
4. Compare a two-layer antecedent reservoir with the current memoryless tank;
   reject any design that delays Event 9's bone-dry response excessively.
5. Evolve bay head through the 45-minute projection using astronomical tide
   plus age-bounded surge rather than holding one value.
6. Test explicit duration, delivery, and drainage structure without treating
   forecast-QPF error as tank-physics error.
7. Quantify and repair `_pluvial_fill`'s sub-bin discontinuity.
8. Keep `driveway_central` a cross-fit threshold observable, never relabel it
   as surveyed elevation.
9. Segment historical tide residuals by model version, lead time, surge source,
   regime, and wind before changing the tide bias.
10. Require a new `model/v0.X.md`, archived prior spec with repaired links,
    code/log stamps, frozen replay/goldens, and surface regeneration in one
    commit for any accepted formula or constant change.

Candidate changes compete against v0.10.2 on peak error, onset timing,
recession timing, false-alert behavior, and all nine observed floods. A lower
peak RMSE alone is not sufficient.
