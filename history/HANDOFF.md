# Handoff: Historical Flood Statistics at 342 Bay Ave, Highlands NJ

## Context

This is a multi-day data project for Claude Code. The goal is to pull
the entire historical hourly water level record from NOAA's Sandy Hook
gauge (station 8531680, records back to ~1910) and produce statistics
tailored to a specific address — 342 Bay Avenue, Highlands NJ.

I'm John, the homeowner. I worked with another Claude chat to build a
flood model for my address. The model is calibrated and ready. Now I
want to put it in historical context: how often does my house flood,
how has it changed over time, what are the return periods for severe
events?

## The model parameters you'll need

These are anchored in surveyed elevations from Highlands Borough's H2M
engineering plans (May 2024) plus four flood events I personally
observed in 2025-26 (April 17, April 18, October 30, December 19).

```python
# Translate Sandy Hook MLLW gauge reading to water level at 342 Bay Ave
LOCAL_ENHANCEMENT_FT = 0.40    # ft, empirically fit
MLLW_TO_NAVD88 = -2.82         # NAVD88 = MLLW + offset

# 342 Bay Ave landmark elevations (ft NAVD88)
CURB_TOP     = 4.16    # Bay Ave side at walkway
ROAD_MIDDLE  = 4.36    # Bay Ave centerline at my spot
INTERSECTION = 4.54    # Bay+Central, local high point
LAWN_STEP    = 4.58    # walkway/lawn step

# So Sandy Hook MLLW values that correspond to landmarks getting wet:
# water_at_342_MLLW = Sandy_Hook_MLLW + 0.40
# water_at_342_NAVD88 = water_at_342_MLLW - 2.82

# Flood thresholds in Sandy Hook MLLW units:
# 6.58 ft = water tops curb at walkway (flood onset)
# 6.78 ft = water on Bay Ave road middle
# 6.96 ft = intersection center wet (severe regime begins)
# 7.00 ft = lawn step wet
# 8.00 ft = severe flooding regime
# 13.0+ ft = Hurricane Sandy class
```

## Task

Produce a polished analytical report and a reusable dataset.

### Step 1: Pull historical data

NOAA CO-OPS API gives hourly verified water levels. Endpoint:

```
https://api.tidesandcurrents.noaa.gov/api/prod/datagetter
  ?station=8531680
  &product=hourly_height       # verified hourly observations
  &datum=MLLW
  &begin_date=YYYYMMDD
  &end_date=YYYYMMDD
  &units=english
  &time_zone=lst_ldt
  &format=json
```

Constraints:
- Max 31 days per request for hourly_height
- Sandy Hook gauge data starts in 1910, but pre-1980 coverage is
  spotty. Realistic full-coverage start: ~1980. Try as far back as
  data exists; gracefully skip empty responses.
