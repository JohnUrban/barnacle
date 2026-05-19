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

# Landmark elevations at 342 Bay Ave (NAVD88, ft).
# Sandy Hook MLLW threshold for each = landmark + 2.42
# (= +2.82 datum offset − 0.40 local enhancement).
LOWEST_SENTINEL_GRATE = 3.60   # storm grate Central Ave south (lowest seen) (SH 6.02)
LOWEST_ROAD_CORNER    = 3.64   # corner across Bay (early-warning sentinel)  (SH 6.06)
GUTTER_WALKWAY        = 3.78   # street-curb interface at walkway            (SH 6.20)
CORNER_GRATE          = 3.91   # Bay+Central storm grate; Pathway B onset    (SH 6.33)
CURB_TOP           = 4.16   # Bay Ave side at walkway                   (SH 6.58)
ROAD_MIDDLE        = 4.36   # Bay Ave centerline at user's spot         (SH 6.78)
INTERSECTION       = 4.54   # Bay+Central intersection (local high)     (SH 6.96)
LAWN_STEP          = 4.58   # estimated walkway step                    (SH 7.00)
FRONT_PORCH_STEP   = 5.08   # ~6" above lawn step, est. first step      (SH 7.50)
# At and above the porch step we're firmly in direct-inundation territory
# (well above curb), so the +0.40 ft local enhancement — fit primarily from
# drain-backflow-era events at street level — is an extrapolation. The
# offset still holds at the gauge-to-bay level, but the user may want to
# revisit if more extreme-event data accumulates.

# Stratified landmarks (ascending severity). First several are sub-curb
# sentinels for early-warning visual check + parking decisions.
LANDMARKS = [
    ("lowest_sentinel_grate", "Lowest storm grate (Central Ave)", LOWEST_SENTINEL_GRATE, 6.02),
    ("lowest_road_corner",    "Lowest road corner across Bay",    LOWEST_ROAD_CORNER,    6.06),
    ("gutter_walkway",        "Gutter / curb edge at walkway",    GUTTER_WALKWAY,        6.20),
    ("corner_grate",          "Storm grate at Bay+Central",       CORNER_GRATE,          6.33),
    ("curb",                  "Curb at walkway",                  CURB_TOP,              6.58),
    ("road_middle",           "Bay Ave road middle",              ROAD_MIDDLE,           6.78),
    ("intersection",          "Intersection center",              INTERSECTION,          6.96),
    ("lawn_step",             "Lawn / walkway step",              LAWN_STEP,             7.00),
    ("porch_step",            "Front porch first step",           FRONT_PORCH_STEP,      7.50),
]
# Subset used for the "seasonality typical vs MTD" table — curb-and-up only.
# Sub-curb landmarks would dominate the table (counts of 8-12 days/month
# in recent decades); they're shown in the daily depth table instead.
SEASONALITY_LANDMARK_KEYS = {"curb", "road_middle", "intersection",
                             "lawn_step", "porch_step"}
# Curated landmarks for the oscillation chart on the home page (9b.4(b)).
# Six entries — fewer than the full 9 — so labels don't crowd each other
# on the chart's y-axis. Selected by user 2026-05-19.
OSCILLATION_LANDMARK_KEYS = {
    "lowest_sentinel_grate",  # 3.60 — lowest grate
    "gutter_walkway",         # 3.78 — gutter / curb edge
    "corner_grate",           # 3.91 — Bay+Central storm grate
    "curb",                   # 4.16 — curb at walkway
    "lawn_step",              # 4.58 — lawn / walkway step
    "porch_step",             # 5.08 — front porch first step
}

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


# Rollup window: how far into the future to include high tides in the
# main "upcoming tides" rollup table. Increased from 24h → 72h (HANDOFF
# 9b.2 part 2). The home page renders all rows; a JS toggle filters by
# lead-time band (24/48/72h).
ROLLUP_WINDOW_HOURS = 72


def fetch_tides_24h():
    """Returns dict with 'high' and 'low' lists of (time_str, value_mllw_ft)
    for tides in the next ROLLUP_WINDOW_HOURS (currently 72h). The "24h"
    in the name is retained for backwards-compat with the rest of the
    code; the function now fetches a 72h window so the rollup table can
    show 2-3 days ahead with a JS toggle (HANDOFF 9b.2 part 2). Uses
    NOAA's hilo product for exact tide times."""
    now = dt.datetime.now(dt.timezone.utc)
    end = now + dt.timedelta(hours=ROLLUP_WINDOW_HOURS)
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
    preds = data.get("predictions", []) or []
    return {
        "high": [(p["t"], float(p["v"])) for p in preds if p.get("type") == "H"],
        "low":  [(p["t"], float(p["v"])) for p in preds if p.get("type") == "L"],
    }


def fetch_high_tides_24h():
    """Backwards-compatible wrapper returning only high tides as a list."""
    return fetch_tides_24h()["high"]


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


def fetch_surge_swing_6h():
    """Return (max - min) of hourly surge over the past 6h in feet. None on
    failure. Used by the confidence indicator — large swing means surge
    persistence is unreliable as a forecast for the next high tide."""
    end = dt.datetime.now(dt.timezone.utc)
    start = end - dt.timedelta(hours=6)
    obs_rows = fetch_observed_recent()
    if not obs_rows:
        return None
    try:
        data = _get(
            "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter",
            {
                "station": NOAA_STATION,
                "product": "predictions",
                "datum": "MLLW",
                "time_zone": "lst_ldt",
                "units": "english",
                "interval": "h",
                "begin_date": start.strftime("%Y%m%d %H:%M"),
                "end_date":   end.strftime("%Y%m%d %H:%M"),
                "format": "json",
            },
        )
    except Exception:
        return None
    preds = data.get("predictions", []) or []
    if not preds:
        return None
    pred_by_hour = {}
    for p in preds:
        try:
            pred_by_hour[p["t"][:13]] = float(p["v"])
        except (KeyError, ValueError, TypeError):
            continue
    obs_by_hour = {}
    for t, v in obs_rows:
        obs_by_hour.setdefault(t[:13], []).append(v)
    surges = []
    for hour_key, vals in obs_by_hour.items():
        if hour_key in pred_by_hour:
            surges.append((sum(vals) / len(vals)) - pred_by_hour[hour_key])
    if len(surges) < 2:
        return None
    return max(surges) - min(surges)


# Archive + accuracy-log paths resolved relative to this script. Lets the
# daily workflow run from anywhere and still find the right files.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ARCHIVE_DIR        = os.path.join(_REPO_ROOT, "docs", "archive")
ACCURACY_CSV_PATH  = os.path.join(_REPO_ROOT, "data", "forecast_accuracy.csv")
ACCURACY_CSV_FIELDS = [
    "forecast_run_date",
    "forecast_peak_predicted_mllw",
    "forecast_peak_predicted_time",
    "forecast_regime",
    "actual_peak_observed_mllw",
    "actual_peak_observed_time",
    "mllw_error_ft",
]

# Master predictions log — one row per (prediction_made_at, target_tide_time)
# pair. Append-only. HANDOFF 9b.3. From a row's water_navd88_predicted plus
# the static assets/map_points.csv, every landmark depth + regime + map
# visual can be reconstructed.
PREDICTIONS_LOG_PATH = os.path.join(_REPO_ROOT, "data", "predictions_log.csv")
PREDICTIONS_LOG_FIELDS = [
    "prediction_made_at",        # ISO UTC, when this prediction was generated
    "target_tide_time",          # ISO local (NOAA's lst_ldt), the high tide this predicts
    "hours_until_peak",          # signed; negative once peak has passed
    "predicted_mllw_astronomical",  # NOAA hilo astronomical-only prediction
    "surge_ft_predicted",        # signed; ft above/below astronomical
    "surge_source",              # "nws-coastal-flood-product" | "surge-persistence"
    "sh_peak_mllw_predicted",    # astronomical + surge (NOT cold-lockout aware)
    "peak_rain_in_hr_predicted",
    "water_navd88_predicted",    # = sh_peak_mllw + 0.40 + (-2.82); empty if cold lockout
    "regime_predicted",
    "cold_lockout",              # "true" | "false"
    "confidence_level",          # "high" | "medium" | "low" | ""
    "model_version",             # current model spec version (currently v0.6)
]


def _fetch_actual_peak_around(time_str, window_hours=2):
    """Pull NOAA water_level for ±window_hours around a target high-tide
    time, return (peak_mllw, peak_time_str). (None, None) on failure."""
    try:
        center = dt.datetime.strptime(time_str, "%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return (None, None)
    start = center - dt.timedelta(hours=window_hours)
    end = center + dt.timedelta(hours=window_hours)
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
                "end_date":   end.strftime("%Y%m%d %H:%M"),
                "format": "json",
            },
        )
    except Exception:
        return (None, None)
    peak = None
    peak_t = None
    for d in (data.get("data") or []):
        try:
            v = float(d["v"])
        except (KeyError, ValueError, TypeError):
            continue
        if peak is None or v > peak:
            peak = v
            peak_t = d.get("t")
    return (peak, peak_t)


def update_forecast_accuracy():
    """Walk archived JSON forecasts, evaluate any not yet scored against
    actual NOAA observed peaks, append new rows to data/forecast_accuracy.csv.
    Returns a summary dict for rendering, or None when nothing has been
    scored yet.

    Behavior:
    - First runs (no archive yet, no CSV) silently no-op and return None.
    - Each subsequent day: 1 new row appended for yesterday's forecast,
      typically. Idempotent: re-running on the same forecasts won't
      double-count.
    - Stats are computed over the last 30 scored forecasts.
    """
    if not os.path.isdir(ARCHIVE_DIR):
        return None

    existing_dates = set()
    if os.path.exists(ACCURACY_CSV_PATH):
        try:
            with open(ACCURACY_CSV_PATH) as f:
                for row in csv.DictReader(f):
                    if row.get("forecast_run_date"):
                        existing_dates.add(row["forecast_run_date"])
        except OSError:
            pass

    new_rows = []
    today = dt.date.today()
    for fname in sorted(os.listdir(ARCHIVE_DIR)):
        if not fname.endswith(".json"):
            continue
        date_str = fname[:-5]
        try:
            run_date = dt.date.fromisoformat(date_str)
        except ValueError:
            continue
        # Skip today's and future-dated archives (no observed data yet)
        if run_date >= today:
            continue
        if date_str in existing_dates:
            continue
        try:
            with open(os.path.join(ARCHIVE_DIR, fname)) as f:
                fc = json.load(f)
        except Exception:
            continue
        pred_peak = fc.get("peak_forecast_observed_mllw")
        pred_time = fc.get("peak_time_local")
        pred_regime = ((fc.get("depths_in") or {}).get("regime") or "")
        if pred_peak is None or not pred_time:
            continue
        actual_peak, actual_time = _fetch_actual_peak_around(pred_time)
        if actual_peak is None:
            continue
        new_rows.append({
            "forecast_run_date":            date_str,
            "forecast_peak_predicted_mllw": pred_peak,
            "forecast_peak_predicted_time": pred_time,
            "forecast_regime":              pred_regime,
            "actual_peak_observed_mllw":    actual_peak,
            "actual_peak_observed_time":    actual_time or "",
            "mllw_error_ft":                pred_peak - actual_peak,
        })

    if new_rows:
        os.makedirs(os.path.dirname(ACCURACY_CSV_PATH), exist_ok=True)
        write_header = not os.path.exists(ACCURACY_CSV_PATH)
        with open(ACCURACY_CSV_PATH, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=ACCURACY_CSV_FIELDS)
            if write_header:
                writer.writeheader()
            for row in new_rows:
                writer.writerow(row)

    return _summarize_accuracy(last_n=30)


CURRENT_MODEL_VERSION = "v0.6"


def append_predictions_log(forecast):
    """Append one row per upcoming high tide in `forecast` to the master
    predictions log. Append-only — never rewrites or sorts existing rows.

    HANDOFF 9b.3. Stable column set; we add columns over time but don't
    remove or rename them. From a row's water_navd88_predicted plus the
    static assets/map_points.csv, every landmark depth + regime + map
    visual is reconstructible.

    Called once per forecast run (daily today; hourly when 9b.1 ships).
    Safe to call multiple times — each call appends rows, no dedup; if
    we ever want dedup, do it in a consumer rather than the writer.
    """
    now_utc = dt.datetime.now(dt.timezone.utc)
    now_iso = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    cold = bool(forecast.get("cold_lockout", False))
    confidence_level = forecast.get("confidence_level", "") or ""

    rows_to_write = []
    for t in forecast.get("all_tides", []) or []:
        target_time = t.get("time") or ""
        sh_peak = t.get("forecast_peak_mllw")
        # Hours until peak (signed). Tide times are local lst_ldt
        # ("YYYY-MM-DD HH:MM"); attach EDT (-04:00) for parsing.
        hours_until_peak = ""
        if target_time:
            try:
                target_dt = dt.datetime.strptime(target_time, "%Y-%m-%d %H:%M")
                # Treat as US East tz-naive; convert to UTC for comparison.
                # During EDT this is UTC-4. (Workflow ignores DST nuance —
                # close enough for "hours until peak" granularity.)
                target_utc = target_dt + dt.timedelta(hours=4)
                hours_until_peak = (
                    target_utc.replace(tzinfo=dt.timezone.utc) - now_utc
                ).total_seconds() / 3600.0
                hours_until_peak = f"{hours_until_peak:+.2f}"
            except (ValueError, TypeError):
                pass

        # Water level (NAVD88) — empty when cold lockout suppresses flooding.
        water_navd88 = ""
        if sh_peak is not None and not (cold and sh_peak < 8.0):
            water_navd88 = (
                sh_peak + LOCAL_ENHANCEMENT_FT + MLLW_TO_NAVD88_OFFSET
            )
            water_navd88 = f"{water_navd88:.3f}"

        regime = ""
        depths = t.get("depths_in")
        if isinstance(depths, dict):
            regime = depths.get("regime", "")

        rows_to_write.append({
            "prediction_made_at":         now_iso,
            "target_tide_time":           target_time,
            "hours_until_peak":           hours_until_peak,
            "predicted_mllw_astronomical":
                f"{t.get('predicted_mllw'):.3f}" if t.get("predicted_mllw") is not None else "",
            "surge_ft_predicted":
                f"{t.get('surge_ft'):+.3f}" if t.get("surge_ft") is not None else "",
            "surge_source":               t.get("source", "") or "",
            "sh_peak_mllw_predicted":
                f"{sh_peak:.3f}" if sh_peak is not None else "",
            "peak_rain_in_hr_predicted":
                f"{t.get('peak_rain_in_hr'):.3f}" if t.get("peak_rain_in_hr") is not None else "",
            "water_navd88_predicted":     water_navd88,
            "regime_predicted":           regime,
            "cold_lockout":               "true" if cold else "false",
            "confidence_level":           confidence_level,
            "model_version":              CURRENT_MODEL_VERSION,
        })

    if not rows_to_write:
        return

    os.makedirs(os.path.dirname(PREDICTIONS_LOG_PATH), exist_ok=True)
    write_header = not os.path.exists(PREDICTIONS_LOG_PATH)
    with open(PREDICTIONS_LOG_PATH, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=PREDICTIONS_LOG_FIELDS)
        if write_header:
            writer.writeheader()
        for r in rows_to_write:
            writer.writerow(r)
    print(f"Appended {len(rows_to_write)} row(s) to "
          f"{os.path.relpath(PREDICTIONS_LOG_PATH, _REPO_ROOT)}")


def _summarize_accuracy(last_n=30):
    """Compute summary stats over the most-recent N scored rows. Returns
    None when no rows have been scored yet."""
    if not os.path.exists(ACCURACY_CSV_PATH):
        return None
    errors = []
    pairs = []
    try:
        with open(ACCURACY_CSV_PATH) as f:
            for row in csv.DictReader(f):
                try:
                    e = float(row["mllw_error_ft"])
                except (KeyError, ValueError, TypeError):
                    continue
                errors.append(e)
                pairs.append({
                    "date":   row.get("forecast_run_date", ""),
                    "pred":   row.get("forecast_peak_predicted_mllw", ""),
                    "actual": row.get("actual_peak_observed_mllw", ""),
                    "err":    e,
                })
    except OSError:
        return None
    if not errors:
        return None
    recent = errors[-last_n:]
    return {
        "n_scored_total":     len(errors),
        "n_scored_recent":    len(recent),
        "mean_error_ft":      sum(recent) / len(recent),
        "mean_abs_error_ft":  sum(abs(e) for e in recent) / len(recent),
        "max_abs_error_ft":   max(abs(e) for e in recent),
        "recent_window":      last_n,
    }


