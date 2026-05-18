#!/usr/bin/env python3
"""
Daily flood forecast for 342 Bay Ave, Highlands NJ.

Pulls Sandy Hook tide forecast, current observed water level (for surge),
NWS rainfall and temperature forecast for Highlands, applies the v0.4
flood model, and sends an email report.

Run daily (cron, GitHub Actions, etc).

Environment variables required:
    SMTP_HOST    - e.g. smtp.gmail.com
    SMTP_PORT    - e.g. 465
    SMTP_USER    - login username
    SMTP_PASS    - password or app-specific password
    SMTP_FROM    - sender email address
    SMTP_TO      - recipient(s), comma-separated

Optional:
    USER_AGENT   - identifies your script to NWS API (their requirement)
"""

import os
import math
import json
import smtplib
import datetime as dt
from email.message import EmailMessage
from urllib.request import Request, urlopen
from urllib.parse import urlencode

# ============================================================
# v0.4 model parameters - update these as the model improves
# ============================================================
LOCAL_ENHANCEMENT_FT = 0.40        # Sandy Hook obs -> 342 Bay water level

# Landmark elevations at 342 Bay Ave (NAVD88, ft)
CURB_TOP     = 4.16   # Bay Ave side at walkway
ROAD_MIDDLE  = 4.36   # Bay Ave centerline at user's spot
INTERSECTION = 4.54   # Bay+Central intersection center (local high)
LAWN_STEP    = 4.58   # estimated walkway step

MLLW_TO_NAVD88_OFFSET = -2.82  # NAVD88 = MLLW + offset

COLD_LOCKOUT_F = 32            # 72h mean below this = drains ice-locked
RAIN_SATURATION_IN = 8.0       # max inches rain can add

# Notification thresholds (inches at curb)
ALERT_LIGHT    = 1.0
ALERT_MODERATE = 4.0
ALERT_SEVERE   = 8.0

# Location
HIGHLANDS_LAT = 40.4015
HIGHLANDS_LON = -73.991
NOAA_STATION = "8531680"  # Sandy Hook
UA = os.environ.get("USER_AGENT", "highlands-flood-forecast (contact@example.com)")


# ============================================================
# Data fetchers
# ============================================================
def _get(url, params=None, headers=None):
    if params:
        url = url + "?" + urlencode(params)
    req = Request(url, headers={"User-Agent": UA, **(headers or {})})
    with urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def fetch_predicted_tide_24h():
    """Hourly astronomical tide prediction for next 24h (MLLW ft)."""
    now = dt.datetime.now(dt.timezone.utc)
    end = now + dt.timedelta(hours=24)
    data = _get(
        "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter",
        {
            "station": NOAA_STATION,
            "product": "predictions",
            "datum": "MLLW",
            "time_zone": "lst_ldt",
            "units": "english",
            "interval": "h",
            "begin_date": now.strftime("%Y%m%d %H:%M"),
            "end_date": end.strftime("%Y%m%d %H:%M"),
            "format": "json",
        },
    )
    return [(p["t"], float(p["v"])) for p in data.get("predictions", [])]


def fetch_observed_recent():
    """Past 6h of observed water level. Returns list of (time, value_mllw_ft)."""
    end = dt.datetime.now(dt.timezone.utc)
    start = end - dt.timedelta(hours=6)
    data = _get(
        "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter",
        {
            "station": NOAA_STATION,
            "product": "water_level",
            "datum": "MLLW",
            "time_zone": "lst_ldt",
            "units": "english",
            "begin_date": start.strftime("%Y%m%d %H:%M"),
            "end_date": end.strftime("%Y%m%d %H:%M"),
            "format": "json",
        },
    )
    out = []
    for d in data.get("data", []):
        try:
            out.append((d["t"], float(d["v"])))
        except (ValueError, TypeError):
            continue
    return out


def fetch_current_surge():
    """Compute current surge (observed - predicted) in ft. None if unavailable."""
    obs = fetch_observed_recent()
    if not obs:
        return None
    # Get predicted at the same hour as the latest observation
    last_obs_time, last_obs_val = obs[-1]
    # Pull predicted for that hour
    data = _get(
        "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter",
        {
            "station": NOAA_STATION,
            "product": "predictions",
            "datum": "MLLW",
            "time_zone": "lst_ldt",
            "units": "english",
            "interval": "h",
            "begin_date": last_obs_time.replace("-", "")[:8] + " " + last_obs_time[11:16],
            "end_date":   last_obs_time.replace("-", "")[:8] + " " + last_obs_time[11:16],
            "format": "json",
        },
    )
    preds = data.get("predictions", [])
    if not preds:
        return None
    return last_obs_val - float(preds[0]["v"])


