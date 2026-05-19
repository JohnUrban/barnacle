# 2026-05-18 spot-check session — comprehensive notes

The first real spot-check after the feature went live (commit ebdd144).
A modest tidal event that turned out to be far richer than expected and
surfaced significant findings about the model. This README captures
everything the user observed verbally plus the inferences Claude drew
from those observations. Photos accompanying the observations live in
the subdirectories listed below.

---

## TL;DR

- **Forecast peak: 6.19 ft MLLW at 21:58.** Confidence was **LOW** all
  day because of 0.87 ft surge swing in the prior 6 h.
- **Actual peak: 6.58 ft MLLW at 22:12** (per NOAA Sandy Hook 6-min
  data). Forecast undershot by 0.39 ft AND missed peak time by ~14 min.
  The LOW confidence flag was correct to fire.
- **The model overshot at the property side** even at the higher
  actual peak. At SH 6.58 the v0.6 model predicts water at the curb
  (4.16 NAVD88) and 3.0" above the corner grate at the user's corner
  (3.91 NAVD88). The user observed water 1-1.5" *below* the corner
  grate at peak, and the curb never got wet.
- **Effective local enhancement at SH 6.58 tonight was ~0, not +0.40.**
  Big finding. One event isn't enough to recalibrate, but if it
  repeats, the enhancement is probably not a constant — it's more
  likely the saturated value that develops only when SH is well above
  the Pathway B activation threshold (6.33) and the drains have had
  time to equilibrate.
- **Five grates need to be in the model**, not the two we currently
  track. Naming convention proposed below.
- **A previously-unmapped grate on Bay Ave upstream of the user's
  walkway is the actual primary feeder** to the gutter at walkway —
  not the corner grate at Bay+Central as the model currently implies.

---

## The 5 grates around 342 Bay Ave

Compass-direction naming relative to the Bay+Central intersection
(user's house at the **NE** corner — north of Bay Ave, east of
Central Ave):

| Proposed name | Old / current name | Approx elev (NAVD88) | Status tonight |
|---|---|---:|---|
| `grate_NE` | `corner_grate` (v0.6) | 3.91 | Water 1–1.5" *below* top at peak — never overflowed |
| `grate_NW` | (not in model) | unknown | Same side of Bay as NE, across Central. Never overflowed; water also 1–1.5" below top at peak. Probably similar elevation to NE. |
| `grate_SE` | `lowest_sentinel_grate` (v0.6) | 3.60 | "Proximal" across Bay — closer to user's corner. Overflowed; ~1" above at observed peak. **Water spread more widely from SE than SW** — likely a flatter / larger surrounding pavement pocket. |
| `grate_SW` | (not in model) | likely ~3.55-3.58 | "Distal" across Bay — diagonally opposite NE. Overflowed earlier and *deeper directly above the grate* than SE: when SE had ~1" above, SW had ~1.5" above. **SW is ~0.5" lower than SE.** |
| `grate_bay_ave_upstream` | (not in model) | inferred ~3.78 | On Bay Ave east of NE corner, upstream of the user's walkway. Water emerged ~1 cm above grate at peak. **This is the actual primary feeder to the gutter at the walkway**, not the NE corner grate. |

### Observed kinetics across grates

Inferred from the user's running commentary, ordered by which grate
wets first:

