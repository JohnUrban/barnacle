#!/usr/bin/env python3
"""7-day outlook data adapters (opened 2026-09-23; audit 2026-09-23-a1 R1/R3/R4/R9).

Two producers, by design:

  * The HOURLY production run (flood_forecast_daily.py) calls `gather()`,
    which makes only five quick requests (astronomy, hourly astronomy, the
    NWS grid, the NWS gauge forecast, the cross-check) under ONE monotonic
    deadline (OUTLOOK_FETCH_BUDGET_S). When the budget is spent, remaining
    sources are reported "unavailable: budget", never awaited. It reads the
    expensive sources from the warm job's file and admits them by issuance
    age. It never blocks alert evaluation for a vendor.
  * The WARM job (outlook_warm.py, nbm_qmd.yml) fetches the expensive or
    slow-changing sources (NBM amounts to now+168 h, NBM percentiles from
    the newest synoptic cycle, P-ETSS surge, WPC daily rain) into
    data/outlook_guidance.json on its own budget.

Every adapter returns JSON-safe data or raises; health is decided by the
caller (rule 7: unavailable is never zero). No adapter imports the facade.

Sources and verified reach (2026-09-23):
  astro/astro_hourly  NOAA CO-OPS predictions                  any range
  grid    NWS gridpoint wind / gust / direction / PoP ~7 d; QPF ~72 h
  nwps    NWS water-prediction gauge forecast SDHN4   72 h hourly (ft MLLW)
  petss   P-ETSS GEFS-based storm SURGE, e90/e10 = p10/p90, 102 h hourly
  nbm     National Blend of Models 6-h QPF + PoP (core, hourly cycles)
  nbm_qmd NBM percentiles + exceedance chances (00/06/12/18Z, lags 3+ h)
  wpc     WPC 24-h QPF days 2-7 (per-interval fallback for rain)
  xcheck  non-NOAA multi-model + GEFS ensemble (cross-check only)
"""

import datetime as dt
import json
import math
import os
import re
import statistics
import tempfile
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

try:
    from .station_time import noaa_gmt_to_station_string, STATION_TZ
except ImportError:                      # run as a script from forecast/
    from station_time import noaa_gmt_to_station_string, STATION_TZ

UA = os.environ.get("USER_AGENT",
                    "highlands-flood-forecast (contact@example.com)")
HOUSE_LAT = 40.405479
HOUSE_LON = -73.995195
SANDY_HOOK_STATION = "8531680"
NWPS_GAUGE = "SDHN4"

COOPS_URL = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
NWS_POINTS_URL = "https://api.weather.gov/points/{lat:.4f},{lon:.4f}"
NWPS_URL = "https://api.water.noaa.gov/nwps/v1/gauges/{gauge}/stageflow"
PETSS_URL = ("https://nomads.ncep.noaa.gov/pub/data/nccf/com/petss/prod/"
             "petss.{ymd}/petss.t{hh:02d}z.{pct}.stormsurge.east.txt")
NBM_FILTER_URL = "https://nomads.ncep.noaa.gov/cgi-bin/filter_blend.pl"
WPC_QPF_URL = "https://ftp-wpc.ncep.noaa.gov/2p5km_qpf/p24m_{ymd}{hh:02d}f{fff:03d}.grb"
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_ENS_URL = "https://ensemble-api.open-meteo.com/v1/ensemble"

HORIZON_HOURS = 168
NBM_MAX_FHOUR = 264
WPC_STEPS = (48, 72, 96, 120, 144, 168)                 # 24-h totals
NBM_BOX = {"toplat": 40.5, "bottomlat": 40.3, "leftlon": -74.1, "rightlon": -73.9}

# Hourly-run budget (R1): five quick requests, one deadline, alerts never wait.
OUTLOOK_FETCH_BUDGET_S = 60.0
PER_REQUEST_CAP_S = 15.0

# Warm-file admission by ISSUANCE / cycle age (R4), hours.
GUIDANCE_AGE_H = {          # (ok_below, degraded_below); beyond -> unavailable
    # nbm_qmd: four cycles a day published ~4-5 h late, warm job every 3 h ->
    # ~14 h staleness in normal operation is not a fault.
    "nbm": (9.0, 24.0), "nbm_qmd": (15.0, 30.0), "petss": (12.0, 30.0), "wpc": (18.0, 36.0),
}
NWPS_MAX_ISSUE_AGE_H = 24.0

GUIDANCE_PATH_DEFAULT = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "data", "outlook_guidance.json"))

MM_PER_IN = 25.4
MPH_PER_KMH = 0.621371


# ---------------------------------------------------------------------------
# transport + deadline
# ---------------------------------------------------------------------------
class Deadline:
    """Monotonic budget shared by every request of one gather()."""

    def __init__(self, seconds, clock=time.monotonic):
        self._clock = clock
        self.seconds = float(seconds)
        self._end = clock() + self.seconds

    def remaining(self):
        return self._end - self._clock()

    def timeout(self, cap=PER_REQUEST_CAP_S):
        """Socket timeout for the next request, or None when spent."""
        r = self.remaining()
        if r <= 2.0:
            return None
        return max(1.0, min(cap, r))


def _request(url, timeout=30):
    req = Request(url, headers={"User-Agent": UA})
    with urlopen(req, timeout=timeout) as r:
        return r.read()


def _get_json(url, timeout=30):
    return json.loads(_request(url, timeout))


def _parse_iso(stamp):
    if not stamp:
        return None
    try:
        when = dt.datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
    except ValueError:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=dt.timezone.utc)
    return when