def fetch_temperature_72h_mean():
    """Mean air temperature past 72h at Sandy Hook (deg F)."""
    end = dt.datetime.now(dt.timezone.utc)
    start = end - dt.timedelta(hours=72)
    data = _get(
        "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter",
        {
            "station": NOAA_STATION,
            "product": "air_temperature",
            "time_zone": "gmt",
            "units": "english",
            "begin_date": start.strftime("%Y%m%d %H:%M"),
            "end_date": end.strftime("%Y%m%d %H:%M"),
            "format": "json",
        },
    )
    temps = []
    for d in data.get("data", []):
        try:
            temps.append(float(d["v"]))
        except (ValueError, TypeError):
            continue
    if not temps:
        return None
    return sum(temps) / len(temps)


def fetch_nws_hourly_forecast():
    """NWS hourly forecast for Highlands. Returns list of dicts with
    startTime, temperature, probabilityOfPrecipitation, etc."""
    pts = _get(f"https://api.weather.gov/points/{HIGHLANDS_LAT},{HIGHLANDS_LON}")
    forecast_url = pts["properties"]["forecastHourly"]
    fc = _get(forecast_url)
    return fc["properties"]["periods"]


# ============================================================
# Model
# ============================================================
def predict_landmark_depths(sandy_hook_peak_mllw, peak_rain_rate_in_hr=0.0,
                            cold_lockout=False):
    """Apply v0.4 model. Returns dict of depths (inches) at each landmark."""
    if cold_lockout and sandy_hook_peak_mllw < 8.0:
        return {
            "curb": 0.0, "road_middle": 0.0,
            "intersection": 0.0, "lawn_step": 0.0,
            "regime": "cold_lockout",
        }

    water_navd88 = sandy_hook_peak_mllw + LOCAL_ENHANCEMENT_FT + MLLW_TO_NAVD88_OFFSET

    d = {
        "curb":         max(0.0, water_navd88 - CURB_TOP)     * 12,
        "road_middle":  max(0.0, water_navd88 - ROAD_MIDDLE)  * 12,
        "intersection": max(0.0, water_navd88 - INTERSECTION) * 12,
        "lawn_step":    max(0.0, water_navd88 - LAWN_STEP)    * 12,
    }

    if peak_rain_rate_in_hr > 0.1:
        rain_add = RAIN_SATURATION_IN * math.tanh(peak_rain_rate_in_hr)
        d["curb"]         += rain_add
        d["road_middle"]  += rain_add
        d["intersection"] += max(0.0, rain_add - 2.0)  # crown sheds some
        d["lawn_step"]    += max(0.0, rain_add - 4.0)  # lawn sheds more

    # Regime label
    if d["curb"] >= ALERT_SEVERE:
        regime = "severe"
    elif d["curb"] >= ALERT_MODERATE:
        regime = "moderate"
    elif d["curb"] >= ALERT_LIGHT:
        regime = "light"
    else:
        regime = "dry"
    d["regime"] = regime
    return d


# ============================================================
# Glue: build today's forecast
# ============================================================
def parse_iso(t):
    return dt.datetime.fromisoformat(t.replace("Z", "+00:00"))


