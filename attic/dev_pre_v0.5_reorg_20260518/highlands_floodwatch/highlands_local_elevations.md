# 342 Bay Avenue and Immediate Surroundings — Elevation Reference

**Datum:** All elevations in NAVD88 unless otherwise noted.
**Conversion to MLLW (Sandy Hook gauge units):** `MLLW = NAVD88 + 2.82`
**Conversion to NGVD29 (older surveys):** `NGVD29 = NAVD88 + 1.09` (approx)

---

## Primary sources

1. **Forerunner Borough property platform**
   `https://highlandsboroughnj.withforerunner.com/properties/01751123-0ffe-48f9-be13-3f920022e695`
   Authoritative for FEMA flood zone, BFE, DFE.

2. **HLND2303 Phase 1 Sanitary Improvements — Road Reconstruction Supplement Set**
   H2M Associates, Inc., dated May 6, 2024.
   Signed by Alan P. Hilla Jr., P.E., NJ License 24GE03944200.
   Field survey by PS&S, Thomas J. Murphy, April 19, 2024.
   `https://highlandsnj.gov/wp-content/uploads/2024/05/HLND2303-Road-Reconstruction-Supplement-Set-2024.05.06.pdf`
   Three drawings:
   - **C 100** Central Avenue Roadway Elevation Design Plan
   - **C 101** Beach Boulevard Roadway Elevation Design Plan
   - **C 102** Ocean Avenue Roadway Elevation Design Plan
   Bay Avenue itself was *not* in Phase 1 scope.
   Convention on drawings: lowercase `tc/bc` = existing survey elevations;
   UPPERCASE `TC:/BC:` = design (post-reconstruction) elevations.

3. **User on-site readings from drawing C 100** (definitive for 342 Bay Ave and its immediate surroundings)

---

## Federal / FEMA references (Forerunner)

| Reference | NAVD88 | MLLW |
|---|---|---|
| Flood Zone | AE | — |
| Base Flood Elevation (1% chance) | 11.0 ft | 13.82 ft |
| Design Flood Elevation | 12.0 ft | 14.82 ft |
| FIRM Panel | 34025C0088H | — |
| Initial FIRM date | 9/3/1971 | — |
| Pre-FIRM | Yes | — |
| In Floodway | No | — |
| In CBRS | No | — |
| In OPA | No | — |
| NJDEP CAFE designation | SLR 4ft | — |

---

## 342 Bay Avenue — surveyed and design elevations

### Bay Avenue side (in front of house, near walkway)

| Feature | NAVD88 | MLLW | Source |
|---|---|---|---|
| Top of curb (TC) | 4.16 | 6.98 | C 100 reading |
| Bottom of curb / gutter (BC) | 3.78 | 6.60 | C 100 reading |
| Curb face height | 0.38 ft | — | TC − BC |
| Middle of Bay Ave road | 4.36 | 7.18 | C 100 reading |
| Lawn / walkway step-up | ~4.54–4.63 | ~7.36–7.45 | Inferred (equal-step-up rule + 4.69 observation) |

### Central Avenue side (between Bay+Central corner and fire hydrant)

| Feature | NAVD88 (existing) | NAVD88 (design) | MLLW (design) |
|---|---|---|---|
| Top of curb | 4.12 | 4.20 | 7.02 |
| Bottom of curb / gutter | 3.91 | 3.87 | 6.69 |
| Middle of Central Ave road | 4.44 | — | 7.26 |

### Driveway approach (Central Ave side, Bay-side edge of driveway)

| Feature | NAVD88 | MLLW |
|---|---|---|
| Curb just before driveway (TC) | 4.41 | 7.23 |
| Curb just before driveway (BC) | 4.08 | 6.90 |
| Where driveway starts (TC, smaller font) | 4.27 | 7.09 |
| Where driveway starts (BC) | 4.26 | 7.08 |

### Far side of driveway

| Feature | NAVD88 | MLLW |
|---|---|---|
| Top of curb | 4.52 | 7.34 |
| Bottom of curb | 4.19 | 7.01 |
| Middle of road near driveway | 4.70 | 7.52 |

---

