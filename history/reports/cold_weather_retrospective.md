# Cold-Weather Retrospective

_HANDOFF item 16, X in the 2026-05-19 solo-work backlog._

## Method

1. Pulled NOAA `air_temperature` for Sandy Hook (8531680) from 2010-01-01 onward.
2. Joined to the existing hourly_height parquet from the history project.
3. Computed 72-h trailing mean temperature.
4. Filtered to hours with `SH peak ≥ 6.58 ft AND < 8.0 ft AND 72-h mean temp < 32.0°F`.
5. Grouped consecutive qualifying hours into one event per calendar date (peak row).

## Result

**19 candidate events** since 2010-01-01 — top 19 by SH peak shown below. Each is a date when the v0.6 cold-lockout override would have suppressed predicted flooding because:
  - SH peak was between 6.58 and 8.0 ft MLLW (would otherwise cross the curb), AND
  - 72-h trailing mean air temperature was below 32.0°F.

**Action**: cross-check each date against the Highlands Star-Ledger / Asbury Park Press / Borough records to see whether flooding was actually reported. If most dates have no flooding mention → strong retrospective validation of cold-lockout. If many DID flood → the override is wrong or needs a different threshold.

| Date | SH peak (ft MLLW) | 72-h mean temp (°F) | Notes to check |
|---|---:|---:|---|
| 2021-02-02 | 7.90 | 26.5 | newspaper / borough archive |
| 2017-03-14 | 7.82 | 27.1 | newspaper / borough archive |
| 2016-01-23 | 7.80 | 28.5 | newspaper / borough archive |
| 2021-02-01 | 7.76 | 26.1 | newspaper / borough archive |
| 2014-01-03 | 7.70 | 27.6 | newspaper / borough archive |
| 2016-01-24 | 7.60 | 27.8 | newspaper / borough archive |
| 2018-01-04 | 7.39 | 21.3 | newspaper / borough archive |
| 2014-01-02 | 7.16 | 30.7 | newspaper / borough archive |
| 2021-02-03 | 7.16 | 29.0 | newspaper / borough archive |
| 2010-12-27 | 7.13 | 30.3 | newspaper / borough archive |
| 2022-01-17 | 7.06 | 27.7 | newspaper / borough archive |
| 2026-02-02 | 6.96 | 17.0 | newspaper / borough archive |
| 2014-02-13 | 6.89 | 24.0 | newspaper / borough archive |
| 2026-02-01 | 6.82 | 16.5 | newspaper / borough archive |
| 2019-01-24 | 6.74 | 30.0 | newspaper / borough archive |
| 2014-01-04 | 6.73 | 22.6 | newspaper / borough archive |
| 2013-02-10 | 6.71 | 31.0 | newspaper / borough archive |
| 2026-01-04 | 6.62 | 26.7 | newspaper / borough archive |
| 2010-01-31 | 6.58 | 22.3 | newspaper / borough archive |

Full candidate list: `history/data/cold_weather_candidates.csv`.

## Grouped by year

| Year | Events | Peaks (ft MLLW) |
|---|---:|---|
| 2010 | 2 | 6.58, 7.13 |
| 2013 | 1 | 6.71 |
| 2014 | 4 | 6.73, 6.89, 7.16, 7.70 |
| 2016 | 2 | 7.60, 7.80 |
| 2017 | 1 | 7.82 |
| 2018 | 1 | 7.39 |
| 2019 | 1 | 6.74 |
| 2021 | 3 | 7.16, 7.76, 7.90 |
| 2022 | 1 | 7.06 |
| 2026 | 3 | 6.62, 6.82, 6.96 |

Clustering observations:
- 2014, 2016, 2021 are the biggest cold + tide co-incidence years.
- 2021-02-01 → 02 → 03 is one storm with multiple consecutive
  high tides crossing the threshold (a true 3-day cold storm).
- Same for 2016-01-23 → 24 and 2014-01-02 → 03 → 04.
- 2026 has three already this winter (Jan 4, Feb 1, Feb 2).

