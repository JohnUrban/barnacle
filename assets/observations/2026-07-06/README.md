# 2026-07-06 — Pluvial-only flash flood (first measured rain-driven event)

**The event class we've been waiting for since HANDOFF item 14**
("does heavy rain flood 342 Bay without any tidal contribution?").
Answer: **emphatically yes.** Massive convective rain flooded the
intersection to ~7.3″ at the curb roughly **two hours before high
tide**, while the bay itself was more than a foot below the lowest
grate the entire time.

User summary: *"It was crazy how fast the water appeared and rose in
this flood."* Water appeared before 10:55 AM; peak measured 11:34 AM;
mostly abated by ~12:45 PM. *"This flood was as high as the October
[30] flood I believe... Both made it to the porch steps though. And
both were from massive rain. The tide-only floods have been less
scary."*

## TL;DR

- **Pure pluvial, proven quantitatively**: measured water at 342 Bay
  ran **10–25″ above** what the bay could supply at every measurement.
  Sandy Hook never exceeded 3.14 NAVD88 (bay-equivalent) during the
  flood window — the lowest grate is at 3.52. Zero tidal contribution.
- **Peak: ≈ 4.77 NAVD88 at ~11:34 AM** (sidewalk anchor) → **7.3″ at
  curb**, "moderate" regime. Possibly slightly higher between
  measurements (11:34 → 11:41 gap). Water reached the bottom porch
  step and went **1–2″ up it** at peak.
- **Rise rate: +3.75″ in 34 minutes** (11:00 → 11:34). From first
  water to peak in well under an hour.
- **The model predicted "dry" — a complete false negative**, for two
  stacked reasons:
  1. **Input miss**: NWS QPF forecast 0.0″ rain for today
     (cumulative_rain_24h_in = 0.0 in the morning forecast.json).
     Convective cells are exactly what QPF misses.
  2. **Architectural gap**: the model only predicts at high-tide
     times. A rain flood at 11:34 AM (2 h before high tide) is
     literally unrepresentable in the current architecture.
- **NEW drainage-pattern observation** (user, 1:05–1:12 PM): rain
  floods have a **different spatial signature** than tide floods.
  Tide floods enter via SE/SW grates first (lowest openings,
  backflow). Rain floods concentrate late-stage activity at
  **NE/NW** — the NE grate was **jetting water upward** during
  drainage while the SW grate was *accepting* inflow and the SE
  grate sat inactive. See "Drainage asymmetry" below.
- **Landmark revision candidate**: two independent anchors at
  11:43–44 (NE grate → 4.654; sidewalk → 4.659) while the user
  observed water "approximately level with but just under the lawn
  step" → **lawn_step top is ≈ 4.67 ± 0.02 NAVD88, not the 4.58
  placeholder**. See below.

## Timeline with implied water elevation

Anchors: NE grate 3.80, sidewalk-under-lawn-step 4.33, fire-hydrant
road ≈ 3.85 (all NAVD88). "Bay water" = SH_obs − 2.82 = what the tide
alone could supply. High tide was 13:02 ET (astronomical 4.72; a
meaningful surge ~+1.2–1.4 ft was also running — still nowhere near
flood-relevant).

