# Highlands NJ Bay Avenue Flood Prediction Model — Specification v0.2

**Target:** Predict whether 342 Bay Ave (and similar low-lying Highlands
spots) will flood in the next 24 hours, with rough depth estimate.

**Output:** Binary `flood / no-flood` + probability + depth estimate.

**Changes from v0.1:** Antecedent saturation mechanism removed (was based
on a misreading of tide data). Pathway B threshold anchored at 6.7 ft
Sandy Hook observed based on labeled events. Cold-weather override added.
Surge promoted from "useful feature" to "critical feature." Wind direction
hypothesis softened.

---

## The core insight

**Look at observed total water level at Sandy Hook (= astronomical +
surge), not at the astronomical tide prediction alone.**

Every flood event you've experienced had between +0.8 and +2.9 ft of surge
on top of the predicted astronomical tide. Tide apps and tide tables show
only the astronomical component. The NWS Coastal Flood Statements and the
real-time Sandy Hook gauge are the sources that include surge.

| Event | Predicted | Observed | Surge | Outcome at 342 Bay |
|---|---|---|---|---|
| Oct 12-13 nor'easter | 5.10 ft | 7.63 ft peak (mostly 6.7-7.7, only 6 min in moderate) | +2.53 | No flood (per neighbors + duration) |
| Oct 30 compound | 4.67 ft | 7.57 ft | +2.90 | Severe flood, ~12" |
| Feb 22-23 blizzard | 4.80 ft | 7.19 ft | +2.39 | No flood (cold override) |
| Apr 17 | 5.93 ft | 6.76 ft | +0.83 | Light flood, ~2" |
| Apr 18 | 6.02 ft | 7.32 ft | +1.30 | Moderate flood, ~10" |
| Dec 19 | 5.04 ft | 6.83 ft (peak 8 AM) | +2.11 | Light-to-moderate flood, ~7–9" |

---

## Three pathways

### Pathway A — Bulkhead overtopping (rare, catastrophic)

Untested at 342 in current data. Historical reference from Borough's
calibration table:

- Sandy 2012: Sandy Hook 13.31 ft → 7 ft on Bay Ave
- Donna 1962, Nor'easter 1992: 10.3–10.5 ft → 4 ft
- Irene 2011: 9.75 ft → 3 ft

**Trigger:** Observed Sandy Hook total tide ≥ ~8.0 ft.

### Pathway B — Tidal drain backflow (the dominant mechanism)

At sufficiently high tide, the storm drain outfalls below Bay Ave are
submerged and bay water backflows up onto the street.

**Empirical threshold table (Sandy Hook observed total tide):**

| Observed tide | Expected outcome at 342 Bay Ave | Estimated depth |
|---|---|---|
| < 6.7 ft | No flood | 0 |
| 6.7–7.0 ft | Light flood — water out of grates, sidewalk reached | 2–4" |
| 7.0–7.5 ft | Moderate flood — full road cover, sidewalk + step | 6–10" |
| 7.5–8.0 ft | Severe flood — extends laterally up Central | 10–14" |
| 8.0+ ft | Untested at 342; expect major flooding | 1–2+ ft |

Calibrated from 4 confirmed events at 342 Bay Ave (Apr 17, Apr 18, Oct 30,
Dec 19). Slope is roughly **15 inches of depth per 1 foot of tide above
the 6.7 ft threshold**, but with significant uncertainty given the small
sample.

### Pathway C — Rainfall amplification of Pathway B

Heavy rainfall during high tide adds depth on top of what tide alone would
produce. The drain backflow mechanism doesn't free up to handle the rain
until the tide drops.

**Trigger:** Peak hourly rainfall ≥ ~0.4"/hr while observed tide is
within ±3h of peak and ≥ ~4 ft (drainage outfall elevation).

