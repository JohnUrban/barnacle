#!/usr/bin/env python3
"""7-day outlook data adapters (opened 2026-09-23, John's green light).

Every adapter returns plain JSON-safe data or raises; the caller wraps it
in `refresh()` which owns the cache, the TTL and the health status
(AGENTS rule 7: unavailable is never zero). No adapter imports the
production facade; station-time helpers come from station_time.

Sources and their verified reach (2026-09-23):
  astro   NOAA CO-OPS hi/lo predictions              any range
  grid    NWS gridpoint wind / gust / direction / PoP  ~7 d; QPF ~72 h
  nwps    NWS water-prediction gauge forecast SDHN4    72 h hourly (MLLW)
  petss   P-ETSS GEFS-based storm SURGE, 10th/90th pct 102 h hourly (text)
  nbm     National Blend of Models 6-h QPF + PoP       out to 264 h (GRIB2
          subset via the NOMADS filter; needs eccodes)
  wpc     WPC 24-h QPF, days 2-7 (GRIB, fallback)
  xcheck  non-NOAA multi-model + GEFS ensemble         7 d (cross-check only)
"""

import datetime as dt
import json
import math
import os
import re
import statistics
import tempfile
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
NBM_STEPS = tuple(range(6, HORIZON_HOURS + 1, 6))       # 28 subsets
WPC_STEPS = (48, 72, 96, 120, 144, 168)                 # 24-h totals
# House-centred subset box for the NBM filter (2.5 km grid -> ~80 points)
NBM_BOX = {"toplat": 40.5, "bottomlat": 40.3, "leftlon": -74.1, "rightlon": -73.9}

# Refetch when the cached copy is older than TTL; keep serving a stale copy
# (status "degraded") up to MAX_STALE when the refetch fails.
TTL_H = {"astro": 1, "astro_hourly": 1, "grid": 1, "nwps": 1, "petss": 3, "nbm": 3,
         "wpc": 6, "xcheck": 3}
MAX_STALE_H = {"astro": 48, "astro_hourly": 48, "grid": 12, "nwps": 12, "petss": 12,
               "nbm": 12, "wpc": 30, "xcheck": 12}

MM_PER_IN = 25.4
MPH_PER_KMH = 0.621371


# ---------------------------------------------------------------------------
# transport
# ---------------------------------------------------------------------------
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


def _iso_duration_hours(text):
    """'PT6H' -> 6, 'P3DT22H' -> 94, 'P1D' -> 24, 'PT30M' -> 0.5."""
    m = re.match(r"^P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?)?$", text or "")
    if not m:
        raise ValueError(f"unsupported ISO duration {text!r}")
    days, hours, minutes = (int(x) if x else 0 for x in m.groups())
    return days * 24 + hours + minutes / 60.0


# ---------------------------------------------------------------------------
# cache
# ---------------------------------------------------------------------------
def load_cache(path):
    try:
        with open(path) as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_cache(path, cache):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(cache, f, indent=1, sort_keys=True)
    os.replace(tmp, path)


