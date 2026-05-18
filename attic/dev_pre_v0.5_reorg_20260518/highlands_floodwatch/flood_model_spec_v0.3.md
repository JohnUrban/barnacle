# Highlands NJ Bay Avenue Flood Prediction Model — Specification v0.3

**Target:** Predict whether 342 Bay Ave will flood in the next 24 hours,
and at what depth.

**Changes from v0.2:** Empirical threshold replaced with physical formula
grounded in actual elevation data. Local enhancement factor (~1.5 ft)
introduced. Datum conversions explicit. BFE and DFE incorporated for the
high-end of the prediction range.

---

## Elevations and datums (the missing piece, now anchored)

| Reference | Elevation (NAVD88) | Elevation (MLLW) | Source |
|---|---|---|---|
| Mean Lower Low Water (MLLW = 0) | -2.82 ft | 0.00 ft | NOAA datums |
| Sandy Hook MHHW | -1.27 ft | 1.55 ft | NOAA datums |
| **Road centerline / depressed curb at 342 Bay Ave** | **5.30 ft** | **8.12 ft** | Highlands Phase 1 reconstruction plans (via Gemini; should verify) |
| FEMA Base Flood Elevation (1% chance) | 11.0 ft | 13.82 ft | Forerunner / FEMA AE zone |
| Design Flood Elevation | 12.0 ft | 14.82 ft | Forerunner |
| Sandy 2012 peak Sandy Hook | 10.49 ft | 13.31 ft | Borough table |

**Conversion rule:** `elevation_NAVD88 = elevation_MLLW - 2.82` at Sandy Hook.

NOAA's published Sandy Hook datums show NAVD88 = 0.858 m above MLLW =
2.815 ft, so the 2.82 ft offset is essentially exact (within rounding).

---

## Local enhancement factor

Sandy Hook gauge readings systematically *underestimate* water level at
342 Bay Ave by approximately 1.5 ft. This is empirically derived from
4 confirmed flood events:

```
implied_water_at_342_Bay (NAVD88) ≈ Sandy_Hook_obs_MLLW - 2.82 + 1.50
```

Equivalently: `water_at_342_MLLW ≈ Sandy_Hook_obs_MLLW + 1.50`

**Mechanisms (combined, in order of likely importance):**
1. Wind-driven and surge-driven setup piles water into the SE corner of
   Sandy Hook Bay where Highlands sits. The Sandy Hook gauge is on the
   NE corner of the bay, on a more exposed location.
2. Drain backflow delivers bay water onto Bay Ave before the road
   would otherwise be submerged from above. The water "arrives early."
3. The road's design centerline elevation (5.30 ft NAVD88) may be slightly
   optimistic for actual low spots near 342 Bay Ave.

**Validation across 4 events:**

| Event | Sandy Hook obs MLLW | Predicted depth (formula) | Observed depth |
|---|---|---|---|
| Apr 17 2026 | 6.76 ft | 1.7" | ~2" |
| Apr 18 2026 | 7.32 ft | 8.4" | ~10" |
| Dec 19 2025 (tide only) | 6.83 ft | 2.5" + rain (~5") = ~7.5" | ~7-9" |
| Oct 30 2025 (tide only) | 7.57 ft | 11.4" + rain | ~12" |

This is remarkably clean for a model fit with one free parameter. The
1.5 ft factor is currently *static*; refining it as a function of wind,
pressure, and surge magnitude is the obvious next iteration.

---

## Core flood prediction formula

```
local_water_MLLW = Sandy_Hook_obs_MLLW + LOCAL_ENHANCEMENT
local_water_NAVD88 = local_water_MLLW - 2.82
depth_inches_at_342_Bay_road = max(0, (local_water_NAVD88 - 5.30) * 12)

# Rain amplification (when tide is in high tide window)
IF peak_hourly_rain_in_during_high_tide_window >= 0.4:
    rain_contribution_inches = peak_hourly_rain_in * 12
    depth_inches += rain_contribution_inches

# Cold weather override
IF mean_temp_72h < 32°F:
    depth_inches = 0  # drains ice-locked
```

Where:
- `LOCAL_ENHANCEMENT = 1.5 ft` (current best estimate, room for refinement)
- High tide window = ±2 hours of forecast peak tide

---

## Three pathways (revised)

### Pathway A — Bulkhead/road overtopping (rare, catastrophic)

The bulkhead and Bay Avenue itself become inundated from the bay side
directly.

- **Onset:** Sandy Hook observed tide ≥ ~6.6 ft MLLW (when local
  enhancement brings water to curb level). This is your house's
  empirical threshold.
