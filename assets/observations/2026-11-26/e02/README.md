# 2026-11-26-e02 — Evening coastal surge flood with rain

Record type: `flood_episode`. Storm grouping: none assigned yet (same storm
as [e01](../e01/README.md) this morning; one storm, two floods).
Registered 2026-11-26 21:53 EST while the water was still receding.

**Highest level reported at the house so far:** level with the second porch
step at 21:15 EST, about 6.08 ft NAVD88 (+30.7 in over the SW grate). The
previous highest in the ledger was 5.70 ft on 2026-09-26 09:13 (12.25 in up
from the porch-step base). The 6.08 figure is derived, not read: first step top 5.41 plus the
taped 8 in riser (`assets/porch-measurements.txt`). The 20:59 note ("approx
7 inches ... almost level with second step") suggests the riser where the
owner reads may be slightly under 8 in. OPEN: owner to measure it.

## Sources

- [flood-measurements.txt](../flood-measurements.txt), "EPISODE 2" block: the
  owner's running notes, pasted as one message at 21:49 EST, unchanged.
- Ledger rows 283-295 (`data/labeled_observations.csv`, observer john),
  correction row 296, bands for rows 283 and 284 in
  `data/observation_bounds.jsonl`; see the [episode registry](../../episodes.json).
- [gauge-sources/](gauge-sources/README.md): raw preliminary NOAA pulls,
  Sandy Hook and The Battery.

## Readings (EST) beside the bay

Street level = landmark + inches (`model/elevations.md`). Bay = Sandy Hook
preliminary 6-minute reading at or before the observation, NAVD88 = MLLW − 2.82.

| Time | Owner's reading | Street, ft NAVD88 | Bay, ft NAVD88 | Street − bay |
|---|---|---|---|---|
| 19:16 | street filling near the curb, not above it | < 4.16 | 4.98 | below by > 0.8 |
| 19:54 | over sidewalk, halfway up the lawn step | 4.33–4.66 (about 4.50) | 5.75 | −1.25 |
| 20:11 | 4 in up the first porch step (measured) | 5.01 | 5.99 | −0.98 |
| 20:17 | 4 in up the first porch step (by fingers) | about 5.01 | 6.06 | −1.05 |
| 20:30 | 6.85 in up the first porch step | 5.25 | 6.16 | −0.90 |
| 20:37 | 1 in up the second-step wall | 5.49 | 6.25 | −0.76 |
| 20:52 | 4.25 in up the second-step wall | 5.76 | 6.26 | −0.49 |
| 20:54 | 4.75 in, "coming in fast" | 5.81 | 6.39 | −0.59 |
| 20:59 | 6 in | 5.91 | 6.39 (20:54) | −0.48 |
| 20:59 (second entry) | approx 7 in, almost level with the second step | about 5.99 | 6.39 (20:54) / 6.15 (21:00) | −0.2 to −0.4 |
| 21:15 | level with the second step, barely breaching | about 6.08 | 6.08 (21:12) | 0.0 |
| 21:20 | flow reversed; 6.5 in above the first step | 5.95 | 6.27 (21:18) | −0.32 |
| 21:37 | still 6 in above the first step | 5.91 | 5.79 (21:36) | +0.12 |

The Sandy Hook series is noisy at the crest (9.0 to 9.2 ft MLLW from 20:24 to
21:18, highest reading 9.211 at 20:54; The Battery is smooth, peak 8.556 at
21:00), so single "street − bay" values near the peak carry about ±0.15 ft.
For scale: 9.0 to 9.2 ft MLLW is 6.2 to 6.4 ft NAVD88, the range of #8 to #10
in `data/top10_highest_tides.tsv` (6.21, 6.17, 6.07). Preliminary 6-minute
readings are not comparable with that table's verified highs until NOAA
verifies the peak.

What the table shows `[INFERRED]`: the street ran about a foot BELOW the bay
through the rise, closed the gap as the bay levelled off, crested when the two
met (about 21:15, roughly 20 to 50 minutes after the bay's crest), and by
21:37 the street was ABOVE the falling bay. That is the signature of a
restricted connection between bay and street (the closed tide gate is the
suspect; its state was not observed today). This morning's flood showed the
same lag (street onset about 43 min after the bay peak).

Entry-order questions put to the owner, not resolved here: the 8:17 entry is
listed before the 8:11 entry, and two entries carry 8:59.

## What Barnacle said (first pass, from the published files)

- **Tide table** (NWS coastal flood product): 8.6 ft MLLW all morning, lowered
  to 8.2 at 15:07 EST, raised to 8.8 at 20:08 EST. Observed crest about 9.0 to
  9.1 (highest reading 9.21): the product was 0.4 to 0.6 ft low at ten hours
  and about 0.3 ft low an hour before.
- **Alert:** "severe tide" for 21:07 sent 11:09 EST (email, ntfy), ten hours
  ahead.
- **Barnacle's own water curve** (day peak, NAVD88): 4.5 to 4.7 at midday (lawn
  step), 5.3 to 5.75 from 15:00 to 18:00 (around the first porch step), 5.99 at
  19:20, 6.17 at 20:08, 6.36 at 20:56. Observed street crest about 6.08. One
  run (14:06 EST) published 8.05, unexplained, to be traced.
- **Live radar nowcast:** published no street level until 20:55 EST, when the
  water was already 4.75 in up the second-step wall; the live "porch" push went
  out at 20:56. It then showed +31.5 to +35.1 in (bay level plus rain) against
  an observed +27.5 to +30.7 in: it treats the street as level with the bay,
  which this table contradicts by up to a foot on the rise.

## PENDING (PLAYBOOK hand-off items)

Later readings and the time the water left the steps, lawn and street; photos;
gauge re-pull for the whole recession and verified data; MRMS rain forcing;
standard plots; tide-gate state; second-step riser measurement.
