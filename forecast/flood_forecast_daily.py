#!/usr/bin/env python3
"""
Daily flood forecast for 342 Bay Ave, Highlands NJ.

Pulls Sandy Hook tide forecast, current observed water level (for surge),
NWS rainfall + QPF and temperature forecasts for Highlands, applies the
current flood model (see CURRENT_MODEL_VERSION + model/ docs: tide-keyed
level path + v0.9-gamma dual pluvial pathway), renders the website,
widget JSON, and per-tide pages, and sends an email report.

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
import re
import csv
import math
import json
import smtplib
import datetime as dt
import time as _time
from zoneinfo import ZoneInfo

# NOAA CO-OPS queries with time_zone=lst_ldt interpret begin_date /
# end_date as STATION-LOCAL time (US/Eastern for Sandy Hook). Passing
# UTC-now strings shifts the window +4/5 h — caught 2026-07-06 when
# the widget chart's hour labels came out 4 h late. Use this for any
# begin/end sent to an lst_ldt query.
STATION_TZ = ZoneInfo("America/New_York")


def _station_local_now():
    """Now in the Sandy Hook station's local timezone (naive)."""
    return dt.datetime.now(STATION_TZ).replace(tzinfo=None)
from email.message import EmailMessage
from urllib.request import Request, urlopen
from urllib.parse import urlencode

# ============================================================
# v0.4 model parameters - update these as the model improves
# ============================================================
LOCAL_ENHANCEMENT_FT = 0.00        # v0.8 (2026-06-16): the 4-event-mean conservative value
# v0.8 calibration (2026-06-16): the 6/15 PM tide (SH 7.289) was a
# storm-condition event with a late wind veer from offshore (NW
# afternoon) to onshore (NNE at peak). v0.7 (-0.13) under-predicted
# by 1.5" at curb. Tonight's implied enhancement at peak was ~0,
# vs -0.13 on the 3 prior regular-tide events (5/18, 5/31, 6/14, all
# with offshore peak winds). v0.8 takes the conservative value:
#   - Main model: enhancement = 0 (matches storm conditions)
#   - Wind adjustment (compute_wind_adjustment): reports a -0.13 ft
#     "expected actual" line when forecast wind at peak is in the
#     offshore sector (S/SSW/SW/WSW/SSE)
# This errs on the safer / over-predict side per user preference; the
# wind-adjusted secondary line gives the calibrated regular-tide
# estimate when conditions warrant.

# Landmark elevations at 342 Bay Ave (NAVD88, ft).
# Sandy Hook MLLW threshold for each = landmark + 2.82
# (= +2.82 datum offset − 0.00 local enhancement; v0.8 promotion 2026-06-16).
GRATE_SW              = 3.52   # SW distal grate across Bay (lowest grate)   (SH 6.34)
GRATE_SE              = 3.60   # SE proximal grate across Bay                (SH 6.42)
CORNER_SE             = 3.64   # SE pavement corner across Bay               (SH 6.46)
CORNER_SW             = 3.64   # SW pavement corner across Bay               (SH 6.46)
GRATE_BAY_AVE_UPSTREAM = 3.64  # upstream grate (low-point ref; uneven 3.64-3.78) (SH 6.46)
GUTTER_WALKWAY        = 3.78   # street-curb interface at walkway            (SH 6.60)
GRATE_NE              = 3.80   # user's corner grate                         (SH 6.62)
GRATE_NW              = 3.80   # NW corner grate across Central              (SH 6.62)
CORNER_NE             = 3.91   # NE pavement corner (not the grate)          (SH 6.73)
CORNER_NW             = 3.91   # NW pavement corner (not the grate)          (SH 6.73)
CURB_TOP              = 4.16   # Bay Ave side at walkway                     (SH 6.98)
SIDEWALK_UNDER_LAWN_STEP = 4.33 # Sidewalk where it meets the lawn-step face (SH 7.15)
ROAD_MIDDLE           = 4.36   # Bay Ave centerline at user's spot           (SH 7.18)
INTERSECTION_HIGHPOINT = 4.54  # Bay+Central intersection (local high)       (SH 7.36)
# v0.9 porch ladder (2026-07-06): lawn step + porch geometry re-anchored
# from the 7/6 pluvial event (photo-timeline interpolation + user's
# ordering constraint) + taped riser heights (assets/porch-measurements.txt).
# The old FRONT_PORCH_STEP=5.08 corresponded to no physical feature — it
# was fabricated in v0.5.1 as lawn_step(4.58)+6"; both inputs were wrong.
LAWN_STEP             = 4.66   # lawn-step top (was 4.58 inferred)           (SH 7.48)
PORCH_STEP_BASE       = 4.68   # walkway at the bottom porch step            (SH 7.50)
PORCH_STEP1_TOP       = 5.41   # top of first porch step (8.75" riser)       (SH 8.23)
PORCH_DECK            = 8.08   # porch platform (5 risers, 40.75" total)     (SH 10.90)

# Stratified landmarks (ascending severity). First several are sub-curb
# sentinels for early-warning visual check + parking decisions. SH
# thresholds are recomputed under v0.8 enhancement (0.00).
LANDMARKS = [
    ("grate_SW",              "SW distal grate across Bay",       GRATE_SW,              6.34),
    ("grate_SE",              "SE proximal grate across Bay",     GRATE_SE,              6.42),
    ("corner_SE",             "SE corner across Bay",             CORNER_SE,             6.46),
    ("corner_SW",             "SW corner across Bay",             CORNER_SW,             6.46),
    ("grate_bay_ave_upstream", "Bay Ave upstream grate",          GRATE_BAY_AVE_UPSTREAM, 6.46),
    ("gutter_walkway",        "Gutter / curb edge at walkway",    GUTTER_WALKWAY,        6.60),
    ("grate_NE",              "Storm grate at user's corner (NE)", GRATE_NE,              6.62),
    ("grate_NW",              "NW corner grate across Central",   GRATE_NW,              6.62),
    ("corner_NE",             "NE corner pavement",               CORNER_NE,             6.73),
    ("corner_NW",             "NW corner pavement",               CORNER_NW,             6.73),
    ("curb",                  "Curb TOP at walkway",              CURB_TOP,              6.98),
    ("sidewalk_under_walkway_lawn_step", "Sidewalk under walkway lawn-step", SIDEWALK_UNDER_LAWN_STEP, 7.15),
    ("road_middle",           "Bay Ave road middle",              ROAD_MIDDLE,           7.18),
    ("intersection_highpoint", "Intersection high point",         INTERSECTION_HIGHPOINT, 7.36),
    ("lawn_step",             "Lawn / walkway step",              LAWN_STEP,             7.48),
    ("porch_step_base",       "Bottom of porch steps",            PORCH_STEP_BASE,       7.50),
    ("porch_step1_top",       "Top of first porch step",          PORCH_STEP1_TOP,       8.23),
    ("porch_deck",            "Porch deck (platform)",            PORCH_DECK,           10.90),
]
# Subset used for the "seasonality typical vs MTD" table — curb-and-up only.
# Sub-curb landmarks would dominate the table (counts of 8-12 days/month
# in recent decades); they're shown in the daily depth table instead.
SEASONALITY_LANDMARK_KEYS = {"curb", "road_middle", "intersection_highpoint",
                             "lawn_step", "porch_step_base"}
# Seasonality CSV regenerated 2026-07-06 with v0.9 keys + thresholds
# (analyze.py refresh) — the alias shim from earlier that day is now
# empty. Keep the mechanism: it protects the display join across any
# future rename until the next annual refresh lands.
SEASONALITY_KEY_ALIASES = {}
# Curated landmarks for the oscillation chart on the home page (9b.4(b)).
# Five entries — fewer than the full landmark set — so labels don't crowd
# each other on the chart's y-axis. Updated for v0.7 (2026-06-14).
# Aligned 2026-07-07 (mobile/grammar pass) to the water-level chart's
# landmark set + shared palette, so the two charts read as one system
# (chart grammar: landmark lines live in the LEGEND, learned by color).
OSCILLATION_LANDMARK_KEYS = {
    "grate_SW",               # 3.52 — lowest grate, first water (black, solid)
    "gutter_walkway",         # 3.78 — move-the-car threshold (green)
    "curb",                   # 4.16 — curb TOP at walkway (red)
    "lawn_step",              # 4.66 — lawn / walkway step (purple)
    "porch_step1_top",        # 5.41 — top of first porch step (brown)
}

MLLW_TO_NAVD88_OFFSET = -2.82  # NAVD88 = MLLW + offset

# Derived SH-MLLW thresholds used across report sections. Audit
# 2026-07-06 found the old v0.6 curb value (6.58) hardcoded in the
# recent-history classifier, the SLR newly-wet band, and the near-miss
# line — all silently stale through the v0.7-v0.9 promotions. Deriving
# them here means the next landmark revision propagates automatically.
SH_CURB_THRESHOLD  = round(CURB_TOP - MLLW_TO_NAVD88_OFFSET - LOCAL_ENHANCEMENT_FT, 2)   # 6.98
SH_FIRST_WATER     = round(GRATE_SW - MLLW_TO_NAVD88_OFFSET - LOCAL_ENHANCEMENT_FT, 2)   # 6.34

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

# Recent-past tide visibility: keep a high tide visible in the rollup
# table for this many hours after its predicted peak. Rationale (user,
# 2026-05-31): "if I look at 9:44 PM, for example, and see it flooded,
# it would be better than finding out when I got home a couple hours
# later." Past tides remain visually distinct (`past-tide` class) and
# are excluded from the worst-case headline + predictions log append
# so we don't pollute downstream artifacts with already-happened tides.
PAST_TIDE_VISIBILITY_HOURS = 2


_TIDE_FALLBACK_USED = {"flag": False}


def _tide_cache_path():
    # lazy: _REPO_ROOT is defined further down the module
    return os.path.join(_REPO_ROOT, "data", "tide_predictions_cache.json")


def _tide_cache_load():
    try:
        with open(_tide_cache_path()) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"hilo": [], "series": []}


def _tide_cache_save(kind, rows):
    """Merge fresh astronomical predictions into the on-disk cache.

    RESILIENCE (2026-07-17): NOAA's predictions service went down
    system-wide (every station/datum: 'No Predictions data was
    found') the same evening a Flood Watch was issued — and the
    whole forecast crashed at the tide fetch, silencing the RAIN
    pathway too. Tide predictions are pure astronomy: valid for
    weeks, perfectly cacheable. Every successful fetch merges into
    this cache; on API failure the fetchers fall back to it and the
    site carries a staleness note instead of dying. kind: "hilo"
    rows = [t, v, type]; "series" rows = [t, v]."""
    try:
        cache = _tide_cache_load()
        merged = {r[0]: r for r in cache.get(kind, [])}
        for r in rows:
            merged[r[0]] = r
        try:
            cutoff = (_station_local_now()
                      - dt.timedelta(hours=72)).strftime("%Y-%m-%d %H:%M")
        except Exception:
            cutoff = ""
        cache[kind] = sorted(v for k, v in merged.items() if k >= cutoff)
        with open(_tide_cache_path() + ".tmp", "w") as f:
            json.dump(cache, f)
        os.replace(_tide_cache_path() + ".tmp", _tide_cache_path())
    except Exception:
        pass  # cache is best-effort, never fatal


def fetch_tides_24h():
    """Returns dict with 'high' and 'low' lists of (time_str, value_mllw_ft)
    for tides in the recent past + future. The "24h" in the name is
    retained for backwards-compat; the window is now
    [-PAST_TIDE_VISIBILITY_HOURS, +ROLLUP_WINDOW_HOURS] so the rollup
    can show very-recent past tides (still relevant for a few hours
    post-peak) alongside upcoming ones (HANDOFF 9b.2 part 2). Uses
    NOAA's hilo product for exact tide times.

    Timezone fix 2026-07-06: begin/end must be STATION-LOCAL for
    lst_ldt queries. The old UTC-now version shifted the window +4 h,
    which among other things silently negated the past-tide
    visibility feature (the window never actually reached the past)."""
    now = _station_local_now()
    start = now - dt.timedelta(hours=PAST_TIDE_VISIBILITY_HOURS)
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
            "begin_date": start.strftime("%Y%m%d %H:%M"),
            "end_date": end.strftime("%Y%m%d %H:%M"),
            "format": "json",
        },
    )
    preds = data.get("predictions", []) or []
    if preds:
        _tide_cache_save("hilo", [[p["t"], float(p["v"]), p.get("type")]
                                  for p in preds])
        return {
            "high": [(p["t"], float(p["v"])) for p in preds if p.get("type") == "H"],
            "low":  [(p["t"], float(p["v"])) for p in preds if p.get("type") == "L"],
        }
    # NOAA outage fallback (2026-07-17): serve cached astronomy.
    cache = _tide_cache_load()
    lo = start.strftime("%Y-%m-%d %H:%M")
    hi = end.strftime("%Y-%m-%d %H:%M")
    rows = [r for r in cache.get("hilo", []) if lo <= r[0] <= hi]
    if not rows:
        raise RuntimeError(
            "No high tides from NOAA and tide cache is empty/out of range")
    _TIDE_FALLBACK_USED["flag"] = True
    print("WARNING: NOAA predictions down — serving CACHED tide "
          f"astronomy ({len(rows)} points)", flush=True)
    return {
        "high": [(r[0], r[1]) for r in rows if r[2] == "H"],
        "low":  [(r[0], r[1]) for r in rows if r[2] == "L"],
    }


def build_water_series(surge_ft, qpf_hourly=None, hours_back=6,
                       hours_forward=30, interval_min=30):
    """Model-predicted water level at 342 Bay over a continuous window
    — the data behind the widget tide-curve chart (user request
    2026-07-06: "show 12-24 hours of the expected height over time
    given our model. It would mostly look like sinusoidal tide charts").

    Pulls NOAA astronomical predictions at `interval_min` resolution
    and applies the v0.8 transform at each step:

        water_navd88 = astro_pred + surge + LOCAL_ENHANCEMENT_FT
                       + MLLW_TO_NAVD88_OFFSET

    Notes / honest limitations:
    - `surge_ft` (persisted surge or NWS value) is applied as a
      CONSTANT across the window — same assumption the per-tide
      forecast makes. Fine near-term, increasingly wrong further out.
    - RAIN IS IN THE SERIES (2026-07-06 — the rain-DNA directive:
      rain modeling is Barnacle's value-add over tide apps and is
      never deferred). Each timestep gets the v0.9-alpha pluvial
      water estimate driven by that hour's QPF rate; the series shows
      max(tide water, pluvial water). Crude and directionally right:
      QPF smears convective bursts, so series rain bumps understate
      cells (the pluvial banner's analog-scaled scenarios carry the
      burst case); sustained/stratiform rain renders honestly.
      Every rain event recalibrates this.

    Returns list of {"time": local str, "water_navd88": float (total),
    "tide_navd88": float (tide+surge only)} or [] on fetch failure.
    `rain_navd88_lift` is included when nonzero.

    Timezone fix 2026-07-06: begin/end must be STATION-LOCAL (the
    widget chart's hour labels came out +4 h before this).
    """
    now = _station_local_now()
    start = now - dt.timedelta(hours=hours_back)
    end = now + dt.timedelta(hours=hours_forward)
    try:
        data = _get(
            "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter",
            {
                "station": NOAA_STATION,
                "product": "predictions",
                "datum": "MLLW",
                "time_zone": "lst_ldt",
                "units": "english",
                "interval": str(interval_min),
                "begin_date": start.strftime("%Y%m%d %H:%M"),
                "end_date": end.strftime("%Y%m%d %H:%M"),
                "format": "json",
            },
        )
    except Exception:
        data = {}
    # THREE-LAYER astronomy sourcing (2026-07-18 upgrade of the
    # 07-17 outage fallback): live NOAA points, then cached series
    # points, then COSINE SYNTHESIS between cached high/low extremes
    # for whatever is still missing. The old cache-only fallback let
    # the FUTURE horizon shrink toward the cache edge as the outage
    # aged (user: "the value of the app still lies in prediction" —
    # the chart showed 12 h of past and only ~6 h of future).
    # Astronomy is deterministic; the hilo cache reaches days out,
    # so the +24 h horizon survives any outage the cache survives.
    astro_map = {}
    for pp in data.get("predictions", []) or []:
        try:
            astro_map[pp["t"]] = float(pp["v"])
        except (KeyError, TypeError, ValueError):
            continue
    if astro_map:
        _tide_cache_save("series", [[t, v] for t, v in
                                    sorted(astro_map.items())])
    else:
        _TIDE_FALLBACK_USED["flag"] = True
        cache = _tide_cache_load()
        lo = start.strftime("%Y-%m-%d %H:%M")
        hi = end.strftime("%Y-%m-%d %H:%M")
        for r in cache.get("series", []):
            if lo <= r[0] <= hi:
                astro_map[r[0]] = float(r[1])
    # synthesize whatever 30-min slots remain missing
    expected = []
    _tt = start.replace(minute=(0 if start.minute < 30 else 30),
                        second=0, microsecond=0)
    while _tt <= end:
        expected.append(_tt)
        _tt += dt.timedelta(minutes=interval_min)
    missing = [t for t in expected
               if t.strftime("%Y-%m-%d %H:%M") not in astro_map]
    if missing:
        ext = []
        for r in _tide_cache_load().get("hilo", []):
            try:
                ext.append((dt.datetime.strptime(r[0], "%Y-%m-%d %H:%M"),
                            float(r[1])))
            except (ValueError, TypeError):
                continue
        ext.sort()
        synth = 0
        for t in missing:
            for i in range(1, len(ext)):
                t1, v1 = ext[i - 1]
                t2, v2 = ext[i]
                if t1 <= t <= t2 and (t2 - t1) <= dt.timedelta(hours=9):
                    frac = ((t - t1).total_seconds()
                            / (t2 - t1).total_seconds())
                    astro_map[t.strftime("%Y-%m-%d %H:%M")] = round(
                        (v1 + v2) / 2
                        + (v1 - v2) / 2 * math.cos(math.pi * frac), 3)
                    synth += 1
                    break
        if synth:
            _TIDE_FALLBACK_USED["flag"] = True
            print(f"WARNING: synthesized {synth} tide points from "
                  "cached extremes (cosine; NOAA outage)", flush=True)
    if not astro_map:
        return []
    data = {"predictions": [{"t": t, "v": v}
                            for t, v in sorted(astro_map.items())]}
    # Index QPF hourly rates by STATION-LOCAL hour for the rain layer.
    # qpf_hourly carries tz-aware UTC datetimes.
    qpf_by_local_hour = {}
    for tt, rate in (qpf_hourly or []):
        try:
            local = tt.astimezone(STATION_TZ).replace(tzinfo=None)
        except Exception:
            continue
        qpf_by_local_hour[local.replace(minute=0, second=0, microsecond=0)] = rate
    # OBSERVED-OVERLAY tier 1 (2026-07-17, user session queue): the
    # despiked gauge is a TRUE observation of the bay — and via
    # proven grate coupling + level-driven tidal flooding, of tide-
    # pathway street water. Attach it to past series points; the
    # chart draws it as a gray line that stops at now. (Tier 2 —
    # as-predicted-then pluvial reconstruction — deliberately
    # deferred; user endorsed keeping the current model line across
    # the past. Tier 3 = tape diamonds, added in the renderer.)
    observed_by_t = {}
    try:
        for t, v in fetch_observed_recent(hours=hours_back + 1):
            observed_by_t[t[:16]] = round(v + MLLW_TO_NAVD88_OFFSET, 3)
    except Exception:
        pass
    out = []
    for p in data.get("predictions", []) or []:
        try:
            astro = float(p["v"])
            t_local = dt.datetime.strptime(p["t"], "%Y-%m-%d %H:%M")
        except (TypeError, ValueError):
            continue
        tide_water = astro + (surge_ft or 0.0) + LOCAL_ENHANCEMENT_FT + MLLW_TO_NAVD88_OFFSET
        # v0.10: feed the tank RAW hourly QPF rates — the tank model
        # supplies its own lag + integration (the old ad-hoc two-hour
        # smoothing is retired with the per-point static estimate).
        h0 = t_local.replace(minute=0, second=0, microsecond=0)
        rate_raw = qpf_by_local_hour.get(h0, 0.0)
        row = {"time": p["t"], "tide_navd88": round(tide_water, 3),
               "_t": t_local, "_tide": tide_water, "_rate": rate_raw}
        if p["t"][:16] in observed_by_t:
            row["observed_navd88"] = observed_by_t[p["t"][:16]]
        out.append(row)

    # v0.10 DYNAMIC TANK (2026-07-09): the pluvial line is now a true
    # HYDROGRAPH — rise, peak, and recession with fitted timing —
    # integrated across the whole window, replacing the per-point
    # steady-state estimate. Two-line design unchanged (tide water
    # and rain street-water are different surfaces; never spliced).
    times = [q["_t"] for q in out]
    tides_w = [q["_tide"] for q in out]
    rates = [q["_rate"] for q in out]
    pluv_series = simulate_pluvial_series(times, tides_w, rates)
    for q, pluv in zip(out, pluv_series):
        water = q["_tide"]
        if pluv is not None:
            q["pluvial_navd88"] = round(pluv, 3)
            # tanh co-report retained for bracket continuity (static
            # steady-state at the raw rate — labeled alternative)
            _, pluv_tanh = estimate_pluvial_water_models(
                max(q["_rate"], 0.0), q["_tide"])
            q["pluvial_navd88_tanh"] = round(pluv_tanh, 3)
            water = max(water, pluv)
        q["water_navd88"] = round(water, 3)
        del q["_t"], q["_tide"], q["_rate"]
    return out


def fetch_high_tides_24h():
    """Backwards-compatible wrapper returning only high tides as a list."""
    return fetch_tides_24h()["high"]


def fetch_observed_recent(hours=6):
    """Past N hours of observed water level at Sandy Hook. Returns list of
    (time, value_mllw_ft). Default 6h preserves backwards-compat with the
    surge-swing calculation; pass hours=24 for the live-gauge widget
    (HANDOFF 16f / Y in the 2026-05-19 solo-work backlog)."""
    # TZ fix 2026-07-20: begin/end MUST be station-local for lst_ldt
    # queries (the documented 2026-07-06 bug class, still lurking
    # here) — the UTC window skewed +4 h into the empty future, so
    # "past 7 h" returned only ~3 h and the chart's observed overlay
    # cropped to the tail (user report).
    end = _station_local_now()
    start = end - dt.timedelta(hours=hours)
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
    # Despike (2026-07-09): this series feeds surge persistence — the
    # 11.87 gauge malfunction pushed a +4 ft "surge" into live
    # forecasts (widget read SEVERE +40″ during the event).
    return _despike_gauge(out)


def fetch_current_surge():
    """Compute current surge (observed - predicted) in ft. None on failure.

    BUG FIX 2026-05-19: previously this asked NOAA for hourly
    predictions in a ZERO-DURATION range [last_obs_time, last_obs_time].
    NOAA's hourly predictions land on the hour mark (21:00, 22:00, …),
    and observed is on a 6-min boundary (21:06, 21:12, …), so the
    range contained zero hourly hits → empty response → None
    returned → caller fell back to `or 0.0`. Result: every run logged
    surge as +0.000 regardless of actual conditions. User spotted this
    on the prediction-convergence chart for tonight's tide showing
    39 identical predictions.

    Fix: pull a ±1 h window around the last observed time so we always
    have at least one bracketing hourly prediction, then linearly
    interpolate to the observed minute mark.
    """
    obs = fetch_observed_recent()
    if not obs:
        return None
    last_obs_time, last_obs_val = obs[-1]
    try:
        obs_dt = dt.datetime.strptime(last_obs_time, "%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return None
    start = (obs_dt - dt.timedelta(hours=1)).strftime("%Y%m%d %H:%M")
    end   = (obs_dt + dt.timedelta(hours=1)).strftime("%Y%m%d %H:%M")
    try:
        data = _get(
            "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter",
            {
                "station":    NOAA_STATION,
                "product":    "predictions",
                "datum":      "MLLW",
                "time_zone":  "lst_ldt",
                "units":      "english",
                "interval":   "h",
                "begin_date": start,
                "end_date":   end,
                "format":     "json",
            },
        )
    except Exception:
        return None
    preds = data.get("predictions", []) or []
    if not preds:
        return None
    # Linear-interpolate between the bracketing hourly predictions
    before_t = before_v = after_t = after_v = None
    for p in preds:
        try:
            p_dt = dt.datetime.strptime(p["t"], "%Y-%m-%d %H:%M")
            p_v  = float(p["v"])
        except (ValueError, TypeError, KeyError):
            continue
        if p_dt <= obs_dt and (before_t is None or p_dt > before_t):
            before_t, before_v = p_dt, p_v
        if p_dt >= obs_dt and (after_t is None or p_dt < after_t):
            after_t, after_v = p_dt, p_v
    if before_t is not None and after_t is not None and after_t != before_t:
        span = (after_t - before_t).total_seconds()
        frac = (obs_dt - before_t).total_seconds() / span
        pred_at_obs = before_v + frac * (after_v - before_v)
    elif before_t is not None:
        pred_at_obs = before_v
    elif after_t is not None:
        pred_at_obs = after_v
    else:
        return None
    return last_obs_val - pred_at_obs


def fetch_surge_swing_6h():
    """Return (max - min) of hourly surge over the past 6h in feet. None on
    failure. Used by the confidence indicator — large swing means surge
    persistence is unreliable as a forecast for the next high tide."""
    # TZ fix 2026-07-20 (family sweep): lst_ldt needs station-local —
    # the UTC window skewed +4h into the empty future, so the 6-h
    # surge swing was computed over ~2h of data, systematically
    # UNDERSTATING swing and inflating confidence.
    end = _station_local_now()
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
    # Added 2026-05-19 for self-calibrated confidence uncertainty (HANDOFF
    # 9b.6 refinement / "N" in the solo-work backlog). Old rows from
    # before this column was added have empty values — calibration code
    # filters those out and falls back to the heuristic when N < 3.
    "confidence_level",
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
    "water_navd88_predicted",    # = sh_peak_mllw + LOCAL_ENHANCEMENT_FT + (-2.82)
    "regime_predicted",
    "cold_lockout",              # "true" | "false"
    "confidence_level",          # "high" | "medium" | "low" | ""
    "model_version",             # current model spec version (currently v0.9)
]