# Look-ahead window for the "dates to watch" section (HANDOFF 9b.7).
# 45 days is well past NOAA tide_predictions reliability and gives the user
# ~6 weeks of planning visibility. Astronomical only — surge isn't forecast
# this far out.
LOOKAHEAD_DAYS = 45

# Thresholds for flagging an upcoming high tide. Each entry is
# (sh_mllw_threshold, label_for_user, css_severity_class). Sorted high to
# low; the FIRST threshold a tide crosses defines its row's styling.
LOOKAHEAD_THRESHOLDS = [
    (7.00, "would cross lawn step (no surge needed)",       "watch-severe"),
    (6.58, "would cross curb (no surge needed)",             "watch-moderate"),
    (6.20, "would reach gutter (no surge needed)",           "watch-light"),
    (6.00, "elevated tide — flooding likely with any surge", "watch-minor"),
]


def fetch_high_tides_lookahead(days=LOOKAHEAD_DAYS):
    """Pull NOAA `predictions` hilo for the next `days` days. Returns list of
    (time_str, mllw_ft) for high tides only. Astronomical only — no surge.
    Larger window than fetch_tides_24h; used for HANDOFF 9b.7."""
    now = dt.datetime.now(dt.timezone.utc)
    end = now + dt.timedelta(days=days)
    try:
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
                "end_date":   end.strftime("%Y%m%d %H:%M"),
                "format": "json",
            },
        )
    except Exception:
        return []
    preds = data.get("predictions") or []
    out = []
    for p in preds:
        if p.get("type") != "H":
            continue
        try:
            out.append((p["t"], float(p["v"])))
        except (KeyError, ValueError, TypeError):
            continue
    return out


def build_lookahead_watch_dates(high_tides, skip_first_hours=24):
    """Filter upcoming high tides to the "dates to watch" rows for the
    look-ahead section.

    Rules:
    - Skip tides within `skip_first_hours` of now (those are already
      shown in the next-24h rollup).
    - For each day, keep only the *highest* tide (one row per date max).
    - Drop tides below the lowest threshold (6.00 ft MLLW).
    - Tag each row with the highest threshold it crosses.

    Returns list of dicts:
        {time, time_dt, mllw, threshold_mllw, label, severity_class}
    sorted by time.
    """
    now_utc = dt.datetime.now(dt.timezone.utc)
    cutoff = now_utc + dt.timedelta(hours=skip_first_hours)
    lowest_threshold = min(t[0] for t in LOOKAHEAD_THRESHOLDS)

    per_day_best = {}  # date_str -> (time_str, mllw, datetime)
    for time_str, mllw in high_tides:
        if mllw < lowest_threshold:
            continue
        try:
            tide_dt = dt.datetime.strptime(time_str, "%Y-%m-%d %H:%M")
            # NOAA times are lst_ldt (EDT = UTC-4 in summer); rough UTC
            # conversion is good enough for the "skip the next 24h"
            # boundary, which doesn't need second-precision.
            tide_utc = (tide_dt + dt.timedelta(hours=4)).replace(
                tzinfo=dt.timezone.utc
            )
        except (ValueError, TypeError):
            continue
        if tide_utc < cutoff:
            continue
        date_str = tide_dt.date().isoformat()
        prior = per_day_best.get(date_str)
        if prior is None or mllw > prior[1]:
            per_day_best[date_str] = (time_str, mllw, tide_dt)

    rows = []
    for date_str, (time_str, mllw, tide_dt) in per_day_best.items():
        # Find the highest threshold this tide crosses
        for threshold, label, css_class in LOOKAHEAD_THRESHOLDS:
            if mllw >= threshold:
                rows.append({
                    "time":           time_str,
                    "time_dt":        tide_dt,
                    "mllw":           mllw,
                    "threshold_mllw": threshold,
                    "label":          label,
                    "severity_class": css_class,
                })
                break
    rows.sort(key=lambda r: r["time_dt"])
    return rows


def fetch_recent_history(days=7):
    """Past N days of observed daily peak water level, with the highest
    landmark reached at that peak. Returns list of dicts (one per calendar
    day), sorted chronologically. Empty list on failure."""
    end = dt.datetime.now(dt.timezone.utc)
    start = end - dt.timedelta(days=days)
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
                "end_date":   end.strftime("%Y%m%d %H:%M"),
                "format": "json",
            },
        )
    except Exception:
        return []
    rows = data.get("data") or []
    if not rows:
        return []
    # Track max per day with timestamp
    by_day = {}
    for d in rows:
        try:
            t = d["t"]; v = float(d["v"])
        except (KeyError, ValueError, TypeError):
            continue
        day = t[:10]
        if day not in by_day or v > by_day[day][1]:
            by_day[day] = (t, v)
    # Classify by highest landmark reached + always report relative-to-lowest
    sorted_lm = sorted(LANDMARKS, key=lambda x: x[2])
    lowest_elev = sorted_lm[0][2]  # LOWEST_ROAD_CORNER (3.64 NAVD88)
    out = []
    for day in sorted(by_day.keys()):
        t, peak = by_day[day]
        water_navd88 = peak + LOCAL_ENHANCEMENT_FT + MLLW_TO_NAVD88_OFFSET
        relative_in = (water_navd88 - lowest_elev) * 12  # always: positive or negative
        highest_key = None
        for key, _label, elev, _sh in sorted_lm:
            if water_navd88 >= elev:
                highest_key = key
        if highest_key:
            short = LANDMARK_SHORT_LABELS.get(highest_key, highest_key)
            highest_elev = next(elev for key, _l, elev, _s in sorted_lm if key == highest_key)
            inches = (water_navd88 - highest_elev) * 12
            classification = f"{short} +{inches:.1f}\""
        else:
            classification = "dry"
        out.append({
            "date":             day,
            "peak_time":        t,
            "peak_mllw":        peak,
            "rel_in":           relative_in,
            "highest_landmark": classification,
        })
    return out


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
    """Apply v0.6 model. Returns dict of depths (inches) at each landmark."""
    zero_dict = {key: 0.0 for key, *_ in LANDMARKS}
    if cold_lockout and sandy_hook_peak_mllw < 8.0:
        return {**zero_dict, "regime": "cold_lockout"}

    water_navd88 = sandy_hook_peak_mllw + LOCAL_ENHANCEMENT_FT + MLLW_TO_NAVD88_OFFSET

    d = {key: max(0.0, water_navd88 - elev) * 12
         for key, _label, elev, _sh in LANDMARKS}

    if peak_rain_rate_in_hr > 0.1:
        rain_add = RAIN_SATURATION_IN * math.tanh(peak_rain_rate_in_hr)
        # Sub-curb landmarks: full rain add. Water collects on the street
        # from sheet-flow off Waterwitch + river backup, then pools to
        # gutter level. Same physics as at the curb.
        d["lowest_sentinel_grate"] += rain_add
        d["lowest_road_corner"]    += rain_add
        d["gutter_walkway"]        += rain_add
        d["corner_grate"]          += rain_add
        d["curb"]                  += rain_add
        d["road_middle"]        += rain_add
        d["intersection"]       += max(0.0, rain_add - 2.0)  # crown sheds some
        d["lawn_step"]          += max(0.0, rain_add - 4.0)  # lawn sheds more
        # Porch step receives rain via flash-flood from up-slope
        # (Waterwitch Ave et al.) + river backup — same mechanism as the
        # lawn step. Calibrated to Oct 30 2025: SH 7.57 + 1.45 in/hr rain →
        # user observed water rising to the porch first step.
        d["porch_step"]         += max(0.0, rain_add - 4.0)

    # Regime label (subject-line summary). Order matters: severe is most
    # alarming. STREET sits between DRY and LIGHT — sub-curb water present
    # (parking-relevant, but not at your property's curb top).
    if d["curb"] >= ALERT_SEVERE:
        regime = "severe"
    elif d["curb"] >= ALERT_MODERATE:
        regime = "moderate"
    elif d["curb"] >= ALERT_LIGHT:
        regime = "light"
    elif d["curb"] > 0:
        regime = "light"  # any curb-top water is light, don't underreport
    elif (d["gutter_walkway"] > 0 or d["lowest_road_corner"] > 0 or
          d["lowest_sentinel_grate"] > 0):
        regime = "street"  # sub-curb water — early warning / parking caution
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


def load_seasonality_strata(month):
    """Return list of seasonality rows for the given calendar month, one
    per stratum (ascending threshold). Empty list on failure — caller
    degrades gracefully."""
    path = os.path.join(HISTORY_DATA_DIR, "seasonality_recent.csv")
    out = []
    try:
        with open(path) as f:
            for row in csv.DictReader(f):
                if int(row["month"]) != month:
                    continue
                out.append({
                    "landmark_key":   row.get("landmark_key", ""),
                    "landmark_label": row.get("landmark_label", ""),
                    "threshold_ft":   float(row["threshold_ft"]),
                    "avg_events":     float(row["avg_events_per_month"]),
                    "avg_days":       float(row["avg_flood_days_per_month"]),
                    "avg_hours":      float(row["avg_flood_hours_per_month"]),
                    "descriptor":     row.get("descriptor", ""),
                    "window":         row.get("window", ""),
                })
    except (FileNotFoundError, KeyError, ValueError):
        return []
    out.sort(key=lambda r: r["threshold_ft"])
    return out


def load_monthly_peak_percentile(peak_mllw, month):
    """Look up where peak_mllw falls in the historical daily-peak
    distribution for the given calendar month (1996-2025). Returns
    a percentile description ('top 1%' / 'top 5%' / 'top 10%' / 'top 25%'
    / 'median' / 'below median') and the underlying p* threshold dict.
    None on lookup failure (CSV missing, month absent)."""
    path = os.path.join(HISTORY_DATA_DIR, "monthly_peak_percentiles.csv")
    try:
        row = None
        with open(path) as f:
            for r in csv.DictReader(f):
                if int(r["month"]) == month:
                    row = r
                    break
        if row is None:
            return None
        p = {k: float(row[k]) for k in
             ("p25_mllw", "p50_mllw", "p75_mllw", "p90_mllw",
              "p95_mllw", "p99_mllw", "max_mllw")}
    except (FileNotFoundError, KeyError, ValueError):
        return None
    if peak_mllw >= p["p99_mllw"]:
        label = "top 1%"
    elif peak_mllw >= p["p95_mllw"]:
        label = "top 5%"
    elif peak_mllw >= p["p90_mllw"]:
        label = "top 10%"
    elif peak_mllw >= p["p75_mllw"]:
        label = "top 25%"
    elif peak_mllw >= p["p50_mllw"]:
        label = "above median"
    else:
        label = "below median"
    p["label"] = label
    p["window"] = row.get("window", "")
    return p


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


def fetch_mtd_flood_events():
    """Pull NOAA water_level month-to-date and return flood counts at each
    of the 5 landmark thresholds.

    Returns dict with:
        peak_obs_mllw : float
        month_start, as_of : str
        strata : list of {threshold_ft, n_events, n_flood_days, n_hours_above},
                 sorted ascending by threshold.
    Returns None on fetch/parse failure.

    Note: water_level is preliminary; values may shift by a few cm when later
    verified. Adequate for a count display."""
    thresholds = [t for _k, _l, _e, t in LANDMARKS]
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

    # Also track the highest single 6-min reading + its time. The hourly
    # mean used above can mask brief curb-grazing events (e.g., a 15-20 min
    # tide peak that crosses 6.58 but pulls the hourly mean back below).
    # Surfacing these as "near-miss" context avoids the user wondering
    # whether MTD = 0 means "nothing happened" or "almost happened."
    raw_peak_v = float("-inf")
    raw_peak_t = None
    raw_minutes_above_curb = 0
    for d in rows:
        try:
            v = float(d["v"]); t_str = d["t"]
        except (KeyError, ValueError, TypeError):
            continue
        if v > raw_peak_v:
            raw_peak_v = v; raw_peak_t = t_str
        if v >= 6.58:
            raw_minutes_above_curb += 6  # 6-min sample cadence

    # Pass through each threshold and tally events, flood days, hours.
    peak = float("-inf")
    strata_out = []
    for t in thresholds:
        n_hours_above = 0
        n_events = 0
        in_event = False
        flood_dates = set()
        for h, v in hourly_vals:
            if v > peak:
                peak = v
            above = v >= t
            if above:
                n_hours_above += 1
                flood_dates.add(h[:10])
                if not in_event:
                    n_events += 1
                    in_event = True
            else:
                in_event = False
        strata_out.append({
            "threshold_ft":   t,
            "n_events":       n_events,
            "n_flood_days":   len(flood_dates),
            "n_hours_above":  n_hours_above,
        })
    return {
        "peak_obs_mllw":     peak if peak > float("-inf") else None,
        "peak_6min_mllw":    raw_peak_v if raw_peak_v > float("-inf") else None,
        "peak_6min_time":    raw_peak_t,
        "minutes_above_curb": raw_minutes_above_curb,
        "month_start":       start.strftime("%Y-%m-%d"),
        "as_of":             now.strftime("%Y-%m-%d %H:%M UTC"),
        "strata":            strata_out,
    }