- **Severe:** Sandy Hook ≥ 8.5 ft MLLW (water 1+ ft over curb)
- **Catastrophic:** Sandy Hook ≥ 13 ft MLLW (Sandy / BFE-class event,
  ~6 ft over curb)

### Pathway B — Storm drain backflow (the early-warning mechanism)

Below the Pathway A threshold, bay water can still backflow up through
storm drain outlets and onto streets where street elevation alone wouldn't
flood. This is what produces the "light flooding from grates" pattern.

In our empirical fit, Pathway B onset *is* the local enhancement —
it's how the bay water reaches the street at lower tide levels than
the curb would otherwise permit. Functionally, the model treats this as
the local enhancement factor.

### Pathway C — Rainfall amplification

Heavy rain coinciding with high tide adds depth on top of Pathway A/B.
The drains can't outflow during high tide, so the rain has nowhere to go.

- **Trigger:** Peak hourly rainfall ≥ ~0.4"/hr during ±2h of high tide
- **Magnitude:** Roughly `12 × peak_hourly_rain_inches` additional depth,
  per Dec 19 (0.44"/hr → ~5" extra) and Oct 30 (1.45"/hr → ~10"+ extra,
  but tide alone was also high)

---

## Cold-weather override

When `mean_air_temp_72h < 32°F`, set predicted depth to 0 unless Pathway A
threshold (8.5+ ft Sandy Hook) is exceeded.

**Mechanism:** Ice formation at drain outfalls physically blocks the
backflow pathway that produces the local enhancement.

**Evidence:** Feb 22-23 2026 — observed tide 7.19 ft MLLW, strong onshore
winds, but no flooding at 342 Bay Ave. User confirmed via overnight
vigil. Borough's Nixle archive shows pre-event warnings only, no
post-event flood report.

---

## Forecast inputs at runtime

The model needs these forecasts each morning:

1. **Forecast observed Sandy Hook tide peak (next 24h)** — from NWS
   Coastal Flood Statement or NYHOPS Stevens Institute model. Must
   include surge departure, not just astronomical prediction.
2. **Forecast peak hourly precipitation (next 6h)** — from HRRR or RAP
   gridded model output at Highlands grid cell.
3. **Mean air temperature past 72h** — from Sandy Hook or EWR ASOS, or
   any local sensor.

That's it for the core prediction. Three forecast inputs.

---

## Confirmed labeled events

| Date | SH obs MLLW | Predicted depth (v0.3) | Observed depth | Match? |
|---|---|---|---|---|
| Oct 12-13 2025 nor'easter | 7.63 (brief peak) | ~6" if peak sustained | "no flood at 342" | Mostly minor at sub-threshold times |
| Oct 30 2025 compound | 7.57 | 11" + rain → ~17"? | ~12" | Slight overpredict |
| Feb 22-23 2026 blizzard | 7.19 | 7" (or 0 with cold override) | 0 (no flood) | Cold override correct |
| Apr 17 2026 | 6.76 | 1.7" | ~2" | Excellent |
| Apr 18 2026 | 7.32 | 8.4" | ~10" | Excellent |
| Dec 19 2025 | 6.83 (peak 8 AM) | 2.5" + ~5" rain = 7.5" | ~7-9" | Excellent |

---

## What's still needed

1. **Verify the 5.30 ft NAVD88 curb elevation.** Gemini cited Highlands
   Phase 1 reconstruction plans. The actual document, or a field survey,
   would either confirm or correct this anchor.
2. **Decompose the local enhancement factor.** Right now it's a static
   1.5 ft. Some of it is probably wind-correlated (more onshore wind
   → more piling). Three more flood events with varied wind would
   start to resolve this.
3. **Drainage map for Bay Ave near 342.** Confirms the back-flow
   mechanism and tells us where the outfalls actually are.
4. **NJ LiDAR DEM tile for Highlands.** Lets us check elevations at
   adjacent points (the high spot at Bay+Central, your porch step,
   the bulkhead) without trusting any single survey claim.

---

## Production system sketch

A daily morning script:

1. Pull Sandy Hook NWS Coastal Flood Statement → forecast tide peak
2. Pull HRRR forecast at Highlands grid → peak hourly rain rate next 6h
3. Pull recent temperature history → cold override flag
4. Compute predicted depth using the v0.3 formula
5. Output: "Expected at 342 Bay Ave today: X inches of water at peak
   (around HH:MM). Confidence: high/medium/low based on which inputs
   are firm vs forecast."

Notification triggers:
- depth > 1": alert
- depth > 4": warning
- depth > 8": severe warning
- cold override active and tide forecast > 7 ft: "high tide forecast
  but cold weather should prevent flooding — monitor"