def refresh(cache, key, fetch_fn, now_utc, ttl_h=None, max_stale_h=None):
    """(data, health) for one source, honouring the cache contract.

    health = {"status": ok|degraded|unavailable, "detail": str,
              "fetched_at": iso|None, "age_h": float|None}
    """
    ttl_h = TTL_H[key] if ttl_h is None else ttl_h
    max_stale_h = MAX_STALE_H[key] if max_stale_h is None else max_stale_h
    entry = cache.get(key) or {}
    fetched = _parse_iso(entry.get("fetched_at"))
    age_h = ((now_utc - fetched).total_seconds() / 3600.0) if fetched else None
    data = entry.get("data")
    if data is not None and age_h is not None and 0 <= age_h < ttl_h:
        return data, {"status": "ok",
                      "detail": f"{data.get('summary', 'cached')} (cache {age_h:.1f} h)",
                      "fetched_at": entry.get("fetched_at"), "age_h": round(age_h, 2)}
    try:
        fresh = fetch_fn()
    except Exception as e:  # transport, parse, decoder missing: all reported
        if data is not None and age_h is not None and age_h <= max_stale_h:
            return data, {"status": "degraded",
                          "detail": (f"refetch failed ({type(e).__name__}: {e}); "
                                     f"serving cached copy {age_h:.1f} h old"),
                          "fetched_at": entry.get("fetched_at"), "age_h": round(age_h, 2)}
        return None, {"status": "unavailable",
                      "detail": f"fetch failed ({type(e).__name__}: {e})",
                      "fetched_at": None, "age_h": None}
    stamp = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    cache[key] = {"fetched_at": stamp, "data": fresh}
    return fresh, {"status": "ok", "detail": fresh.get("summary", "fresh"),
                   "fetched_at": stamp, "age_h": 0.0}