def _despike_gauge(pairs, tol_ft=1.0, half_window=10):
    """Drop physically-impossible points from a 6-min gauge series.

    2026-07-09: the Sandy Hook sensor spiked to 11.87 ft MLLW (would
    be #2 all-time) during a violent convective cell while The
    Battery, 15 mi away in the same harbor, sat flat — instrument
    malfunction, not water. The 40-min-wide spike DEFEATED the older
    neighbor-agreement check (adjacent garbage points "agreed") and
    fed surge-persistence: the widget showed SEVERE +40″ from
    garbage while the real (rain) flood measured +18.7″. A point is
    rejected when it differs from the MEDIAN of its ±half_window
    neighbors by more than tol_ft — tide + real surge cannot move
    1 ft in minutes (even Sandy rose ~1 ft per 30 min). Trade-off
    accepted: a true meteotsunami would also be filtered from PEAK
    numbers (it would still be visible in raw data / at the house).
    pairs = [(t, v), ...] chronological; returns filtered list."""
    # 2026-07-18 live-rain fix: the old guard PASSED THROUGH whole
    # windows shorter than 2·half_window+1 — and a 2-h bay read is at
    # most 20 points, so with half_window=10 the filter silently never
    # ran (a 9.75 spike sailed into the nowcast base during rain).
    # Shrink the window to fit the data instead of giving up; only
    # truly tiny series (<5 pts) pass through.
    if len(pairs) < 5:
        return pairs
    half_window = max(2, min(half_window, (len(pairs) - 1) // 2))
    vals = [v for _, v in pairs]
    out = []
    n = len(pairs)
    for i, (t, v) in enumerate(pairs):
        lo = max(0, i - half_window)
        hi = min(n, i + half_window + 1)
        neigh = sorted(vals[lo:i] + vals[i + 1:hi])
        med = neigh[len(neigh) // 2]
        if abs(v - med) <= tol_ft:
            out.append((t, v))
    return out


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
    vals = []
    for d in (data.get("data") or []):
        try:
            vals.append((d.get("t"), float(d["v"])))
        except (KeyError, ValueError, TypeError):
            continue
    # SPIKE REJECTION v2 (2026-07-09): median-window despike replaces
    # the 2026-07-08 neighbor-agreement check, which a 40-min-wide
    # malfunction defeated (garbage neighbors agree with each other).
    peak = None
    peak_t = None
    for t, v in _despike_gauge(vals):
        if peak is None or v > peak:
            peak = v
            peak_t = t
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
            "confidence_level":             fc.get("confidence_level", ""),
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


CURRENT_MODEL_VERSION = "v0.10"

# v0.8 wind-direction sectors for the storm-bump adjustment. Sandy Hook
# Bay's SE corner (where Highlands sits) is piled when winds blow INTO
# that corner — from the N/NE quadrant. Winds FROM the S/SW push water
# OUT of the corner, reducing local enhancement.
# Calibrated against 2026-06-14 (peak wind SSW → offshore → enh -0.13)
# and 2026-06-15 (peak wind N/NNE → onshore → enh 0). The "main" model
# (enhancement = 0) matches onshore peak conditions. Forecast offshore
# peak conditions get reported as an "expected actual" line that's
# 0.13 ft lower than the main prediction.
WIND_OFFSHORE_DIRECTIONS = {"S", "SSW", "SW", "WSW", "SSE"}
WIND_ONSHORE_DIRECTIONS  = {"N", "NNE", "NE", "ENE", "E", "NNW"}
WIND_OFFSHORE_ADJUSTMENT_FT = -0.13


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
        # Skip past tides (rollup now includes them for visibility, but
        # appending them here would create duplicate-with-different-
        # hours_until_peak rows in the log, polluting the convergence
        # chart for that tide).
        hfn = t.get("hours_from_now")
        if hfn is not None and hfn < 0:
            continue
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
# Recomputed for v0.9 thresholds (landmark + 2.82); the old values
# (7.00/6.58/6.20) were v0.6-era and never updated through v0.7-v0.9.
LOOKAHEAD_THRESHOLDS = [
    (7.48, "would cross lawn step (no surge needed)",       "watch-severe"),
    (6.98, "would cross curb (no surge needed)",             "watch-moderate"),
    (6.60, "would reach gutter (no surge needed)",           "watch-light"),
    (6.34, "would reach the lowest grate (SW) — street water", "watch-minor"),
]


def _moon_phase_age_days(date):
    """Days since 2000-01-06 reference new moon, modulo synodic month.
    Used to annotate spring tides in the look-ahead table (HANDOFF 25a / Z).

    Accurate to about ±1 day across centuries — good enough for the
    "is this date within ±2 days of new/full moon" purpose. For finer
    precision, see Jean Meeus's astronomical formulas; for the current
    use case the simple modular arithmetic is sufficient and dep-free.
    """
    synodic = 29.530588
    ref = dt.date(2000, 1, 6)
    return ((date - ref).days % synodic + synodic) % synodic


def _spring_tide_marker(date, tolerance_days=2.0):
    """Returns 'new moon' if `date` is within ±tolerance of new moon,
    'full moon' if within ±tolerance of full moon, else ''. Spring tides
    cluster around these days because the Sun + Moon + Earth approach
    alignment — strongest tidal pull, highest highs."""
    synodic = 29.530588
    full = 14.765
    age = _moon_phase_age_days(date)
    d_new  = min(age, synodic - age)
    d_full = abs(age - full)
    if d_new <= tolerance_days and d_new <= d_full:
        return "new moon"
    if d_full <= tolerance_days:
        return "full moon"
    return ""


def fetch_high_tides_lookahead(days=LOOKAHEAD_DAYS):
    """Pull NOAA `predictions` hilo for the next `days` days. Returns list of
    (time_str, mllw_ft) for high tides only. Astronomical only — no surge.
    Larger window than fetch_tides_24h; used for HANDOFF 9b.7."""
    now = _station_local_now()
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
            # TZ fix 2026-07-20: proper station-tz conversion (the old
            # hardcoded +4 was wrong every winter, EST = UTC-5)
            # conversion is good enough for the "skip the next 24h"
            # boundary, which doesn't need second-precision.
            tide_utc = tide_dt.replace(tzinfo=STATION_TZ).astimezone(
                dt.timezone.utc)
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
                spring = _spring_tide_marker(tide_dt.date())
                rows.append({
                    "time":           time_str,
                    "time_dt":        tide_dt,
                    "mllw":           mllw,
                    "threshold_mllw": threshold,
                    "label":          label,
                    "severity_class": css_class,
                    "spring_tide":    spring,  # 'new moon', 'full moon', or ''
                })
                break
    rows.sort(key=lambda r: r["time_dt"])
    return rows


def fetch_recent_history(days=7):
    """Past N days of observed daily peak water level, with the highest
    landmark reached at that peak. Returns list of dicts (one per calendar
    day), sorted chronologically. Empty list on failure."""
    # TZ fix 2026-07-20 (family sweep): station-local for lst_ldt —
    # the +4h skew shifted the 7-day window and could mis-bucket
    # peaks near midnight into the wrong day.
    end = _station_local_now()
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
    startTime, temperature, probabilityOfPrecipitation, etc.

    NOTE (2026-07-06): these periods do NOT contain
    quantitativePrecipitation — NWS only publishes QPF in the raw
    gridpoint endpoint. Use fetch_nws_qpf() for rain. This function
    remains the source for wind (compute_wind_adjustment) and
    probabilityOfPrecipitation / shortForecast (pluvial advisory)."""
    pts = _get(f"https://api.weather.gov/points/{HIGHLANDS_LAT},{HIGHLANDS_LON}")
    forecast_url = pts["properties"]["forecastHourly"]
    fc = _get(forecast_url)
    return fc["properties"]["periods"]


def _parse_iso_duration_hours(dur):
    """Parse the ISO-8601 durations NWS uses in gridpoint validTime
    strings ("PT6H", "PT2H", "P1D", "P1DT6H"). Returns float hours.
    Minutes appear rarely ("PT30M"); handled. Anything unparsable
    returns None."""
    m = re.match(r"^P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?)?$", dur)
    if not m or dur == "P":
        return None
    days, hours, minutes = (int(g) if g else 0 for g in m.groups())
    total = days * 24 + hours + minutes / 60.0
    return total if total > 0 else None


def fetch_nws_flood_alerts():
    """Active NWS alerts for the 342 Bay point, filtered to
    flood-relevant events (2026-07-09 — the day a live Flood Watch
    was up while Barnacle showed nothing). Alerts carry the human
    forecaster's convective judgment that never survives into the
    smeared QPF numbers — the same information channel as the Flash
    Flood Warning that existed DURING the 7/6 flood. Returns a list
    of {event, headline, severity, ends}; [] on any failure (alerts
    must never break the run)."""
    try:
        data = _get(
            "https://api.weather.gov/alerts/active",
            {"point": f"{HIGHLANDS_LAT},{HIGHLANDS_LON}"},
        )
    except Exception:
        return []
    out = []
    for feat in (data.get("features") or []):
        props = feat.get("properties") or {}
        event = props.get("event") or ""
        # Flood Watch / Flash Flood Watch / Flood Warning / Flash Flood
        # Warning / Flood Advisory. Coastal Flood products are the
        # TIDE pathway's business (nws_surge_parser) — exclude here.
        if "flood" not in event.lower():
            continue
        if "coastal" in event.lower():
            continue
        out.append({
            "event": event,
            "headline": props.get("headline") or "",
            "severity": props.get("severity") or "",
            "onset": props.get("onset") or props.get("effective") or "",
            "ends": props.get("ends") or props.get("expires") or "",
        })
    return out


def fetch_nws_qpf():
    """Hourly rain-rate buckets (in/hr, UTC) from the NWS gridpoint
    QPF data — THE fix for the bug where rain read 0.0 forever
    (discovered 2026-07-06, the pluvial flash flood the model called
    "dry"): forecastHourly periods stopped carrying
    quantitativePrecipitation, so every read returned None → 0.0.
    The raw gridpoint endpoint still has QPF, in mm over ISO-8601
    intervals (typically PT6H).

    Expands each interval into per-hour buckets at the interval's
    AVERAGE rate. Honesty note: a convective cell dumping 1+ in/hr
    for 40 min inside a 6-h bucket averages to ~0.1 in/hr — QPF
    resolution structurally understates convective peaks. That's why
    the pluvial advisory (2026-07-06) also triggers on
    probabilityOfPrecipitation + thunderstorm wording, not just QPF.

    Returns list of (bucket_start_utc_datetime, rate_in_per_hr),
    hour-aligned, sorted. Empty list on failure.
    """
    try:
        pts = _get(f"https://api.weather.gov/points/{HIGHLANDS_LAT},{HIGHLANDS_LON}")
        grid_url = pts["properties"]["forecastGridData"]
        grid = _get(grid_url)
        values = grid["properties"]["quantitativePrecipitation"]["values"]
    except Exception:
        return []
    out = []
    for v in values:
        try:
            start_str, dur = v["validTime"].split("/")
            start = parse_iso(start_str)
            hours = _parse_iso_duration_hours(dur)
            mm = float(v["value"]) if v["value"] is not None else 0.0
        except Exception:
            continue
        if not hours:
            continue
        rate_in_hr = (mm / 25.4) / hours
        n_buckets = max(1, int(round(hours)))
        for i in range(n_buckets):
            out.append((start + dt.timedelta(hours=i), rate_in_hr))
    out.sort(key=lambda x: x[0])
    return out


# ============================================================
# Model
# ============================================================
def compute_wind_adjustment(nws_hourly, peak_dt):
    """v0.8 wind-direction-dependent enhancement adjustment.

    Looks up forecast wind direction at the NWS hourly period closest
    to `peak_dt`. Returns a dict suitable for display alongside the
    main prediction as a SEPARATE "expected actual" estimate.

    Calibrated against:
      - 2026-06-14 peak (wind SSW at 12-16 kt) → offshore → enh -0.13
      - 2026-06-15 peak (wind N/NNE at 8-10 kt) → onshore → enh ~0

    Main model uses enhancement = 0 (matches onshore peak conditions
    or "unknown wind" — the safer / over-predict default per user
    preference). This function returns the OFFSHORE adjustment when
    forecast winds at peak would push water away from the bay corner.

    Returns dict with:
      sector: "offshore" | "onshore" | "neither" | "unknown"
      adjustment_ft: 0 (default) or WIND_OFFSHORE_ADJUSTMENT_FT (offshore)
      wind_dir_at_peak: e.g. "SSW", "N"
      wind_speed_at_peak: NWS forecast string e.g. "10 mph"
      note: human-readable explanation
    """
    if peak_dt is None or not nws_hourly:
        return None
    closest = None
    closest_delta = None
    for p in nws_hourly[:96]:
        try:
            tt = parse_iso(p["startTime"])
        except Exception:
            continue
        delta = abs((tt - peak_dt).total_seconds())
        if closest is None or delta < closest_delta:
            closest = p
            closest_delta = delta
    if closest is None:
        return None
    wind_dir = closest.get("windDirection") or ""
    wind_speed = closest.get("windSpeed") or ""
    if wind_dir in WIND_OFFSHORE_DIRECTIONS:
        sector = "offshore"
        adjustment = WIND_OFFSHORE_ADJUSTMENT_FT
        note = (
            f"Forecast wind at peak ({wind_dir} at {wind_speed}) is in "
            f"the offshore sector — water at 342 Bay is typically "
            f"~{abs(WIND_OFFSHORE_ADJUSTMENT_FT*12):.1f}\" lower than the "
            f"main prediction because bay-corner water is being pushed "
            f"away from Highlands. Expect actual closer to this "
            f"wind-adjusted estimate."
        )
    elif wind_dir in WIND_ONSHORE_DIRECTIONS:
        sector = "onshore"
        adjustment = 0.0
        note = (
            f"Forecast wind at peak ({wind_dir} at {wind_speed}) is in "
            f"the onshore sector — water gets piled into the bay corner "
            f"where Highlands sits. Main prediction applies."
        )
    else:
        sector = "neither" if wind_dir else "unknown"
        adjustment = 0.0
        note = (
            f"Forecast wind at peak ({wind_dir or 'unknown'} at "
            f"{wind_speed or '?'}) is cross-shore or unspecified — "
            f"defaulting to main prediction (no wind adjustment)."
        )
    return {
        "sector": sector,
        "adjustment_ft": adjustment,
        "wind_dir_at_peak": wind_dir,
        "wind_speed_at_peak": wind_speed,
        "note": note,
    }


def predict_landmark_depths(sandy_hook_peak_mllw, peak_rain_rate_in_hr=0.0,
                            cold_lockout=False, enhancement_override=None):
    """Apply v0.8 model. Returns dict of depths (inches) at each landmark.

    v0.8 (2026-06-16) changes from v0.7:
    - Enhancement constant: -0.13 → 0.00. The 2026-06-15 storm-condition
      event (SH 7.289, peak winds N/NNE) cleanly fit a 0 enhancement
      across 4-grate cross-fit, while the 3 prior tape-measured events
      (5/18, 5/31, 6/14, all with offshore peak winds) fit -0.13. v0.8
      takes the conservative (over-predict) value of 0 as the main
      model. The wind-adjustment function (compute_wind_adjustment)
      reports a -0.13 ft "expected actual" line when forecast wind at
      peak is in the offshore sector — calibrated to S/SW peak
      conditions like 6/14.
    - 16 landmarks (was 15): added `sidewalk_under_walkway_lawn_step`
      at 4.33 NAVD88 (cross-fit from the 6/15 measurements; the
      sidewalk surface where it meets the lawn-step face on the
      user's walkway).
    - SH landmark thresholds shift by -0.13 ft uniformly (everything
      activates 1.5" earlier than v0.7).

    Inherited from v0.7:
    - Single-water-level math: rain adds to a shared water level
      (dZ_rain = 8·tanh(rate)/12 ft); per-landmark shedding constants
      removed.
    - Cold-lockout demoted from override to advisory (parameter
      retained for caller-API stability but no longer applied).

    `enhancement_override` (v0.8): if not None, overrides
    `LOCAL_ENHANCEMENT_FT` for this call. Used by the report renderer
    to compute the wind-adjusted secondary prediction alongside the
    main one.

    Rain-term calibration: fits Oct 30 2025 anchor (SH 7.63 + 1.45
    in/hr → water 5.27 NAVD88 from photo cross-fit) within 0.4" at
    curb. v0.7→v0.8 enhancement change of +0.13 ft also bumps Oct 30
    prediction by 0.13 ft (now 5.41 NAVD88 vs photo lower bound 5.25
    — over by 1.9", which is the price of moving to the conservative
    constant). v0.8 9d.3 (open) is whether antecedent moisture or
    accumulated rain at modest rates explains Dec 19's remaining
    mismatch.
    """
    enh = enhancement_override if enhancement_override is not None else LOCAL_ENHANCEMENT_FT
    # Tide-driven water level at 342 Bay (NAVD88, ft).
    water_navd88 = sandy_hook_peak_mllw + enh + MLLW_TO_NAVD88_OFFSET

    # Rain adds to the shared water level (water-is-level model).
    # 8·tanh(rate) is the v0.6 rain magnitude (inches) preserved
    # verbatim; division by 12 converts to feet. v0.7 9d.2 will refit
    # this term once we have a second rain-flood anchor event.
    if peak_rain_rate_in_hr > 0.1:
        rain_add_ft = RAIN_SATURATION_IN * math.tanh(peak_rain_rate_in_hr) / 12.0
        water_navd88 += rain_add_ft

    d = {key: max(0.0, water_navd88 - elev) * 12
         for key, _label, elev, _sh in LANDMARKS}

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
    elif (d["gutter_walkway"] > 0 or d["corner_SE"] > 0 or
          d["grate_SE"] > 0 or d["grate_SW"] > 0):
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
    now = _station_local_now()  # lst_ldt query; month boundary in ET
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
    # tide peak that crosses the curb threshold but pulls the hourly mean back below).
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
        if v >= SH_CURB_THRESHOLD:
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

    # SLR line shows only in the "newly-wet" band: today's peak crosses the
    # curb threshold but would have been below curb in 1990.
    # Also suppress in severe regime (>= 7.5 ft) — SLR isn't the story there.
    peak = ctx["slr_today_peak_ft"]
    slr = ctx["slr_ft_since_1990"]
    if peak is not None and slr is not None and slr > 0:
        ceiling_today = SH_CURB_THRESHOLD + slr
        if SH_CURB_THRESHOLD <= peak < min(ceiling_today, 7.5):
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
    # QPF from the gridpoint endpoint — the ONLY place NWS publishes
    # it (2026-07-06 fix; forecastHourly periods carry no QPF and the
    # old read silently returned 0.0 forever).
    qpf_hourly = fetch_nws_qpf()   # list of (utc_dt, in/hr)

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
            # Surge persistence fallback. v0.7 (2026-06-14) dropped the
            # `max(0.0, surge)` clip — negative surge is now passed
            # through (HANDOFF 9c.6). Anti-surge conditions exist; the
            # forecast should be allowed to predict below the
            # astronomical tide.
            surge = persisted_surge if persisted_surge is not None else 0.0
            forecast_peak = tide_pred + surge
            source = "surge-persistence"

        # Rain in [-90 min, +15 min] of THIS high tide (v0.7 before-biased
        # window — HANDOFF 9c.7). Rain after the peak cannot raise the
        # peak water level; the small +15 min forward tolerance covers
        # tide-time uncertainty (observed flooding has lagged the
        # predicted peak by up to ~30 min). Wider ±3h hourly profile
        # for the email's rain-timing block is unchanged.
        # 2026-07-06: source switched from forecastHourly periods
        # (which no longer carry QPF — the read was silently 0.0
        # forever) to the gridpoint QPF buckets in qpf_hourly.
        peak_rain_rate = 0.0
        rain_window = []  # list of (hours_offset_from_high_tide, rain_rate_in_hr)
        peak_rain_offset_h = None
        if peak_dt is not None:
            window_start = peak_dt - dt.timedelta(minutes=90)
            window_end   = peak_dt + dt.timedelta(minutes=15)
            wider_start  = peak_dt - dt.timedelta(hours=3)
            wider_end    = peak_dt + dt.timedelta(hours=3)
            for tt, rate in qpf_hourly:
                if window_start <= tt <= window_end:
                    if rate > peak_rain_rate:
                        peak_rain_rate = rate
                        peak_rain_offset_h = (tt - peak_dt).total_seconds() / 3600.0
                if wider_start <= tt <= wider_end:
                    off_h = (tt - peak_dt).total_seconds() / 3600.0
                    rain_window.append((off_h, rate))

        # Depth at landmarks for this tide (main prediction)
        depths = predict_landmark_depths(forecast_peak, peak_rain_rate, cold)

        # v0.8 wind-direction adjustment: compute a secondary "expected
        # actual" prediction when forecast wind at peak is offshore.
        # Reported alongside the main prediction; does NOT replace it.
        wind_adj = compute_wind_adjustment(nws_hourly, peak_dt)
        depths_wind_adjusted = None
        if wind_adj is not None and wind_adj["adjustment_ft"] != 0.0:
            depths_wind_adjusted = predict_landmark_depths(
                forecast_peak, peak_rain_rate, cold,
                enhancement_override=LOCAL_ENHANCEMENT_FT + wind_adj["adjustment_ft"],
            )

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
            "depths_in_wind_adjusted": depths_wind_adjusted,
            "wind_adjustment": wind_adj,
            "hours_from_now": hours_from_now,
        })

    # Identify the worst-case high tide for headline / subject line.
    # Exclude past tides (hours_from_now < 0): the headline is about
    # what to watch out for, not what already happened. If the rollup
    # contains only past tides (edge case — e.g. bot just resumed
    # after a multi-hour gap), fall back to the full list so something
    # still gets headlined.
    upcoming_tides = [t for t in all_tides
                      if (t.get("hours_from_now") is None
                          or t["hours_from_now"] >= 0)]
    worst = max(upcoming_tides or all_tides,
                key=lambda t: t["forecast_peak_mllw"])

    forecast_for_context = {"peak_forecast_observed_mllw": worst["forecast_peak_mllw"]}
    seasonal_context = build_seasonal_context(forecast_for_context)

    # Cumulative rain over the next 24h (from NWS hourly forecast). Used in
    # the rain-timing block.
    cumulative_rain_24h = 0.0
    peak_rain_rate_24h = 0.0      # max hourly QPF rate anywhere in next 24h
    now_utc = dt.datetime.now(dt.timezone.utc)
    cutoff = now_utc + dt.timedelta(hours=24)
    window_rates = []             # hourly (utc, rate) inside the 24h window
    for tt, rate in qpf_hourly:
        if tt < now_utc or tt > cutoff:
            continue
        window_rates.append((tt, rate))
        cumulative_rain_24h += rate  # rate (in/hr) × 1 h bucket = inches
        if rate > peak_rain_rate_24h:
            peak_rain_rate_24h = rate
    # Max rolling 6-h QPF accumulation in the window — the analog-model
    # predictor (matches QPF's native bucket size, so it's the most
    # trustworthy magnitude number QPF gives us).
    max_6h_accum = 0.0
    for i in range(len(window_rates)):
        t0 = window_rates[i][0]
        acc = sum(r for tt, r in window_rates
                  if t0 <= tt < t0 + dt.timedelta(hours=6))
        max_6h_accum = max(max_6h_accum, acc)

    # Pluvial flood risk (v0.9 first step — 2026-07-06 flash flood
    # proved rain alone floods the intersection; see
    # assets/observations/2026-07-06/README.md). This is a CATEGORICAL
    # advisory, not a depth prediction: QPF's ~6-h buckets smear
    # convective peaks (the 7/6 cell averaged ~0.09 in/hr in QPF while
    # actually producing a 7.3-in-at-curb flood), so the trigger also
    # uses probabilityOfPrecipitation + thunderstorm wording from the
    # hourly forecast.
    pluvial_max_pop = 0
    pluvial_convective = False
    for p in nws_hourly[:24]:
        pop = ((p.get("probabilityOfPrecipitation") or {}).get("value")) or 0
        pluvial_max_pop = max(pluvial_max_pop, pop)
        sf = (p.get("shortForecast") or "").lower()
        if pop >= 60 and ("thunder" in sf or "heavy rain" in sf):
            pluvial_convective = True
    # NWS flood alerts (2026-07-09): the forecaster's own call.
    # Warnings (flooding imminent/occurring) → elevated; Watches /
    # Advisories → at least possible. An active flood alert also
    # counts as the convective signal for the analog burst below —
    # the human forecaster IS the convection detector the smeared
    # QPF numbers lack (today's live example: Flood Watch active,
    # QPF smeared to 0.05 in/hr, PoP 52% — every numeric trigger
    # silent).
    nws_flood_alerts = fetch_nws_flood_alerts()
    alert_warning = any("warning" in a["event"].lower()
                        for a in nws_flood_alerts)
    pluvial_risk_level = None
    if peak_rain_rate_24h >= 0.30 or pluvial_convective or alert_warning:
        pluvial_risk_level = "elevated"
    elif (cumulative_rain_24h >= 1.0
          or (pluvial_max_pop >= 70 and cumulative_rain_24h >= 0.5)
          or nws_flood_alerts):
        pluvial_risk_level = "possible"
    # Analog burst estimate + the "rain burst potential" water level —
    # the level a 7/6-analog burst would reach at low tide. Charts draw
    # this as a dashed line: rain potential belongs ON the primary
    # surfaces (rain-DNA directive) but a convective burst has no
    # knowable clock time, so it renders as a level, not a bump.
    burst_est = peak_rain_rate_24h
    if pluvial_convective or nws_flood_alerts:
        analog = 1.7 * (max_6h_accum / 0.55) if max_6h_accum > 0 else 1.7
        burst_est = max(burst_est, min(analog, 3.0))
    potential_low_tide = potential_low_tide_tanh = None
    if burst_est > 0.1:
        potential_low_tide, potential_low_tide_tanh = (
            estimate_pluvial_water_models(burst_est, 2.5))
    pluvial_risk = {
        "level": pluvial_risk_level,     # None | "possible" | "elevated"
        "peak_rain_rate_24h_in_hr": round(peak_rain_rate_24h, 3),
        "cumulative_rain_24h_in": round(cumulative_rain_24h, 2),
        "max_6h_accum_in": round(max_6h_accum, 2),
        "max_pop_24h_pct": pluvial_max_pop,
        "convective_wording": pluvial_convective,
        "burst_est_in_hr": round(burst_est, 2),
        # primary (power-law) estimate; _tanh = saturating alternative
        # (v0.9-gamma dual reporting — additive fields)
        "potential_low_tide_navd88": (round(potential_low_tide, 2)
                                      if potential_low_tide else None),
        "potential_low_tide_navd88_tanh": (
            round(potential_low_tide_tanh, 2)
            if potential_low_tide_tanh else None),
        # additive (2026-07-09): the alerts that informed the level
        "nws_flood_alerts": nws_flood_alerts,
    }

    # Rain outlook, next 72 h by local day (user 2026-07-09: a rain
    # box parallel to the high-tides summary). Aggregates the hourly
    # QPF + PoP/wording per station-local calendar day.
    rain_outlook = []
    try:
        _now_local = _station_local_now()
        for day_i in range(3):
            day = (_now_local + dt.timedelta(days=day_i)).date()
            day_iso = day.isoformat()
            cum = 0.0
            peak = 0.0
            for t_utc, rate in (qpf_hourly or []):
                try:
                    t_loc = t_utc.astimezone(STATION_TZ)
                except (TypeError, ValueError):
                    continue
                if t_loc.date() == day:
                    cum += rate
                    peak = max(peak, rate)
            pop = 0
            thunder = False
            for pd in (nws_hourly or []):
                if (pd.get("startTime") or "")[:10] != day_iso:
                    continue
                pop = max(pop, ((pd.get("probabilityOfPrecipitation")
                                 or {}).get("value")) or 0)
                sf = (pd.get("shortForecast") or "").lower()
                if "thunder" in sf:
                    thunder = True
            label = ("today" if day_i == 0 else
                     "tomorrow" if day_i == 1 else day.strftime("%a %b %-d"))
            rain_outlook.append({
                "day": day_iso, "label": label,
                "cum_in": round(cum, 2), "peak_in_hr": round(peak, 2),
                "max_pop_pct": pop, "thunder": thunder,
            })
    except Exception:
        rain_outlook = []

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

    # Live gauge — past 24h of observed water level (HANDOFF 16f, "Y")
    try:
        live_gauge_24h = fetch_observed_recent(hours=24)
    except Exception:
        live_gauge_24h = []

    # Model-predicted water level series for the widget tide-curve
    # chart (2026-07-06). Uses the worst tide's surge as the constant
    # surge across the window — same persistence assumption as the
    # per-tide forecasts.
    water_series = build_water_series(worst["surge_ft"], qpf_hourly)

    # Mark burst-capable hours on the series points (user 2026-07-06:
    # the rain-burst zone should only span the hours when a burst is
    # actually plausible, not the whole window). An hour qualifies if
    # the NWS hourly forecast has PoP >= 60% with thunder/heavy-rain
    # wording, PoP >= 80% alone, or QPF rate >= 0.15 in/hr.
    burst_hours = set()
    for p in nws_hourly[:36]:
        try:
            tt = parse_iso(p["startTime"]).astimezone(STATION_TZ)
        except Exception:
            continue
        pop = ((p.get("probabilityOfPrecipitation") or {}).get("value")) or 0
        sf = (p.get("shortForecast") or "").lower()
        if ((pop >= 60 and ("thunder" in sf or "heavy rain" in sf))
                or pop >= 80):
            burst_hours.add(tt.strftime("%Y-%m-%d %H"))
    for tt, rate in qpf_hourly:
        if rate >= 0.15:
            try:
                burst_hours.add(tt.astimezone(STATION_TZ).strftime("%Y-%m-%d %H"))
            except Exception:
                pass
    for p in water_series:
        if p["time"][:13] in burst_hours:
            p["burst_risk"] = True

    # Flood windows + "today" summary derived from the series
    # (2026-07-06 — start/end/duration, not just peak instants; and
    # "today" reflects rain because rain is IN the series).
    flood_windows = compute_flood_windows(water_series)
    # DAY-SCOPE the pluvial risk (user 2026-07-20: 'POSSIBLE RAIN
    # FLOODING' sat in the TODAY box while the watch didn't begin
    # until tomorrow — scope-mixing). risk_today = any burst-capable
    # series hour dated TODAY, or an alert whose onset is today or
    # earlier. When False, the TODAY headline stays regime-based and
    # the risk is announced as TOMORROW's in the 72-h strip.
    try:
        _today_str = _station_local_now().strftime("%Y-%m-%d")
    except Exception:
        _today_str = dt.date.today().isoformat()
    _risk_today = any(p.get("burst_risk") and
                      (p.get("time") or "").startswith(_today_str)
                      for p in water_series)
    for _a in (pluvial_risk.get("nws_flood_alerts") or []):
        _on = (_a.get("onset") or "")[:10]
        if _on and _on <= _today_str:
            _risk_today = True
    pluvial_risk["risk_today"] = bool(_risk_today)
    today_peak_water = None
    today_peak_time = None
    # OUTLOOK stays forward-looking: with the series now extending
    # 12 h back (observed overlay), past water must not masquerade
    # as the TODAY headline — the SO-FAR lookback owns the past.
    try:
        _now_cut = (_station_local_now()
                    - dt.timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M")
    except Exception:
        _now_cut = ""
    for p in water_series:
        if (p.get("time") or "") < _now_cut:
            continue
        try:
            w = float(p["water_navd88"])
        except (KeyError, TypeError, ValueError):
            continue
        if today_peak_water is None or w > today_peak_water:
            today_peak_water = w
            today_peak_time = p.get("time")
    today_regime = (classify_regime_from_water(today_peak_water)
                    if today_peak_water is not None else None)
    # Highest landmark crossed in the series window
    today_highest_crossed = None
    if today_peak_water is not None:
        for key, label, elev, _sh in LANDMARKS:
            if key in FLOOD_WINDOW_KEYS and today_peak_water > elev:
                today_highest_crossed = {"key": key, "label": label,
                                         "elev": elev}
    # Standard mental unit: inches relative to the lowest grate (SW)
    today_rel_grate_sw_in = (round((today_peak_water - GRATE_SW) * 12, 1)
                             if today_peak_water is not None else None)

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
        "depths_in_wind_adjusted": worst.get("depths_in_wind_adjusted"),
        "wind_adjustment": worst.get("wind_adjustment"),
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
        # Pluvial flood risk advisory (v0.9 first step, 2026-07-06)
        "pluvial_risk": pluvial_risk,
        "rain_outlook_72h": rain_outlook,
        # Confidence indicator inputs (level computed below after assembly)
        "surge_swing_6h_ft": surge_swing,
        # Recent observed peaks for the recap block
        "recent_history_7d": recent_history,
        # Look-ahead "dates to watch" — astronomical only (HANDOFF 9b.7)
        "lookahead_watch": lookahead_watch,
        # Last 24h observed water level for the live gauge (HANDOFF 16f / Y)
        "live_gauge_24h": [
            {"time": t, "value_mllw": v} for t, v in live_gauge_24h
        ],
        # Model-predicted water level (NAVD88) at 30-min steps,
        # now-2h → now+24h. Tide + surge + QPF rain layer (rain-DNA
        # directive 2026-07-06: rain is in the series, not deferred).
        "water_series": water_series,
        # Flood windows (start/end/duration/peak per landmark) derived
        # from the series, + the "today" summary the widget leads with.
        "flood_windows": flood_windows,
        "today_peak_water_navd88": (round(today_peak_water, 3)
                                    if today_peak_water is not None else None),
        "today_peak_time": today_peak_time,
        "today_regime": today_regime,
        "today_lookback": _today_lookback(),   # what already happened today
        "tide_predictions_stale": _TIDE_FALLBACK_USED["flag"],
        "today_highest_crossed": today_highest_crossed,
        "today_rel_grate_sw_in": today_rel_grate_sw_in,
    }


_CONFIDENCE_HEURISTIC_FT = {
    "high":   0.10,
    "medium": 0.30,
    "low":    0.50,
}
# Below this row count, prefer the heuristic over the per-band sample
# mean — small samples are noisy and would mislead users with bogus
# precision. Tune up as the accuracy log accumulates.
CONFIDENCE_CALIBRATION_MIN_N = 3


def _calibrate_confidence_from_accuracy_log():
    """Compute per-confidence-band mean |error| in SH MLLW ft from
    data/forecast_accuracy.csv (HANDOFF 9b.6 refinement). Returns
    dict like {"high": {"mean_abs_err_ft": 0.08, "n": 4}, ...}.

    Skips rows whose confidence_level column is empty (those were
    written before that column existed in the CSV). Returns empty
    dict when nothing usable yet.
    """
    if not os.path.exists(ACCURACY_CSV_PATH):
        return {}
    buckets = {}
    try:
        with open(ACCURACY_CSV_PATH) as f:
            for r in csv.DictReader(f):
                level = (r.get("confidence_level") or "").strip()
                if not level:
                    continue
                try:
                    err = float(r["mllw_error_ft"])
                except (TypeError, ValueError, KeyError):
                    continue
                buckets.setdefault(level, []).append(abs(err))
    except OSError:
        return {}
    out = {}
    for level, errs in buckets.items():
        out[level] = {
            "mean_abs_err_ft": sum(errs) / len(errs),
            "n":               len(errs),
        }
    return out


def _confidence_uncertainty_ft(level):
    """Estimated ±uncertainty in SH peak MLLW (ft) for a confidence
    level. Uses per-band sample mean |error| from
    data/forecast_accuracy.csv when ≥ CONFIDENCE_CALIBRATION_MIN_N
    rows exist for that band; falls back to a hardcoded heuristic
    otherwise.

    HANDOFF 9b.6 refinement. Used by the confidence-qualifier
    sentences to translate the abstract "LOW confidence" badge
    into a concrete "peak ± X ft" range that propagates to a
    regime band.
    """
    cal = _calibrate_confidence_from_accuracy_log()
    band = cal.get(level)
    if band and band["n"] >= CONFIDENCE_CALIBRATION_MIN_N:
        return band["mean_abs_err_ft"]
    return _CONFIDENCE_HEURISTIC_FT.get(level, 0.30)


def _confidence_uncertainty_source(level):
    """Returns 'data' if the uncertainty for this level is data-driven
    (calibrated from the accuracy log), 'heuristic' otherwise. Used to
    annotate the confidence qualifier line so users know which it is."""
    cal = _calibrate_confidence_from_accuracy_log()
    band = cal.get(level)
    if band and band["n"] >= CONFIDENCE_CALIBRATION_MIN_N:
        return ("data", band["n"])
    return ("heuristic", 0)


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
    source, n = _confidence_uncertainty_source(level)
    source_phrase = (
        f"calibrated from {n} past forecasts at this confidence level"
        if source == "data"
        else "estimated heuristically until enough data accumulates"
    )
    out = [
        f"This is uncertainty about the peak Sandy Hook level "
        f"({peak:.2f} ft MLLW), which could land within roughly "
        f"±{unc:.2f} ft of the forecast ({source_phrase})."
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
    # day cards (2026-07-20) replaced the per-tide sentence list;
    # this block now carries the outage notice + confidence + unusual
    summary = ""
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


SEVERITY_RANK = {"dry": 0, "cold_lockout": 0, "street": 1,
                 "light": 2, "moderate": 3, "severe": 4}


def _render_day_cards_html(forecast):
    """DAY CARDS (user redesign 2026-07-20): the 72-h window organized
    by calendar day - TODAY / TOMORROW / day-3 - each card holding its
    own tides, rain outlook, and regime badge, with a WORST ribbon on
    the window's worst day. Replaces the TODAY box, WORST-72H strip,
    per-tide summary sentences, and the rain-outlook box (four objects
    slicing the same 72 h differently - "mish-mashed"). Overnight
    tides sit in their calendar day labeled "Tue 2:35 AM" (user:
    everyone can interpret that). TODAY is deliberately the heaviest
    card. The FLOODING-NOW nowcast override keeps targeting
    id=today-block = the TODAY card."""
    try:
        now_l = _station_local_now()
    except Exception:
        now_l = dt.datetime.now()
    days = [(now_l + dt.timedelta(days=i)).strftime("%Y-%m-%d")
            for i in range(3)]

    def _dk(base, i):
        d = now_l + dt.timedelta(days=i)
        return base + d.strftime("%a %b ").upper() + str(d.day)

    kickers = {days[0]: _dk("TODAY &middot; ", 0),
               days[1]: _dk("TOMORROW &middot; ", 1),
               days[2]: _dk("", 2)}
    rain_by_day = {d.get("day"): d
                   for d in (forecast.get("rain_outlook_72h") or [])}
    pr = forecast.get("pluvial_risk") or {}
    alerts = pr.get("nws_flood_alerts") or []
    peak_t = forecast.get("peak_time_local")

    def alert_covers(day):
        for a in alerts:
            on = (a.get("onset") or "")[:10]
            en = (a.get("ends") or "")[:10]
            if (not on or on <= day) and (not en or en >= day):
                yield a

    cards = []
    for day in days:
        tides = [t for t in (forecast.get("all_tides") or [])
                 if (t.get("time") or "").startswith(day)]
        tide_rank = 0
        tide_rows = []
        for t in tides:
            reg = ((t.get("depths_in") or {}).get("regime")) or "dry"
            tide_rank = max(tide_rank, SEVERITY_RANK.get(reg, 0))
            rel = ((t.get("forecast_peak_mllw") or 0)
                   + MLLW_TO_NAVD88_OFFSET - GRATE_SW) * 12
            star = "&#9733; " if t.get("time") == peak_t else ""
            past = ((t.get("hours_from_now") is not None)
                    and t["hours_from_now"] < 0)
            tide_rows.append(
                '<div class="dc-line">' + star
                + format_time_short(t["time"]) + " tide &mdash; "
                + regime_display(reg) + f" ({rel:+.1f}&Prime;)"
                + (' <span class="dc-past">(past)</span>' if past else "")
                + "</div>")
        rain = rain_by_day.get(day) or {}
        day_alerts = list(alert_covers(day))
        rain_bits = []
        if day_alerts:
            names = ", ".join(a.get("event", "") for a in day_alerts)
            a0 = day_alerts[0]
            on = (a0.get("onset") or "")
            span = ""
            if on[:10] == day and on[11:16]:
                hh, mm = int(on[11:13]), on[14:16]
                span = (" from " + str((hh % 12) or 12)
                        + (":" + mm if mm != "00" else "")
                        + ("AM" if hh < 12 else "PM"))
            rain_bits.append("<b>" + names + "</b>" + span)
        if rain.get("cum_in", 0) >= 0.02 or rain.get("max_pop_pct", 0) >= 20:
            rain_bits.append(
                f"~{rain.get('cum_in', 0):.2f}&Prime; rain, "
                f"PoP {rain.get('max_pop_pct', 0)}%"
                + (", thunderstorms" if rain.get("thunder") else ""))
        rain_line = ("Rain: " + "; ".join(rain_bits)
                     if rain_bits else "Rain: nothing significant expected")
        rain_risky = bool(day_alerts) or bool(
            pr.get("level") and (rain.get("thunder")
                                 or rain.get("peak_in_hr", 0) >= 0.15))
        if tide_rank >= 2 or (tide_rank >= 1 and not rain_risky):
            badge_cls = next(k for k, v in SEVERITY_RANK.items()
                             if v == tide_rank)
            badge = regime_display(badge_cls).upper()
        elif rain_risky:
            badge = ("RAIN FLOOD RISK" if pr.get("level") == "elevated"
                     else "POSSIBLE RAIN FLOODING")
            badge_cls = "light"
        else:
            badge_cls = "dry" if tide_rank == 0 else "street"
            badge = regime_display(badge_cls).upper()
        cards.append({"day": day, "kicker": kickers[day], "badge": badge,
                      "badge_cls": badge_cls, "tide_rows": tide_rows,
                      "rain_line": rain_line,
                      "rank": (tide_rank, 1 if rain_risky else 0)})
    worst = max(cards, key=lambda c: c["rank"])
    html_cards = []
    for c in cards:
        is_today = c["day"] == days[0]
        ribbon = (' <span class="dc-worst">&#9650; WORST OF 72 H</span>'
                  if c is worst and c["rank"] > (0, 0) else "")
        extra = ""
        if is_today:
            _lb = forecast.get("today_lookback")
            if _lb and (_lb.get("rel_grate_in") or 0) > 0:
                extra = (
                    '<div class="regime-summary dc-sofar"><b>SO FAR:</b> '
                    + regime_display(_lb.get("regime") or "").upper()
                    + f' &mdash; peak {_lb["rel_grate_in"]:+.1f}&Prime; at '
                    + _lb["time_local"] + ", " + _lb["source"] + ".</div>")
        html_cards.append(
            '<section class="regime regime-' + c["badge_cls"] + ' day-card'
            + (" day-card-today" if is_today else "")
            + ('" id="today-block">' if is_today else '">')
            + '<div class="regime-kicker">' + c["kicker"] + ribbon + '</div>'
            + '<div class="regime-label">' + c["badge"] + '</div>'
            + '<div class="regime-summary">'
            + "".join(c["tide_rows"])
            + '<div class="dc-line">' + c["rain_line"] + '</div>'
            + '</div>' + extra + '</section>')
    return '<div class="day-cards">' + "".join(html_cards) + '</div>'


def _render_how_flooding_html(forecast):
    return f"""
  <section class="reference">
    <h2>How flooding works here (plain English)</h2>
    <p><b>Tide floods.</b> When the bay at Sandy Hook climbs above the
       storm-grate elevations (roughly 6.3&ndash;6.6 ft on the gauge),
       bay water pushes backwards up the storm drains and surfaces in
       the street — the SE and SW grates across Bay Ave go first, and
       those areas stay wettest. No rain required.</p>
    <p><b>Rain floods — the tide does not matter.</b> This corner
       sits at the bottom of the Highlands hillside — the bluffs
       climb ~200 feet directly above it, and everything that falls
       on them surges downhill onto this low shelf within minutes.
       So the rainfall <i>rate</i> alone understates the input
       enormously: the intersection receives the hillside's water,
       not just its own. When a burst is intense enough (roughly 1+
       inch/hour), that amplified inflow fills the drain system
       beyond its discharge capacity, the water backs up, and it
       behaves exactly as if a high tide were in — <b>even at dead
       low tide</b>. Proven July 6, 2026: about 7&Prime; of water at
       the curb while the bay sat more than a foot below the lowest
       grate. In rain floods the backup concentrates around the
       NE/NW grates (the drain trunk line) — the opposite corner
       from tide floods. <b>Take-home: never judge flood risk here
       by the tide chart alone.</b> Once the rain is hard enough,
       the tide level is irrelevant to whether it floods. The
       timing is now measured and modeled (v0.10): street water
       lags the rain peak by ~15 min, can rise 8&Prime; in 12
       minutes, and drains back within ~20&ndash;30 min of the rain
       stopping. All four floods measured to date &mdash; including
       the two worst &mdash; were rain-driven.</p>
    <p><b>Compound (the worst case).</b> The tide can't prevent a rain
       flood, but it can raise its floor: heavy rain landing on a high
       tide has nowhere to go at all. The biggest flood in this
       project's records — October 30, 2025, water past the bottom
       porch step — was exactly this combination. The two add
       <i>sub-linearly</i>, though: the deeper the water, the larger
       the area it covers, so each additional inch takes more water
       than the last. The same rain that raises a low-tide street
       pool by a foot might add only a few inches on top of a high
       tide — but those inches start from a much higher floor.</p>
  </section>

"""


def _render_reference_scale_html(forecast):
    return f"""
  <section class="reference">
    <h2>Reference scale</h2>
    <p>Sandy Hook observed water level (MLLW; {CURRENT_MODEL_VERSION} thresholds = landmark elevation + 2.82):</p>
    <ul>
      <li>&lt; 6.34 ft — no flooding, nothing visible</li>
      <li>6.34 ft — water emerges from SW grate across Bay (lowest grate)</li>
      <li>6.42 ft — SE grate across Bay emerges</li>
      <li>6.46 ft — SE/SW pavement corners wet; Bay Ave upstream grate emerges</li>
      <li>6.60 ft — water at gutter / curb edge at walkway (don't park there)</li>
      <li>6.62 ft — NE (user's corner) + NW grates emerge (Pathway B)</li>
      <li>6.98 ft — water tops curb at walkway (flood onset at property)</li>
      <li>7.15 ft — water on sidewalk under the walkway lawn step</li>
      <li>7.18 ft — Bay Ave road middle covered</li>
      <li>7.36 ft — intersection high point submerged</li>
      <li>7.48 ft — water at lawn / walkway step</li>
      <li>7.50 ft — water at bottom of porch steps</li>
      <li>8.23 ft — water over the first porch step</li>
      <li>10.90 ft — water at the porch deck (Sandy-class)</li>
    </ul>
  </section>

"""


def _render_glossary_html(forecast):
    return f"""
  <section class="reference">
    <h2>Regime glossary</h2>
    <p>The label in the subject line (NO FLOODING / STREET / LIGHT / MODERATE / SEVERE) summarises severity based on water depth at the curb.</p>
    <ul>
      <li><b>no flooding</b> — {REGIME_GLOSSARY['dry']}</li>
      <li><b>street</b> — {REGIME_GLOSSARY['street']}</li>
      <li><b>light</b> — {REGIME_GLOSSARY['light']}</li>
      <li><b>moderate</b> — {REGIME_GLOSSARY['moderate']}</li>
      <li><b>severe</b> — {REGIME_GLOSSARY['severe']}</li>
      <li><b>cold lockout</b> — {REGIME_GLOSSARY['cold_lockout']}</li>
    </ul>
  </section>

"""


def render_details_page(forecast):
    """The "For more information" page (docs/details.html, 2026-07-20
    multi-page split): deep reference material off the landing scroll —
    how-flooding, reference scale, historical floods, the model term
    by term (incl. the rain-pathway calculator), spot-check protocol,
    accuracy, glossary. Anchors match _render_more_info_links_html."""
    gen = ""
    try:
        gen = _station_local_now().strftime("%a %b %d, %I:%M %p ET")
    except Exception:
        pass
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="robots" content="noindex">
<title>Bay Ave Barnacle — details &amp; reference</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
<main>
  <header>
    <h1><a href="index.html" style="text-decoration:none;color:inherit">Bay Ave Barnacle</a> — details</h1>
    <p class="subtitle"><a href="index.html">&larr; back to the forecast</a> &middot; reference &amp; model internals &middot; generated {gen}</p>
  </header>

  <div id="how"></div>
{_render_how_flooding_html(forecast)}
  <div id="reference"></div>
{_render_reference_scale_html(forecast)}
  <div id="history"></div>
{_render_historical_floods_html()}
  <div id="model"></div>
{_render_equation_widget_html(forecast)}
  <div id="spotcheck"></div>
  {_spot_check_block_html(forecast)}
  <div id="accuracy"></div>
  {_render_accuracy_html(forecast)}
  <div id="glossary"></div>
{_render_glossary_html(forecast)}

  <footer>
    <p><a href="index.html">&larr; back to the live forecast</a></p>
  </footer>
</main>
</body></html>"""


def _render_more_info_links_html():
    """Landing-page links to details.html (2026-07-20 multi-page
    split — user: landing ends at the heat-map; deep reference
    material moves off the scroll)."""
    items = [
        ("how", "How flooding works here (plain English)"),
        ("reference", "Reference scale"),
        ("history", "How bad can it get? The 10 worst floods"),
        ("model", "The model, term by term"),
        ("spotcheck", "Spot-check (help calibrate the model)"),
        ("accuracy", "Model accuracy — predicted vs observed"),
        ("glossary", "Regime glossary"),
    ]
    links = "".join(
        f'<li><a href="details.html#{a}">{t}</a></li>'
        for a, t in items)
    return ('<section class="more-info"><h2>For more information</h2>'
            f'<ul class="more-info-list">{links}</ul></section>')


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
    if forecast.get("tide_predictions_stale"):
        parts.append(
            '<p class="tldr-confidence confidence-low"><b>NOAA tide-'
            'prediction service outage</b> &mdash; tide times/heights '
            'below are served from cached astronomy (identical maths, '
            'just not refreshed). Rain-risk inputs (QPF, alerts) are '
            'unaffected and live.</p>')
    if summary:
        # One tide per line (user 2026-07-09): the semicolon-joined
        # sentence was a wall of text. Keep the "Next 24 h:" lead-in,
        # then indent each tide entry on its own line.
        html_summary = summary
        for lead in ("Next 72 h — high tides: ",
                     "Next 24 h: ", "Next 24h: "):
            if summary.startswith(lead):
                entries = summary[len(lead):].split("; ")
                html_summary = (
                    lead.strip() + "<br>" + "<br>".join(
                        f'<span style="padding-left:1em;display:inline-block">'
                        f'{e.rstrip(".")}{";" if i < len(entries) - 1 else "."}'
                        f'</span>'
                        for i, e in enumerate(entries)))
                break
        parts.append(f'<p class="tldr-summary">{html_summary}</p>')
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


def _render_rain_outlook_html(forecast):
    """The rain twin of the high-tides summary box (user 2026-07-09):
    one line per local day for the next 72 h, plus alert / burst
    context when pluvial risk is live. Rain-DNA: rain gets the same
    top-of-page altitude as the tides."""
    days = forecast.get("rain_outlook_72h") or []
    if not days:
        return ""
    pr = forecast.get("pluvial_risk") or {}
    lines = []
    for d in days:
        if d["cum_in"] < 0.02 and d["max_pop_pct"] < 20:
            desc = f"no measurable rain expected (PoP {d['max_pop_pct']}%)"
        else:
            desc = (f"~{d['cum_in']:.2f}&Prime; total, peak "
                    f"{d['peak_in_hr']:.2f} in/hr smeared, "
                    f"PoP {d['max_pop_pct']}%")
            if d["thunder"]:
                desc += ", thunderstorms possible"
        lines.append(
            f'<span style="padding-left:1em;display:inline-block">'
            f'{d["label"]} — {desc};</span>')
    body = "Next 72 h — rain:<br>" + "<br>".join(lines)
    body = body.rstrip(";</span>") + ".</span>"
    extra = ""
    alerts = pr.get("nws_flood_alerts") or []
    if alerts:
        names = ", ".join(a.get("event", "") for a in alerts)
        extra += (f'<br><b>{names} in effect (NWS).</b>')
    if pr.get("level") and pr.get("potential_low_tide_navd88"):
        pot_in = (pr["potential_low_tide_navd88"] - GRATE_SW) * 12
        extra += (
            f'<br>A convective burst could bring street water to '
            f'~{pot_in:+.0f}&Prime; vs SW grate at ANY tide (QPF smears '
            f'bursts — the rates above understate cells).')
    return (
        '<section class="tldr">'
        f'<p class="tldr-summary">{body}{extra}</p>'
        '</section>')


def _upcoming_tides_only(forecast):
    """all_tides minus any tide whose peak is already past (rollup includes
    very-recent past tides for visibility; summary blocks like rain
    timing should not — past-tide rain info is stale)."""
    return [t for t in (forecast.get("all_tides") or [])
            if (t.get("hours_from_now") is None
                or t["hours_from_now"] >= 0)]


def _rain_is_notable(forecast):
    """True if there's enough rain in the next 24 h to warrant a rain block.
    Threshold deliberately low (0.05 in cumulative) so even minor wet weather
    surfaces — these are the events where timing relative to tide matters."""
    return (forecast.get("cumulative_rain_24h_in") or 0) >= 0.05 or any(
        (t.get("peak_rain_in_hr") or 0) >= 0.05
        for t in _upcoming_tides_only(forecast)
    )


def _render_rain_timing_text(forecast):
    """Plain-text rain timing block. Empty list when no rain is expected."""
    if not _rain_is_notable(forecast):
        return []
    cum = forecast.get("cumulative_rain_24h_in") or 0
    lines = ["Rain & tide timing:"]
    lines.append(f"  Cumulative next 24 h: {cum:.2f}\"")
    peak_t = forecast.get("peak_time_local")
    for t in _upcoming_tides_only(forecast):
        peak_rain = t.get("peak_rain_in_hr") or 0
        offset = t.get("peak_rain_offset_h")
        label = "★ peak tide" if t["time"] == peak_t else "lower high"
        # weekday-annotated (user 2026-07-20): bare clock times here
        # spanned three calendar days with no day indication
        when = format_time_short(t["time"])
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
    for t in _upcoming_tides_only(forecast):
        peak_rain = t.get("peak_rain_in_hr") or 0
        offset = t.get("peak_rain_offset_h")
        label = "★ peak tide" if t["time"] == peak_t else "lower high"
        # weekday-annotated (user 2026-07-20): bare clock times here
        # spanned three calendar days with no day indication
        when = format_time_short(t["time"])
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


LABELED_OBSERVATIONS_PATH = os.path.join(
    _REPO_ROOT, "data", "labeled_observations.csv"
)


def _load_outcome_depth_rows():
    """Load `data/labeled_observations.csv` and return rows usable for
    outcome-depth accuracy (HANDOFF 9b.8 mode 2): those with both
    `observed_depth_in` and `model_predicted_depth_in` numeric.

    Each returned dict has:
      time, landmark, observed_in, predicted_in, error_in (signed,
      positive = model over-predicted), notes
    """
    if not os.path.exists(LABELED_OBSERVATIONS_PATH):
        return []
    out = []
    try:
        with open(LABELED_OBSERVATIONS_PATH) as f:
            for r in csv.DictReader(f):
                try:
                    obs = float(r["observed_depth_in"])
                    pred = float(r["model_predicted_depth_in"])
                except (TypeError, ValueError, KeyError):
                    continue
                out.append({
                    "time":       r.get("observation_time_local", ""),
                    "landmark":   r.get("landmark_key", ""),
                    "observed_in":  obs,
                    "predicted_in": pred,
                    "error_in":   pred - obs,
                    "notes":      r.get("notes", ""),
                })
    except OSError:
        return []
    return out


# Sandy Hook MLLW threshold for "flooded" in the binary classifier.
# 6.02 = lowest grate emerges (the earliest visible-water signal at the
# property). Configurable later (HANDOFF 9b.8 mentions "threshold
# configurable per view") — keeping it as a constant for now.
FLOODED_THRESHOLD_SH_MLLW = SH_FIRST_WATER  # 6.34 under v0.9 (was hardcoded 6.02, the v0.6 value)


# Observed-peak cache so the lead-time accuracy view doesn't hit NOAA
# once per past tide on every hourly workflow run. Grows monotonically;
# old entries never expire.
OBSERVED_PEAKS_CACHE_PATH = os.path.join(
    _REPO_ROOT, "data", "observed_peaks_cache.csv"
)


def _load_observed_peaks_cache():
    if not os.path.exists(OBSERVED_PEAKS_CACHE_PATH):
        return {}
    out = {}
    try:
        with open(OBSERVED_PEAKS_CACHE_PATH) as f:
            for r in csv.DictReader(f):
                try:
                    out[r["target_tide_time"]] = float(r["observed_peak_mllw"])
                except (TypeError, ValueError, KeyError):
                    continue
    except OSError:
        return {}
    return out


def _save_observed_peaks_cache(cache):
    fields = ["target_tide_time", "observed_peak_mllw"]
    try:
        os.makedirs(os.path.dirname(OBSERVED_PEAKS_CACHE_PATH), exist_ok=True)
        with open(OBSERVED_PEAKS_CACHE_PATH, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for target, peak in sorted(cache.items()):
                w.writerow({
                    "target_tide_time": target,
                    "observed_peak_mllw": f"{peak:.3f}",
                })
    except OSError as e:
        print(f"WARNING: observed peaks cache write failed: {e}", flush=True)


# Lead-time accuracy buckets — how many hours BEFORE the peak the
# prediction was made. Smaller numbers = closer to the event.
LEADTIME_BUCKETS = [
    (0,   3,   "0-3 h before peak"),
    (3,   6,   "3-6 h"),
    (6,   12,  "6-12 h"),
    (12,  24,  "12-24 h"),
    (24,  48,  "24-48 h"),
    (48,  120, "48-120 h"),
]


def _compute_leadtime_accuracy(max_age_days=14):
    """Walk data/predictions_log.csv and group prediction errors by how
    far in advance they were made (lead time). Tells you whether the
    model converges as the tide approaches.

    For each past target_tide_time within `max_age_days` of now, fetch
    the observed peak (cached on disk) and bucket each prediction's
    `predicted - observed` error by the row's hours_until_peak.

    Returns dict with `buckets` (list of per-bucket stats) + `n_total`
    + `n_tides`, or None when no usable data yet.

    HANDOFF 9b.8 lead-time axis.
    """
    if not os.path.exists(PREDICTIONS_LOG_PATH):
        return None

    now_utc = dt.datetime.now(dt.timezone.utc)
    cutoff_min = now_utc - dt.timedelta(days=max_age_days)
    cutoff_max = now_utc - dt.timedelta(hours=2)  # tide has "ended"

    # Group rows by target_tide_time, only past tides within window.
    by_target = {}
    try:
        with open(PREDICTIONS_LOG_PATH) as f:
            for r in csv.DictReader(f):
                target_str = r.get("target_tide_time", "") or ""
                try:
                    target_dt = dt.datetime.strptime(
                        target_str, "%Y-%m-%d %H:%M"
                    )
                    # TZ fix 2026-07-20: proper station-tz conversion
                    # (hardcoded +4 was wrong in EST).
                    target_utc = target_dt.replace(
                        tzinfo=STATION_TZ).astimezone(dt.timezone.utc)
                except (ValueError, TypeError):
                    continue
                if target_utc > cutoff_max:
                    continue  # tide not yet past
                if target_utc < cutoff_min:
                    continue  # too old
                try:
                    pred_mllw = float(r["sh_peak_mllw_predicted"])
                    hu = float(r["hours_until_peak"])
                except (TypeError, ValueError, KeyError):
                    continue
                by_target.setdefault(target_str, []).append({
                    "pred":              pred_mllw,
                    "hours_until_peak":  hu,
                })
    except OSError:
        return None

    if not by_target:
        return None

    # Look up observed peaks (use cache, fetch any missing)
    cache = _load_observed_peaks_cache()
    fetched_new = False
    for target_str in by_target:
        if target_str in cache:
            continue
        peak, _ = _fetch_actual_peak_around(target_str)
        if peak is not None:
            cache[target_str] = peak
            fetched_new = True
    if fetched_new:
        _save_observed_peaks_cache(cache)

    # Bucket errors by lead time
    bucket_errs = {label: [] for _, _, label in LEADTIME_BUCKETS}
    n_total = 0
    n_tides = 0
    for target_str, rows in by_target.items():
        obs = cache.get(target_str)
        if obs is None:
            continue
        n_tides += 1
        for row in rows:
            hu = row["hours_until_peak"]
            err = row["pred"] - obs
            for lo, hi, label in LEADTIME_BUCKETS:
                if lo <= hu < hi:
                    bucket_errs[label].append(err)
                    n_total += 1
                    break

    if n_total == 0:
        return None
    buckets_out = []
    for _, _, label in LEADTIME_BUCKETS:
        errs = bucket_errs[label]
        if not errs:
            continue
        n = len(errs)
        buckets_out.append({
            "label":           label,
            "n":               n,
            "mean_err_ft":     sum(errs) / n,
            "mean_abs_err_ft": sum(abs(e) for e in errs) / n,
        })
    return {
        "buckets":  buckets_out,
        "n_total":  n_total,
        "n_tides":  n_tides,
    }


def _compute_classifier_metrics():
    """Binary flood-classifier confusion matrix from forecast_accuracy.csv.
    HANDOFF 9b.8 mode 3.

    Flooded definition:
      observed_flooded = observed SH peak >= FLOODED_THRESHOLD_SH_MLLW
      predicted_flooded = predicted regime is not 'dry'

    Returns None when no rows in the accuracy log.
    """
    rows = _load_accuracy_rows()
    if not rows:
        return None
    tp = fp = fn = tn = 0
    for r in rows:
        pred_flood = (r.get("regime") or "") not in ("dry", "")
        obs_flood = r["observed"] >= FLOODED_THRESHOLD_SH_MLLW
        if pred_flood and obs_flood:
            tp += 1
        elif pred_flood and not obs_flood:
            fp += 1
        elif not pred_flood and obs_flood:
            fn += 1
        else:
            tn += 1
    total = tp + fp + fn + tn
    def safe_div(a, b):
        return (a / b) if b > 0 else None
    return {
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "total": total,
        "fpr":      safe_div(fp, fp + tn),
        "fnr":      safe_div(fn, fn + tp),
        "accuracy": safe_div(tp + tn, total),
        "threshold_sh_mllw": FLOODED_THRESHOLD_SH_MLLW,
    }


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

    # Mode 2: outcome-depth accuracy from data/labeled_observations.csv
    # (HANDOFF 9b.8 mode 2). Each row is one in-the-field observation
    # that already has both `observed_depth_in` and
    # `model_predicted_depth_in` columns — no joining needed.
    outcome_rows = _load_outcome_depth_rows()
    outcome_html = ""
    if outcome_rows:
        n = len(outcome_rows)
        mean_err = sum(r["error_in"] for r in outcome_rows) / n
        mean_abs = sum(abs(r["error_in"]) for r in outcome_rows) / n
        max_abs = max(abs(r["error_in"]) for r in outcome_rows)
        rows_html = ""
        for r in outcome_rows:
            err = r["error_in"]
            sign_cls = "err-over" if err > 0 else ("err-under" if err < 0 else "")
            rows_html += (
                f'<tr>'
                f'<td>{r["time"]}</td>'
                f'<td>{r["landmark"]}</td>'
                f'<td>{r["observed_in"]:+.1f}&Prime;</td>'
                f'<td>{r["predicted_in"]:+.1f}&Prime;</td>'
                f'<td class="{sign_cls}">{err:+.1f}&Prime;</td>'
                f'</tr>'
            )
        outcome_html = (
            f'<div class="outcome-block">'
            f'<h3 style="margin:12px 0 4px 0;font-size:15px">'
            f'Outcome-depth accuracy (per-observation)</h3>'
            f'<p style="font-size:13px;margin:4px 0">'
            f'N = {n} labeled observations. Mean error '
            f'<b>{mean_err:+.1f}&Prime;</b> (positive = model over-predicts), '
            f'mean |error| <b>{mean_abs:.1f}&Prime;</b>, '
            f'worst |error| {max_abs:.1f}&Prime;.</p>'
            f'<table class="outcome-table">'
            f'<thead><tr><th>Time</th><th>Landmark</th>'
            f'<th>Observed</th><th>Predicted</th><th>Error</th></tr></thead>'
            f'<tbody>{rows_html}</tbody></table>'
            f'<p class="note">Compares each user-logged observation in '
            f'<code>data/labeled_observations.csv</code> to the model\'s '
            f'predicted depth at the same landmark at the same time, '
            f'<b>as logged at observation time</b> — an append-only '
            f'record of the model version that was live that day, kept '
            f'unrevised on purpose. The large early over-predictions '
            f'(2026-05-18, offshore-wind event) are v0.7-era rows that '
            f'motivated the v0.8 wind adjustment; they are history, not '
            f'current-model skill. Sparse but each row is a real '
            f'observation with real depth.</p>'
            f'</div>'
        )

    # Lead-time accuracy (HANDOFF 9b.8 lead-time axis): does the model
    # converge as the tide approaches? Built from predictions_log.csv
    # (HANDOFF 9b.3) joined to NOAA observed peaks (cached on disk).
    leadtime = _compute_leadtime_accuracy()
    leadtime_html = ""
    if leadtime and leadtime["buckets"]:
        rows_html = ""
        for b in leadtime["buckets"]:
            err = b["mean_err_ft"]
            sign_cls = "err-over" if err > 0 else ("err-under" if err < 0 else "")
            rows_html += (
                f'<tr>'
                f'<td>{b["label"]}</td>'
                f'<td>{b["n"]}</td>'
                f'<td class="{sign_cls}">{err:+.2f} ft</td>'
                f'<td>{b["mean_abs_err_ft"]:.2f} ft</td>'
                f'</tr>'
            )
        leadtime_html = (
            f'<div class="leadtime-block">'
            f'<h3 style="margin:12px 0 4px 0;font-size:15px">'
            f'Accuracy by lead time (predictions log)</h3>'
            f'<p style="font-size:13px;margin:4px 0">'
            f'{leadtime["n_total"]} predictions across '
            f'{leadtime["n_tides"]} past tides. Each row groups '
            f'predictions by how many hours BEFORE the tide they were '
            f'made — closer to peak should mean smaller error.</p>'
            f'<table class="outcome-table">'
            f'<thead><tr><th>Lead time</th><th>N predictions</th>'
            f'<th>Mean error (signed)</th><th>Mean |error|</th></tr></thead>'
            f'<tbody>{rows_html}</tbody></table>'
            f'<p class="note">From '
            f'<code>data/predictions_log.csv</code> joined to NOAA '
            f'observed peaks (cached at '
            f'<code>data/observed_peaks_cache.csv</code>). Populated '
            f'over time as hourly predictions accumulate.</p>'
            f'</div>'
        )

    # Binary classifier metrics (HANDOFF 9b.8 mode 3)
    cm = _compute_classifier_metrics()
    classifier_html = ""
    if cm and cm["total"] > 0:
        def pct(x):
            return f"{x * 100:.1f}%" if x is not None else "—"
        classifier_html = (
            f'<div class="classifier-block">'
            f'<h3 style="margin:12px 0 4px 0;font-size:15px">'
            f'Flood / no-flood (binary, SH ≥ {cm["threshold_sh_mllw"]:.2f} ft = lowest grate)</h3>'
            f'<table class="confusion-table"><tbody>'
            f'<tr><th></th><th>Actual flood</th><th>Actual dry</th></tr>'
            f'<tr><th>Predicted flood</th>'
            f'<td class="tp">{cm["tp"]} TP</td>'
            f'<td class="fp">{cm["fp"]} FP</td></tr>'
            f'<tr><th>Predicted dry</th>'
            f'<td class="fn">{cm["fn"]} FN</td>'
            f'<td class="tn">{cm["tn"]} TN</td></tr>'
            f'</tbody></table>'
            f'<p style="font-size:13px;margin:6px 0">'
            f'Overall accuracy: <b>{pct(cm["accuracy"])}</b> &middot; '
            f'False-positive rate: {pct(cm["fpr"])} &middot; '
            f'False-negative rate: {pct(cm["fnr"])} &middot; '
            f'N = {cm["total"]}</p>'
            f'</div>'
        )
    note_html = (
        '<p class="note">Positive mean error = model over-predicts on '
        'average. Each point is one archived daily forecast (since the '
        'JSON archive started). x = predicted Sandy Hook peak, y = '
        'actual NOAA observed peak. The dashed diagonal is perfect '
        'prediction (y=x); points above the line = model under-predicted, '
        'below = over-predicted. Raw data: '
        '<code>data/forecast_accuracy.csv</code>.</p>'
        '<p class="note">Scope: this scores the <b>tide-keyed input</b> '
        '— each day\'s predicted vs observed peak at the Sandy Hook '
        'gauge, as the forecast actually ran that day (an append-only '
        'record; rows are never recomputed under newer models). It '
        'cannot see rain-driven street floods (the gauge is 4 miles '
        'away and tide-only): pluvial skill is tracked separately '
        'against the spot-check log in '
        '<code>data/labeled_observations.csv</code>, currently four '
        'measured rain events, all fit by the v0.10 tank model — '
            'one parameter set, including two full measured hydrographs.</p>'
    )

    rows = _load_accuracy_rows()
    if len(rows) < 2:
        # Not enough data for a scatter chart yet — text summary +
        # (optional) outcome-depth + lead-time + binary classifier blocks
        return (
            '<section class="accuracy">'
            '<h2>Model accuracy</h2>'
            f'{summary_html}'
            f'{outcome_html}'
            f'{leadtime_html}'
            f'{classifier_html}'
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
  {outcome_html}
  {leadtime_html}
  {classifier_html}
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


def _lookahead_label(row):
    """Build the human-readable significance label for one look-ahead
    row, appending the spring-tide marker when present (HANDOFF 25a / Z)."""
    base = row["label"]
    spring = row.get("spring_tide") or ""
    if spring:
        return f"{base}  ·  spring tide ({spring})"
    return base


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
            f"  {when_full}  —  {r['mllw']:.2f} ft MLLW  ({_lookahead_label(r)})"
        )
    lines.append(
        "  These are baseline astronomical tides — surge isn't forecast "
        "this far out. An event of significance also needs surge or rain. "
        "Spring tides (new/full moon ±2 d) are when astronomical highs "
        "stack highest; expect tighter margins on those days."
    )
    return lines


def _render_lookahead_html(forecast):
    """HTML version of the look-ahead block. HANDOFF 9b.7."""
    rows = forecast.get("lookahead_watch") or []
    if not rows:
        return ""
    body = ""
    for r in rows:
        spring_cls = f" spring-{r['spring_tide'].replace(' ', '-')}" if r.get("spring_tide") else ""
        body += (
            f'<tr class="{r["severity_class"]}{spring_cls}">'
            f'<td>{format_time_full(r["time"])}</td>'
            f'<td>{r["mllw"]:.2f}</td>'
            f'<td>{_lookahead_label(r)}</td>'
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
        'than as a flood forecast. Spring-tide rows (new / full moon '
        '±2 d) are marked — those are when astronomical highs stack '
        'highest and a small surge can do extra damage.</p>'
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
        '(SW grate, 3.52 NAVD88), always positive or negative. '
        '"Highest landmark" applies the 0.00 ft local enhancement (v0.8, carried in v0.9) '
        'to the observed peak.</p>'
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
    "corner_SE":             "sentinel",
    "corner_SW":             "sentinel",
    "gutter_walkway":        "parking",
    "grate_NE":              "Pathway B",
    "curb":                  "flood onset",
}

# Short labels for the compact per-tide table. Full labels live in LANDMARKS.
LANDMARK_SHORT_LABELS = {
    "grate_SW":              "SW grate",
    "grate_SE":              "SE grate",
    "corner_SE":             "SE corner",
    "corner_SW":             "SW corner",
    "grate_bay_ave_upstream": "Upstream grate",
    "gutter_walkway":        "Gutter",
    "grate_NE":              "NE grate",
    "grate_NW":              "NW grate",
    "corner_NE":             "NE corner",
    "corner_NW":             "NW corner",
    "curb":                  "Curb",
    "road_middle":           "Road middle",
    "intersection_highpoint": "Intersection",
    "lawn_step":             "Lawn step",
    "porch_step_base":       "Porch base",
    "porch_step1_top":       "Porch step 1",
    "porch_deck":            "Porch deck",
}


def landmark_summary(depths, sandy_hook_peak_mllw):
    """For a given forecast peak + per-landmark depths, return a compact
    summary for the per-tide table:
        (short_label, inches_above_landmark, relative_to_lowest_inches)
    where:
      - short_label = highest landmark exceeded by water level, OR the
        lowest landmark (grate_SW in v0.7) if no landmark is exceeded
      - inches_above_landmark = depth at that landmark from depths dict
        (positive); when no exceedance, negative inches below the lowest
        landmark (computed from tide-only water level)
      - relative_to_lowest = depth at the lowest landmark from depths
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
    # Note 2026-05-19: cold-lockout no longer flips confidence to HIGH
    # — see history/reports/cold_weather_retrospective.md. Cold
    # conditions are surfaced as a separate advisory instead.
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
        # "cold_lockout" regime can no longer be produced by
        # predict_landmark_depths after 2026-05-19 (rule demoted to
        # advisory). Branch retained for safety / legacy archive
        # entries that may have the old regime label.
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
    return "Next 72 h — high tides: " + "; ".join(parts) + "."


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
    "dry":          "no visible flood water at any landmark",
    "street":       "water on the street at sub-curb landmarks; curb still clear",
    "light":        "water at curb (0–4 inches)",
    "moderate":     "water at curb (4–8 inches)",
    "severe":       "water past lawn step / bulkhead overtopping territory",
    "cold_lockout": "cold conditions met but rule no longer actively applied (see retrospective)",
}

# User-facing display names for regimes. The internal keys (esp. "dry")
# are frozen — they're baked into predictions_log.csv (~5k rows), CSS
# classes, and the accuracy-log comparisons. Display-only mapping.
# Why: "DRY" reads ridiculous on a rainy day with no flooding (user,
# 2026-07-06). What the regime actually means is "no flooding".
REGIME_DISPLAY = {
    "dry":          "no flooding",
    "cold_lockout": "cold lockout",
}


def regime_display(regime):
    """User-facing label for an internal regime key."""
    return REGIME_DISPLAY.get(regime, regime)


def headline_for(forecast, regime, scope="today"):
    """(headline_text, css_regime_class) for banners/subjects.

    Fixes the contradiction (user 2026-07-07) where a rainy no-tide
    day read "NO FLOODING" right next to "RAIN FLOOD RISK": when the
    tide-derived regime is dry but pluvial risk is live, the RAIN
    message IS the headline and "no tidal flooding expected" becomes
    the detail. CSS class shifts to 'light' (amber) so the banner
    color matches the message."""
    _pr_h = forecast.get("pluvial_risk") or {}
    if scope == "today" and _pr_h.get("risk_today") is False:
        # risk window opens tomorrow — TODAY's headline must not
        # claim it (2026-07-20 scope fix); the 72-h strip carries it.
        return (regime_display(regime).upper(), regime)
    level = (_pr_h.get("level")
             if forecast else None)
    if regime == "dry" and level:
        text = ("RAIN FLOOD RISK" if level == "elevated"
                else "POSSIBLE RAIN FLOODING")
        return text, "light"
    return regime_display(regime).upper(), regime


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
        season = season_by_key.get(
            key, season_by_key.get(SEASONALITY_KEY_ALIASES.get(key), {})) or {}
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
                        if s["threshold_ft"] == SH_CURB_THRESHOLD), None)  # CSV regenerated 2026-07-06 with v0.9 thresholds
    if curb_events is None or curb_events > 0:
        return None
    raw = mtd.get("peak_6min_mllw")
    if raw is None or raw < SH_CURB_THRESHOLD - 0.1:
        return None
    when = format_time_full(mtd.get("peak_6min_time") or "")
    mins = mtd.get("minutes_above_curb", 0)
    if raw >= SH_CURB_THRESHOLD and mins > 0:
        return (f"Closest call: water touched {SH_CURB_THRESHOLD} ft on the 6-min sensor "
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
        (t.get("depths_in") or {}).get("corner_SE", 0) > 0
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
        if peak >= SH_CURB_THRESHOLD:
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


def _landmarks_section_html(forecast, today=None, wrapper="section",
                            include_spot_check=True):
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
    if include_spot_check:
        return landmarks_section + _spot_check_block_html(forecast, today)
    return landmarks_section


# ============================================================
# Email rendering and sending
# ============================================================
def render_email(forecast):
    d = forecast["depths_in"]
    regime = d["regime"]
    try:
        _now_k = _station_local_now()
    except Exception:
        _now_k = dt.datetime.now()
    _kick_today = _now_k.strftime("%a %b ") + str(_now_k.day)
    _kick_end = (_now_k + dt.timedelta(hours=72)).strftime("%a")
    peak_t = forecast["peak_time_local"]
    peak_ft = forecast["peak_forecast_observed_mllw"]
    all_tides = forecast.get("all_tides", [])

    subject_short, subject_above, _ = landmark_summary(d, peak_ft)
    headline, _ = headline_for(forecast, regime)
    # Email parity with the site's TODAY/WORST split (2026-07-17):
    # subject leads with TODAY (incl. the so-far lookback when water
    # already happened); the worst-72h peak becomes the tail.
    _tr = forecast.get("today_regime") or regime
    _today_head, _ = headline_for(forecast, _tr)
    _lb = forecast.get("today_lookback")
    if _lb and (_lb.get("rel_grate_in") or 0) > 0:
        _today_head += (f" (so far: {regime_display(_lb.get('regime') or '').upper()}"
                        f" {_lb['rel_grate_in']:+.1f}\")")
    subject = (f"[342 Bay] TODAY {_today_head} | WORST 72H {headline}: "
               f"{peak_ft:.2f} ft at {format_time_short(peak_t)} "
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
        "  Rel = inches above the lowest landmark (SW grate across Bay, "
        "3.64 NAVD88) — always."
    )

    summary_lines = _render_summary_text(forecast)
    summary_block = ("\n".join(summary_lines) + "\n\n") if summary_lines else ""
    rain_lines = _render_rain_timing_text(forecast)
    rain_block = ("\n".join(rain_lines) + "\n\n") if rain_lines else ""
    pr = forecast.get("pluvial_risk") or {}
    if pr.get("level"):
        rain_block = (
            f"*** PLUVIAL FLOOD RISK ({pr['level'].upper()}) — independent of tide ***\n"
            + "".join(
                f"  NWS ALERT: {a.get('event', '')} — {a.get('headline', '')}\n"
                for a in (pr.get("nws_flood_alerts") or []))
            + f"  Peak QPF {pr.get('peak_rain_rate_24h_in_hr', 0):.2f} in/hr, "
            f"cumulative {pr.get('cumulative_rain_24h_in', 0):.2f}\", "
            f"max PoP {pr.get('max_pop_24h_pct', 0)}%"
            + (", thunderstorm wording" if pr.get("convective_wording") else "")
            + ".\n  Heavy rain alone floods the intersection (see 2026-07-06"
            " event); tide-keyed predictions below do not capture this.\n\n"
        ) + rain_block
    recap_lines = _render_recent_history_text(forecast)
    recap_block = ("\n".join(recap_lines) + "\n\n") if recap_lines else ""
    low_lines = _render_low_tides_text(forecast)
    low_block = ("\n".join(low_lines) + "\n\n") if low_lines else ""
    accuracy_lines = _render_accuracy_text(forecast)
    accuracy_block = ("\n".join(accuracy_lines) + "\n\n") if accuracy_lines else ""
    lookahead_lines = _render_lookahead_text(forecast)
    lookahead_block = ("\n".join(lookahead_lines) + "\n\n") if lookahead_lines else ""
    cold_lines = _render_cold_advisory_text(forecast)
    cold_block = ("\n".join(cold_lines) + "\n\n") if cold_lines else ""

    _today_head_text, _ = headline_for(
        forecast, forecast.get("today_regime") or regime)
    _lbt = forecast.get("today_lookback")
    _lb_text = ""
    if _lbt and (_lbt.get("rel_grate_in") or 0) > 0:
        _lb_text = (f" | so far: "
                    f"{regime_display(_lbt.get('regime') or '').upper()} "
                    f"{_lbt['rel_grate_in']:+.1f}\" at {_lbt['time_local']}")
    text = f"""\
TODAY: {_today_head_text}{_lb_text}
WORST 72H: {headline}: {peak_ft:.2f} ft at {format_time_short(peak_t)}

Bay Ave Barnacle flood forecast for 342 Bay Ave - {dt.date.today().isoformat()}

{summary_block}{cold_block}High tides in next 24h ( * = worst case, headlined below):
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
  Cold conditions: {'YES — ice-lock hypothesis met but no longer applied (see retrospective)' if forecast['cold_lockout'] else 'no'}

{rain_block}{_landmarks_section_text(forecast)}
Regime: {regime_display(regime)} — {REGIME_GLOSSARY.get(regime, '')}
Today ({_station_local_now().strftime("%A")}): {regime_display(forecast.get('today_regime') or regime)}; peak water {forecast.get('today_rel_grate_sw_in', 0) or 0:+.1f}" vs SW grate{f" at {forecast['today_peak_time'][-5:]}" if forecast.get('today_peak_time') else ""}

{recap_block}{accuracy_block}{low_block}{lookahead_block}Reference scale (Sandy Hook obs MLLW; {CURRENT_MODEL_VERSION} thresholds = landmark + 2.82):
  < 6.34  : no flooding (nothing visible)
  6.34    : water emerges from SW grate across Bay (lowest grate)
  6.42    : SE grate across Bay emerges
  6.46    : SE/SW pavement corners wet; Bay Ave upstream grate emerges
  6.60    : water at gutter / curb edge at walkway — don't park there
  6.62    : NE (user's corner) + NW grates emerge (Pathway B)
  6.98    : water at curb top — flood onset at property
  7.15    : water on sidewalk under the walkway lawn step
  7.18    : Bay Ave road middle covered
  7.36    : intersection high point submerged
  7.48    : water at lawn / walkway step
  7.50    : water at bottom of porch steps
  8.23    : water over the first porch step
  10.90   : water at the porch deck (Sandy-class)

Regime glossary (subject-line label, based on water depth at the curb):
  no flooding  : {REGIME_GLOSSARY['dry']}
  street       : {REGIME_GLOSSARY['street']}
  light        : {REGIME_GLOSSARY['light']}
  moderate     : {REGIME_GLOSSARY['moderate']}
  severe       : {REGIME_GLOSSARY['severe']}
  cold lockout : {REGIME_GLOSSARY['cold_lockout']}

Model: {CURRENT_MODEL_VERSION} (pluvial: dynamic tank hydrograph; scenarios = tank steady-state / tanh bracket). Local enhancement {LOCAL_ENHANCEMENT_FT:+.2f} ft (4-event calibration, conservative).
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
            f'<td>{regime_display(td["regime"])}</td>'
            f'</tr>'
        )

    summary_html = _render_summary_html(forecast)
    rain_html = _render_rain_timing_html(forecast)
    recap_html = _render_recent_history_html(forecast)
    low_html = _render_low_tides_html(forecast)
    accuracy_html = _render_accuracy_html(forecast)
    lookahead_html = _render_lookahead_html(forecast)

    # Email parity with the site (2026-07-17): TODAY — OUTLOOK (+ so-far
    # line when water already happened) then WORST 72H, before the
    # summary/confidence blocks — same order as the home page.
    _tr = forecast.get("today_regime") or regime
    _today_head, _today_cls = headline_for(forecast, _tr)
    _tbg = {"dry": "#e8f5e9", "street": "#e3f2fd", "light": "#fff8e1",
            "moderate": "#ffe0b2", "severe": "#ffcdd2",
            "cold_lockout": "#eceff1"}.get(_today_cls, "#fff8e1")
    _lb = forecast.get("today_lookback")
    _lb_html = ""
    if _lb and (_lb.get("rel_grate_in") or 0) > 0:
        _lb_html = (
            f'<div style="border-top:1px solid rgba(0,0,0,0.15);'
            f'margin-top:6px;padding-top:6px;font-size:14px">'
            f'<b>SO FAR TODAY:</b> '
            f'{regime_display(_lb.get("regime") or "").upper()} — peak '
            f'water {_lb["rel_grate_in"]:+.1f}&Prime; vs SW grate at '
            f'{_lb["time_local"]}, {_lb["source"]}.</div>')
    _today_sub = (f'Tide peak today {forecast.get("today_rel_grate_sw_in", 0) or 0:+.1f}&Prime; '
                  f'vs SW grate'
                  + (f' at {forecast["today_peak_time"][-5:]}'
                     if forecast.get("today_peak_time") else ""))
    today_block_html = (
        f'<div style="background:{_tbg};padding:14px 18px;border-radius:8px;'
        f'margin:12px 0;border:1px solid rgba(0,0,0,0.08)">'
        f'<div style="font-size:11px;color:#777;letter-spacing:1px">TODAY — OUTLOOK</div>'
        f'<div style="font-size:26px;font-weight:bold">{_today_head}</div>'
        f'<div style="font-size:14px">{_today_sub}</div>{_lb_html}</div>'
        f'<div style="background:#f4f6f8;padding:8px 18px;border-radius:8px;'
        f'margin:-4px 0 14px 0;border:1px solid rgba(0,0,0,0.08)">'
        f'<div style="font-size:11px;color:#777;letter-spacing:1px">WORST 72 H</div>'
        f'<div style="font-size:14px"><b>{headline_for(forecast, regime)[0]}</b> — '
        f'worst-case tide peak {peak_ft:.2f} ft MLLW at '
        f'{format_time_full(peak_t)}.</div></div>')

    html = f"""\
<html><body style="font-family:sans-serif;background:{bg};padding:20px">
<h2>Bay Ave Flood Forecast</h2>
<p><b>{dt.date.today().isoformat()}</b></p>

{today_block_html}
{summary_html}
<h3>High tides in next 24h</h3>
<table border="1" cellpadding="8" style="border-collapse:collapse;background:white">
<tr><th>Time</th><th>Pred (ft)</th><th>Surge</th><th>Peak (ft)</th><th>Highest landmark</th><th>Above</th><th>Rel</th><th>Regime</th></tr>
{tide_rows_html}
</table>
<p style="font-size:small;color:#666">Highlighted row = worst-case tide, headlined below.
<b>Above</b> = inches above the highest exceeded landmark (negative when water is below the lowest landmark).
<b>Rel</b> = inches above the lowest landmark (SW grate across Bay, 3.52 NAVD88).</p>

<p><b>Worst case:</b> {format_time_full(peak_t)}<br>
<b>Forecast peak (obs):</b> {peak_ft:.2f} ft MLLW Sandy Hook
({forecast['peak_predicted_mllw']:.2f} predicted {forecast['current_surge_ft']:+.2f} surge)<br>
<b>Surge source:</b> {forecast['surge_source']} ({forecast['nws_status']})<br>
<b>Rainfall in window:</b> {forecast['peak_rain_rate_in_hr']:.2f} in/hr peak<br>
<b>72h mean temp:</b> {forecast['temp_avg_72h_f']:.1f}&deg;F
{'(cold conditions met — ice-lock hypothesis no longer applied; see retrospective)' if forecast['cold_lockout'] else ''}</p>

{rain_html}
{_landmarks_section_html(forecast, wrapper='inline')}

<p><b>Regime: {regime_display(regime)}</b> &mdash; <span style="color:#666;font-size:13px">{REGIME_GLOSSARY.get(regime, '')}</span></p>

<h3>Regime glossary</h3>
<table border="1" cellpadding="6" style="border-collapse:collapse;background:white;font-size:13px">
<tr><td><b>no flooding</b></td><td>{REGIME_GLOSSARY['dry']}</td></tr>
<tr><td><b>street</b></td><td>{REGIME_GLOSSARY['street']}</td></tr>
<tr><td><b>light</b></td><td>{REGIME_GLOSSARY['light']}</td></tr>
<tr><td><b>moderate</b></td><td>{REGIME_GLOSSARY['moderate']}</td></tr>
<tr><td><b>severe</b></td><td>{REGIME_GLOSSARY['severe']}</td></tr>
<tr><td><b>cold lockout</b></td><td>{REGIME_GLOSSARY['cold_lockout']}</td></tr>
</table>

{recap_html}
{accuracy_html}
{low_html}
{lookahead_html}
<p style="font-size:small;color:#666">
Model {CURRENT_MODEL_VERSION} (pluvial: dynamic tank hydrograph on the chart; scenario brackets = tank steady-state / tanh).
Local enhancement {LOCAL_ENHANCEMENT_FT:+.2f} ft (conservative, 4-event calibration).
Surge persistence is a rough proxy; for active coastal storms, check NWS
Coastal Flood Statement directly.
</p>
</body></html>"""
    return subject, text, html


def _past_tides_with_predictions(days=7):
    """Per-tide history for the oscillation chart (2026-07-07, user
    design): every past high tide recorded in predictions_log.csv
    within `days`, with (a) its observed peak (NOAA fetch, disk-cached
    in observed_peaks_cache.csv — same cache the lead-time accuracy
    section uses) and (b) the prediction made ~24 h ahead — the lead
    time the daily email promises, so the square↔circle gap on the
    chart is the product's own error at its own job. Nearest logged
    run within [16, 36] h lead counts (the hourly bot is throttled to
    ~62% coverage, so exact-24h rows don't always exist); None when no
    qualifying run.

    Empty list when the log is missing/unusable — caller falls back to
    the old daily-peak series."""
    if not os.path.exists(PREDICTIONS_LOG_PATH):
        return []
    try:
        now_local = _station_local_now()
    except Exception:
        now_local = dt.datetime.now()
    cutoff_min = now_local - dt.timedelta(days=days)
    cutoff_max = now_local - dt.timedelta(hours=2)   # tide has ended
    by_target = {}
    try:
        with open(PREDICTIONS_LOG_PATH) as f:
            for r in csv.DictReader(f):
                t = r.get("target_tide_time") or ""
                try:
                    target = dt.datetime.strptime(t, "%Y-%m-%d %H:%M")
                    pred = float(r["sh_peak_mllw_predicted"])
                    lead = float(r["hours_until_peak"])
                except (ValueError, TypeError, KeyError):
                    continue
                if not (cutoff_min <= target <= cutoff_max):
                    continue
                by_target.setdefault(t, []).append((lead, pred))
    except OSError:
        return []
    cache = _load_observed_peaks_cache()
    dirty = False
    out = []
    for t in sorted(by_target):
        obs = cache.get(t)
        if obs is None:
            obs, _ = _fetch_actual_peak_around(t)
            if obs is not None:
                cache[t] = obs
                dirty = True
        if obs is None:
            continue
        cand = [(abs(lead - 24.0), pred)
                for lead, pred in by_target[t] if 16.0 <= lead <= 36.0]
        out.append({
            "time": t,
            "observed": obs,
            "predicted_24h": (min(cand)[1] if cand else None),
        })
    if dirty:
        _save_observed_peaks_cache(cache)
    return out


def _oscillation_chart_data(forecast):
    """Build data points for the home-page oscillation chart (HANDOFF 9b.4(b)).

    Axis: y is Sandy Hook peak (ft MLLW) — a pure observation, not
    model-derived. v0.8 enhancement = 0.00, so landmark threshold
    (MLLW) = landmark_NAVD88 + 2.82 - 0.00 = landmark_NAVD88 + 2.82.
    The chart shows SH peaks observed at the gauge plus the SH-MLLW
    threshold lines at which v0.7 predicts water reaches each
    landmark.

    Returns dict with:
      'points': list of {time, sh_peak_mllw, kind} where kind is
                'observed' (past tide peak from recent history) or
                'predicted' (upcoming tide peak from current forecast).
      'landmarks': list of {label, mllw_threshold, navd88} for the
                   horizontal threshold lines.
    """
    points = []

    # Past: PER-TIDE observed peaks (both daily highs — so the observed
    # squares show the same day/night inequality the predicted circles
    # do), each paired with the ~24h-ahead prediction where the hourly
    # log has one. Falls back to the old one-peak-per-day series if the
    # predictions log is unavailable.
    per_tide = _past_tides_with_predictions(days=7)
    if per_tide:
        for r in per_tide:
            points.append({
                "time": r["time"],
                "sh_peak_mllw": r["observed"],
                "kind": "observed",
                "predicted_24h_mllw": r["predicted_24h"],
            })
    else:
        for r in (forecast.get("recent_history_7d") or []):
            peak = r.get("peak_mllw")
            time_str = r.get("peak_time")
            if peak is None or not time_str:
                continue
            try:
                peak_f = float(peak)
            except (TypeError, ValueError):
                continue
            points.append({
                "time": time_str,
                "sh_peak_mllw": peak_f,
                "kind": "observed",
            })

    # Future: predicted peaks for upcoming high tides in this forecast.
    # When pluvial risk is live, tides inside the ~24h QPF horizon also
    # carry a rain-burst COMPOUND potential (2026-07-08, user): the
    # dual-model max of estimate_pluvial_water at that tide's bay
    # level, expressed in SH-MLLW-EQUIVALENT units (local water +2.82
    # — the gauge itself never reads rain floods; the marker says what
    # the STREET could see, on this chart's axis).
    pr = forecast.get("pluvial_risk") or {}
    burst = (pr.get("burst_est_in_hr") or 0) if pr.get("level") else 0
    try:
        now_local = _station_local_now()
    except Exception:
        now_local = dt.datetime.now()
    qpf_horizon = now_local + dt.timedelta(hours=24)
    for t in (forecast.get("all_tides") or []):
        peak = t.get("forecast_peak_mllw")
        time_str = t.get("time")
        if peak is None or not time_str:
            continue
        try:
            peak_f = float(peak)
        except (TypeError, ValueError):
            continue
        point = {
            "time": time_str,
            "sh_peak_mllw": peak_f,
            "kind": "predicted",
        }
        if burst > 0.1:
            try:
                tide_dt = dt.datetime.strptime(time_str, "%Y-%m-%d %H:%M")
            except (ValueError, TypeError):
                tide_dt = None
            if tide_dt is not None and tide_dt <= qpf_horizon:
                bay = peak_f + MLLW_TO_NAVD88_OFFSET
                pot = max(estimate_pluvial_water_models(burst, bay))
                point["burst_potential_mllw"] = round(
                    pot - MLLW_TO_NAVD88_OFFSET, 3)
        points.append(point)

    # Landmark threshold lines — curated subset, expressed as the SH
    # MLLW value at which v0.7 would predict water reaches that
    # landmark. Per user 2026-05-19 selection: see OSCILLATION_LANDMARK_KEYS.
    keep_keys = OSCILLATION_LANDMARK_KEYS
    landmark_lines = []
    for key, label, elev, sh in LANDMARKS:
        if key in keep_keys:
            landmark_lines.append({
                "key":            key,           # palette + short-label lookup in JS
                "label":          label,
                "mllw_threshold": float(sh),     # the threshold drawn on the chart
                "navd88":         float(elev),   # for tooltip context
            })

    return {"points": points, "landmarks": landmark_lines}


# v0.9-alpha pluvial depth model (2026-07-06, same-day as the flash
# flood that motivated it). Two regimes split on whether the bay has
# reached the street bowl (drains functional vs. backflowed):
#
#   base = max(bay_water_navd88, PLUVIAL_STREET_BASE)
#   drains functional (bay < street): lift = 1.40 * tanh(rate / 1.2)
#   drains blocked   (bay >= street): lift = 8 * tanh(rate) / 12
#                                     (the v0.8 compound term, unchanged)
#
# Calibration (2 events):
#   7/6/2026 pure pluvial: bay ~2.6, obs peak 4.77 (7.3" curb).
#     Fits at a convective burst of ~1.7 in/hr. VALIDATED same-day
#     against observed regional data: NWS flash-flood warning had
#     1.5-2.5" fallen by 11:02 AM at the Bayshore (Sandy Hook named),
#     radar-estimated rates up to 3 in/hr over the Monmouth corridor,
#     "2 in/hr possible" per NWS media briefings. 1.7 sits mid-band;
#     the exact rate over THIS catchment still awaits MRMS gridded
#     data, but the anchor is no longer a bare invention.
#   Oct 30 2025 compound: bay 4.81 (SH 7.63), rate 1.45 in/hr,
#     obs peak >= 5.25. Model: 5.41 (~2" conservative).
#
# Why the free-drain lift (1.25 ft at burst) EXCEEDS the blocked-drain
# lift (0.60 ft max): geometry, not drainage paradox. Pure-pluvial
# lift is measured from the narrow street bowl bottom where converging
# watershed runoff concentrates; compound lift is measured from an
# already-elevated bay level spread across the whole flooded plain.
# Same volume, different container width. A proper stage-storage curve
# unifies these in v0.9; this closed form is the alpha.
PLUVIAL_STREET_BASE = 3.52       # grate_SW — the low point the model keys on
PLUVIAL_FREE_LIFT_FT = 1.40      # saturation lift, drains functional
PLUVIAL_FREE_RATE_SCALE = 1.2    # in/hr
# Minimum smeared QPF rate for the SERIES rain layer to activate.
# User ground truth (2026-07-06 evening): "When it is lightly raining,
# the drains work fine" — light steady rain is wet pavement anywhere,
# not street water; the old 0.1 in/hr gate painted a false street-water
# tabletop through every drizzly evening. 0.25 in/hr keeps the layer
# for sustained-heavy rain (tropical/stalled systems); convective
# bursts are carried by the rain-potential level, not this line.
PLUVIAL_SERIES_RATE_MIN = 0.25


# ---- v0.9-beta pluvial: volume-based, stage-storage unified ----
# (2026-07-07, user theory → same-day implementation.) The two-regime
# closed form is REPLACED by one continuous model: a burst delivers a
# saturating net VOLUME, and depth follows by filling the measured
# stage-storage curve (history/data/stage_storage_curve.csv — wet
# area vs stage from the 96-point heat-map elevation surface) from
# the event's base level. This removes the regime discontinuity at
# bay = 3.52 and makes compound flooding correctly SUB-LINEAR: the
# same rain adds fewer inches from a higher base because the area is
# larger there.
#
# Calibration: V_K set so a 1.7 in/hr burst from an empty bowl fills
# to +15.4″ (the 7/6 anchor). Zero further parameters. Cross-check
# on Oct 30 2025 (base = bay 4.81, rate 1.45): predicts peak
# ≈ 5.22–5.24 NAVD88 vs observed ≥ 5.25–5.27 — within ~0.5″
# (the old two-regime form was +2″ over). One-model consistency of
# the two events' fill volumes: within 11% before known biases.
#
# Above the curve's top (+24″, where the surveyed region saturates)
# the fill extrapolates with the last marginal area — conservative
# (real area keeps growing, so real rise is slower than modeled).
#
# TWO-SOURCE PRINCIPLE (user, 2026-07-07): the bay is an effectively
# INFINITE reservoir — tidal flooding is LEVEL-driven and never uses
# this curve (the tide-keyed path stays pure level arithmetic). Rain
# is a FINITE source — only the rain contribution is volume-filled
# through the curve, starting from the level the tide has set.
#
# Known low-volume caveat: the model assumes one connected pool; at
# tiny net volumes reality is disconnected puddles (pocket + grate
# depressions fill first), so small-rate outputs overstate "street
# water." Bounded by the drainage floor; scenarios stay ±3″-class.
# Drain absorption rate: a JUDGMENT NUMBER, not measured (user
# 2026-07-07: "somewhat guided by evidence and somewhat arbitrarily
# — let's not put too much weight on it, nor on the assumption that
# we can simply subtract it"; V_K calibration partially absorbs the
# error). Bracketing evidence is weak: 0.09-smeared QPF didn't pool,
# 0.44 in/hr with blocked drains flooded.
PLUVIAL_DRAIN_RATE = 0.25        # in/hr, full drain capacity (judgment)
# HEAD-DEPENDENT DRAINAGE (2026-07-07): drain capacity is not
# constant — it collapses as the bay submerges the outfall. Constant
# subtraction double-counted drainage on Oct 30 (drains were blocked,
# yet we subtracted 0.25 from its rate). Provisional form: full
# capacity with the bay below 3.0 NAVD88, ramping linearly to ZERO
# at 3.52 (grate tops = outfall backwatered). The 3.0 knee is itself
# a placeholder — the drainage map / more events will refine it.
PLUVIAL_DRAIN_FULL_BELOW = 3.0   # bay level below which drains are full-capacity
# NOTE: the 1.2 in/hr tanh scale is a PLACEHOLDER (set by assumption
# at v0.9-alpha, never independently identified — needs testing as
# rain events accumulate).
#
# ---- v0.9-gamma DUAL INPUT MODELS (2026-07-07, user directive:
# "keep the tanh model and add the power-law runoff model; report
# both") ----
# Two rate→volume forms share everything else (head-dependent
# drainage, stage-storage fill):
#   POWER (primary):  V = K_pow · net_rate^GAMMA
#     Fitted to all THREE anchors (7/6, Oct 30, Dec 19) in the
#     model's own input space (logged/effective peak-hourly rates).
#     GAMMA comes out ≈ 0.9 — near-linear, NO saturation. Grounded
#     in the MRMS C·(R−D)·T analysis (delivery efficiency does not
#     collapse at high rates; if anything it grows).
#   TANH (co-reported): V = V_K · tanh(net_rate / 1.2)
#     The v0.9-beta form — saturates above ~2 in/hr. Kept as the
#     "saturating alternative", NOT as a fallback: the two agree
#     within ~1″ across the calibrated range (0.4–1.7 in/hr) and
#     DIVERGE in extrapolation (3+ in/hr, Sandy-class compound) —
#     exactly where we have no data. Reporting both brackets the
#     genuine model uncertainty; the next violent event arbitrates.
# Provenance: GAMMA/K_pow provisional (n=3, one dof); refit per
# event like V_K. The v0.9-alpha closed form remains the true
# fallback (only if the curve CSV is missing).
PLUVIAL_VOLUME_K = None          # tanh scale, lazily calibrated
PLUVIAL_POW_K = None             # power-law scale, lazily calibrated
PLUVIAL_POW_GAMMA = None         # power-law exponent, lazily fitted
_STAGE_CURVE = None              # [(stage_in, area_cells), ...]

# The three calibration anchors, in the model's input space:
# (net rate in/hr after drainage, fill stages: base_in -> peak_in).
# 7/6/2026: input 1.7, bay 2.6 -> drain 0.25 -> net 1.45; 0 -> +15.4
# Oct 30 25: input 1.45, bay 4.81 -> drain 0 -> net 1.45; +15.5 -> +20.9
# Dec 19 25: input 0.44, bay 4.04 -> drain 0 -> net 0.44; +6.2 -> +11.2
_PLUVIAL_ANCHORS = [
    (1.45, 0.0, 15.4),
    (1.45, 15.48, 20.88),
    (0.44, 6.24, 11.16),
]


def _curve_fill_volume(curve, s0, s1):
    """Storage volume (cell-inches) between stages s0 and s1."""
    v = 0.0
    for i in range(1, len(curve)):
        lo, hi = curve[i-1][0], curve[i][0]
        if hi <= s0 or lo >= s1:
            continue
        v += curve[i][1] * (min(hi, s1) - max(lo, s0))
    return v


def _load_stage_curve():
    global _STAGE_CURVE, PLUVIAL_VOLUME_K, PLUVIAL_POW_K, PLUVIAL_POW_GAMMA
    if _STAGE_CURVE is not None:
        return _STAGE_CURVE
    path = os.path.join(_REPO_ROOT, "history", "data",
                        "stage_storage_curve.csv")
    curve = []
    try:
        with open(path) as f:
            for r in csv.DictReader(f):
                curve.append((float(r["stage_in_vs_sw_grate"]),
                              float(r["wet_area_cells"])))
    except Exception:
        curve = []
    _STAGE_CURVE = curve
    if curve:
        v76 = _curve_fill_volume(curve, *_PLUVIAL_ANCHORS[0][1:])
        voct = _curve_fill_volume(curve, *_PLUVIAL_ANCHORS[1][1:])
        vdec = _curve_fill_volume(curve, *_PLUVIAL_ANCHORS[2][1:])
        # tanh: V_K pinned by the 7/6 anchor alone (v0.9-beta)
        PLUVIAL_VOLUME_K = v76 / math.tanh(
            _PLUVIAL_ANCHORS[0][0] / PLUVIAL_FREE_RATE_SCALE)
        # power law: two high-rate anchors share net 1.45 (averaged);
        # Dec 19 at 0.44 sets the exponent through the ratio
        v_hi = (v76 + voct) / 2.0
        PLUVIAL_POW_GAMMA = (math.log(v_hi / vdec)
                             / math.log(1.45 / 0.44))
        PLUVIAL_POW_K = v_hi / (1.45 ** PLUVIAL_POW_GAMMA)
    return curve


def _pluvial_fill(curve, base_stage, budget):
    """Fill the stage curve upward from base_stage with a volume
    budget; returns final stage (inches vs SW grate)."""
    stage = base_stage
    for i in range(1, len(curve)):
        s, a = curve[i]
        if s <= base_stage:
            continue
        step_v = a * (s - curve[i-1][0])
        if budget < step_v:
            stage = curve[i-1][0] + (budget / a) if a > 0 else s
            budget = 0
            break
        budget -= step_v
        stage = s
    if budget > 0:
        # Past the curve top: extrapolate with the last marginal area
        last_area = curve[-1][1]
        if last_area > 0:
            stage += budget / last_area
    return stage


def estimate_pluvial_water(rain_rate_in_hr, bay_water_navd88,
                           model="tank"):
    """v0.9-gamma: water at 342 Bay (NAVD88) for a rain rate and
    concurrent bay level, via volume-fill of the stage-storage curve.
    model="power" (primary, near-linear fit to all three anchors) or
    "tanh" (v0.9-beta saturating form, co-reported). Falls back to
    the v0.9-alpha two-regime closed form when the curve file is
    unavailable."""
    base = max(bay_water_navd88, PLUVIAL_STREET_BASE)
    # Head-dependent drainage: capacity declines as the bay submerges
    # the outfall (full below 3.0 NAVD88 -> zero at grate tops 3.52).
    span = PLUVIAL_STREET_BASE - PLUVIAL_DRAIN_FULL_BELOW
    frac_open = min(1.0, max(0.0,
        (PLUVIAL_STREET_BASE - bay_water_navd88) / span))
    drain = PLUVIAL_DRAIN_RATE * frac_open
    net_rate = rain_rate_in_hr - drain
    if net_rate <= 0:
        return base
    curve = _load_stage_curve()
    if not curve or not PLUVIAL_VOLUME_K:
        # v0.9-alpha fallback
        if bay_water_navd88 >= PLUVIAL_STREET_BASE:
            lift = RAIN_SATURATION_IN * math.tanh(rain_rate_in_hr) / 12.0
        else:
            lift = PLUVIAL_FREE_LIFT_FT * math.tanh(
                rain_rate_in_hr / PLUVIAL_FREE_RATE_SCALE)
        return base + lift
    base_stage = max(0.0, (base - PLUVIAL_STREET_BASE) * 12)
    if model == "tanh":
        budget = PLUVIAL_VOLUME_K * math.tanh(
            net_rate / PLUVIAL_FREE_RATE_SCALE)
    elif model == "power":
        # v0.9-gamma legacy (γ=0.914, implicit ~1h duration)
        budget = PLUVIAL_POW_K * (net_rate ** PLUVIAL_POW_GAMMA)
    else:
        # v0.10 TANK STEADY STATE (default, 2026-07-09): dV/dt = 0 →
        # V = (K/k_out)·net^γ — the level a SUSTAINED rate holds
        # (reached within ~1 h; drains back out in ~20 min once rain
        # stops). Same calibration as the series hydrograph, so the
        # static scenarios and the dynamic line are ONE model family.
        budget = (TANK_K / TANK_KOUT) * (net_rate ** TANK_GAMMA)
    stage = _pluvial_fill(curve, base_stage, budget)
    return PLUVIAL_STREET_BASE + stage / 12.0


# ---- v0.10 DYNAMIC TANK MODEL (2026-07-09, fitted the night of
# event #4 while the recession data was fresh) ----
#   dV/dt = TANK_K · max(0, R(t − lag) − D(bay))^TANK_GAMMA − TANK_KOUT · V
#   stage = stage_curve(fill from tide-set base + V)
# ONE global parameter set fits BOTH measured hydrographs (7/6 and
# 7/9, RMS 1.3″ over 24 tape points, peak times within 0–8 min) and
# independently lands Oct 30 (20.7 vs ≥21) and Dec 19 (11.3 at the
# 08:12 observation vs band 10.1–12.2). Fit script:
# history/scripts/tank_model_fit.py. This model gives the series
# TIMING (rise / peak / recession) — the open item since 7/6.
# NOTE: γ=0.70 in TRUE-rate space with duration explicit; the
# earlier "C grows with intensity" finding was partly duration-
# confounded. The static v0.9-gamma estimate_pluvial_water() remains
# for banner SCENARIOS (steady-state "a burst like X could reach Y")
# and the rain-pathway calculator; the tank drives the water_series.
# v0.10.1 (2026-07-18 evening): k_out MEASURED from event #5's clean
# recession limb (rain ~0, 16:03-16:40): 3.50/h — and with jets still
# feeding, that's a floor. K/gamma/lag jointly refit against the 7/6
# + 7/9 hydrographs with k_out pinned; RMS IMPROVED 1.44 -> 1.32 in.
# The rare legitimate tuning: input-independent measurement first,
# refit second, validation better everywhere.
TANK_K = 1.296e6        # cell-inches per hour at 1 in/hr net (refit v0.10.1)
TANK_GAMMA = 0.78       # intensity exponent (refit v0.10.1)
TANK_KOUT = 3.50        # /hour — MEASURED 2026-07-18 (e-fold ~17 min)
TANK_LAG_MIN = 15       # hillside concentration lag (refit; obs 14-20)


def simulate_pluvial_series(times, tide_waters, rates, dt_min=5.0):
    """Integrate the v0.10 tank over a series window.

    times: list of naive local datetimes (ascending, ~30-min steps);
    tide_waters: NAVD88 bay water per point; rates: QPF in/hr per
    point (raw hourly bucket rates — the tank supplies its own lag
    and smoothing; do NOT pre-smooth). Returns pluvial water NAVD88
    per point (None where the tank holds no water above the base).
    """
    curve = _load_stage_curve()
    if not curve or len(times) < 2:
        return [None] * len(times)

    def rate_at(t):
        t = t - dt.timedelta(minutes=TANK_LAG_MIN)
        if t <= times[0]:
            return rates[0]
        for i in range(1, len(times)):
            if t <= times[i]:
                return rates[i - 1]   # step function per bucket
        return rates[-1]

    def bay_at(t):
        for i in range(1, len(times)):
            if t <= times[i]:
                return tide_waters[i - 1]
        return tide_waters[-1]

    out = []
    V = 0.0
    t = times[0]
    idx = 0
    step = dt.timedelta(minutes=dt_min)
    while idx < len(times):
        # integrate up to times[idx]
        while t < times[idx]:
            bay = bay_at(t)
            span = PLUVIAL_STREET_BASE - PLUVIAL_DRAIN_FULL_BELOW
            frac = min(1.0, max(0.0, (PLUVIAL_STREET_BASE - bay) / span))
            net = max(0.0, rate_at(t) - PLUVIAL_DRAIN_RATE * frac)
            dV = (TANK_K * net ** TANK_GAMMA - TANK_KOUT * V) * (dt_min / 60.0)
            V = max(0.0, V + dV)
            t = t + step
        bay = tide_waters[idx]
        base = max(bay, PLUVIAL_STREET_BASE)
        base_stage = max(0.0, (base - PLUVIAL_STREET_BASE) * 12)
        if V > 0:
            stage = _pluvial_fill(_STAGE_CURVE, base_stage,
                                  V)
            w = PLUVIAL_STREET_BASE + stage / 12.0
            out.append(w if (w - base) * 12 > 0.25 else None)
        else:
            out.append(None)
        idx += 1
    return out


def estimate_pluvial_water_models(rain_rate_in_hr, bay_water_navd88):
    """(primary, tanh) for the same sustained conditions. Primary =
    v0.10 tank steady state (2026-07-09); tanh = the labeled
    conservative alternative (refuted as a peak model by event #4 —
    it saturates below measured levels — kept as the bracket's low
    edge). v0.9-gamma power remains via model="power" (legacy)."""
    return (estimate_pluvial_water(rain_rate_in_hr, bay_water_navd88,
                                   model="tank"),
            estimate_pluvial_water(rain_rate_in_hr, bay_water_navd88,
                                   model="tanh"))


# Landmarks eligible for flood-window computation. The high porch
# features are excluded (windows there would only matter in
# Sandy-class events where this UI is not the tool you'd be using).
FLOOD_WINDOW_KEYS = [
    "grate_SW", "grate_SE", "corner_SE", "corner_SW",
    "grate_bay_ave_upstream", "gutter_walkway", "grate_NE", "grate_NW",
    "corner_NE", "corner_NW", "curb", "sidewalk_under_walkway_lawn_step",
    "road_middle", "intersection_highpoint", "lawn_step",
    "porch_step_base",
]


def compute_flood_windows(series):
    """Flood start/end/duration per landmark, derived from the water
    series (2026-07-06 — user: "not just what will happen at the very
    top of the peak"). Linear interpolation between the 30-min samples
    gives crossing times.

    Returns {landmark_key: [episode, ...]} where episode =
      {"start", "end", "duration_h", "peak_time", "peak_depth_in",
       "grazing": bool}
    `end` is None when the series ends while still flooded. `grazing`
    is True when the episode's peak clears the landmark by < 0.1 ft —
    surge error can easily erase or double those windows, so callers
    should phrase them as "may briefly touch" rather than quoting
    times. Times are station-local strings matching the series.

    Honest limitation: crossings are symmetric level-crossings of the
    predicted series. Observed drain-down lags the gauge slightly
    (falling-limb hysteresis, 6/15 data) and retention pockets hold
    water for hours after — end times are the optimistic edge.
    """
    elev_by_key = {k: e for k, _l, e, _s in LANDMARKS}
    pts = []
    for p in series or []:
        try:
            t = dt.datetime.strptime(p["time"], "%Y-%m-%d %H:%M")
            pts.append((t, float(p["water_navd88"])))
        except (KeyError, ValueError, TypeError):
            continue
    out = {}
    if len(pts) < 2:
        return out
    for key in FLOOD_WINDOW_KEYS:
        elev = elev_by_key.get(key)
        if elev is None:
            continue
        episodes = []
        cur = None   # {"start": dt, "peak": (t, depth)}
        for (t0, w0), (t1, w1) in zip(pts, pts[1:]):
            if cur is None and w0 <= elev < w1:
                # Rising crossing between t0 and t1
                frac = (elev - w0) / (w1 - w0)
                cur = {"start": t0 + (t1 - t0) * frac,
                       "peak": (t1, w1 - elev)}
            elif cur is not None:
                if w1 - elev > cur["peak"][1]:
                    cur["peak"] = (t1, w1 - elev)
                if w1 <= elev:
                    frac = (w0 - elev) / (w0 - w1) if w0 != w1 else 0
                    end = t0 + (t1 - t0) * frac
                    episodes.append((cur, end))
                    cur = None
        if cur is not None:
            episodes.append((cur, None))
        # Handle "already flooded at series start"
        if pts[0][1] > elev:
            first_end = None
            peak = (pts[0][0], pts[0][1] - elev)
            for (t0, w0), (t1, w1) in zip(pts, pts[1:]):
                if w1 - elev > peak[1]:
                    peak = (t1, w1 - elev)
                if w1 <= elev:
                    frac = (w0 - elev) / (w0 - w1) if w0 != w1 else 0
                    first_end = t0 + (t1 - t0) * frac
                    break
            lead = ({"start": pts[0][0], "peak": peak}, first_end)
            episodes.insert(0, lead)
        fmt = "%Y-%m-%d %H:%M"
        rows = []
        for cur, end in episodes:
            dur = ((end - cur["start"]).total_seconds() / 3600.0
                   if end else None)
            rows.append({
                "start": cur["start"].strftime(fmt),
                "end": end.strftime(fmt) if end else None,
                "duration_h": round(dur, 2) if dur is not None else None,
                "peak_time": cur["peak"][0].strftime(fmt),
                "peak_depth_in": round(cur["peak"][1] * 12, 1),
                "grazing": cur["peak"][1] < 0.1,
            })
        if rows:
            out[key] = rows
    return out


ALERT_STATE_PATH = os.path.join(_REPO_ROOT, "data", "alert_state.json")

# Alert ranks: 0 = nothing worth a message. Tide regimes and pluvial
# levels merge onto one ladder so "risk appeared" has one meaning.
_ALERT_RANKS = {"dry": 0, "cold_lockout": 0, "street": 1, "light": 2,
                "moderate": 3, "severe": 4}
_PLUVIAL_RANKS = {None: 0, "possible": 1, "elevated": 3}


def compute_alert_level(forecast):
    """(rank, label, signature) for the event-driven alert policy
    (user, 2026-07-17: the daily-morning email became ignorable —
    'mostly not telling me it will flood'). rank>0 = some flood risk
    exists in the 72h window or the rain pathway. signature
    identifies the risk episode so we alert on APPEARANCE and
    ESCALATION, never repeat on steady state, and reset after
    all-clear."""
    tide_rank = 0
    tide_label = "no tidal flooding"
    for t in (forecast.get("all_tides") or []):
        r = ((t.get("depths_in") or {}).get("regime")) or "dry"
        if _ALERT_RANKS.get(r, 0) > tide_rank:
            tide_rank = _ALERT_RANKS.get(r, 0)
            tide_label = f"{regime_display(r)} tide {t.get('time','')}"
    pr = forecast.get("pluvial_risk") or {}
    pl_rank = _PLUVIAL_RANKS.get(pr.get("level"), 0)
    rank = max(tide_rank, pl_rank)
    if pl_rank >= tide_rank and pl_rank > 0:
        label = f"rain risk {pr.get('level')}"
        if pr.get("nws_flood_alerts"):
            label += " (" + pr["nws_flood_alerts"][0]["event"] + ")"
    else:
        label = tide_label
    sig_bits = [str(rank)]
    if tide_rank > 0:
        worst = forecast.get("peak_time_local") or ""
        sig_bits.append("tide:" + worst)
    if pl_rank > 0:
        sig_bits.append("pluv:" + str(pr.get("level")))
        for a in pr.get("nws_flood_alerts") or []:
            sig_bits.append(a.get("event", ""))
    return rank, label, "|".join(sig_bits)


def should_send_alert(forecast):
    """(send: bool, reason) with persisted state. Send on appearance
    (0→>0) or escalation (rank above last-sent rank). Steady or
    de-escalating states update the file silently; all-clear resets
    so the NEXT episode alerts again."""
    rank, label, sig = compute_alert_level(forecast)
    try:
        with open(ALERT_STATE_PATH) as f:
            st = json.load(f)
    except (OSError, ValueError):
        st = {"rank": 0, "sig": ""}
    prev_rank = st.get("rank", 0)
    send = rank > 0 and (prev_rank == 0 or rank > prev_rank)
    reason = (f"alert rank {prev_rank}→{rank} ({label})" if send else
              f"steady (rank {rank}, was {prev_rank})")
    # 24-HOUR COOLDOWN (user policy 2026-07-18: "no more than 1 per
    # 24 h if the headline doesn't change"): a transient dip to rank
    # 0 (NWS hiccup, alert boundary) must not re-fire the same alert
    # on the next run. Suppress re-sends at or below the last-SENT
    # rank within 24 h; a strictly HIGHER rank (real escalation)
    # always sends immediately.
    now_utc = dt.datetime.now(dt.timezone.utc)
    if send:
        ls_rank = st.get("last_sent_rank", 0)
        ls_ts = None
        try:
            ls_ts = dt.datetime.strptime(
                st.get("last_sent_ts", ""), "%Y-%m-%dT%H:%M:%SZ"
            ).replace(tzinfo=dt.timezone.utc)
        except (ValueError, TypeError):
            pass
        if (ls_ts is not None and rank <= ls_rank
                and (now_utc - ls_ts) < dt.timedelta(hours=24)):
            hrs = (now_utc - ls_ts).total_seconds() / 3600
            send = False
            reason = (f"suppressed: rank {rank} already alerted "
                      f"{hrs:.1f}h ago (24h cooldown; a higher rank "
                      f"would send immediately)")
    new_state = {"rank": rank, "sig": sig, "label": label,
                 "updated": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
                 "last_sent_rank": st.get("last_sent_rank", 0),
                 "last_sent_ts": st.get("last_sent_ts", "")}
    if send:
        new_state["last_sent_rank"] = rank
        new_state["last_sent_ts"] = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        with open(ALERT_STATE_PATH + ".tmp", "w") as f:
            json.dump(new_state, f)
        os.replace(ALERT_STATE_PATH + ".tmp", ALERT_STATE_PATH)
    except OSError:
        pass
    return send, reason


def build_sms_text(forecast):
    """~150-char alert for email-to-SMS gateways (ALERT_SMS_TO secret,
    e.g. 5551234567@vtext.com). Short + link, per user design."""
    rank, label, _ = compute_alert_level(forecast)
    _tr = forecast.get("today_regime") or "dry"
    head, _ = headline_for(forecast, _tr)
    peak = forecast.get("peak_forecast_observed_mllw") or 0
    return (f"[Barnacle] {head} — {label}. Worst 72h {peak:.2f}ft "
            f"{format_time_short(forecast.get('peak_time_local') or '')}. "
            f"johnurban.github.io/barnacle/?a={int(_time.time()) // 60}")


def _today_lookback():
    """What actually happened at the corner SO FAR today (user design
    2026-07-09, post-event-#4: an hour after a top-3 flood the widget
    said only 'RAIN FLOOD RISK' — true forward-looking, but reads as
    amnesia to a casual user). Sources, best wins:
      (a) today's spot-check rows in labeled_observations.csv (tape —
          the only source that sees RAIN floods), max implied water;
      (b) today's despiked gauge peak (tide floods, converted local).
    Returns {navd88, rel_grate_in, time_local, regime, source} or
    None when nothing measured/observed above the SW grate today."""
    try:
        today = _station_local_now().date().isoformat()
    except Exception:
        return None
    best = None
    # (a) tape
    try:
        elev_by_key = {k: e for k, _lbl, e, _sh in LANDMARKS}
        obs_path = os.path.join(_REPO_ROOT, "data",
                                "labeled_observations.csv")
        with open(obs_path) as f:
            for r in csv.DictReader(f):
                ts = (r.get("observation_time_local") or "")
                if not ts.startswith(today):
                    continue
                key = (r.get("landmark_key") or "").strip()
                if "pocket" in key or key not in elev_by_key:
                    continue
                try:
                    w = elev_by_key[key] + float(r["observed_depth_in"]) / 12.0
                except (TypeError, ValueError, KeyError):
                    continue
                if best is None or w > best[0]:
                    best = (w, ts[11:16], "measured (tape)")
    except OSError:
        pass
    # (b) gauge (despiked upstream)
    try:
        peak, peak_t = _fetch_actual_peak_around(
            _station_local_now().strftime("%Y-%m-%d %H:%M"),
            window_hours=12)
        if peak is not None and (peak_t or "").startswith(today):
            w = peak + MLLW_TO_NAVD88_OFFSET
            if best is None or w > best[0]:
                best = (w, (peak_t or "")[11:16], "observed (gauge)")
    except Exception:
        pass
    # (c) the nowcast's own day-max — the AUTOMATIC witness (2026-07-18,
    # user: Barnacle must look right with nobody home). Weakest source:
    # only used when tape and gauge have nothing higher.
    try:
        with open(os.path.join(_REPO_ROOT, "docs", "nowcast.json")) as f:
            nc = json.load(f)
        if (nc.get("generated_utc") or "").startswith(today):
            dmx = nc.get("day_max_street_in") or 0
            if dmx > 0:
                w_nc = GRATE_SW + dmx / 12.0
                t_nc = (nc.get("day_max_utc") or "")[11:16]
                # convert UTC HH:MM to local for display (approx -4)
                try:
                    hh = (int(t_nc[:2]) - 4) % 24
                    t_nc = f"{hh:02d}:{t_nc[3:5]}"
                except Exception:
                    pass
                if best is None or w_nc > best[0]:
                    best = (w_nc, t_nc, "modeled (live radar)")
    except (OSError, ValueError):
        pass
    if best is None or best[0] <= GRATE_SW:
        return None
    w, t, src = best
    return {
        "navd88": round(w, 3),
        "rel_grate_in": round((w - GRATE_SW) * 12, 1),
        "time_local": t,
        "regime": classify_regime_from_water(w),
        "source": src,
    }


def classify_regime_from_water(water_navd88):
    """Regime label from a water level (NAVD88) — same bands as
    predict_landmark_depths but usable on series maxima (for the
    'today' summary, which must reflect rain too, not just tide
    peaks)."""
    curb_depth = (water_navd88 - CURB_TOP) * 12
    if curb_depth >= ALERT_SEVERE:
        return "severe"
    if curb_depth >= ALERT_MODERATE:
        return "moderate"
    if curb_depth > 0:
        return "light"
    if water_navd88 > GRATE_SW:
        return "street"
    return "dry"


TOP10_FLOODS_PATH = os.path.join(_REPO_ROOT, "history", "data",
                                 "top10_floods.csv")


def _render_historical_floods_html():
    """Bottom-of-page historical context (user request 2026-07-06):
    the 10 worst floods of the last ~100 years at Sandy Hook, in both
    standard datums AND 342 Bay terms (inches above the SW grate — the
    standard mental unit — plus the highest landmark covered under the
    v0.9 transform). "This would give an idea of how bad it can get at
    342 Bay Ave."

    Data: history/data/top10_floods.csv — verified NOAA peaks
    cross-referenced against the ShorelySafe Sandy Hook dashboard's
    top-ten list and our own 1910–2026 hourly parquet (both sources
    agree on the event set). Static; regenerate only if NOAA revises
    verified peaks or the landmark ladder changes."""
    try:
        with open(TOP10_FLOODS_PATH) as f:
            events = list(csv.DictReader(f))
    except Exception:
        return ""
    if not events:
        return ""
    rows = ""
    for i, e in enumerate(events, 1):
        rows += (
            f"<tr><td>{i}</td><td>{e['date']}</td><td>{e['event']}</td>"
            f"<td>{float(e['peak_mllw_ft']):.2f}</td>"
            f"<td>{float(e['water_navd88_ft']):.2f}</td>"
            f"<td>+{float(e['rel_sw_grate_in']):.0f}&Prime;</td>"
            f"<td>{e['highest_landmark_covered']} "
            f"(+{float(e['inches_over_highest']):.0f}&Prime;)</td></tr>"
        )
    return f"""
  <section class="reference historical-floods">
    <h2>How bad can it get? The 10 worst floods of the last century</h2>
    <p class="note">Verified Sandy Hook peaks (NOAA station 8531680;
       cross-checked against the ShorelySafe dashboard's top-ten and
       our own 1910&ndash;2026 hourly record — the event lists agree).
       Local columns apply the {CURRENT_MODEL_VERSION} transform
       (water at 342 = SH &minus; 2.82 ft) and are <b>tide-only
       floors</b>: every event on this list also had rain, whose
       local boost is unrecorded — actual water at 342 was at least
       this high. <b>vs SW grate</b> is inches above the lowest grate
       (3.52 NAVD88, where water first appears); <b>highest
       landmark</b> uses the surveyed porch ladder.</p>
    <table class="tide-table">
      <thead><tr><th>#</th><th>Date</th><th>Event</th>
      <th>Peak (ft MLLW)</th><th>Tide-only floor at 342 (ft NAVD88)</th>
      <th>vs SW grate (floor)</th><th>Highest landmark covered (min)</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
    <p class="note"><b>Even at their tide-only floors, every event on
       this list puts water on the porch stairs</b> — the mildest
       reaches the top of the 1st step; Sandy put ~3&frac12; feet over
       the porch deck <i>before counting its rain</i>. For scale: the
       worst events measured since this project began — Oct 30 2025
       (~5.27 NAVD88 measured, +21&Prime; vs SW grate, past the
       porch-step base) and the 7/6/2026 flash flood (~4.8 NAVD88) —
       sit far below these floors. <b>Epistemic honesty</b>: this
       ranking is built from the tide gauge, which records no local
       water and no rain. True local rankings are unknowable from it —
       each event's rain boost is unrecorded, and pluvial-only floods
       (like 7/6/2026, when the gauge read an unremarkable ~6.0) are
       entirely invisible to it. 342 Bay has no historical flood
       record; the spot-check log this project keeps is, as far as we
       know, the first one. Other caveats: the local transform is
       calibrated on 2026 moderate events and extrapolates to
       hurricane regimes; Sandy's 14.4 is the estimated true peak
       (the gauge failed at 13.31).</p>
  </section>
"""


def _render_water_series_section(forecast):
    """Home-page water-level chart (2026-07-06) — the widget's
    tide-curve, promoted to the site. Continuous predicted water at
    342 Bay for now−2h → now+24h (tide + surge + QPF rain layer),
    with landmark reference lines and the rain-burst potential level
    when pluvial risk is active."""
    series = forecast.get("water_series") or []
    if len(series) < 4:
        return ""
    def to_in(v):
        return None if v is None else round((v - GRATE_SW) * 12, 1)
    labels = [p["time"][-5:] for p in series]
    tide = [to_in(p.get("tide_navd88")) for p in series]
    pluv = [to_in(p.get("pluvial_navd88")) for p in series]
    observed = [to_in(p.get("observed_navd88")) for p in series]
    has_observed = any(v is not None for v in observed)
    # Tier-3 tape diamonds: user measurements in the chart window
    tape_pts = []
    try:
        elev_by_key = {k: e for k, _l, e, _sh in LANDMARKS}
        t0 = series[0]["time"]
        t1 = series[-1]["time"]
        with open(os.path.join(_REPO_ROOT, "data",
                               "labeled_observations.csv")) as f:
            for r in csv.DictReader(f):
                ts = (r.get("observation_time_local") or "").replace("T", " ")[:16]
                key = (r.get("landmark_key") or "").strip()
                if not (t0 <= ts <= t1) or "pocket" in key \
                        or key not in elev_by_key:
                    continue
                try:
                    w = elev_by_key[key] + float(r["observed_depth_in"]) / 12.0
                except (TypeError, ValueError):
                    continue
                # snap to nearest series label index
                idx = min(range(len(series)),
                          key=lambda i: abs(
                              dt.datetime.strptime(series[i]["time"][:16],
                                                   "%Y-%m-%d %H:%M")
                              - dt.datetime.strptime(ts, "%Y-%m-%d %H:%M")))
                tape_pts.append((idx, to_in(w)))
    except Exception:
        tape_pts = []
    has_rain_layer = any(v is not None for v in pluv)
    pr = forecast.get("pluvial_risk") or {}
    # v0.9-gamma dual models: band top = the HIGHER of the two
    # estimates (honest upper bound); the note reports the bracket.
    _pot_pow = pr.get("potential_low_tide_navd88")
    _pot_tanh = pr.get("potential_low_tide_navd88_tanh")
    _pots = [v for v in (_pot_pow, _pot_tanh) if v is not None]
    potential = max(_pots) if _pots else None
    potential_lo = min(_pots) if _pots else None
    curb_in = round((CURB_TOP - GRATE_SW) * 12, 1)
    # Standard y-limits (user 2026-07-06): the same frame every day so
    # the eye calibrates — normal tides swing roughly −55″..+5″ and
    # measured floods have peaked ~+21″ (Oct 30). [−60, +36] holds all
    # of that; the frame expands only if data/reference lines exceed it
    # (a Sandy-class forecast should not be clipped).
    all_vals = ([v for v in tide if v is not None]
                + [v for v in pluv if v is not None]
                + [v for v in observed if v is not None]
                + [v for _i, v in tape_pts]
                + ([to_in(potential)] if potential else []))
    y_min = min(-60, (min(all_vals) - 3) if all_vals else -60)
    y_max = max(36, (max(all_vals) + 3) if all_vals else 36)
    # Two lines, two surfaces (user design 2026-07-06): bay/tide water
    # and rain street-water are plotted separately, never spliced.
    datasets = [
        {"label": "Tide + surge (bay water)", "data": tide,
         "borderColor": "#1a5fa8",
         "fill": False, "pointRadius": 0, "borderWidth": 2, "tension": 0.35},
    ]
    tide_idx = 0   # band must fill to the TIDE dataset (index shifts
                   # as overlay datasets are inserted below — the
                   # 2026-07-20 invisible-band regression was fill:0
                   # pointing at the inserted tape/observed layers)
    if has_observed:
        tide_idx += 1
        datasets.insert(0,
            {"label": "OBSERVED bay (gauge, despiked)", "data": observed,
             "borderColor": "#555555",
             "fill": False, "spanGaps": False,
             "pointRadius": 0, "borderWidth": 2.5, "tension": 0.3})
    if tape_pts:
        tape_data = [None] * len(labels)
        for idx, v in tape_pts:
            tape_data[idx] = (max(tape_data[idx], v)
                              if tape_data[idx] is not None else v)
        tide_idx += 1
        datasets.insert(0,
            {"label": "MEASURED (tape)", "data": tape_data,
             "borderColor": "#0b3d6b",
             "backgroundColor": "rgba(217,119,6,0.9)",
             "pointStyle": "rectRot", "pointRadius": 6,
             "pointBorderWidth": 2, "showLine": False})
    if has_rain_layer:
        datasets.append(
            {"label": "Rain street-water (v0.10 tank hydrograph)",
             "data": pluv, "borderColor": "#d97706",
             "fill": False, "spanGaps": False,
             "pointRadius": 0, "borderWidth": 2, "tension": 0.2})
    # Landmark reference lines — colors are the SHARED PALETTE with the
    # widget chart (user 2026-07-06: widget lines go unlabeled, learned
    # by color; the website labels them).
    gutter_in = round((GUTTER_WALKWAY - GRATE_SW) * 12, 1)   # +3.1
    lawn_in = round((LAWN_STEP - GRATE_SW) * 12, 1)          # +13.7
    porch1_in = round((PORCH_STEP1_TOP - GRATE_SW) * 12, 1)  # +22.7
    # Landmark lines live as constant DATASETS (2026-07-06 final
    # design): the legend above the plot carries each colored segment
    # + label, so no white label boxes ever sit on the data.
    def _landmark_ds(y, color, text, solid=False):
        return {"label": text, "data": [y] * len(labels),
                "borderColor": color, "borderWidth": 1.5 if solid else 1.2,
                "borderDash": [] if solid else [6, 5],
                "fill": False, "pointRadius": 0}
    landmark_datasets = [
        _landmark_ds(0, "#222222", "SW grate 0″ (ground)", solid=True),
        _landmark_ds(gutter_in, "#2f8f5f", f"gutter +{gutter_in}″ (move the car)"),
        _landmark_ds(curb_in, "#c0392b", f"curb +{curb_in}″ (flood onset)"),
        _landmark_ds(lawn_in, "#7c4dbc", f"lawn step +{lawn_in}″"),
        _landmark_ds(porch1_in, "#6d4c2f", f"1st porch step top +{porch1_in}″"),
    ]
    annotations = {}
    # Day-boundary line at midnight
    for idx, lab in enumerate(labels):
        if lab == "00:00":
            try:
                _md = dt.datetime.strptime(series[idx]["time"][:10],
                                           "%Y-%m-%d").strftime("%a")
            except Exception:
                _md = "12 AM"
            annotations[f"midnight{idx}"] = {
                "type": "line", "xMin": idx, "xMax": idx,
                "borderColor": "#999999", "borderWidth": 1,
                "borderDash": [2, 3],
                "label": {"display": True, "content": _md,
                          "position": "start", "font": {"size": 9},
                          "backgroundColor": "rgba(255,255,255,0.7)",
                          "color": "#777777"}}
    if potential:
        pot_in = to_in(potential)
        # Possibility ZONE as a DATASET (not an annotation): the chart
        # legend then shows a colored square with the label at top —
        # no more label collisions on the crowded left edge. Water-navy
        # fill (user: amber read poorly; blue = water).
        flags = [bool(p.get("burst_risk")) for p in series]
        if not any(flags):
            flags = [True] * len(labels)   # risk fired but no hour
                                           # qualified — show full width
        # Band: bottom = the tide curve, top = the FLAT absolute burst
        # potential level (user correction 2026-07-06: the burst can
        # bring street water to ~the same absolute level at any point
        # in the storm window — thickness IS the rain's headroom,
        # biggest at low tide). Where the tide already exceeds the
        # potential, thickness clamps to zero.
        zone_data = [round(max(pot_in, tide[i]), 1) if flags[i] else None
                     for i in range(len(labels))]
        datasets.append({
            "label": f"rain-burst potential (up to +{pot_in}″, storm-capable hours)",
            "data": zone_data,
            "fill": tide_idx,
            "backgroundColor": "rgba(11, 61, 107, 0.30)",
            "borderColor": "rgba(11, 61, 107, 0.9)",
            "pointRadius": 0, "borderWidth": 1.5, "spanGaps": False,
        })
    datasets.extend(landmark_datasets)
    cfg = {
        "type": "line",
        "data": {"labels": labels, "datasets": datasets},
        "options": {
            "responsive": True,
            "maintainAspectRatio": False,
            "plugins": {
                "legend": {"display": True,
                           "labels": {"boxWidth": 22, "boxHeight": 2,
                                      "font": {"size": 10}}},
                "annotation": {"annotations": annotations},
            },
            "scales": {
                "y": {"title": {"display": True,
                                "text": "inches vs SW grate (± = above/below)"},
                      "min": y_min, "max": y_max},
                "x": {"ticks": {"maxTicksLimit": 9, "font": {"size": 10}}},
            },
        },
    }
    note_bits = [
        "Y-axis is inches relative to the SW grate — the reference "
        "point for all relative depths. Convert: ft NAVD88 = 3.52 + "
        "inches/12; ft MLLW (Sandy Hook gauge) = 6.34 + inches/12."]
    if has_observed:
        note_bits.append(
            "The chart reaches 6 h into the PAST: the gray line "
            "is the OBSERVED bay (despiked gauge — a true observation, "
            "and via the drains' proven bay-coupling, the tide-pathway "
            "street water); it stops at the now-line where forecast "
            "takes over. Orange diamonds are tape measurements. The "
            "blue/amber model lines across the past show the CURRENT "
            "model's view, not what was predicted at the time — past "
            "rain floods can exceed them (that gap is the point).")
    if has_rain_layer:
        note_bits.append(
            "The amber curve is the v0.10 tank hydrograph — predicted "
            "rain street-water with real timing (rise, peak, ~20-min "
            "drain-down), integrated from hourly QPF. A different "
            "surface than the blue bay/tide water; light rain drains "
            "fine and draws no line.")
    if potential:
        band_note = (
            "The navy band spans from the tide curve up to the "
            "rain-burst potential level (7/6-analog scaling) across "
            "the hours when burst-capable weather is in the forecast "
            "— a burst could fill street water to roughly that level "
            "at any point in the band; its thickness is the rain's "
            "headroom over the tide. Bursts have estimable magnitude "
            "but no exact clock time.")
        if (potential_lo is not None
                and (potential - potential_lo) >= 0.04):
            band_note += (
                f" The band top is the higher of the two pluvial "
                f"models — power-law +{to_in(_pot_pow)}″ / saturating "
                f"tanh +{to_in(_pot_tanh)}″ vs SW grate; they agree "
                f"in the calibrated range and diverge for violent "
                f"bursts.")
        note_bits.append(band_note)
    note_bits.append("Windows below are derived from these curves.")
    return f"""
  <section class="water-series">
    <h2>Predicted near-term water levels</h2>
    <div style="position:relative;height:340px;margin:8px auto">
      <canvas id="water-series-chart"></canvas>
    </div>
    <p class="note">{' '.join(note_bits)}</p>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@3.0.1/dist/chartjs-plugin-annotation.min.js"></script>
    <script>
      (function() {{
        var cfg = {json.dumps(cfg)};
        var seriesTimes = {json.dumps([p["time"] for p in series])};
        var tideVals = {json.dumps(tide)};
        // "Now" marker computed at VIEW time (page regenerates hourly,
        // but a viewer may load it mid-cycle): vertical line + filled
        // dot on the tide curve, mirroring the widget.
        var now = new Date();
        var best = -1, bestD = Infinity;
        for (var i = 0; i < seriesTimes.length; i++) {{
          var m = seriesTimes[i].match(/(\\d+)-(\\d+)-(\\d+) (\\d+):(\\d+)/);
          if (!m) continue;
          var t = new Date(+m[1], m[2]-1, +m[3], +m[4], +m[5]);
          var d = Math.abs(t - now);
          if (d < bestD) {{ bestD = d; best = i; }}
        }}
        if (best >= 0 && bestD < 45*60*1000 && tideVals[best] != null) {{
          cfg.options.plugins.annotation.annotations.nowLine = {{
            type: 'line', xMin: best, xMax: best,
            borderColor: '#555555', borderWidth: 1
          }};
          cfg.options.plugins.annotation.annotations.nowDot = {{
            type: 'point', xValue: best, yValue: tideVals[best],
            radius: 5, backgroundColor: '#1a5fa8',
            borderColor: '#ffffff', borderWidth: 2
          }};
        }}
        new Chart(document.getElementById('water-series-chart'), cfg);
      }})();
    </script>
  </section>
"""


def _render_flood_windows_html(forecast):
    """Flood start/end/duration table (2026-07-06 — "not just what
    will happen at the very top of the peak"). Only landmarks with
    episodes in the series window appear; grazing episodes render as
    "may briefly touch"."""
    fw = forecast.get("flood_windows") or {}
    if not fw:
        return ""
    label_by_key = {k: l for k, l, _e, _s in LANDMARKS}
    elev_by_key = {k: e for k, _l, e, _s in LANDMARKS}
    rows = ""
    for key in FLOOD_WINDOW_KEYS:      # ascending elevation order
        for ep in fw.get(key, []):
            label = label_by_key.get(key, key)
            if ep.get("grazing"):
                when = f"~{ep['peak_time'][-5:]} — may briefly touch"
                dur = "—"
                peak = f"&lt;1.2&Prime;"
            else:
                end = ep["end"][-5:] if ep.get("end") else "beyond window"
                when = f"~{ep['start'][-5:]} &rarr; {end}"
                dur = (f"{ep['duration_h']:.1f} h"
                       if ep.get("duration_h") is not None else "ongoing")
                peak = f"+{ep['peak_depth_in']:.1f}&Prime; at {ep['peak_time'][-5:]}"
            rows += (f"<tr><td>{label}</td><td>{elev_by_key.get(key, '')}</td>"
                     f"<td>{when}</td><td>{dur}</td><td>{peak}</td></tr>")
    if not rows:
        return ""
    return f"""
  <section class="flood-windows">
    <h2>Flooding windows (next 24 h)</h2>
    <table class="tide-table">
      <thead><tr><th>Landmark</th><th>NAVD88</th><th>Wet window</th>
      <th>Duration</th><th>Peak</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
    <p class="note">Derived from the predicted water curve above
       (tide + surge + rain layer). Times are approximate (&sim;10–20
       min); end times are the optimistic edge — water drains slightly
       slower than the gauge falls, and the retention pockets hold
       water for hours after. Convective bursts can flood outside
       these windows entirely (see the rain-risk banner).</p>
  </section>
"""


def _render_pluvial_advisory_html(forecast):
    """Pluvial flood-risk banner (v0.9 first step, 2026-07-06).

    Rain alone floods the intersection — proven by the 7/6 flash
    flood (7.3" at curb, 1.5 h before high tide, bay below all
    grates). The tide-keyed model cannot predict that event class,
    so this banner surfaces the risk CATEGORICALLY whenever forecast
    rain conditions resemble it. Empty string when no risk."""
    pr = forecast.get("pluvial_risk") or {}
    level = pr.get("level")
    if not level:
        return ""
    heading = ("ELEVATED pluvial flood risk" if level == "elevated"
               else "Possible pluvial flooding")
    alerts_html = ""
    alerts = pr.get("nws_flood_alerts") or []
    if alerts:
        rows = "".join(
            f'<li><b>{a.get("event", "")}</b> ({a.get("severity", "")}) '
            f'— {a.get("headline", "")}</li>'
            for a in alerts)
        alerts_html = (
            f'<p style="margin:6px 0 2px 0"><b>Active NWS alerts for '
            f'this location:</b></p><ul style="margin:2px 0 8px 18px">'
            f'{rows}</ul>')
    details = (
        f"Next 24 h: peak QPF rate {pr.get('peak_rain_rate_24h_in_hr', 0):.2f} in/hr, "
        f"cumulative {pr.get('cumulative_rain_24h_in', 0):.2f}\", "
        f"max precip probability {pr.get('max_pop_24h_pct', 0)}%"
        + (", thunderstorm/heavy-rain wording in the NWS forecast"
           if pr.get("convective_wording") else "")
        + "."
    )
    # v0.9-alpha scenario depths. Two scenarios:
    #  (a) burst at LOW tide (drains functional) — 7/6-class
    #  (b) burst at the worst HIGH tide (compound) — Oct 30-class
    #
    # Burst estimate — ANALOG SCALING (user proposal 2026-07-06: "use
    # this and the October 2025 event as examples of what to expect").
    # We can't know true convective rates, but we don't need to: the
    # 7/6 event pins the mapping from QPF-as-forecast to observed
    # flood. 7/6's max 6-h QPF bucket was ~0.55" and the flood fit a
    # 1.7 in/hr effective burst. Scale linearly off that single
    # anchor: burst ≈ 1.7 × (max_6h_accum / 0.55), clamped to
    # [QPF peak rate, 3.0 in/hr]. The ratio absorbs both QPF's
    # convective smearing AND the Highlands-hillside catchment
    # amplification (rain on the ~200-ft hill drains to this low
    # corner — local water input outruns local rainfall), because
    # both were baked into the 7/6 anchor. One-anchor calibration —
    # every future rain event tightens or breaks it; the bot archives
    # pluvial_risk + QPF daily so the training set builds itself.
    burst = pr.get("burst_est_in_hr", 0) or 0
    worst_peak = forecast.get("peak_forecast_observed_mllw")
    scenario_html = ""
    if burst > 0.1:
        # v0.9-gamma dual models: each scenario reports the bracket
        # [min, max] of the power-law (primary) and tanh (saturating)
        # estimates. They agree within ~1" in the calibrated range
        # (0.4-1.7 in/hr) and diverge for violent bursts — the spread
        # IS the model uncertainty, so show it instead of hiding it.
        def _bracket(bay):
            pw, th = estimate_pluvial_water_models(burst, bay)
            lo, hi = min(pw, th), max(pw, th)
            lo_c, hi_c = (lo - 4.16) * 12, (hi - 4.16) * 12
            if (hi - lo) < 0.04:
                return f'{pw:.2f} NAVD88 ({"%+.1f" % ((pw-4.16)*12)}&Prime; at curb)', hi
            return (f'{lo:.2f}&ndash;{hi:.2f} NAVD88 '
                    f'({"%+.1f" % lo_c} to {"%+.1f" % hi_c}&Prime; at curb, '
                    f'power-law/tanh spread)', hi)
        lt_txt, _ = _bracket(2.5)
        scenario_html = (
            f'<p><b>Scenario estimates (v0.10 tank steady-state / tanh bracket, burst '
            f'{burst:.1f} in/hr):</b><br>'
            f'&bull; Burst at LOW tide (drains working): water ≈ '
            f'{lt_txt} — 7/6-class flash flood.<br>'
        )
        if worst_peak is not None:
            bay_at_high = worst_peak + LOCAL_ENHANCEMENT_FT + MLLW_TO_NAVD88_OFFSET
            cp_txt, cp_hi = _bracket(bay_at_high)
            oct30_tag = (" — Oct 30 2025 class"
                         if cp_hi >= 5.0 else "")
            scenario_html += (
                f'&bull; Burst at the worst HIGH tide '
                f'({forecast.get("peak_time_local", "")}): water ≈ '
                f'{cp_txt} — compound rain+tide{oct30_tag}.</p>'
            )
        else:
            scenario_html += '</p>'
    return (
        '<section class="pluvial-advisory">'
        f'<h3>&#9888; {heading} — independent of the tide</h3>'
        f'{alerts_html}'
        f'<p>{details}</p>'
        f'{scenario_html}'
        '<p class="note">Heavy rain can flood the Bay+Central '
        'intersection with no tidal contribution at all — the '
        '2026-07-06 flash flood put ~7&Prime; of water at the curb '
        '1.5 hours <i>before</i> high tide with the bay a foot below '
        'the lowest grate. The tide-keyed predictions below do not '
        'capture this event class. NWS rain amounts (QPF) smear '
        'short convective bursts, so the scenario estimates assume a '
        '7/6-class burst whenever thunderstorms are in the forecast. '
        'The pluvial model is calibrated on FOUR events (7/6 + 7/9/2026 '
        'flash floods — both with full measured hydrographs — Oct 30 '
        '2025 compound, Dec 19 2025 moderate) '
        'with rain forcing measured by MRMS radar. Scenario depths '
        'bracket the v0.10 tank steady-state (primary) against the '
        'saturating tanh (conservative floor — event #4 showed real '
        'peaks exceed it in violent bursts). Treat depths as '
        '&plusmn;3&Prime;-class estimates, not measurements.</p>'
        '</section>'
    )


def _render_wind_adjustment_html(forecast):
    """v0.8 wind-direction adjustment block — rendered as a separate
    "expected actual" line in the worst-case detail section. Only
    shown when forecast wind at peak is in the offshore sector
    (currently the only sector that yields a non-zero adjustment).

    Empty string when no adjustment applies (onshore or unknown
    winds → main prediction stands).
    """
    wind_adj = forecast.get("wind_adjustment") or {}
    adjusted_depths = forecast.get("depths_in_wind_adjusted")
    if not wind_adj or wind_adj.get("adjustment_ft", 0) == 0 or not adjusted_depths:
        return ""
    main_depths = forecast.get("depths_in") or {}
    main_curb = main_depths.get("curb", 0)
    adj_curb = adjusted_depths.get("curb", 0)
    adj_regime = adjusted_depths.get("regime", "?")
    main_regime = main_depths.get("regime", "?")
    return (
        '<section class="wind-adjustment-advisory">'
        '<h3>Wind adjustment — expected actual</h3>'
        f'<p class="note">{wind_adj.get("note", "")}</p>'
        f'<p><b>Wind-adjusted curb depth:</b> {adj_curb:+.1f}&Prime; '
        f'(regime: <b>{adj_regime}</b>) &mdash; vs. main prediction of '
        f'{main_curb:+.1f}&Prime; ({main_regime}). The main prediction '
        f'errs on the safer / over-predict side; the wind-adjusted '
        f'value is the v0.8 calibrated estimate for the forecast wind '
        f'sector. <i>v0.8 calibration anchor: 2026-06-14 (offshore peak '
        f'wind, enh -0.13) vs 2026-06-15 (onshore peak wind, enh 0).</i></p>'
        '</section>'
    )


def _render_cold_advisory_html(forecast):
    """When 72-h mean temp is below 32°F (cold-lockout conditions met),
    surface an advisory note instead of zeroing predictions.

    Pre-2026-05-19: predict_landmark_depths returned all-zero depths
    in cold conditions and the regime banner said COLD_LOCKOUT.
    Post-2026-05-19 (per history/reports/cold_weather_retrospective.md):
    the web-evidence retrospective showed the rule was likely too
    generous, so predictions go through unchanged and this advisory
    notes that conditions are met but the hypothesis is unresolved.

    Empty string when cold-lockout conditions are NOT met."""
    if not forecast.get("cold_lockout"):
        return ""
    temp = forecast.get("temp_avg_72h_f")
    temp_str = f"{temp:.1f}°F" if temp is not None else "below freezing"
    return (
        '\n  <section class="cold-advisory">\n'
        '    <h2>Cold-conditions advisory</h2>\n'
        f'    <p>72-h mean temperature at Sandy Hook is <b>{temp_str}</b> '
        '(below the 32°F cold-lockout threshold). Through v0.6 the model '
        'forced predicted flooding to zero in this regime, on the theory '
        'that storm-drain outfalls become ice-locked and block bay → street '
        'backflow (Pathway B); since 2026-05-19 the rule is advisory-only '
        '(hypothesis open, evidence: one event).</p>\n'
        '    <p>The 19-event historical retrospective '
        '(<a href="https://github.com/JohnUrban/barnacle/blob/main/history/reports/cold_weather_retrospective.md">'
        'cold_weather_retrospective.md</a>) found web evidence that ~3 of '
        '5 named-storm candidates likely flooded Monmouth County despite '
        'the override conditions being met — so the rule appears too '
        'generous. The single Feb 22-23 2026 observation that originally '
        'calibrated it may be an outlier.</p>\n'
        '    <p><b>Current status: hypothesis open, not applied.</b> The '
        'predictions below assume <i>no</i> suppression. Cold-lockout '
        'may still apply at 342 Bay specifically — every cold-conditions-'
        'met event going forward adds to the validation dataset.</p>\n'
        '  </section>\n'
    )


def _render_cold_advisory_text(forecast):
    """Plain-text equivalent of _render_cold_advisory_html. Returns
    list of lines (possibly empty)."""
    if not forecast.get("cold_lockout"):
        return []
    temp = forecast.get("temp_avg_72h_f")
    temp_str = f"{temp:.1f} F" if temp is not None else "below freezing"
    return [
        "Cold-conditions advisory:",
        f"  72-h mean temp at Sandy Hook is {temp_str} (below 32 F).",
        "  Pre-v0.7 cold-lockout rule would have suppressed predicted",
        "  flooding here, but the 19-event historical retrospective",
        "  (history/reports/cold_weather_retrospective.md) found",
        "  evidence the rule is too generous. Hypothesis remains open;",
        "  predictions below assume NO suppression.",
    ]


def _render_live_gauge_section(forecast):
    """Render a 24h sparkline of observed Sandy Hook water level.
    HANDOFF 16f / Y in the 2026-05-19 solo-work backlog.

    Empty string when no observed data available."""
    obs = forecast.get("live_gauge_24h") or []
    if len(obs) < 2:
        return ""
    latest = obs[-1]
    latest_val = latest.get("value_mllw")
    latest_time = latest.get("time", "")
    series = [
        {"time": p["time"], "v": p["value_mllw"]}
        for p in obs if p.get("value_mllw") is not None
    ]
    series_json = json.dumps(series)

    return f"""
  <section class="live-gauge">
    <h2>Live observed water level — past 24 h</h2>
    <p class="note">Sandy Hook gauge (station 8531680). Latest:
       <b>{latest_val:.2f} ft MLLW</b> at {format_time_full(latest_time)}.
       Refreshed each workflow run (hourly).</p>
    <canvas id="live-gauge-chart" width="800" height="240"
            style="max-width:100%;height:auto;display:block;margin:8px auto"></canvas>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@3.0.1/dist/chartjs-plugin-annotation.min.js"></script>
    <script>
      (function() {{
        var series = {series_json};
        var labels = series.map(function(p) {{
          var d = new Date(p.time.replace(' ', 'T'));
          if (isNaN(d.getTime())) return p.time;
          return d.toLocaleString(undefined, {{
            hour: 'numeric', minute: '2-digit'
          }});
        }});
        var values = series.map(function(p) {{ return p.v; }});
        var ctx = document.getElementById('live-gauge-chart').getContext('2d');
        new Chart(ctx, {{
          type: 'line',
          data: {{
            labels: labels,
            datasets: [{{
              label: 'Observed (ft MLLW)',
              data: values,
              borderColor: 'rgba(31, 111, 235, 0.95)',
              backgroundColor: 'rgba(31, 111, 235, 0.10)',
              fill: true,
              pointRadius: 0,
              tension: 0.25,
            }}]
          }},
          options: {{
            responsive: true,
            plugins: {{
              annotation: {{ annotations: {{
                curb: {{
                  type: 'line', yMin: 6.58, yMax: 6.58,
                  borderColor: 'rgba(217, 119, 6, 0.7)',
                  borderWidth: 1, borderDash: [6, 4],
                  label: {{ display: true, content: 'curb (6.58)',
                            position: 'end',
                            backgroundColor: 'rgba(255,255,255,0.85)',
                            color: '#b35a00',
                            font: {{ size: 10 }} }}
                }},
                grate: {{
                  type: 'line', yMin: {SH_FIRST_WATER}, yMax: {SH_FIRST_WATER},
                  borderColor: 'rgba(31, 111, 235, 0.5)',
                  borderWidth: 1, borderDash: [3, 3],
                  label: {{ display: true, content: 'lowest grate ({SH_FIRST_WATER})',
                            position: 'end',
                            backgroundColor: 'rgba(255,255,255,0.85)',
                            color: '#1f6feb',
                            font: {{ size: 10 }} }}
                }}
              }} }},
              legend: {{ display: false }},
              tooltip: {{
                callbacks: {{
                  label: function(c) {{ return c.parsed.y.toFixed(2) + ' ft MLLW'; }}
                }}
              }}
            }},
            scales: {{
              x: {{ grid: {{ display: false }},
                    ticks: {{ maxTicksLimit: 8, autoSkip: true }} }},
              y: {{ title: {{ display: true, text: 'ft MLLW' }},
                    grid: {{ color: 'rgba(0,0,0,0.05)' }} }}
            }}
          }}
        }});
      }})();
    </script>
    <p class="note">For NOAA's official gauge page (more products,
       longer windows):
       <a href="https://tidesandcurrents.noaa.gov/stationhome.html?id=8531680">
       Sandy Hook 8531680</a>.</p>
  </section>
"""


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
    <h2>Sandy Hook peak over time</h2>
    <p class="note">Observed (■) past peaks and predicted (●) upcoming peaks,
       plotted by default in <b>inches vs the SW grate</b> (the
       project's standard reference; 0&Prime; = water first emerges) —
       toggle to the raw gauge reading (ft MLLW).
       Both series are PER-TIDE (both daily highs — the zig-zag is the
       real day/night inequality, often ~1 ft here). Under each past
       square, a faded circle shows what the model predicted
       <b>~24 hours ahead</b> — the lead time the daily email promises
       — so the square-to-circle gap is the forecast error you would
       actually have lived with (nearest logged run within 16–36 h;
       missing where the throttled hourly bot had no qualifying run).
       When burst-capable rain is in the forecast, navy triangles mark
       the rain-burst COMPOUND potential over the affected upcoming
       tides (same meaning as the burst band on the 24-h chart;
       plotted in SH-equivalent units — the gauge itself never records
       rain floods). Horizontal lines are the SH-MLLW thresholds at
       which the
       {CURRENT_MODEL_VERSION} model (enhancement 0.00, calibrated on
       4 tape-measured events, SH 6.17&ndash;7.29) predicts water
       reaches each landmark. <b>Caveats</b>: offshore peak winds run
       ~0.13 ft lower (see the wind adjustment); the 0.00 enhancement
       is untested by tape above SH ~7.3 (storm-surge extrapolation);
       and these are TIDE thresholds — rain floods ignore them
       entirely (see the rain pathway / burst band above).</p>
    <div class="heatmap-toggle unit-toggle">
      <span class="note">Units:</span>
      <label><input type="radio" name="osc-unit" value="in" checked>
        &Prime; vs SW grate</label>
      <label><input type="radio" name="osc-unit" value="mllw">
        ft MLLW</label>
    </div>
    <!-- Fixed-height wrapper + maintainAspectRatio:false — on phones a
         width-locked aspect ratio squashed the plot to ~50px once the
         legend took its rows (user screenshot 2026-07-07 PM). -->
    <div style="position:relative;height:360px;margin:8px auto">
      <canvas id="oscillation-chart"></canvas>
    </div>
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
          return p.kind === 'observed' ? p.sh_peak_mllw : null;
        }});
        var predictedData = points.map(function(p) {{
          return p.kind === 'predicted' ? p.sh_peak_mllw : null;
        }});
        // What the model said ~24h before each PAST tide (null where
        // the throttled hourly log has no 16-36h-lead run). Drawn as
        // a faded halo under the observed square: the vertical gap IS
        // the forecast error at the lead time the daily email promises.
        var pred24Data = points.map(function(p) {{
          return p.predicted_24h_mllw != null ? p.predicted_24h_mllw : null;
        }});
        // Rain-burst compound potential for near-term future tides
        // (only present when pluvial risk is live) — navy triangles,
        // same meaning as the 24h chart's burst-band top.
        var burstData = points.map(function(p) {{
          return p.burst_potential_mllw != null ? p.burst_potential_mllw : null;
        }});
        var hasBurst = burstData.some(function(v) {{ return v != null; }});
        // Landmark threshold lines as constant DATASETS with legend
        // entries — the 2026-07-06 chart grammar (labels live in the
        // LEGEND, never boxes on the plot; boxes collided into soup on
        // phones). Shared palette with the water-level chart, so the
        // reader learns ONE color language.
        var landmarks = data.landmarks;
        var thresholds = landmarks.map(function(l) {{ return l.mllw_threshold; }});
        var minE = Math.min.apply(null, thresholds);
        var maxE = Math.max.apply(null, thresholds);
        // Short names: the legend is 7 entries on a ~360px phone —
        // every character costs a wrap row, and rows cost plot height.
        var LM_STYLE = {{
          grate_SW:        {{ color: '#222222', name: 'SW grate', solid: true }},
          gutter_walkway:  {{ color: '#2f8f5f', name: 'gutter' }},
          curb:            {{ color: '#c0392b', name: 'curb' }},
          lawn_step:       {{ color: '#7c4dbc', name: 'lawn step' }},
          porch_step1_top: {{ color: '#6d4c2f', name: 'porch step' }}
        }};
        var landmarkDatasets = landmarks.map(function(l) {{
          var st = LM_STYLE[l.key] || {{ color: '#888', name: l.label }};
          return {{
            label: st.name + ' ' + l.mllw_threshold.toFixed(2),
            data: labels.map(function() {{ return l.mllw_threshold; }}),
            borderColor: st.color,
            borderWidth: st.solid ? 1.5 : 1.2,
            borderDash: st.solid ? [] : [6, 5],
            fill: false, pointRadius: 0, spanGaps: true,
          }};
        }});
        // Unit toggle (user 2026-07-07): default inches-vs-SW-grate,
        // option ft MLLW. Shared preference + event with the flood-
        // peaks chart below so both flip together.
        var UNIT_KEY = 'barnacle-peaks-unit';
        var unit = 'in';
        try {{ unit = localStorage.getItem(UNIT_KEY) || 'in'; }} catch (e) {{}}
        var GRATE_SH = 6.34;   // the SW grate expressed at the gauge
        function conv(v) {{ return unit === 'in' ? (v - GRATE_SH) * 12 : v; }}
        function fmtShort(v) {{
          var c = conv(v);
          return unit === 'in'
            ? (c >= 0 ? '+' : '') + c.toFixed(1) + '\u2033' : c.toFixed(2);
        }}
        function fmtVal(v) {{
          return fmtShort(v) + (unit === 'in' ? ' vs SW grate' : ' ft MLLW');
        }}
        function cmap(arr) {{
          return arr.map(function(v) {{ return v == null ? null : conv(v); }});
        }}
        var ctx = document.getElementById('oscillation-chart').getContext('2d');
        var chart = null;
        function build() {{
          if (chart) chart.destroy();
          var lmDatasets = landmarks.map(function(l) {{
            var st = LM_STYLE[l.key] || {{ color: '#888', name: l.label }};
            return {{
              label: st.name + ' ' + fmtShort(l.mllw_threshold),
              data: labels.map(function() {{ return conv(l.mllw_threshold); }}),
              borderColor: st.color,
              borderWidth: st.solid ? 1.5 : 1.2,
              borderDash: st.solid ? [] : [6, 5],
              fill: false, pointRadius: 0, spanGaps: true,
            }};
          }});
          chart = new Chart(ctx, {{
            type: 'line',
            data: {{
              labels: labels,
              datasets: [
                {{
                  label: 'Observed SH peak',
                  data: cmap(observedData),
                  borderColor: 'rgba(60,60,60,0.85)',
                  backgroundColor: 'rgba(60,60,60,0.85)',
                  pointStyle: 'rect', pointRadius: 4,
                  spanGaps: true, showLine: false,
                }},
                {{
                  label: 'Predicted SH peak',
                  data: cmap(predictedData),
                  borderColor: 'rgba(31, 111, 235, 0.9)',
                  backgroundColor: 'rgba(31, 111, 235, 0.9)',
                  pointStyle: 'circle', pointRadius: 4,
                  spanGaps: true, showLine: false,
                }},
                {{
                  label: 'as predicted ~24 h ahead',
                  data: cmap(pred24Data),
                  borderColor: 'rgba(31, 111, 235, 0.45)',
                  backgroundColor: 'rgba(31, 111, 235, 0.25)',
                  pointStyle: 'circle', pointRadius: 7,
                  pointBorderWidth: 1.5,
                  spanGaps: true, showLine: false,
                }}
              ].concat(hasBurst ? [{{
                  label: 'rain-burst compound potential',
                  data: cmap(burstData),
                  borderColor: 'rgba(11, 61, 107, 0.95)',
                  backgroundColor: 'rgba(11, 61, 107, 0.35)',
                  pointStyle: 'triangle', pointRadius: 6,
                  spanGaps: true, showLine: false,
                }}] : []).concat(lmDatasets)
            }},
            options: {{
              responsive: true,
              maintainAspectRatio: false,
              plugins: {{
                tooltip: {{
                  filter: function(item) {{
                    return item.datasetIndex < (hasBurst ? 4 : 3);
                  }},
                  callbacks: {{
                    label: function(c) {{
                      var p = points[c.dataIndex];
                      if (!p) return c.formattedValue;
                      if (hasBurst && c.datasetIndex === 3) {{
                        return [
                          'If a forecast-class burst lands on this tide:',
                          'street water \u2248 ' +
                            fmtVal(p.burst_potential_mllw) +
                            (unit === 'in' ? '' :
                             ' (SH-equivalent \u2014 the gauge never' +
                             ' reads rain floods)'),
                        ];
                      }}
                      if (c.datasetIndex === 2) {{
                        var err = conv(p.predicted_24h_mllw) -
                                  conv(p.sh_peak_mllw);
                        var eu = unit === 'in' ? '\u2033' : ' ft';
                        return [
                          '~24 h ahead we said: ' +
                            fmtVal(p.predicted_24h_mllw),
                          'It came in: ' + fmtShort(p.sh_peak_mllw) +
                            ' (' + (err >= 0 ? '+' : '') +
                            err.toFixed(unit === 'in' ? 1 : 2) +
                            eu + ' error)',
                        ];
                      }}
                      return [
                        (p.kind === 'observed' ? 'Observed' : 'Predicted'),
                        fmtVal(p.sh_peak_mllw),
                      ];
                    }}
                  }}
                }},
                legend: {{ position: 'top',
                           labels: {{ boxWidth: 22, boxHeight: 2,
                                      font: {{ size: 10 }} }} }}
              }},
              scales: {{
                x: {{
                  title: {{ display: true, text: 'Tide peak (local time)',
                            font: {{ size: 11 }} }},
                  ticks: {{ maxTicksLimit: 8, font: {{ size: 10 }},
                            maxRotation: 50 }},
                  grid: {{ color: 'rgba(0,0,0,0.05)' }}
                }},
                y: {{
                  title: {{ display: true,
                            text: unit === 'in'
                              ? 'inches vs SW grate'
                              : 'Sandy Hook peak (ft MLLW)',
                            font: {{ size: 11 }} }},
                  ticks: {{ font: {{ size: 10 }} }},
                  grid: {{ color: 'rgba(0,0,0,0.06)' }},
                  suggestedMin: conv(Math.min(minE - 0.2,
                    Math.min.apply(null,
                      points.map(function(p) {{ return p.sh_peak_mllw; }})))),
                  suggestedMax: conv(Math.max(maxE + 0.2,
                    Math.max.apply(null,
                      points.map(function(p) {{
                        return Math.max(p.sh_peak_mllw,
                                        p.burst_potential_mllw || 0);
                      }})))),
                }}
              }}
            }}
          }});
        }}
        build();
        var radios = document.querySelectorAll('input[name="osc-unit"]');
        function syncRadios() {{
          radios.forEach(function(r) {{ r.checked = (r.value === unit); }});
        }}
        syncRadios();
        radios.forEach(function(r) {{
          r.addEventListener('change', function() {{
            try {{ localStorage.setItem(UNIT_KEY, r.value); }} catch (e) {{}}
            document.dispatchEvent(new CustomEvent('barnacle-peaks-unit'));
          }});
        }});
        document.addEventListener('barnacle-peaks-unit', function() {{
          try {{ unit = localStorage.getItem(UNIT_KEY) || 'in'; }} catch (e) {{}}
          syncRadios();
          build();
        }});
      }})();
    </script>
  </section>
"""


def _flood_peaks_chart_data(forecast):
    """Data for the all-pathways flood-peaks timeline (2026-07-07,
    user design). Everything in ft NAVD88 (client converts to the
    display unit): tide peaks past+future (reusing the oscillation
    data), MEASURED flood peaks from the spot-check log (any pathway
    — this is where the 7/6 11:34 AM rain flood lives, which a
    per-tide axis cannot represent), and past days' archived
    burst-potential assessments (day-wide: the daily archive is the
    day's LAST run, so there is no honest clock time for them)."""
    base = _oscillation_chart_data(forecast)
    tides = []
    for pt in base["points"]:
        row = {
            "time": pt["time"],
            "navd88": round(pt["sh_peak_mllw"] + MLLW_TO_NAVD88_OFFSET, 3),
            "kind": pt["kind"],
        }
        if pt.get("predicted_24h_mllw") is not None:
            row["pred24_navd88"] = round(
                pt["predicted_24h_mllw"] + MLLW_TO_NAVD88_OFFSET, 3)
        if pt.get("burst_potential_mllw") is not None:
            row["burst_navd88"] = round(
                pt["burst_potential_mllw"] + MLLW_TO_NAVD88_OFFSET, 3)
        tides.append(row)

    # Measured flood peaks: max implied water per day from the
    # spot-check log (landmark elevation + depth). Pocket rows are
    # excluded (retention, not street water); dry checks (implied
    # water below the SW grate) don't mark.
    measured = []
    try:
        elev_by_key = {k: e for k, _lbl, e, _sh in LANDMARKS}
        cutoff = _station_local_now() - dt.timedelta(days=7)
        best = {}
        obs_path = os.path.join(_REPO_ROOT, "data",
                                "labeled_observations.csv")
        with open(obs_path) as f:
            for r in csv.DictReader(f):
                key = (r.get("landmark_key") or "").strip()
                if "pocket" in key or key not in elev_by_key:
                    continue
                try:
                    d_in = float(r.get("observed_depth_in") or "")
                except ValueError:
                    continue
                ts = (r.get("observation_time_local") or "").strip()
                try:
                    t = dt.datetime.strptime(ts[:16], "%Y-%m-%dT%H:%M")
                except ValueError:
                    continue
                if t < cutoff:
                    continue
                w = elev_by_key[key] + d_in / 12.0
                if w <= GRATE_SW:
                    continue
                day = t.date().isoformat()
                if day not in best or w > best[day][1]:
                    best[day] = (ts[:16].replace("T", " "), w)
        measured = [{"time": v[0], "navd88": round(v[1], 3)}
                    for v in sorted(best.values())]
    except OSError:
        measured = []

    # Past days where the archived forecast carried live pluvial risk.
    risk_days = []
    try:
        today = _station_local_now().date()
    except Exception:
        today = dt.date.today()
    for i in range(1, 8):
        d = today - dt.timedelta(days=i)
        path = os.path.join(_REPO_ROOT, "docs", "archive",
                            d.isoformat() + ".json")
        try:
            with open(path) as f:
                arc = json.load(f)
        except (OSError, ValueError):
            continue
        pr = arc.get("pluvial_risk") or {}
        level = pr.get("day_max_level") or pr.get("level")
        if not level:
            continue
        # Prefer the day-max carry-forward fields (2026-07-08+); older
        # archives only hold the day's LAST run, which can postdate the
        # event it should describe (the 7/6 flood day archived only the
        # evening residue — a known historical artifact, noted on the
        # chart).
        pots = [v for v in (pr.get("day_max_potential_low_tide_navd88"),
                            pr.get("day_max_potential_low_tide_navd88_tanh"),
                            pr.get("potential_low_tide_navd88"),
                            pr.get("potential_low_tide_navd88_tanh"))
                if v is not None]
        if not pots:
            continue
        risk_days.append({"day": d.isoformat(),
                          "navd88": round(max(pots), 3),
                          "level": level})

    landmarks = [{"key": l["key"], "navd88": l["navd88"]}
                 for l in base["landmarks"]]
    return {"tides": tides, "measured": measured,
            "risk_days": risk_days, "landmarks": landmarks}


def _render_flood_peaks_section(forecast):
    """The all-pathways companion to the per-tide peaks chart above it
    (2026-07-07, user: "we care about flooding any time" — rain-only
    floods happen between tides and at low tide; the per-tide axis
    cannot show them). Continuous TIME x-axis, local-water y-axis.
    Kept alongside the original per-tide chart for now (single-user
    A/B; a keep/retire decision can come later)."""
    data = _flood_peaks_chart_data(forecast)
    if len(data["tides"]) < 2:
        return ""
    data_json = json.dumps(data, default=str)
    js = r"""
      (function() {
        var data = __DATA__;
        var GRATE = 3.52, MLLW_OFF = 2.82;
        var UNIT_KEY = 'barnacle-peaks-unit';
        var unit = 'in';
        try { unit = localStorage.getItem(UNIT_KEY) || 'in'; } catch (e) {}
        function conv(v) {
          return unit === 'in' ? (v - GRATE) * 12 : v + MLLW_OFF;
        }
        function fmtShort(v) {
          var c = conv(v);
          return unit === 'in'
            ? (c >= 0 ? '+' : '') + c.toFixed(1) + '″' : c.toFixed(2);
        }
        function fmtVal(v) {
          return fmtShort(v) + (unit === 'in' ? ' vs SW grate' : ' ft MLLW');
        }
        function T(str) {
          var d = new Date(str.replace(' ', 'T'));
          return isNaN(d.getTime()) ? null : d.getTime();
        }
        function fmtTick(ms) {
          return new Date(ms).toLocaleDateString(undefined,
            { weekday: 'short', month: 'numeric', day: 'numeric' });
        }
        var LM_STYLE = {
          grate_SW:        { color: '#222222', name: 'SW grate', solid: true },
          gutter_walkway:  { color: '#2f8f5f', name: 'gutter' },
          curb:            { color: '#c0392b', name: 'curb' },
          lawn_step:       { color: '#7c4dbc', name: 'lawn step' },
          porch_step1_top: { color: '#6d4c2f', name: 'porch step' }
        };
        var nowMs = Date.now();
        var allX = [];
        function pts(rows, field, kindFilter) {
          var out = [];
          rows.forEach(function(r) {
            if (kindFilter && r.kind !== kindFilter) return;
            var v = field ? r[field] : r.navd88;
            var x = T(r.time);
            if (v == null || x == null) return;
            allX.push(x);
            out.push({ x: x, y: v, src: r });
          });
          return out;
        }
        var obsP    = pts(data.tides, null, 'observed');
        var futP    = pts(data.tides, null, 'predicted');
        var p24P    = pts(data.tides, 'pred24_navd88', null);
        var burstP  = pts(data.tides, 'burst_navd88', null);
        var measP   = pts(data.measured, null, null);
        // Day-wide archived-risk segments: pairs separated by a null
        // gap so each day is its own dash.
        var riskSeg = [];
        data.risk_days.forEach(function(r) {
          var d0 = T(r.day + ' 00:00'), d1 = T(r.day + ' 23:59');
          if (d0 == null) return;
          allX.push(d0, d1);
          riskSeg.push({ x: d0, y: r.navd88, src: r });
          riskSeg.push({ x: d1, y: r.navd88, src: r });
          riskSeg.push({ x: (d0 + d1) / 2, y: null });
        });
        var xMin = Math.min.apply(null, allX.concat([nowMs])) - 6*3600e3;
        var xMax = Math.max.apply(null, allX.concat([nowMs])) + 6*3600e3;
        var allY = [];
        [obsP, futP, p24P, burstP, measP].forEach(function(a) {
          a.forEach(function(q) { allY.push(q.y); });
        });
        riskSeg.forEach(function(q) { if (q.y != null) allY.push(q.y); });
        data.landmarks.forEach(function(l) { allY.push(l.navd88); });
        var ctx = document.getElementById('flood-peaks-chart')
                    .getContext('2d');
        var chart = null;
        function cpts(a) {
          return a.map(function(q) {
            return { x: q.x, y: q.y == null ? null : conv(q.y), src: q.src };
          });
        }
        function build() {
          if (chart) chart.destroy();
          var lmDatasets = data.landmarks.map(function(l) {
            var st = LM_STYLE[l.key] || { color: '#888', name: l.key };
            return {
              label: st.name + ' ' + fmtShort(l.navd88),
              data: [{ x: xMin, y: conv(l.navd88) },
                     { x: xMax, y: conv(l.navd88) }],
              borderColor: st.color,
              borderWidth: st.solid ? 1.5 : 1.2,
              borderDash: st.solid ? [] : [6, 5],
              fill: false, pointRadius: 0, showLine: true,
            };
          });
          var core = [
            { label: 'Observed tide peak', data: cpts(obsP),
              borderColor: 'rgba(60,60,60,0.85)',
              backgroundColor: 'rgba(60,60,60,0.85)',
              pointStyle: 'rect', pointRadius: 4, showLine: false },
            { label: 'Predicted tide peak', data: cpts(futP),
              borderColor: 'rgba(31,111,235,0.9)',
              backgroundColor: 'rgba(31,111,235,0.9)',
              pointStyle: 'circle', pointRadius: 4, showLine: false },
            { label: 'as predicted ~24 h ahead', data: cpts(p24P),
              borderColor: 'rgba(31,111,235,0.45)',
              backgroundColor: 'rgba(31,111,235,0.25)',
              pointStyle: 'circle', pointRadius: 7,
              pointBorderWidth: 1.5, showLine: false },
          ];
          if (measP.length) core.push(
            { label: 'MEASURED flood (spot-check, any cause)',
              data: cpts(measP),
              borderColor: 'rgba(11,61,107,1)',
              backgroundColor: 'rgba(217,119,6,0.9)',
              pointStyle: 'rectRot', pointRadius: 7,
              pointBorderWidth: 2, showLine: false });
          if (burstP.length) core.push(
            { label: 'rain-burst compound potential', data: cpts(burstP),
              borderColor: 'rgba(11,61,107,0.95)',
              backgroundColor: 'rgba(11,61,107,0.35)',
              pointStyle: 'triangle', pointRadius: 6, showLine: false });
          if (riskSeg.length) core.push(
            { label: 'burst potential archived that day', data: cpts(riskSeg),
              borderColor: 'rgba(11,61,107,0.45)',
              borderWidth: 3, borderDash: [2, 3],
              pointRadius: 0, showLine: true, spanGaps: false });
          var nCore = core.length;
          chart = new Chart(ctx, {
            type: 'scatter',
            data: { datasets: core.concat(lmDatasets) },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              plugins: {
                annotation: { annotations: {
                  nowline: {
                    type: 'line', xMin: nowMs, xMax: nowMs,
                    borderColor: '#888', borderWidth: 1,
                    borderDash: [3, 3],
                    label: { display: true, content: 'now',
                             position: 'start',
                             backgroundColor: 'rgba(255,255,255,0.75)',
                             color: '#666', font: { size: 9 } }
                  }
                } },
                tooltip: {
                  filter: function(item) {
                    return item.datasetIndex < nCore;
                  },
                  callbacks: {
                    title: function(items) {
                      if (!items.length) return '';
                      return new Date(items[0].parsed.x).toLocaleString(
                        undefined, { weekday: 'short', month: 'numeric',
                                     day: 'numeric', hour: 'numeric',
                                     minute: '2-digit' });
                    },
                    label: function(c) {
                      var raw = c.raw || {};
                      var lbl = c.dataset.label + ': ';
                      var y = raw.src && raw.src.navd88 != null
                        ? raw.src.navd88
                        : (raw.src && raw.src.burst_navd88) || null;
                      return lbl + (c.parsed.y >= 0 && unit === 'in'
                        ? '+' : '') +
                        c.parsed.y.toFixed(unit === 'in' ? 1 : 2) +
                        (unit === 'in' ? '″ vs SW grate'
                                       : ' ft MLLW-equivalent');
                    }
                  }
                },
                legend: { position: 'top',
                          labels: { boxWidth: 22, boxHeight: 2,
                                    font: { size: 10 } } }
              },
              scales: {
                x: {
                  type: 'linear', min: xMin, max: xMax,
                  ticks: {
                    maxTicksLimit: 8, font: { size: 10 },
                    maxRotation: 50,
                    callback: function(v) { return fmtTick(v); }
                  },
                  grid: { color: 'rgba(0,0,0,0.05)' }
                },
                y: {
                  title: { display: true,
                           text: unit === 'in'
                             ? 'inches vs SW grate'
                             : 'ft MLLW (gauge-equivalent)',
                           font: { size: 11 } },
                  ticks: { font: { size: 10 } },
                  grid: { color: 'rgba(0,0,0,0.06)' },
                  suggestedMin: conv(Math.min.apply(null, allY)) -
                                (unit === 'in' ? 3 : 0.25),
                  suggestedMax: conv(Math.max.apply(null, allY)) +
                                (unit === 'in' ? 3 : 0.25),
                }
              }
            }
          });
        }
        build();
        var radios = document.querySelectorAll('input[name="fpk-unit"]');
        function syncRadios() {
          radios.forEach(function(r) { r.checked = (r.value === unit); });
        }
        syncRadios();
        radios.forEach(function(r) {
          r.addEventListener('change', function() {
            try { localStorage.setItem(UNIT_KEY, r.value); } catch (e) {}
            document.dispatchEvent(new CustomEvent('barnacle-peaks-unit'));
          });
        });
        document.addEventListener('barnacle-peaks-unit', function() {
          try { unit = localStorage.getItem(UNIT_KEY) || 'in'; } catch (e) {}
          syncRadios();
          build();
        });
      })();
""".replace("__DATA__", data_json)
    return """
  <section class="oscillation">
    <h2>Flood peaks at 342 Bay — past &amp; forecast (all pathways)</h2>
    <p class="note">The chart above is organized BY TIDE — but this
       corner floods on rain alone, between tides, even at dead low
       tide (7/6/2026). This companion view puts everything on a real
       TIME axis in local units: tide peaks (observed ■ / predicted ●
       / faded halo = what we said ~24&nbsp;h ahead), <b>measured
       flood peaks from the spot-check log</b> (orange diamonds — any
       cause, placed when they actually happened), navy triangles =
       rain-burst compound potential on upcoming tides, and faint
       navy day-dashes = days whose archived forecast carried live
       burst risk (day-wide, because a burst has magnitude but no
       forecastable clock time; the dash height is the day's MAXIMUM
       archived assessment from 2026-07-08 onward — dashes before
       that show only the day's last run, which can postdate the
       event: the 7/6 dash is the post-storm evening residue, not a
       hindcast; nothing predicted that flood — the QPF input was
       broken and the pluvial model didn't exist until that
       evening). A rain flood with no halo under it =
       a miss the tide model could never have seen; that is the point
       of this chart.</p>
    <div class="heatmap-toggle unit-toggle">
      <span class="note">Units:</span>
      <label><input type="radio" name="fpk-unit" value="in" checked>
        &Prime; vs SW grate</label>
      <label><input type="radio" name="fpk-unit" value="mllw">
        ft MLLW</label>
    </div>
    <div style="position:relative;height:380px;margin:8px auto">
      <canvas id="flood-peaks-chart"></canvas>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@3.0.1/dist/chartjs-plugin-annotation.min.js"></script>
    <script>""" + js + """    </script>
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
                # "~4.15" = inferred elevation (flood_edge event marks);
                # the ~ is honest display, not a parse obstacle
                v = float(str(row["value"]).lstrip("~"))
            except (TypeError, ValueError, KeyError):
                continue
            out.append({"x": x, "y": y, "navd88": v})
    return out


def _client_map_section_html(forecast, container_class="heatmap", level=2,
                              base_map_url="icons/map_raw.png",
                              show_depth_slider=False):
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
        f"baseMapUrl: '{base_map_url}', title: {json.dumps(title_with)}, "
        "style: window.barnacleMapStyle }});"
    ).replace("{{", "{").replace("}}", "}")
    intro_note = (
        '<p class="note">Overlay shows predicted tidal water depth across '
        'nearby topography. Classic shading: darker blue = deeper '
        '(saturates at 2 ft); depth bands: labeled physical ranges '
        '(splash / ankle / knee / waist / first floor / over head) '
        'that stay informative up to Sandy class. No meaningful rain '
        'forecast — overlay is tide-only.</p>'
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
            f"title: {json.dumps(title_no_rain)}, "
            "style: window.barnacleMapStyle }});"
        )
        script_render += no_rain_render
        intro_note = (
            '<p class="note">Overlay shows predicted water depth across '
            'nearby topography (classic blue or labeled depth bands — '
            'see the shading toggle). Toggle between including the '
            'forecast rain bonus or tide-only (HANDOFF 9b.5).</p>'
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

    # Depth slider — interactive "what would the map look like at any
    # water level" control (Batch 2 idea #1, user follow-up 2026-05-19).
    # Renders client-side via BarnacleMap.render() on each input change.
    # No pre-rendered PNGs.
    slider_html = ""
    slider_script = ""
    if show_depth_slider:
        # v0.9-gamma: the extra-rain slider runs the REAL pluvial
        # pathway client-side (head-dependent drainage + dual input
        # models + stage-storage fill), replacing the legacy
        # 8·tanh(rate) uniform bump. Embed the curve + constants;
        # null -> the JS keeps the legacy bump as fallback.
        _c = _load_stage_curve()
        rain_pathway_js = "null"
        if _c and PLUVIAL_VOLUME_K and PLUVIAL_POW_K:
            rain_pathway_js = json.dumps({
                "curve": [[c[0], round(c[1], 1)] for c in _c],
                "kss": round(TANK_K / TANK_KOUT, 1),   # v0.10 steady state
                "gt": TANK_GAMMA,
                "kpow": round(PLUVIAL_POW_K, 1),
                "gamma": round(PLUVIAL_POW_GAMMA, 4),
                "vk": round(PLUVIAL_VOLUME_K, 1),
                "drain": PLUVIAL_DRAIN_RATE,
                "knee": PLUVIAL_DRAIN_FULL_BELOW,
                "base": PLUVIAL_STREET_BASE,
                "scale": PLUVIAL_FREE_RATE_SCALE})
        _map_series = [
            {"t": pt["time"], "w": pt.get("water_navd88"),
             "b": bool(pt.get("burst_risk"))}
            for pt in (forecast.get("water_series") or [])
            if pt.get("water_navd88") is not None]
        _pots_m = [v for v in (
            (forecast.get("pluvial_risk") or {}).get("potential_low_tide_navd88"),
            (forecast.get("pluvial_risk") or {}).get("potential_low_tide_navd88_tanh"))
            if v is not None]
        map_series_js = json.dumps(
            {"series": _map_series,
             "potential": (max(_pots_m) if _pots_m else None)})
        slider_html = f"""
    <div class="depth-slider time-slider">
      <label for="time-slider-input">Slide through the forecast:</label>
      <input type="range" id="time-slider-input" min="0"
             max="{max(0, len(_map_series) - 1)}" step="1" value="0">
      <span id="time-slider-value">&mdash;</span>
    </div>
    <div class="depth-slider burst-toggle-row">
      <label><input type="checkbox" id="burst-potential-toggle">
        during rain-risk windows, show the BURST-POTENTIAL level
        (the chart's navy shading) instead of the expected level</label>
    </div>
    <div class="depth-slider">
      <label for="depth-slider-input">Explore water level:</label>
      <input type="range" id="depth-slider-input"
             min="1.5" max="11.6" step="0.05"
             value="{water_with_rain:.2f}"
             data-current="{water_with_rain:.4f}">
      <span id="depth-slider-value">{water_with_rain:.2f} ft NAVD88</span>
      <button type="button" id="depth-slider-reset">Snap to current forecast</button>
    </div>
    <div class="depth-slider unit-toggle">
      <span class="note">Units:</span>
      <label><input type="radio" name="depth-unit" value="in" checked> &Prime; vs SW grate</label>
      <label><input type="radio" name="depth-unit" value="navd88"> ft NAVD88</label>
      <label><input type="radio" name="depth-unit" value="mllw"> ft MLLW</label>
    </div>
    <div class="depth-slider rain-slider">
      <label for="rain-slider-input">Extra rain:</label>
      <input type="range" id="rain-slider-input"
             min="0" max="4.0" step="0.05" value="0">
      <span id="rain-slider-value">0.00 in/hr &rarr; +0.0&Prime;</span>
      <button type="button" id="rain-slider-reset">Reset extra rain</button>
    </div>
    <div class="depth-slider rain-model-toggle">
      <span class="note">Rain model:</span>
      <label><input type="radio" name="rain-model" value="tank" checked>
        v0.10 tank (steady-state, primary)</label>
      <label><input type="radio" name="rain-model" value="tanh">
        tanh (conservative)</label>
      <label><input type="radio" name="rain-model" value="power">
        power-law (v0.9, legacy)</label>
    </div>
    <p class="note">The depth slider sets the base (tide-set) water
       level; the extra-rain slider answers "what level does a
       SUSTAINED rate hold?" — drains absorb up to 0.25 in/hr
       (less as the base level backwaters the outfall toward the
       grate tops at 3.52), the surviving rate becomes a volume via
       the selected model, and that volume fills the measured
       stage-storage curve. Default = the v0.10 tank's steady state
       (the level reached within ~1 h of sustained rain; it drains
       back in ~20 min once rain stops — same calibration as the
       hydrograph on the chart, validated on four measured floods).
       The models agree below ~2 in/hr and diverge for violent
       bursts, where event #4 (+18.7&Prime; measured at sustained
       3.4 in/hr) sits exactly on the tank curve. "Extra" because
       rain may already be in the current forecast's water level —
       this explores additional rain beyond that. The depth range
       tops out at Sandy class: Hurricane Sandy's estimated true
       peak (~14.4 ft MLLW; the gauge failed at 13.31) &asymp; 11.6
       ft NAVD88 &asymp; +97&Prime; over the SW grate — nearly 3 ft
       of water on the porch deck. Note the blue shading saturates
       at 2 ft depth, so extreme levels differ in EXTENT more than
       in shade.</p>
"""
        slider_script = f"""
      (function() {{
        var dSlider = document.getElementById('depth-slider-input');
        var dLabel  = document.getElementById('depth-slider-value');
        var dBtn    = document.getElementById('depth-slider-reset');
        var rSlider = document.getElementById('rain-slider-input');
        var rLabel  = document.getElementById('rain-slider-value');
        var rBtn    = document.getElementById('rain-slider-reset');
        var canvas  = document.getElementById('heatmap-canvas');
        if (!dSlider || !canvas) return;
        var defaultWater = parseFloat(dSlider.getAttribute('data-current'));
        var RAIN_SAT_IN = {RAIN_SATURATION_IN};  // legacy fallback only
        // v0.10 pluvial pathway constants (null -> legacy 8·tanh bump)
        var RP = {rain_pathway_js};
        var rainModel = 'tank';
        try {{
          rainModel = localStorage.getItem('barnacle-rain-model') || 'tank';
        }} catch (e) {{}}
        var modelRadios = document.querySelectorAll('input[name="rain-model"]');
        modelRadios.forEach(function(r) {{
          r.checked = (r.value === rainModel);
          r.addEventListener('change', function() {{
            rainModel = r.value;
            try {{ localStorage.setItem('barnacle-rain-model', rainModel); }} catch (e) {{}}
            rerender();
          }});
        }});
        // Mirrors estimate_pluvial_water(): head-dependent drainage,
        // selected input model, stage-storage fill from the base.
        function rainWater(baseW, rate) {{
          if (!RP) return baseW + (RAIN_SAT_IN * Math.tanh(rate)) / 12.0;
          var b = Math.max(baseW, RP.base);
          var fracOpen = Math.min(1, Math.max(0,
            (RP.base - baseW) / (RP.base - RP.knee)));
          var net = rate - RP.drain * fracOpen;
          if (net <= 0) return b;
          var budget = rainModel === 'tanh'
            ? RP.vk * Math.tanh(net / RP.scale)
            : rainModel === 'power'
            ? RP.kpow * Math.pow(net, RP.gamma)
            : (RP.kss || RP.kpow) * Math.pow(net, RP.gt || RP.gamma);
          var baseStage = Math.max(0, (b - RP.base) * 12);
          var stage = baseStage;
          var C = RP.curve;
          for (var i = 1; i < C.length; i++) {{
            var s = C[i][0], a = C[i][1];
            if (s <= baseStage) continue;
            var step = a * (s - C[i-1][0]);
            if (budget < step) {{
              stage = a > 0 ? C[i-1][0] + budget / a : s;
              budget = 0; break;
            }}
            budget -= step; stage = s;
          }}
          if (budget > 0 && C[C.length-1][1] > 0)
            stage += budget / C[C.length-1][1];
          return RP.base + stage / 12.0;
        }}
        // Unit toggle (2026-07-06): display in inches-vs-SW-grate
        // (default — the project's standard reference), ft NAVD88, or
        // ft MLLW. The slider itself always runs in NAVD88 (model
        // space); only the display converts. Choice persists locally.
        var GRATE_SW = 3.52, MLLW_OFF = 2.82;
        var unit = 'in';
        try {{ unit = localStorage.getItem('barnacle-depth-unit') || 'in'; }} catch (e) {{}}
        var unitRadios = document.querySelectorAll('input[name="depth-unit"]');
        unitRadios.forEach(function(r) {{
          r.checked = (r.value === unit);
          r.addEventListener('change', function() {{
            unit = r.value;
            try {{ localStorage.setItem('barnacle-depth-unit', unit); }} catch (e) {{}}
            rerender();
          }});
        }});
        // Ladder context (2026-07-20): same names as the chart legend
        var LADDER_CTX = [
          [3.78, 'gutter'], [4.16, 'curb'],
          [4.66, 'lawn step'], [5.41, '1st porch step']
        ];
        function ladderContext(v) {{
          if (v < 3.52) return 'below the grates';
          var below = null, above = null;
          for (var i = 0; i < LADDER_CTX.length; i++) {{
            if (v >= LADDER_CTX[i][0]) below = LADDER_CTX[i][1];
            else if (!above) above = LADDER_CTX[i][1];
          }}
          if (!below) return 'street water, below the ' + (above || 'gutter');
          return 'above the ' + below + (above ? ', below the ' + above : '');
        }}
        function fmtWater(v) {{
          if (unit === 'navd88') return v.toFixed(2) + ' ft NAVD88';
          if (unit === 'mllw')   return (v + MLLW_OFF).toFixed(2) + ' ft MLLW';
          var inches = (v - GRATE_SW) * 12;
          return (inches >= 0 ? '+' : '') + inches.toFixed(1)
                 + '\u2033 vs SW grate';
        }}
        // Initialize the readout in the active unit (fix 2026-07-07:
        // the server-rendered label said "ft NAVD88" while the unit
        // toggle defaults to inches-vs-SW-grate; the label was only
        // corrected after the first user interaction).
        dLabel.textContent = fmtWater(parseFloat(dSlider.value))
          + ' (current forecast)';
        function rerender() {{
          var base = parseFloat(dSlider.value);
          var rate = parseFloat(rSlider.value);
          var w = rate > 0.001 ? Math.max(base, rainWater(base, rate))
                               : base;
          var extraFt = w - base;
          var atDefault = (Math.abs(base - defaultWater) < 0.005
                           && rate < 0.001);
          dLabel.textContent = fmtWater(base)
            + ' \u00b7 ' + ladderContext(base)
            + (Math.abs(base - defaultWater) < 0.005 ? ' (current forecast)' : '');
          rLabel.innerHTML = rate.toFixed(2) + ' in/hr \\u2192 +'
            + (extraFt * 12).toFixed(1) + '\\u2033'
            + (RP ? (rainModel === 'tanh' ? ' (tanh)'
                     : rainModel === 'power' ? ' (power-law v0.9)'
                     : ' (v0.10 tank)')
                  : ' (legacy)');
          BarnacleMap.render({{
            canvas: canvas,
            points: window.barnaclePoints,
            waterNavd88: w,
            style: window.barnacleMapStyle,
            baseMapUrl: {json.dumps(base_map_url)},
            title: 'Water level — ' + fmtWater(w)
              + ' · ' + ladderContext(w)
              + (rate > 0.001 ? ' (incl. +' + (extraFt * 12).toFixed(1)
                                 + '\\u2033 extra rain)' : '')
              + (atDefault ? '' : '  (exploration)')
          }});
        }}
        dSlider.addEventListener('input', function() {{
          // manual level exploration leaves time-scrub mode
          var tl = document.getElementById('time-slider-value');
          if (tl) tl.textContent = '\u2014';
          rerender();
        }});
        rSlider.addEventListener('input', rerender);
        // Shading toggle re-runs the current exploration state
        window.barnacleRerender = rerender;

        // TIME SCRUBBER (user 2026-07-20): slide the map through the
        // same series the top chart draws — see the street at any
        // forecast moment. Burst checkbox swaps in the navy-band
        // potential level across flagged (rain-risk) hours.
        var MS = {map_series_js};
        var tSlider = document.getElementById('time-slider-input');
        var tLabel = document.getElementById('time-slider-value');
        var bToggle = document.getElementById('burst-potential-toggle');
        function fmtT(t) {{
          var m = t.match(/(\\d{{4}})-(\\d{{2}})-(\\d{{2}}) (\\d{{2}}):(\\d{{2}})/);
          if (!m) return t;
          var d = new Date(+m[1], m[2]-1, +m[3], +m[4], +m[5]);
          var wd = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'][d.getDay()];
          var h = d.getHours(), ap = h >= 12 ? 'PM' : 'AM';
          return wd + ' ' + ((h % 12) || 12) + ':' + m[5] + ' ' + ap;
        }}
        function scrub() {{
          if (!MS.series || !MS.series.length) return;
          var i = Math.min(MS.series.length - 1,
                           Math.max(0, parseInt(tSlider.value, 10) || 0));
          var pt = MS.series[i];
          var lvl = pt.w;
          var burst = false;
          if (bToggle && bToggle.checked && pt.b && MS.potential != null) {{
            lvl = Math.max(lvl, MS.potential);
            burst = true;
          }}
          dSlider.value = String(lvl);
          if (thumbOn) drawThumb(i, lvl);
          tLabel.textContent = fmtT(pt.t)
            + (burst ? ' \u2014 BURST POTENTIAL' : '')
            + (pt.b && !burst ? ' (rain-risk hour)' : '');
          rerender();
        }}
        // CHART THUMBNAIL over the map corner (user 2026-07-20):
        // miniature of the near-term series + ladder lines + a ball
        // tracking the scrubber. Unlabeled by design.
        var thumbC = document.getElementById('map-thumb');
        var thumbBtn = document.getElementById('thumb-toggle');
        var thumbOn = false;
        try {{ thumbOn = localStorage.getItem('barnacle-map-thumb') === '1'; }} catch (e) {{}}
        function drawThumb(idx, lvl) {{
          if (!thumbC || !MS.series || !MS.series.length) return;
          var c = thumbC.getContext('2d');
          var W = thumbC.width, H = thumbC.height, P = 6;
          c.clearRect(0, 0, W, H);
          var ws = MS.series.map(function(p) {{ return p.w; }});
          var lo = Math.min.apply(null, ws.concat([3.5]));
          var hi = Math.max.apply(null, ws.concat([5.6, lvl || 0]));
          function X(i) {{ return P + (W - 2*P) * i / (MS.series.length - 1); }}
          function Y(v) {{ return H - P - (H - 2*P) * (v - lo) / (hi - lo); }}
          var LC = [[3.78, '#2f8f5f'], [4.16, '#c0392b'],
                    [4.66, '#7c4dbc'], [5.41, '#6d4c2f']];
          LC.forEach(function(l) {{
            if (l[0] > hi || l[0] < lo) return;
            c.strokeStyle = l[1]; c.lineWidth = 1;
            c.setLineDash([3, 3]);
            c.beginPath(); c.moveTo(P, Y(l[0])); c.lineTo(W - P, Y(l[0]));
            c.stroke();
          }});
          c.setLineDash([]);
          c.strokeStyle = '#1a5fa8'; c.lineWidth = 1.6;
          c.beginPath();
          MS.series.forEach(function(p, i) {{
            if (i === 0) c.moveTo(X(i), Y(p.w)); else c.lineTo(X(i), Y(p.w));
          }});
          c.stroke();
          if (idx != null) {{
            c.fillStyle = '#b91c1c';
            c.beginPath();
            c.arc(X(idx), Y(lvl != null ? lvl : MS.series[idx].w), 3.5, 0, 7);
            c.fill();
          }}
        }}
        function applyThumb() {{
          if (!thumbC) return;
          thumbC.style.display = thumbOn ? 'block' : 'none';
          if (thumbOn) {{
            var i = tSlider ? (parseInt(tSlider.value, 10) || 0) : null;
            drawThumb(i, null);
          }}
        }}
        if (thumbBtn) {{
          thumbBtn.addEventListener('click', function() {{
            thumbOn = !thumbOn;
            try {{ localStorage.setItem('barnacle-map-thumb', thumbOn ? '1' : '0'); }} catch (e) {{}}
            applyThumb();
          }});
        }}
        var _scrubPending = false;
        function scrubThrottled() {{
          if (_scrubPending) return;
          _scrubPending = true;
          requestAnimationFrame(function() {{
            _scrubPending = false;
            scrub();
          }});
        }}
        if (tSlider) {{
          // start the scrubber at "now" (first future point)
          var nowMs = Date.now();
          var startI = 0;
          for (var i = 0; i < MS.series.length; i++) {{
            var mm = MS.series[i].t.match(/(\\d{{4}})-(\\d{{2}})-(\\d{{2}}) (\\d{{2}}):(\\d{{2}})/);
            if (mm && new Date(+mm[1], mm[2]-1, +mm[3], +mm[4], +mm[5]).getTime() >= nowMs) {{
              startI = i; break;
            }}
          }}
          tSlider.value = String(startI);
          tSlider.addEventListener('input', scrubThrottled);
          if (bToggle) bToggle.addEventListener('change', scrub);
        }}
        applyThumb();
        dBtn.addEventListener('click', function() {{
          // full reset: level to the live forecast, scrubber back to
          // now, burst view off (2026-07-20 — snap left the time
          // slider stranded; also the old 3.0 floor clamped a ~2.5
          // forecast level so the thumb never visibly moved).
          dSlider.value = String(defaultWater);
          var tS = document.getElementById('time-slider-input');
          var tL = document.getElementById('time-slider-value');
          var bT = document.getElementById('burst-potential-toggle');
          if (bT) bT.checked = false;
          if (tS && typeof startI !== 'undefined') tS.value = String(startI);
          if (tL) tL.textContent = 'now';
          rerender();
        }});
        rBtn.addEventListener('click', function() {{
          rSlider.value = '0';
          rerender();
        }});
      }})();
"""

    shading_html = """
    <div class="heatmap-toggle shading-toggle">
      <span class="note">Shading:</span>
      <label><input type="radio" name="heatmap-shading" value="bands"
        checked> depth bands (labeled, Sandy-ready)</label>
      <label><input type="radio" name="heatmap-shading" value="classic">
        classic blue (saturates at 2&nbsp;ft)</label>
    </div>"""
    shading_script = """
      (function() {
        var style = 'bands';
        try { style = localStorage.getItem('barnacle-map-shading') || 'bands'; } catch (e) {}
        window.barnacleMapStyle = style;
        var radios = document.querySelectorAll('input[name="heatmap-shading"]');
        radios.forEach(function(r) {
          r.checked = (r.value === style);
          r.addEventListener('change', function() {
            window.barnacleMapStyle = r.value;
            try { localStorage.setItem('barnacle-map-shading', r.value); } catch (e) {}
            if (window.barnacleRerender) window.barnacleRerender();
            if (window.barnacleRenderAll) window.barnacleRenderAll();
          });
        });
      })();"""
    return f"""
  <section class="{container_class}">
    <{hh}>Predicted water depth (worst tide)</{hh}>
    {intro_note}{toggle_html}{shading_html}
    <div class="map-wrap" style="position:relative">
      <canvas id="heatmap-canvas" style="{canvas_styles}"></canvas>
      <button type="button" id="thumb-toggle" title="show position on the water-level chart"
              style="position:absolute;top:8px;left:8px;font-size:15px;
                     padding:2px 7px;border:1px solid #999;border-radius:5px;
                     background:rgba(255,255,255,0.9);cursor:pointer">&#128200;</button>
      <canvas id="map-thumb" width="190" height="95"
              style="position:absolute;top:40px;left:8px;display:none;
                     background:rgba(255,255,255,0.88);border:1px solid #999;
                     border-radius:5px"></canvas>
    </div>{second_canvas_html}
    {slider_html}
    <script>
      window.barnaclePoints = {points_json};
    </script>
    <script src="https://cdn.jsdelivr.net/npm/d3-delaunay@6"></script>
    <script src="{_relpath_to_map_render_js(base_map_url)}"></script>
    <script>
      {shading_script}
      window.barnacleRenderAll = function() {{
      {script_render}
      }};
      window.barnacleRenderAll();
      {toggle_script}{slider_script}
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


def _render_equation_widget_html(forecast, wrapper="section"):
    """Interactive widget that shows the v0.6 model equation with the
    current forecast's term values filled in. Every term is an editable
    number input; the water level and the depth at a chosen landmark
    recompute live. A 'snap back' button restores the forecast values.

    The math here mirrors predict_landmark_depths() exactly:
        water_navd88 = SH_peak_mllw + local_enhancement + datum_offset
        rain_add(in) = 8 * tanh(rate)   when rate > 0.1, else 0
        depth(in)    = max(0, water_navd88 - elev) * 12
                       + max(0, rain_add - shed[landmark])
    so the widget is a faithful calculator for the model, not a
    simplified illustration.
    """
    sh_peak = forecast.get("peak_forecast_observed_mllw", 0.0) or 0.0
    rain_rate = forecast.get("peak_rain_rate_in_hr", 0.0) or 0.0

    # Rain-pathway interactive calculator (v0.9-gamma): embed the
    # stage-storage curve + fitted constants so the client mirrors
    # estimate_pluvial_water() exactly, step by step.
    _curve = _load_stage_curve()
    pluv_calc_html = ""
    if _curve and PLUVIAL_VOLUME_K and PLUVIAL_POW_K:
        _v76 = _curve_fill_volume(_curve, 0.0, 15.4)
        _pr = forecast.get("pluvial_risk") or {}
        _rate_default = _pr.get("burst_est_in_hr") or 1.7
        _bay_default = 2.5
        _curve_js = json.dumps([[c[0], round(c[1], 1)] for c in _curve])
        pluv_calc_html = f"""
    <div class="eqn-line">
      <span class="eqn-lhs">Rain burst</span>
      <input type="number" id="pv-rate" step="0.05" min="0" max="6"
             value="{_rate_default:.2f}" data-default="{_rate_default:.4f}">
      <span class="eqn-termname">in/hr &mdash; effective sustained rate</span>
    </div>
    <div class="eqn-line">
      <span class="eqn-lhs">Bay level</span>
      <input type="number" id="pv-bay" step="0.05" min="2.0" max="5.5"
             value="{_bay_default:.2f}" data-default="{_bay_default:.4f}">
      <span class="eqn-termname">ft NAVD88 &mdash; sets the base AND the
        drain capacity (grate tops = 3.52)</span>
    </div>
    <div class="eqn-result">
      &rarr; Drains absorb <b id="pv-drain">&mdash;</b> in/hr
      <span id="pv-drainnote" class="eqn-termname"></span><br>
      &rarr; Net rain filling the bowl = <b id="pv-net">&mdash;</b> in/hr<br>
      &rarr; Water volume &asymp; <b id="pv-volpow">&mdash;</b>&times;
      the 7/6 flood <span class="eqn-termname">(v0.10 tank steady-state;
      tanh: <span id="pv-voltanh">&mdash;</span>&times;)</span><br>
      &rarr; Street water: <b id="pv-outpow">&mdash;</b>
      <span class="eqn-termname">v0.10 tank (steady-state)</span> /
      <b id="pv-outtanh">&mdash;</b>
      <span class="eqn-termname">tanh (conservative)</span>
      <span id="pv-spreadnote" class="eqn-termname"></span>
    </div>
    <button type="button" id="pv-reset">Snap back to forecast burst</button>

    <script>
      (function() {{
        var CURVE = {_curve_js};
        var K_SS = {TANK_K / TANK_KOUT:.1f}, G_T = {TANK_GAMMA};
        var K_POW = {PLUVIAL_POW_K:.1f}, GAMMA = {PLUVIAL_POW_GAMMA:.4f};
        var V_K = {PLUVIAL_VOLUME_K:.1f}, V76 = {_v76:.1f};
        var DRAIN = {PLUVIAL_DRAIN_RATE}, KNEE = {PLUVIAL_DRAIN_FULL_BELOW};
        var BASE = {PLUVIAL_STREET_BASE}, SCALE = {PLUVIAL_FREE_RATE_SCALE};
        var GRATE = 3.52;
        var rIn = document.getElementById('pv-rate');
        var bIn = document.getElementById('pv-bay');
        if (!rIn || !bIn) return;
        function fillCurve(baseStage, budget) {{
          var stage = baseStage;
          for (var i = 1; i < CURVE.length; i++) {{
            var s = CURVE[i][0], a = CURVE[i][1];
            if (s <= baseStage) continue;
            var step = a * (s - CURVE[i-1][0]);
            if (budget < step) {{
              stage = a > 0 ? CURVE[i-1][0] + budget / a : s;
              budget = 0; break;
            }}
            budget -= step; stage = s;
          }}
          if (budget > 0 && CURVE[CURVE.length-1][1] > 0)
            stage += budget / CURVE[CURVE.length-1][1];
          return stage;
        }}
        function fmt(w) {{
          var inches = (w - GRATE) * 12;
          return w.toFixed(2) + ' ft NAVD88 ('
            + (inches >= 0 ? '+' : '') + inches.toFixed(1)
            + '\\u2033 vs SW grate)';
        }}
        function recompute() {{
          var rate = parseFloat(rIn.value) || 0;
          var bay = parseFloat(bIn.value) || 0;
          var base = Math.max(bay, BASE);
          var fracOpen = Math.min(1, Math.max(0,
            (BASE - bay) / (BASE - KNEE)));
          var drain = DRAIN * fracOpen;
          var net = rate - drain;
          document.getElementById('pv-drain').textContent =
            drain.toFixed(2);
          document.getElementById('pv-drainnote').textContent =
            fracOpen >= 1 ? '(outfall clear \\u2014 full capacity)'
            : fracOpen <= 0 ? '(bay at the grate tops \\u2014 outfall blocked)'
            : '(bay is backwatering the outfall \\u2014 '
              + Math.round(fracOpen * 100) + '% capacity)';
          var netEl = document.getElementById('pv-net');
          if (net <= 0) {{
            netEl.textContent = '0 (drains keep up)';
            document.getElementById('pv-volpow').textContent = '0';
            document.getElementById('pv-voltanh').textContent = '0';
            document.getElementById('pv-outpow').textContent = fmt(base);
            document.getElementById('pv-outtanh').textContent = fmt(base);
            document.getElementById('pv-spreadnote').textContent =
              '\\u2014 no rain lift; water = the tide-set base.';
            return;
          }}
          netEl.textContent = net.toFixed(2);
          var vPow = K_SS * Math.pow(net, G_T);   // v0.10 tank steady state
          var vTanh = V_K * Math.tanh(net / SCALE);
          document.getElementById('pv-volpow').textContent =
            (vPow / V76).toFixed(2);
          document.getElementById('pv-voltanh').textContent =
            (vTanh / V76).toFixed(2);
          var baseStage = Math.max(0, (base - BASE) * 12);
          var wPow = BASE + fillCurve(baseStage, vPow) / 12;
          var wTanh = BASE + fillCurve(baseStage, vTanh) / 12;
          document.getElementById('pv-outpow').textContent = fmt(wPow);
          document.getElementById('pv-outtanh').textContent = fmt(wTanh);
          var spread = Math.abs(wPow - wTanh) * 12;
          document.getElementById('pv-spreadnote').textContent =
            spread < 0.5
              ? '\\u2014 the two models agree here (calibrated range).'
              : '\\u2014 models differ by ' + spread.toFixed(1)
                + '\\u2033: extrapolation territory; the spread is the '
                + 'honest uncertainty.';
        }}
        rIn.addEventListener('input', recompute);
        bIn.addEventListener('input', recompute);
        document.getElementById('pv-reset')
          .addEventListener('click', function() {{
            rIn.value = rIn.getAttribute('data-default');
            bIn.value = bIn.getAttribute('data-default');
            recompute();
          }});
        recompute();
      }})();
    </script>
"""

    # v0.7 single-water-level math: rain adds to a shared water level,
    # not per-landmark with shedding constants. Each landmark's `shed`
    # is 0 — kept in the JS API for backwards compatibility with the
    # widget's render path.
    landmarks_js = json.dumps([
        {"key": key, "label": label, "elev": elev, "shed": 0.0}
        for key, label, elev, _sh in LANDMARKS
    ])

    hh = "h2" if wrapper == "section" else "h3"
    open_tag = f'<section class="eqn-widget">' if wrapper == "section" else \
               '<div class="eqn-widget">'
    close_tag = "</section>" if wrapper == "section" else "</div>"

    return f"""
  {open_tag}
    <{hh}>The model, term by term</{hh}>
    <p class="note">This is the actual {CURRENT_MODEL_VERSION} <b>tide-keyed</b>
       prediction math with this forecast's numbers filled in — the
       calculation behind the per-tide table, alerts, and heat-map.
       Edit any term to see how the prediction would change — then
       "Snap back" to return to the live forecast. (Rain-driven street
       water is a separate pathway; see "The rain pathway" below the
       glossary.)</p>

    <div class="eqn-line">
      <span class="eqn-lhs">Water level (NAVD88) =</span>
      <input type="number" id="eq-shpeak" step="0.01"
             value="{sh_peak:.2f}" data-default="{sh_peak:.4f}">
      <span class="eqn-termname">ft &mdash; Sandy Hook peak (MLLW)</span>
    </div>
    <div class="eqn-line">
      <span class="eqn-op">+</span>
      <input type="number" id="eq-enh" step="0.01"
             value="{LOCAL_ENHANCEMENT_FT:.2f}"
             data-default="{LOCAL_ENHANCEMENT_FT:.4f}">
      <span class="eqn-termname">ft &mdash; local enhancement</span>
    </div>
    <div class="eqn-line">
      <span class="eqn-op">+</span>
      <input type="number" id="eq-datum" step="0.01"
             value="{MLLW_TO_NAVD88_OFFSET:.2f}"
             data-default="{MLLW_TO_NAVD88_OFFSET:.4f}">
      <span class="eqn-termname">ft &mdash; MLLW&rarr;NAVD88 datum offset</span>
    </div>
    <div class="eqn-result">
      &rarr; Water level = <b id="eq-water">&mdash;</b> ft NAVD88
    </div>

    <div class="eqn-line">
      <span class="eqn-lhs">Depth at</span>
      <select id="eq-landmark"></select>
      <span class="eqn-termname">= max(0, water &minus; elevation) &times; 12
        + rain</span>
    </div>
    <div class="eqn-line">
      <span class="eqn-lhs">Peak rain</span>
      <input type="number" id="eq-rain" step="0.05" min="0"
             value="{rain_rate:.2f}" data-default="{rain_rate:.4f}">
      <span class="eqn-termname">in/hr &mdash; adds
        <b id="eq-rainadd">&mdash;</b>&Prime; of depth
        (<span id="eq-rainnote"></span>)</span>
    </div>
    <div class="eqn-result">
      &rarr; Depth at <span id="eq-lmname">&mdash;</span> =
      <b id="eq-depth">&mdash;</b>&Prime;
      <span class="eqn-regime" id="eq-regime"></span>
    </div>

    <button type="button" id="eq-reset">Snap back to current forecast</button>

    <h3 class="eqn-sub">What each term means</h3>
    <dl class="eqn-glossary">
      <dt>Sandy Hook peak (MLLW)</dt>
      <dd>The forecast peak water height at the NOAA Sandy Hook gauge
        (station 8531680) for the worst high tide in the next 24 hours,
        in feet above Mean Lower Low Water. This is the live input that
        changes tide to tide &mdash; it already folds in the astronomical
        tide plus any storm surge.</dd>
      <dt>Local enhancement ({LOCAL_ENHANCEMENT_FT:+.2f} ft)</dt>
      <dd>The residual after the datum conversion: how much water at
        342 Bay differs from what the SH gauge reads. v0.8+ sets this
        to <b>0.00 ft</b> — the conservative value from 4 tape-measured
        spot-check events (SH 6.17–7.29). Regular tides with offshore
        peak winds run ~0.13 ft lower; the wind-adjustment line in the
        worst-case detail reports that "expected actual" separately.
        (The v0.6 constant +0.40 was over-fit to memory-based
        observations that pre-dated the spot-check protocol.)</dd>
      <dt>MLLW&rarr;NAVD88 offset (&minus;2.82 ft)</dt>
      <dd>A pure datum conversion. The gauge reports heights in MLLW;
        the landmark elevations at the house were surveyed in NAVD88.
        This is fixed geometry, not a tunable model parameter.</dd>
      <dt>Peak rain (in/hr)</dt>
      <dd>The heaviest single hour of rainfall the NWS forecasts in
        the window [-90 min, +15 min] around the high tide (v0.7
        before-biased window — rain after the peak can't raise the
        peak). In this tide-keyed calculation rain adds depth through
        a saturating curve, 8&middot;tanh(rate) inches, applied as a
        uniform water-level rise above 0.1 in/hr — a legacy
        approximation kept because it fits the compound events. The
        rain <i>pathway</i> below is the modern treatment.</dd>
    </dl>
    <p class="note">The tide-keyed model in one sentence: convert the
       gauge's tide forecast to a water level at the house (first
       three terms), then at each landmark the depth is simply how far
       that water level sits above the landmark's surveyed elevation,
       with a rain term added on top. The per-tide table, alerts, and
       heat-map are this one calculation applied at different
       points.</p>

    <h3 class="eqn-sub">The rain pathway (v0.10) — how the rain
      line, burst band, and scenario depths are computed</h3>
    <p class="note">Rain-driven street water is <b>volume</b>-driven,
       not level-driven (the bay is effectively infinite; rain is a
       finite source). The pipeline: (1) drains absorb the first
       0.25 in/hr, a capacity that shrinks to zero as the bay rises
       from 3.0 to 3.52 ft NAVD88 and blocks the outfall
       (head-dependent drainage); (2) the surviving net rain rate
       feeds the <b>v0.10 dynamic tank</b> — dV/dt = K&middot;rate
       <sup>0.70</sup> &minus; k&middot;V — whose output volume
       fills the measured stage-storage curve upward from whatever
       level the tide has set (each additional inch needs more
       volume because the pool widens). On the 24-h chart this runs
       as a true <b>hydrograph</b>: rise (~14-min hillside lag),
       peak, and ~20-min drain-down. The calculator below shows the
       tank's <b>steady state</b> (the level a sustained rate holds,
       reached within ~1&nbsp;h), bracketed against the saturating
       <b>tanh</b> alternative (a conservative floor — the 7/9 flood
       exceeded it). Calibration: ONE parameter set fits all four
       measured floods — 7/6 and 7/9/2026 (full measured
       hydrographs), Oct 30 2025 (compound), Dec 19 2025 (moderate)
       — all with MRMS-radar-measured rain forcing.</p>
{pluv_calc_html}
    <script>
      (function() {{
        var L = {landmarks_js};
        var ids = ['eq-shpeak','eq-enh','eq-datum','eq-rain'];
        var sel = document.getElementById('eq-landmark');
        if (!sel) return;
        for (var i = 0; i < L.length; i++) {{
          var o = document.createElement('option');
          o.value = String(i);
          o.textContent = L[i].label;
          sel.appendChild(o);
        }}
        // Default to the SW grate — the project's reference point
        // (all relative depths are quoted vs the SW grate; it is the
        // first landmark to wet). Regime is still computed at the
        // curb below, where the thresholds are defined.
        for (var i = 0; i < L.length; i++) {{
          if (L[i].key === 'grate_SW') {{ sel.value = String(i); break; }}
        }}
        var curbElev = 4.16;
        for (var i = 0; i < L.length; i++) {{
          if (L[i].key === 'curb') {{ curbElev = L[i].elev; }}
        }}
        function num(id) {{
          return parseFloat(document.getElementById(id).value) || 0;
        }}
        function recompute() {{
          var shpeak = num('eq-shpeak');
          var enh    = num('eq-enh');
          var datum  = num('eq-datum');
          var rate   = num('eq-rain');
          var water  = shpeak + enh + datum;
          var rainAdd = (rate > 0.1) ? 8.0 * Math.tanh(rate) : 0.0;
          var lm = L[parseInt(sel.value, 10) || 0];
          var rainHere = Math.max(0, rainAdd - lm.shed);
          var depth = Math.max(0, water - lm.elev) * 12 + rainHere;
          document.getElementById('eq-water').textContent =
            water.toFixed(2);
          document.getElementById('eq-rainadd').textContent =
            rainAdd.toFixed(1);
          document.getElementById('eq-rainnote').textContent =
            (rate > 0.1)
              ? (lm.shed > 0
                  ? lm.label + ' sheds ' + lm.shed.toFixed(0)
                    + '\\u2033 \\u2192 +' + rainHere.toFixed(1) + '\\u2033 here'
                  : 'no shedding here')
              : 'below the 0.1 in/hr threshold';
          document.getElementById('eq-lmname').textContent = lm.label;
          document.getElementById('eq-depth').textContent =
            depth.toFixed(1);
          // Regime thresholds are DEFINED at the curb top — compute
          // there regardless of which landmark the depth readout uses
          // (fix 2026-07-07: the regime previously followed the
          // selected landmark, mislabeling sub-curb depths).
          var curbDepth = Math.max(0, water - curbElev) * 12 + rainHere;
          var regime = '';
          if (curbDepth >= 8)      regime = 'severe';
          else if (curbDepth >= 4) regime = 'moderate';
          else if (curbDepth > 0)  regime = 'light';
          else                     regime = 'dry';
          var rEl = document.getElementById('eq-regime');
          // 'dry' is the internal key; display as 'no flooding'
          rEl.textContent = '(regime at curb: '
            + (regime === 'dry' ? 'no flooding' : regime) + ')';
          rEl.className = 'eqn-regime regime-' + regime;
        }}
        ids.forEach(function(id) {{
          document.getElementById(id)
            .addEventListener('input', recompute);
        }});
        sel.addEventListener('change', recompute);
        document.getElementById('eq-reset')
          .addEventListener('click', function() {{
            ids.forEach(function(id) {{
              var el = document.getElementById(id);
              el.value = el.getAttribute('data-default');
            }});
            for (var i = 0; i < L.length; i++) {{
              if (L[i].key === 'grate_SW') {{ sel.value = String(i); break; }}
            }}
            recompute();
          }});
        recompute();
      }})();
    </script>
  {close_tag}
"""


def _per_tide_log_stats(target_tide_time):
    """Quick stats about predictions_log.csv slice for one tide.
    Returns dict with n, first_at, last_at, span_hours, avg_cadence_min.
    HANDOFF observability — CC in the 2026-05-19 solo-work backlog.

    Returns None when no rows match (e.g., tide just rolled into the
    window and the log hasn't ticked yet)."""
    if not os.path.exists(PREDICTIONS_LOG_PATH):
        return None
    times = []
    try:
        with open(PREDICTIONS_LOG_PATH) as f:
            for r in csv.DictReader(f):
                if r.get("target_tide_time") == target_tide_time:
                    pred_at = r.get("prediction_made_at", "")
                    if pred_at:
                        times.append(pred_at)
    except OSError:
        return None
    if not times:
        return None
    times.sort()
    n = len(times)
    first_at = times[0]
    last_at = times[-1]
    span_hours = None
    avg_cadence_min = None
    try:
        first_dt = dt.datetime.strptime(first_at, "%Y-%m-%dT%H:%M:%SZ")
        last_dt = dt.datetime.strptime(last_at, "%Y-%m-%dT%H:%M:%SZ")
        span_seconds = (last_dt - first_dt).total_seconds()
        span_hours = span_seconds / 3600.0
        if n > 1 and span_seconds > 0:
            avg_cadence_min = span_seconds / (n - 1) / 60.0
    except (ValueError, TypeError):
        pass
    return {
        "n":               n,
        "first_at":        first_at,
        "last_at":         last_at,
        "span_hours":      span_hours,
        "avg_cadence_min": avg_cadence_min,
    }


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
    # Build (slug, time) for every tide first so we can pass prev/next
    # context into the renderer (HANDOFF 9b.2 — per-tide nav, "T").
    all_tides_in_order = forecast.get("all_tides") or []
    slugs = [(t, _tide_slug(t.get("time", ""))) for t in all_tides_in_order]
    slugs = [(t, s) for (t, s) in slugs if s]
    for i, (tide, slug) in enumerate(slugs):
        prev_slug = slugs[i - 1][1] if i > 0 else None
        next_slug = slugs[i + 1][1] if i < len(slugs) - 1 else None
        prev_time = slugs[i - 1][0]["time"] if i > 0 else None
        next_time = slugs[i + 1][0]["time"] if i < len(slugs) - 1 else None
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
            f.write(render_per_tide_page(
                tide, forecast,
                prev_slug=prev_slug, prev_time=prev_time,
                next_slug=next_slug, next_time=next_time,
            ))
        n_written += 1

    if n_written:
        print(f"Wrote {n_written} per-tide page(s) under {tides_root}")

    # Tides archive index — lists all past + upcoming per-tide pages so
    # they're discoverable from the home page. User asked 2026-05-19:
    # "Do we have retrospective plots for per-tides pages too? i.e.
    # pages with plots from previous days?" Pages persist on disk
    # forever; this index makes them browseable.
    try:
        _write_tides_archive_index(tides_root)
    except Exception as e:
        print(f"WARNING: tides archive index write failed: {e}", flush=True)


def _write_tides_archive_index(tides_root):
    """Walk docs/tides/, build a chronological index of all per-tide
    pages, write to docs/tides/index.html. Grows monotonically as
    tides pass — old pages keep their content (heat-map for that tide's
    prediction + the per-tide evolution.csv + the convergence chart)."""
    if not os.path.isdir(tides_root):
        return
    entries = []
    for name in sorted(os.listdir(tides_root)):
        full = os.path.join(tides_root, name)
        if not os.path.isdir(full):
            continue
        fc_path = os.path.join(full, "forecast.json")
        if not os.path.exists(fc_path):
            continue
        try:
            with open(fc_path) as f:
                tide_fc = json.load(f)
        except Exception:
            continue
        entries.append({
            "slug":   name,
            "time":   tide_fc.get("time", name),
            "peak":   tide_fc.get("forecast_peak_mllw"),
            "regime": ((tide_fc.get("depths_in") or {}).get("regime") or ""),
        })
    if not entries:
        return
    # Most recent first
    entries.sort(key=lambda e: e["time"], reverse=True)
    now_local_str = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    rows = ""
    for e in entries:
        peak_str = (f"{e['peak']:.2f}" if e["peak"] is not None else "—")
        time_pretty = format_time_full(e["time"]) if e.get("time") else e["slug"]
        rows += (
            f'<tr class="tide-row regime-{e["regime"]}">'
            f'<td><a href="{e["slug"]}/">{time_pretty}</a></td>'
            f'<td>{peak_str}</td>'
            f'<td>{e["regime"]}</td>'
            f'</tr>'
        )
    html = f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Per-tide archive — Bay Ave Barnacle</title>
<link rel="stylesheet" href="../style.css">
</head>
<body>
<main>
  <header>
    <h1>Per-tide archive</h1>
    <p class="subtitle"><a href="../">&larr; Back to today's forecast</a></p>
    <p class="note">Every high tide the workflow has generated a page
       for. Old pages persist forever; their content (tide-specific
       heat-map + prediction-evolution slider + convergence chart) is
       a retrospective of how the forecast for that tide evolved.
       Latest at the top. Index regenerated each workflow run; last
       built {now_local_str} local.</p>
  </header>
  <section class="tides">
    <table class="tide-table">
      <thead><tr><th>Tide time</th><th>Forecast peak (ft MLLW)</th><th>Regime</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </section>
  <footer>
    <p><a href="https://github.com/JohnUrban/barnacle">Source code &amp; model</a></p>
  </footer>
</main>
</body>
</html>
"""
    out_path = os.path.join(tides_root, "index.html")
    with open(out_path, "w") as f:
        f.write(html)
    print(f"Wrote per-tide archive index → {out_path} ({len(entries)} tides)")


def render_per_tide_page(tide, forecast,
                          prev_slug=None, prev_time=None,
                          next_slug=None, next_time=None):
    """Render a single per-tide deep-link HTML page. Focuses on ONE tide:
    its predicted peak, surge breakdown, depths at landmarks, link to
    evolution.csv (the per-tide slice of the master predictions log).

    `prev_slug` / `next_slug` (with `prev_time` / `next_time` for the
    link labels) wire up "← prev tide / next tide →" navigation in the
    page header so users can walk through upcoming tides without going
    back to the home page (HANDOFF 9b.2 — "T" in the solo-work backlog).

    The page is at docs/tides/<slug>/index.html so it's two levels deep
    from the repo root — all asset paths get a "../../" prefix.

    HANDOFF 9b.2."""
    td = tide["depths_in"]
    regime = td["regime"]
    time_str = tide["time"]
    short, above_in, rel_in = landmark_summary(td, tide["forecast_peak_mllw"])

    # Prev / next tide navigation (HANDOFF 9b.2 — "T" in solo backlog).
    prev_link = (
        f'<a href="../{prev_slug}/">&larr; {format_time_full(prev_time)}</a>'
        if prev_slug and prev_time else '<span class="nav-disabled">&larr; —</span>'
    )
    next_link = (
        f'<a href="../{next_slug}/">{format_time_full(next_time)} &rarr;</a>'
        if next_slug and next_time else '<span class="nav-disabled">— &rarr;</span>'
    )

    # Prediction-log status (CC — observability). Tells the reader how
    # much data this tide has accumulated and at what cadence.
    log_stats = _per_tide_log_stats(time_str)
    if log_stats:
        n = log_stats["n"]
        span = log_stats["span_hours"]
        cadence = log_stats["avg_cadence_min"]
        bits = [f"<b>{n}</b> prediction{'s' if n != 1 else ''} logged"]
        if span is not None:
            bits.append(f"over {span:.1f} h")
        if cadence is not None:
            bits.append(f"({cadence:.0f} min cadence avg)")
        log_status_html = (
            '<section class="log-status">'
            '<p class="note">' + " ".join(bits) +
            ' for this tide so far. Updates as the hourly workflow ticks.</p>'
            '</section>'
        )
    else:
        log_status_html = (
            '<section class="log-status">'
            '<p class="note">No predictions logged yet for this tide. '
            'Rows accumulate as the hourly workflow runs leading up to '
            'the peak.</p>'
            '</section>'
        )

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
<meta name="description" content="Bay Ave Barnacle — high tide at {format_time_full(time_str)}: {regime_display(regime).upper()} regime, peak {tide['forecast_peak_mllw']:.2f} ft MLLW Sandy Hook.">
<!-- Open Graph — W -->
<meta property="og:title" content="High tide {format_time_full(time_str)} — Bay Ave Barnacle">
<meta property="og:description" content="{regime_display(regime).upper()} regime. Forecast peak {tide['forecast_peak_mllw']:.2f} ft MLLW Sandy Hook.">
<meta property="og:image" content="https://johnurban.github.io/barnacle/icons/icon-512.png">
<meta property="og:type" content="website">
<meta name="twitter:card" content="summary">
</head>
<body>
<main>
  <header>
    <h1>High tide @ {format_time_full(time_str)}</h1>
    <p class="subtitle"><a href="../../">&larr; Back to today's forecast</a></p>
    <nav class="tide-nav">
      <span class="tide-nav-prev">{prev_link}</span>
      <span class="tide-nav-next">{next_link}</span>
    </nav>
  </header>

  <section class="regime regime-{regime}">
    <div class="regime-label">{regime_display(regime).upper()}</div>
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

{log_status_html}
{tide_heatmap_section}
  <section class="scrubber-section">
    <h2>Replay forecast evolution</h2>
    <p class="note">Scrub through past predictions for this tide and see
       how the heat-map (above) would have looked at each point. Loads
       <a href="evolution.csv">evolution.csv</a> — HANDOFF 9b.4(c).</p>
    <div class="scrubber-controls">
      <button type="button" id="scrubber-play" aria-label="Play / pause">▶︎ Play</button>
      <input type="range" id="scrubber-range" min="0" max="0" value="0" step="1" disabled>
      <span id="scrubber-label" class="scrubber-label">Loading…</span>
    </div>
    <script>
      (function() {{
        var btn = document.getElementById('scrubber-play');
        var range = document.getElementById('scrubber-range');
        var label = document.getElementById('scrubber-label');
        var canvas = document.getElementById('heatmap-canvas');
        if (!canvas) {{
          label.textContent = '(no heat-map to scrub)';
          return;
        }}
        var rows = [];
        var playing = false;
        var playTimer = null;
        function fmtTime(iso) {{
          // iso like "2026-05-19T16:26:29Z"
          var d = new Date(iso);
          if (isNaN(d.getTime())) return iso;
          return d.toLocaleString(undefined, {{
            month: 'numeric', day: 'numeric',
            hour: 'numeric', minute: '2-digit'
          }});
        }}
        function showStep(i) {{
          var r = rows[i];
          if (!r) return;
          var hu = parseFloat(r.hours_until_peak);
          var huTxt = isNaN(hu) ? '' : (
            ' (' + Math.abs(hu).toFixed(1) + ' h '
            + (hu >= 0 ? 'before' : 'after') + ' peak)'
          );
          label.textContent = 'Predicted at ' + fmtTime(r.prediction_made_at) +
            huTxt + ' — water ' +
            parseFloat(r.water_navd88_predicted).toFixed(2) + ' ft NAVD88';
          if (typeof BarnacleMap !== 'undefined') {{
            BarnacleMap.render({{
              canvas: canvas,
              points: window.barnaclePoints,
              waterNavd88: parseFloat(r.water_navd88_predicted),
              style: window.barnacleMapStyle || 'bands',
              baseMapUrl: '../../icons/map_raw.png',
              title: 'As predicted at ' + fmtTime(r.prediction_made_at),
            }});
          }}
          // FF — link the views: highlight the matching point on the
          // convergence chart. Match by hours_until_peak (same source
          // field both use). Guarded for the case where the chart's
          // script hasn't run yet (initial page load order).
          if (window.convergenceChart && window.convergencePoints) {{
            var hu = parseFloat(r.hours_until_peak);
            var matchIdx = -1;
            for (var j = 0; j < window.convergencePoints.length; j++) {{
              if (Math.abs(window.convergencePoints[j].hours_until_peak - hu)
                  < 0.01) {{
                matchIdx = j;
                break;
              }}
            }}
            if (matchIdx >= 0) {{
              window.convergenceChart.setActiveElements([
                {{datasetIndex: 0, index: matchIdx}}
              ]);
              window.convergenceChart.update('none');
            }} else {{
              window.convergenceChart.setActiveElements([]);
              window.convergenceChart.update('none');
            }}
          }}
        }}
        function setPlaying(p) {{
          playing = p;
          btn.textContent = playing ? '⏸ Pause' : '▶︎ Play';
          if (playing) {{
            playTimer = setInterval(function() {{
              var next = parseInt(range.value, 10) + 1;
              if (next > parseInt(range.max, 10)) next = 0;
              range.value = next;
              showStep(next);
            }}, 800);
          }} else if (playTimer) {{
            clearInterval(playTimer);
            playTimer = null;
          }}
        }}
        btn.addEventListener('click', function() {{
          if (rows.length < 2) return;
          setPlaying(!playing);
        }});
        range.addEventListener('input', function() {{
          if (playing) setPlaying(false);
          showStep(parseInt(range.value, 10));
        }});
        fetch('evolution.csv').then(function(r) {{
          if (!r.ok) throw new Error('no evolution.csv yet');
          return r.text();
        }}).then(function(text) {{
          var lines = text.trim().split('\\n');
          if (lines.length < 2) {{
            label.textContent = 'No prediction history yet. Fills in '
              + 'as the hourly workflow logs predictions.';
            return;
          }}
          var headers = lines[0].split(',');
          var idx = {{}};
          headers.forEach(function(h, i) {{ idx[h] = i; }});
          for (var i = 1; i < lines.length; i++) {{
            var cols = lines[i].split(',');
            rows.push({{
              prediction_made_at: cols[idx['prediction_made_at']],
              target_tide_time:   cols[idx['target_tide_time']],
              hours_until_peak:   cols[idx['hours_until_peak']],
              sh_peak_mllw_predicted:
                cols[idx['sh_peak_mllw_predicted']],
              water_navd88_predicted:
                cols[idx['water_navd88_predicted']],
            }});
          }}
          if (rows.length < 2) {{
            label.textContent = 'Only one prediction logged so far. '
              + 'Slider unlocks at ≥2 predictions.';
            return;
          }}
          range.disabled = false;
          range.min = '0';
          range.max = String(rows.length - 1);
          range.value = String(rows.length - 1);  // start at the latest
          showStep(rows.length - 1);
        }}).catch(function(e) {{
          label.textContent = 'No evolution data yet (' + e.message + ').';
        }});
      }})();
    </script>
  </section>

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
            points.push({{ x: -hu, y: sh, water: wat, conf: conf, hours_until_peak: hu }});
          }}
          points.sort(function(a, b) {{ return a.x - b.x; }});
          if (points.length < 2) {{
            note.textContent = 'Only one prediction logged so far for this tide. '
              + 'The convergence curve will appear after the next workflow run.';
          }} else {{
            note.textContent = points.length + ' predictions logged. '
              + 'Convergence pattern reveals how the forecast settles as the tide approaches.';
          }}
          // Expose the parsed points so the scrubber can find the
          // index matching a given prediction_made_at (FF).
          window.convergencePoints = points;
          var ctx = document.getElementById('convergence-chart').getContext('2d');
          // Expose for the scrubber to highlight the active point (FF —
          // link the three interactive views on per-tide pages)
          window.convergenceChart = new Chart(ctx, {{
            type: 'line',
            data: {{
              datasets: [{{
                label: 'Predicted SH peak (ft MLLW)',
                data: points,
                borderColor: 'rgba(31, 111, 235, 0.9)',
                backgroundColor: 'rgba(31, 111, 235, 0.15)',
                pointRadius: 4,
                pointHoverRadius: 6,
                pointHoverBackgroundColor: 'rgba(217, 119, 6, 1)',
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


def render_html_page(forecast):
    """
    Standalone HTML page for GitHub Pages publication.
    Like the email HTML but with proper <head>, mobile meta, and footer
    links to source repo + archive.

    The heat-map is rendered CLIENT-SIDE (HANDOFF 9b.10) from the
    static map_points.csv data and the current water level — no
    pre-rendered PNG needed.
    """
    d = forecast["depths_in"]
    regime = d["regime"]
    # Headline resolves the "NO FLOODING" vs "RAIN FLOOD RISK"
    # contradiction (2026-07-07): rain risk takes the banner when the
    # tide-derived regime is dry.
    # 72-h strip + subject legitimately own tomorrow's risk — the
    # today-gate applies only to the TODAY box (2026-07-20: the strip
    # read "NO FLOODING ... rain risk begins tomorrow", contradicting
    # itself; window scope resolves it to "POSSIBLE RAIN FLOODING —
    # no tidal flooding expected, but ... begins TOMORROW").
    headline_text, headline_class = headline_for(forecast, regime,
                                                 scope="window")
    # TODAY-first banner (user 2026-07-09, matching the widget's
    # 2026-07-06 redesign): today's regime + rain risk is the top
    # banner; the worst-72h tide becomes a labeled secondary strip.
    _today_regime = forecast.get("today_regime") or regime
    today_headline, today_class = headline_for(forecast, _today_regime)
    _t_rel = forecast.get("today_rel_grate_sw_in")
    _t_time = forecast.get("today_peak_time") or ""
    today_summary = ""
    if _t_rel is not None:
        today_summary = (f"Tide peak today {_t_rel:+.1f}&Prime; vs SW grate"
                         + (f" at {_t_time[-5:]}" if _t_time else "") + ".")
    _lb = forecast.get("today_lookback")
    lookback_html = ""
    if _lb and (_lb.get("rel_grate_in") or 0) > 0:
        _lb_reg = regime_display(_lb.get("regime") or "").upper()
        lookback_html = (
            f'\n    <div class="regime-summary" style="margin-top:6px;'
            f'border-top:1px solid rgba(0,0,0,0.12);padding-top:6px">'
            f'<b>SO FAR TODAY:</b> {_lb_reg} — peak water '
            f'{_lb["rel_grate_in"]:+.1f}&Prime; vs SW grate at '
            f'{_lb["time_local"]}, {_lb["source"]}.</div>')
    _pr_b = forecast.get("pluvial_risk") or {}
    rain_later_note = ""
    if _pr_b.get("level"):
        _alerts_b = _pr_b.get("nws_flood_alerts") or []
        _alert_names = ", ".join(a.get("event", "") for a in _alerts_b)
        _pot_txt = ""
        if _pr_b.get("potential_low_tide_navd88"):
            _pot_txt = (f"; a burst could bring street water to "
                        f"~{(_pr_b['potential_low_tide_navd88'] - 3.52) * 12:+.0f}&Prime; "
                        f"vs SW grate regardless of tide")
        if _pr_b.get("risk_today") is False:
            # risk belongs to TOMORROW — say so in the 72-h strip,
            # keep the TODAY box about today (2026-07-20 scope fix)
            _on = ""
            for _a in _alerts_b:
                if _a.get("onset"):
                    _on = _a["onset"][11:16]
                    break
            try:
                _tmrw_wd = (_station_local_now()
                            + dt.timedelta(days=1)).strftime("%a")
            except Exception:
                _tmrw_wd = ""
            rain_later_note = (
                f" <b>Rain risk begins TOMORROW"
                + (f" ({_tmrw_wd})" if _tmrw_wd else "") + "</b>"
                + (f" ({_alert_names}" + (f" from {_on}" if _on else "")
                   + ")" if _alert_names else "")
                + _pot_txt + ".")
        else:
            today_summary += (
                " Rain risk is live today"
                + (" — " + _alert_names + " in effect" if _alert_names else "")
                + _pot_txt + ".")
    if headline_class == regime:
        headline_summary = f"{REGIME_GLOSSARY.get(regime, '')}."
    else:
        headline_summary = ("No tidal flooding expected, but heavy "
                            "rain could flood the intersection "
                            "independently of the tide — see the "
                            "rain-risk banner below.")
    headline_summary += rain_later_note
    try:
        _now_k = _station_local_now()
    except Exception:
        _now_k = dt.datetime.now()
    _kick_today = _now_k.strftime("%a %b ") + str(_now_k.day)
    _kick_end = (_now_k + dt.timedelta(hours=72)).strftime("%a")
    peak_t = forecast["peak_time_local"]
    peak_ft = forecast["peak_forecast_observed_mllw"]
    today = dt.date.today().isoformat()
    cold = forecast["cold_lockout"]
    all_tides = forecast.get("all_tides", [])

    # Heat-map section: client-side render (HANDOFF 9b.10) + interactive
    # depth slider (Batch 2 idea #1 follow-up, 2026-05-19).
    map_section = _client_map_section_html(
        forecast,
        container_class="heatmap",
        level=2,
        base_map_url="icons/map_raw.png",
        show_depth_slider=True,
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
        hfn_row = t.get("hours_from_now")
        is_past = hfn_row is not None and hfn_row < 0
        regime_class = f"regime-{td['regime']}"
        classes = ["tide-row", regime_class]
        if is_worst:
            classes.append("worst-tide")
        if is_past:
            classes.append("past-tide")
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
            f'<td>{regime_display(td["regime"])}</td>'
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
<meta name="description" content="Bay Ave Barnacle — {headline_text}. Worst-case tide peak {peak_ft:.2f} ft MLLW at {format_time_full(peak_t)}. Hyperlocal flood forecast for the Bay Ave &amp; Central Ave intersection, Highlands NJ (referenced to 342 Bay Ave).">
<!-- Open Graph (link previews) — W -->
<meta property="og:title" content="Bay Ave Barnacle — {headline_text}">
<meta property="og:description" content="Worst-case peak {peak_ft:.2f} ft MLLW at {format_time_full(peak_t)}. Hyperlocal flood forecast for the Bay Ave &amp; Central Ave intersection, Highlands NJ (referenced to 342 Bay Ave).">
<meta property="og:image" content="https://johnurban.github.io/barnacle/icons/icon-512.png">
<meta property="og:url" content="https://johnurban.github.io/barnacle/">
<meta property="og:type" content="website">
<meta name="twitter:card" content="summary">
</head>
<body>
<main>
  <header>
    <h1>Bay Ave Barnacle</h1>
    <p class="subtitle">Hyperlocal flood forecast for the intersection of Bay Ave &amp; Central Ave in Highlands NJ &mdash; water levels referenced to 342 Bay Ave</p>
    <p class="last-updated"
       data-generated-at="{dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}">
      <span id="last-updated-display">Last updated …</span>
    </p>
  </header>
  <!-- DD: workflow-health banner. Hidden by default; revealed by the
       script below when last-update age exceeds the stale threshold.
       Three tiers: <90 min fresh (no banner), 90 min - 3 h amber on
       the inline last-updated indicator only (V), >3 h red banner (DD),
       >24 h bright-red banner with a "Run workflow manually" note. -->
  <div class="health-alert" id="health-alert" style="display:none">
    <span class="health-alert-title">⚠ System update is delayed</span>
    <span class="health-alert-detail" id="health-alert-detail"></span>
  </div>
  <script>
    (function() {{
      var el = document.querySelector('.last-updated');
      var disp = document.getElementById('last-updated-display');
      var banner = document.getElementById('health-alert');
      var bDetail = document.getElementById('health-alert-detail');
      if (!el || !disp) return;
      var iso = el.getAttribute('data-generated-at');
      var gen = new Date(iso);
      if (isNaN(gen.getTime())) return;
      function update() {{
        var now = new Date();
        var diffSec = Math.max(0, Math.round((now - gen) / 1000));
        var ago;
        if (diffSec < 90) ago = diffSec + ' s ago';
        else if (diffSec < 3600) ago = Math.round(diffSec / 60) + ' min ago';
        else if (diffSec < 86400) ago = Math.round(diffSec / 3600) + ' h ago';
        else ago = Math.round(diffSec / 86400) + ' d ago';
        var local = gen.toLocaleString(undefined, {{
          month: 'numeric', day: 'numeric',
          hour: 'numeric', minute: '2-digit'
        }});
        disp.textContent = 'Last updated ' + local + ' (' + ago + ')';
        // V: amber inline indicator at >2h
        if (diffSec > 7200) disp.classList.add('stale');
        else disp.classList.remove('stale');
        // DD: prominent banner at >3h, severe variant at >24h
        if (banner && bDetail) {{
          if (diffSec > 86400) {{
            banner.style.display = 'block';
            banner.classList.add('severe');
            bDetail.innerHTML = 'Last workflow run was <b>' + ago +
              '</b> (' + local + '). The hourly cron may have stalled. ' +
              '<a href="https://github.com/JohnUrban/barnacle/actions" target="_blank">' +
              'Run the workflow manually</a> to refresh.';
          }} else if (diffSec > 10800) {{
            banner.style.display = 'block';
            banner.classList.remove('severe');
            bDetail.innerHTML = 'Last workflow run was <b>' + ago +
              '</b> (' + local + '). Expected hourly; if this persists, ' +
              'the cron may have stalled.';
          }} else {{
            banner.style.display = 'none';
          }}
        }}
      }}
      update();
      setInterval(update, 30000);  // refresh "X ago" every 30s while open
    }})();
  </script>

  <div id="nowcast-strip" style="display:none"></div>
  <script>
    // LIVE RADAR NOWCAST strip (2026-07-17): renders docs/nowcast.json
    // client-side; the 10-min Action keeps that file fresh during
    // rain-capable weather. Hidden when inactive or >20 min stale.
    (function() {{
      var bust = Math.floor(Date.now() / 120000);
      fetch('nowcast.json?t=' + bust).then(function(r) {{
        return r.json();
      }}).then(function(nc) {{
        if (!nc || !nc.active || !nc.generated_utc) return;
        var age = (Date.now() - Date.parse(nc.generated_utc)) / 60000;
        if (age > 20) return;
        var el = document.getElementById('nowcast-strip');
        var reg = (nc.regime_now === 'dry') ? 'street water'
                  : nc.regime_now;
        el.innerHTML =
          '<section class="regime regime-severe" style="border:2px solid #b91c1c">' +
          '<div class="regime-kicker">&#128225; LIVE RADAR NOWCAST ' +
          '(as of ' + Math.round(age) + ' min ago)</div>' +
          '<div class="regime-label">' + reg.toUpperCase() + '</div>' +
          '<div class="regime-summary">Rain on the hillside now: ' +
          nc.recent_max_in_hr.toFixed(1) + ' in/hr (radar). Street ' +
          'water ≈ ' + (nc.street_now_in >= 0 ? '+' : '') +
          nc.street_now_in.toFixed(1) + '″ vs SW grate; ' +
          'projected peak ' + (nc.peak_proj_in >= 0 ? '+' : '') +
          nc.peak_proj_in.toFixed(1) + '″ around ' +
          nc.peak_proj_utc + ' UTC. Tank model on OBSERVED radar, ' +
          'not forecast.</div></section>';
        el.style.display = 'block';
        // HEADLINE OVERRIDE (2026-07-18, user during a live flood:
        // "the app should be actively saying FLOODING at the top").
        // When observed-radar street water is real, the TODAY label
        // becomes the live truth, not the QPF outlook.
        if (nc.street_now_in >= 1) {{
          // Target the TODAY block explicitly — the first '.regime'
          // in the DOM is this strip itself (bug caught by the user
          // MID-FLOOD: strip said FLOODING NOW while TODAY still
          // said the QPF outlook, "light", under crazy flooding).
          var tb = document.getElementById('today-block');
          if (tb) {{
            var lbl = tb.querySelector('.regime-label');
            var kick = tb.querySelector('.regime-kicker');
            var summ = tb.querySelector('.regime-summary');
            if (lbl) lbl.textContent = '\u26A0 FLOODING NOW \u2014 ' +
              reg.toUpperCase() + ' (+' +
              nc.street_now_in.toFixed(1) + '\u2033 and live)';
            if (kick) kick.textContent =
              'TODAY \u2014 HAPPENING NOW (live radar; QPF outlook superseded)';
            tb.className = 'regime regime-severe';
          }}
        }}
      }}).catch(function() {{}});
    }})();
  </script>

{_render_water_series_section(forecast)}

{_render_day_cards_html(forecast)}

{map_section}

  {_render_summary_html(forecast)}

{_render_flood_windows_html(forecast)}

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
       <b>Click any time in the first column</b> to open that tide's detail
       page (per-tide heat-map, prediction-evolution replay, convergence
       chart, full landmark table). <b>Above</b> = inches above the highest
       exceeded landmark (negative if water below the lowest landmark).
       <b>Rel</b> = inches above the lowest landmark (lowest road corner,
       3.64 NAVD88) — always. Surge persistence is increasingly unreliable
       for tides beyond ~24h out — use the longer windows for planning,
       not for trust. The most recent high tide stays visible (greyed
       out, marked "past") for {PAST_TIDE_VISIBILITY_HOURS} h after its
       peak so you can check whether it flooded before you head home.</p>
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
    <h2>Worst-case detail
      <a class="detail-link" href="tides/{_tide_slug(peak_t)}/">View this tide's full detail page →</a>
    </h2>
    <dl>
      <dt>High tide time</dt><dd>{peak_t}</dd>
      <dt>Predicted tide</dt><dd>{forecast['peak_predicted_mllw']:.2f} ft MLLW (Sandy Hook)</dd>
      <dt>Surge</dt><dd>{forecast['current_surge_ft']:+.2f} ft</dd>
      <dt>Forecast peak</dt><dd>{peak_ft:.2f} ft MLLW</dd>
      <dt>Surge source</dt><dd>{forecast['surge_source']} <span class="note">({forecast['nws_status']})</span></dd>
      <dt>Peak rainfall</dt><dd>{forecast['peak_rain_rate_in_hr']:.2f} in/hr</dd>
      <dt>72h mean temp</dt><dd>{forecast['temp_avg_72h_f']:.1f}&deg;F</dd>
      <dt>Cold conditions</dt><dd>{'<b>YES</b> — ice-lock hypothesis met; <i>no longer actively applied</i> (see <a href="https://github.com/JohnUrban/barnacle/blob/main/history/reports/cold_weather_retrospective.md">retrospective</a>)' if cold else 'no'}</dd>
    </dl>
{_render_wind_adjustment_html(forecast)}
    <p class="note">Per-tide detail pages live under <code>tides/&lt;date&gt;T&lt;HH-MM&gt;/</code>
       (one per upcoming high tide; click any time in the rollup table above
       to open one). They contain a tide-specific heat-map, a slider that
       replays the prediction history (drag through past predictions, see
       the heat-map redraw), and a convergence chart showing how the peak
       forecast for that tide evolved.</p>
  </section>
{_render_pluvial_advisory_html(forecast)}
{_render_cold_advisory_html(forecast)}

<section class="peaks-toggle-wrap">
    <div class="heatmap-toggle" id="peaks-view-toggle">
      <span class="note">Peaks view:</span>
      <label><input type="radio" name="peaks-view" value="all" checked>
        rain + tide (all pathways)</label>
      <label><input type="radio" name="peaks-view" value="tide">
        tide-only (per-tide, gauge)</label>
    </div>
    <div id="peaks-all">
{_render_flood_peaks_section(forecast)}
    </div>
    <div id="peaks-tide" style="display:none">
{_render_oscillation_section(forecast)}
    </div>
    <script>
      (function() {{
        var radios = document.querySelectorAll('input[name="peaks-view"]');
        var v = 'all';
        try {{ v = localStorage.getItem('barnacle-peaks-view') || 'all'; }} catch (e) {{}}
        function apply() {{
          document.getElementById('peaks-all').style.display =
            (v === 'all') ? 'block' : 'none';
          document.getElementById('peaks-tide').style.display =
            (v === 'tide') ? 'block' : 'none';
          // hidden Chart.js canvases render zero-size; nudge on reveal
          window.dispatchEvent(new Event('resize'));
        }}
        radios.forEach(function(r) {{
          r.checked = (r.value === v);
          r.addEventListener('change', function() {{
            v = r.value;
            try {{ localStorage.setItem('barnacle-peaks-view', v); }} catch (e) {{}}
            apply();
          }});
        }});
        apply();
      }})();
    </script>
  </section>
  {_render_rain_timing_html(forecast)}

  {_landmarks_section_html(forecast, wrapper='section', include_spot_check=False)}

{_render_live_gauge_section(forecast)}

  {_render_recent_history_html(forecast)}


  {_render_low_tides_html(forecast)}

  {_render_lookahead_html(forecast)}

{_render_more_info_links_html()}


  <footer>
    <p>Model {CURRENT_MODEL_VERSION} (pluvial: dynamic tank hydrograph —
       timing calibrated on two measured floods; scenarios = tank
       steady-state / tanh bracket; stage-storage fill,
       head-dependent drainage). Local enhancement
       {LOCAL_ENHANCEMENT_FT:+.2f} ft.
       Updated hourly (best-effort) via GitHub Actions.</p>
    <p><a href="https://github.com/JohnUrban/barnacle">Source code &amp; model</a> &middot;
       <a href="archive/">Past daily archives</a> &middot;
       <a href="tides/">Per-tide archive</a> &middot;
       <a href="barnacle-widget.js">iOS widget script (Scriptable)</a></p>
  </footer>
</main>
</body>
</html>
"""


def build_series_chart_png(forecast):
    """Compact PNG of the near-term water chart for the TOP of emails
    (user 2026-07-20: "the widget gives me everything in a glance...
    a snapshot of that graph should be the top of emails"). Mirrors
    the chart grammar: blue tide, amber tank hydrograph, gray
    observed past, navy burst band, landmark dashed lines, now-line.
    Returns PNG bytes or None (matplotlib missing / no series)."""
    series = forecast.get("water_series") or []
    if len(series) < 4:
        return None
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from io import BytesIO
    except Exception:
        return None
    def to_in(v):
        return None if v is None else (v - GRATE_SW) * 12
    t = list(range(len(series)))
    tide = [to_in(p.get("tide_navd88")) for p in series]
    pluv = [to_in(p.get("pluvial_navd88")) for p in series]
    obs = [to_in(p.get("observed_navd88")) for p in series]
    pr = forecast.get("pluvial_risk") or {}
    pots = [v for v in (pr.get("potential_low_tide_navd88"),
                        pr.get("potential_low_tide_navd88_tanh"))
            if v is not None]
    pot = to_in(max(pots)) if pots else None
    fig, ax = plt.subplots(figsize=(7.2, 2.9), dpi=110)
    for y, c, lbl in ((0, "#222222", "SW grate"),
                      (3.1, "#2f8f5f", "gutter"),
                      (7.7, "#c0392b", "curb"),
                      (13.7, "#7c4dbc", "lawn step")):
        ax.axhline(y, color=c, lw=0.9,
                   ls="-" if y == 0 else (0, (5, 4)), alpha=0.65)
        ax.text(len(series) - 0.5, y + 0.25, lbl, fontsize=6.5,
                color=c, ha="right")
    if pot is not None:
        flags = [bool(p.get("burst_risk")) for p in series]
        if not any(flags):
            flags = [True] * len(series)
        top = [max(pot, tv) if (f and tv is not None) else None
               for f, tv in zip(flags, tide)]
        bot = [tv if f else None for f, tv in zip(flags, tide)]
        ax.fill_between(t, [b if b is not None else 0 for b in bot],
                        [tp if tp is not None else 0 for tp in top],
                        where=[tp is not None for tp in top],
                        color="#0b3d6b", alpha=0.28, linewidth=0)
    ax.plot(t, tide, color="#1a5fa8", lw=1.8)
    if any(v is not None for v in pluv):
        ax.plot(t, pluv, color="#d97706", lw=1.8)
    if any(v is not None for v in obs):
        ax.plot(t, obs, color="#555555", lw=2.2)
        now_i = max(i for i, v in enumerate(obs) if v is not None)
        ax.axvline(now_i, color="#888888", lw=0.8, ls=":")
    ticks = [i for i, p in enumerate(series)
             if p["time"][-5:] in ("00:00", "06:00", "12:00", "18:00")]
    ax.set_xticks(ticks)
    labs = []
    for i in ticks:
        hh = series[i]["time"][-5:]
        if hh == "00:00":
            try:
                labs.append(dt.datetime.strptime(
                    series[i]["time"][:10], "%Y-%m-%d").strftime("%a"))
            except Exception:
                labs.append("12A")
        else:
            labs.append({"06:00": "6A", "12:00": "12P",
                         "18:00": "6P"}[hh])
    ax.set_xticklabels(labs, fontsize=7)
    ax.tick_params(axis="y", labelsize=7)
    ax.set_ylabel('in vs SW grate', fontsize=7.5)
    ax.grid(alpha=0.15)
    ax.set_title("Water at 342 Bay — observed (gray) → forecast",
                 fontsize=8.5)
    fig.tight_layout(pad=0.6)
    buf = BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return buf.getvalue()


def send_email(subject, text_body, html_body, inline_png=None):
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
    if html_body:
        if inline_png:
            html_body = html_body.replace(
                "<body>",
                '<body><img src="cid:chart" alt="water chart" '
                'style="width:100%;max-width:680px;display:block;'
                'margin:0 auto 10px auto">', 1)
        msg.add_alternative(html_body, subtype="html")
        if inline_png:
            msg.get_payload()[-1].add_related(
                inline_png, "image", "png", cid="<chart>")

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
    uniform water-level addition. v0.7 (2026-06-14) made this the
    canonical model formulation — both the heat-map and
    `predict_landmark_depths` now use water-is-level math, no per-
    landmark shedding.

    Rain term: `rain_add = 8 * tanh(rate)` inches, divided by 12 for
    feet. (v0.7 known limitation: this magnitude was co-fit with the
    old +0.40 enhancement; with the v0.7 -0.13 enhancement, rain-
    flood events will likely under-predict. v0.8 9d.2 will refit.)

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
    parser.add_argument("--force-email", action="store_true",
                        help="Send the report email regardless of the "
                             "event-driven alert state (manual/dispatch runs).")
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

    # Optionally render heat-map PNG(s) via assets/render_map.py
    # (matplotlib). This is purely a local convenience for the user's
    # workflow; the website (HTML page below) renders maps CLIENT-SIDE
    # (HANDOFF 9b.10) and does not consume these PNGs. Kept for a
    # future email-embed feature (HANDOFF 9b.5 — emails can't run JS).
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
            except Exception as e:
                print(f"WARNING: heat-map render failed: {e}", flush=True)

            # Second map: no-rain comparison (only when rain is meaningful)
            if rain_meaningful:
                water_no_rain = _compute_map_water_level(
                    forecast, include_rain=False
                )
                if water_no_rain is not None:
                    base, ext = os.path.splitext(out_path)
                    out_path_nr = base + "_no_rain" + ext
                    title_nr = (
                        f"Predicted water level — {water_no_rain:.2f} ft NAVD88 "
                        f"— TIDE ONLY (no rain bonus) — SH {peak_mllw:.2f} ft MLLW"
                    )
                    try:
                        _render_heatmap(out_path_nr, water_no_rain, title_nr)
                        print(f"Wrote heat-map (no rain): {out_path_nr}")
                    except Exception as e:
                        print(f"WARNING: no-rain heat-map render failed: {e}",
                              flush=True)

    subject, text, html = render_email(forecast)

    # Write standalone HTML page if requested. Map renders client-side
    # from inlined points + the static base map (HANDOFF 9b.10) — no
    # map_url argument needed.
    if args.write_html:
        page_html = render_html_page(forecast)
        out_path = os.path.abspath(args.write_html)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w") as f:
            f.write(page_html)
        print(f"Wrote HTML: {args.write_html}")
        try:
            details_path = os.path.join(os.path.dirname(out_path),
                                        "details.html")
            with open(details_path, "w") as f:
                f.write(render_details_page(forecast))
            print(f"Wrote details page: {details_path}")
        except Exception as e:
            print(f"WARNING: details page failed: {e}")

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
        # DAY-MAX carry-forward (2026-07-08): each hourly run OVERWRITES
        # the daily archive, so the day's peak risk assessment used to
        # vanish by evening — the 7/6 flood day's archive ended up
        # showing only the post-storm residue (burst 0.25, potential
        # 3.8) instead of anything about the event. Carry the day's
        # maximum burst assessment forward across runs so the archive
        # answers "how risky did this day ever look?", not "how did the
        # day end?". The all-pathways chart reads these day_max fields.
        try:
            with open(out_path) as f:
                prev = json.load(f)
            ppr = prev.get("pluvial_risk") or {}
            cpr = forecast.get("pluvial_risk")
            if cpr is None:
                cpr = forecast["pluvial_risk"] = {}
            _rank = {None: 0, "possible": 1, "elevated": 2}
            lv_prev = ppr.get("day_max_level", ppr.get("level"))
            lv_cur = cpr.get("level")
            cpr["day_max_level"] = (lv_prev if _rank.get(lv_prev, 0)
                                    >= _rank.get(lv_cur, 0) else lv_cur)
            for fld in ("potential_low_tide_navd88",
                        "potential_low_tide_navd88_tanh",
                        "burst_est_in_hr"):
                vals = [v for v in (ppr.get("day_max_" + fld),
                                    ppr.get(fld), cpr.get(fld))
                        if v is not None]
                if vals:
                    cpr["day_max_" + fld] = max(vals)
        except (OSError, ValueError):
            pass  # first run of the day / unreadable previous archive
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
        # Still evaluate + persist the alert state so risk episodes
        # are tracked even on runs that can't send (state resets on
        # all-clear; escalation triggers the next sending run).
        send, reason = should_send_alert(forecast)
        print(f"Skipping email send (--no-send set). Alert eval: {reason}"
              + (" — WOULD SEND" if send else ""))
        return

    # EVENT-DRIVEN ALERTING (user, 2026-07-17): the daily-morning
    # email became ignorable ("mostly not telling me it will flood").
    # Email now goes out ONLY when flood risk APPEARS or ESCALATES
    # (tide regime ≥ street in the 72h window, or pluvial risk
    # active); a short SMS (email-to-SMS gateway, ALERT_SMS_TO
    # secret) rides along. --force-email preserves a manual path.
    send, reason = should_send_alert(forecast)
    if getattr(args, "force_email", False):
        send, reason = True, "forced (--force-email)"
    if not send:
        print(f"No alert email: {reason}")
        return

    required = ["SMTP_HOST", "SMTP_USER", "SMTP_PASS", "SMTP_FROM", "SMTP_TO"]
    missing = [v for v in required if v not in os.environ]
    if missing:
        print(f"ERROR: missing environment variables: {', '.join(missing)}", flush=True)
        print("Either set them, or run with --dry-run / --no-send.", flush=True)
        raise SystemExit(2)

    subject = "[ALERT] " + subject
    _png = None
    try:
        _png = build_series_chart_png(forecast)
    except Exception as e:
        print(f"WARNING: chart png failed: {e}")
    send_email(subject, text, html, inline_png=_png)
    print(f"Sent alert email ({reason}): {subject}"
          + (" [chart attached]" if _png else " [no chart]"))

    # PUSH NOTIFICATIONS via ntfy (2026-07-17): carrier email-to-SMS
    # gateways are dead or dying (AT&T shut June 2025, T-Mobile late
    # 2024, Verizon degraded w/ 2027 sunset) — ntfy is the reliable
    # rail: free, no account, HTTP POST, and natively multi-person
    # (anyone subscribed to the topic gets the push). NTFY_TOPIC
    # secret = the topic name; treat it like a password (anyone who
    # knows it can subscribe/post).
    ntfy_topic = os.environ.get("NTFY_TOPIC", "").strip()
    if ntfy_topic:
        try:
            sms = build_sms_text(forecast)
            rank, label, _sig = compute_alert_level(forecast)
            req = Request(
                f"https://ntfy.sh/{ntfy_topic}",
                data=sms.encode(),
                headers={
                    "Title": f"Barnacle flood alert ({label})",
                    "Priority": "urgent" if rank >= 3 else "high",
                    "Tags": "ocean" if rank < 3 else "rotating_light",
                    # cache-busted (2026-07-20): clicking an alert
                    # seconds after it fires must not serve the CDN's
                    # pre-alert page — the "disconnect" the user hit
                    "Click": "https://johnurban.github.io/barnacle/?a="
                             + str(int(_time.time())),
                })
            urlopen(req, timeout=15).read()
            print(f"Sent ntfy push to topic ({rank=})")
        except Exception as e:
            print(f"WARNING: ntfy push failed: {e}")

    # Legacy email-to-SMS gateway path (kept while Verizon's vtext
    # limps toward its 2027 sunset; AT&T/T-Mobile gateways are gone).
    sms_to = os.environ.get("ALERT_SMS_TO", "").strip()
    if sms_to:
        try:
            sms = build_sms_text(forecast)
            _orig_to = os.environ.get("SMTP_TO")
            os.environ["SMTP_TO"] = sms_to
            send_email("", sms, None)
            os.environ["SMTP_TO"] = _orig_to
            print(f"Sent SMS alert to gateway ({len(sms)} chars) — "
                  "NOTE: carrier gateways are unreliable/deprecated; "
                  "prefer NTFY_TOPIC")
        except Exception as e:
            print(f"WARNING: SMS send failed: {e}")


if __name__ == "__main__":
    main()
