# Draft observations for review

**Status:** First-pass interpretations by Claude based on photos + photo_log.md.
User: please review, correct, then we'll append to `data/labeled_observations.csv`.

Conventions:
- **Observed depth** = positive when water is *above* the landmark; negative when *below*.
- **Model depth (+0.40)** = what v0.6 predicts at the NOAA-observed SH at that time, assuming the +0.40 enhancement.
- **Model depth (0)** = what the model would predict if enhancement was 0 (no Pathway B contribution).
- "Effective enhancement" column at the right = the local enhancement implied by working backward from the observation.

## NOAA Sandy Hook (6-min, observed)

| Time (lst_ldt) | SH ft MLLW | Notes |
|---|---:|---|
| 21:54 | 6.57 | Rising |
| 22:00 | 6.56 | Plateau begins |
| 22:06 | 6.56 | |
| 22:12 | **6.58** | **NOAA peak** |
| 22:18 | 6.55 | Just past peak |
| 22:24 | 6.51 | Receding |
| 22:30 | 6.48 | Receding |

## Per-photo observations

| Photo | Time | Landmark | Observed depth | NOAA SH | Model (+0.40) | Model (0) | Implied enhancement | Notes |
|---:|---|---|---|---:|---|---|---:|---|
| 1 | 21:56:26 | SE proximal (3.60) | ~0″ (just above slots / wet around) | 6.57 | +6.6″ | +1.8″ | ~0 ft | First shot. Wet "splat" forming. |
| 2 | 21:57:15 | SE proximal | +0″ to +0.5″ (water in slots, modest overflow) | 6.57 | +6.6″ | +1.8″ | ~0 ft | Pavement around grate wet, no big puddle yet |
| 2 | 21:57:15 | SW distal (≤3.60) | small wet patch across road | 6.57 | n/a | n/a | n/a | SW becoming visible — just a small dark area |
| 3 | 21:58:23 | SE proximal | +0.5″ (clearer wet zone around grate) | 6.56 | +6.5″ | +1.7″ | ~0 ft | |
| 3 | 21:58:23 | SW distal (≤3.60) | wet patch growing | 6.56 | n/a | n/a | n/a | Visibly more water at SW |
| 4 | 22:00:53 | SE proximal | +0.5–1″ wet around grate | 6.56 | +6.5″ | +1.7″ | ~0 ft | |
| 4 | 22:00:53 | SW distal | clear wet patch between crosswalk lines | 6.56 | n/a | n/a | n/a | Substantially more water than photo 3 |
| 5 | 22:02:19 | SW distal | ~+1″ (water in slots, splat around) | 6.56 | +6.5″ | +1.7″ | ~0 ft | First good close-up of SW overflow |
| 6 | 22:02:32 | SW distal | ~+1″ (clear overflow, large wet area) | 6.56 | +6.5″ | +1.7″ | ~0 ft | Wider view |
| 7 | 22:02:43 | SE proximal | ~+0.5–1″ (similar level to SW) | 6.56 | +6.5″ | +1.7″ | ~0 ft | Iron fence visible behind — SE confirmed |
| 8 | 22:04:21 | upstream Bay Ave | water visible in cells | 6.56 | n/a (not in v0.6) | n/a | (inferred ~3.78 NAVD88) | Square grid grate, different design from corner |
| 9 | 22:04:39 | upstream Bay Ave | water in openings, small wet trail | 6.56 | n/a | n/a | | Confirms grate emitting |
| 10 | 22:04:51 | gutter at walkway (3.78) | "worm" stream visible | 6.56 | +4.5″ | −0.2″ | ~0 ft (water at or just below gutter line) | Stream from upstream grate flowing along curb-gutter line toward walkway |
| 11 | 22:05:31 | SE proximal | +1″ (large puddle, streetlight reflection) | 6.56 | +6.5″ | +1.7″ | ~0 ft | Wide shot showing intersection — also visible: wet area at SW |
| 11 | 22:05:31 | SW distal | wet area at SW visible | 6.56 | n/a | n/a | n/a | |
| 12 | 22:05:43 | SW distal | +1″ (large wet patch in road) | 6.56 | +6.5″ | +1.7″ | ~0 ft | From middle of Central |
| 13 | 22:14:41 | SE proximal (3.60) | (wide shot — large wet patch with sediment in road) | 6.58 | +6.7″ | +1.9″ | ~0 ft | Sediment in puddle = water been there a while |
| 14 | 22:14:59 | SE proximal | wet patch + grate visible at right | 6.58 | +6.7″ | +1.9″ | ~0 ft | Looking back up at intersection from south of Bay |
| 15 | 22:15:15 | SW distal | wet patch extending into crosswalk | 6.58 | +6.7″ | +1.9″ | ~0 ft | SW at peak. NW also visible across — no clear standing water at NW. |
| 15 | 22:15:15 | NW (3.91 assumed) | no clear water above grate | 6.58 | +3.0″ | −1.6″ | <0 ft (water below grate) | NW visible across; appears dry on top |
| 16 | 22:16:23 | NE user-corner (3.91) | grate dry on top, water in slots | 6.55 | +2.7″ | −1.9″ | small positive | Top-down view, clearly dry above grate |
| 17 | 22:17:02 | NE user-corner | **water 1–1.5″ below grate top** (USER-CONFIRMED tape reading) | 6.55 | +2.7″ | −1.9″ | **+0.06 to +0.10 ft** | Water at 3.79–3.83 NAVD88; SH 6.55 → no-enhancement water = 3.73; difference = +0.06–0.10 ft |
| 18 | 22:17:43 | NE user-corner | grate dry on top (wide intersection shot) | 6.55 | +2.7″ | −1.9″ | small positive | Foreground NE grate clearly dry; consistent with 17 |
| 18 | 22:17:43 | SE distant | wet patch visible across | 6.55 | +6.5″ | +1.7″ | small positive | |
| 19 | 22:18:08 | NW across-Central | grate dry on top | 6.55 | +2.7″ | −1.9″ | small positive | NW confirmed by user (typo in log was fixed) |
| 20 | 22:18:36 | NW across-Central | **water 1.5–1.75″ below grate top** (USER-CONFIRMED tape reading; tape slightly in water) | 6.55 | +2.7″ | −1.9″ | **+0.03 to +0.06 ft** | Water at 3.77–3.79 NAVD88; SH 6.55 → no-enhancement water = 3.73; difference = +0.04–0.06 ft. Marginally smaller enhancement than NE at 22:17, consistent with tide starting to recede. |
| 21 | 22:28:37 | SE pocket retention | LARGE persistent puddle, road otherwise dry | 6.50 | +5.9″ | +1.1″ | n/a (pocket physics, not direct enhancement) | **Visual proof of post-overflow retention.** Pocket pavement ~3.48-3.52 NAVD88 (1-1.5″ below grate top); water trapped. |
| 22 | 22:28:53 | SW receding | SW pocket much smaller than SE | 6.50 | +5.9″ | +1.1″ | n/a | Suggests SW pavement is more level — drains back through grate. |