# ---------------------------------------------------------------------------
# astro: NOAA CO-OPS hi/lo predictions
# ---------------------------------------------------------------------------
def fetch_astro_highs(now_utc, hours=HORIZON_HOURS + 6):
    begin = (now_utc - dt.timedelta(hours=2)).strftime("%Y%m%d %H:%M")
    params = dict(product="predictions", application="barnacle-outlook",
                  begin_date=begin, range=int(hours + 2), datum="MLLW",
                  station=SANDY_HOOK_STATION, time_zone="gmt", units="english",
                  interval="hilo", format="json")
    data = _get_json(COOPS_URL + "?" + urlencode(params))
    highs = []
    for p in data.get("predictions") or []:
        if p.get("type") != "H":
            continue
        gmt = p["t"]
        when = dt.datetime.strptime(gmt, "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc)
        highs.append({"utc": when.strftime("%Y-%m-%dT%H:%M:%SZ"),
                      "time": noaa_gmt_to_station_string(gmt),
                      "mllw": round(float(p["v"]), 3)})
    if not highs:
        raise ValueError("no high tides in CO-OPS response")
    return {"highs": highs, "summary": f"{len(highs)} astronomical highs"}


def fetch_astro_hourly(now_utc, hours_back=6, hours=HORIZON_HOURS):
    """Hourly astronomical predictions (ft MLLW) from -hours_back to +hours:
    the backbone of the continuous 7-day water series."""
    begin = (now_utc - dt.timedelta(hours=hours_back)).strftime("%Y%m%d %H:%M")
    params = dict(product="predictions", application="barnacle-outlook",
                  begin_date=begin, range=int(hours + hours_back + 1), datum="MLLW",
                  station=SANDY_HOOK_STATION, time_zone="gmt", units="english",
                  interval="h", format="json")
    data = _get_json(COOPS_URL + "?" + urlencode(params))
    pts = []
    for p in data.get("predictions") or []:
        gmt = p["t"]
        when = dt.datetime.strptime(gmt, "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc)
        pts.append({"utc": when.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "time": noaa_gmt_to_station_string(gmt),
                    "mllw": round(float(p["v"]), 3)})
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
            out.append({"start": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "hours": _iso_duration_hours(dur),
                        "value": (round(conv(val), 3) if val is not None else None)})
        series[name] = out
    last = {}
    for name, rows in series.items():
        if rows:
            end = _parse_iso(rows[-1]["start"]) + dt.timedelta(hours=rows[-1]["hours"])
            last[name] = end.strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"update_time": props.get("updateTime"), "series": series, "reach": last,
            "summary": ("grid QPF to " + last.get("qpf_in", "?")[:13] + "Z, wind to "
                        + last.get("gust_mph", "?")[:13] + "Z")}


def fetch_nws_grid(lat=HOUSE_LAT, lon=HOUSE_LON):
    pts = _get_json(NWS_POINTS_URL.format(lat=lat, lon=lon))
    grid_url = pts["properties"]["forecastGridData"]
    return parse_nws_grid(_get_json(grid_url)["properties"])


def grid_value_at(series, when_utc):
    """Value of a grid series covering `when_utc` (bucket start <= t < end)."""
    for row in series or []:
        start = _parse_iso(row["start"])
        if start <= when_utc < start + dt.timedelta(hours=row["hours"]):
            return row["value"]
    return None


# ---------------------------------------------------------------------------
# nwps: NWS water-prediction gauge forecast (SDHN4, ft MLLW, hourly, 72 h)
# ---------------------------------------------------------------------------
def parse_nwps(doc):
    f = doc.get("forecast") or {}
    pts = []
    for x in f.get("data") or []:
        v = x.get("primary")
        if v is None or v <= -900:
            continue
        pts.append({"utc": x["validTime"], "ft": round(float(v), 3)})
    if not pts:
        raise ValueError("NWPS forecast has no points")
    return {"issued": f.get("issuedTime"), "units": f.get("primaryUnits"),
            "series": pts,
            "summary": f"{len(pts)} hourly points issued {f.get('issuedTime')}"}


def fetch_nwps_forecast(gauge=NWPS_GAUGE):
    return parse_nwps(_get_json(NWPS_URL.format(gauge=gauge)))


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
    """Hourly surge (ft) for one station from a P-ETSS text product.

    Row layout: the third header line names the first column's hour
    ("07Z" for a 06Z cycle), i.e. value i is valid at cycle + (i+1) h.
    Values are tenths of a foot; |v| >= 300 (e.g. -400) is missing.
    """
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
        t = cycle_utc + dt.timedelta(hours=i + 1)
        series.append({"utc": t.strftime("%Y-%m-%dT%H:%M:%SZ"), "surge_ft": v})
    return series


def _petss_cycles(now_utc):
    """Candidate (cycle_utc) newest first, at least 90 min old."""
    out = []
    for back in (0, 1):
        day = (now_utc - dt.timedelta(days=back)).date()
        for hh in (18, 12, 6, 0):
            c = dt.datetime(day.year, day.month, day.day, hh, tzinfo=dt.timezone.utc)
            if c <= now_utc - dt.timedelta(minutes=90):
                out.append(c)
    return sorted(out, reverse=True)


def fetch_petss(now_utc):
    last_err = None
    for cycle in _petss_cycles(now_utc)[:4]:
        try:
            out = {"cycle": cycle.strftime("%Y-%m-%dT%H:%M:%SZ")}
            # P-ETSS files are named by EXCEEDANCE probability: e10 is the
            # value exceeded by only 10 % of members (the HIGH end, our
            # p90); e90 is exceeded by 90 % (the LOW end, our p10).
            for pct, key in (("e90", "p10"), ("e10", "p90")):
                url = PETSS_URL.format(ymd=cycle.strftime("%Y%m%d"), hh=cycle.hour, pct=pct)
                text = _request(url, timeout=120).decode("ascii", "replace")
                out[key] = parse_petss_station(text, cycle)
            if any(a["surge_ft"] > b["surge_ft"] + 0.05
                   for a, b in zip(out["p10"], out["p90"])):
                raise ValueError("P-ETSS p10 exceeds p90: exceedance mapping wrong")
            n = len(out["p90"])
            out["summary"] = (f"P-ETSS cycle {out['cycle'][:13]}Z, {n} h, "
                              f"p10/p90 surge")
            return out
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"no P-ETSS cycle readable: {last_err}")