| Time | Source | Reading | Water at 342 | Bay water | Rain excess |
|---|---|---:|---:|---:|---:|
| 11:00 | sidewalk | +1.5″ | 4.455 | 2.35 | +25″ |
| 11:04 | fire hydrant | +7″ | 4.433 | 2.48 | +23″ |
| 11:05 | NE grate | +8″ | 4.467 | 2.51 | +23″ |
| 11:07 | NE grate | +8.75″ | 4.529 | 2.54 | +24″ |
| 11:11 | sidewalk | +2.75″ | 4.559 | 2.52 | +25″ |
| 11:14 | NE grate | +9.25″ | 4.571 | 2.52 | +25″ — intersection fully covered |
| 11:17 | sidewalk | +3.25″ | 4.601 | 2.54 | +25″ |
| 11:22 | sidewalk | +4.25″ | 4.684 | 2.64 | +25″ |
| **11:34** | **sidewalk** | **+5.25″** | **4.768 (peak)** | 2.77 | **+24″** |
| 11:41 | sidewalk | +4.25″ | 4.684 | 2.85 | +22″ — rain slowed dramatically |
| 11:43 | NE grate | +10.25″ | 4.654 | 2.88 | +21″ — "just under lawn step" |
| 11:44 | sidewalk | +3.9–4″ | 4.659 | 2.89 | +21″ |
| 11:50 | NE grate | +9″ | 4.550 | 2.92 | +20″ |
| ~11:54 | sidewalk | +2.25–2.5″ | 4.528 | 2.90 | +20″ |
| 12:00 | NE grate | +7″ | 4.383 | 2.99 | +17″ |
| 12:01 | sidewalk | +0.5–0.75″ | 4.382 | 3.00 | +17″ |
| 12:08 | NE grate | +6″ | 4.300 | 3.03 | +15″ — light rain |
| 12:43 | (visual) | — | light flooding still visible | — | — |
| 13:05 | NE grate | +2.5″ | 4.008 | 3.14 | +10″ — grate JETTING upward |
| 13:12 | NE grate | +3.1″ | 4.058 | 3.00 | +13″ |
| 13:18 | NE grate | +3.2″ | 4.067 | 3.10 | +12″ |

(The second "11:44" entry in the raw notes is sequential between
11:50 and 12:00; treated as ~11:54.)

Notes on the shape:
- **The flood abated while the tide was still rising.** At 11:41 the
  user noted the rain slowing and the flood abating — with 80 min of
  incoming tide and ~1 ft of tidal rise still to come. This is the
  signature of a working drainage network: bay level was low, so the
  drains had somewhere to send the water. The moment the rain input
  dropped below drainage capacity, the pool drained — tide be damned.
- **The 13:05–13:18 uptick** (4.008 → 4.067) tracks a brief rain
  re-intensification right at high tide — "round 2" that fizzled when
  the rain slowed again.

## Cross-anchor consistency + the lawn-step revision

At 11:43–11:44, two independent anchors agree to **0.005 ft**:
NE grate (+10.25″ → 4.654) and sidewalk (+3.95″ → 4.659). Even in a
pluvial event, water around the NE corner / walkway area was locally
level at that moment.

The user's simultaneous observation: water *"approximately level with
but just under the lawn step."* If 4.655 is just under the lawn-step
top, then **lawn_step ≈ 4.67–4.70 NAVD88** — not the 4.58 placeholder
(which HANDOFF 7.4 already flagged as unreliable: originally
tape-measured with slope concerns, inferred range 4.54–4.63).

Corroboration from the peak: at 4.768 (11:34), water reached the
bottom porch step and went 1–2″ up it, and (implicitly) was over the
lawn step. With lawn_step ≈ 4.67–4.70, peak water was ~1″ over it —
consistent with the user's description. With the old 4.58, peak water
would have been 2.3″ over, and the 11:43 observation ("just under")
would be flatly contradicted (4.654 > 4.58).

**Proposed revision (pending one more anchor): `lawn_step` 4.58 →
≈ 4.67.** Not applied to the model yet — one landmark revision per
event observed at the step edge; a tide-flood measurement at the
lawn step would confirm cleanly since tide floods are more reliably
level. Also implies the sidewalk-to-lawn-step riser is ~4″, not 3″.

### Porch-step base cross-fit (added same evening, user-confirmed method)

The model's `porch_step` (5.08) was never measured — the archives
show it was estimated as lawn_step + 6″ in v0.5.1. Today's data pins
the *base* of the bottom porch step for the first time:

- Peak water = 4.77 NAVD88 (dual-anchored)
- User: water went "1″ or so, 2″ at most" up the bottom porch step
  at peak
- → **bottom porch-step base = 4.60–4.68 NAVD88**

Combined with the lawn-step revision (~4.67): **the walkway rise
from lawn step to porch-step base is ≈ 0–1″, not the 1–2″ the user
had verbally estimated** — the porch-step base is essentially level
with the lawn-step top (or the peak crested slightly above 4.77
between the 11:34 and 11:41 readings, which would restore up to an
inch of gradient).