## Key inferences (one event — don't recalibrate yet)

### 1. Effective local enhancement at this event was +0.06–0.10 ft at peak, NOT +0.40

With **corrected** tape readings (NE 1-1.5″ below at 22:17, NW 1.5-1.75″ below at 22:18), the
implied enhancement was:
- 0 to +0.04 ft on the rising tide (~22:06)
- **+0.06 to +0.10 ft at peak (~22:15-22:17)**
- +0.03 to +0.06 ft just past peak (~22:18)

So enhancement *did* build as Pathway B engaged — consistent with the "equilibration over time"
hypothesis — but never approached the +0.40 the model assumes. At its peak tonight, enhancement
was ~25% of the saturated value.

Pattern matches the hypothesis: +0.40 is the saturated enhancement value that develops when SH
is well above 6.33 AND the peak lasts long enough for Pathway B to equilibrate. At SH 6.58 with
a brief peak (only ~10-15 min near top), only partial Pathway B engagement → smaller enhancement.

### 2. SW vs SE: SW overflows earlier and deeper above the grate; SE spreads more widely

**User correction:** SW probably started at the same time or *earlier* than SE — user was
hyperfocused on SE (the previously-mapped "lowest sentinel"). Photos 3-4 show clear water
already at SW while SE was just starting to spread. SE spreads widely (less depth directly
above grate, more wet area); SW concentrates deeper directly above the grate. Suggests SW
is the *lower* of the two by up to ~0.5" — SW likely at ~3.55-3.58 NAVD88 (SE at 3.60).

