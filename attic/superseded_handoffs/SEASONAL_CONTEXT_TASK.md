# Task: Add seasonal context to the daily forecast email and HTML page

This is a hand-off to Claude Code for a small feature add. It builds on
the historical-stats project you just completed (see
`history/RESULTS_HANDOFF.md` if you don't have it loaded). The data you
need is already produced and sitting in `history/data/`.

## Goal

Add two context lines to the daily forecast output (email body + HTML
page on GitHub Pages) so the reader sees today's tide in long-term
context:

1. **Seasonality line.** Tell the reader how often the curb gets wet in
   this month historically. Example:
   > "October averages ~4 flood days at your curb (Sandy Hook ≥ 6.58 ft).
   > That's the wettest month of the year — Sandy Hook's late-summer/early-
   > fall surge season."
2. **SLR-context line.** When today's high tide is in the "newly wet"
   regime — high enough to cross the user's curb today but wouldn't have
   in 1990 because sea level has risen — call that out. Example:
   > "Sea level at Sandy Hook has risen ~0.6 ft since 1990. Today's high
   > tide of 6.72 ft wouldn't have crossed your curb back then; today it
   > does."

Both lines should appear in the email and on the published HTML page.
They are contextual / educational, not part of the forecast itself.

## Files to read first

1. **`history/data/seasonality_by_threshold.csv`** — monthly averages at
   each threshold. Confirm column layout (likely something like
   `threshold_ft`, `month`, `avg_events_per_month`, `avg_hours_above`).
   You want the row matching threshold = 6.58 ft (or closest) for the
   current calendar month.
2. **`history/data/slr_trend_by_window.csv`** — SLR rate by window.
   Look for a row with the post-1980 window (~5.45 mm/yr). You'll use
   the rate to compute "how much has MSL risen since 1990" for the
   SLR-context line.
3. **`history/data/summary_stats.json`** — headline numbers; useful
   sanity check for the SLR rate and the order-of-magnitude flood
   frequency.
4. **`history/reports/flood_history_report.md`** — full context for
   what these numbers mean.
5. **`forecast/flood_forecast_daily.py`** — the script you're modifying.
   Focus on `render_email()` and `render_html_page()`. Don't touch the
   forecast logic itself.

## Implementation guidance

### Seasonality line: keep it simple

For v1, skip the "you've had N so far this month" idea — it requires a
month-to-date NOAA API call and a defensible definition of "event"
(contiguous hours? unique days? peaks?). Save that for a v2 if the user
asks.

For v1, just state the historical monthly average. Read the relevant
row from `seasonality_by_threshold.csv`, format the line, inject.

If you want a small flourish, you can add a single descriptor like
"wettest month" / "quietest month" / "shoulder season" based on
month-relative ranking — but only if it falls out naturally. Don't force.

### SLR-context line: conditional and quantitative

This line only makes sense when today's forecast peak is in the "newly
wet" regime. Pseudocode:

```python
slr_rate_mm_per_yr = 5.45        # post-1980 rate from slr_trend_by_window.csv
years_since_1990 = today.year - 1990
slr_since_1990_ft = (slr_rate_mm_per_yr * years_since_1990) / 304.8

# Effective 1990 curb threshold in today's reference frame
# (today's curb is 6.58 ft MLLW; in 1990, equivalent water level was lower
# by slr_since_1990_ft)
curb_threshold_today = 6.58
curb_threshold_in_1990_equiv = curb_threshold_today + slr_since_1990_ft

# Show the line only when today's peak is in the newly-wet band
if curb_threshold_today <= forecast_peak < curb_threshold_in_1990_equiv:
    line = f"Sea level at Sandy Hook has risen ~{slr_since_1990_ft:.1f} ft since 1990. " \
           f"Today's high tide of {forecast_peak:.2f} ft wouldn't have crossed your " \
           f"curb back then; today it does."
```

If today's peak is below the curb threshold, skip the SLR line entirely
(the seasonality line is enough). If today's peak is *well above* the
curb in any era (>7.5 ft, severe regime), also skip — the context is
unnecessary noise during real flood events.

Optional polish: pick the comparison year dynamically. "Wouldn't have
wet your curb in 1990" works year-round. But for tides only slightly
above curb you could say "wouldn't have crossed in 2010" — more recent,
more impactful. Whatever feels right.

### Where to place these lines

Plain text email: somewhere between the landmark depth table and the
sign-off / source footer. Either a single combined "Context" section or
two separate one-liners, your call.

HTML page: same logical position. Match existing visual style. Don't
introduce a new color or font weight — these are de-emphasized context
lines, not part of the headline forecast.

### Voice

The project has a "barnacle" voice: concise, accurate, slightly playful.
"Today's high tide of 6.72 ft wouldn't have crossed your curb in 1990;
today it does" is on tone. Don't editorialize about climate change in the
output — let the numbers speak. The user knows what's happening.

## Testing

The system is in production. Use the existing tools:

1. `forecast/smoke_test.sh` is the safety net — run it before any commit.
2. `python3 forecast/flood_forecast_daily.py --dry-run --no-send` to
   exercise without sending email.
3. `python3 forecast/flood_forecast_daily.py --dry-run --no-send --write-html /tmp/test.html`
   to also produce the HTML for visual review.
4. Run multiple times with mocked or varied tide values to exercise
   both the "newly-wet" regime (SLR line fires) and other regimes
   (SLR line skipped). Easiest way: temporarily override the forecast
   peak in a local copy before running.

## Acceptance

When done:

- Daily email and `docs/index.html` both show the new seasonal context
- Seasonality line shows every day, accurate for current calendar month
- SLR-context line shows only when forecast peak is in the "newly wet"
  band (between today's curb threshold and 1990's effective curb)
- Smoke test passes
- No change to forecast logic, formula, or any existing output line
- Commit message something like `forecast: add seasonal/SLR context lines`

## Things to be careful of

- **System is in production.** Daily emails arrive at 5 AM ET; the
  GitHub Pages site updates automatically. A bug that crashes the
  script breaks the daily loop. Always run the smoke test before
  pushing.
- **The bot commits daily.** `git pull --rebase` before pushing.
- **CSV column names are not assumed.** Read the file headers; don't
  guess. If a column doesn't exist or the layout surprises you, stop
  and flag it.
- **`history/data/raw_chunks/` and `sandy_hook_hourly_history.parquet`
  are gitignored.** Don't accidentally commit them.

## Stretch (if there's appetite, otherwise skip)

- "You've had N flood days at your curb this October" — requires
  month-to-date NOAA hourly_height pull and a "day flagged as flood
  if peak hour ≥ 6.58 ft" definition. Adds an API call to the daily
  script, which is otherwise fast.
- "On track for X events this month" — extrapolation from MTD count
  + historical month-of-year shape. Niche.
- "Year-to-date: N flood days vs ~22 historical average" — useful
  anchor, requires a yearly-cumulative pull.

End of task spec.
