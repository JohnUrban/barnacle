# Handoff: Deploying the Highlands Flood Forecast Script

## Context for you (the new chat / Claude Code instance)

I am John, a homeowner at 342 Bay Ave in Highlands, NJ. I worked with a
previous Claude chat to build a flood prediction model for my address.
The result is a Python script at:

```
/Users/johnurban/searchPaths/github/highlands_floodwatch/forecast/flood_forecast_daily.py
```

(I'll attach the latest version of the script along with this document.)

The script:
1. Pulls Sandy Hook NOAA tide forecast and observed surge
2. Pulls NWS rainfall and temperature forecast for Highlands
3. Applies a hyperlocal flood model that translates the forecast into
   inches of water at landmarks at my address (curb, road middle,
   intersection center, lawn step)
4. Sends an email report

The script uses **only the Python standard library** — no pip installs
required. Python 3.9+.

## What I need help with

1. **Run the script in dry-run mode** to confirm it works end-to-end and
   the email content looks right
2. **Set up SMTP** so the script can send real emails
3. **Schedule it** to run daily, automatically

I'm on macOS. I have a GitHub account. I'm comfortable in the terminal
but new to cron and to GitHub Actions.

## Step 1: Test the script end-to-end (no email)

```bash
cd ~/searchPaths/github/highlands_floodwatch/forecast
python3 flood_forecast_daily.py --dry-run
```

This should print the email content to stdout. Possible outcomes:

- **It prints a forecast email**: great, move to step 2
- **It throws an error fetching NOAA/NWS data**: likely a transient
  network or API issue; retry. The script uses only public APIs and
  doesn't require any keys.
- **It throws an error about a missing field**: probably an API
  schema change. Inspect the error, fix the affected fetcher.

Also useful for debugging: `python3 flood_forecast_daily.py --json`
prints the raw forecast dict.

## Step 2: Set up email sending

Easiest path: Gmail with an **app-specific password** (not your normal
Gmail password — that won't work with SMTP).

1. Go to https://myaccount.google.com/apppasswords
2. Generate an app password labeled "highlands flood forecast"
3. Save the 16-character password (Gmail shows it once)

Then test:

```bash
export SMTP_HOST=smtp.gmail.com
export SMTP_PORT=465
export SMTP_USER=youremail@gmail.com
export SMTP_PASS='your-16-char-app-password'
export SMTP_FROM=youremail@gmail.com
export SMTP_TO=youremail@gmail.com
python3 flood_forecast_daily.py
```

Should print `Sent: [subject line]` and you should get an email.

## Step 3: Schedule it to run daily

Two options — pick one.

### Option A: cron on your Mac

Pros: simple, no internet dependency for scheduling.
Cons: requires your laptop to be on and connected at the scheduled time.

1. Make a wrapper script that includes the env vars, so cron has access:

```bash
cat > ~/searchPaths/github/highlands_floodwatch/forecast/run_forecast.sh <<'EOF'
#!/bin/bash
export SMTP_HOST=smtp.gmail.com
export SMTP_PORT=465
export SMTP_USER=youremail@gmail.com
export SMTP_PASS='your-app-password'
export SMTP_FROM=youremail@gmail.com
export SMTP_TO=youremail@gmail.com
cd "$(dirname "$0")"
/usr/bin/python3 flood_forecast_daily.py >> log.txt 2>&1
EOF
chmod +x ~/searchPaths/github/highlands_floodwatch/forecast/run_forecast.sh
```

2. Edit your crontab:

```bash
crontab -e
```

Add this line to run daily at 7 AM:

```
0 7 * * * /Users/johnurban/searchPaths/github/highlands_floodwatch/forecast/run_forecast.sh
```

Save and exit. Check installed crontabs with `crontab -l`. macOS may
ask for permission for cron to access your home folder — say yes.

Note: `run_forecast.sh` has your password in plaintext. Make sure the
file is not world-readable (`chmod 700 run_forecast.sh`) and don't
commit it to git. Add it to `.gitignore`.

### Option B: GitHub Actions (recommended)

Pros: runs in the cloud, free, doesn't need your laptop, secrets stored
properly.
Cons: requires the repo to be hosted on GitHub.

1. Push the script to a GitHub repo if you haven't already.

2. Add secrets in repo Settings -> Secrets and variables -> Actions ->
   New repository secret. Add each of:
   `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM`, `SMTP_TO`

3. Add this workflow file at `.github/workflows/forecast.yml`:

```yaml
name: Daily flood forecast
on:
  schedule:
    - cron: '0 11 * * *'   # 7 AM EDT = 11 UTC. Adjust for winter (12 UTC = 7 AM EST).
  workflow_dispatch:        # manual run button in GitHub UI

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
        run: python forecast/flood_forecast_daily.py
```

4. Push, then verify in the GitHub Actions tab. Use the manual run
   button first to confirm. If that works, the daily schedule will
   take over.

## Troubleshooting

- **`KeyError: 'SMTP_FROM'`**: env vars not set in the current shell.
  Either export them first or use `--dry-run` to skip the email step.
- **NOAA API returns no data**: occasionally CO-OPS API hiccups.
  Retry. If persistent, check
  https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?station=8531680&product=predictions&datum=MLLW&date=today&format=json
  in a browser.
- **NWS rate limits**: api.weather.gov requires a User-Agent header
  identifying you. The script defaults to a generic one — set the
  `USER_AGENT` env var to something like
  `"flood-forecast yourname@email.com"` to be polite and avoid rate
  limits.
- **Time zone**: cron uses local time on your Mac. GitHub Actions uses
  UTC. The `0 11 * * *` line above is 7 AM EDT / 8 AM EST. If you're
  in winter, change to `0 12 * * *` for 7 AM EST.
- **GitHub Actions running but not sending email**: check the Actions
  log. If you see SMTP authentication errors, regenerate the Gmail
  app password.

## What the model does internally (for your reference)

The script applies "flood model v0.4" which uses these calibrated
parameters:

```python
LOCAL_ENHANCEMENT_FT = 0.40    # Sandy Hook obs -> 342 Bay water level
CURB_TOP     = 4.16            # ft NAVD88, Bay Ave side at walkway
ROAD_MIDDLE  = 4.36
INTERSECTION = 4.54
LAWN_STEP    = 4.58
```

These are anchored in surveyed elevations from a Borough engineering
plan (H2M Associates, May 2024). The local enhancement factor was
empirically fit from 4 confirmed flood events. The model predicts
depth in inches above each landmark.

You shouldn't need to change these. If the model later improves (more
events, refined parameters), the user (me) will update them.