def build_forecast():
    """Pull all inputs, find next high tide, apply model, return dict."""
    predicted = fetch_predicted_tide_24h()
    if not predicted:
        raise RuntimeError("No predicted tide data from NOAA")

    # Find next high tide peak in next 24h (local maximum)
    peak_time, peak_pred = max(predicted, key=lambda x: x[1])

    # Surge: prefer NWS Coastal Flood product if active, else surge persistence
    nws_active = False
    nws_status = "not active"
    forecast_observed_peak = None
    surge = 0.0
    try:
        import nws_surge_parser
        nws_active, projections, _, msg = nws_surge_parser.get_surge_forecast()
        if nws_active and projections:
            # Find highest tide in next 24h from NWS forecast
            now = dt.datetime.now()
            future_24h = [p for p in projections
                          if now <= p["when"] <= now + dt.timedelta(hours=24)]
            if future_24h:
                peak_proj = max(future_24h, key=lambda p: p["total_mllw_ft"])
                forecast_observed_peak = peak_proj["total_mllw_ft"]
                surge = peak_proj["departure_ft"]
                peak_time = peak_proj["when"].strftime("%Y-%m-%d %H:%M")
                nws_status = (f"NWS Coastal Flood forecast: peak "
                              f"{forecast_observed_peak:.2f} ft "
                              f"at {peak_time} (cat: {peak_proj['cat']})")
        elif nws_active:
            nws_status = f"NWS event active but parser failed: {msg}"
    except ImportError:
        nws_status = "parser module not found"
    except Exception as e:
        nws_status = f"NWS fetch error: {e}"

    # Fall back to surge persistence if no NWS forecast available
    if forecast_observed_peak is None:
        surge = fetch_current_surge() or 0.0
        forecast_observed_peak = peak_pred + max(0.0, surge)
        source = "surge-persistence"
    else:
        source = "nws-coastal-flood-product"

    # Rainfall in window around peak tide
    forecast_periods = fetch_nws_hourly_forecast()
    peak_dt = parse_iso(peak_time + "-04:00" if "T" not in peak_time else peak_time)
    # NOAA returns local time; NWS returns ISO. Find NWS periods within +/- 90 min of peak.
    window_start = peak_dt - dt.timedelta(minutes=90)
    window_end   = peak_dt + dt.timedelta(minutes=90)

    peak_rain_rate = 0.0
    for p in forecast_periods[:48]:
        try:
            t = parse_iso(p["startTime"])
        except Exception:
            continue
        if window_start <= t <= window_end:
            # NWS provides probabilityOfPrecipitation, not always a rate.
            # Use 'quantitativePrecipitation' if present, otherwise estimate.
            qp = p.get("quantitativePrecipitation") or {}
            val = qp.get("value")
            if val is not None:
                peak_rain_rate = max(peak_rain_rate, float(val))

    # Cold lockout
    temp_avg = fetch_temperature_72h_mean()
    cold = (temp_avg is not None and temp_avg < COLD_LOCKOUT_F)

    depths = predict_landmark_depths(forecast_observed_peak, peak_rain_rate, cold)

    return {
        "peak_predicted_mllw": peak_pred,
        "peak_forecast_observed_mllw": forecast_observed_peak,
        "peak_time_local": peak_time,
        "current_surge_ft": surge,
        "peak_rain_rate_in_hr": peak_rain_rate,
        "temp_avg_72h_f": temp_avg,
        "cold_lockout": cold,
        "depths_in": depths,
        "surge_source": source,
        "nws_status": nws_status,
    }