### 3. NE and NW corner grates: water 1-2.5″ below top throughout the event

**Corrected** based on user's live commentary + tape-measure photos:
- ~22:06 (rising tide, SH 6.56): NE 2-2.5" below top → water at 3.70-3.74 NAVD88
- ~22:15-22:17 (at peak, SH 6.55-6.58): NE 1-1.5" below → water at 3.79-3.83 NAVD88
- ~22:18 (just past peak, SH 6.55): NW 1.5-1.75" below → water at 3.77-3.79 NAVD88

Water level at the property climbed ~1" during the rise to peak, then started receding
within a few minutes. Neither NE nor NW overflowed. NE and NW are likely at very similar
elevations (~3.91 NAVD88).

### 4. The pocket-as-retention hypothesis is visually confirmed by photo 21

16 min after peak, the road is mostly dry but the SE pocket retains a clear puddle.
SW pocket (photo 22) is much smaller, suggesting different pavement topography.

### 5. The upstream Bay Ave grate is the primary feeder to the gutter at walkway

Photo 10 shows the "worm" stream visible along the curb-gutter line from the upstream
grate end toward the walkway. The corner grate (NE) never overflowed, so it didn't feed
the gutter tonight at all.

### 6. NW grate elevation

With corrected tape reading (1.5-1.75″ below top at 22:18, SH 6.55), water level at NW was
3.77-3.79 NAVD88. If NW grate is at 3.91 NAVD88 (same as NE), implied enhancement = +0.04 to
+0.06 ft. Slightly smaller than NE's +0.06 to +0.10 ft at 22:17 (1 min earlier) — consistent
with tide starting to recede. NW elevation appears to be very close to NE (~3.91 NAVD88).

## Discrepancies resolved (2026-05-19)

1. ✅ Photo 19/20: user confirmed log typo → updated to NW.
2. ✅ Tape readings: user confirmed NE=1-1.5″, NW=1.5-1.75″ (my reads were off by
   ~1-2″ each). Implied enhancement recomputed; all tables above use corrected values.
3. ✅ NW elevation: with corrected tape, NW elevation appears very close to NE (~3.91 NAVD88).
4. ✅ Photo 21 stays in both `grate-SE-proximal/` and `pocket-SE-retention/`.

## Remaining uncertainties Claude wants to surface

These are smaller and don't block the CSV write. Flagging in case the user wants to clarify:

- **Spatial water-level variation:** at peak, NE-corner water level (3.79-3.83) and SW-corner
  water level (3.67-3.72 if SW=3.55) don't quite match. ~0.1 ft difference could mean different
  corners of the intersection have different water levels (plausible — Pathway B floods unevenly
  across an intersection), or one of the elevations is slightly off. Not critical to resolve.
- **Upstream grate elevation refinement:** if SE peak water was 3.68 NAVD88 and upstream grate
  had ~1 cm of water above it at the same time, grate top = 3.68 - 0.033 ≈ 3.65 NAVD88. That's
  lower than the earlier 3.78 estimate. Worth user verifying the timing (was the "1 cm above
  upstream" observation at peak, or earlier/later?).
- **NE/NW elevation slight asymmetry:** NW water reads as ~0.02-0.06 ft lower than NE at very
  close-in-time tape shots. Could indicate NW grate is at 3.93 (slightly higher than NE's 3.91)
  OR water level varied across the intersection. Not actionable without more events.

Once the user gives a "looks good, proceed" I'll append rows to `data/labeled_observations.csv`
using the corrected enhancement numbers above.
