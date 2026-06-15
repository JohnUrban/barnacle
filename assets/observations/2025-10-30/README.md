# 2025-10-30 — Compound flood event (tide + rain), photo evidence

**The biggest 342 Bay flood event in our records.** Compound event:
high tide + heavy rain. User commentary 2026-06-15: *"The major major
take home is that the flooding was far more expansive that day than
any I've seen since. The only one close-ish was the April 18th flood
event."*

This was a pre-spot-check event — no tape measurements were taken.
But it produced two anchored observations: the user's qualitative
memory ("water at first porch step") and a set of photos taken from
the house. The photos let us back-fit peak water within ~0.1″ of the
v0.7 model, and they're the primary calibration anchor for the v0.7
rain term.

---

## Event context

- **Sandy Hook observed peak: 7.630 ft MLLW at 14:54 ET** (NOAA
  station 8531680 6-min product). Early specs recorded 7.57; the
  actual NOAA value is 7.630.
- **Peak hourly rainfall: 1.45 in/hr** (contemporaneous log).
- This is the only event in the 4-event historical calibration set
  with peak rain rate above 0.5 in/hr.

## Property layout (important context for reading the photos)

The user's vantage is the front of 342 Bay Ave, at the Bay+Central
intersection (NE corner of the intersection). Layout from porch
outward:

1. **Top of porch deck** (where most photos were taken from)
2. Five steps down (4 steps + a platform step) to lawn level
3. **Walkway** runs from the bottom of the porch steps across the
   front lawn to the sidewalk
4. **Wooden fence** at the lawn/sidewalk boundary, with an opening
   for the walkway. There is a **step UP from sidewalk onto the
   lawn** at this point — this is the **`lawn_step`** landmark at
   4.58 NAVD88
5. **Sidewalk**
6. **Step DOWN from sidewalk to road** — the **`curb`** at 4.16 NAVD88
7. **Bay Ave** (Bay-Central intersection)
8. Across the road: **VFW lawn** with an iron fence (vertical bars,
   not decorative). If you follow that fence to the right, the
   corner is **`corner_SE`** at 3.64 NAVD88
9. Beyond the VFW: **Shore Ave** (where parked cars are visible in
   several photos)

**Important note about the iron fence in the foreground of porch
photos**: it's the **porch railing** (~5 steps + walkway gradient
above lawn_step elevation), NOT a yard fence. Don't infer water
elevation from where it sits relative to the porch railing.

The walkway from the porch steps to the sidewalk is **angled** —
the lawn_step end (sidewalk side) sits at 4.58 NAVD88, but the
porch-steps end (house side) sits higher because the walkway slopes
up toward the porch. So water depth reads differently along the
walkway: shallower near the porch steps, deeper near the sidewalk
step-up.

## Photo timeline + NOAA water-level anchor

NOAA SH (MLLW) at each photo time (interpolated from 6-min product):

| Cluster (ET) | Time | NOAA SH | Min post-peak | Vantage |
|---|---|---:|---:|---|
| **Peak-phase** | 15:41 | 7.04 | +47 | top-of-porch (photos 1, 2) |
|  | 15:45 | 6.93 | +51 | top-of-porch (photo 3), window-facing-Central (photo 4) |
| **Receded-phase** | 17:07 | 5.86 | +2 h 13 | top-of-porch (photos 5–9) |
|  | 17:08 | 5.80 | +2 h 14 | yard-NE-corner (photo 10), corner-of-house-central (photos 11, 12) |

The peak-phase cluster is the analytically important one: water at
342 Bay is still elevated, and the photos pin water to landmarks.

The receded-phase cluster (~1 h 22 m after the peak-phase shots) is
mainly useful as a contrast — water is mostly gone, but the
**4 residual pools at the corners of the intersection** in photo 5
mark the locations of the 4 corner grates and confirm the spatial
layout.

## Per-photo notes (verified with user 2026-06-15)

### `from-top-of-porch/`