# ============================================================
# Email rendering and sending
# ============================================================
def render_email(forecast):
    d = forecast["depths_in"]
    regime = d["regime"]
    peak_t = forecast["peak_time_local"]
    peak_ft = forecast["peak_forecast_observed_mllw"]

    subject = (f"[342 Bay] {regime.upper()}: forecast {peak_ft:.2f} ft "
               f"at {peak_t} (curb {d['curb']:.1f}\")")

    text = f"""\
Bay Ave Barnacle flood forecast for 342 Bay Ave - {dt.date.today().isoformat()}

Next high tide:  {peak_t}
Predicted tide:  {forecast['peak_predicted_mllw']:.2f} ft MLLW (Sandy Hook)
Current surge:   {forecast['current_surge_ft']:+.2f} ft
Forecast peak:   {peak_ft:.2f} ft MLLW
Surge source:    {forecast['surge_source']}
                 ({forecast['nws_status']})
Rain in window:  {forecast['peak_rain_rate_in_hr']:.2f} in/hr peak
72h mean temp:   {forecast['temp_avg_72h_f']:.1f} F
Cold lockout:    {'YES (drains likely ice-locked)' if forecast['cold_lockout'] else 'no'}

PREDICTED DEPTH (inches above each landmark at 342 Bay Ave):
  Curb at walkway (4.16 NAVD88):    {d['curb']:5.1f} in
  Bay Ave road middle (4.36):       {d['road_middle']:5.1f} in
  Intersection center (4.54):       {d['intersection']:5.1f} in
  Lawn / walkway step (4.58):       {d['lawn_step']:5.1f} in

Regime: {regime}

Reference scale (Sandy Hook obs MLLW):
  < 6.6   : dry
  6.6-6.9 : light (curb wet)
  6.9-7.3 : moderate (road covered, intersection still dry)
  7.3-7.6 : water at lawn step
  7.6+    : severe

Model: v0.5. Local enhancement +0.40 ft.
"""

    bg = {"dry": "#e8f5e9", "light": "#fff8e1", "moderate": "#ffe0b2",
          "severe": "#ffcdd2", "cold_lockout": "#e3f2fd"}.get(regime, "#fff")

    html = f"""\
<html><body style="font-family:sans-serif;background:{bg};padding:20px">
<h2>Bay Ave Flood Forecast</h2>
<p><b>{dt.date.today().isoformat()}</b></p>
<p><b>Next high tide:</b> {peak_t}<br>
<b>Forecast peak (obs):</b> {peak_ft:.2f} ft MLLW Sandy Hook
({forecast['peak_predicted_mllw']:.2f} predicted {forecast['current_surge_ft']:+.2f} surge)<br>
<b>Rainfall in window:</b> {forecast['peak_rain_rate_in_hr']:.2f} in/hr peak<br>
<b>72h mean temp:</b> {forecast['temp_avg_72h_f']:.1f}&deg;F
{'(COLD LOCKOUT ACTIVE)' if forecast['cold_lockout'] else ''}</p>

<h3>Predicted depth at 342 Bay Ave landmarks</h3>
<table border="1" cellpadding="8" style="border-collapse:collapse;background:white">
<tr><th align="left">Location</th><th>NAVD88</th><th>Depth (in)</th></tr>
<tr><td>Curb at walkway</td><td>4.16</td><td><b>{d['curb']:.1f}</b></td></tr>
<tr><td>Bay Ave road middle</td><td>4.36</td><td>{d['road_middle']:.1f}</td></tr>
<tr><td>Intersection center</td><td>4.54</td><td>{d['intersection']:.1f}</td></tr>
<tr><td>Lawn/walkway step</td><td>4.58</td><td>{d['lawn_step']:.1f}</td></tr>
</table>

<p><b>Regime: {regime}</b></p>
<p style="font-size:small;color:#666">
Model v0.5. Local enhancement +0.40 ft. Rain term saturates at 8".
Surge persistence is a rough proxy; for active coastal storms, check NWS
Coastal Flood Statement directly.
</p>
</body></html>"""
    return subject, text, html


def render_html_page(forecast):
    """
    Standalone HTML page for GitHub Pages publication.
    Like the email HTML but with proper <head>, mobile meta, and footer
    links to source repo + archive.
    """
    d = forecast["depths_in"]
    regime = d["regime"]
    peak_t = forecast["peak_time_local"]
    peak_ft = forecast["peak_forecast_observed_mllw"]
    today = dt.date.today().isoformat()
    cold = forecast["cold_lockout"]

    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Bay Ave Barnacle — {today}</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
