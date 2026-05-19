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
| 16 | 22:16:23 | NE user-corner (3.91) | grate dry on top, water in slots | 6.55 | +2.7″ | −1.9″ | ≤0 ft | Top-down view, clearly dry above grate |
| 17 | 22:17:02 | NE user-corner | **water ~2–2.5″ below grate top** (tape measure visible) | 6.55 | +2.7″ | −1.9″ | ≈−0.04 ft (very small negative) | Tape shows 2-2.5 mark at water surface |
| 18 | 22:17:43 | NE user-corner | grate dry on top (wide intersection shot) | 6.55 | +2.7″ | −1.9″ | ≤0 ft | Foreground NE grate clearly dry |
| 18 | 22:17:43 | SE distant | wet patch visible across | 6.55 | +6.5″ | +1.7″ | ~0 ft | |
| 19 | 22:18:08 | NW across-Central | grate dry on top | 6.55 | +2.7″ | −1.9″ | ≤0 ft | **Log says "SW" but photo and dir say NW — likely typo in log** |
| 20 | 22:18:36 | NW across-Central | tape measure shows ~**3.5-4″ below grate top** (water surface) | 6.55 | +2.7″ | −1.9″ | ≈−0.1 ft | My reading uncertain — please verify the exact tape reading |
| 21 | 22:28:37 | SE pocket retention | LARGE persistent puddle, road otherwise dry | 6.50 | +5.9″ | +1.1″ | n/a (pocket physics, not direct enhancement) | **Visual proof of post-overflow retention.** Pocket pavement ~3.48-3.52 NAVD88 (1-1.5″ below grate top); water trapped. |
| 22 | 22:28:53 | SW receding | SW pocket much smaller than SE | 6.50 | +5.9″ | +1.1″ | n/a | Suggests SW pavement is more level — drains back through grate. |

## Key inferences (one event — don't recalibrate yet)

### 1. Effective local enhancement at this event was ~0 ft, not +0.40

Most striking pattern across all observations: the v0.6 model with +0.40 enhancement consistently
overshoots by 4-7″ at every landmark. Setting enhancement = 0 brings every observed depth within
~0.5″ of the model. Hypothesis (from earlier analysis): +0.40 is the saturated enhancement value
that only develops when SH is well above 6.33 AND the peak lasts long enough for Pathway B to
equilibrate. At SH 6.58 with a brief peak, only partial Pathway B engagement → small enhancement.

### 2. SW shows more water at peak than SE — likely a topography (pit-size) difference, not elevation

User noted SE had more water than SW initially; later SW caught up and overflowed deeper.
At peak, both showed similar overflow (~1″ above grate). The "SW slightly lower than SE"
hypothesis is supported but the elevation difference is small (maybe 0.05 ft / 0.6″).

### 3. NE and NW corner grates: water 2-4″ below top throughout the event

Both NE and NW grates stayed below their tops. Tape-measure shots (17 + 20) are the most
precise observations of the event. Reconciles with the implied water level at the property
during peak: ~3.73-3.78 NAVD88 (zero-enhancement back-calc).

### 4. The pocket-as-retention hypothesis is visually confirmed by photo 21

16 min after peak, the road is mostly dry but the SE pocket retains a clear puddle.
SW pocket (photo 22) is much smaller, suggesting different pavement topography.

### 5. The upstream Bay Ave grate is the primary feeder to the gutter at walkway

Photo 10 shows the "worm" stream visible along the curb-gutter line from the upstream
grate end toward the walkway. The corner grate (NE) never overflowed, so it didn't feed
the gutter tonight at all.

### 6. NW grate elevation inference

If my read of photo 20 is right (water ~3.5-4″ below top at 22:18, when SH was 6.55 and
water-at-342 in the zero-enhancement model = 3.73), then NW grate top is at ~3.73 + 0.29 to
0.33 = ~4.02-4.06 NAVD88 — slightly *higher* than NE (3.91). Possible. Or my tape read is
off. Need user to verify.

## Discrepancies to resolve before committing to CSV

1. **Photo 19/20 log labels.** Log says "SW grate" but they're in the NW directory and the
   photo content looks like NW. Likely a typo in the log. Confirm?
2. **Tape measure readings (photos 17 and 20).** I read photo 17 as ~2-2.5″ below grate top.
   Photo 20 as ~3.5-4″ below grate top. Hard to read at the medium resolution. Please confirm
   the exact tape readings if you remember them, or check the original photos at full size.
3. **NW elevation.** If both tape readings are accurate, NW grate is slightly higher than NE
   (4.02-4.06 vs 3.91). Plausible but worth confirming.
4. **Photo 21 placement.** I copied it to `pocket-SE-retention/` since it's clearly the
   pocket photo. Should we also keep it in `grate-SE-proximal/` (since SE grate IS visible in
   the lower-left corner), or remove from there?

Once you've reviewed and corrected, I'll append the rows to `data/labeled_observations.csv`
in proper CSV format.
