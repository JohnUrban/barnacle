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
import csv
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


def fetch_high_tides_24h():
    """Returns list of (time_str, value_mllw_ft) for each HIGH tide in the
    next 24h. Uses NOAA's hilo product which gives exact tide times rather
    than hourly samples. Typically returns 2 entries (~12.5h apart)."""
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
            "interval": "hilo",
            "begin_date": now.strftime("%Y%m%d %H:%M"),
            "end_date": end.strftime("%Y%m%d %H:%M"),
            "format": "json",
        },
    )
    return [
        (p["t"], float(p["v"]))
        for p in data.get("predictions", [])
        if p.get("type") == "H"
    ]


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
# Seasonal context (sourced from history/ project outputs)
# ============================================================
# Resolve relative to this file so the script works regardless of CWD.
_HERE = os.path.dirname(os.path.abspath(__file__))
HISTORY_DATA_DIR = os.path.abspath(os.path.join(_HERE, "..", "history", "data"))

# 1990 is the reference year for "wouldn't have crossed your curb back then"
SLR_REFERENCE_YEAR = 1990


def load_seasonality_row(month):
    """Return current month's row from seasonality_recent.csv (1996-2025).
    None if file missing or row absent — caller degrades gracefully."""
    path = os.path.join(HISTORY_DATA_DIR, "seasonality_recent.csv")
    try:
        with open(path) as f:
            for row in csv.DictReader(f):
                if int(row["month"]) == month:
                    return {
                        "avg_events":   float(row["avg_events_per_month"]),
                        "avg_days":     float(row["avg_flood_days_per_month"]),
                        "avg_hours":    float(row["avg_flood_hours_per_month"]),
                        "descriptor":   row.get("descriptor", ""),
                        "threshold_ft": float(row["threshold_ft"]),
                        "window":       row.get("window", ""),
                    }
    except (FileNotFoundError, KeyError, ValueError):
        return None
    return None


def load_slr_since(reference_year):
    """Return ft of MSL rise from reference_year to most-recent year in
    annual_means.csv. Uses 5-yr smoothing on each end to dampen noise.
    None on failure."""
    path = os.path.join(HISTORY_DATA_DIR, "annual_means.csv")
    try:
        years = {}
        with open(path) as f:
            for row in csv.DictReader(f):
                years[int(row["year"])] = float(row["mean_mllw"])
        if reference_year not in years:
            return None
        recent = max(years.keys())
        # 5-year averages centered on reference and most-recent years
        def avg_window(center, span=2):
            vals = [years[y] for y in range(center - span, center + span + 1) if y in years]
            return sum(vals) / len(vals) if vals else None
        ref = avg_window(reference_year)
        cur = avg_window(recent)
        if ref is None or cur is None:
            return None
        return cur - ref  # ft
    except (FileNotFoundError, KeyError, ValueError):
        return None


CURB_THRESHOLD_SH_MLLW = 6.58   # Sandy Hook obs at which curb at 342 Bay wets