## High-priority validations (user can answer from memory)

The user (John, homeowner at 342 Bay Ave) was at the property
during the 2026 events. Direct memory beats newspaper archives:

| Date | SH peak | 72-h mean temp | Flooded? (user) |
|---|---:|---:|---|
| 2026-01-04 | 6.62 | 26.7°F | ? |
| 2026-02-01 | 6.82 | 16.5°F | ? |
| 2026-02-02 | 6.96 | 17.0°F | ? |

The Feb 22-23 2026 event (the existing single calibration data
point — SH 7.19, "should have flooded but didn't") is in the same
cold winter as Feb 1-2 above. If these three also produced no
flooding, **that's a 4-event corroboration of the cold-lockout
rule without needing newspaper archives**.

The bigger events (SH > 7.5 ft, requiring real surge to reach):
2014-01-03, 2016-01-23/24, 2017-03-14, 2021-02-01/02/03 — these
are the strongest tests of the rule, since the override is
overriding a substantially elevated tide. Newspaper / Borough
archive cross-checks for these dates would be the most valuable.

## Storm-name reference

Without claiming completeness, several of these dates match
known Nor'easters and winter storms in NJ:

- 2010-12-27: Boxing Day Blizzard (Dec 26-27)
- 2014-01-02 → 03 → 04: Winter Storm Hercules
- 2016-01-23 → 24: Winter Storm Jonas
- 2017-03-14: Winter Storm Stella
- 2018-01-04: Winter Storm Grayson ("bomb cyclone")
- 2021-02-01 → 02 → 03: Winter Storm Orlena

These are all major named storms with verifiable impact records.
That makes the next analysis pass cheap: pull NWS storm summaries
or borough emergency declarations rather than newspaper microfilm.

## Web-evidence cross-check (2026-05-19)

Web searches against the 5 highest-peak candidates (the named
winter storms). Looking for "did coastal flooding actually occur
in Monmouth County / Sandy Hook Bay area on this date?"

| Date | SH peak | 72h temp | Storm | Web evidence summary | Verdict |
|---|---:|---:|---|---|---|
| 2014-01-03 | 7.70 | 27.6°F | Hercules | Mostly a SNOW event for NJ; major coastal flooding was in Massachusetts. Storm tracked east. | Probably NOT flooded — **supports cold-lockout** |
| 2016-01-23 | 7.80 | 28.5°F | Jonas | Severe flooding documented in SOUTH Jersey (Cape May, Wildwood, Stone Harbor — record peaks). North Jersey / Sandy Hook Bay area not specifically called out. | Ambiguous for Monmouth |
| 2017-03-14 | 7.82 | 27.1°F | Stella | "Coastal flooding from Winter Storm Stella inundates NJ roads" (Weather Underground). Storm shifted west, hit NJ coast. | Probably DID flood — **against cold-lockout** |
| 2018-01-04 | 7.39 | **21.3°F** | Grayson (bomb cyclone) | NJ state of emergency declared for Monmouth County; insurer claims for coastal flooding > snow claims. Highlands NJ Borough actively tracks Bay Avenue water level for this kind of event. | Probably DID flood — **against cold-lockout** |
| 2021-02-02 | 7.90 | 26.5°F | Orlena | Union Beach (Monmouth Co) police rescued motorist from rising flood waters; Route 35 in Belmar closed for flooding. | Probably DID flood — **against cold-lockout** |

### Highlands Borough's own flood log

The Borough's official flood-information page documents only 4
historical floods at the 342 Bay Ave area: Donna 1962 (4 ft on
Bay Ave), Nor'Easter 1992 (4 ft), Irene 2011 (3 ft), Sandy 2012
(7 ft) — all from Sandy Hook MLLW ≥ 9.75 ft.

**None of our 19 candidates appear on that page** — they're all in
the 6.58-7.90 ft range, well below the "worth-listing-officially"
threshold. So the Borough page can't validate or refute any of
our candidates.