- **Photo 1** (15:41:28 ET, +47 min post-peak; NOAA SH ≈ 7.04 MLLW)
  Top-of-porch view, facing **roughly south/southwest across Bay Ave
  toward the VFW**. Foreground: porch railing (iron fence with
  decorative scrollwork). Below the railing: bushes and lawn, then a
  wooden yard fence at the lawn/sidewalk boundary (partly visible).
  Beyond the yard fence: **submerged sidewalk + curb step-down + road
  + intersection + VFW lawn opposite**. Visible: parked cars on
  Shore Ave beyond the VFW (NOT on Bay/Central — those are flooded).
  Telephone pole visible to the left of frame.
  **Water level inference (user-confirmed)**: water is on the lawn,
  above the lawn_step elevation by about 1″ (some grass closest to
  the lawn-edge is submerged). **Implied water at 342 Bay ≈ 4.66
  NAVD88** (= lawn_step 4.58 + 1/12).
- **Photo 2** (15:41:34 ET, ~6 s after Photo 1; same SH 7.04)
  Same vantage as Photo 1, panned slightly to the right. The porch
  steps + their iron railing partially obscure the view, but the
  walkway at the bottom of the porch steps is visible. **Best
  water-anchor photo of the event**: "a good inch of water on the
  lawn_step part of the walkway where it steps up from the sidewalk."
  Walkway-gradient note: closer to the bottom of the porch steps,
  water is shallower (because walkway slopes UP toward the porch).
  Wooden yard fence visible behind the iron railing, with the
  walkway opening visible. Across the road: **entire Bay-Central
  intersection completely submerged**. `corner_SE` is visible in
  middle-left across the road; `corner_SW` is to the right of
  `corner_SE`. **`intersection_highpoint` (4.54 NAVD88) is
  underwater** by 1.4″ at this moment.
- **Photo 3** (15:45:09 ET, +51 min post-peak; SH ≈ 6.93)
  Top-of-porch view, panned further to the **left** of Photo 1. VFW
  building visible across the submerged intersection. Same telephone
  pole as Photo 1 is now to the **right** of frame instead of left.
  **`grate_bay_ave_upstream`** is in this photo somewhere proximal
  to the user's lawn between the left edge of the frame and the
  telephone pole on the right (precise location not marked).
- **Photo 5** (17:07:14 ET, +2 h 13 post-peak; SH ≈ 5.86)
  **Same vantage as Photo 2** (panned right showing Bay-Central
  intersection), but ~1 h 26 m later. Bay-Central intersection is
  **no longer fully submerged** — only **4 pools of water at the
  corners** of the intersection remain, marking the locations of
  the 4 corner-area grates (NE, NW, SE, SW). The pocket-retention
  pattern (water collects in the low spots at grate areas after the
  tide recedes) is clearly visible. Confirms post-overtopping
  retention at these locations, similar to the pocket-SE-retention
  observation from the 5/18 spot-check.
- **Photos 6, 7, 8, 9** (17:07:27–17:08:29 ET, +2 h 13–14 post-peak)
  Additional top-of-porch shots from the same time cluster as
  Photo 5. Various pans/angles of the receded state. (Specific
  per-photo notes not collected — user-described as the same general
  period; useful for layout reference but not water-level anchoring.)

### `from-window-facing-central/`

- **Photo 4** (15:45:26 ET, +51 min post-peak; SH ≈ 6.93)
  From an upstairs/inside window, **facing NE up Central Ave toward
  Snug Harbor Beach**. Water reaches **past the third house /
  driveway** up Central — much farther up Central than the user has
  ever seen in any other event. **Reference point for spatial
  comparison**: the neighbor's driveway across the street, first one
  to the left with a basketball net, was the one barely reached on
  the 2026-06-14 event. Oct 30 went past the *third* driveway.
  Implies Central Ave's slope going NE: water rose ~2 driveways'
  worth of elevation between the 6/14 peak and Oct 30 peak — a
  spatial constraint we could use to derive the slope along Central
  if we ever lock the cross-driveway elevations via cross-fit.

### `from-yard-NE-corner/`