def fetch_mtd_flood_events(threshold=CURB_THRESHOLD_SH_MLLW):
    """Count flood events month-to-date at the Sandy Hook curb threshold
    (6.58 ft MLLW). Pulls NOAA water_level (preliminary 6-min, no lag) from
    month-start to now, aggregates to hourly mean, counts contiguous runs.

    Returns dict with: n_events, n_flood_days, n_hours_above, peak_obs_mllw,
    month_start, as_of.  Returns None on fetch/parse failure.

    Note: water_level is preliminary; values may shift by a few cm when later
    verified. Adequate for a count-of-flood-events display."""
    now = dt.datetime.now(dt.timezone.utc)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    try:
        data = _get(
            "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter",
            {
                "station": NOAA_STATION,
                "product": "water_level",
                "datum": "MLLW",
                "time_zone": "lst_ldt",
                "units": "english",
                "begin_date": start.strftime("%Y%m%d %H:%M"),
                "end_date":   now.strftime("%Y%m%d %H:%M"),
                "format": "json",
            },
        )
    except Exception:
        return None
    rows = data.get("data") or []
    if not rows:
        return None
    # Aggregate 6-min samples to hourly mean (matches historical hourly_height
    # definition more closely than raw 6-min counts).
    by_hour = {}
    for d in rows:
        try:
            ts = d["t"]                  # "YYYY-MM-DD HH:MM"
            v = float(d["v"])
        except (KeyError, ValueError, TypeError):
            continue
        hour_key = ts[:13]               # "YYYY-MM-DD HH"
        by_hour.setdefault(hour_key, []).append(v)
    if not by_hour:
        return None
    sorted_hours = sorted(by_hour.keys())
    hourly_vals = [(h, sum(vs) / len(vs)) for h, vs in by_hour.items()]
    hourly_vals.sort(key=lambda x: x[0])

    n_hours_above = 0
    n_events = 0
    in_event = False
    peak = float("-inf")
    flood_dates = set()
    for h, v in hourly_vals:
        if v > peak:
            peak = v
        above = v >= threshold
        if above:
            n_hours_above += 1
            flood_dates.add(h[:10])
            if not in_event:
                n_events += 1
                in_event = True
        else:
            in_event = False
    return {
        "n_events": n_events,
        "n_flood_days": len(flood_dates),
        "n_hours_above": n_hours_above,
        "peak_obs_mllw": peak if peak > float("-inf") else None,
        "month_start": start.strftime("%Y-%m-%d"),
        "as_of": now.strftime("%Y-%m-%d %H:%M UTC"),
    }


def build_seasonal_context(forecast):
    """Assemble dict of seasonal-context fields for injection into email/HTML.
    Always returns a dict; missing pieces are None or empty. Render code
    should handle absent fields gracefully."""
    today = dt.date.today()
    ctx = {
        "month_name": today.strftime("%B"),
        "season": load_seasonality_row(today.month),
        "mtd": None,
        "slr_ft_since_1990": load_slr_since(SLR_REFERENCE_YEAR),
        "slr_reference_year": SLR_REFERENCE_YEAR,
        "show_slr_line": False,
        "slr_today_peak_ft": forecast.get("peak_forecast_observed_mllw"),
    }
    # MTD count is best-effort; failure shouldn't break the forecast email.
    try:
        ctx["mtd"] = fetch_mtd_flood_events()
    except Exception:
        ctx["mtd"] = None

    # SLR line shows only in the "newly-wet" band: today's peak crosses 6.58
    # but would have been below curb in 1990 (i.e., < 6.58 + slr_since_1990).
    # Also suppress in severe regime (>= 7.5 ft) — SLR isn't the story there.
    peak = ctx["slr_today_peak_ft"]
    slr = ctx["slr_ft_since_1990"]
    if peak is not None and slr is not None and slr > 0:
        ceiling_today = 6.58 + slr
        if 6.58 <= peak < min(ceiling_today, 7.5):
            ctx["show_slr_line"] = True
    return ctx


# ============================================================
# Glue: build today's forecast
# ============================================================
def parse_iso(t):
    return dt.datetime.fromisoformat(t.replace("Z", "+00:00"))


