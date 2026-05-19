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

## Web-evidence cross-check (2026-05-19)

Web searches against the 5 highest-peak candidates (the named
winter storms). Looking for "did coastal flooding actually occur
in Monmouth County / Sandy Hook Bay area on this date?"

| Date | SH peak | 72h temp | Storm | Web evidence summary | Verdict |
|---|---:|---:|---|---|---|
| 2014-01-03 | 7.70 | 27.6°F | Hercules | Mostly a SNOW event for NJ; major coastal flooding was in Massachusetts. Storm tracked east. | Probably NOT flooded — supports cold-lockout |
| 2016-01-23 | 7.80 | 28.5°F | Jonas | Severe flooding documented in SOUTH Jersey (Cape May, Wildwood, Stone Harbor — record peaks). North Jersey / Sandy Hook Bay area not specifically called out. | Ambiguous for Monmouth |
| 2017-03-14 | 7.82 | 27.1°F | Stella | "Coastal flooding from Winter Storm Stella inundates NJ roads" (Weather Underground). Storm shifted west, hit NJ coast. | Probably DID flood — against cold-lockout |
| 2018-01-04 | 7.39 | **21.3°F** | Grayson (bomb cyclone) | NJ state of emergency declared for Monmouth County; insurer claims for coastal flooding > snow claims. | Probably DID flood — against cold-lockout |
| 2021-02-02 | 7.90 | 26.5°F | Orlena | Union Beach (Monmouth Co) police rescued motorist from rising flood waters; Route 35 in Belmar closed for flooding. | Probably DID flood — against cold-lockout |

The Highlands Borough's own flood-info page documents only Donna
1962, Nor'Easter 1992, Irene 2011, Sandy 2012 — all ≥ 9.75 ft MLLW.
None of our 19 candidates appear there (all are < 7.90 ft MLLW).

## Augmented analysis (4 new columns, script rerun 2026-05-19)

After adding `predicted_depth_at_curb_without_lockout_in`,
`wind_dir`, `wind_speed_max_kts`, and `wind_dir_deg` columns:

### Pattern (suggestive, not yet conclusive)

**Every event flagged "LIKELY flooded" by the web search has
NNE or N (onshore) winds AND a 9-16" depth-without-lockout claim**:

| Event | wind_dir | wind_kts | depth_wo_lockout | flooded? |
|---|---|---:|---:|---|
| Stella 2017-03-14 | **NNE** | 16.9 | 14.9" | LIKELY |
| Grayson 2018-01-04 | N | 24.9 | 9.7" | LIKELY |
| Orlena 2021-02-01 | **NNE** | 16.3 | 14.1" | LIKELY |
| Orlena 2021-02-02 | **NNE** | 15.5 | 15.8" | LIKELY |
| Hercules 2014-01-03 | (no wind data) | — | 13.4" | NOT flooded |

This is consistent with: **onshore winds bathe the storm-drain
outfall in bay water continuously, preventing ice formation
regardless of air temp.** v0.6's implicit assumption that 72-h
mean temp alone determines drain ice appears wrong.

The 2026 events (Jan 4, Feb 1, Feb 2) all have NNW or N winds
(borderline offshore) and small depth-without-lockout claims
(0.5-4.6"). These are the candidates where the rule might
actually apply (drain outfall exposed to subfreezing air rather
than continuously bathed in bay water). User wasn't at the
property for any of them (only on-site since Sept 2025 for the
Feb 22 event which isn't in this list).

Wind data was unavailable for ~7 of 19 events (NOAA `wind`
product at station 8531680 not reported for some date ranges).
Pattern observation based on the 12 events with wind data.

### Refined v0.7 hypothesis candidate

The cold-lockout rule may be salvageable with a wind-direction
condition. Provisional formulation:

> Cold-lockout fires when:
>   - 72-h mean temp at Sandy Hook < 32°F, AND
>   - Wind during the high-tide window is OFFSHORE (~30-110° for
>     Sandy Hook Bay is onshore, so OFFSHORE = outside that arc),
>     AND
>   - SH peak between curb (6.58) and lockout ceiling (8.0) MLLW.

This would have correctly suppressed:
- The smaller 2026 candidates (Jan 4, Feb 1, Feb 2 — NNW/N winds,
  small depth claims)

And correctly NOT suppressed:
- 2017-03-14 Stella, 2021-02-01/02 Orlena (NNE = onshore)
- 2018-01-04 Grayson (N = borderline; would need a wider
  off-shore threshold or a softer rule)

**The single Feb 22 2026 observation** that originally calibrated
the rule had ONSHORE winds AND a high SH peak, AND the user
observed NO flooding. That's contrary to the pattern emerging
from this retrospective — suggesting it's an outlier and the
rule may be wrong even with a wind-direction condition.

**Decision (2026-05-19, in commit 88d1f54)**: cold-lockout
demoted from active override to advisory. The predictions go
through unchanged when conditions are met; a yellow banner
explains the hypothesis is open. Every cold-conditions-met
event going forward becomes new validation data.

## Decision summary

Web evidence + augmented retrospective leans **against** the
cold-lockout rule as currently formulated. The single Feb 22
2026 calibration point may be an outlier. Rule remains in code
as advisory only (not actively suppressing predictions). The
hypothesis is open and may be revisited with a wind-direction
condition as part of v0.7.

## Caveats

- Web evidence is "flooding in NJ" — not "flooding at 342 Bay
  specifically." South Jersey can flood while Sandy Hook Bay
  stays calm.
- Wind data missing for ~7 of 19 events.
- The "user wasn't there" 2026 candidates can't be directly
  validated yet.
- The 6.58 ft threshold is the curb at 342 Bay. Some named
  storms could have flooded the region without crossing this
  specific curb.

## Next steps

1. ✅ DONE 2026-05-19: cold-lockout demoted to advisory in the
   v0.6 model (commit 88d1f54).
2. ✅ DONE 2026-05-19: script extended with 4 new columns
   (predicted_depth_at_curb_without_lockout_in, rain_24h_in,
   wind_speed_max_kts, wind_dir_deg, wind_dir).
3. **FUTURE**: every cold-conditions-met event observed at 342
   Bay going forward adds to the validation dataset. With ~3-5
   more events in either direction, the rule's status (drop or
   refine with wind condition) can be resolved.
4. **v0.7**: consider wind-direction condition for the cold-
   lockout rule, OR drop the rule entirely. Decision waits on
   more data.