# ---------------------------------------------------------------------------
# GRIB helpers (eccodes; installed by forecast/requirements.txt)
# ---------------------------------------------------------------------------
def _grib_messages(raw):
    """Yield dicts for every message in a GRIB byte string (needs eccodes)."""
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
                    yield {
                        "template": g("productDefinitionTemplateNumber"),
                        "length_h": g("lengthOfTimeRange"),
                        "end_step": g("endStep"),
                        "units": g("units"),
                        "short_name": g("shortName"),
                        "lats": ec.codes_get_array(gid, "latitudes"),
                        "lons": ec.codes_get_array(gid, "longitudes"),
                        "values": ec.codes_get_values(gid),
                    }
                finally:
                    ec.codes_release(gid)
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def _nearest_value(msg, lat=HOUSE_LAT, lon=HOUSE_LON):
    """Value at the grid point nearest the house (vectorized: WPC files
    carry 3.4 M points)."""
    import numpy as np   # eccodes depends on numpy; keep the import local
    lats = np.asarray(msg["lats"], dtype=float)
    lons = np.asarray(msg["lons"], dtype=float)
    lons = np.where(lons > 180.0, lons - 360.0, lons)
    coslat = math.cos(math.radians(lat))
    d = (lats - lat) ** 2 + ((lons - lon) * coslat) ** 2
    i = int(np.argmin(d))
    return float(msg["values"][i])


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
    params = {
        "dir": f"/blend.{cycle_utc:%Y%m%d}/{cycle_utc:%H}/core",
        "file": f"blend.t{cycle_utc:%H}z.core.f{fhour:03d}.co.grib2",
        "all_lev": "on", "var_APCP": "on", "subregion": "",
        **NBM_BOX,
    }
    return NBM_FILTER_URL + "?" + urlencode(params)


def parse_nbm_subset(raw):
    """{'qpf_in': 6-h amount, 'pop_pct': 6-h probability} at the house."""
    out = {"qpf_in": None, "pop_pct": None}
    for msg in _grib_messages(raw):
        if msg["length_h"] != 6:
            continue
        v = _nearest_value(msg)
        if msg["template"] == 8:          # deterministic accumulation
            out["qpf_in"] = _precip_inches(v, msg["units"])
        elif msg["template"] == 9:        # probability of exceedance (PoP)
            out["pop_pct"] = round(v, 1) if v is not None else None
    if out["qpf_in"] is None:
        raise ValueError("no 6-h APCP message in NBM subset")
    return out


# Exceedance thresholds we keep from the NBM probabilistic (qmd) file,
# in inches per 6 h -> field name.
NBM_EXCEEDANCE_IN = {0.25: "p_ge_quarter_in_pct", 0.5: "p_ge_half_in_pct", 1.0: "p_ge_1in_pct"}
NBM_PERCENTILES = (10, 50, 90)


def nbm_qmd_subset_url(cycle_utc, fhour):
    params = {
        "dir": f"/blend.{cycle_utc:%Y%m%d}/{cycle_utc:%H}/qmd",
        "file": f"blend.t{cycle_utc:%H}z.qmd.f{fhour:03d}.co.grib2",
        "var_APCP": "on", "all_lev": "on", "subregion": "",   # precip-only: ~9 s, not ~54 s
        **NBM_BOX,
    }
    return NBM_FILTER_URL + "?" + urlencode(params)


def parse_nbm_qmd_subset(raw):
    """6-h rain percentiles (in) and exceedance probabilities (%) at the
    house from an NBM qmd subset. Percentiles are GRIB template 10
    (percentileValue); exceedances are template 9 with an upper limit
    scaled as value x 10^-factor mm."""
    try:
        import eccodes as ec
    except ImportError as e:
        raise RuntimeError("GRIB decoder not installed (eccodes)") from e
    out = {f"p{q}_in": None for q in NBM_PERCENTILES}
    out.update({name: None for name in NBM_EXCEEDANCE_IN.values()})
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
                    if not (g("parameterCategory") == 1 and g("parameterNumber") == 8
                            and g("lengthOfTimeRange") == 6):
                        continue
                    tmpl = g("productDefinitionTemplateNumber")
                    msg = {"lats": ec.codes_get_array(gid, "latitudes"),
                           "lons": ec.codes_get_array(gid, "longitudes"),
                           "values": ec.codes_get_values(gid)}
                    if tmpl == 10 and g("percentileValue") in NBM_PERCENTILES:
                        out[f"p{g('percentileValue')}_in"] = _precip_inches(_nearest_value(msg), g("units"))
                    elif tmpl == 9 and g("probabilityType") == 1:
                        sv, sf = g("scaledValueOfUpperLimit"), g("scaleFactorOfUpperLimit")
                        if sv is None or sf is None:
                            continue
                        thr_in = round(sv * (10.0 ** -sf) / MM_PER_IN, 3)
                        for thr, name in NBM_EXCEEDANCE_IN.items():
                            if abs(thr_in - thr) < 0.02:
                                out[name] = round(_nearest_value(msg), 1)
                finally:
                    ec.codes_release(gid)
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
    if out["p90_in"] is None:
        raise ValueError("no 6-h percentile messages in NBM qmd subset")
    return out