def build_seasonal_context(forecast):
    """Assemble dict of seasonal-context fields for injection into email/HTML.
    Always returns a dict; missing pieces are None or empty. Render code
    should handle absent fields gracefully."""
    today = dt.date.today()
    ctx = {
        "month_name": today.strftime("%B"),
        "strata": load_seasonality_strata(today.month),  # list, possibly empty
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
    tides = fetch_tides_24h()
    high_tides = tides["high"]
    low_tides = tides["low"]
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

        # Rain in ±90 min of THIS high tide (used by the v0.6 model)
        # plus a wider ±3h hourly profile for the email's rain-timing block.
        peak_rain_rate = 0.0
        rain_window = []  # list of (hours_offset_from_high_tide, rain_rate_in_hr)
        peak_rain_offset_h = None
        if peak_dt is not None:
            window_start = peak_dt - dt.timedelta(minutes=90)
            window_end   = peak_dt + dt.timedelta(minutes=90)
            wider_start  = peak_dt - dt.timedelta(hours=3)
            wider_end    = peak_dt + dt.timedelta(hours=3)
            for p in nws_hourly[:96]:
                try:
                    tt = parse_iso(p["startTime"])
                except Exception:
                    continue
                qp = p.get("quantitativePrecipitation") or {}
                val = qp.get("value")
                if val is None:
                    continue
                rate = float(val)
                if window_start <= tt <= window_end:
                    if rate > peak_rain_rate:
                        peak_rain_rate = rate
                        peak_rain_offset_h = (tt - peak_dt).total_seconds() / 3600.0
                if wider_start <= tt <= wider_end:
                    off_h = (tt - peak_dt).total_seconds() / 3600.0
                    rain_window.append((off_h, rate))

        # Depth at landmarks for this tide
        depths = predict_landmark_depths(forecast_peak, peak_rain_rate, cold)

        # Hours from "now" to this tide's peak (positive = future, negative
        # = already passed). Used by the JS duration toggle (HANDOFF 9b.2
        # part 2) to hide rows past the user-selected window.
        hours_from_now = None
        if peak_dt is not None:
            now_utc = dt.datetime.now(dt.timezone.utc)
            try:
                hours_from_now = (
                    peak_dt - now_utc.replace(tzinfo=peak_dt.tzinfo)
                ).total_seconds() / 3600.0
            except Exception:
                hours_from_now = None

        all_tides.append({
            "time": tide_time,
            "predicted_mllw": tide_pred,
            "surge_ft": surge,
            "forecast_peak_mllw": forecast_peak,
            "peak_rain_in_hr": peak_rain_rate,
            "peak_rain_offset_h": peak_rain_offset_h,
            "rain_window_3h": sorted(rain_window),  # (offset_h, in/hr) pairs
            "source": source,
            "depths_in": depths,
            "hours_from_now": hours_from_now,
        })

    # Identify the worst-case high tide for headline / subject line
    worst = max(all_tides, key=lambda t: t["forecast_peak_mllw"])

    forecast_for_context = {"peak_forecast_observed_mllw": worst["forecast_peak_mllw"]}
    seasonal_context = build_seasonal_context(forecast_for_context)

    # Cumulative rain over the next 24h (from NWS hourly forecast). Used in
    # the rain-timing block.
    cumulative_rain_24h = 0.0
    now_utc = dt.datetime.now(dt.timezone.utc)
    cutoff = now_utc + dt.timedelta(hours=24)
    for p in nws_hourly[:48]:
        try:
            tt = parse_iso(p["startTime"])
        except Exception:
            continue
        if tt < now_utc or tt > cutoff:
            continue
        qp = p.get("quantitativePrecipitation") or {}
        val = qp.get("value")
        if val is not None:
            cumulative_rain_24h += float(val)

    # Confidence indicator inputs
    surge_swing = fetch_surge_swing_6h()
    # Recent-history recap (last 7 days of observed daily peaks)
    try:
        recent_history = fetch_recent_history(days=7)
    except Exception:
        recent_history = []

    # Look-ahead "dates to watch" — astronomical only, 45 days out (9b.7)
    try:
        lookahead_highs = fetch_high_tides_lookahead(LOOKAHEAD_DAYS)
        lookahead_watch = build_lookahead_watch_dates(lookahead_highs)
    except Exception:
        lookahead_watch = []

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
        # Low tides in next 24h: list of {time, value_mllw}
        "low_tides": [{"time": t, "value_mllw": v} for t, v in low_tides],
        # Seasonal / SLR context for the email and HTML page
        "seasonal_context": seasonal_context,
        # Rain summary across next 24h
        "cumulative_rain_24h_in": cumulative_rain_24h,
        # Confidence indicator inputs (level computed below after assembly)
        "surge_swing_6h_ft": surge_swing,
        # Recent observed peaks for the recap block
        "recent_history_7d": recent_history,
        # Look-ahead "dates to watch" — astronomical only (HANDOFF 9b.7)
        "lookahead_watch": lookahead_watch,
    }


def _confidence_uncertainty_ft(level):
    """Estimated ±uncertainty in SH peak MLLW (ft) for each confidence
    level. Rough heuristic — should eventually be data-driven from
    `data/predictions_log.csv` joined to observed peaks (9b.8).

    Used by 9b.6 confidence refinement to translate the abstract
    "LOW confidence" badge into a concrete "peak ± X ft" range that
    can be propagated to a regime band.
    """
    return {
        "high":   0.10,
        "medium": 0.30,
        "low":    0.50,
    }.get(level, 0.30)


def _compute_regime_band(forecast, uncertainty_ft):
    """Given the worst-tide forecast and a ±uncertainty in SH peak MLLW,
    return (lo_regime, hi_regime) — the regime range that results when
    the peak slides within ±uncertainty.

    Returns None when both bounds resolve to the same regime (no
    useful band to display).
    """
    peak = forecast.get("peak_forecast_observed_mllw")
    if peak is None or uncertainty_ft <= 0:
        return None
    cold = bool(forecast.get("cold_lockout", False))
    rain = forecast.get("peak_rain_rate_in_hr", 0.0) or 0.0
    lo_peak = max(0.0, peak - uncertainty_ft)
    hi_peak = peak + uncertainty_ft
    try:
        lo_regime = predict_landmark_depths(lo_peak, rain, cold).get("regime")
        hi_regime = predict_landmark_depths(hi_peak, rain, cold).get("regime")
    except Exception:
        return None
    if not lo_regime or not hi_regime or lo_regime == hi_regime:
        return None
    return (lo_regime, hi_regime)


def _attach_summary_and_confidence(forecast):
    """Compute plain-language summary + confidence + unusual-forecast flag
    + forecast-accuracy summary after the forecast dict is otherwise
    complete."""
    level, reason = assess_confidence(forecast)
    forecast["confidence_level"] = level
    forecast["confidence_reason"] = reason
    forecast["confidence_uncertainty_ft"] = _confidence_uncertainty_ft(level)
    forecast["confidence_regime_band"] = _compute_regime_band(
        forecast, forecast["confidence_uncertainty_ft"]
    )
    forecast["plain_language_summary"] = plain_language_summary(forecast)
    # Unusual-forecast flag (HANDOFF 16e): where does today's peak sit in
    # the 1996-2025 distribution of daily peaks for this calendar month?
    peak = forecast.get("peak_forecast_observed_mllw")
    month = dt.date.today().month
    if peak is not None:
        forecast["peak_percentile"] = load_monthly_peak_percentile(peak, month)
    # Accuracy log (HANDOFF 8b): score any archived forecasts not yet
    # compared against actual observed peaks; attach summary stats.
    try:
        forecast["accuracy_summary"] = update_forecast_accuracy()
    except Exception:
        forecast["accuracy_summary"] = None
    return forecast


# ============================================================
# Seasonal context line builders (shared between email and HTML)
# ============================================================
def _unusual_forecast_text(forecast):
    """One-line note when today's predicted peak is unusually high for the
    current calendar month. Returns None when forecast is median-or-below
    (suppresses noise on routine days)."""
    p = forecast.get("peak_percentile") or {}
    label = p.get("label", "")
    if label not in ("top 1%", "top 5%", "top 10%", "top 25%"):
        return None
    peak = forecast.get("peak_forecast_observed_mllw")
    month_name = dt.date.today().strftime("%B")
    return (f"Note: today's forecast peak ({peak:.2f} ft) is in the {label} "
            f"of historical daily peaks for {month_name} (1996-2025).")


def _confidence_qualifier_sentences(forecast):
    """Build the second-and-third clauses for the confidence line:
    (1) what the confidence is *about* (peak magnitude, ± uncertainty)
    (2) the regime range that uncertainty implies, when non-trivial.

    Returns a list of plain strings (no markup). Empty list when there's
    nothing meaningful to add (high confidence, or cold lockout, or
    insufficient data).

    Addresses HANDOFF 9b.6 — the user pointed out that "Confidence: LOW"
    on a DRY day is ambiguous without spelling out *what* is uncertain.
    """
    level = forecast.get("confidence_level") or ""
    if level == "high":
        return []
    peak = forecast.get("peak_forecast_observed_mllw")
    unc = forecast.get("confidence_uncertainty_ft")
    if peak is None or not unc:
        return []
    out = [
        f"This is uncertainty about the peak Sandy Hook level "
        f"({peak:.2f} ft MLLW), which could land within roughly "
        f"±{unc:.1f} ft of the forecast."
    ]
    band = forecast.get("confidence_regime_band")
    if band:
        lo, hi = band
        out.append(
            f"Depending on which way it resolves, the regime could be "
            f"anywhere from {lo.upper()} to {hi.upper()}."
        )
    return out


def _render_summary_text(forecast):
    """One-line plain-language summary, plus confidence + unusual-forecast
    note (when applicable) on their own lines."""
    out = []
    summary = forecast.get("plain_language_summary") or ""
    if summary:
        out.append(summary)
    level = forecast.get("confidence_level")
    reason = forecast.get("confidence_reason") or ""
    if level:
        # Primary line: badge + reason
        out.append(f"Confidence: {level.upper()} — {reason}")
        # Augment lines for non-high confidence (HANDOFF 9b.6)
        for extra in _confidence_qualifier_sentences(forecast):
            out.append(f"  {extra}")
    unusual = _unusual_forecast_text(forecast)
    if unusual:
        out.append(unusual)
    return out


def _render_summary_html(forecast):
    """HTML version: summary + confidence + optional unusual-forecast note
    inside a styled banner."""
    summary = forecast.get("plain_language_summary") or ""
    level = forecast.get("confidence_level") or ""
    reason = forecast.get("confidence_reason") or ""
    unusual = _unusual_forecast_text(forecast)
    if not summary and not level and not unusual:
        return ""
    parts = ['<section class="tldr">']
    if summary:
        parts.append(f'<p class="tldr-summary">{summary}</p>')
    if level:
        # Primary confidence line: badge + reason
        confidence_html = (
            f'<p class="tldr-confidence confidence-{level}">'
            f'<b>Confidence: {level.upper()}</b> &mdash; '
            f'<span>{reason}</span>'
        )
        # Augment with qualifier sentences for non-high confidence (9b.6)
        for extra in _confidence_qualifier_sentences(forecast):
            confidence_html += f'<br><span class="confidence-qualifier">{extra}</span>'
        confidence_html += "</p>"
        parts.append(confidence_html)
    if unusual:
        parts.append(f'<p class="tldr-unusual">{unusual}</p>')
    parts.append('</section>')
    return "".join(parts)


def _rain_is_notable(forecast):
    """True if there's enough rain in the next 24 h to warrant a rain block.
    Threshold deliberately low (0.05 in cumulative) so even minor wet weather
    surfaces — these are the events where timing relative to tide matters."""
    return (forecast.get("cumulative_rain_24h_in") or 0) >= 0.05 or any(
        (t.get("peak_rain_in_hr") or 0) >= 0.05
        for t in (forecast.get("all_tides") or [])
    )


def _render_rain_timing_text(forecast):
    """Plain-text rain timing block. Empty list when no rain is expected."""
    if not _rain_is_notable(forecast):
        return []
    cum = forecast.get("cumulative_rain_24h_in") or 0
    lines = ["Rain & tide timing:"]
    lines.append(f"  Cumulative next 24 h: {cum:.2f}\"")
    peak_t = forecast.get("peak_time_local")
    for t in (forecast.get("all_tides") or []):
        peak_rain = t.get("peak_rain_in_hr") or 0
        offset = t.get("peak_rain_offset_h")
        label = "★ peak tide" if t["time"] == peak_t else "lower high"
        when = t["time"][-5:]
        if peak_rain <= 0.005:
            lines.append(f"  {when} ({label}): no rain in ±90 min window")
            continue
        if offset is None:
            timing = "during the window"
        elif abs(offset) < 0.25:
            timing = "at the high tide"
        elif offset < 0:
            timing = f"{abs(offset):.0f} h before high tide"
        else:
            timing = f"{offset:.0f} h after high tide"
        lines.append(f"  {when} ({label}): peak {peak_rain:.2f} in/hr {timing}")
    return lines


def _render_rain_timing_html(forecast):
    """HTML version of the rain-timing block."""
    if not _rain_is_notable(forecast):
        return ""
    cum = forecast.get("cumulative_rain_24h_in") or 0
    peak_t = forecast.get("peak_time_local")
    rows = ""
    for t in (forecast.get("all_tides") or []):
        peak_rain = t.get("peak_rain_in_hr") or 0
        offset = t.get("peak_rain_offset_h")
        label = "★ peak tide" if t["time"] == peak_t else "lower high"
        when = t["time"][-5:]
        if peak_rain <= 0.005:
            timing_desc = "no rain in ±90 min window"
        else:
            if offset is None:
                timing_desc = "during the window"
            elif abs(offset) < 0.25:
                timing_desc = "at high tide"
            elif offset < 0:
                timing_desc = f"{abs(offset):.0f} h before high tide"
            else:
                timing_desc = f"{offset:.0f} h after high tide"
            timing_desc = f"peak {peak_rain:.2f} in/hr, {timing_desc}"
        rows += (
            f'<tr><td>{when} ({label})</td>'
            f'<td>{timing_desc}</td></tr>'
        )
    return (
        '<section class="rain-timing">'
        '<h2>Rain &amp; tide timing</h2>'
        f'<p>Cumulative rain next 24 h: <b>{cum:.2f}&Prime;</b></p>'
        '<table class="rain-table">'
        '<thead><tr><th>High tide</th><th>Rain near it</th></tr></thead>'
        f'<tbody>{rows}</tbody></table>'
        '</section>'
    )


def _render_accuracy_text(forecast):
    """Plain-text one-line model accuracy summary. Empty list when no
    forecasts have been scored yet (first few days after archive starts)."""
    a = forecast.get("accuracy_summary") or {}
    n = a.get("n_scored_recent") or 0
    if n == 0:
        return []
    return [(
        f"Model accuracy (last {n} forecasts): "
        f"mean error {a['mean_error_ft']:+.2f} ft, "
        f"mean |error| {a['mean_abs_error_ft']:.2f} ft, "
        f"worst |error| {a['max_abs_error_ft']:.2f} ft. "
        f"Total scored: {a['n_scored_total']}."
    )]


def _load_accuracy_rows():
    """Load all rows from data/forecast_accuracy.csv with parsed numeric
    values. Used by the accuracy chart on the home page (HANDOFF 9b.8)."""
    if not os.path.exists(ACCURACY_CSV_PATH):
        return []
    rows = []
    try:
        with open(ACCURACY_CSV_PATH) as f:
            for r in csv.DictReader(f):
                try:
                    rows.append({
                        "date":      r.get("forecast_run_date", ""),
                        "predicted": float(r["forecast_peak_predicted_mllw"]),
                        "observed":  float(r["actual_peak_observed_mllw"]),
                        "error":     float(r["mllw_error_ft"]),
                        "regime":    r.get("forecast_regime", ""),
                    })
                except (TypeError, ValueError, KeyError):
                    continue
    except OSError:
        return []
    return rows


def _render_accuracy_html(forecast):
    """HTML accuracy section: text summary + scatter chart of
    predicted vs observed SH peaks (HANDOFF 9b.8 mode 1 — peak-magnitude
    accuracy). Empty string when no scored forecasts yet."""
    a = forecast.get("accuracy_summary") or {}
    n = a.get("n_scored_recent") or 0
    if n == 0:
        return ""

    summary_html = (
        f'<p>Last {n} forecasts: mean error '
        f'<b>{a["mean_error_ft"]:+.2f} ft</b>, '
        f'mean |error| <b>{a["mean_abs_error_ft"]:.2f} ft</b>, '
        f'worst |error| {a["max_abs_error_ft"]:.2f} ft. '
        f'Total scored: {a["n_scored_total"]}.</p>'
    )
    note_html = (
        '<p class="note">Positive mean error = model over-predicts on '
        'average. Each point is one archived daily forecast (since the '
        'JSON archive started). x = predicted Sandy Hook peak, y = '
        'actual NOAA observed peak. The dashed diagonal is perfect '
        'prediction (y=x); points above the line = model under-predicted, '
        'below = over-predicted. Raw data: '
        '<code>data/forecast_accuracy.csv</code>.</p>'
    )

    rows = _load_accuracy_rows()
    if len(rows) < 2:
        # Not enough data for a chart yet — just the text summary
        return (
            '<section class="accuracy">'
            '<h2>Model accuracy</h2>'
            f'{summary_html}'
            f'{note_html}'
            '</section>'
        )

    # Bounds for the chart axes — include the y=x line range
    all_vals = []
    for r in rows:
        all_vals.append(r["predicted"])
        all_vals.append(r["observed"])
    lo = min(all_vals) - 0.1
    hi = max(all_vals) + 0.1

    rows_json = json.dumps(rows)
    return f"""
<section class="accuracy">
  <h2>Model accuracy — predicted vs observed peaks</h2>
  {summary_html}
  <canvas id="accuracy-chart" width="800" height="380"
          style="max-width:100%;height:auto;display:block;margin:8px auto"></canvas>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@3.0.1/dist/chartjs-plugin-annotation.min.js"></script>
  <script>
    (function() {{
      var rows = {rows_json};
      var lo = {lo:.2f};
      var hi = {hi:.2f};
      var data = rows.map(function(r) {{
        return {{ x: r.predicted, y: r.observed, date: r.date,
                  error: r.error, regime: r.regime }};
      }});
      var ctx = document.getElementById('accuracy-chart').getContext('2d');
      new Chart(ctx, {{
        type: 'scatter',
        data: {{
          datasets: [{{
            label: 'Daily forecast vs actual',
            data: data,
            backgroundColor: 'rgba(31, 111, 235, 0.55)',
            borderColor: 'rgba(31, 111, 235, 0.85)',
            pointRadius: 5,
            pointHoverRadius: 7,
          }}]
        }},
        options: {{
          responsive: true,
          plugins: {{
            annotation: {{
              annotations: {{
                yEqualsX: {{
                  type: 'line',
                  xMin: lo, xMax: hi, yMin: lo, yMax: hi,
                  borderColor: 'rgba(150,150,150,0.7)',
                  borderWidth: 1, borderDash: [6, 4],
                  label: {{ display: true, content: 'y = x (perfect)',
                            position: 'end',
                            backgroundColor: 'rgba(255,255,255,0.85)',
                            color: '#666',
                            font: {{ size: 11 }} }}
                }}
              }}
            }},
            tooltip: {{
              callbacks: {{
                label: function(ctx) {{
                  var r = ctx.raw;
                  return [
                    r.date,
                    'Predicted: ' + r.x.toFixed(2) + ' ft MLLW',
                    'Observed:  ' + r.y.toFixed(2) + ' ft MLLW',
                    'Error:     ' + r.error.toFixed(2) + ' ft '
                      + (r.error > 0 ? '(over-pred)' : '(under-pred)'),
                  ];
                }}
              }}
            }},
            legend: {{ display: false }}
          }},
          scales: {{
            x: {{ title: {{ display: true,
                            text: 'Predicted SH peak (ft MLLW)' }},
                  suggestedMin: lo, suggestedMax: hi,
                  grid: {{ color: 'rgba(0,0,0,0.05)' }} }},
            y: {{ title: {{ display: true,
                            text: 'Observed SH peak (ft MLLW)' }},
                  suggestedMin: lo, suggestedMax: hi,
                  grid: {{ color: 'rgba(0,0,0,0.05)' }} }}
          }}
        }}
      }});
    }})();
  </script>
  {note_html}
</section>
"""