<main>
  <header>
    <h1>Bay Ave Barnacle</h1>
    <p class="subtitle">Hyperlocal flood forecast for 342 Bay Avenue, Highlands NJ</p>
  </header>

  <section class="regime regime-{regime}">
    <div class="regime-label">{regime.upper()}</div>
    <div class="regime-summary">Peak {peak_ft:.2f} ft MLLW at {peak_t}, curb depth {d['curb']:.1f}&Prime;</div>
  </section>

  <section class="forecast">
    <h2>Forecast for {today}</h2>
    <dl>
      <dt>Next high tide</dt><dd>{peak_t}</dd>
      <dt>Predicted tide</dt><dd>{forecast['peak_predicted_mllw']:.2f} ft MLLW (Sandy Hook)</dd>
      <dt>Current surge</dt><dd>{forecast['current_surge_ft']:+.2f} ft</dd>
      <dt>Forecast peak</dt><dd>{peak_ft:.2f} ft MLLW</dd>
      <dt>Surge source</dt><dd>{forecast['surge_source']} <span class="note">({forecast['nws_status']})</span></dd>
      <dt>Peak rainfall</dt><dd>{forecast['peak_rain_rate_in_hr']:.2f} in/hr</dd>
      <dt>72h mean temp</dt><dd>{forecast['temp_avg_72h_f']:.1f}&deg;F</dd>
      <dt>Cold lockout</dt><dd>{'<b>YES</b> (drains likely ice-locked)' if cold else 'no'}</dd>
    </dl>
  </section>

  <section class="landmarks">
    <h2>Predicted depth at landmarks</h2>
    <table>
      <thead><tr><th>Location</th><th>NAVD88</th><th>Depth</th></tr></thead>
      <tbody>
        <tr><td>Curb at walkway</td><td>4.16 ft</td><td><b>{d['curb']:.1f}&Prime;</b></td></tr>
        <tr><td>Bay Ave road middle</td><td>4.36 ft</td><td>{d['road_middle']:.1f}&Prime;</td></tr>
        <tr><td>Intersection center</td><td>4.54 ft</td><td>{d['intersection']:.1f}&Prime;</td></tr>
        <tr><td>Lawn / walkway step</td><td>4.58 ft</td><td>{d['lawn_step']:.1f}&Prime;</td></tr>
      </tbody>
    </table>
  </section>

  <section class="reference">
    <h2>Reference scale</h2>
    <p>Sandy Hook observed water level (MLLW):</p>
    <ul>
      <li>&lt; 6.6 ft — dry</li>
      <li>6.6&ndash;6.9 ft — light (curb wet)</li>
      <li>6.9&ndash;7.3 ft — moderate (road covered, intersection still dry)</li>
      <li>7.3&ndash;7.6 ft — water at lawn step</li>
      <li>&ge; 7.6 ft — severe</li>
    </ul>
  </section>

  <footer>
    <p>Model v0.5. Local enhancement +0.40 ft. Rain term saturates at 8&Prime;.
       Updated daily at 5 AM ET.</p>
    <p><a href="https://github.com/JohnUrban/barnacle">Source code &amp; model</a> &middot;
       <a href="archive/">Past forecasts</a></p>
  </footer>
</main>
</body>
</html>
"""


def send_email(subject, text_body, html_body):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = os.environ["SMTP_FROM"]
    msg["To"] = os.environ["SMTP_TO"]
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", 465))
    user = os.environ["SMTP_USER"]
    pw   = os.environ["SMTP_PASS"]

    with smtplib.SMTP_SSL(host, port) as s:
        s.login(user, pw)
        s.send_message(msg)


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Bay Ave Barnacle — daily flood forecast for 342 Bay Ave, Highlands NJ.",
        epilog="Set SMTP_* environment variables to send email, or use --dry-run to print to stdout."
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the email to stdout instead of sending. Useful for testing.")
    parser.add_argument("--json", action="store_true",
                        help="Print the raw forecast dict as JSON (for debugging).")
    parser.add_argument("--write-html", metavar="PATH", default=None,
                        help="Write standalone HTML page to PATH (e.g. docs/index.html). "
                             "Independent of email sending — can combine with --dry-run.")
    parser.add_argument("--no-send", action="store_true",
                        help="Skip email sending even if SMTP env vars are set. "
                             "Useful when only writing HTML.")
    args = parser.parse_args()

    try:
        forecast = build_forecast()
    except Exception as e:
        print(f"ERROR fetching forecast: {e}", flush=True)
        raise

    if args.json:
        print(json.dumps(forecast, indent=2, default=str))
        return

    subject, text, html = render_email(forecast)

    # Write standalone HTML page if requested
    if args.write_html:
        page_html = render_html_page(forecast)
        out_path = os.path.abspath(args.write_html)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w") as f:
            f.write(page_html)
        print(f"Wrote HTML: {args.write_html}")

    if args.dry_run:
        print("=" * 60)
        print(f"SUBJECT: {subject}")
        print("=" * 60)
        print(text)
        print("=" * 60)
        print("(HTML body suppressed in --dry-run; use --json to see raw data)")
        return

    if args.no_send:
        print("Skipping email send (--no-send set).")
        return

    # Check SMTP env vars before attempting to send
    required = ["SMTP_HOST", "SMTP_USER", "SMTP_PASS", "SMTP_FROM", "SMTP_TO"]
    missing = [v for v in required if v not in os.environ]
    if missing:
        print(f"ERROR: missing environment variables: {', '.join(missing)}", flush=True)
        print("Either set them, or run with --dry-run / --no-send.", flush=True)
        raise SystemExit(2)

    send_email(subject, text, html)
    print(f"Sent: {subject}")


if __name__ == "__main__":
    main()