def _stamp(when):
    return when.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _iso_duration_hours(text):
    """'PT6H' -> 6, 'P3DT22H' -> 94, 'P1D' -> 24, 'PT30M' -> 0.5."""
    m = re.match(r"^P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?)?$", text or "")
    if not m:
        raise ValueError(f"unsupported ISO duration {text!r}")
    days, hours, minutes = (int(x) if x else 0 for x in m.groups())
    return days * 24 + hours + minutes / 60.0


def _finite(v):
    return isinstance(v, (int, float)) and math.isfinite(v)


# ---------------------------------------------------------------------------
# quick-source cache contract (used with an in-memory dict per run)
# ---------------------------------------------------------------------------
def refresh(cache, key, fetch_fn, now_utc, ttl_h=1.0, max_stale_h=12.0, deadline=None):
    """(data, health) for one quick source under the deadline contract.

    fetch_fn(timeout) must return JSON-safe data with a 'summary' or raise.
    """
    entry = cache.get(key) or {}
    fetched = _parse_iso(entry.get("fetched_at"))
    age_h = ((now_utc - fetched).total_seconds() / 3600.0) if fetched else None
    data = entry.get("data")
    if data is not None and age_h is not None and 0 <= age_h < ttl_h:
        return data, {"status": "ok",
                      "detail": f"{data.get('summary', 'cached')} (cache {age_h:.1f} h)",
                      "fetched_at": entry.get("fetched_at"), "age_h": round(age_h, 2)}
    timeout = deadline.timeout() if deadline is not None else 30.0
    if timeout is None:
        if data is not None and age_h is not None and age_h <= max_stale_h:
            return data, {"status": "degraded",
                          "detail": f"skipped: outlook time budget exhausted; cached copy {age_h:.1f} h old",
                          "fetched_at": entry.get("fetched_at"), "age_h": round(age_h, 2)}
        return None, {"status": "unavailable", "detail": "skipped: outlook time budget exhausted",
                      "fetched_at": None, "age_h": None}
    try:
        fresh = fetch_fn(timeout)
    except Exception as e:  # transport, parse, validation: all reported
        if data is not None and age_h is not None and age_h <= max_stale_h:
            return data, {"status": "degraded",
                          "detail": (f"refetch failed ({type(e).__name__}: {e}); "
                                     f"serving cached copy {age_h:.1f} h old"),
                          "fetched_at": entry.get("fetched_at"), "age_h": round(age_h, 2)}
        return None, {"status": "unavailable",
                      "detail": f"fetch failed ({type(e).__name__}: {e})",
                      "fetched_at": None, "age_h": None}
    stamp = _stamp(now_utc)
    cache[key] = {"fetched_at": stamp, "data": fresh}
    return fresh, {"status": "ok", "detail": fresh.get("summary", "fresh"),
                   "fetched_at": stamp, "age_h": 0.0}