What the 5.08 `porch_step` landmark physically refers to (top of
first step? a higher step?) still needs pinning — user has offered
to tape the riser heights (each porch step, bottom → deck), which
would rebuild the full vertical ladder from the 4.33 sidewalk anchor.
Oct 30's "water at first porch step" memory + its ≥5.19 peak
reconstruction suggests 5.08 does correspond to a real feature about
6″ above the step base — plausibly the top of the first step.

### Refinement via photo-timeline interpolation (added later same evening)

User caution: 11:34 may not be THE peak (11:41 was already falling,
so the crest is somewhere in 11:34–11:41). Photo review added two
timeline anchors:

- **11:21**: NO water at the porch-step base; water in the photo is
  approximately LEVEL with the lawn step
- **11:26**: a good 0.5″ of water at the porch-step base

Rise rate from the sidewalk measurements (11:22 → 11:34: 4.25″ →
5.25″) = 0.083 in/min. Interpolating:

- Water at 11:21 ≈ 4.677; at 11:26 ≈ 4.712

**Ordering constraint (user, watching in real time)**: the porch-step
base is *definitely* higher than the lawn-step top — water visibly
"climbs" the walkway toward the porch after topping the lawn step; it
does not spill straight across. Any fit must satisfy
porch_base > lawn_top. Constrained solution:

- **Porch-step base ≈ 4.68 NAVD88** (dry at 11:21 water 4.677 →
  base ≥ 4.68; holding "a good ½″" at 11:26 water 4.712 → base
  ≈ 4.67–4.68)
- **Lawn-step top ≈ 4.66–4.67** (the 11:43 "level with but just
  under" note at water 4.654 puts the top just above that; the
  11:21 "approximately level" frame at 4.677 reads as water already
  a hair past the top, starting its walkway advance)
- **Walkway rise lawn step → porch base ≈ ¼″ (band 0.1–0.5″)** —
  small but strictly positive; over the walkway's length this
  produces exactly the visible slow "climb" the user watched. The
  original 1–2″ verbal estimate revises down to ~¼″.
- Peak bound: at 4.77–4.84 the porch base (4.68) held 1.1–1.9″ —
  inside the user's "1 inch or so, 2″ at most."
  **Peak ∈ [4.77, 4.84], most likely 4.78–4.80.**

## Drainage asymmetry — tide floods vs. rain floods (NEW)

User observations at 1:05–1:12 PM (post-flood, during drain-down,
right at high tide):

- **NE grate: water actively JETTING upward** — visibly pressurized
  outflow. Still jetting at 1:12 even in very light rain.
