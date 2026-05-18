# Highlands NJ Bay Avenue Flood Prediction Model — Specification v0.1

**Target:** Predict whether 342 Bay Ave (and similar low-lying Highlands spots)
will flood in the next 24 hours.

**Output:** Binary `flood / no-flood` plus probability; depth estimate as a
stretch goal.

---

## Three pathways

Floods at 342 Bay Ave can arise from three distinct mechanisms. Any one
can trigger flooding alone, and they can compound.

### Pathway A — Bulkhead overtopping (rare, severe)

Water from Sandy Hook Bay overtops the seawall/bulkhead and floods Bay Ave
from the bay side.

- **Trigger threshold (estimated):** Total water level > ~7.7 ft MLLW at Sandy Hook
- **Frequency:** Roughly once every 1–3 years
- **Historical examples (Borough calibration):**
  - Sandy 2012: 13.31 ft Sandy Hook → 7 ft on Bay Ave
  - Donna 1962, Nor'easter 1992: 10.3–10.5 ft → 4 ft on Bay Ave
  - Irene 2011: 9.75 ft → 3 ft on Bay Ave
- **Note:** None of the user's logged events fall in this regime.

### Pathway B — Tidal drain backup (chronic nuisance)

At sufficiently high tide, storm drain outfalls are submerged and bay water
backflows up through the drains onto the street. No rain needed.

- **Trigger threshold (estimated):** Tide > ~6.3 ft at Atlantic Highlands (~6.2 ft Sandy Hook), sustained 30+ min
- **Frequency:** Several times per year, especially around spring tides
- **Logged examples:**
  - Apr 17 2026: 6.41 ft peak → light flooding from drains, ~2"
  - Apr 18 2026: 6.25 ft peak + antecedent → moderate, ~10"
- **Key amplifier:** Antecedent saturation. April 18 flooded worse than
  April 17 *with lower tide* — the prior day's flood left drains backed up
  and groundwater elevated.

### Pathway C — Compound rain+tide (the emerging concern)

Heavy rainfall arrives while the tide is high enough to block drainage.
Water has nowhere to go and accumulates rapidly.

- **Trigger threshold (estimated):** Peak hourly rainfall > ~1.0"/hr AND
  tide above ~4 ft MLLW (the likely drainage outfall elevation)
- **Frequency:** Once observed in the user's 8 months, but the only event
  that produced ~1 ft of water on Bay Ave from a non-storm-surge cause
- **Logged example:**
  - Oct 30 2025: 1.45"/hr peak (at 3 PM) + 4.65 ft tide (peak 2:41 PM) → ~1 ft on Bay Ave