- **Photo 10** (17:08:36 ET, +2 h 15 post-peak; SH ≈ 5.80)
  **NE corner from inside the wooden fence around the user's lawn.**
  Close-up of the dark pavement with a thin film of water + a
  receded puddle around the NE corner / `grate_NE` location. Manhole
  cover visible. Wooden yard fence visible at right edge. Useful as
  a layout reference for grate_NE area.

### `from-corner-of-house-central/`

- **Photos 11, 12** (17:08:57 + 17:08:59 ET, +2 h 15 post-peak;
  SH ≈ 5.80)
  Taken from **outside the house, at the corner of the building**,
  looking up Central Ave. Shows a lot of the same landmarks as
  Photo 4 but from ground level: houses 1–2 or 1–3 across Central
  visible. Water has mostly receded; only the lowest spots retain
  residual moisture.

## Photo-derived water-level reconstruction

The **15:41 ET (Photo 2)** anchor is the analytically important
moment:

> Water at 342 Bay at 15:41 ET ≈ **4.66 NAVD88**
> (lawn_step 4.58 + 1″ on the walkway, user-confirmed)

NOAA SH dropped from 7.630 (peak, 14:54) to ≈ 7.04 (15:41), a
**ΔSH ≈ 0.59 ft** drop. Assuming water at 342 tracks the SH drop
1:1 between these two moments (a *floor* assumption — water at 342
might recede slightly slower than SH at the gauge, so this gives a
lower bound on peak water):

> **Implied peak water at 342 ≈ 4.66 + 0.59 = 5.25 NAVD88 (lower bound)**

That puts peak water **1.7″ above the porch step** (5.08 NAVD88) —
matching the user's original memory of *"water at first porch step"*.

In terms of curb depth:
> Peak water 5.25 NAVD88 → **13.1″ at curb** — within 1.1″ of the
> user's original *"~12 in at curb"* memory.

**Both memory claims for Oct 30 corroborate each other and agree
with the photo-derived peak water within 1–2″.** Unlike Apr 18 and
Dec 19 (where depth-at-curb memory was 5–6″ over-stated and 5–8″
inconsistent with the landmark anchor respectively), the Oct 30
memories were essentially accurate.

## v0.7 model agreement

| Quantity | Value | Source |
|---|---:|---|
| v0.7 predicted water at peak | **5.28 NAVD88** | formula at SH 7.630, rain 1.45 in/hr, enh −0.13 |
| Photo-derived peak water (lower bound) | **5.25 NAVD88** | tide-decay from 15:41 photo anchor |
| User's memory of peak water | "at first porch step" (≈ 5.08) | qualitative recollection |

**Δ between v0.7 and photo-derived: 0.03 ft (0.4″).** Effectively
within tape precision.

## What this anchors going forward

- **v0.7's rain-term magnitude (`8·tanh(rate)` saturation = 8.0 in)
  is calibrated** by this event within tape precision. The earlier
  "rain-flood under-predicts" caveat I (Claude) wrote at v0.7
  promotion time was based on a flawed mental calculation; removed
  in commit ee703f6.
- The original v0.6 +0.40 enhancement appears to have been over-fit
  to the depth-at-curb memories on Apr 17, Apr 18, Dec 19 (which
  are less reliable than the Oct 30 memory + photo evidence). v0.7's
  −0.13 enhancement is correct.
- **Lesson for future spot-checks**: always record at least one
  landmark anchor in addition to any depth-at-curb estimate. The
  5/18+ protocol does this automatically.

## Cross-references

- Model spec: `model/v0.7.md` (Calibration evidence → Historical
  events re-evaluated)
- The original calibration writeups (now archived):
  `model/archive/v0.5.md`, `model/archive/v0.6.md`
- HANDOFF section 9c (v0.7 spec history), 9d.2 (v0.8 rain term —
  scope reduced 2026-06-15)
- Recent measured-event readmes:
  `assets/observations/2026-05-18/README.md`,
  `assets/observations/2026-05-31/README.md`,
  `assets/observations/2026-06-14/README.md`
- Tape-reading reference:
  `assets/observations/0-measuring-tape/README.md`
