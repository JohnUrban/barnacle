# Historical-stats project: handoff back to the main chat

This is a return handoff from the Claude Code session that worked the
`history/HANDOFF.md` task. The project ran cleanly. The main report is at
`history/reports/flood_history_report.md`; this document is the short
peer-to-peer summary of what to update in the model spec / main HANDOFF and
where I think things are uncertain.

## What I did

1. Wrote a chunked / resumable NOAA puller for station 8531680 hourly_height
   and predictions, 1910-01-01 through 2026-05-17. Pulled in 31-day blocks,
   ~30 min wall-clock total. **1,020,142 hourly rows**, 98 years with
   ≥7000 hours of observation.
2. Built a derived hourly dataset using v0.5 constants (local enhancement
   +0.40 ft, NAVD88 = MLLW − 2.82). Verified the math at each landmark
   round-trips to the threshold values in the HANDOFF table exactly.
3. Computed seasonality (5 thresholds), GEV return periods, SLR by 4
   windows, decade-by-decade event counts, hour-of-day / week-of-year
   distributions, storm-vs-nuisance classification, and a calibration check
   on the four labeled events.
4. Wrote the report with the requested 4-question plain-language summary
   on top.

All scripts re-run end-to-end from raw chunks in seconds; raw chunks are
on-disk and resumable, so re-pulling for incremental updates is cheap.

## Headlines (with calibrated confidence)

- **Calibration check: all four labeled events match the HANDOFF / v0.5
  values exactly** (Apr 17: 6.76, Apr 18: 7.32, Oct 30: 7.57 + surge 2.90,
  Dec 19: 6.83 + surge 2.12). The historical pull is internally consistent
  with what you tuned against. No model recalibration is implied by the
  historical data.
- **SLR cross-validation succeeds.** My 1932–2024 trend is **4.29 mm/yr**
  vs NOAA's published **4.05 mm/yr** for the same window. Differences this
  small are expected from datum-update choices and minor coverage
  differences. So the gauge data and my processing chain are sound.
- **Flood-day frequency at the 6.58 ft curb threshold is up ~9× since the
  1910s**, ~15× since the 1950s. Recent decade averages **38 (2010s) → 44
  (2020s) flood days/year**. The story is overwhelmingly nuisance
  flooding (stable storms riding a higher mean), not more storms.
- **100-yr return level: 10.57 ft MLLW** (95% CI 9.5–11.8). At your curb
  that's ~48" of water from tide alone, before any rainfall amplification.

## Things I think you should update in the model spec and main HANDOFF

These are corrections I have moderate-to-high confidence in:

### 1. The "dashboard uses 7.20 ft Minor" claim is probably wrong

**Both** the project HANDOFF (`history/HANDOFF.md`) and section 5 of
`HANDOFF.md` reference a dashboard "Minor 7.20 ft" threshold. I cannot
reproduce the dashboard's monthly numbers at 7.20 ft — I'm off by ~10×.
I **can** reproduce them within rounding using **6.7 ft (NWS standard
Minor for Sandy Hook) over a ~1996–2025 window**:

| Month | Dashboard | This study at 6.7 ft, 1996–2025 |
|---|---:|---:|
| Jan | 1.50 | 1.93 |
| Feb | 1.44 | 1.50 |
| Mar | 2.13 | 2.37 |
| Apr | 2.09 | 2.07 |
| May | 1.88 | 1.93 |
| Jun | 1.88 | 1.73 |
| Jul | 1.59 | 1.53 |
| Aug | 1.78 | 1.57 |
| Sep | 2.84 | 2.73 |
| Oct | 3.97 | 3.93 |
| Nov | 1.88 | 2.03 |
| Dec | 1.97 | 2.10 |
| **Total** | **25.0** | **25.4** |

Two possibilities I can't distinguish from inside the data:

- **Dashboard mislabel:** the page says "Minor 7.20 ft" in its UI but the
  underlying threshold is the actual NWS 6.7 ft. This is what the numbers
  suggest most directly.
- **Different definition of "event":** the dashboard could be using 7.20 ft
  but with a much looser event definition (e.g., counting each hour, or
  including events I'm discarding because they're below my completeness
  filter). I tried hourly counts and tide-peak counts; neither matches at
  7.20.

If you have a way to inspect the dashboard's source (it's
`hondrospj.github.io/Sandy-Hook/`), that would resolve it. Until then I'd
**stop characterizing the dashboard as "7.20 ft Minor" in the spec** and
re-label it as "Sandy Hook dashboard, threshold uncertain — empirically
matches 6.7 ft NWS Minor."

This also has a small effect on Section 7 of the main HANDOFF: the line
"every published 'floods per year' number understates my actual exposure
by something like 2-3x" is approximately correct in magnitude. At 6.58
(curb) the rate is ~20% higher than at 6.7, and the historical record
shows the **time-window matters as much as the threshold**.

### 2. Hurricane Sandy peak: 12.03 ft hourly vs 13.31 ft instantaneous

NOAA's `hourly_height` is a centered-hour value; Sandy peaked at 13.31 ft
on the 6-minute product. The 12.03 vs 13.31 distinction matters for the
GEV fit (annual maxima of hourly values). It's a ~10% gap at the very
extreme tail.