**Evidence:**
- Dec 19: 0.44"/hr rain at high tide added ~4" of depth beyond what
  6.83 ft tide alone would have produced (compared to Apr 17's similar
  tide with no rain producing ~2").
- Oct 30: 1.45"/hr rain at high tide produced the deepest event in the
  dataset.

No clean "pure pluvial at low tide" event has been observed; we don't yet
know whether heavy rain at low tide alone can flood 342 Bay Ave.

---

## Cold-weather override

**Rule:** When average air temperature for the preceding 3+ days has been
below freezing, the Pathway B threshold does not apply. Flooding may not
occur even with observed tide > 6.7 ft.

**Evidence:** Feb 22-23 2026 had observed tide 7.19 ft with strong onshore
winds, but the user confirmed no flooding occurred despite being awake and
checking through the night. Borough did not issue a post-event flood
advisory. Most likely mechanism is ice formation at drain outfalls
physically blocking the back-flow path.

**Implementation:** Set a `cold_lockout` boolean feature based on
`mean_temp_last_72h < 32°F`. When true, set predicted flood probability
to near-zero unless Pathway A threshold is exceeded.

---

## Features (model inputs)

### Primary (forecast must include these)
- `forecast_observed_tide_peak_24h` — Total water level peak, including
  forecast surge. From NWS Coastal Flood Statement or NYHOPS.
- `forecast_peak_rain_rate_6h` — Peak hourly precipitation rate in next
  6 hours. From HRRR.
- `mean_temp_last_72h` — For cold-weather override.

### Secondary
- `current_observed_surge` — Live Sandy Hook surge departure; updates the
  forecast as the event unfolds.
- `tide_phase_at_rain_peak` — Whether forecast rainfall peak coincides
  with high tide (Pathway C trigger).
- `forecast_wind_speed_max_24h` — Stronger winds generally amplify surge,
  though direction matters less than initially hypothesized.

### Tertiary (worth tracking; not yet in core model)
- `wind_dir_during_storm` — NE may be protective per ShorelySafe Oct report,
  but Feb 22-23 N-wind no-flood and April 18 SE-wind flood complicate this.
- `min_pressure_24h` — Loosely correlates with surge magnitude.
- `lunar_phase` — Spring tides matter astronomically.

### Removed (no longer used)
- ~~`flooded_in_past_48h`~~ — Antecedent saturation hypothesis falsified
  by April 18's actual observed tide being higher than April 17's.

---

## Decision logic

```
IF cold_lockout:
    flood_prob = 0.05  # very low, but not zero
    expected_depth = 0
ELSE:
    # Pathway A check
    IF forecast_observed_tide_peak > 8.0:
        flood_prob = 0.95
        expected_depth_in = pathway_a_curve(tide_peak)

    # Pathway B check
    ELIF forecast_observed_tide_peak > 6.7:
        flood_prob = sigmoid((tide_peak - 6.7) * 5)
        expected_depth_in = 15 * (tide_peak - 6.7)

        # Pathway C amplification
        IF forecast_peak_rain_rate_6h > 0.4
           AND tide_phase_at_rain_peak == "high":
            expected_depth_in += min(8, 15 * forecast_peak_rain_rate_6h)
            flood_prob = max(flood_prob, 0.7)

    ELSE:
        flood_prob = 0.02
        expected_depth_in = 0
```

---

## Labeled data so far

| Date | Sandy Hook obs tide | Rain peak | Flood at 342 Bay? | Depth |
|---|---|---|---|---|
| Oct 12-13 2025 | 7.63 (brief) | 0.23"/hr | No (per neighbors, brief peak) | 0 |
| Oct 30 2025 | 7.57 | 1.45"/hr | Yes | ~12" |
| Feb 22-23 2026 | 7.19 | 0.10"/hr (snow) | **No** (cold override) | 0 |
| Apr 17 2026 | 6.76 | 0.01"/hr | Yes (light) | ~2" |
| Apr 18 2026 | 7.32 | 0 | Yes (moderate) | ~10" |
| Dec 19 2025 | 6.83 | 0.44"/hr | Yes (light-mod) | ~7-9" |

Plus 38 other rain events Sep 2025 – May 2026 presumed no-flood (none had
observed tide > 6.5 ft AND rain rate > 0.4"/hr simultaneously per the
merged dataset).

---

## Data sources

- **NJDEP/Rutgers MPE rainfall** — station RABCH022 "Highlands":
  https://njdep.rutgers.edu/rainfall/
- **NOAA Sandy Hook (8531680) water level + met:**
  https://tidesandcurrents.noaa.gov/waterlevels.html?id=8531680
  https://tidesandcurrents.noaa.gov/met.html?id=8531680
- **NWS Mt Holly Coastal Flood Statements:** regional total-tide forecast
- **Stevens Flood Advisory System:** hyperlocal hydrodynamic model
  http://hudson.dl.stevens-tech.edu/sfas/d/
- **Sandy Hook Tidal Flooding Dashboard:** Borough-linked,
  https://hondrospj.github.io/Sandy-Hook/
- **Ground truth labels:** user log, Borough ShorelySafe post-event PDFs,
  Borough Nixle archive, NJ MyCoast

---

## What's still missing

1. **Forecast tide data with surge** — currently looking at observations
   after the fact. For real-time prediction, need to ingest NWS forecasts.
2. **Forecast rainfall** — HRRR or RAP model API ingestion.
3. **More labeled events** — especially edge cases:
   - Pure pluvial at low tide (does heavy rain alone flood 342?)
   - Borderline tides (6.5–6.7 ft) to refine the threshold
   - Another cold-weather high-tide event to confirm the override
4. **Local elevation data** for 342 Bay Ave specifically — NJ LiDAR DEM
   would let us translate predicted water level to depth above the
   user's specific spot rather than the generalized "Bay Ave" depth.
5. **Drainage outfall elevation** — currently estimated at ~4 ft MLLW
   for the Pathway C tide trigger; a Borough drainage map would confirm.

---

## Forecast workflow (production system)

Each morning, the system would:

1. Pull NWS Sandy Hook coastal flood forecast (next 24h, observed tide)
2. Pull HRRR forecast for Highlands grid (next 6h, hourly precipitation)
3. Compute `cold_lockout` from past 72h temperature average
4. Apply decision logic above
5. Output: probability + expected depth + driver explanation
   ("forecast tide 7.1 ft + light rain — expect ~6 inches at 342 Bay")