def build_forecast():
    """Pull all inputs, evaluate each high tide in the next 24h, apply model
    to each, return forecast dict with per-tide breakdown and worst-case
    summary."""
    high_tides = fetch_high_tides_24h()
    if not high_tides:
        raise RuntimeError("No high tides returned by NOAA for the next 24h")

    # Time-independent inputs (shared across all tides today)
    temp_avg = fetch_temperature_72h_mean()
    cold = (temp_avg is not None and temp_avg < COLD_LOCKOUT_F)
    nws_hourly = fetch_nws_hourly_forecast()

    # NWS Coastal Flood projections (if any active event)
    nws_active = False
    nws_status = "not active"
    nws_projections = []
    try:
        import nws_surge_parser
        nws_active, nws_projections, _, msg = nws_surge_parser.get_surge_forecast()
        if not nws_active:
            nws_status = "not active"
        elif not nws_projections:
            nws_status = f"NWS event active but parser failed: {msg}"
    except ImportError:
        nws_status = "parser module not found"
    except Exception as e:
        nws_status = f"NWS fetch error: {e}"

    # If NWS not active, fall back to surge persistence (one value, applies to all tides today)
    persisted_surge = None
    if not (nws_active and nws_projections):
        persisted_surge = fetch_current_surge() or 0.0

    # Evaluate each high tide independently
    all_tides = []
    for tide_time, tide_pred in high_tides:
        # Surge for this specific high tide
        surge = 0.0
        forecast_peak = None
        source = None
        try:
            peak_dt = parse_iso(tide_time + "-04:00" if "T" not in tide_time else tide_time)
        except Exception:
            peak_dt = None

        if nws_active and nws_projections and peak_dt is not None:
            # Find NWS projection closest to this high tide (NWS rows are at exact tide times too)
            closest = min(
                nws_projections,
                key=lambda p: abs((p["when"] - peak_dt.replace(tzinfo=None)).total_seconds()),
            )
            # Only use NWS value if it's within 2 hours of this tide
            if abs((closest["when"] - peak_dt.replace(tzinfo=None)).total_seconds()) < 7200:
                forecast_peak = closest["total_mllw_ft"]
                surge = closest["departure_ft"]
                source = "nws-coastal-flood-product"

        if forecast_peak is None:
            # Surge persistence fallback
            surge = persisted_surge if persisted_surge is not None else 0.0
            forecast_peak = tide_pred + max(0.0, surge)
            source = "surge-persistence"

        # Rain in ±90 min of THIS high tide
        peak_rain_rate = 0.0
        if peak_dt is not None:
            window_start = peak_dt - dt.timedelta(minutes=90)
            window_end   = peak_dt + dt.timedelta(minutes=90)
            for p in nws_hourly[:48]:
                try:
                    t = parse_iso(p["startTime"])
                except Exception:
                    continue
                if window_start <= t <= window_end:
                    qp = p.get("quantitativePrecipitation") or {}
                    val = qp.get("value")
                    if val is not None:
                        peak_rain_rate = max(peak_rain_rate, float(val))

        # Depth at landmarks for this tide
        depths = predict_landmark_depths(forecast_peak, peak_rain_rate, cold)

        all_tides.append({
            "time": tide_time,
            "predicted_mllw": tide_pred,
            "surge_ft": surge,
            "forecast_peak_mllw": forecast_peak,
            "peak_rain_in_hr": peak_rain_rate,
            "source": source,
            "depths_in": depths,
        })

    # Identify the worst-case high tide for headline / subject line
    worst = max(all_tides, key=lambda t: t["forecast_peak_mllw"])

    forecast_for_context = {"peak_forecast_observed_mllw": worst["forecast_peak_mllw"]}
    seasonal_context = build_seasonal_context(forecast_for_context)

    return {
        # Headline fields (worst-case tide)
        "peak_predicted_mllw": worst["predicted_mllw"],
        "peak_forecast_observed_mllw": worst["forecast_peak_mllw"],
        "peak_time_local": worst["time"],
        "current_surge_ft": worst["surge_ft"],
        "peak_rain_rate_in_hr": worst["peak_rain_in_hr"],
        "temp_avg_72h_f": temp_avg,
        "cold_lockout": cold,
        "depths_in": worst["depths_in"],
        "surge_source": worst["source"],
        "nws_status": nws_status,
        # New: full breakdown of all high tides in next 24h
        "all_tides": all_tides,
        # Seasonal / SLR context for the email and HTML page
        "seasonal_context": seasonal_context,
    }