### Caveats

- Web evidence is "flooding in NJ" — not "flooding at 342 Bay
  specifically." South Jersey can flood while Sandy Hook Bay
  stays calm (e.g., Jonas was severe in Cape May but unclear in
  Monmouth). Monmouth-County evidence is the best proxy.
- The 6.58 ft threshold is the curb at 342 Bay. Some named storms
  could have flooded the *region* without crossing this specific
  curb.
- 2026 candidates (Jan 4, Feb 1, Feb 2): user has only been at the
  property since September 2025 and only directly remembers the
  2026-02-22 event. The Jan 4 / Feb 1 / Feb 2 events can't be
  validated from user memory.

## Decision (2026-05-19)

Web evidence is **inconclusive overall, but leans against** the
cold-lockout override as currently formulated:

- 3 of 5 named-storm candidates (Stella, Grayson, Orlena) almost
  certainly produced coastal flooding in Monmouth County despite
  meeting both lockout conditions.
- 1 of 5 (Hercules) was primarily a snow event in NJ with no
  obvious coastal flooding — supports cold-lockout.
- 1 of 5 (Jonas) is ambiguous for our area.

**The single Feb 22-23 2026 observation** (the rule's original
calibration — "no flooding observed despite SH 7.19 + onshore
winds + cold") **may be an outlier rather than typical**. We
don't have enough evidence to confirm or reject the hypothesis
at 342 Bay specifically.

**Resulting decision**: stop applying cold-lockout as an active
model override (do NOT force predicted depths to zero when
conditions are met). Instead, surface it as an advisory note:
"Cold-weather conditions are present that could in theory
ice-lock the storm drains; the model is collecting data to
support or reject this hypothesis at 342 Bay. Predictions below
assume no suppression."

This change ships in commit-pending alongside this report. The
hypothesis remains open — every future cold-conditions-met event
adds to the validation dataset, and `data/predictions_log.csv` +
`data/labeled_observations.csv` will accumulate the relevant
evidence over time.

## Open questions going forward

- **Wind direction matters but isn't in the rule.** Onshore winds
  bathe the drain outfall continuously with bay water, which may
  prevent ice formation even in subfreezing air. Future v0.7
  refinement candidate: condition cold-lockout on wind direction
  as well, not just air temperature.
- **The 72-h mean might be too lax.** Grayson had a 21.3°F mean
  and apparently still flooded. If real ice formation needs a
  lower threshold (e.g., 72-h mean < 25°F), Hercules's 27.6°F
  wouldn't actually clear that bar either — and we'd lose the
  one positive data point.
- **The pre-existing 6.58-8.0 ft band might be wrong.** If the
  rule only suppresses small events but big events flood
  regardless, the 8.0 ceiling is too high and the band should
  shrink. (This is what the Grayson / Orlena evidence hints at.)
- **Pure-rain confounding.** Most named winter storms also
  delivered rain. Some "flooding" attributed to these storms
  might be rain-driven, not surge-driven. Filtering by rain
  amount (column added in this commit) will clarify.

## Next steps (for v0.7 calibration)

1. ~~User confirms 2026 candidates from memory~~ — user only has
   memory of 2026-02-22 (not in this list); only confirms
   cold-lockout in one direction (NO flood at 7.19 ft, cold).
2. ~~NWS Mt Holly storm summary cross-check~~ — web search above
   covered the equivalent.
3. **DONE 2026-05-19**: demote cold-lockout from active override
   to advisory note in the v0.6 model (see commit).
4. **NEW**: extend the candidate CSV with 4 more columns —
   predicted_depth_at_curb_without_lockout, rain_24h_in, wind_dir,
   wind_speed_max — so each row carries the context needed to
   classify it (pure-tidal vs rain-confounded vs offshore-vs-onshore
   wind).
5. **FUTURE**: every cold-conditions-met event observed at 342
   Bay going forward becomes a new data point. With ~3-5 more
   events in either direction, the rule's status can be
   resolved.