- **Key insight:** Rainfall RATE matters, not total. The 8-month data shows
  rain totals up to 1.15" without flooding (Jan 25), but Oct 30's 1.45"/hr
  peak was triple the next-highest peak (Dec 19 at 0.44"/hr).
- **Critical unknown:** Whether ~0.5"/hr at high tide would flood. We need
  to check the tide phase at Dec 19's 0.44"/hr peak to find out.

---

## Features (model inputs)

### Tidal
- `pred_high_tide_24h` — Predicted astronomical peak in next 24h (Sandy Hook)
- `obs_surge_now` — Current observed water level minus predicted (proxy for forecast skill)
- `time_to_next_high_tide`
- `forecast_total_water_level` — pred_tide + forecast_surge from NWS/NYHOPS

### Meteorological
- `wind_speed_max_24h`
- `wind_dir_N_component` — wind direction matters specifically because Sandy
  Hook Bay opens NW. NE winds = 12-mile fetch (Brooklyn) = protective.
  N/NW winds = long fetch over the bay = dangerous. This is from the
  ShorelySafe Oct 2025 report.
- `min_pressure_24h` — Each 1 inHg drop ≈ 13 inches water column

### Precipitation
- `peak_hourly_rain_next_6h` — From HRRR or NAM forecast; the key feature
- `cumulative_rain_next_24h`
- `rate_at_high_tide` — Specifically: forecast rate during ±2h of high tide

### Antecedent
- `flooded_in_past_48h` — Boolean
- `cumulative_rain_past_72h` — Soil saturation proxy
- `season` — Seasonal MSL variation

### Static / contextual
- `lunar_phase` — Spring vs neap, perigee
- `is_offshore_low` — Storm position relative to NJ coast

---

## Architecture

### Tier 1 — Hard rules (high precision)

```
IF peak_hourly_rain_next_6h > 1.0
    AND tide_at_rain_peak > 4.0 ft:
    → FLOOD (compound, Pathway C)

ELIF forecast_total_water_level > 7.7 ft:
    → FLOOD (overtopping, Pathway A)

ELIF forecast_total_water_level > 6.3 ft AND wind_dir_N_component > 0:
    → FLOOD (tidal, Pathway B)

ELIF forecast_total_water_level > 6.0 ft AND flooded_in_past_48h:
    → FLOOD (tidal with antecedent, Pathway B amplified)
```

### Tier 2 — Probabilistic score

For cases where Tier 1 doesn't trigger but conditions are elevated, compute
a continuous risk score:

```
risk = w1 * relu(forecast_total_water_level - 6.0)
     + w2 * relu(peak_hourly_rain_next_6h - 0.3) * 10
     + w3 * forecast_total_water_level * flooded_in_past_48h
     + w4 * wind_N_component * (wind_speed > 15)
     - w5 * (forecast_total_water_level < 5.0)  # nothing happens at low tide
```

Calibrate weights against labeled events; convert score to probability with
logistic transform.

### Tier 3 — ML refinement (future)

Once we have 50+ labeled events (~2–3 more years of data), retrain with
gradient-boosted trees on the same feature set. Tier 2 rules become
features rather than rules.

---

## Labeled data so far

| Date | Flood? | Pathway | Bay Ave depth |
|---|---|---|---|
| Oct 12-13 2025 | Town flooded (status at 342 unclear) | B (severe tidal, 7.71 ft Sandy Hook) | Unknown for 342 |
| Oct 30 2025 | Yes | C (compound) | ~1 ft |
| Feb 22-23 2026 | No | (forecast B failed to materialize) | 0 |
| Apr 17 2026 | Yes | B (tidal, light) | ~2" |
| Apr 18 2026 | Yes | B amplified by antecedent | ~10" |
| 39 other rain events Sep 2025–May 2026 | Unlabeled | — | Presumed 0 |

---

## Data sources

### Rainfall — NJDEP/Rutgers MPE
- Station: **RABCH022 "Highlands"** (40.406, -73.995)
- Resolution: hourly, 2.5-mi grid (radar + gauges)
- URL: https://njdep.rutgers.edu/rainfall/

### Water level & tide predictions — NOAA Sandy Hook
- Station: **8531680**
- Resolution: 6-min observed; hourly verified
- URL: https://tidesandcurrents.noaa.gov/waterlevels.html?id=8531680

### Tide predictions (subordinate) — Atlantic Highlands
- Station: **8531662**
- Offset: Sandy Hook × 1.01, shifted -10 min
- Note: prediction-only, no real-time gauge

### Wind + pressure — NOAA Sandy Hook
- URL: https://tidesandcurrents.noaa.gov/met.html?id=8531680

### Coastal flood forecasts — NWS / Stevens NYHOPS
- NWS Mt Holly: regional coastal flood advisories
- Stevens Flood Advisory System: hydrodynamic, hyperlocal
  http://hudson.dl.stevens-tech.edu/sfas/d/

### Ground-truth labels
- User's flood log (primary)
- Highlands Borough ShorelySafe post-event reports
- Highlands Borough Nixle/Facebook archive
- NJ MyCoast crowdsourced flood photos

---

## What's still missing

1. **Sandy Hook observed water level + met data for the 5 labeled events**
   to validate the surge and wind hypotheses.
2. **Labels for the high-peak unlabeled rain events** (Dec 19, Nov 25, Mar 6,
   Apr 30). Especially Dec 19 — its 0.44"/hr peak is the second-highest in
   8 months. We need to know what the tide was doing at 7–11 AM Dec 19 and
   whether 342 Bay Ave flooded.
3. **Drainage outfall elevation at Bay Ave near 342** — would let us
   calibrate the compound threshold properly.
4. **NJ LiDAR DEM for 342 Bay Ave** — converts predicted water level to
   "feet above street level" at the user's specific spot.
5. **Confirmation on Oct 12-13 status at 342 Bay Ave** — Sandy Hook hit
   7.71 ft (top 0.15% historic) and other parts of Highlands flooded.
   Why didn't 342? Microelevation, or did it actually flood?

---

## Forecast inputs needed at runtime

For the daily prediction, the model needs to ingest forecasts from these
upstream sources:

- NWS Mt Holly Coastal Flood Statement (forecast tide + departure)
- NWS HRRR or RAP model (forecast hourly rainfall rate)
- NWS forecast wind (direction and speed)
- NWS forecast pressure
- Current observed water level from Sandy Hook
- Current Highlands rainfall from RABCH022

All of these have free public APIs.