# ============================================================
# Seasonal context line builders (shared between email and HTML)
# ============================================================
def _seasonal_context_lines_text(ctx, today=None):
    """Return list of plain-text lines (zero, one, or two) for seasonal /
    SLR context. Each piece is independent — partial failures degrade
    cleanly to fewer lines, never an exception."""
    today = today or dt.date.today()
    lines = []
    season = (ctx or {}).get("season")
    mtd = (ctx or {}).get("mtd")
    if season:
        month_name = today.strftime("%B")
        desc = season.get("descriptor", "")
        avg_days = season.get("avg_days")
        # Window string may already contain parens, e.g. "1996-2025 (30 yrs)".
        # Strip them for cleaner sentence flow.
        window = (season.get("window", "") or "").split(" (")[0]
        if desc in ("wettest month", "quietest month"):
            tag = f" — the {desc} of the year"
        elif desc:
            tag = f" — a {desc} month"
        else:
            tag = ""
        lines.append(
            f"{month_name} typically has ~{avg_days:.1f} flood days at your "
            f"curb (avg over {window}){tag}."
        )
        if mtd:
            peak_str = (f" Peak Sandy Hook so far: {mtd['peak_obs_mllw']:.2f} ft."
                        if mtd.get("peak_obs_mllw") is not None else "")
            lines.append(
                f"So far this {month_name}: {mtd['n_flood_days']} flood days "
                f"({mtd['n_events']} events).{peak_str}"
            )
    if ctx and ctx.get("show_slr_line"):
        slr = ctx["slr_ft_since_1990"]
        peak = ctx["slr_today_peak_ft"]
        ref_year = ctx["slr_reference_year"]
        lines.append(
            f"Sea level at Sandy Hook is ~{slr:.2f} ft higher than in {ref_year}. "
            f"Today's high tide of {peak:.2f} ft wouldn't have crossed your curb "
            f"in {ref_year}; today it does."
        )
    return lines


def _seasonal_context_lines_html(ctx, today=None):
    """Return list of HTML <p> strings for seasonal context."""
    return [f'<p class="context">{line}</p>'
            for line in _seasonal_context_lines_text(ctx, today)]


def _seasonal_context_block_text(forecast):
    """Plain-text block for the email: 'Context: ...' heading + lines, or
    empty string if no context lines."""
    ctx = forecast.get("seasonal_context") or {}
    lines = _seasonal_context_lines_text(ctx)
    if not lines:
        return ""
    return "Context:\n" + "\n".join("  " + line for line in lines) + "\n\n"


def _seasonal_context_block_html(forecast, wrapper="section"):
    """HTML block for the email or page. Returns empty string if no lines."""
    ctx = forecast.get("seasonal_context") or {}
    lines = _seasonal_context_lines_html(ctx)
    if not lines:
        return ""
    if wrapper == "section":
        return ('<section class="context">'
                '<h2>Context</h2>' + "".join(lines) + "</section>")
    # inline (for the email)
    return ('<h3>Context</h3>'
            '<div style="background:white;padding:8px;border-radius:4px">'
            + "".join(lines) + "</div>")


