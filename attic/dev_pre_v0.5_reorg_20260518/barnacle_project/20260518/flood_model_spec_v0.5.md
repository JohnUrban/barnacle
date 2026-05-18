# Bay Ave Barnacle — Flood Prediction Model v0.5

**Target:** Predict whether 342 Bay Ave (Highlands NJ) will flood in
the next 24 hours, with per-landmark depth estimates.

**Changes from v0.4:** Arithmetic corrections to three landmark Sandy Hook
threshold values in the Hydraulic Interpretation table and Pathway A onset
levels. Python code (`flood_forecast_daily.py`) was already correct — only
the human-readable tables in v0.4 had errors. No model logic changes.

If anything in another document disagrees with v0.5, **v0.5 wins.**

---

## Core formula (unchanged from v0.4)

```
# Translate Sandy Hook gauge to local water level at 342 Bay Ave
LOCAL_ENHANCEMENT = +0.40 ft                 # empirically fit, 4 events
water_at_342_MLLW = Sandy_Hook_obs_MLLW + LOCAL_ENHANCEMENT
water_at_342_NAVD88 = water_at_342_MLLW - 2.82

# Per-landmark depth (in)
depth_curb       = max(0, water_at_342_NAVD88 - 4.16) * 12
depth_road       = max(0, water_at_342_NAVD88 - 4.36) * 12
depth_intersect  = max(0, water_at_342_NAVD88 - 4.54) * 12
depth_lawn       = max(0, water_at_342_NAVD88 - 4.58) * 12

# Rain amplification (saturating, applied when peak rain >= 0.1"/hr)
rain_add = 8.0 * tanh(peak_rain_rate_in_hr)
depth_curb       += rain_add
depth_road       += rain_add
depth_intersect  += max(0, rain_add - 2)
depth_lawn       += max(0, rain_add - 4)

# Cold weather override (drains ice-locked)
if mean_temp_72h < 32°F and Sandy_Hook < 8.0:
    all depths = 0
```

The shortcut: at any Sandy Hook reading X (MLLW), water at 342 Bay sits
at `(X − 2.42)` ft NAVD88. So Sandy Hook threshold for landmark Y NAVD88
is just `Y + 2.42`.

---

## Hydraulic interpretation (CORRECTED)

| Sandy Hook obs MLLW | Water at 342 Bay (NAVD88) | What gets wet |
|---|---|---|
| < 6.06 | < 3.64 | All dry |
| 6.06 | 3.64 | Water at lowest road corner (across Bay) — *early-warning sentinel* |
| 6.20 | 3.78 | Gutter line at user's walkway begins filling |
| 6.33 | 3.91 | Lowest storm inlet grate becomes submerged |
| **6.58** | **4.16** | **Water tops curb at walkway — flood onset at 342 Bay** |
| 6.74 | 4.32 | Middle of Bay Ave at the corner |
| 6.78 | 4.36 | Middle of Bay Ave at user's spot — full road cover begins |
| 6.96 | 4.54 | **Intersection center (local high point) submerged** |
| 7.00 | 4.58 | **Water at lawn / walkway step** |
| 7.12 | 4.70 | Middle of road near driveway |
| 7.58 | 5.16 | ~1 ft above curb (Apr 18 2026 class event) |
| 8.0+ | 5.58+ | Severe regime; approaching bulkhead overtopping |
| 13.0+ | 10.58+ | Hurricane Sandy-class (~7 ft over Bay Ave) |

These are all derived as `landmark_NAVD88 + 2.42`. No other arithmetic
involved.

---

## Three pathways

### Pathway A — Direct overtopping (rare, catastrophic)

Bay water rises directly to street and lawn elevations.

- **Onset:** Sandy Hook ≥ 6.58 ft MLLW (water tops curb at walkway)
- **Moderate at 342 Bay:** Sandy Hook ≥ 7.00 ft (water on lawn step)
- **Severe at 342 Bay:** Sandy Hook ≥ 7.58 ft (~1 ft over curb)
- **Catastrophic:** Sandy Hook ≥ 11.0 ft MLLW (BFE — 100-year flood)
- **Sandy 2012:** Sandy Hook 13.31 ft MLLW (~7 ft on Bay Ave per Borough table)

### Pathway B — Storm drain back-flow (the workhorse)

Storm drain outfalls below Bay Ave become submerged in the bay; back-pressure pushes water up through inlets onto the street. The +0.40 ft "local enhancement" between Sandy Hook gauge and water at 342 Bay is largely Pathway B at work — bay water arrives at the street before the gauge reading alone would predict.

Inlet grate elevations near 342 Bay are 3.91–4.22 NAVD88 (= Sandy Hook thresholds 6.33–6.64 MLLW). The empirical 6.58 onset matches: bay water is above the inlet grates by Sandy Hook ~6.4 ft, well before the curb is structurally overtopped.

### Pathway C — Rainfall amplification

Heavy rain coinciding with high tide adds depth on top of A/B. Drains can't outflow against bay back-pressure, so rain pools.