NBM_QMD_PATH_DEFAULT = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "data", "outlook_nbm_qmd.json"))
NBM_QMD_OK_AGE_H = 9.0        # a fresh synoptic cycle every ~6 h plus lag
NBM_QMD_STALE_AGE_H = 30.0


def newest_qmd_cycle(now_utc):
    """Newest 00/06/12/18Z cycle whose probabilistic file is published."""
    base = now_utc.replace(hour=(now_utc.hour // 6) * 6, minute=0, second=0, microsecond=0)
    for back in range(0, 30, 6):
        c = base - dt.timedelta(hours=back)
        try:
            raw = _request(nbm_qmd_subset_url(c, 6), timeout=90)
        except Exception:
            continue
        if raw[:4] == b"GRIB":
            return c
    return None


def fetch_nbm_qmd(now_utc, steps=NBM_STEPS, time_budget_s=None):
    """Percentiles + exceedance chances per 6-h bucket from the newest
    published synoptic cycle, keyed by valid END time. ~9 s per step, so
    this runs in its own warm job (nbm_qmd.yml), never in the hourly run."""
    import time as _time
    qcycle = newest_qmd_cycle(now_utc)
    if qcycle is None:
        raise RuntimeError("no NBM qmd cycle published in the last 30 h")
    started = _time.time()
    buckets, missing = {}, []
    for fh in steps:
        if time_budget_s is not None and _time.time() - started > time_budget_s:
            missing.append(f"f{fh:03d}: time budget")
            continue
        end = qcycle + dt.timedelta(hours=fh)
        try:
            got = parse_nbm_qmd_subset(_request(nbm_qmd_subset_url(qcycle, fh), timeout=90))
        except Exception as e:
            missing.append(f"f{fh:03d}: {type(e).__name__}")
            continue
        buckets[end.strftime("%Y-%m-%dT%H:%M:%SZ")] = got
    if not buckets:
        raise RuntimeError(f"NBM qmd: no buckets decoded ({missing[:3]})")
    return {"qmd_cycle": qcycle.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "fetched_at": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "buckets": buckets, "missing": missing,
            "summary": f"NBM qmd {qcycle:%Y-%m-%dT%H}Z: {len(buckets)}/{len(steps)} buckets"}


def load_nbm_qmd(path):
    try:
        with open(path) as f:
            data = json.load(f)
        return data if isinstance(data, dict) and data.get("buckets") else None
    except (OSError, ValueError):
        return None


def merge_nbm_qmd(nbm, qmd, now_utc):
    """Attach percentile fields to NBM amount buckets by valid end time.
    Returns a health dict for the qmd file (age-based)."""
    if not qmd:
        return {"status": "unavailable", "detail": "no NBM percentile file yet",
                "fetched_at": None, "age_h": None}
    fetched = _parse_iso(qmd.get("fetched_at"))
    age_h = ((now_utc - fetched).total_seconds() / 3600.0) if fetched else None
    n = 0
    for b in (nbm or {}).get("buckets") or []:
        q = (qmd.get("buckets") or {}).get(b["end_utc"])
        if q:
            b.update({k: v for k, v in q.items() if k != "summary"})
            n += 1
    if age_h is None or age_h > NBM_QMD_STALE_AGE_H:
        status = "unavailable"
    elif age_h > NBM_QMD_OK_AGE_H:
        status = "degraded"
    else:
        status = "ok"
    return {"status": status,
            "detail": (f"percentiles from NBM {str(qmd.get('qmd_cycle', ''))[:13]}Z on {n} buckets"
                       + (f", file {age_h:.1f} h old" if age_h is not None else "")),
            "fetched_at": qmd.get("fetched_at"), "age_h": round(age_h, 2) if age_h is not None else None}


def fetch_nbm_qpf(now_utc, steps=NBM_STEPS):
    cycle = None
    last_err = None
    for lag in range(3, 10):
        c = (now_utc - dt.timedelta(hours=lag)).replace(minute=0, second=0, microsecond=0)
        try:
            raw = _request(nbm_subset_url(c, steps[0]), timeout=60)
            if raw[:4] != b"GRIB":
                raise ValueError("not GRIB")
            cycle = c
            first = parse_nbm_subset(raw)
            break
        except Exception as e:
            last_err = e
    if cycle is None:
        raise RuntimeError(f"no NBM cycle available: {last_err}")
    buckets, missing = [], []
    for fh in steps:
        try:
            got = first if fh == steps[0] else parse_nbm_subset(
                _request(nbm_subset_url(cycle, fh), timeout=60))
        except Exception as e:
            missing.append(f"f{fh:03d}: {type(e).__name__}")
            continue
        end = cycle + dt.timedelta(hours=fh)
        buckets.append({"end_utc": end.strftime("%Y-%m-%dT%H:%M:%SZ"), "hours": 6,
                        "qpf_in": got["qpf_in"], "pop_pct": got["pop_pct"]})
    if len(buckets) < len(steps) // 2:
        raise RuntimeError(f"NBM: only {len(buckets)}/{len(steps)} buckets ({missing[:3]})")
    return {"cycle": cycle.strftime("%Y-%m-%dT%H:%M:%SZ"), "buckets": buckets,
            "missing": missing,
            "summary": (f"NBM cycle {cycle:%Y-%m-%dT%H}Z, {len(buckets)}/{len(steps)} "
                        f"6-h buckets to +{steps[-1]} h")}


# ---------------------------------------------------------------------------
# wpc: WPC 24-h QPF files (fallback)
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


def fetch_wpc_qpf(now_utc, steps=WPC_STEPS):
    last_err = None
    for cycle in _wpc_cycles(now_utc)[:2]:
        buckets, missing = [], []
        for fh in steps:
            url = WPC_QPF_URL.format(ymd=cycle.strftime("%Y%m%d"), hh=cycle.hour, fff=fh)
            try:
                qpf = parse_wpc_file(_request(url, timeout=90))
            except Exception as e:
                missing.append(f"f{fh:03d}: {type(e).__name__}")
                last_err = e
                continue
            end = cycle + dt.timedelta(hours=fh)
            buckets.append({"end_utc": end.strftime("%Y-%m-%dT%H:%M:%SZ"), "hours": 24,
                            "qpf_in": qpf})
        if buckets:
            return {"cycle": cycle.strftime("%Y-%m-%dT%H:%M:%SZ"), "buckets": buckets,
                    "missing": missing,
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
            p = (dd.get(f"precipitation_sum_{api_name}") or [None])[i] if i < len(dd.get(f"precipitation_sum_{api_name}") or []) else None
            g = (dd.get(f"wind_gusts_10m_max_{api_name}") or [None])[i] if i < len(dd.get(f"wind_gusts_10m_max_{api_name}") or []) else None
            row[short] = {"precip_in": p, "gust_mph": g}
        out["models"][day] = row
    ed = ens_doc.get("daily") or {}
    pk = [k for k in ed if k.startswith("precipitation_sum")]
    gk = [k for k in ed if k.startswith("wind_gusts_10m_max")]
    for i, day in enumerate(ed.get("time") or []):
        p = sorted(v for v in (ed[k][i] for k in pk if i < len(ed[k])) if v is not None)
        g = sorted(v for v in (ed[k][i] for k in gk if i < len(ed[k])) if v is not None)
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


def fetch_openmeteo(lat=HOUSE_LAT, lon=HOUSE_LON, days=8):
    common = {"latitude": f"{lat:.4f}", "longitude": f"{lon:.4f}", "forecast_days": days,
              "timezone": "America/New_York", "wind_speed_unit": "mph",
              "precipitation_unit": "inch"}
    models = _get_json(OPEN_METEO_URL + "?" + urlencode({
        **common, "daily": "precipitation_sum,wind_gusts_10m_max",
        "models": ",".join(m for m, _ in XCHECK_MODELS)}))
    try:
        ens = _get_json(OPEN_METEO_ENS_URL + "?" + urlencode({
            **common, "daily": "precipitation_sum,wind_gusts_10m_max",
            "models": "gfs_seamless"}), timeout=45)
    except Exception:
        ens = {}
    return parse_openmeteo(models, ens)


# ---------------------------------------------------------------------------
# orchestration
# ---------------------------------------------------------------------------
PERSISTED_KEYS = ("petss", "nbm", "wpc")   # the expensive, slow-changing sources


def gather(now_utc, cache, nbm_needed=True, nbm_qmd_path=None):
    """Fetch every source through the cache contract. Returns (data, health).

    Only PERSISTED_KEYS live in the on-disk cache (data/outlook_cache.json,
    committed hourly by the bot): P-ETSS and NBM change every few hours
    and cost 28 NOMADS requests, so they are worth carrying between runs.
    The cheap single-request sources use a throwaway cache so they are
    always fresh and never add commit churn.
    """
    data, health = {}, {}
    scratch = {}
    for key in [k for k in list(cache) if k not in PERSISTED_KEYS]:
        cache.pop(key, None)
    data["astro"], health["astro"] = refresh(scratch, "astro", lambda: fetch_astro_highs(now_utc), now_utc)
    data["astro_hourly"], health["astro_hourly"] = refresh(
        scratch, "astro_hourly", lambda: fetch_astro_hourly(now_utc), now_utc)
    data["grid"], health["grid"] = refresh(scratch, "grid", fetch_nws_grid, now_utc)
    data["nwps"], health["nwps"] = refresh(scratch, "nwps", fetch_nwps_forecast, now_utc)
    data["petss"], health["petss"] = refresh(cache, "petss", lambda: fetch_petss(now_utc), now_utc)
    data["nbm"], health["nbm"] = refresh(cache, "nbm", lambda: fetch_nbm_qpf(now_utc), now_utc)
    if data["nbm"] is None or health["nbm"]["status"] != "ok":
        data["wpc"], health["wpc"] = refresh(cache, "wpc", lambda: fetch_wpc_qpf(now_utc), now_utc)
    else:
        data["wpc"], health["wpc"] = None, {"status": "ok", "detail": "not needed (NBM fresh)",
                                            "fetched_at": None, "age_h": None}
    data["xcheck"], health["xcheck"] = refresh(scratch, "xcheck", fetch_openmeteo, now_utc)
    # NBM percentiles come from the warm job's file (nbm_qmd.yml), never
    # fetched here: 28 subsets at ~9 s each do not fit the hourly budget.
    qmd = load_nbm_qmd(nbm_qmd_path or NBM_QMD_PATH_DEFAULT)
    health["nbm_qmd"] = merge_nbm_qmd(data.get("nbm"), qmd, now_utc)
    data["nbm_qmd"] = qmd
    return data, health