# ============================================================
# Email rendering and sending
# ============================================================
def render_email(forecast):
    d = forecast["depths_in"]
    regime = d["regime"]
    peak_t = forecast["peak_time_local"]
    peak_ft = forecast["peak_forecast_observed_mllw"]
    all_tides = forecast.get("all_tides", [])

    subject = (f"[342 Bay] {regime.upper()}: forecast {peak_ft:.2f} ft "
               f"at {peak_t} (curb {d['curb']:.1f}\")")

    # Format the list of all high tides in next 24h
    tide_lines = []
    for t in all_tides:
        td = t["depths_in"]
        marker = " *" if t["time"] == peak_t else "  "
        tide_lines.append(
            f"{marker}{t['time']}    "
            f"pred {t['predicted_mllw']:5.2f}  "
            f"surge {t['surge_ft']:+5.2f}  "
            f"= {t['forecast_peak_mllw']:5.2f} ft   "
            f"{td['regime']:10s}  curb {td['curb']:4.1f}\""
        )
    tide_block = "\n".join(tide_lines)

    text = f"""\
Bay Ave Barnacle flood forecast for 342 Bay Ave - {dt.date.today().isoformat()}

High tides in next 24h ( * = worst case, headlined below):
{tide_block}

Worst case detail:
  High tide time:  {peak_t}
  Predicted tide:  {forecast['peak_predicted_mllw']:.2f} ft MLLW (Sandy Hook)
  Surge:           {forecast['current_surge_ft']:+.2f} ft
  Forecast peak:   {peak_ft:.2f} ft MLLW
  Surge source:    {forecast['surge_source']}
                   ({forecast['nws_status']})
  Rain in window:  {forecast['peak_rain_rate_in_hr']:.2f} in/hr peak
  72h mean temp:   {forecast['temp_avg_72h_f']:.1f} F
  Cold lockout:    {'YES (drains likely ice-locked)' if forecast['cold_lockout'] else 'no'}

PREDICTED DEPTH at worst-case tide (inches above each landmark at 342 Bay Ave):
  Curb at walkway (4.16 NAVD88):    {d['curb']:5.1f} in
  Bay Ave road middle (4.36):       {d['road_middle']:5.1f} in
  Intersection center (4.54):       {d['intersection']:5.1f} in
  Lawn / walkway step (4.58):       {d['lawn_step']:5.1f} in

Regime: {regime}

{_seasonal_context_block_text(forecast)}\
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

    # Build the all-tides rows for the HTML email
    tide_rows_html = ""
    for t in all_tides:
        td = t["depths_in"]
        is_worst = (t["time"] == peak_t)
        row_style = "background:#ffffcc" if is_worst else ""
        tide_rows_html += (
            f'<tr style="{row_style}">'
            f'<td>{t["time"]}</td>'
            f'<td align="right">{t["predicted_mllw"]:.2f}</td>'
            f'<td align="right">{t["surge_ft"]:+.2f}</td>'
            f'<td align="right"><b>{t["forecast_peak_mllw"]:.2f}</b></td>'
            f'<td align="right">{td["curb"]:.1f}&Prime;</td>'
            f'<td>{td["regime"]}</td>'
            f'</tr>'
        )

    html = f"""\
<html><body style="font-family:sans-serif;background:{bg};padding:20px">
<h2>Bay Ave Flood Forecast</h2>
<p><b>{dt.date.today().isoformat()}</b></p>

<h3>High tides in next 24h</h3>
<table border="1" cellpadding="8" style="border-collapse:collapse;background:white">
<tr><th>Time</th><th>Pred (ft)</th><th>Surge</th><th>Peak (ft)</th><th>Curb</th><th>Regime</th></tr>
{tide_rows_html}
</table>
<p style="font-size:small;color:#666">Highlighted row = worst-case tide, headlined below.</p>

<p><b>Worst case:</b> {peak_t}<br>
<b>Forecast peak (obs):</b> {peak_ft:.2f} ft MLLW Sandy Hook
({forecast['peak_predicted_mllw']:.2f} predicted {forecast['current_surge_ft']:+.2f} surge)<br>
<b>Surge source:</b> {forecast['surge_source']} ({forecast['nws_status']})<br>
<b>Rainfall in window:</b> {forecast['peak_rain_rate_in_hr']:.2f} in/hr peak<br>
<b>72h mean temp:</b> {forecast['temp_avg_72h_f']:.1f}&deg;F
{'(COLD LOCKOUT ACTIVE)' if forecast['cold_lockout'] else ''}</p>