def _render_low_tides_text(forecast):
    """Plain-text block listing low tides in the next 24h. Useful for
    knowing when sub-curb water might drain back out, parking returns,
    etc. (See also: future Atlantic Highlands Marina Barnacle spin-off,
    where this block is the headline rather than a footnote.)"""
    lows = forecast.get("low_tides") or []
    if not lows:
        return []
    lines = ["Low tides in next 24h:"]
    for lt in lows:
        when = format_time_full(lt["time"])
        lines.append(f"  {when}  —  {lt['value_mllw']:.2f} ft MLLW")
    return lines


def _render_low_tides_html(forecast):
    """HTML version of the low-tides block."""
    lows = forecast.get("low_tides") or []
    if not lows:
        return ""
    rows = ""
    for lt in lows:
        rows += (
            f'<tr>'
            f'<td>{format_time_full(lt["time"])}</td>'
            f'<td>{lt["value_mllw"]:.2f}</td>'
            f'</tr>'
        )
    return (
        '<section class="low-tides">'
        '<h2>Low tides in next 24h</h2>'
        '<table class="history-table">'
        '<thead><tr><th>Time</th><th>Level (ft MLLW)</th></tr></thead>'
        f'<tbody>{rows}</tbody></table>'
        '<p class="note">Astronomical low-tide predictions for situational '
        'awareness — useful for parking returns, sub-curb drainage, and '
        '(eventually) boat-ramp viability at Atlantic Highlands Marina.</p>'
        '</section>'
    )


def _render_lookahead_text(forecast):
    """Plain-text "dates to watch" block — 1-2 month astronomical look-ahead.
    HANDOFF 9b.7. Empty when no upcoming tides cross the lowest threshold."""
    rows = forecast.get("lookahead_watch") or []
    if not rows:
        return []
    lines = [
        f"Dates to watch (next {LOOKAHEAD_DAYS} days, astronomical only):",
    ]
    for r in rows:
        when_full = format_time_full(r["time"])
        lines.append(
            f"  {when_full}  —  {r['mllw']:.2f} ft MLLW  ({r['label']})"
        )
    lines.append(
        "  These are baseline astronomical tides — surge isn't forecast "
        "this far out. An event of significance also needs surge or rain."
    )
    return lines


def _render_lookahead_html(forecast):
    """HTML version of the look-ahead block. HANDOFF 9b.7."""
    rows = forecast.get("lookahead_watch") or []
    if not rows:
        return ""
    body = ""
    for r in rows:
        body += (
            f'<tr class="{r["severity_class"]}">'
            f'<td>{format_time_full(r["time"])}</td>'
            f'<td>{r["mllw"]:.2f}</td>'
            f'<td>{r["label"]}</td>'
            f'</tr>'
        )
    return (
        '<section class="lookahead">'
        f'<h2>Dates to watch — next {LOOKAHEAD_DAYS} days</h2>'
        '<table class="history-table">'
        '<thead><tr><th>Date / time</th><th>Peak (ft MLLW)</th>'
        '<th>Significance</th></tr></thead>'
        f'<tbody>{body}</tbody></table>'
        '<p class="note">Astronomical-only predictions — surge isn\'t '
        'forecast this far out. An event of real significance also needs '
        'surge or rain, neither of which is in this table. Use as a '
        'planning aid (which dates have elevated baseline tides) rather '
        'than as a flood forecast.</p>'
        '</section>'
    )


def _render_recent_history_text(forecast):
    """Recent-history recap block (last 7 days). Empty when no data."""
    history = forecast.get("recent_history_7d") or []
    if not history:
        return []
    lines = ["Recent observed peaks (last 7 days):"]
    lines.append(
        f"  {'Date':<14}{'Peak (MLLW)':>13}  "
        f"{'Peak time':<14}{'Rel':>8}  Highest landmark reached"
    )
    for h in history:
        date_label = format_date_short(h["date"])
        peak_t = format_time_short(h.get("peak_time") or "")
        rel_str = f"{h['rel_in']:+.1f}\""
        lines.append(
            f"  {date_label:<14}"
            f"{h['peak_mllw']:>12.2f}   "
            f"{peak_t:<14}"
            f"{rel_str:>8}  "
            f"{h['highest_landmark']}"
        )
    return lines


def _render_recent_history_html(forecast):
    """HTML recap block."""
    history = forecast.get("recent_history_7d") or []
    if not history:
        return ""
    rows = ""
    for h in history:
        date_label = format_date_short(h["date"])
        peak_t = format_time_short(h.get("peak_time") or "")
        rel_str = f"{h['rel_in']:+.1f}&Prime;"
        rows += (
            f'<tr>'
            f'<td>{date_label}</td>'
            f'<td>{h["peak_mllw"]:.2f}</td>'
            f'<td>{peak_t}</td>'
            f'<td>{rel_str}</td>'
            f'<td>{h["highest_landmark"]}</td>'
            f'</tr>'
        )
    return (
        '<section class="recent-history">'
        '<h2>Recent observed peaks (last 7 days)</h2>'
        '<table class="history-table">'
        '<thead><tr><th>Date</th><th>Peak (ft MLLW)</th><th>Peak time</th>'
        '<th>Rel</th><th>Highest landmark</th></tr></thead>'
        f'<tbody>{rows}</tbody></table>'
        '<p class="note">From NOAA Sandy Hook water_level (6-min product, '
        'preliminary). <b>Rel</b> = inches above the lowest landmark '
        '(lowest road corner, 3.64 NAVD88), always positive or negative. '
        '"Highest landmark" applies the +0.40 ft local enhancement to the '
        'observed peak.</p>'
        '</section>'
    )


def _format_decimal(v):
    """Show <1.0 numbers with two decimals, otherwise one. Keeps narrow values
    readable in the table without losing precision at the rare end."""
    if v is None:
        return "—"
    return f"{v:.2f}" if v < 1.0 else f"{v:.1f}"


# Per-landmark short role tags used in the unified table. Blank means
# the landmark name itself is descriptive enough.
LANDMARK_ROLES = {
    # lowest_sentinel_grate: label "Lowest storm grate" is self-descriptive;
    # leaving the role tag empty avoids overflow in the text table.
    "lowest_road_corner":    "sentinel",
    "gutter_walkway":        "parking",
    "corner_grate":          "Pathway B",
    "curb":                  "flood onset",
}

# Short labels for the compact per-tide table. Full labels live in LANDMARKS.
LANDMARK_SHORT_LABELS = {
    "lowest_sentinel_grate": "Sentinel grate",
    "lowest_road_corner":    "Lowest corner",
    "gutter_walkway":        "Gutter",
    "corner_grate":          "Storm grate",
    "curb":                  "Curb",
    "road_middle":           "Road middle",
    "intersection":          "Intersection",
    "lawn_step":             "Lawn step",
    "porch_step":            "Porch step",
}


def landmark_summary(depths, sandy_hook_peak_mllw):
    """For a given forecast peak + per-landmark depths, return a compact
    summary for the per-tide table:
        (short_label, inches_above_landmark, relative_to_lowest_inches)
    where:
      - short_label = highest landmark exceeded by water level, OR the
        lowest landmark (Lowest road corner) if no landmark is exceeded
      - inches_above_landmark = depth at that landmark from depths dict
        (positive); when no exceedance, negative inches below the lowest
        landmark (computed from tide-only water level)
      - relative_to_lowest = depth at the lowest_road_corner from depths
        when water exceeds it; when below the lowest, the same negative
        value as inches_above_landmark
    Uses rain-augmented depths so the per-tide row stays consistent with
    the lower unified landmark table."""
    sorted_landmarks = sorted(LANDMARKS, key=lambda x: x[2])  # ascending elev
    lowest_key, _, lowest_elev, _ = sorted_landmarks[0]

    highest_exceeded = None
    for key, _label, _elev, _sh in sorted_landmarks:
        if depths.get(key, 0) > 0:
            highest_exceeded = key

    if highest_exceeded:
        short = LANDMARK_SHORT_LABELS.get(highest_exceeded, highest_exceeded)
        inches_above = depths[highest_exceeded]
        relative = depths.get(lowest_key, 0.0)
    else:
        short = LANDMARK_SHORT_LABELS.get(lowest_key, lowest_key)
        water_navd88 = sandy_hook_peak_mllw + LOCAL_ENHANCEMENT_FT + MLLW_TO_NAVD88_OFFSET
        inches_above = (water_navd88 - lowest_elev) * 12  # negative
        relative = inches_above
    return short, inches_above, relative


def assess_confidence(forecast):
    """Return (level, reason) for the daily forecast confidence indicator.
    Levels: 'high' / 'medium' / 'low'. Reason is a one-liner human
    explanation safe to drop into the email."""
    if forecast.get("cold_lockout"):
        return ("high",
                "cold lockout active — model is correctly zeroing predictions")
    surge_source = forecast.get("surge_source", "")
    if surge_source == "nws-coastal-flood-product":
        return ("high",
                "NWS Coastal Flood product active — forecaster-vetted projection")
    peak = forecast.get("peak_forecast_observed_mllw") or 0
    if peak > 8.0:
        return ("low",
                f"forecast peak {peak:.2f} ft is above the model's "
                f"calibrated range (events fit ≤ 7.6 ft)")
    swing = forecast.get("surge_swing_6h_ft")
    if swing is not None and swing > 0.5:
        return ("low",
                f"observed surge has swung {swing:.2f} ft in the past 6 h — "
                f"persistence assumption is unreliable")
    return ("medium",
            "surge persistence applied; forecast within calibrated range")