# ---------------------------------------------------------------------------
# astro: NOAA CO-OPS predictions
# ---------------------------------------------------------------------------
def _coops_predictions(now_utc, hours_back, hours, interval, timeout):
    begin = (now_utc - dt.timedelta(hours=hours_back)).strftime("%Y%m%d %H:%M")
    params = dict(product="predictions", application="barnacle-outlook",
                  begin_date=begin, range=int(hours + hours_back + 1), datum="MLLW",
                  station=SANDY_HOOK_STATION, time_zone="gmt", units="english",
                  interval=interval, format="json")
    data = _get_json(COOPS_URL + "?" + urlencode(params), timeout)
    pts = []
    for p in data.get("predictions") or []:
        gmt = p["t"]
        when = dt.datetime.strptime(gmt, "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc)
        v = float(p["v"])
        if not math.isfinite(v):
            continue
        pts.append({"utc": _stamp(when), "time": noaa_gmt_to_station_string(gmt),
                    "mllw": round(v, 3), "type": p.get("type")})
    return pts


def fetch_astro_highs(now_utc, hours=HORIZON_HOURS + 6, timeout=30):
    highs = [{k: v for k, v in p.items() if k != "type"}
             for p in _coops_predictions(now_utc, 2, hours, "hilo", timeout) if p.get("type") == "H"]
    if not highs:
        raise ValueError("no high tides in CO-OPS response")
    return {"highs": highs, "summary": f"{len(highs)} astronomical highs"}


def fetch_astro_hourly(now_utc, hours_back=6, hours=HORIZON_HOURS, timeout=30):
    """Hourly astronomical predictions: the backbone of the 7-day series."""
    pts = [{k: v for k, v in p.items() if k != "type"}
           for p in _coops_predictions(now_utc, hours_back, hours, "h", timeout)]
    if len(pts) < 24:
        raise ValueError(f"only {len(pts)} hourly predictions")
    return {"points": pts, "summary": f"{len(pts)} hourly astronomical points"}


# ---------------------------------------------------------------------------
# grid: NWS gridpoint 7-day wind / PoP / QPF
# ---------------------------------------------------------------------------
_GRID_FIELDS = {
    "quantitativePrecipitation": ("qpf_in", lambda v: v / MM_PER_IN),
    "probabilityOfPrecipitation": ("pop_pct", lambda v: v),
    "windSpeed": ("wind_mph", lambda v: v * MPH_PER_KMH),
    "windGust": ("gust_mph", lambda v: v * MPH_PER_KMH),
    "windDirection": ("wind_dir_deg", lambda v: v),
}


def parse_nws_grid(props):
    series = {}
    for src, (name, conv) in _GRID_FIELDS.items():
        out = []
        for v in (props.get(src) or {}).get("values") or []:
            stamp, _, dur = (v.get("validTime") or "").partition("/")
            start = _parse_iso(stamp)
            if start is None:
                continue
            val = v.get("value")
            out.append({"start": _stamp(start), "hours": _iso_duration_hours(dur),
                        "value": (round(conv(val), 3) if _finite(val) else None)})
        series[name] = out
    last = {}
    for name, rows in series.items():
        if rows:
            end = _parse_iso(rows[-1]["start"]) + dt.timedelta(hours=rows[-1]["hours"])
            last[name] = _stamp(end)
    return {"update_time": props.get("updateTime"), "series": series, "reach": last,
            "summary": ("grid QPF to " + last.get("qpf_in", "?")[:13] + "Z, wind to "
                        + last.get("gust_mph", "?")[:13] + "Z")}


def _next_timeout(deadline, fallback):
    """Timeout for the NEXT request: recomputed from the deadline each time
    (round 03 S7); None means the budget is spent."""
    if deadline is None:
        return fallback
    return deadline.timeout()


def fetch_nws_grid(lat=HOUSE_LAT, lon=HOUSE_LON, timeout=30, deadline=None):
    t = _next_timeout(deadline, timeout)
    if t is None:
        raise TimeoutError("outlook budget spent before the NWS points request")
    pts = _get_json(NWS_POINTS_URL.format(lat=lat, lon=lon), t)
    grid_url = pts["properties"]["forecastGridData"]
    t = _next_timeout(deadline, timeout)
    if t is None:
        raise TimeoutError("outlook budget spent before the NWS grid request")
    return parse_nws_grid(_get_json(grid_url, t)["properties"])


def grid_value_at(series, when_utc):
    """Value of a grid series covering `when_utc` (start <= t < end)."""
    for row in series or []:
        start = _parse_iso(row["start"])
        if start <= when_utc < start + dt.timedelta(hours=row["hours"]):
            return row["value"]
    return None


# ---------------------------------------------------------------------------
# nwps: NWS water-prediction gauge forecast (SDHN4, ft MLLW, hourly, 72 h)
# ---------------------------------------------------------------------------
def parse_nwps(doc, now_utc=None):
    """Validated (R4): issuance parseable, not future, <= 24 h old; units
    ft; finite plausible values; at least 12 future points."""
    f = doc.get("forecast") or {}
    issued = _parse_iso(f.get("issuedTime"))
    if issued is None:
        raise ValueError("NWPS forecast has no parseable issuedTime")
    if now_utc is not None:
        age_h = (now_utc - issued).total_seconds() / 3600.0
        if age_h < -1.0:
            raise ValueError(f"NWPS issuedTime is in the future ({f.get('issuedTime')})")
        if age_h > NWPS_MAX_ISSUE_AGE_H:
            raise ValueError(f"NWPS forecast is {age_h:.1f} h old (issued {f.get('issuedTime')})")
    units = (f.get("primaryUnits") or "").strip().lower()
    if units != "ft":
        raise ValueError(f"NWPS units {f.get('primaryUnits')!r}, expected ft")
    pts = []
    for x in f.get("data") or []:
        v = x.get("primary")
        t = _parse_iso(x.get("validTime"))
        if t is None or not _finite(v) or v <= -900 or not (-5.0 <= v <= 25.0):
            continue
        pts.append({"utc": _stamp(t), "ft": round(float(v), 3)})
    future = sum(1 for p in pts if now_utc is None or _parse_iso(p["utc"]) >= now_utc)
    if future < 12:
        raise ValueError(f"NWPS forecast has only {future} future points")
    return {"issued": _stamp(issued), "units": "ft", "series": pts,
            "summary": f"{len(pts)} hourly points issued {_stamp(issued)}"}


def fetch_nwps_forecast(now_utc=None, gauge=NWPS_GAUGE, timeout=30):
    return parse_nwps(_get_json(NWPS_URL.format(gauge=gauge), timeout), now_utc)


def series_max_near(series, when_utc, window_h=2.0, key="ft"):
    best = None
    for p in series or []:
        t = _parse_iso(p["utc"])
        if t is None or abs((t - when_utc).total_seconds()) > window_h * 3600:
            continue
        if best is None or p[key] > best:
            best = p[key]
    return best


def series_value_nearest(series, when_utc, max_gap_h=1.0, key="surge_ft"):
    best, gap = None, None
    for p in series or []:
        t = _parse_iso(p["utc"])
        if t is None:
            continue
        g = abs((t - when_utc).total_seconds()) / 3600.0
        if g <= max_gap_h and (gap is None or g < gap):
            best, gap = p[key], g
    return best


# ---------------------------------------------------------------------------
# petss: P-ETSS storm surge text (FQUS23), tenths of ft, hourly, 102 h
# ---------------------------------------------------------------------------
_PETSS_STATION_RE = re.compile(r"^\s*(\d{7})\s+[A-Z]")


def parse_petss_station(text, cycle_utc, station=SANDY_HOOK_STATION):
    """Hourly surge (ft) for one station: value i is valid at cycle + (i+1) h;
    tenths of a foot; |v| >= 300 (e.g. -400) is missing and DROPPED."""
    lines = text.splitlines()
    hdr = next((l for l in lines[:6] if re.search(r"\b\d{2}Z\b", l)), None)
    if hdr is None:
        raise ValueError("P-ETSS header without hour row")
    first_hour = int(re.search(r"(\d{2})Z", hdr).group(1))
    if first_hour != (cycle_utc.hour + 1) % 24:
        raise ValueError(f"P-ETSS first column {first_hour:02d}Z does not follow "
                         f"cycle {cycle_utc.hour:02d}Z")
    start = None
    for i, line in enumerate(lines):
        m = _PETSS_STATION_RE.match(line)
        if m and m.group(1) == station:
            start = i + 1
            break
    if start is None:
        raise ValueError(f"station {station} not in P-ETSS product")
    vals = []
    for line in lines[start:]:
        if _PETSS_STATION_RE.match(line) or not line.strip():
            break
        for tok in re.findall(r"-?\d+", line):
            v = int(tok)
            vals.append(None if abs(v) >= 300 else round(v / 10.0, 2))
    if len(vals) < 24:
        raise ValueError(f"P-ETSS station block too short ({len(vals)} values)")
    series = []
    for i, v in enumerate(vals):
        if v is None:
            continue
        series.append({"utc": _stamp(cycle_utc + dt.timedelta(hours=i + 1)), "surge_ft": v})
    return series


def _petss_cycles(now_utc):
    out = []
    for back in (0, 1):
        day = (now_utc - dt.timedelta(days=back)).date()
        for hh in (18, 12, 6, 0):
            c = dt.datetime(day.year, day.month, day.day, hh, tzinfo=dt.timezone.utc)
            if c <= now_utc - dt.timedelta(minutes=90):
                out.append(c)
    return sorted(out, reverse=True)


def fetch_petss(now_utc, timeout=120):
    last_err = None
    for cycle in _petss_cycles(now_utc)[:4]:
        try:
            out = {"cycle": _stamp(cycle)}
            # P-ETSS files are named by EXCEEDANCE probability: e10 is exceeded
            # by only 10 % of members (our p90); e90 is exceeded by 90 % (p10).
            for pct, key in (("e90", "p10"), ("e10", "p90")):
                url = PETSS_URL.format(ymd=cycle.strftime("%Y%m%d"), hh=cycle.hour, pct=pct)
                out[key] = parse_petss_station(_request(url, timeout).decode("ascii", "replace"), cycle)
            if any(a["surge_ft"] > b["surge_ft"] + 0.05 for a, b in zip(out["p10"], out["p90"])):
                raise ValueError("P-ETSS p10 exceeds p90: exceedance mapping wrong")
            out["summary"] = f"P-ETSS cycle {out['cycle'][:13]}Z, {len(out['p90'])} h, p10/p90 surge"
            return out
        except Exception as e:
            last_err = e
    raise RuntimeError(f"no P-ETSS cycle readable: {last_err}")


# ---------------------------------------------------------------------------
# GRIB helpers (eccodes; installed by forecast/requirements.txt)
# ---------------------------------------------------------------------------
def _grib_messages(raw, keys=()):
    try:
        import eccodes as ec
    except ImportError as e:
        raise RuntimeError("GRIB decoder not installed (eccodes)") from e
    with tempfile.NamedTemporaryFile(suffix=".grib2", delete=False) as tmp:
        tmp.write(raw)
        path = tmp.name
    try:
        with open(path, "rb") as f:
            while True:
                gid = ec.codes_grib_new_from_file(f)
                if gid is None:
                    break
                try:
                    def g(key):
                        return ec.codes_get(gid, key) if ec.codes_is_defined(gid, key) else None
                    msg = {k: g(k) for k in ("productDefinitionTemplateNumber", "lengthOfTimeRange",
                                             "units", "shortName", "parameterCategory",
                                             "parameterNumber", "percentileValue", "probabilityType",
                                             "scaledValueOfUpperLimit", "scaleFactorOfUpperLimit")}
                    msg.update({"lats": ec.codes_get_array(gid, "latitudes"),
                                "lons": ec.codes_get_array(gid, "longitudes"),
                                "values": ec.codes_get_values(gid)})
                    yield msg
                finally:
                    ec.codes_release(gid)
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def _nearest_value(msg, lat=HOUSE_LAT, lon=HOUSE_LON):
    import numpy as np   # eccodes depends on numpy; keep the import local
    lats = np.asarray(msg["lats"], dtype=float)
    lons = np.asarray(msg["lons"], dtype=float)
    lons = np.where(lons > 180.0, lons - 360.0, lons)
    coslat = math.cos(math.radians(lat))
    d = (lats - lat) ** 2 + ((lons - lon) * coslat) ** 2
    v = float(msg["values"][int(np.argmin(d))])
    if not math.isfinite(v):
        raise ValueError("non-finite GRIB value at the house")
    return v


def _precip_inches(value, units):
    if value is None:
        return None
    if units in ("kg m**-2", "mm", "kg m-2"):
        return round(value / MM_PER_IN, 3)
    if units in ("in", "inch", "inches"):
        return round(value, 3)
    raise ValueError(f"unexpected precipitation units {units!r}")


# ---------------------------------------------------------------------------
# nbm: National Blend of Models 6-h QPF + PoP via the NOMADS filter
# ---------------------------------------------------------------------------
def nbm_subset_url(cycle_utc, fhour):
    params = {"dir": f"/blend.{cycle_utc:%Y%m%d}/{cycle_utc:%H}/core",
              "file": f"blend.t{cycle_utc:%H}z.core.f{fhour:03d}.co.grib2",
              "all_lev": "on", "var_APCP": "on", "subregion": "", **NBM_BOX}
    return NBM_FILTER_URL + "?" + urlencode(params)


def parse_nbm_subset(raw):
    """{'qpf_in': 6-h amount, 'pop_pct': 6-h probability} at the house
    (template 8 = deterministic accumulation, 9 = probability)."""
    out = {"qpf_in": None, "pop_pct": None}
    for msg in _grib_messages(raw):
        if msg["lengthOfTimeRange"] != 6:
            continue
        v = _nearest_value(msg)
        if msg["productDefinitionTemplateNumber"] == 8:
            out["qpf_in"] = _precip_inches(v, msg["units"])
        elif msg["productDefinitionTemplateNumber"] == 9:
            out["pop_pct"] = round(v, 1)
    if out["qpf_in"] is None:
        raise ValueError("no 6-h APCP message in NBM subset")
    return out


def nbm_steps_to_cover(cycle_utc, horizon_end_utc, step=6, max_fhour=NBM_MAX_FHOUR):
    """6-h forecast hours from the cycle to cover horizon_end (R3): the
    horizon is measured from NOW, not from the cycle."""
    need = (horizon_end_utc - cycle_utc).total_seconds() / 3600.0
    last = min(max_fhour, int(math.ceil(need / step)) * step)
    return tuple(range(step, max(step, last) + 1, step))


def fetch_nbm_qpf(now_utc, horizon_end_utc=None, timeout=60):
    horizon_end = horizon_end_utc or (now_utc + dt.timedelta(hours=HORIZON_HOURS + 6))
    cycle, first, last_err = None, None, None
    for lag in range(3, 10):
        c = (now_utc - dt.timedelta(hours=lag)).replace(minute=0, second=0, microsecond=0)
        try:
            raw = _request(nbm_subset_url(c, 6), timeout)
            if raw[:4] != b"GRIB":
                raise ValueError("not GRIB")
            cycle, first = c, parse_nbm_subset(raw)
            break
        except Exception as e:
            last_err = e
    if cycle is None:
        raise RuntimeError(f"no NBM cycle available: {last_err}")
    steps = nbm_steps_to_cover(cycle, horizon_end)
    buckets, missing = [], []
    for fh in steps:
        try:
            got = first if fh == 6 else parse_nbm_subset(_request(nbm_subset_url(cycle, fh), timeout))
        except Exception as e:
            missing.append(f"f{fh:03d}: {type(e).__name__}")
            continue
        buckets.append({"end_utc": _stamp(cycle + dt.timedelta(hours=fh)), "hours": 6,
                        "qpf_in": got["qpf_in"], "pop_pct": got["pop_pct"]})
    if len(buckets) < len(steps) // 2:
        raise RuntimeError(f"NBM: only {len(buckets)}/{len(steps)} buckets ({missing[:3]})")
    return {"cycle": _stamp(cycle), "buckets": buckets, "missing": missing,
            "summary": (f"NBM cycle {cycle:%Y-%m-%dT%H}Z, {len(buckets)}/{len(steps)} "
                        f"6-h buckets to +{steps[-1]} h")}


# NBM probabilistic (qmd): percentiles + exceedance chances, precip-only subsets
NBM_EXCEEDANCE_IN = {0.25: "p_ge_quarter_in_pct", 0.5: "p_ge_half_in_pct", 1.0: "p_ge_1in_pct"}
NBM_PERCENTILES = (10, 50, 90)
NBM_QMD_FIELDS = tuple(f"p{q}_in" for q in NBM_PERCENTILES) + tuple(NBM_EXCEEDANCE_IN.values())


def nbm_qmd_subset_url(cycle_utc, fhour):
    params = {"dir": f"/blend.{cycle_utc:%Y%m%d}/{cycle_utc:%H}/qmd",
              "file": f"blend.t{cycle_utc:%H}z.qmd.f{fhour:03d}.co.grib2",
              "var_APCP": "on", "all_lev": "on", "subregion": "", **NBM_BOX}
    return NBM_FILTER_URL + "?" + urlencode(params)


def parse_nbm_qmd_subset(raw):
    out = {k: None for k in NBM_QMD_FIELDS}
    for msg in _grib_messages(raw):
        if not (msg["parameterCategory"] == 1 and msg["parameterNumber"] == 8
                and msg["lengthOfTimeRange"] == 6):
            continue
        tmpl = msg["productDefinitionTemplateNumber"]
        if tmpl == 10 and msg["percentileValue"] in NBM_PERCENTILES:
            out[f"p{msg['percentileValue']}_in"] = _precip_inches(_nearest_value(msg), msg["units"])
        elif tmpl == 9 and msg["probabilityType"] == 1:
            sv, sf = msg["scaledValueOfUpperLimit"], msg["scaleFactorOfUpperLimit"]
            if sv is None or sf is None:
                continue
            thr_in = round(sv * (10.0 ** -sf) / MM_PER_IN, 3)
            for thr, name in NBM_EXCEEDANCE_IN.items():
                if abs(thr_in - thr) < 0.02:
                    out[name] = round(_nearest_value(msg), 1)
    if out["p90_in"] is None:
        raise ValueError("no 6-h percentile messages in NBM qmd subset")
    return out


def newest_qmd_cycle(now_utc, timeout=90):
    """Newest 00/06/12/18Z cycle whose probabilistic file is published."""
    base = now_utc.replace(hour=(now_utc.hour // 6) * 6, minute=0, second=0, microsecond=0)
    for back in range(0, 30, 6):
        c = base - dt.timedelta(hours=back)
        try:
            raw = _request(nbm_qmd_subset_url(c, 6), timeout)
        except Exception:
            continue
        if raw[:4] == b"GRIB":
            return c
    return None


def fetch_nbm_qmd(now_utc, cycle=None, steps=None, time_budget_s=None, timeout=90,
                  horizon_end_utc=None):
    """Percentiles per 6-h bucket keyed by valid END time (warm job only).
    The budget clock covers discovery too (R9); the first step is always
    attempted so a published cycle yields at least one bucket."""
    started = time.monotonic()
    qcycle = cycle or newest_qmd_cycle(now_utc, timeout)
    if qcycle is None:
        raise RuntimeError("no NBM qmd cycle published in the last 30 h")
    if steps is None:
        steps = nbm_steps_to_cover(qcycle, horizon_end_utc or (now_utc + dt.timedelta(hours=HORIZON_HOURS + 6)))
    buckets, missing = {}, []
    for i, fh in enumerate(steps):
        if i > 0 and time_budget_s is not None and time.monotonic() - started > time_budget_s:
            missing.append(f"f{fh:03d}: time budget")
            continue
        try:
            buckets[_stamp(qcycle + dt.timedelta(hours=fh))] = parse_nbm_qmd_subset(
                _request(nbm_qmd_subset_url(qcycle, fh), timeout))
        except Exception as e:
            missing.append(f"f{fh:03d}: {type(e).__name__}")
    if not buckets:
        raise RuntimeError(f"NBM qmd: no buckets decoded ({missing[:3]})")
    return {"qmd_cycle": _stamp(qcycle), "buckets": buckets, "missing": missing,
            "summary": f"NBM qmd {qcycle:%Y-%m-%dT%H}Z: {len(buckets)}/{len(steps)} buckets"}


def merge_nbm_qmd(nbm, qmd, now_utc):
    """Attach percentile fields to NBM amount buckets by valid end time.

    R4: expiry is decided FIRST (by the qmd CYCLE age); stale data is not
    merged; any percentile fields already on the buckets are cleared before
    the merge so a missing or expired file cannot leave old values behind.
    ok requires at least one matching bucket.
    """
    buckets = (nbm or {}).get("buckets") or []
    for b in buckets:
        for k in NBM_QMD_FIELDS:
            b.pop(k, None)
    if not qmd or not qmd.get("buckets"):
        return {"status": "unavailable", "detail": "no NBM percentile file yet",
                "issued": None, "age_h": None}
    cycle = _parse_iso(qmd.get("qmd_cycle"))
    age_h = ((now_utc - cycle).total_seconds() / 3600.0) if cycle else None
    ok_h, deg_h = GUIDANCE_AGE_H["nbm_qmd"]
    if age_h is None or age_h < -1.0 or age_h > deg_h:
        return {"status": "unavailable",
                "detail": (f"NBM percentiles cycle {qmd.get('qmd_cycle')} "
                           + ("unparseable" if age_h is None else f"{age_h:.1f} h old, expired")
                           + "; not used"),
                "issued": qmd.get("qmd_cycle"), "age_h": round(age_h, 2) if age_h is not None else None}
    n = 0
    for b in buckets:
        q = (qmd.get("buckets") or {}).get(b["end_utc"])
        if not q:
            continue
        p10, p50, p90 = q.get("p10_in"), q.get("p50_in"), q.get("p90_in")
        if not _finite(p90) or p90 < 0:
            continue
        if (_finite(p10) and p10 > p90 + 1e-6) or (_finite(p50) and _finite(p10) and p50 < p10 - 1e-6) \
                or (_finite(p50) and p50 > p90 + 1e-6):
            continue                                     # disordered percentiles: skip the bucket
        clean = {k: v for k, v in q.items() if k in NBM_QMD_FIELDS and (v is None or _finite(v))}
        b.update(clean)
        n += 1
    if n == 0:
        status = "degraded"
    elif age_h > ok_h:
        status = "degraded"
    else:
        status = "ok"
    return {"status": status,
            "detail": f"percentiles from NBM {str(qmd.get('qmd_cycle', ''))[:13]}Z on {n} buckets, cycle {age_h:.1f} h old",
            "issued": qmd.get("qmd_cycle"), "age_h": round(age_h, 2)}


# ---------------------------------------------------------------------------
# wpc: WPC 24-h QPF files (per-interval rain fallback)
# ---------------------------------------------------------------------------
def _wpc_cycles(now_utc):
    out = []
    for back in (0, 1):
        day = (now_utc - dt.timedelta(days=back)).date()
        for hh in (12, 0):
            c = dt.datetime(day.year, day.month, day.day, hh, tzinfo=dt.timezone.utc)
            if c <= now_utc - dt.timedelta(hours=4):
                out.append(c)
    return sorted(out, reverse=True)


def parse_wpc_file(raw):
    for msg in _grib_messages(raw):
        return _precip_inches(_nearest_value(msg), msg["units"])
    raise ValueError("empty WPC GRIB")


def fetch_wpc_qpf(now_utc, steps=WPC_STEPS, timeout=90):
    last_err = None
    for cycle in _wpc_cycles(now_utc)[:2]:
        buckets, missing = [], []
        for fh in steps:
            url = WPC_QPF_URL.format(ymd=cycle.strftime("%Y%m%d"), hh=cycle.hour, fff=fh)
            try:
                qpf = parse_wpc_file(_request(url, timeout))
            except Exception as e:
                missing.append(f"f{fh:03d}: {type(e).__name__}")
                last_err = e
                continue
            buckets.append({"end_utc": _stamp(cycle + dt.timedelta(hours=fh)), "hours": 24,
                            "qpf_in": qpf})
        if buckets:
            return {"cycle": _stamp(cycle), "buckets": buckets, "missing": missing,
                    "summary": f"WPC cycle {cycle:%Y-%m-%dT%H}Z, {len(buckets)} daily totals"}
    raise RuntimeError(f"no WPC cycle readable: {last_err}")


# ---------------------------------------------------------------------------
# xcheck: non-NOAA multi-model + ensemble (cross-check only, never an input)
# ---------------------------------------------------------------------------
XCHECK_MODELS = (("gfs_seamless", "gfs"), ("ecmwf_ifs025", "ecmwf"),
                 ("icon_seamless", "icon"), ("gem_seamless", "gem"))


def parse_openmeteo(models_doc, ens_doc):
    out = {"models": {}, "ensemble": {}}
    dd = models_doc.get("daily") or {}
    for i, day in enumerate(dd.get("time") or []):
        row = {}
        for api_name, short in XCHECK_MODELS:
            ps = dd.get(f"precipitation_sum_{api_name}") or []
            gs = dd.get(f"wind_gusts_10m_max_{api_name}") or []
            row[short] = {"precip_in": ps[i] if i < len(ps) else None,
                          "gust_mph": gs[i] if i < len(gs) else None}
        out["models"][day] = row
    ed = ens_doc.get("daily") or {}
    pk = [k for k in ed if k.startswith("precipitation_sum")]
    gk = [k for k in ed if k.startswith("wind_gusts_10m_max")]
    for i, day in enumerate(ed.get("time") or []):
        p = sorted(v for v in (ed[k][i] for k in pk if i < len(ed[k])) if _finite(v))
        g = sorted(v for v in (ed[k][i] for k in gk if i < len(ed[k])) if _finite(v))
        if not p:
            continue
        out["ensemble"][day] = {
            "members": len(p),
            "p_half_inch_pct": round(100.0 * sum(x > 0.5 for x in p) / len(p)),
            "median_in": round(statistics.median(p), 2),
            "p90_in": round(p[max(0, int(0.9 * len(p)) - 1)], 2),
            "max_in": round(p[-1], 2),
            "gust_median_mph": round(statistics.median(g)) if g else None,
            "gust_p90_mph": round(g[max(0, int(0.9 * len(g)) - 1)]) if g else None,
            "gust_max_mph": round(g[-1]) if g else None,
        }
    if not out["models"]:
        raise ValueError("cross-check response has no daily rows")
    out["summary"] = (f"{len(out['models'])} days x {len(XCHECK_MODELS)} models"
                      + (f", ensemble n={next(iter(out['ensemble'].values()))['members']}"
                         if out["ensemble"] else ", ensemble unavailable"))
    return out


def fetch_openmeteo(lat=HOUSE_LAT, lon=HOUSE_LON, days=8, timeout=30, deadline=None):
    common = {"latitude": f"{lat:.4f}", "longitude": f"{lon:.4f}", "forecast_days": days,
              "timezone": "America/New_York", "wind_speed_unit": "mph",
              "precipitation_unit": "inch"}
    t = _next_timeout(deadline, timeout)
    if t is None:
        raise TimeoutError("outlook budget spent before the cross-check request")
    models = _get_json(OPEN_METEO_URL + "?" + urlencode({
        **common, "daily": "precipitation_sum,wind_gusts_10m_max",
        "models": ",".join(m for m, _ in XCHECK_MODELS)}), t)
    ens = {}
    t = _next_timeout(deadline, timeout)
    if t is not None:
        try:
            ens = _get_json(OPEN_METEO_ENS_URL + "?" + urlencode({
                **common, "daily": "precipitation_sum,wind_gusts_10m_max",
                "models": "gfs_seamless"}), t)
        except Exception:
            ens = {}
    return parse_openmeteo(models, ens)


# ---------------------------------------------------------------------------
# warm-file guidance: producer (warm job) and admission (hourly run)
# ---------------------------------------------------------------------------
def load_guidance(path):
    try:
        with open(path) as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_guidance(path, data):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=1, sort_keys=True)
    os.replace(tmp, path)


def fetch_guidance(now_utc, existing=None, qmd_budget_s=480.0):
    """Warm job: refetch every expensive source; on a failure keep the
    previous copy (its own cycle stamp decides admission later)."""
    existing = existing or {}
    out = {"fetched_at": _stamp(now_utc), "errors": {}}
    horizon_end = now_utc + dt.timedelta(hours=HORIZON_HOURS + 6)
    for key, fn in (("nbm", lambda: fetch_nbm_qpf(now_utc, horizon_end)),
                    ("petss", lambda: fetch_petss(now_utc)),
                    ("wpc", lambda: fetch_wpc_qpf(now_utc))):
        try:
            out[key] = fn()
        except Exception as e:
            out["errors"][key] = f"{type(e).__name__}: {e}"
            out[key] = existing.get(key)
    prev_qmd = existing.get("nbm_qmd") or {}
    try:
        newest = newest_qmd_cycle(now_utc)
        if newest is None:
            raise RuntimeError("no NBM qmd cycle published in the last 30 h")
        needed = nbm_steps_to_cover(newest, horizon_end)
        if (prev_qmd.get("qmd_cycle") == _stamp(newest)
                and len(prev_qmd.get("buckets") or {}) >= len(needed)):
            out["nbm_qmd"] = prev_qmd
            out["errors"]["nbm_qmd"] = "unchanged: newest cycle already on disk"
        else:
            out["nbm_qmd"] = fetch_nbm_qmd(now_utc, cycle=newest, steps=needed,
                                           time_budget_s=qmd_budget_s)
    except Exception as e:
        out["errors"]["nbm_qmd"] = f"{type(e).__name__}: {e}"
        out["nbm_qmd"] = prev_qmd or None
    return out


def _cycle_age_h(data, key, now_utc):
    stamp = (data or {}).get("qmd_cycle" if key == "nbm_qmd" else "cycle")
    when = _parse_iso(stamp)
    return None if when is None else (now_utc - when).total_seconds() / 3600.0


def admit_guidance(guidance, key, now_utc):
    """(data or None, health) for one warm-file source by CYCLE age and
    structural validity (R4). Unavailable data is never returned."""
    data = (guidance or {}).get(key)
    if not data:
        return None, {"status": "unavailable", "detail": f"{key}: not in the warm file",
                      "issued": None, "age_h": None}
    age_h = _cycle_age_h(data, key, now_utc)
    ok_h, deg_h = GUIDANCE_AGE_H[key]
    stamp = data.get("cycle")
    if age_h is None or age_h < -1.0 or age_h > deg_h:
        return None, {"status": "unavailable",
                      "detail": (f"{key} cycle {stamp} " + ("unparseable" if age_h is None
                                 else f"{age_h:.1f} h old, expired")),
                      "issued": stamp, "age_h": round(age_h, 2) if age_h is not None else None}
    buckets = data.get("buckets")
    dropped = 0
    if key in ("nbm", "wpc"):
        good = []
        for b in (buckets or []):
            ok = (isinstance(b, dict) and _parse_iso(b.get("end_utc")) is not None
                  and _finite(b.get("hours")) and 0 < b["hours"] <= 48
                  and _finite(b.get("qpf_in")) and b["qpf_in"] >= 0
                  and (b.get("pop_pct") is None or (_finite(b["pop_pct"]) and 0 <= b["pop_pct"] <= 100)))
            if ok:
                good.append(b)
            else:
                dropped += 1
        good.sort(key=lambda b: _parse_iso(b["end_utc"]))
        if not good:
            return None, {"status": "unavailable", "detail": f"{key}: no valid buckets ({dropped} malformed dropped)",
                          "issued": stamp, "age_h": round(age_h, 2)}
        data = dict(data, buckets=good)
        future = sum(1 for b in good if _parse_iso(b["end_utc"]) > now_utc)
        coverage = f"{future} future buckets" + (f", {dropped} malformed dropped" if dropped else "")
    else:  # petss: every point parseable, finite, and p10 <= p90 where both exist
        p10, p90 = [], []
        for name, dst in (("p10", p10), ("p90", p90)):
            for pt in (data.get(name) or []):
                if isinstance(pt, dict) and _parse_iso(pt.get("utc")) is not None \
                        and _finite(pt.get("surge_ft")) and -10 < pt["surge_ft"] < 30:
                    dst.append(pt)
                else:
                    dropped += 1
        lo_by = {q["utc"]: q["surge_ft"] for q in p10}
        p90 = [q for q in p90 if lo_by.get(q["utc"], -99) <= q["surge_ft"] + 0.05]
        if not (p10 and p90):
            return None, {"status": "unavailable", "detail": f"petss: no valid percentile series ({dropped} malformed dropped)",
                          "issued": stamp, "age_h": round(age_h, 2)}
        data = dict(data, p10=sorted(p10, key=lambda q: q["utc"]), p90=sorted(p90, key=lambda q: q["utc"]))
        future = sum(1 for q in data["p90"] if _parse_iso(q["utc"]) > now_utc)
        coverage = f"{future} future hours" + (f", {dropped} malformed dropped" if dropped else "")
    status = "ok" if (age_h <= ok_h and not dropped) else "degraded"   # any dropped row is visible (round 03 S6)
    return data, {"status": status,
                  "detail": f"{data.get('summary', key)}; cycle {age_h:.1f} h old; {coverage}",
                  "issued": stamp, "age_h": round(age_h, 2)}


def _quick_sources(now_utc, dl):
    return (
        ("astro", lambda t: fetch_astro_highs(now_utc, timeout=t)),
        ("astro_hourly", lambda t: fetch_astro_hourly(now_utc, timeout=t)),
        ("grid", lambda t: fetch_nws_grid(timeout=t, deadline=dl)),
        ("nwps", lambda t: fetch_nwps_forecast(now_utc, timeout=t)),
        ("xcheck", lambda t: fetch_openmeteo(timeout=t, deadline=dl)),
    )


def gather(now_utc, guidance_path=None, deadline=None, wall_clock_s=None):
    """Hourly run: quick requests under one deadline INSIDE a wall-clock
    isolation boundary (round 03 S7), plus admission of the warm file's
    sources. Never raises; every source carries health.

    The quick fetches run in a daemon worker thread; the caller waits at
    most `wall_clock_s` (default: the deadline's budget plus one request
    cap). Whatever has not completed by then is reported "unavailable:
    wall-clock budget" and the worker is abandoned, so a slowly progressing
    response body cannot hold the alert path beyond the boundary.
    """
    import threading
    dl = deadline or Deadline(OUTLOOK_FETCH_BUDGET_S)
    wall = wall_clock_s if wall_clock_s is not None else dl.seconds + PER_REQUEST_CAP_S
    data, health, scratch = {}, {}, {}
    done = {}
    lock = threading.Lock()

    def work():
        for key, fn in _quick_sources(now_utc, dl):
            d, h = refresh(scratch, key, fn, now_utc, deadline=dl)
            with lock:
                done[key] = (d, h)
    worker = threading.Thread(target=work, name="outlook-quick-sources", daemon=True)
    worker.start()
    worker.join(max(0.0, wall))
    with lock:
        finished = dict(done)
    for key, _fn in _quick_sources(now_utc, dl):
        if key in finished:
            data[key], health[key] = finished[key]
        else:
            data[key], health[key] = None, {"status": "unavailable",
                                            "detail": f"skipped: outlook wall-clock budget ({wall:.1f} s) exhausted",
                                            "fetched_at": None, "age_h": None}
    g = load_guidance(guidance_path or GUIDANCE_PATH_DEFAULT)
    for key in ("nbm", "petss", "wpc"):
        data[key], health[key] = admit_guidance(g, key, now_utc)
    data["nbm_qmd"] = g.get("nbm_qmd")
    health["nbm_qmd"] = merge_nbm_qmd(data.get("nbm"), data["nbm_qmd"], now_utc)
    used = dl.seconds - max(0.0, dl.remaining())
    health["_budget"] = {"status": "ok" if worker.is_alive() is False else "degraded",
                         "detail": (f"{used:.1f} s of {dl.seconds:.0f} s used"
                                    + ("" if not worker.is_alive() else "; worker abandoned at the wall-clock boundary"))}
    return data, health