## Bay+Central intersection geometry

| Feature | NAVD88 | MLLW | Notes |
|---|---|---|---|
| Center of intersection | 4.54 | 7.36 | **Local high point** — explains why intersection is often dry when surrounding road floods |
| Middle of Bay Ave at corner | 4.32 | 7.14 | Bay Ave road dips slightly approaching corner |
| Corner *across Bay Ave* from user's house | **3.64** | **6.46** | **Lowest point in immediate vicinity** |
| Middle of Central at that far corner | 3.91 | 6.73 | |
| Walkway between corners (across Central, opposite user's side) | 4.44 | 7.26 | |
| Storm inlet grate, Bay+Central corner | 3.91–4.22 | 6.73–7.04 | Range due to hard-to-read drawing |

---

## Hydraulic interpretation — what gets wet at what Sandy Hook level

Using `water_at_342_Bay_MLLW = Sandy_Hook_obs_MLLW + 0.4` (local enhancement, empirically fit) and converting to NAVD88 to compare against the table above:

| Sandy Hook obs (MLLW) | Water at 342 Bay (NAVD88) | What gets wet |
|---|---|---|
| < 6.0 | < 3.78 | All dry |
| 6.0–6.2 | 3.78–3.98 | Water reaches lowest corner across Bay; gutters begin filling |
| 6.2–6.6 | 3.98–4.38 | Water in gutters at user's house, may push up from drain inlets |
| **6.6–6.8** | **4.38–4.58** | **Water tops curb at user's walkway; sidewalk wet; some road covered. ≈ user's empirical flood onset.** |
| 6.8–7.0 | 4.58–4.78 | Bay Ave road middle covered at user's spot (4.36) but intersection center (4.54) still dry |
| 7.0–7.3 | 4.78–5.08 | Intersection center begins covering; water reaches lawn step-up |
| 7.3–7.6 | 5.08–5.38 | Water on lawn / walkway; moderate flooding (Apr 18 = 7.32) |
| 7.6+ | 5.38+ | Severe flooding; substantial water on lawn (Oct 30 = 7.57) |
| 8.0+ | 5.78+ | Approaching bulkhead overtopping conditions |
| ~13.3 (Sandy peak) | ~11.1 | ~7 ft over Bay Ave per Borough's historical table |
| 13.82 (1% BFE) | ~11.6 | Bay Avenue catastrophically submerged |

---

## Borough's historic flood calibration (for context)

| Event | Sandy Hook peak (MLLW) | Depth on Bay Ave |
|---|---|---|
| Hurricane Sandy 2012 | 13.31 ft | ~7 ft |
| Hurricane Donna 1962 | 10.5 ft | ~4 ft |
| Nor'easter 1992 | 10.3 ft | ~4 ft |
| Hurricane Irene 2011 | 9.75 ft | ~3 ft |

These all involve significant bulkhead overtopping (Pathway A). The
events we've modeled (Oct 13, Oct 30, Dec 19, Apr 17, Apr 18) are all
in a much lower regime where Pathway B (drain back-flow) dominates.

---

## What's still missing

1. **Bay Avenue elevations not in Phase 1 PDF.** Phase 1 only covered
   Central, Beach, Ocean. Bay Ave itself is implicit from the
   Bay+Central corner readings, but a full Bay Ave longitudinal profile
   would be useful. May exist in a separate Borough engineering file or
   in CME Associates' "Ph 1 Sanitary Sewer Improvements" document
   dated 1/19/2022 (referenced on the H2M plans but not included).
2. **Storm drainage outfall locations.** We know inlet grate
   elevations; we don't know where the outfall pipes discharge into
   the bay or at what elevation. The Borough's Floodplain Administrator
   (Stephen Winters, swinters@highlandsnj.gov) should have a storm
   sewer map.
3. **House finished-floor elevation.** Forerunner doesn't show it.
   It might be on a 1971-era Elevation Certificate filed with FEMA
   when the FIRM was first issued, or with the Borough.
4. **Construction status of Phase 1.** Whether the road in front of
   342 Bay has been reconstructed to design elevations or is still
   at the slightly-lower existing elevations.