1. **`grate_SE` and `grate_SW`** (across Bay) wet first as bay rises.
   At 21:45, water was already 1-2 cm shy of flush at SE. **SW was
   likely overflowing at the same time or earlier** — the user was
   hyperfocused on SE (the previously-mapped "lowest sentinel") and
   didn't measure SW initially, but photos 3 and 4 show clear water
   already at SW while SE was just starting to spread. SE spreads
   widely (less depth above grate); SW concentrates deeper directly
   above the grate (suggests it's the lower of the two, by ~0.5").
2. **`grate_bay_ave_upstream`** wets next — water emerges and begins
   flowing along the curb downhill toward the user's walkway gutter,
   forming a thin "worm-like stream."
3. **The gutter at walkway (3.78 NAVD88, `gutter_walkway`)** wets
   from this upstream feeder.
4. **`grate_NE`** (user's corner) and **`grate_NW`** (across Central
   on same side of Bay) wet *last* — and **didn't fully overflow
   tonight.** Water reached 1-1.5" below their tops at peak.

In other words: **water reaches 342 Bay's gutter from the upstream
side first, not from the corner grate.** The v0.6 model's framing
of `corner_grate` as the Pathway B onset point is partially right
(it's the onset for the *corner*) but misleading for the property —
the *property gutter* wets earlier, from the upstream Bay Ave grate.

---

## Tonight's observation timeline

Approximate timestamps from user's running commentary; refined by
EXIF timestamps once photos are in.

| Time | Observation | Inferred NAVD88 | Implied SH |
|---:|---|---:|---:|
| ~21:45 | SE grate: water 1-2 cm shy of top | 3.53–3.57 | SH ≈ 5.95-5.99 if +0.40 holds; **SH ≈ 6.35-6.39 if enhancement is 0** |
| ~22:06 | SE grate: ≥1" above top; NE grate: 2-2.5" below top | 3.68 (SE side); 3.71-3.74 (NE side) | NOAA SH ≈ 6.56 |
| ~22:12 | (NOAA actual peak) | — | **6.58 ft MLLW** |
| ~22:15 | SE grate: deeper than 22:06 reading; NE grate: 1-1.5" below top; SW grate: ~1.5" above top; upstream grate: ~1 cm above | NE ≈ 3.79-3.83; SW ≈ 3.72-3.85; upstream ≈ 3.78 | NOAA SH ≈ 6.55 |
| ~22:20 | Water plateau / starting to recede | — | ~6.50 |
| ~22:30 | Receding clearly | — | 6.48 (NOAA) |

(See `model_vs_observed.md` if we make one later — for now this table
is the canonical record.)

---

## Key inferences and model-implications

### 1. Local enhancement at this magnitude is much smaller than +0.40

The starkest finding. At the NOAA observed peak (SH 6.58), v0.6
predicts water at the property of 4.16 NAVD88 (= curb top), but the
user observed water 1-1.5" below the corner grate (3.91 NAVD88) — so
water at the property was ~3.79-3.83 NAVD88, not 4.16. **Effective
local enhancement at this event was about +0.06 to +0.10 ft at peak,
0 to +0.04 ft on the rising tide, not +0.40 ft.** Across the event
the enhancement was always small and positive — never close to the
+0.40 the model assumes.

Possible explanations (need more events to discriminate):

- **Magnitude-dependent enhancement.** The +0.40 was calibrated from
  4 events that all reached the curb (SH ≥ 6.76 effective). At those
  magnitudes Pathway B was saturated. At SH 6.58 — only 0.25 ft above
  the 6.33 Pathway B threshold — Pathway B may have only been
  *partially* engaged, so enhancement was smaller.
- **Timing / equilibration.** Tonight's peak lasted ~10-15 minutes
  near the top. Pathway B may need longer to "fill the system" before
  water at the property fully matches bay water. Sustained-peak
  events (multi-hour storms) might show the full +0.40.
- **Spatial / surge type.** Wind direction, pressure, or storm shape
  could affect how surge propagates from Sandy Hook to the user's
  property. Tonight's surge re-organized between morning and evening
  (the 0.87 ft swing the LOW confidence flag warned about); maybe
  that produces a different bay-to-property profile.

**Action**: Log this event in `data/labeled_observations.csv` once
the photo timestamps are in. Don't change the model yet. Watch for
the pattern in subsequent sub-curb events.

### 2. Five grates, not two

The current v0.6 model has two grates: `corner_grate` (NE in the
new naming) and `lowest_sentinel_grate` (SE). Tonight surfaced
three more: NW, SW, and `grate_bay_ave_upstream`. The upstream
one is the most consequential for the model since it's the actual
first feeder to the property's gutter.

**Action for v0.7**: Add NW, SW, and upstream as proper landmarks
once their elevations are confirmed. Probably rename the existing
two as well to make the compass scheme consistent. See the table
above for proposed names + elevations.

### 3. The lowest *visible* point isn't always a grate

The pavement around `grate_SE` dips 1-1.5" below the grate top —
making a pocket where water pools (~3.48-3.52 NAVD88 at the
deepest). **But the pocket is downstream of the grate, not upstream**:
water can only reach the pocket *after* it has overflowed the grate.
So the pocket is a **post-overflow retention indicator**, not a
sub-3.60 sentinel for water arrival.

**Action**: Don't add the pocket as a landmark for tidal arrival.
*Do* use the pocket's pavement elevation for the future heat-map
work — it'll affect the visualized depth in that area after water
recedes.

### 4. Peak time can slip ~15 min later than forecast

Forecast peak: 21:58 (astronomical). Actual peak: 22:12 (NOAA 6-min
data). Surge can push observed peak past astronomical peak by 10-30
min. Currently the forecast script reports the astronomical peak
time as "peak time" — accurate for the predicted-astronomical part
but not necessarily for when water-at-property peaks.

**Action**: Note in HANDOFF as a minor refinement. Could be added
to v0.7's confidence indicator (e.g., "peak time may slip 10-30 min
later when surge persistence is uncertain").

### 5. Forecast undershot the peak magnitude

Forecast peak 6.19 ft, actual 6.58 ft — undershot by 0.39 ft. The
0.87 ft surge swing in the prior 6 hours, which fired the LOW
confidence flag, was exactly the kind of unstable surge regime
where persistence breaks down. The flag was correct.

**Action**: No model change. The confidence indicator did its job —
the user knew not to trust the headline number tonight. Tomorrow
will tell us whether the NWS Coastal Flood product was active
(if so we should have used it instead) or if surge persistence
is the only option for these mid-magnitude events.

---

## Photo directory layout

After the directory renames in this commit, the subdirectory layout
maps cleanly to the 5 grates + key landmarks:

```
assets/observations/2026-05-18/
├── README.md                          ← this file
├── grate-NE-user-corner/              ← v0.6 corner_grate (3.91)
├── grate-NW-across-central/           ← NEW (not in v0.6)
├── grate-SE-proximal/                 ← v0.6 lowest_sentinel_grate (3.60)
├── grate-SW-distal/                   ← NEW (likely < 3.60)
├── grate-bay-ave-upstream/            ← NEW, inferred ~3.78
├── gutter-at-walkway/                 ← v0.6 gutter_walkway (3.78)
└── pocket-SE-retention/               ← pavement-low pocket near SE grate
```

Drop iPhone JPGs into the matching subdirectory. EXIF timestamps
carry the time so filenames can be anything.

---

## Followup actions

When photos are in:

1. **Walk through each photo**, log EXIF timestamp + visible water level
2. **Pull NOAA 6-min water_level** for each photo's timestamp window
3. **Append rows to `data/labeled_observations.csv`** — one per
   observation point — with both the observed and the NOAA SH reading,
   so the local-enhancement gap is captured for each
4. **Compute "effective enhancement at this event"** across all the
   observations — does it correlate with SH magnitude, time-since-
   rising, or some other variable?
5. **Decide whether to call the SW grate's elevation a refinement of
   3.60** (e.g., 3.55) or leave it as a separate landmark — depends
   on whether they're at clearly different elevations (photos will
   help)

Next session, queued for the user to decide on:

- **v0.7 model spec promotion** adding the 3 new grates + renaming.
- **Refine the local enhancement** — start with a magnitude-dependent
  scaling and revisit after a few more sub-curb events.
- **Annotate `map_points.csv`** with the 4 intersection grates (compass
  names) + upstream grate. Need user to click them in `pick_coords.py`.

---

## Naming convention summary (for v0.7)

Adopted by Claude in this README, pending user confirmation:

- `grate_NE` — northeast corner of Bay+Central (user's corner)
- `grate_NW` — northwest corner (across Central, same Bay side)
- `grate_SE` — southeast corner (across Bay, proximal to user's corner)
- `grate_SW` — southwest corner (across Bay, diagonal/distal)
- `grate_bay_ave_upstream` — east of NE corner on Bay Ave, before
  user's walkway

The compass refers to the position around the Bay+Central
intersection. North = inland side; South = bay side.

If the user prefers a different scheme (e.g., "user_corner",
"sibling", "proximal", "distal"), we'll adjust before v0.7 lands.
The compass names have the advantage of being self-documenting if
someone else picks this up — no project-specific lookup needed.