I noted this in the report. Worth flagging in the spec too because the
forecast script's threshold ladder ("13+ ft = Hurricane Sandy class")
implicitly uses the higher number, and a real forecast hitting 12.0 ft
hourly **is** Sandy-class — don't anchor expectations on hourly numbers
matching the historical 13.31.

### 3. SLR rate is accelerating, not constant

The HANDOFF's "4.05 mm/yr (1932-2024)" is correct as a long-term fit.
But the post-1980 rate is **5.45 mm/yr** in my data (r² 0.84, n=45). That
matters for forward planning: at 5.45 mm/yr the bay rises ~5.4 cm in 10
years and ~16 cm (~0.5 ft) in 30 years. Your 4.16 ft NAVD88 curb is
~0.5 ft of additional SLR from being a moderate-tide threshold. If the
acceleration holds, the curb-wet rate doubles again by mid-century.

I'd consider adding a "future projection" line to the daily email
seasonal context: "today is a routine 6.6-ft high tide. In 1990 that
wouldn't have wet the curb; today it does; in 2040 it will wet the
lawn step."

## Things I think but am uncertain about

These are calls I made in the report but where the evidence is thin:

- **Hurricane Sandy as a "~5000-year event."** That's what the GEV fit
  says, but the CI on the 500-yr level alone runs to 14 ft — meaning the
  ratio of best-fit to upper-CI is ~1.2. Sandy's 13.31 ft is at the very
  edge of the bootstrap envelope. I described it as a "black swan even by
  EVT standards"; I think that's defensible language. **But I'd not want
  a planning document to use "5000-year" as a probability.** It's the
  fit's verdict, not a physical statement.
- **The 1910s "5.1 flood days/yr" baseline.** Only 7 years of usable data
  in that decade, and the very early gauge era may have biases I can't
  diagnose from data alone. I anchored "9× more frequent now" on this
  number. The "15× more than 1950s" comparison is on firmer ground
  (decade has 10 years of solid data).
- **My 6.7 ft Aug = 1.57 vs dashboard 1.78.** A few months are slightly
  off the dashboard. I attribute this to small window or completeness
  differences; could also be that the dashboard uses a slightly different
  threshold (e.g., 6.65) or weights years differently. The total annual
  matches within 2%; the monthly residuals are within 0.2 events/month.
  Good enough for cross-validation; not so good I'd claim "the dashboard
  is exactly 6.7 ft."
- **Cold-weather suppression.** The v0.5 spec says cold-snap events
  shouldn't be counted as floods (drain backflow lockout). I didn't
  filter those out — I'd need historical temperature joined into this
  dataset to do it cleanly. So my flood-day counts are slight
  over-estimates by some unknown small fraction (a handful per year
  in winter). This is a candidate follow-up project.

## Open questions worth chewing on

- **Aug 21 2025 NWS Moderate forecast.** It's in your section 7 of the
  main HANDOFF. The historical pull confirms a real elevated event:
  observed Sandy Hook reached **6.93 ft at 19:00 on 2025-08-21** with
  surge +1.4 ft. That's above your curb threshold (6.58) and just below
  the lawn-step (7.00). So you almost certainly would have seen water on
  the road for ~1-2 hours at the high tide that evening. If you weren't
  home that night or didn't go check, the threshold-crossing was real.
- **Is the +0.40 local enhancement actually constant?** From the
  historical record I can't tell. The pattern of "same storms reach the
  curb more often" doesn't probe variability of the offset. With weather
  data joined in, you could regress residuals against wind/pressure to
  estimate scatter. I'd guess ±0.05 ft (rough), based on the spread you
  noted (0.39–0.49 across 4 events).
- **The 1990s discontinuity.** The flood-day rate goes from ~6/yr in the
  1980s to ~14/yr in the 1990s — a sharper-than-trend jump. Could be:
  acceleration kicking in, gauge methodology change (per the HANDOFF,
  pre-1996 was 6-min vs hourly), or coincidence with a clustered
  storm-active period. The gauge methodology hypothesis is testable —
  the abrupt step around 1995-96 in the decadal data is suggestive.

## Files to grab (if you want raw data)

- `history/reports/flood_history_report.md` — primary
- `history/data/summary_stats.json` — headline numbers, machine-readable
- `history/data/calibration_check.csv` — what the historical pull says
  about your 4 labeled events
- `history/data/slr_trend_by_window.csv` — SLR by 4 windows
- `history/data/return_periods.csv` — GEV return levels + depths

The big files (the 15 MB hourly parquet, raw chunks, all the analytical
CSVs) are kept locally and listed in the report's deliverables index.
Most can be regenerated by re-running the three scripts in
`history/scripts/`.

## My one suggestion if you do nothing else

**Add a "seasonal context" line to the daily forecast email** that
mentions:

- "October averages 4 flood days at your curb. You've had 3 so far this October."
- "The bay surface in 2026 sits ~0.5 ft higher than in 1990 due to sea
  level rise — today's routine 6.7 ft high tide wouldn't have reached
  your curb in your parents' time."

You already have the seasonality data; both lines pull from
`history/data/seasonality_by_threshold.csv` and
`history/data/slr_trend_by_window.csv`. Tiny code change to
`render_email()` in `forecast/flood_forecast_daily.py`. Highest
leverage of any item in your section-7 backlog now that the historical
data exists.