- Rate limit: be polite, sleep 0.5-1s between requests, retry on 429
- Pull through "yesterday" (don't pull today, data not yet verified)

Also pull predicted hourly tide for the same range (for surge
calculation):

```
&product=predictions   # astronomical
```

Save both as Parquet or CSV (Parquet preferred for size/speed).

Estimated size: ~30-45 years × 24 hr × 365 days ≈ 300k-400k rows.
Trivial for pandas.

### Step 2: Build derived dataset

Per hour, compute:
- `observed_mllw` (from hourly_height)
- `predicted_mllw` (from predictions)
- `surge_ft = observed_mllw - predicted_mllw`
- `water_at_342_navd88 = observed_mllw + 0.40 - 2.82`
- `depth_at_curb_in = max(0, water_at_342_navd88 - 4.16) * 12`
- Similarly for road_middle, intersection, lawn_step
- `year`, `month`, `dow`, `hour` columns for grouping
- `event_id` — assign consecutive hours of flooding the same event ID

### Step 3: Analytical outputs

Produce a Markdown report with these sections:

#### 3a. Monthly seasonality (the real version)

The user has a CSV from the Sandy Hook dashboard showing average floods
per month, but it uses the dashboard's 7.20 ft Minor threshold — too
high for my house. Recompute using *my* threshold (Sandy Hook obs ≥
6.58 ft, i.e., water at my curb).

For comparison, also compute at:
- 6.58 ft (my house flood onset)
- 7.00 ft (water on my lawn)
- 7.20 ft (the dashboard's Minor — for sanity check against their stats)
- 7.70 ft (NWS Moderate)
- 8.70 ft (NWS Major)

For each threshold, by month:
- Average events per month (event = contiguous hours above threshold)
- Average total hours per month above threshold
- Maximum observed event in that month (peak height, duration)

Present as a table. Include the published Sandy Hook dashboard
seasonality numbers as one column for cross-validation.

#### 3b. Return periods

For peak observed water level (annual maxima):
- 2-year, 5-year, 10-year, 25-year, 50-year, 100-year return levels
- Use a Generalized Extreme Value fit (scipy.stats.genextreme)
- Plot the GEV fit with confidence intervals
- Convert to depth at 342 Bay landmarks

Where does Hurricane Sandy fit on the return curve? (It was 13.31 ft
MLLW — what return period does that correspond to in the fitted
distribution?)

#### 3c. Sea level rise effect

Two ways to show it:

1. Annual mean water level over time. Plot. Estimate trend (linear
   regression). Express in mm/year and ft/century.
2. Frequency of crossing 6.58 ft threshold per decade. Plot. The
   expected story: events at any given threshold becoming more
   frequent over time as base sea level rises.

For Sandy Hook specifically, the NOAA published linear trend is about
4.05 mm/year (1932-2024). Your fit should be in that ballpark.

#### 3d. Hour-of-day and day-of-year patterns

- At any given threshold, what hours of the day do peaks tend to occur?
  (Should follow the M2 tidal cycle, roughly 12.4-hour period.)
- Day-of-year heat map: which weeks of the year see the most flooding?

#### 3e. Storm events vs nuisance floods

Define:
- "Nuisance" event: peak < 7.5 ft, duration < 6 hours
- "Storm" event: peak >= 8.5 ft OR duration >= 12 hours above 6.58 ft

Count each type per year. Has the ratio changed?

#### 3f. Recent calibration check

Look up the four flood events I observed:
- 2025-10-30, 2025-12-19, 2026-04-17, 2026-04-18

For each, pull the actual hourly observed/predicted/surge from the
historical data and verify it matches what we used in model
calibration. Sanity check.

Also count: between Sep 1 2025 and May 17 2026, how many hours above
6.58 ft did Sandy Hook record? That tells me how many flood events I
*should* have seen — useful for catching any I missed.

### Step 4: Deliverables

In addition to the Markdown report:

1. `sandy_hook_hourly_history.parquet` — the full pulled dataset
2. `342_bay_flood_events.csv` — one row per flood event with peak,
   duration, max depth at each landmark, year, month
3. `figures/` — all plots as PNGs

## Practical notes

- Pulling all the data takes a few hours. Pull in 30-day chunks, save
  progress periodically so you can resume.
- The NOAA API uses lst_ldt (local standard / local daylight time)
  — this is fine, just remember it for joining with weather data
  later. Treat all timestamps as America/New_York.
- Pre-1996 gauge readings may have less precision (every 6 minutes vs
  hourly, different sensors). The hourly_height product abstracts
  this away.
- Cross-validate against published Sandy Hook trends:
  https://tidesandcurrents.noaa.gov/sltrends/sltrends_station.shtml?id=8531680

## Why this matters

The published Sandy Hook flood statistics use a 7.20 ft threshold
(NWS Minor). At my house I flood at 6.58 ft. So every published
"floods per year" number understates my actual exposure by something
like 2-3x. This project produces the version of those statistics that
is actually accurate for my specific address.

That accuracy matters for:
- Insurance decisions (what's my real expected loss?)
- Long-term planning (sea level rise impact at my landmarks)
- Forecasting calibration (does the daily prediction script match
  historical reality?)
- Sharing with neighbors (similar elevations, similar threshold)

## Final form

When done, write me a one-page summary at the top of the report that
answers in plain language:

1. How many days per year does my house flood, historically?
2. How is that changing over time?
3. What's the worst event I should plan for? (100-year return level)
4. Have I been seeing more floods recently than my parents would have?