def plain_language_summary(forecast):
    """Return a one-line plain-language summary of the next 24 h. Skim-friendly
    framing for the top of the email and Pages site."""
    tides = forecast.get("all_tides") or []
    if not tides:
        return ""
    tides_sorted = sorted(tides, key=lambda t: t["time"])
    today = dt.date.today()

    def time_phrase(t):
        time_str = t["time"]
        try:
            tide_dt = dt.datetime.strptime(time_str, "%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            return time_str
        tide_date = tide_dt.date()
        hour = tide_dt.hour
        # 12-hour AM/PM time for the user-facing summary
        ampm = tide_dt.strftime("%-I:%M %p")
        if tide_date == today:
            if hour < 12:
                period = "this morning"
            elif hour < 17:
                period = "this afternoon"
            elif hour < 21:
                period = "this evening"
            else:
                period = "tonight"
            return f"{ampm} {period}"
        # tomorrow (or later)
        if tide_date == today + dt.timedelta(days=1):
            prefix = "tomorrow"
        else:
            prefix = tide_dt.strftime("%a %b %-d")
        if hour < 12:
            return f"{ampm} {prefix} morning"
        if hour < 17:
            return f"{ampm} {prefix} afternoon"
        if hour < 21:
            return f"{ampm} {prefix} evening"
        return f"{ampm} {prefix} night"

    def phrase_for_tide(t):
        regime = t["depths_in"]["regime"]
        short, above, _ = landmark_summary(t["depths_in"], t["forecast_peak_mllw"])
        if regime == "cold_lockout":
            return "cold lockout — no flooding predicted despite high tide"
        if regime == "dry":
            return "dry"
        if regime == "street":
            return f"brief water at the {short.lower()}, nothing at the curb"
        if regime == "light":
            return f"curb wet (~{above:.1f}\" above {short.lower()})"
        if regime == "moderate":
            return f"moderate flooding — water past curb (~{above:.1f}\" above {short.lower()})"
        if regime == "severe":
            return f"SEVERE flooding — water past {short.lower()} (~{above:.1f}\")"
        return regime

    parts = [f"{time_phrase(t)} — {phrase_for_tide(t)}" for t in tides_sorted]
    return "Next 24 h: " + "; ".join(parts) + "."


def format_time_full(time_str):
    """Convert NOAA-style '2026-05-18 22:14' to 'May 18, 2026: Mon 10:14 PM'.
    Pass-through on parse failure."""
    try:
        d = dt.datetime.strptime(time_str, "%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return time_str
    # %-d / %-I work on Linux + macOS (the only environments this runs on).
    date_part = d.strftime("%b %-d, %Y")
    time_part = d.strftime("%a %-I:%M %p")
    return f"{date_part}: {time_part}"


def format_time_short(time_str):
    """Convert '2026-05-18 22:14' to 'Mon 10:14 PM' for tight contexts
    (subject line, tide table rows, spot-check times)."""
    try:
        d = dt.datetime.strptime(time_str, "%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return time_str
    return d.strftime("%a %-I:%M %p")


def format_date_short(date_str):
    """Convert 'YYYY-MM-DD' to 'Mon, May 18' for recent-history rows."""
    try:
        d = dt.date.fromisoformat(date_str)
    except (ValueError, TypeError):
        return date_str
    return d.strftime("%a, %b %-d")


# Regime glossary for inline annotation and the email/HTML footer.
REGIME_GLOSSARY = {
    "dry":          "no visible water at any landmark",
    "street":       "water on the street at sub-curb landmarks; curb still dry",
    "light":        "water at curb (0–4 inches)",
    "moderate":     "water at curb (4–8 inches)",
    "severe":       "water past lawn step / bulkhead overtopping territory",
    "cold_lockout": "drains likely ice-locked; flooding suppressed despite high tide",
}


def _unified_landmark_rows(forecast):
    """Build per-landmark row dicts used by both the text and HTML renderers.
    Each row has: key, label, elev_navd88, sh_threshold, today_in,
    avg_days, mtd_days, descriptor, role."""
    d = forecast.get("depths_in") or {}
    ctx = forecast.get("seasonal_context") or {}
    strata = ctx.get("strata") or []
    season_by_key = {s.get("landmark_key"): s for s in strata}
    mtd = ctx.get("mtd") or {}
    mtd_by_thresh = {s["threshold_ft"]: s for s in (mtd.get("strata") or [])}

    out = []
    for key, label, elev, sh in LANDMARKS:
        season = season_by_key.get(key, {})
        mtd_row = mtd_by_thresh.get(sh, {})
        out.append({
            "key":         key,
            "label":       label,
            "elev_navd88": elev,
            "sh":          sh,
            "today_in":    d.get(key, 0.0),
            "avg_days":    season.get("avg_days"),
            "mtd_days":    mtd_row.get("n_flood_days", 0),
            "descriptor":  season.get("descriptor", ""),
            "role":        LANDMARK_ROLES.get(key, ""),
        })
    return out


def _unified_landmark_table_text(forecast, today=None):
    """Plain-text unified table: per-landmark prediction + history.
    Returns list of strings (header + rows + footnote)."""
    today = today or dt.date.today()
    rows = _unified_landmark_rows(forecast)
    if not rows:
        return []
    month_name = today.strftime("%B")
    # Window string from any seasonality row that has it
    ctx = forecast.get("seasonal_context") or {}
    strata = ctx.get("strata") or []
    window = (strata[0].get("window").split(" (")[0]
              if strata and strata[0].get("window") else "1996-2025")

    lines = [f"Landmarks at 342 Bay Ave (worst-case tide; {month_name} typical "
             f"avg over {window}, MTD = this month):"]
    # Column widths chosen to keep the table compact but readable.
    lines.append(f"   {'Landmark':<42}{'NAVD':>5}{'Today':>8}{'Typ':>7}{'MTD':>5}  Notes")
    for r in rows:
        label_with_role = r["label"]
        if r["role"]:
            label_with_role = f"{r['label']} ({r['role']})"
        label_with_role = label_with_role[:42]
        avg_str = _format_decimal(r["avg_days"]) if r["avg_days"] is not None else "—"
        marker = "★" if r["today_in"] > 0 else " "
        lines.append(
            f"  {marker} {label_with_role:<42}"
            f"{r['elev_navd88']:>5.2f}"
            f"{r['today_in']:>7.1f}\""
            f"{avg_str:>7}"
            f"{r['mtd_days']:>5}"
            f"  {r['descriptor']}"
        )
    lines.append("  (★ = water predicted today at this landmark. Typ / MTD "
                 "in days/month at the landmark threshold.)")
    return lines


def _unified_landmark_table_html(forecast, today=None):
    """HTML version of the unified landmark table. Returns single HTML
    string (table + caption). Empty if no rows."""
    today = today or dt.date.today()
    rows = _unified_landmark_rows(forecast)
    if not rows:
        return ""
    month_name = today.strftime("%B")
    ctx = forecast.get("seasonal_context") or {}
    strata = ctx.get("strata") or []
    window = (strata[0].get("window").split(" (")[0]
              if strata and strata[0].get("window") else "1996-2025")

    row_html = ""
    for r in rows:
        avg_str = _format_decimal(r["avg_days"]) if r["avg_days"] is not None else "—"
        marker = "★ " if r["today_in"] > 0 else ""
        role_html = f" <span class=\"role\">({r['role']})</span>" if r["role"] else ""
        bold_open, bold_close = ("<b>", "</b>") if r["today_in"] > 0 else ("", "")
        row_html += (
            f"<tr>"
            f"<td>{marker}{r['label']}{role_html}</td>"
            f"<td>{r['elev_navd88']:.2f}</td>"
            f"<td>{bold_open}{r['today_in']:.1f}&Prime;{bold_close}</td>"
            f"<td>{avg_str}</td>"
            f"<td>{r['mtd_days']}</td>"
            f"<td class=\"note\">{r['descriptor']}</td>"
            f"</tr>"
        )
    return (
        f'<p class="context">Today\'s prediction vs <b>{month_name} typical</b> '
        f'(avg flood days/month over {window}) and <b>month-to-date</b>:</p>'
        f'<table class="landmark-table">'
        f'<thead><tr>'
        f'<th>Landmark</th><th>NAVD88</th><th>Today</th>'
        f'<th>Typ</th><th>MTD</th><th>Notes</th>'
        f'</tr></thead><tbody>'
        f'{row_html}'
        f'</tbody></table>'
        f'<p class="note">★ = water predicted today at this landmark. '
        f'Typ / MTD in days/month at the landmark threshold.</p>'
    )


def _near_miss_text(mtd):
    """One-line near-miss summary, or None if not applicable.
    Triggers when MTD curb events = 0 but the 6-min sensor came within
    0.1 ft of the curb threshold. Distinguishes the case where 6-min
    actually crossed (gives a duration) from the case where it just
    got close."""
    if not mtd:
        return None
    curb_events = next((s["n_events"] for s in (mtd.get("strata") or [])
                        if s["threshold_ft"] == 6.58), None)
    if curb_events is None or curb_events > 0:
        return None
    raw = mtd.get("peak_6min_mllw")
    if raw is None or raw < 6.58 - 0.1:
        return None
    when = format_time_full(mtd.get("peak_6min_time") or "")
    mins = mtd.get("minutes_above_curb", 0)
    if raw >= 6.58 and mins > 0:
        return (f"Closest call: water touched 6.58 ft on the 6-min sensor "
                f"for ~{mins} min ({when}, peaked at {raw:.2f} ft) — "
                f"hourly mean stayed just under the curb threshold.")
    return (f"Closest call: 6-min sensor peaked at {raw:.2f} ft on "
            f"{when} — below your curb but within 0.1 ft of it.")


def _landmarks_footer_text(forecast, today=None):
    """Plain-text footer lines below the unified landmark table: month
    descriptor at the curb, peak so far this month, near-miss, SLR line.
    Each piece independent; returns list of strings (possibly empty)."""
    today = today or dt.date.today()
    ctx = forecast.get("seasonal_context") or {}
    strata = ctx.get("strata") or []
    month_name = today.strftime("%B")
    lines = []
    curb_row = next((s for s in strata if s.get("landmark_key") == "curb"), None)
    if curb_row:
        desc = curb_row.get("descriptor", "")
        if desc in ("wettest month", "quietest month"):
            lines.append(f"{month_name} is the {desc} of the year at the curb threshold.")
        elif desc:
            lines.append(f"{month_name} is a {desc} month at the curb threshold.")
    mtd = ctx.get("mtd")
    if mtd and mtd.get("peak_obs_mllw") is not None:
        lines.append(f"Peak Sandy Hook so far this month: "
                     f"{mtd['peak_obs_mllw']:.2f} ft MLLW.")
    nm = _near_miss_text(mtd)
    if nm:
        lines.append(nm)
    if ctx.get("show_slr_line"):
        slr = ctx["slr_ft_since_1990"]
        peak = ctx["slr_today_peak_ft"]
        ref_year = ctx["slr_reference_year"]
        lines.append(
            f"Sea level at Sandy Hook is ~{slr:.2f} ft higher than in {ref_year}. "
            f"Today's high tide of {peak:.2f} ft wouldn't have crossed your curb "
            f"in {ref_year}; today it does."
        )
    return lines


def _landmarks_footer_html(forecast, today=None):
    """HTML version. Returns list of <p> fragments."""
    return [f'<p class="context">{line}</p>'
            for line in _landmarks_footer_text(forecast, today)]


def _high_value_calibration_callouts(forecast):
    """Return list of strings flagging observation opportunities that
    would resolve open calibration questions (HANDOFF items 10, 14).
    Empty when nothing special is happening today. Used by both text
    and HTML spot-check renderers so the call-outs stay consistent."""
    callouts = []
    cumulative_rain = forecast.get("cumulative_rain_24h_in") or 0
    all_tides = forecast.get("all_tides") or []
    # Pluvial-only opportunity (HANDOFF item 14): meaningful rain
    # forecast AND no tide reaches even the lowest sentinel. One good
    # observation could resolve "does heavy rain flood 342 Bay without
    # any tidal contribution?"
    rain_meaningful = cumulative_rain >= 0.25
    any_tide_above_sentinel = any(
        (t.get("depths_in") or {}).get("lowest_road_corner", 0) > 0
        for t in all_tides
    )
    if rain_meaningful and not any_tide_above_sentinel:
        callouts.append(
            "  ★ PLUVIAL-ONLY OPPORTUNITY: today has notable rain "
            f"({cumulative_rain:.2f}\" forecast over next 24 h) but no tide "
            "is expected to reach even the lowest landmark. If you see "
            "any water on the street during the heaviest rain hour, "
            "that's a rare data point for whether 342 Bay can flood from "
            "rain alone (HANDOFF item 14)."
        )
    # Cold-lockout calibration opportunity (HANDOFF item 10): override
    # is active AND today's predicted peak (without override) would have
    # crossed the curb. Did the lockout hold?
    if forecast.get("cold_lockout"):
        peak = forecast.get("peak_forecast_observed_mllw") or 0
        if peak >= 6.58:
            callouts.append(
                "  ★ COLD-LOCKOUT CALIBRATION OPPORTUNITY: cold-weather "
                "override is active and today's tide would have crossed "
                f"the curb without it ({peak:.2f} ft predicted). The model "
                "predicts no flooding; if water actually does appear at "
                "the curb today, that breaks the override and is a "
                "high-value data point (HANDOFF item 10)."
            )
    return callouts


def _spot_check_block_text(forecast, today=None):
    """Plain-text spot-check prompt with suggested observation times.
    Always emitted (every email, including DRY); the user requested this
    to build the calibration habit. References the landmark table above
    rather than duplicating the ladder. Includes high-value calibration
    callouts when today's conditions are unusual (rain at low tide;
    cold lockout above curb)."""
    today = today or dt.date.today()
    all_tides = forecast.get("all_tides") or []
    if not all_tides:
        return []
    peak_t = forecast.get("peak_time_local")
    items = []
    for t in all_tides:
        when = format_time_short(t["time"])
        role = "peak" if t["time"] == peak_t else "lower high"
        items.append(f"{when} ({role})")
    times_str = ", ".join(items)
    lines = [
        "Spot-check (help calibrate the model):",
        f"  Suggested observation times today: {times_str}",
    ]
    lines.extend(_high_value_calibration_callouts(forecast))
    lines.extend([
        "  Take a peek around one of those times — even 'no water at all'",
        "  is useful. Use the landmark table above (lowest to highest) to",
        "  describe what you saw. Report back with: time you looked,",
        "  highest landmark with water (or 'no water'), and rough depth",
        "  above it. Goes into data/labeled_observations.csv.",
    ])
    return lines


def _spot_check_block_html(forecast, today=None):
    """HTML version of the spot-check prompt."""
    today = today or dt.date.today()
    all_tides = forecast.get("all_tides") or []
    if not all_tides:
        return ""
    peak_t = forecast.get("peak_time_local")
    items = []
    for t in all_tides:
        when = format_time_short(t["time"])
        role = "peak" if t["time"] == peak_t else "lower high"
        items.append(f"{when} ({role})")
    times_str = ", ".join(items)
    callouts = _high_value_calibration_callouts(forecast)
    callouts_html = ""
    for c in callouts:
        # Strip the leading "  ★ " marker from the text version
        text = c.strip().lstrip("★").strip()
        callouts_html += f'<p class="spot-check-callout">★ {text}</p>'
    return (
        '<section class="spot-check">'
        '<h2>Spot-check (help calibrate the model)</h2>'
        f'<p>Suggested observation times today: <b>{times_str}</b>.</p>'
        f'{callouts_html}'
        '<p>Take a peek around one of those times — even '
        '&ldquo;no water at all&rdquo; is useful. Use the landmark table '
        'above (lowest to highest) to describe what you saw. Report back '
        'with: time you looked, highest landmark with water (or '
        '&ldquo;no water&rdquo;), and rough depth above it. '
        'Goes into <code>data/labeled_observations.csv</code>.</p>'
        '</section>'
    )


def _landmarks_section_text(forecast, today=None):
    """Combined Landmarks section: unified table + footer + spot-check."""
    parts = []
    table_lines = _unified_landmark_table_text(forecast, today)
    if table_lines:
        parts.extend(table_lines)
    footer = _landmarks_footer_text(forecast, today)
    if footer:
        if parts:
            parts.append("")  # blank line
        parts.extend(footer)
    spot = _spot_check_block_text(forecast, today)
    if spot:
        if parts:
            parts.append("")
        parts.extend(spot)
    if not parts:
        return ""
    return "\n".join(parts) + "\n"


def _landmarks_section_html(forecast, today=None, wrapper="section"):
    """Combined Landmarks section (HTML)."""
    table_html = _unified_landmark_table_html(forecast, today)
    footer_html = "".join(_landmarks_footer_html(forecast, today))
    if not table_html and not footer_html:
        body = ""
    else:
        body = table_html + footer_html
    if not body:
        landmarks_section = ""
    elif wrapper == "section":
        landmarks_section = (
            '<section class="landmarks">'
            '<h2>Landmarks today</h2>' + body + '</section>'
        )
    else:
        landmarks_section = (
            '<h3>Landmarks today</h3>'
            '<div style="background:white;padding:8px;border-radius:4px">'
            + body + '</div>'
        )
    return landmarks_section + _spot_check_block_html(forecast, today)


# ============================================================
# Email rendering and sending
# ============================================================
def render_email(forecast):
    d = forecast["depths_in"]
    regime = d["regime"]
    peak_t = forecast["peak_time_local"]
    peak_ft = forecast["peak_forecast_observed_mllw"]
    all_tides = forecast.get("all_tides", [])

    subject_short, subject_above, _ = landmark_summary(d, peak_ft)
    subject = (f"[342 Bay] {regime.upper()}: forecast {peak_ft:.2f} ft "
               f"at {format_time_short(peak_t)} "
               f"({subject_short} {subject_above:+.1f}\")")

    # Format the list of all high tides in next 24h.
    # Columns: time, pred, surge, peak, highest-exceeded landmark, inches
    # above that landmark, inches relative to the lowest landmark, regime.
    tide_lines = []
    tide_lines.append(
        f"   {'Time':<16}{'Pred':>6}{'Surge':>8}{'Peak':>7}  "
        f"{'Landmark':<14}{'Above':>8}{'Rel':>8}  Regime"
    )
    for t in all_tides:
        td = t["depths_in"]
        short, above_in, rel_in = landmark_summary(td, t["forecast_peak_mllw"])
        marker = "★" if t["time"] == peak_t else " "
        tide_lines.append(
            f" {marker} {format_time_short(t['time']):<16}"
            f"{t['predicted_mllw']:>6.2f}"
            f"{t['surge_ft']:>+8.2f}"
            f"{t['forecast_peak_mllw']:>7.2f}  "
            f"{short:<14}"
            f"{above_in:>+7.1f}\""
            f"{rel_in:>+7.1f}\""
            f"  {td['regime']}"
        )
    tide_block = "\n".join(tide_lines)
    tide_block += (
        "\n  Above = inches above the highest exceeded landmark (negative "
        "= water below the lowest landmark).\n"
        "  Rel = inches above the lowest landmark (lowest road corner, "
        "3.64 NAVD88) — always."
    )

    summary_lines = _render_summary_text(forecast)
    summary_block = ("\n".join(summary_lines) + "\n\n") if summary_lines else ""
    rain_lines = _render_rain_timing_text(forecast)
    rain_block = ("\n".join(rain_lines) + "\n\n") if rain_lines else ""
    recap_lines = _render_recent_history_text(forecast)
    recap_block = ("\n".join(recap_lines) + "\n\n") if recap_lines else ""
    low_lines = _render_low_tides_text(forecast)
    low_block = ("\n".join(low_lines) + "\n\n") if low_lines else ""
    accuracy_lines = _render_accuracy_text(forecast)
    accuracy_block = ("\n".join(accuracy_lines) + "\n\n") if accuracy_lines else ""
    lookahead_lines = _render_lookahead_text(forecast)
    lookahead_block = ("\n".join(lookahead_lines) + "\n\n") if lookahead_lines else ""

    text = f"""\
Bay Ave Barnacle flood forecast for 342 Bay Ave - {dt.date.today().isoformat()}

{summary_block}High tides in next 24h ( * = worst case, headlined below):
{tide_block}

Worst case detail:
  High tide time:  {format_time_full(peak_t)}
  Predicted tide:  {forecast['peak_predicted_mllw']:.2f} ft MLLW (Sandy Hook)
  Surge:           {forecast['current_surge_ft']:+.2f} ft
  Forecast peak:   {peak_ft:.2f} ft MLLW
  Surge source:    {forecast['surge_source']}
                   ({forecast['nws_status']})
  Rain in window:  {forecast['peak_rain_rate_in_hr']:.2f} in/hr peak
  72h mean temp:   {forecast['temp_avg_72h_f']:.1f} F
  Cold lockout:    {'YES (drains likely ice-locked)' if forecast['cold_lockout'] else 'no'}

{rain_block}{_landmarks_section_text(forecast)}
Regime: {regime} — {REGIME_GLOSSARY.get(regime, '')}

{recap_block}{accuracy_block}{low_block}{lookahead_block}Reference scale (Sandy Hook obs MLLW):
  < 6.02  : dry (nothing visible)
  6.02    : water emerges from lowest storm grate (Central Ave south)
  6.06    : lowest road corner across Bay first wets (visible from window)
  6.20    : water at gutter / curb edge — don't park there
  6.33    : water emerges from corner storm grate at Bay+Central (Pathway B)
  6.58    : water at curb top — flood onset at property
  6.78    : Bay Ave road middle covered
  6.96    : intersection center submerged
  7.00    : water at lawn / walkway step
  7.50    : water at front porch first step
  7.9+    : severe (well past porch)

Regime glossary (subject-line label, based on water depth at the curb):
  dry          : {REGIME_GLOSSARY['dry']}
  street       : {REGIME_GLOSSARY['street']}
  light        : {REGIME_GLOSSARY['light']}
  moderate     : {REGIME_GLOSSARY['moderate']}
  severe       : {REGIME_GLOSSARY['severe']}
  cold_lockout : {REGIME_GLOSSARY['cold_lockout']}

Model: v0.6. Local enhancement +0.40 ft.
"""

    bg = {"dry": "#e8f5e9", "street": "#e3f2fd", "light": "#fff8e1",
          "moderate": "#ffe0b2", "severe": "#ffcdd2",
          "cold_lockout": "#eceff1"}.get(regime, "#fff")

    # Build the all-tides rows for the HTML email (new column layout)
    tide_rows_html = ""
    for t in all_tides:
        td = t["depths_in"]
        is_worst = (t["time"] == peak_t)
        row_style = "background:#ffffcc" if is_worst else ""
        short, above_in, rel_in = landmark_summary(td, t["forecast_peak_mllw"])
        tide_rows_html += (
            f'<tr style="{row_style}">'
            f'<td>{format_time_full(t["time"])}</td>'
            f'<td align="right">{t["predicted_mllw"]:.2f}</td>'
            f'<td align="right">{t["surge_ft"]:+.2f}</td>'
            f'<td align="right"><b>{t["forecast_peak_mllw"]:.2f}</b></td>'
            f'<td>{short}</td>'
            f'<td align="right">{above_in:+.1f}&Prime;</td>'
            f'<td align="right">{rel_in:+.1f}&Prime;</td>'
            f'<td>{td["regime"]}</td>'
            f'</tr>'
        )

    summary_html = _render_summary_html(forecast)
    rain_html = _render_rain_timing_html(forecast)
    recap_html = _render_recent_history_html(forecast)
    low_html = _render_low_tides_html(forecast)
    accuracy_html = _render_accuracy_html(forecast)
    lookahead_html = _render_lookahead_html(forecast)

    html = f"""\
<html><body style="font-family:sans-serif;background:{bg};padding:20px">
<h2>Bay Ave Flood Forecast</h2>
<p><b>{dt.date.today().isoformat()}</b></p>

{summary_html}
<h3>High tides in next 24h</h3>
<table border="1" cellpadding="8" style="border-collapse:collapse;background:white">
<tr><th>Time</th><th>Pred (ft)</th><th>Surge</th><th>Peak (ft)</th><th>Highest landmark</th><th>Above</th><th>Rel</th><th>Regime</th></tr>
{tide_rows_html}
</table>
<p style="font-size:small;color:#666">Highlighted row = worst-case tide, headlined below.
<b>Above</b> = inches above the highest exceeded landmark (negative when water is below the lowest landmark).
<b>Rel</b> = inches above the lowest landmark (lowest road corner across Bay, 3.64 NAVD88).</p>

<p><b>Worst case:</b> {format_time_full(peak_t)}<br>
<b>Forecast peak (obs):</b> {peak_ft:.2f} ft MLLW Sandy Hook
({forecast['peak_predicted_mllw']:.2f} predicted {forecast['current_surge_ft']:+.2f} surge)<br>
<b>Surge source:</b> {forecast['surge_source']} ({forecast['nws_status']})<br>
<b>Rainfall in window:</b> {forecast['peak_rain_rate_in_hr']:.2f} in/hr peak<br>
<b>72h mean temp:</b> {forecast['temp_avg_72h_f']:.1f}&deg;F
{'(COLD LOCKOUT ACTIVE)' if forecast['cold_lockout'] else ''}</p>

{rain_html}
{_landmarks_section_html(forecast, wrapper='inline')}

<p><b>Regime: {regime}</b> &mdash; <span style="color:#666;font-size:13px">{REGIME_GLOSSARY.get(regime, '')}</span></p>

<h3>Regime glossary</h3>
<table border="1" cellpadding="6" style="border-collapse:collapse;background:white;font-size:13px">
<tr><td><b>dry</b></td><td>{REGIME_GLOSSARY['dry']}</td></tr>
<tr><td><b>street</b></td><td>{REGIME_GLOSSARY['street']}</td></tr>
<tr><td><b>light</b></td><td>{REGIME_GLOSSARY['light']}</td></tr>
<tr><td><b>moderate</b></td><td>{REGIME_GLOSSARY['moderate']}</td></tr>
<tr><td><b>severe</b></td><td>{REGIME_GLOSSARY['severe']}</td></tr>
<tr><td><b>cold_lockout</b></td><td>{REGIME_GLOSSARY['cold_lockout']}</td></tr>
</table>

{recap_html}
{accuracy_html}
{low_html}
{lookahead_html}
<p style="font-size:small;color:#666">
Model v0.6. Local enhancement +0.40 ft. Rain term saturates at 8".
Surge persistence is a rough proxy; for active coastal storms, check NWS
Coastal Flood Statement directly.
</p>
</body></html>"""
    return subject, text, html


def _oscillation_chart_data(forecast):
    """Build data points for the home-page oscillation chart (HANDOFF 9b.4(b)).

    Returns dict with:
      'points': list of {time, water_navd88, kind} where kind is
                'observed' (past tide peak from recent history) or
                'predicted' (upcoming tide peak from current forecast).
      'landmarks': list of {label, navd88} from the model's LANDMARKS,
                   for rendering horizontal threshold lines.

    Water level at 342 Bay (NAVD88) = SH_peak + LOCAL_ENHANCEMENT − 2.82,
    so landmark crossings on this single axis tell the full story.
    """
    points = []

    # Past: observed peaks from the last 7 days
    for r in (forecast.get("recent_history_7d") or []):
        peak = r.get("peak_mllw")
        time_str = r.get("peak_time")
        if peak is None or not time_str:
            continue
        try:
            water = float(peak) + LOCAL_ENHANCEMENT_FT + MLLW_TO_NAVD88_OFFSET
        except (TypeError, ValueError):
            continue
        points.append({
            "time": time_str,
            "water_navd88": round(water, 3),
            "kind": "observed",
            "sh_peak_mllw": float(peak),
        })

    # Future: predicted peaks for upcoming high tides in this forecast
    for t in (forecast.get("all_tides") or []):
        peak = t.get("forecast_peak_mllw")
        time_str = t.get("time")
        if peak is None or not time_str:
            continue
        try:
            water = float(peak) + LOCAL_ENHANCEMENT_FT + MLLW_TO_NAVD88_OFFSET
        except (TypeError, ValueError):
            continue
        points.append({
            "time": time_str,
            "water_navd88": round(water, 3),
            "kind": "predicted",
            "sh_peak_mllw": float(peak),
        })

    # Landmark threshold lines — a curated subset of LANDMARKS to keep
    # the chart readable. Per user 2026-05-19: include lowest grate,
    # gutter/curb, Bay+Central storm grate, curb at walkway, lawn step,
    # porch step. Excluded: lowest_road_corner (3.64 — crowds the
    # gutter line at 3.78), road_middle (4.36 — crowds curb at 4.16),
    # intersection (4.54 — crowds lawn_step at 4.58).
    keep_keys = OSCILLATION_LANDMARK_KEYS
    landmark_lines = [
        {"label": label, "navd88": float(elev)}
        for key, label, elev, _sh in LANDMARKS
        if key in keep_keys
    ]

    return {"points": points, "landmarks": landmark_lines}


def _render_oscillation_section(forecast):
    """Render the home-page water-level oscillation chart section
    (HANDOFF 9b.4(b)). Empty string when there's no plottable data."""
    data = _oscillation_chart_data(forecast)
    if len(data["points"]) < 2:
        return ""
    # Inline as JSON; Chart.js reads from the global on load.
    data_json = json.dumps(data, default=str)
    return f"""
  <section class="oscillation">
    <h2>Water level over time</h2>
    <p class="note">Observed (■) past peaks and predicted (●) upcoming peaks
       plotted on a single water-level axis (NAVD88 ft at 342 Bay). Horizontal
       lines mark landmark elevations — when a peak crosses a line, the water
       reached that landmark.</p>
    <canvas id="oscillation-chart" width="800" height="380"
            style="max-width:100%;height:auto;display:block;margin:8px auto"></canvas>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@3.0.1/dist/chartjs-plugin-annotation.min.js"></script>
    <script>
      (function() {{
        var data = {data_json};
        var points = data.points.slice().sort(function(a, b) {{
          return (a.time < b.time) ? -1 : (a.time > b.time ? 1 : 0);
        }});
        var labels = points.map(function(p) {{
          // Compact tide-time label (e.g., "Tue 5/19 11 PM")
          var d = new Date(p.time.replace(' ', 'T'));
          if (isNaN(d.getTime())) return p.time;
          return d.toLocaleString(undefined, {{
            weekday: 'short', month: 'numeric', day: 'numeric',
            hour: 'numeric'
          }});
        }});
        var observedData = points.map(function(p) {{
          return p.kind === 'observed' ? p.water_navd88 : null;
        }});
        var predictedData = points.map(function(p) {{
          return p.kind === 'predicted' ? p.water_navd88 : null;
        }});
        // Build a horizontal-line annotation per landmark, color-graded
        // blue (low) → red (high) so the band reads bottom-to-top as a
        // severity gradient.
        var landmarks = data.landmarks;
        var navd88s = landmarks.map(function(l) {{ return l.navd88; }});
        var minE = Math.min.apply(null, navd88s);
        var maxE = Math.max.apply(null, navd88s);
        function lerp(a, b, t) {{ return a + (b - a) * t; }}
        var annotations = {{}};
        landmarks.forEach(function(l, i) {{
          var t = (l.navd88 - minE) / (maxE - minE || 1);
          // Blue (31, 111, 235) → Red (209, 68, 74)
          var r = Math.round(lerp(31, 209, t));
          var g = Math.round(lerp(111, 68, t));
          var b = Math.round(lerp(235, 74, t));
          annotations['lm' + i] = {{
            type: 'line',
            yMin: l.navd88, yMax: l.navd88,
            borderColor: 'rgba(' + r + ',' + g + ',' + b + ',0.7)',
            borderWidth: 1,
            borderDash: [4, 3],
            label: {{
              display: true,
              content: l.label + ' (' + l.navd88.toFixed(2) + ')',
              position: 'end',
              backgroundColor: 'rgba(255,255,255,0.85)',
              color: 'rgb(' + r + ',' + g + ',' + b + ')',
              font: {{ size: 10 }},
              padding: 2,
            }}
          }};
        }});
        var ctx = document.getElementById('oscillation-chart').getContext('2d');
        new Chart(ctx, {{
          type: 'line',
          data: {{
            labels: labels,
            datasets: [
              {{
                label: 'Observed peak',
                data: observedData,
                borderColor: 'rgba(60,60,60,0.85)',
                backgroundColor: 'rgba(60,60,60,0.85)',
                pointStyle: 'rect',
                pointRadius: 6,
                spanGaps: true,
                showLine: false,
              }},
              {{
                label: 'Predicted peak',
                data: predictedData,
                borderColor: 'rgba(31, 111, 235, 0.9)',
                backgroundColor: 'rgba(31, 111, 235, 0.9)',
                pointStyle: 'circle',
                pointRadius: 6,
                spanGaps: true,
                showLine: false,
              }}
            ]
          }},
          options: {{
            responsive: true,
            plugins: {{
              annotation: {{ annotations: annotations }},
              tooltip: {{
                callbacks: {{
                  label: function(ctx) {{
                    var p = points[ctx.dataIndex];
                    if (!p) return ctx.formattedValue;
                    return [
                      (p.kind === 'observed' ? 'Observed' : 'Predicted'),
                      'Water at 342: ' + p.water_navd88.toFixed(2) + ' ft NAVD88',
                      'Sandy Hook: ' + p.sh_peak_mllw.toFixed(2) + ' ft MLLW',
                    ];
                  }}
                }}
              }},
              legend: {{ position: 'top' }}
            }},
            scales: {{
              x: {{
                title: {{ display: true, text: 'Tide peak (local time)' }},
                grid: {{ color: 'rgba(0,0,0,0.05)' }}
              }},
              y: {{
                title: {{ display: true, text: 'Water at 342 Bay (ft NAVD88)' }},
                grid: {{ color: 'rgba(0,0,0,0.06)' }},
                suggestedMin: Math.min(minE - 0.2,
                  Math.min.apply(null,
                    points.map(function(p) {{ return p.water_navd88; }}))),
                suggestedMax: Math.max(maxE + 0.2,
                  Math.max.apply(null,
                    points.map(function(p) {{ return p.water_navd88; }}))),
              }}
            }}
          }}
        }});
      }})();
    </script>
  </section>
"""


def _load_map_points_for_js():
    """Load assets/map_points.csv into a list of {x, y, navd88} dicts for
    inlining as JSON in HTML pages. Used by the client-side heat-map
    renderer (HANDOFF 9b.10). Skips rows with missing or non-numeric
    x/y/value."""
    csv_path = os.path.join(_REPO_ROOT, "assets", "map_points.csv")
    if not os.path.exists(csv_path):
        return []
    out = []
    with open(csv_path) as f:
        for row in csv.DictReader(f):
            try:
                x = float(row["x"])
                y = float(row["y"])
                v = float(row["value"])
            except (TypeError, ValueError, KeyError):
                continue
            out.append({"x": x, "y": y, "navd88": v})
    return out


def _client_map_section_html(forecast, container_class="heatmap", level=2,
                              base_map_url="icons/map_raw.png"):
    """Render an HTML section that displays the heat-map via client-side
    rendering (HANDOFF 9b.10) — replaces the prior <img> embed.

    Caller specifies `base_map_url` relative to the HTML page's location.
    For docs/index.html this is "icons/map_raw.png"; for per-tide pages
    at docs/tides/<slug>/index.html it's "../../icons/map_raw.png".

    Renders TWO canvases when rain is meaningful (tide+rain default
    visible, tide-only togglable) so the user can compare. When rain is
    not meaningful, a single canvas.

    Reading order in the page:
      (1) <canvas> elements with IDs and data-water-navd88 attrs
      (2) optional radio toggle for rain
      (3) inline JSON points + d3-delaunay + map-render.js + invocation
    """
    water_with_rain = _compute_map_water_level(forecast, include_rain=True)
    if water_with_rain is None:
        return ""

    rain_bonus_in = _rain_bonus_inches(forecast)
    rain_meaningful = rain_bonus_in > 0.0
    water_no_rain = (
        _compute_map_water_level(forecast, include_rain=False)
        if rain_meaningful else None
    )

    points = _load_map_points_for_js()
    if len(points) < 3:
        return ""

    peak_t = forecast.get("peak_time_local", "")
    peak_mllw = forecast.get("peak_forecast_observed_mllw") or 0.0
    title_with = (
        f"Predicted water level — {water_with_rain:.2f} ft NAVD88 "
        + (f"(SH {peak_mllw:.2f} + rain {rain_bonus_in:.1f}\")"
           if rain_meaningful
           else f"(SH {peak_mllw:.2f} ft MLLW @ {peak_t})")
    )
    title_no_rain = (
        f"Predicted water level — {water_no_rain:.2f} ft NAVD88 "
        f"— TIDE ONLY (no rain bonus)"
    ) if water_no_rain is not None else ""

    points_json = json.dumps(points)
    hh = "h" + str(level)
    canvas_styles = (
        "max-width:100%;height:auto;display:block;margin:8px auto;"
        "background:#fff;"
    )

    toggle_html = ""
    second_canvas_html = ""
    script_render = (
        "BarnacleMap.render({{ canvas: document.getElementById('heatmap-canvas'), "
        f"points: window.barnaclePoints, waterNavd88: {water_with_rain:.4f}, "
        f"baseMapUrl: '{base_map_url}', title: {json.dumps(title_with)} }});"
    ).replace("{{", "{").replace("}}", "}")
    intro_note = (
        '<p class="note">Blue overlay shows predicted tidal water depth across '
        'nearby topography. Darker blue = deeper. No meaningful rain forecast — '
        'overlay is tide-only.</p>'
    )

    if water_no_rain is not None:
        toggle_html = (
            '\n    <div class="heatmap-toggle">\n'
            '      <label><input type="radio" name="heatmap-mode" '
            'value="with-rain" checked> Tide + rain</label>\n'
            '      <label><input type="radio" name="heatmap-mode" '
            'value="no-rain"> Tide only</label>\n'
            '    </div>'
        )
        second_canvas_html = (
            f'\n    <canvas id="heatmap-canvas-no-rain" style="{canvas_styles}'
            f'display:none"></canvas>'
        )
        # Render both canvases on load; the toggle just flips display.
        no_rain_render = (
            f"\n      BarnacleMap.render({{ canvas: "
            f"document.getElementById('heatmap-canvas-no-rain'), "
            f"points: window.barnaclePoints, "
            f"waterNavd88: {water_no_rain:.4f}, "
            f"baseMapUrl: {json.dumps(base_map_url)}, "
            f"title: {json.dumps(title_no_rain)} }});"
        )
        script_render += no_rain_render
        intro_note = (
            '<p class="note">Blue overlay shows predicted water depth across '
            'nearby topography. Darker blue = deeper. Toggle between '
            'including the forecast rain bonus or tide-only (HANDOFF 9b.5).</p>'
        )

    toggle_script = ""
    if water_no_rain is not None:
        toggle_script = """
      (function() {
        var radios = document.querySelectorAll('input[name="heatmap-mode"]');
        var withRain = document.getElementById('heatmap-canvas');
        var noRain   = document.getElementById('heatmap-canvas-no-rain');
        radios.forEach(function(r) {
          r.addEventListener('change', function() {
            var show = r.value;
            withRain.style.display = (show === 'with-rain') ? 'block' : 'none';
            noRain.style.display   = (show === 'no-rain')   ? 'block' : 'none';
          });
        });
      })();
"""

    return f"""
  <section class="{container_class}">
    <{hh}>Predicted water depth (worst tide)</{hh}>
    {intro_note}{toggle_html}
    <canvas id="heatmap-canvas" style="{canvas_styles}"></canvas>{second_canvas_html}
    <script>
      window.barnaclePoints = {points_json};
    </script>
    <script src="https://cdn.jsdelivr.net/npm/d3-delaunay@6"></script>
    <script src="{_relpath_to_map_render_js(base_map_url)}"></script>
    <script>
      {script_render}{toggle_script}
    </script>
  </section>
"""


def _relpath_to_map_render_js(base_map_url):
    """Where does docs/map-render.js live relative to the page?

    We use the same relative depth as base_map_url: if the page links to
    'icons/map_raw.png' the page is at docs/, so map-render.js is
    'map-render.js'. If the page links to '../../icons/map_raw.png',
    the page is at docs/tides/<slug>/, so map-render.js is
    '../../map-render.js'.
    """
    if base_map_url.startswith("../../"):
        return "../../map-render.js"
    if base_map_url.startswith("../"):
        return "../map-render.js"
    return "map-render.js"


def _tide_slug(tide_time_str):
    """Convert a NOAA tide time string ('YYYY-MM-DD HH:MM') to a
    filesystem-safe slug ('YYYY-MM-DDTHH-MM') for per-tide page paths.
    Returns empty string for unparseable input.

    HANDOFF 9b.2 — each upcoming high tide gets a deep-link page at
    `docs/tides/<slug>/`."""
    if not tide_time_str:
        return ""
    try:
        # Normalize whitespace; drop seconds if present.
        s = tide_time_str.strip()[:16]
        # Expected shape: "YYYY-MM-DD HH:MM"
        if " " in s:
            date_part, time_part = s.split(" ", 1)
        elif "T" in s:
            date_part, time_part = s.split("T", 1)
        else:
            return ""
        return f"{date_part}T{time_part.replace(':', '-')}"
    except Exception:
        return ""


def write_per_tide_pages(forecast, docs_root):
    """Write per-tide deep-link pages for each upcoming high tide.

    For each tide in forecast["all_tides"] generates:
      docs/tides/<slug>/index.html      static snapshot
      docs/tides/<slug>/forecast.json   the tide's prediction object
      docs/tides/<slug>/evolution.csv   slice of data/predictions_log.csv

    HANDOFF 9b.2. Per-tide pages are generated eagerly for upcoming
    tides (lazy generation can come later if maintenance burden grows).
    """
    tides_root = os.path.join(docs_root, "tides")
    os.makedirs(tides_root, exist_ok=True)
    n_written = 0
    for tide in forecast.get("all_tides") or []:
        slug = _tide_slug(tide.get("time", ""))
        if not slug:
            continue
        tide_dir = os.path.join(tides_root, slug)
        os.makedirs(tide_dir, exist_ok=True)

        # forecast.json — this tide's prediction object
        with open(os.path.join(tide_dir, "forecast.json"), "w") as f:
            json.dump(tide, f, indent=2, default=str)

        # evolution.csv — filter predictions_log.csv to this tide's
        # target_tide_time. Append-only-of-a-derived-view: we overwrite
        # this file on each run since predictions_log.csv is the source.
        evo_path = os.path.join(tide_dir, "evolution.csv")
        if os.path.exists(PREDICTIONS_LOG_PATH):
            try:
                target_time = tide.get("time", "")
                rows = []
                with open(PREDICTIONS_LOG_PATH) as src:
                    reader = csv.DictReader(src)
                    for row in reader:
                        if row.get("target_tide_time") == target_time:
                            rows.append(row)
                if rows:
                    with open(evo_path, "w", newline="") as out:
                        writer = csv.DictWriter(out,
                            fieldnames=PREDICTIONS_LOG_FIELDS)
                        writer.writeheader()
                        for row in rows:
                            writer.writerow(row)
                elif os.path.exists(evo_path):
                    # No matching rows yet; leave existing file alone
                    pass
            except Exception as e:
                print(f"WARNING: evolution.csv write failed for {slug}: {e}",
                      flush=True)

        # index.html — static per-tide snapshot
        with open(os.path.join(tide_dir, "index.html"), "w") as f:
            f.write(render_per_tide_page(tide, forecast))
        n_written += 1

    if n_written:
        print(f"Wrote {n_written} per-tide page(s) under {tides_root}")


def render_per_tide_page(tide, forecast):
    """Render a single per-tide deep-link HTML page. Focuses on ONE tide:
    its predicted peak, surge breakdown, depths at landmarks, link to
    evolution.csv (the per-tide slice of the master predictions log).

    The page is at docs/tides/<slug>/index.html so it's two levels deep
    from the repo root — all asset paths get a "../../" prefix.

    HANDOFF 9b.2."""
    td = tide["depths_in"]
    regime = td["regime"]
    time_str = tide["time"]
    short, above_in, rel_in = landmark_summary(td, tide["forecast_peak_mllw"])

    # Per-tide heat-map: build a fake "forecast" with this tide as the
    # worst-case so _client_map_section_html renders for THIS tide's
    # water level (not the home page's worst-case). HANDOFF 9b.10.
    tide_as_forecast = {
        "peak_forecast_observed_mllw": tide["forecast_peak_mllw"],
        "cold_lockout": forecast.get("cold_lockout", False),
        "peak_rain_rate_in_hr": tide.get("peak_rain_in_hr") or 0.0,
        "peak_time_local": tide["time"],
    }
    tide_heatmap_section = _client_map_section_html(
        tide_as_forecast,
        container_class="heatmap",
        level=2,
        base_map_url="../../icons/map_raw.png",
    )

    # Landmark rows
    rows = ""
    for key, label, elev, sh in LANDMARKS:
        depth = td.get(key, 0.0) or 0.0
        wet = depth > 0
        row_cls = ' class="wet"' if wet else ""
        rows += (
            f'<tr{row_cls}>'
            f'<td>{label}</td>'
            f'<td>{elev:.2f}</td>'
            f'<td>{sh:.2f}</td>'
            f'<td>{depth:+.1f}&Prime;</td>'
            f'</tr>'
        )

    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Tide {time_str} — Bay Ave Barnacle</title>
<link rel="stylesheet" href="../../style.css">
</head>
<body>
<main>
  <header>
    <h1>High tide @ {format_time_full(time_str)}</h1>
    <p class="subtitle"><a href="../../">&larr; Back to today's forecast</a></p>
  </header>

  <section class="regime regime-{regime}">
    <div class="regime-label">{regime.upper()}</div>
    <div class="regime-summary">{REGIME_GLOSSARY.get(regime, '')}.
       Peak forecast: <b>{tide['forecast_peak_mllw']:.2f} ft MLLW</b> Sandy Hook.</div>
  </section>

  <section class="forecast">
    <h2>This tide</h2>
    <dl>
      <dt>High tide time</dt><dd>{format_time_full(time_str)}</dd>
      <dt>Predicted tide (astronomical)</dt><dd>{tide['predicted_mllw']:.2f} ft MLLW</dd>
      <dt>Surge</dt><dd>{tide['surge_ft']:+.2f} ft</dd>
      <dt>Forecast peak (tide + surge)</dt><dd>{tide['forecast_peak_mllw']:.2f} ft MLLW</dd>
      <dt>Surge source</dt><dd>{tide.get('source', '')}</dd>
      <dt>Peak rainfall in ±90 min window</dt><dd>{(tide.get('peak_rain_in_hr') or 0):.2f} in/hr</dd>
      <dt>Highest landmark reached</dt><dd>{short} ({above_in:+.1f}&Prime; above; {rel_in:+.1f}&Prime; rel to lowest landmark)</dd>
    </dl>
  </section>

{tide_heatmap_section}
  <section class="landmarks">
    <h2>Predicted depths at landmarks</h2>
    <table class="landmark-table">
      <thead><tr><th>Landmark</th><th>NAVD88</th><th>SH threshold (MLLW)</th><th>Predicted depth</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
    <p class="note">Depth is the height of water above each landmark
       elevation, in inches. Negative = water below this landmark.</p>
  </section>

  <section class="evolution">
    <h2>Prediction convergence</h2>
    <p>How the forecast for this tide has evolved as the tide approaches.
       Each point is one prediction event from
       <a href="evolution.csv">evolution.csv</a> (slice of the
       <a href="https://github.com/JohnUrban/barnacle/blob/main/data/predictions_log.csv">master
       predictions log</a>). x = hours from peak (negative = before),
       y = predicted Sandy Hook peak in ft MLLW. HANDOFF 9b.4(a).</p>
    <canvas id="convergence-chart" width="800" height="380"
            style="max-width:100%;height:auto;display:block;margin:8px auto"></canvas>
    <p id="convergence-note" class="note" style="text-align:center"></p>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js"></script>
    <script>
      (function() {{
        var note = document.getElementById('convergence-note');
        fetch('evolution.csv').then(function(r) {{
          if (!r.ok) throw new Error('evolution.csv not found');
          return r.text();
        }}).then(function(text) {{
          var lines = text.trim().split('\\n');
          if (lines.length < 2) {{
            note.textContent = 'No prediction history yet for this tide. '
              + 'The chart fills in as the hourly workflow logs predictions.';
            return;
          }}
          var headers = lines[0].split(',');
          var idx = {{}};
          headers.forEach(function(h, i) {{ idx[h] = i; }});
          var points = [];
          for (var i = 1; i < lines.length; i++) {{
            var cols = lines[i].split(',');
            var hu = parseFloat(cols[idx['hours_until_peak']]);
            var sh = parseFloat(cols[idx['sh_peak_mllw_predicted']]);
            var wat = parseFloat(cols[idx['water_navd88_predicted']]);
            var conf = cols[idx['confidence_level']] || '';
            if (isNaN(hu) || isNaN(sh)) continue;
            // x = "hours from peak" (negative = before; convergence reads left→right)
            points.push({{ x: -hu, y: sh, water: wat, conf: conf }});
          }}
          points.sort(function(a, b) {{ return a.x - b.x; }});
          if (points.length < 2) {{
            note.textContent = 'Only one prediction logged so far for this tide. '
              + 'The convergence curve will appear after the next workflow run.';
          }} else {{
            note.textContent = points.length + ' predictions logged. '
              + 'Convergence pattern reveals how the forecast settles as the tide approaches.';
          }}
          var ctx = document.getElementById('convergence-chart').getContext('2d');
          new Chart(ctx, {{
            type: 'line',
            data: {{
              datasets: [{{
                label: 'Predicted SH peak (ft MLLW)',
                data: points,
                borderColor: 'rgba(31, 111, 235, 0.9)',
                backgroundColor: 'rgba(31, 111, 235, 0.15)',
                pointRadius: 4,
                pointHoverRadius: 6,
                tension: 0.2,
              }}]
            }},
            options: {{
              responsive: true,
              plugins: {{
                tooltip: {{
                  callbacks: {{
                    label: function(ctx) {{
                      var p = ctx.raw;
                      var lines = [
                        'Predicted SH peak: ' + p.y.toFixed(2) + ' ft MLLW',
                      ];
                      if (!isNaN(p.water)) {{
                        lines.push('Water at 342: ' + p.water.toFixed(2) + ' ft NAVD88');
                      }}
                      lines.push('Made ' + Math.abs(p.x).toFixed(1) + ' h '
                        + (p.x < 0 ? 'before' : 'after') + ' peak');
                      if (p.conf) lines.push('Confidence: ' + p.conf.toUpperCase());
                      return lines;
                    }}
                  }}
                }},
                legend: {{ display: false }}
              }},
              scales: {{
                x: {{
                  type: 'linear',
                  title: {{ display: true,
                           text: 'Hours from peak (negative = before)' }},
                  grid: {{ color: function(c) {{
                    return c.tick.value === 0 ? 'rgba(217, 119, 6, 0.5)' : 'rgba(0,0,0,0.06)';
                  }} }}
                }},
                y: {{
                  title: {{ display: true, text: 'Predicted SH peak (ft MLLW)' }},
                  grid: {{ color: 'rgba(0,0,0,0.06)' }}
                }}
              }}
            }}
          }});
        }}).catch(function(e) {{
          note.textContent = 'No convergence data available yet ('
            + e.message + '). Will populate after a few workflow runs.';
        }});
      }})();
    </script>
  </section>

  <footer>
    <p><a href="https://github.com/JohnUrban/barnacle">Source code &amp; model</a></p>
    <p style="font-size:11px;color:#888">Per-tide page generated by the
       daily/hourly workflow. Snapshot of one forecast event; the full
       picture lives on the <a href="../../">home page</a>.</p>
  </footer>
</main>
</body>
</html>
"""


def render_html_page(forecast, map_url=None, map_url_no_rain=None):
    """
    Standalone HTML page for GitHub Pages publication.
    Like the email HTML but with proper <head>, mobile meta, and footer
    links to source repo + archive.

    The heat-map is rendered CLIENT-SIDE (HANDOFF 9b.10) from the static
    map_points.csv data and the current water level. The legacy
    map_url / map_url_no_rain parameters are kept for backwards-compat
    but unused; the client-side render replaces them.
    """
    _ = map_url, map_url_no_rain  # legacy parameters, kept for compat
    d = forecast["depths_in"]
    regime = d["regime"]
    peak_t = forecast["peak_time_local"]
    peak_ft = forecast["peak_forecast_observed_mllw"]
    today = dt.date.today().isoformat()
    cold = forecast["cold_lockout"]
    all_tides = forecast.get("all_tides", [])

    # Heat-map section: client-side render (HANDOFF 9b.10).
    map_section = _client_map_section_html(
        forecast,
        container_class="heatmap",
        level=2,
        base_map_url="icons/map_raw.png",
    )

    # Build the all-tides table rows (new column layout). Each row carries:
    #  - regime class for severity-colored backgrounds (HANDOFF 9b.2)
    #  - worst-tide class on the headlined row
    #  - link to per-tide deep page (docs/tides/<slug>/) — HANDOFF 9b.2
    #  - data-hours-from-now attribute for the JS duration toggle
    #    (HANDOFF 9b.2 part 2)
    tide_rows = ""
    for t in all_tides:
        td = t["depths_in"]
        is_worst = (t["time"] == peak_t)
        regime_class = f"regime-{td['regime']}"
        classes = ["tide-row", regime_class]
        if is_worst:
            classes.append("worst-tide")
        row_class = f' class="{" ".join(classes)}"'
        hours = t.get("hours_from_now")
        data_attr = f' data-hours-from-now="{hours:.2f}"' if hours is not None else ""
        short, above_in, rel_in = landmark_summary(td, t["forecast_peak_mllw"])
        slug = _tide_slug(t["time"])
        time_cell = (
            f'<a href="tides/{slug}/">{format_time_full(t["time"])}</a>'
            if slug else format_time_full(t["time"])
        )
        tide_rows += (
            f'<tr{row_class}{data_attr}>'
            f'<td>{time_cell}</td>'
            f'<td>{t["predicted_mllw"]:.2f}</td>'
            f'<td>{t["surge_ft"]:+.2f}</td>'
            f'<td><b>{t["forecast_peak_mllw"]:.2f}</b></td>'
            f'<td>{short}</td>'
            f'<td>{above_in:+.1f}&Prime;</td>'
            f'<td>{rel_in:+.1f}&Prime;</td>'
            f'<td>{td["regime"]}</td>'
            f'</tr>'
        )

    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Bay Ave Barnacle — {today}</title>
<link rel="stylesheet" href="style.css">
<!-- PWA / iOS home-screen install (HANDOFF item 27, Stage 1) -->
<link rel="manifest" href="manifest.json">
<link rel="apple-touch-icon" href="icons/apple-touch-icon.png">
<link rel="icon" type="image/png" sizes="192x192" href="icons/icon-192.png">
<link rel="icon" type="image/png" sizes="512x512" href="icons/icon-512.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="Barnacle">
<meta name="theme-color" content="#0f4064">
<meta name="description" content="Hyperlocal flood forecast for 342 Bay Avenue, Highlands NJ — daily prediction at 8 named landmarks.">
</head>
<body>
<main>
  <header>
    <h1>Bay Ave Barnacle</h1>
    <p class="subtitle">Hyperlocal flood forecast for 342 Bay Avenue, Highlands NJ</p>
  </header>

  {_render_summary_html(forecast)}

  <section class="regime regime-{regime}">
    <div class="regime-label">{regime.upper()}</div>
    <div class="regime-summary">{REGIME_GLOSSARY.get(regime, '')}. Worst-case peak {peak_ft:.2f} ft MLLW at {format_time_full(peak_t)}.</div>
  </section>

  <section class="tides">
    <h2>Upcoming high tides</h2>
    <div class="duration-toggle">
      Show:
      <label><input type="radio" name="duration" value="24"> 24h</label>
      <label><input type="radio" name="duration" value="48"> 48h</label>
      <label><input type="radio" name="duration" value="72" checked> 72h</label>
    </div>
    <table class="tide-table">
      <thead><tr><th>Time</th><th>Pred (ft)</th><th>Surge</th><th>Peak (ft)</th><th>Highest landmark</th><th>Above</th><th>Rel</th><th>Regime</th></tr></thead>
      <tbody>{tide_rows}</tbody>
    </table>
    <p class="note">Highlighted row is the worst case headlined above.
       <b>Above</b> = inches above the highest exceeded landmark (negative if water below the lowest landmark).
       <b>Rel</b> = inches above the lowest landmark (lowest road corner, 3.64 NAVD88) — always.
       Surge persistence is increasingly unreliable for tides beyond ~24h out
       — use the longer windows for planning, not for trust.</p>
    <script>
      (function() {{
        var radios = document.querySelectorAll('input[name="duration"]');
        function applyFilter(hours) {{
          var rows = document.querySelectorAll('.tide-table tbody tr.tide-row');
          rows.forEach(function(tr) {{
            var h = parseFloat(tr.getAttribute('data-hours-from-now'));
            tr.style.display = (isNaN(h) || h <= hours) ? '' : 'none';
          }});
        }}
        radios.forEach(function(r) {{
          r.addEventListener('change', function() {{
            applyFilter(parseFloat(r.value));
          }});
        }});
        // Apply the default (72) on load
        applyFilter(72);
      }})();
    </script>
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
{map_section}
{_render_oscillation_section(forecast)}
  {_render_rain_timing_html(forecast)}

  {_landmarks_section_html(forecast, wrapper='section')}

  {_render_recent_history_html(forecast)}

  {_render_accuracy_html(forecast)}

  {_render_low_tides_html(forecast)}

  {_render_lookahead_html(forecast)}

  <section class="reference">
    <h2>Reference scale</h2>
    <p>Sandy Hook observed water level (MLLW):</p>
    <ul>
      <li>&lt; 6.02 ft — dry, nothing visible</li>
      <li>6.02 ft — water emerges from lowest storm grate (Central Ave south)</li>
      <li>6.06 ft — lowest road corner across Bay first wets (visible from window)</li>
      <li>6.20 ft — water at gutter / curb edge (don't park there)</li>
      <li>6.33 ft — water emerges from corner storm grate at Bay+Central (Pathway B)</li>
      <li>6.58 ft — water tops curb at walkway (flood onset at property)</li>
      <li>6.78 ft — Bay Ave road middle covered</li>
      <li>6.96 ft — intersection center submerged</li>
      <li>7.00 ft — water at lawn / walkway step</li>
      <li>7.50 ft — water at front porch first step</li>
      <li>&ge; 7.9 ft — severe (well past porch)</li>
    </ul>
  </section>

  <section class="reference">
    <h2>Regime glossary</h2>
    <p>The single word in the subject line (DRY / STREET / LIGHT / MODERATE / SEVERE) summarises severity based on water depth at the curb.</p>
    <ul>
      <li><b>dry</b> — {REGIME_GLOSSARY['dry']}</li>
      <li><b>street</b> — {REGIME_GLOSSARY['street']}</li>
      <li><b>light</b> — {REGIME_GLOSSARY['light']}</li>
      <li><b>moderate</b> — {REGIME_GLOSSARY['moderate']}</li>
      <li><b>severe</b> — {REGIME_GLOSSARY['severe']}</li>
      <li><b>cold_lockout</b> — {REGIME_GLOSSARY['cold_lockout']}</li>
    </ul>
  </section>

  <footer>
    <p>Model v0.6. Local enhancement +0.40 ft. Rain term saturates at 8&Prime;.
       Updated daily at 5 AM ET.</p>
    <p><a href="https://github.com/JohnUrban/barnacle">Source code &amp; model</a> &middot;
       <a href="archive/">Past forecasts</a> &middot;
       <a href="barnacle-widget.js">iOS widget script (Scriptable)</a></p>
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


def _compute_map_water_level(forecast, include_rain=True):
    """NAVD88 water level (ft) for the worst tide today, for heat-map
    rendering. Returns None when no overlay should be drawn (cold lockout
    suppressing flooding, or peak below all map points).

    With `include_rain=True` (default), folds in the rain term as a
    uniform water-level addition. Per the user's "water is level"
    framing (HANDOFF 9b.5 + 9c.4): rain raises the surface uniformly;
    depth at each point follows from `water_navd88 - elev`.

    Uses v0.6's `rain_add = 8 * tanh(rate)` inches at street level
    (the strongest of v0.6's per-landmark rain bonuses), divided by
    12 for feet. This slightly over-states water level at lawn/porch
    vs v0.6's per-landmark shedding (the shedding constants subtract
    2-4 inches at higher points), but is internally consistent: the
    map is one water-level surface, and all depths derive from it.
    v0.7 9c.4 will make this the canonical model formulation.

    `include_rain=False` returns the bare tide-only water level, used
    to render a comparison "no-rain" map when rain is forecast.
    """
    peak_mllw = forecast.get("peak_forecast_observed_mllw")
    cold = forecast.get("cold_lockout", False)
    if peak_mllw is None:
        return None
    if cold and peak_mllw < 8.0:
        return None
    water = peak_mllw + LOCAL_ENHANCEMENT_FT + MLLW_TO_NAVD88_OFFSET
    if include_rain:
        rain_rate = forecast.get("peak_rain_rate_in_hr") or 0.0
        if rain_rate > 0.1:
            rain_add_in = RAIN_SATURATION_IN * math.tanh(rain_rate)
            water += rain_add_in / 12.0
    return water


def _rain_bonus_inches(forecast):
    """Returns the rain bonus added to the water level (inches), or 0.
    Used by callers that need to label maps / titles with the rain
    contribution. Matches the formula in _compute_map_water_level."""
    rain_rate = forecast.get("peak_rain_rate_in_hr") or 0.0
    if rain_rate <= 0.1:
        return 0.0
    return RAIN_SATURATION_IN * math.tanh(rain_rate)


def _render_heatmap(out_path, water_navd88, title):
    """Invoke assets/render_map.py as a subprocess to write the heat-map
    PNG. Subprocess keeps matplotlib out of this script's import path
    (it's only needed when --write-map is set)."""
    import subprocess, sys
    here = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(here)
    script = os.path.join(repo_root, "assets", "render_map.py")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    cmd = [
        sys.executable, script,
        "--water-level", f"{water_navd88:.2f}",
        "--out", out_path,
        "--title", title,
    ]
    subprocess.run(cmd, check=True)


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
    parser.add_argument("--write-json", metavar="PATH", default=None,
                        help="Write the raw forecast dict to PATH as JSON. "
                             "Machine-readable archive companion to --write-html. "
                             "Datetime values are stringified; otherwise unchanged. "
                             "Required input for the forecast accuracy log.")
    parser.add_argument("--write-map", metavar="PATH", default=None,
                        help="Write a heat-map PNG of predicted water depth "
                             "(blue overlay) to PATH. Calls assets/render_map.py "
                             "as a subprocess; requires matplotlib+numpy.")
    parser.add_argument("--no-send", action="store_true",
                        help="Skip email sending even if SMTP env vars are set. "
                             "Useful when only writing HTML.")
    args = parser.parse_args()

    try:
        forecast = build_forecast()
        _attach_summary_and_confidence(forecast)
    except Exception as e:
        print(f"ERROR fetching forecast: {e}", flush=True)
        raise

    # Append to the master predictions log (HANDOFF 9b.3). Append-only.
    # Wrapped: a logging failure must not break the daily forecast run.
    try:
        append_predictions_log(forecast)
    except Exception as e:
        print(f"WARNING: append_predictions_log failed: {e}", flush=True)

    if args.json:
        print(json.dumps(forecast, indent=2, default=str))
        return

    # Render heat-map PNG(s). When rain is forecast, we render TWO maps —
    # one with the rain bonus folded into the water level (9b.5), one
    # tide-only — so the HTML page can offer a toggle and the user can
    # see what rain alone would add.
    map_url = None
    map_url_no_rain = None
    if args.write_map:
        rain_bonus_in = _rain_bonus_inches(forecast)
        rain_meaningful = rain_bonus_in > 0.0

        water_navd88 = _compute_map_water_level(forecast, include_rain=True)
        if water_navd88 is None:
            print("Skipping heat-map: cold lockout suppressing flooding "
                  "or no peak data.")
        else:
            peak_t = forecast.get("peak_time_local", "")
            peak_mllw = forecast["peak_forecast_observed_mllw"]
            if rain_meaningful:
                title = (
                    f"Predicted water level — {water_navd88:.2f} ft NAVD88 "
                    f"(SH {peak_mllw:.2f} + rain {rain_bonus_in:.1f}\" @ {peak_t})"
                )
            else:
                title = (
                    f"Predicted water level — {water_navd88:.2f} ft NAVD88 "
                    f"(SH {peak_mllw:.2f} ft MLLW @ {peak_t})"
                )
            out_path = os.path.abspath(args.write_map)
            try:
                _render_heatmap(out_path, water_navd88, title)
                print(f"Wrote heat-map: {args.write_map}")
                # Compute URL for HTML embed
                if args.write_html:
                    html_dir = os.path.dirname(os.path.abspath(args.write_html))
                    map_url = os.path.relpath(out_path, html_dir)
                else:
                    map_url = out_path
            except Exception as e:
                print(f"WARNING: heat-map render failed: {e}", flush=True)

            # Second map: no-rain comparison (only when rain is meaningful)
            if rain_meaningful:
                water_no_rain = _compute_map_water_level(
                    forecast, include_rain=False
                )
                if water_no_rain is not None:
                    # Derive path: …map_today.png → …map_today_no_rain.png
                    base, ext = os.path.splitext(out_path)
                    out_path_nr = base + "_no_rain" + ext
                    title_nr = (
                        f"Predicted water level — {water_no_rain:.2f} ft NAVD88 "
                        f"— TIDE ONLY (no rain bonus) — SH {peak_mllw:.2f} ft MLLW"
                    )
                    try:
                        _render_heatmap(out_path_nr, water_no_rain, title_nr)
                        print(f"Wrote heat-map (no rain): {out_path_nr}")
                        if args.write_html:
                            map_url_no_rain = os.path.relpath(
                                out_path_nr, html_dir
                            )
                        else:
                            map_url_no_rain = out_path_nr
                    except Exception as e:
                        print(f"WARNING: no-rain heat-map render failed: {e}",
                              flush=True)

    # Fallback: even when --write-map is NOT passed (hourly runs under
    # 9b.1), embed the previously-rendered map if one exists on disk at
    # the expected path. The map may be slightly stale within the day
    # (it regenerates at the 09:00 UTC daily run) but doesn't disappear
    # from the page between daily refreshes. 9b.10 (client-side render)
    # replaces this with always-fresh map data.
    if map_url is None and args.write_html:
        html_dir = os.path.dirname(os.path.abspath(args.write_html))
        candidate = os.path.join(html_dir, "icons", "map_today.png")
        if os.path.exists(candidate):
            map_url = os.path.relpath(candidate, html_dir)
        # Same fallback for the no-rain map
        candidate_nr = os.path.join(html_dir, "icons", "map_today_no_rain.png")
        if os.path.exists(candidate_nr):
            map_url_no_rain = os.path.relpath(candidate_nr, html_dir)

    subject, text, html = render_email(forecast)

    # Write standalone HTML page if requested
    if args.write_html:
        page_html = render_html_page(
            forecast, map_url=map_url, map_url_no_rain=map_url_no_rain
        )
        out_path = os.path.abspath(args.write_html)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w") as f:
            f.write(page_html)
        print(f"Wrote HTML: {args.write_html}")

        # Generate per-tide deep-link pages (HANDOFF 9b.2). Each upcoming
        # tide gets docs/tides/<slug>/{index.html,forecast.json,evolution.csv}.
        # Wrapped: a per-tide-page failure must not break the daily run.
        try:
            docs_root = os.path.dirname(out_path)
            write_per_tide_pages(forecast, docs_root)
        except Exception as e:
            print(f"WARNING: write_per_tide_pages failed: {e}", flush=True)

    # Write JSON archive if requested
    if args.write_json:
        out_path = os.path.abspath(args.write_json)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(forecast, f, indent=2, default=str)
        print(f"Wrote JSON: {args.write_json}")

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
