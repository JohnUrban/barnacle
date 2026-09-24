"""Trailing 365-day mean surge at Sandy Hook for the v0.10.6 surge decay.

Computed by the warm job (outlook_warm.py, every 3 h; recomputed at most
once per MIN_RECOMPUTE_H) and saved to data/surge_mean.json; the hourly
run only reads it (surge_decay.resolve_mean age-gates it and falls back to
a documented constant). Two CO-OPS requests: verified `hourly_height`
(lags ~3 weeks) and hourly `predictions` for the last 364 days (the API's
365-day limit). The mean is over hours with both values.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import os
import urllib.parse
import urllib.request

STATION = "8531680"
COOPS = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
UA = os.environ.get("USER_AGENT", "barnacle-flood-forecast (github.com/JohnUrban/barnacle)")
PATH_DEFAULT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "data", "surge_mean.json")
WINDOW_DAYS = 364
MIN_RECOMPUTE_H = 20.0


def _get(params, timeout):
    q = {"station": STATION, "time_zone": "gmt", "units": "english", "datum": "MLLW",
         "format": "json", "application": "barnacle", **params}
    req = urllib.request.Request(COOPS + "?" + urllib.parse.urlencode(q), headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def compute(now_utc, timeout=60, get=_get):
    begin = (now_utc - dt.timedelta(days=WINDOW_DAYS)).strftime("%Y%m%d")
    end = now_utc.strftime("%Y%m%d")
    obs = get({"product": "hourly_height", "begin_date": begin, "end_date": end}, timeout)
    prd = get({"product": "predictions", "interval": "h", "begin_date": begin, "end_date": end}, timeout)
    o = {}
    for r in obs.get("data") or []:
        try:
            v = float(r["v"])
        except (KeyError, TypeError, ValueError):
            continue
        if math.isfinite(v):
            o[r["t"]] = v
    diffs, times = [], []
    for r in prd.get("predictions") or []:
        if r.get("t") in o:
            try:
                pv = float(r["v"])
            except (TypeError, ValueError):
                continue
            if not math.isfinite(pv):
                continue                    # R4: a non-finite prediction never enters the mean
            diffs.append(o[r["t"]] - pv)
            times.append(r["t"])
    if len(diffs) < 24 * 300:
        raise ValueError(f"only {len(diffs)} paired hours in the trailing window")
    mean = sum(diffs) / len(diffs)
    if not (math.isfinite(mean) and -2.0 < mean < 3.0):
        raise ValueError(f"implausible trailing mean {mean!r}")   # keeps the previous good record
    return {"mean_ft": round(mean, 4), "n_hours": len(diffs),
            "window_start": min(times)[:10], "window_end": max(times)[:10],
            "computed_utc": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "method": "mean of verified hourly_height minus hourly predictions, last 364 days"}


def load(path=PATH_DEFAULT):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def refresh(now_utc, path=PATH_DEFAULT, timeout=60, get=_get):
    """Recompute unless the saved record is younger than MIN_RECOMPUTE_H.
    Returns (record, note). A failure keeps the previous record."""
    old = load(path)
    try:
        age_h = (now_utc - dt.datetime.fromisoformat(old["computed_utc"].replace("Z", "+00:00"))).total_seconds() / 3600
        if 0 <= age_h < MIN_RECOMPUTE_H:
            return old, f"kept ({age_h:.1f} h old)"
    except (TypeError, KeyError, ValueError, AttributeError):
        pass
    try:
        rec = compute(now_utc, timeout=timeout, get=get)
    except Exception as e:  # noqa: BLE001
        return old, f"recompute failed ({type(e).__name__}: {e}); kept previous"
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(rec, f, indent=1, sort_keys=True)
        f.write("\n")
    os.replace(tmp, path)
    return rec, "recomputed"
