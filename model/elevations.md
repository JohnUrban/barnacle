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
| Lawn / walkway step-up | 4.66 | 7.48 | Field cross-fit / tape observations |
| Bottom of porch steps | 4.68 | 7.50 | Field re-anchoring, v0.9 |
| Top of first porch step | 5.41 | 8.23 | Measured porch ladder, v0.9 |
| Porch deck | 8.08 | 10.90 | Measured porch ladder, v0.9 |

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

The production tide pathway uses no constant local enhancement:
`water_at_342_NAVD88 = Sandy_Hook_obs_MLLW − 2.82`. The retired
v0.6 `+0.40 ft` term was over-fit to memory-based observations and was
rejected by repeated tape measurements. A separate −0.13 ft expected-actual
adjustment is reported for offshore winds; it does not change this conservative
threshold table.

| Sandy Hook obs (MLLW) | Water at 342 Bay (NAVD88) | What gets wet |
|---|---|---|
| < 6.34 | < 3.52 | No connected tidal flooding visible |
| 6.34 | 3.52 | SW distal grate emerges — first-water sentinel |
| 6.42 | 3.60 | SE proximal grate emerges |
| 6.46 | 3.64 | SE/SW pavement corners wet; upstream Bay Ave grate emerges |
| 6.60 | 3.78 | Gutter line at user's walkway begins filling |
| 6.62 | 3.80 | NE and NW corner grates emerge |
| 6.73 | 3.91 | NE/NW pavement corners reached |
| **6.98** | **4.16** | **Water tops curb at walkway — flood onset at 342 Bay** |
| 7.15 | 4.33 | Sidewalk under the walkway lawn-step face reached |
| 7.18 | 4.36 | Middle of Bay Ave at user's spot covered |
| 7.36 | 4.54 | Intersection center submerged (local high point) |
| 7.48 | 4.66 | Water reaches lawn / walkway step |
| 7.50 | 4.68 | Water reaches bottom of porch steps |
| **8.23** | **5.41** | **Water reaches top of first porch step** |
| 10.90 | 8.08 | Water reaches porch deck |
| 13.0 | 10.18 | Hurricane Sandy-class catastrophic flooding |
| 13.82 (1% BFE) | 11.00 | Water reaches the FEMA base-flood elevation |

(Earlier versions of this table used the retired +0.40 enhancement and a
fictitious 5.08-ft porch-step estimate. Reconciled with the measured v0.10.1
landmark ladder on 2026-07-21.)

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