- **Trigger:** Peak hourly rainfall ≥ ~0.4 in/hr during ±2 h of high tide
- **Magnitude:** `8 × tanh(peak_rain_rate)` inches added at curb / road middle; less at the intersection (sheds via crown) and lawn (sheds via slight slope)
- **Calibration source:** Dec 19 2025 (0.44"/hr, +~5" added) and Oct 30 2025 (1.45"/hr)

---

## Cold-weather override

When `mean_air_temp_72h < 32°F` and Sandy Hook < 8.0 ft, set predicted depths to zero.

**Mechanism:** Ice at storm drain outfalls blocks the Pathway B back-flow that produces the +0.40 ft local enhancement. Without that pathway, bay water at 7+ ft MLLW stays in the bay rather than emerging on Bay Avenue.

**Evidence:** Feb 22–23 2026, observed tide 7.19 ft + strong onshore winds + no flooding at 342 Bay confirmed by overnight vigil. Borough issued no post-event coastal flood advisory.

**Caveat:** Single confirmed observation. Confidence in the override threshold (72h, 32°F) is low. More cold-weather high-tide events will refine.

---

## Labeled events used for calibration

| Date | Sandy Hook obs MLLW | Rain peak | Observed depth | Predicted depth (v0.5) | Notes |
|---|---|---|---|---|---|
| Oct 13 2025 nor'easter | 7.63 (brief) | 0.23 in/hr | No flood at 342 (per neighbors + brief peak) | — | Mostly minor; flood only ~6 min at moderate stage |
| Oct 30 2025 compound | 7.57 | 1.45 in/hr | ~12 in (severe) | ~14 in incl rain | Best fit; tide+rain compound |
| Feb 22–23 2026 blizzard | 7.19 | 0.10 in/hr (snow) | No flood (verified) | 0 (cold lockout) | Cold override correct |
| Apr 17 2026 | 6.76 | 0.01 in/hr | ~2 in (light) | 2.2 in | Excellent |
| Apr 18 2026 | 7.32 | 0 | ~10 in (moderate) | 10.8 in | Excellent |
| Dec 19 2025 | 6.83 | 0.44 in/hr | ~7–9 in (moderate) | 2.8 in tide + ~3 in rain = ~6 in | Good — slight underestimate of rain term |
| Aug 21 2025 (newly discovered) | unknown — NWS forecast 8.0 ft @ 7 PM, +2.4 ft surge, Moderate cat | unknown | unknown — user not home? | n/a | Need to check; this was a forecast Moderate event |

---

## Forecast inputs at runtime

1. **Forecast peak Sandy Hook total water level (next 24 h)** — from NWS Coastal Flood product if active, else NOAA predicted tide + persistent surge
2. **Forecast peak hourly precipitation (next 6 h)** — from NWS api.weather.gov hourly forecast for Highlands grid
3. **Mean air temperature past 72 h** — from NOAA Sandy Hook met station

Production system: `flood_forecast_daily.py` plus `nws_surge_parser.py`.

---

## What might break this model

1. **Local enhancement isn't truly constant.** Currently 0.40 ft fits all 4 confirmed events to within ±0.05 ft. May vary with wind direction, storm category, or lunar phase. Becomes detectable with 8–10 events.
2. **Rain term is fit with one data point** (Dec 19). The 8·tanh saturation curve is plausible but speculative.
3. **Cold lockout based on single observation** (Feb 22–23). The 32°F / 72h threshold is a guess.
4. **Phase 1 construction status unknown.** If curb has been reconstructed to design (+0.04 ft), all thresholds shift up by ~0.5 inch — within noise.
5. **Sea-level rise.** Will silently shift the +0.40 enhancement upward by ~0.04 ft per decade. Re-calibrate every 5–10 years.

---

## Open elevation questions

1. **Lawn step exact height.** User estimated 4.54–4.63 NAVD88 range; spec uses 4.58 as midpoint. Field measurement would tighten.
2. **Bay Avenue elevations.** Phase 1 reconstruction PDF covers Central / Beach / Ocean Aves only. Bay Ave itself isn't in scope — Bay Ave–side curb came from the corner of the Central drawing.
3. **Storm drain outfall locations.** Inlet elevations known; outfall pipes' discharge locations unknown. Would clarify Pathway B mechanism. Stephen Winters (Floodplain Administrator, swinters@highlandsnj.gov) likely has the storm sewer map.

---

## Cross-references

- Python implementation: `flood_forecast_daily.py` (uses these exact values via module-level constants)
- NWS surge parser: `nws_surge_parser.py`
- Elevation source data: `highlands_local_elevations.md` (note: that file's bottom "Hydraulic interpretation" table predates v0.5 and may have slightly off range edges — v0.5 supersedes)
- Historical-stats project context: `HANDOFF_historical_data.md` (already uses correct v0.5 thresholds)
- Deployment context: `HANDOFF_deploy_script.md`
- Full project history: `BARNACLE_PROJECT_HANDOFF.md`