<h3>Depth at 342 Bay Ave landmarks (worst-case tide)</h3>
<table border="1" cellpadding="8" style="border-collapse:collapse;background:white">
<tr><th align="left">Location</th><th>NAVD88</th><th>Depth (in)</th></tr>
<tr><td>Curb at walkway</td><td>4.16</td><td><b>{d['curb']:.1f}</b></td></tr>
<tr><td>Bay Ave road middle</td><td>4.36</td><td>{d['road_middle']:.1f}</td></tr>
<tr><td>Intersection center</td><td>4.54</td><td>{d['intersection']:.1f}</td></tr>
<tr><td>Lawn/walkway step</td><td>4.58</td><td>{d['lawn_step']:.1f}</td></tr>
</table>

<p><b>Regime: {regime}</b></p>
{_seasonal_context_block_html(forecast, wrapper='inline')}
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
    all_tides = forecast.get("all_tides", [])

    # Build the all-tides table rows
    tide_rows = ""
    for t in all_tides:
        td = t["depths_in"]
        is_worst = (t["time"] == peak_t)
        row_class = ' class="worst-tide"' if is_worst else ""
        tide_rows += (
            f'<tr{row_class}>'
            f'<td>{t["time"]}</td>'
            f'<td>{t["predicted_mllw"]:.2f}</td>'
            f'<td>{t["surge_ft"]:+.2f}</td>'
            f'<td><b>{t["forecast_peak_mllw"]:.2f}</b></td>'
            f'<td>{td["curb"]:.1f}&Prime;</td>'
            f'<td>{td["regime"]}</td>'
            f'</tr>'
        )

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
    <div class="regime-summary">Worst-case peak {peak_ft:.2f} ft MLLW at {peak_t}, curb depth {d['curb']:.1f}&Prime;</div>
  </section>

  <section class="tides">
    <h2>High tides in next 24h</h2>
    <table class="tide-table">
      <thead><tr><th>Time</th><th>Pred (ft)</th><th>Surge</th><th>Peak (ft)</th><th>Curb</th><th>Regime</th></tr></thead>
      <tbody>{tide_rows}</tbody>
    </table>
    <p class="note">Highlighted row is the worst case headlined above. Both high tides shown for situational awareness.</p>
  </section>

  <section class="forecast">
    <h2>Worst-case detail</h2>
    <dl>
      <dt>High tide time</dt><dd>{peak_t}</dd>
      <dt>Predicted tide</dt><dd>{forecast['peak_predicted_mllw']:.2f} ft MLLW (Sandy Hook)</dd>
      <dt>Surge</dt><dd>{forecast['current_surge_ft']:+.2f} ft</dd>
      <dt>Forecast peak</dt><dd>{peak_ft:.2f} ft MLLW</dd>
      <dt>Surge source</dt><dd>{forecast['surge_source']} <span class="note">({forecast['nws_status']})</span></dd>
      <dt>Peak rainfall</dt><dd>{forecast['peak_rain_rate_in_hr']:.2f} in/hr</dd>
      <dt>72h mean temp</dt><dd>{forecast['temp_avg_72h_f']:.1f}&deg;F</dd>
      <dt>Cold lockout</dt><dd>{'<b>YES</b> (drains likely ice-locked)' if cold else 'no'}</dd>
    </dl>
  </section>

  <section class="landmarks">
    <h2>Predicted depth at landmarks (worst-case tide)</h2>
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

  {_seasonal_context_block_html(forecast, wrapper='section')}

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

    # SMTP_TO can be comma-separated. If multiple recipients, use Bcc to
    # keep the recipient list private. If a single recipient, keep them in
    # the To: header (clearer, no "undisclosed recipients" weirdness).
    recipients = [r.strip() for r in os.environ["SMTP_TO"].split(",") if r.strip()]
    if len(recipients) <= 1:
        msg["To"] = recipients[0] if recipients else os.environ["SMTP_FROM"]
    else:
        msg["To"] = "Undisclosed recipients:;"
        msg["Bcc"] = ", ".join(recipients)

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
