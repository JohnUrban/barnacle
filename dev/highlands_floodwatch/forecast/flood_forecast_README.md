# Daily flood forecast — deployment notes

## What it does

Pulls Sandy Hook tide forecast, current surge, NWS rainfall and temperature
for Highlands, applies the v0.4 model, and emails a per-landmark depth
prediction for 342 Bay Ave.

## Requirements

- Python 3.9+
- No third-party packages — uses only the standard library
- SMTP credentials for sending email (Gmail with an app-specific password works fine)

## Environment variables

```
SMTP_HOST       e.g. smtp.gmail.com
SMTP_PORT       e.g. 465
SMTP_USER       login username
SMTP_PASS       password or app-specific password
SMTP_FROM       sender email address
SMTP_TO         recipient(s), comma-separated
USER_AGENT      optional, identifies your script (NWS API requires this; default works)
```

## Test it once before scheduling

```bash
export SMTP_HOST=smtp.gmail.com
export SMTP_PORT=465
export SMTP_USER=you@gmail.com
export SMTP_PASS='your-app-specific-password'
export SMTP_FROM=you@gmail.com
export SMTP_TO=you@gmail.com
python3 flood_forecast_daily.py
```

## Schedule it

### Option A: cron (Linux/Mac)

Run daily at 7 AM local:
```cron
0 7 * * * cd /path/to/script && /usr/bin/python3 flood_forecast_daily.py >> log.txt 2>&1
```

### Option B: GitHub Actions (free, runs in the cloud)

`.github/workflows/forecast.yml`:
```yaml
name: Daily flood forecast
on:
  schedule:
    - cron: '0 11 * * *'  # 7 AM EDT = 11 UTC; adjust for DST
  workflow_dispatch:       # manual trigger button

jobs:
  forecast:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - env:
          SMTP_HOST: ${{ secrets.SMTP_HOST }}
          SMTP_PORT: ${{ secrets.SMTP_PORT }}
          SMTP_USER: ${{ secrets.SMTP_USER }}
          SMTP_PASS: ${{ secrets.SMTP_PASS }}
          SMTP_FROM: ${{ secrets.SMTP_FROM }}
          SMTP_TO:   ${{ secrets.SMTP_TO }}
        run: python flood_forecast_daily.py
```

Add the secrets in your repo's Settings -> Secrets and variables -> Actions.

## What it gets right

- Astronomical tide for next 24h (NOAA, reliable)
- Current surge as a proxy for forecast surge (works when conditions are
  steady or worsening; fails for rapidly developing storms)
- Rainfall in the high-tide window (NWS, reasonable)
- Cold lockout detection (NOAA Sandy Hook air temp)
- v0.4 model with all four landmark predictions

## What it gets approximately right

- Surge persistence assumption: takes current observed minus current
  predicted and adds that to the forecast peak. This works for ongoing
  storms but underestimates rapidly developing ones. For active coastal
  flood watches, cross-check NWS Coastal Flood Statement manually.
- Rainfall rate: NWS hourly forecast `quantitativePrecipitation` is
  somewhat coarse and may underreport intense convective bursts.

## What it can't get right yet

- NWS Coastal Flood Statement ingestion (text product, requires parsing
  natural language — would substantially improve surge forecasting)
- NYHOPS Stevens Institute model forecasts (would give better surge
  estimates but needs a different API integration)
- HRRR high-resolution rainfall (NWS public API uses NDFD which is
  smoother)

## Tuning the model

All v0.4 parameters are constants at the top of the script:

```python
LOCAL_ENHANCEMENT_FT = 0.40
CURB_TOP     = 4.16
ROAD_MIDDLE  = 4.36
INTERSECTION = 4.54
LAWN_STEP    = 4.58
COLD_LOCKOUT_F = 32
RAIN_SATURATION_IN = 8.0
```

Adjust as more events come in and the empirical fit improves.

## Output

The email subject line gives the regime and a one-line summary; the body
contains the full landmark table and the inputs that produced it. Open
the message and you have everything you need to decide whether to move
the car, sandbag, or relax.


## Try

```
python3 flood_forecast_daily.py --help        # see options
python3 flood_forecast_daily.py --dry-run     # print email to stdout
python3 flood_forecast_daily.py --json        # see raw data
```