- **SW grate: accepting inflow** — water flowing down into it.
- **SE grate: inactive** — only residual pocket water nearby.
- **North side of Bay Ave (user's side): taking on water. South side:
  draining.**

User's hypothesis (recorded verbatim): *"Since my side is closer to
where the water would be draining to, this seems like it might be a
function of how the water is draining. Clearing out farther away and
still jetting up as it gets closer to its outlet. The water jetting
up from the NE grate might be receiving its energy from water
draining down towards it from the southern side and beyond."*

Contrast with tide floods: **SE/SW grates are the entry points and
focal areas** (lowest grate openings — 3.52/3.60 — so bay backflow
surfaces there first, and those areas stay wettest).

Implication for the drain-network picture: the NE grate appears to
sit on (or near) the **main trunk line toward the outfall**. Under
backflow (tide) the lowest openings vent first regardless of
topology; under forward drainage (rain) the trunk-line grates see
converging flow and pressurize. This is a structural fact about the
network we didn't have before, and it predicts **rain floods will
persist longest / re-emerge first around NE/NW**, while tide floods
do so around SE/SW.

## Model implications (the v0.9 agenda)

1. **Pluvial pathway is real and unmodeled.** Today's flood is
   unrepresentable in the current architecture (predictions exist
   only at high-tide timestamps). A rain-driven prediction pathway
   needs sub-daily timing, driven by rain-rate forecasts.
2. **A unifying frame: drainage capacity as a function of bay level.**
   Today: bay low → drains worked → flood tracked rain input and
   abated within ~30 min of the rain slowing, even against a rising
   tide. Oct 30 2025: bay high (SH 7.63) → drains blocked → the same
   class of rain had nowhere to go and stacked on top of the tide.
   The existing tide+rain term and today's pure-rain flood may both
   be limits of one model: water_in(rain) vs water_out(drainage
   capacity(bay level)).
3. **QPF is not a sufficient rain input for convective events.** NWS
   forecast 0.0″ for today. Radar-based nowcasts (MRMS) or the
   NJDEP/Rutgers mesonet (RABCH022 "Highlands", hourly) are candidate
   inputs for a pluvial warning. Even a "QPF says dry but radar shows
   a cell inbound" banner would have beaten today's forecast.
4. **The widget tide-curve now has a purpose beyond tides**: when a
   time-resolved rain term exists, today's event would appear as a
   sharp spike riding the low-tide portion of the curve.

## Comparison to Oct 30 2025 (user's felt-equivalence)

User: *"This flood was as high as the October flood I believe. I
wouldn't be able to say which was higher. Both made it to the porch
steps."*

By the street-pool numbers: today ≈ 4.77 NAVD88 vs Oct 30
reconstruction ≥ 5.19–5.27. Oct 30 was probably ~5″ higher at the
street. But the felt-equivalence makes sense: both events put water
at the bottom porch steps (the walkway-porch area also collects
local runoff sheet flow in heavy rain, which pools independent of
the street level), both were rain-driven, and both rose fast. The
big difference: Oct 30 had SH 7.63 under it; today had SH ~5.6. Same
rain class on top of a high tide = Oct 30. **If today's cell had
landed at a 7+ ft tide, we plausibly get another Oct 30.**

## Measurements

Raw notes: `flood-measurements.txt` (verbatim, timestamped).
Measurements were deliberately limited mainly to the NE grate and
the sidewalk-under-lawn-step wall (user's protocol evolution: fewer
points, faster cadence, during-event coverage — 20 data points
across 2h18m vs. previous events' 4-grate sweeps).

## Photos (documentary)

13 subfolders named by vantage; per current protocol, photos document
spatial extent rather than tape readings. Notable: the NE-grate
jetting photos (~1:05 PM), referenced by the drainage-asymmetry
observations above.

## Cross-references

- HANDOFF item 14 (pluvial-only question) — answered by this event
- `assets/observations/2025-10-30/README.md` — the compound (tide +
  rain) sibling event
- `model/v0.8.md` — current model; does not cover this event class
- HANDOFF 9d.3 — antecedent moisture / accumulation questions, now
  joined by the pluvial pathway

## Measured rainfall (MRMS radar, added 2026-07-07)

Pulled from the Iowa State mtarchive with
`history/scripts/mrms_point_rain.py` (PrecipRate 2-min instantaneous
+ MultiSensor_QPE_01H_Pass2 gauge-corrected hourly, at the house
point and a ~1.5 km hillside box).

| ET | point (in/hr) | hill-box max |
|---|---:|---:|
| 10:40 | 0.34 | 0.94 |
| 10:44 | 0.99 | 1.71 |
| 10:52 | 1.32 | 1.91 |
| 11:04 | 1.61 | 1.86 |
| 11:08 | 1.43 | 2.48 |
| **11:12** | **2.95** | 2.95 |
| 11:16 | 2.37 | **3.06** |
| 11:20 | 2.07 | 2.43 |
| 11:28 | 0.78 | 1.55 |
| 11:36 | 0.23 | 0.41 |

Hourly QPE at the point: 0.08″ (hr ending 10:00), 0.51″ (11:00),
**0.94″ (12:00)**, 0.06″ (13:00) → storm total **1.60″**.

Findings:
- **Peak rate 2.95 in/hr at 11:12 ET** — top of the regional 1.5–3
  band; the flood-producing core DID sit on the hillside, not just
  south of us. ~2 in/hr sustained 11:04–11:20.
- **~20-min catchment lag**: measured water peak 11:34 vs rain peak
  11:12 — the hillside concentration time, directly observed.
- **Catchment amplification ≥ ~13×** (lower bound): filling the
  street bowl to +15.4″ takes ≈5.9″ of rain-equivalent over the
  peak wetted footprint (stage-storage curve), but only ≈0.45″ fell
  during the 39-min rise. The bluffs supplied the rest.
- Water appeared (~10:55) after ~0.5″ had accumulated with rates
  crossing ~1 in/hr — a first empirical onset threshold.
