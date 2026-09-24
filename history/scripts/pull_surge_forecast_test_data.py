#!/usr/bin/env python3
"""Data for the archived-forecast wind test (2026-09-23), all saved under
history/data/forecast_test/ (git-ignored, regeneratable):

1. surge_hourly.parquet: Sandy Hook 8531680 surge = observed - predicted,
   2023-01-01 .. END. Observed = CO-OPS `water_level` (6-min, preliminary +
   verified) taken on the hour, so recent months are available; predicted =
   CO-OPS `predictions` hourly. The trailing 365-d mean needs 2023.
2. met_obs.parquet: observed wind (kn, deg FROM) and pressure (mb) at the
   station, same span (CO-OPS `wind`, `air_pressure`, hourly).
3. fcst_<model>.parquet: Open-Meteo previous-runs archive at the station
   (wind_speed_10m / wind_direction_10m / pressure_msl, `_previous_day1`
   and `_previous_day2`): the value for each hour from the model run ~24 h
   and ~48 h earlier. Archive starts 2024-02 (gfs_seamless), 2024-03 (ecmwf).
Resumable per chunk. Run: python3 history/scripts/pull_surge_forecast_test_data.py
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "history" / "data" / "forecast_test"
UA = "highlands-flood-history (dr.john.urban@gmail.com)"
STATION, LAT, LON = "8531680", 40.4669, -74.0094
COOPS = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
PREV = "https://previous-runs-api.open-meteo.com/v1/forecast"
BEGIN = dt.date(2023, 1, 1)
END = dt.date(2026, 9, 22)
MODELS = {"gfs_seamless": dt.date(2024, 2, 1), "ecmwf_ifs025": dt.date(2024, 3, 1)}


def get(url, tries=6):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=90) as r:
                return json.loads(r.read())
        except Exception as e:  # noqa: BLE001
            if i == tries - 1:
                raise
            time.sleep(2 ** i)


def chunks(a, b, days):
    while a <= b:
        e = min(a + dt.timedelta(days=days - 1), b)
        yield a, e
        a = e + dt.timedelta(days=1)


def coops(product, a, b, extra):
    q = {"product": product, "station": STATION, "begin_date": f"{a:%Y%m%d}", "end_date": f"{b:%Y%m%d}",
         "time_zone": "gmt", "units": "english", "format": "json", "application": "barnacle-research", **extra}
    return get(COOPS + "?" + urllib.parse.urlencode(q))


def cached(name, fn):
    path = OUT / "chunks" / name
    if path.exists():
        return pd.read_parquet(path)
    df = fn()
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    time.sleep(0.4)
    return df


def rows(payload, key="data"):
    return payload.get(key) or payload.get("predictions") or []


def pull_coops():
    obs, prd, wind, pres = [], [], [], []
    for a, b in chunks(BEGIN, END, 30):
        tag = f"{a:%Y%m%d}_{b:%Y%m%d}"
        obs.append(cached(f"wl_{tag}.parquet", lambda: pd.DataFrame(
            [{"timestamp": r["t"], "observed_mllw": r["v"]} for r in rows(coops("water_level", a, b, {"datum": "MLLW"}))])))
        prd.append(cached(f"pred_{tag}.parquet", lambda: pd.DataFrame(
            [{"timestamp": r["t"], "predicted_mllw": r["v"]} for r in rows(coops("predictions", a, b, {"datum": "MLLW", "interval": "h"}))])))
        wind.append(cached(f"wind_{tag}.parquet", lambda: pd.DataFrame(
            [{"timestamp": r["t"], "wind_speed_kn": r["s"], "wind_dir_deg": r["d"]} for r in rows(coops("wind", a, b, {"interval": "h"}))])))
        pres.append(cached(f"pres_{tag}.parquet", lambda: pd.DataFrame(
            [{"timestamp": r["t"], "pressure_mb": r["v"]} for r in rows(coops("air_pressure", a, b, {"interval": "h"}))])))
        print(f"  coops {tag}", flush=True)

    def cat(parts):
        d = pd.concat([p for p in parts if len(p)], ignore_index=True)
        d["timestamp"] = pd.to_datetime(d["timestamp"])
        for c in d.columns[1:]:
            d[c] = pd.to_numeric(d[c], errors="coerce")
        return d.drop_duplicates("timestamp").set_index("timestamp").sort_index()
    o = cat(obs)
    o = o[o.index.minute == 0]                         # on-the-hour 6-min value
    p = cat(prd)
    surge = o.join(p, how="inner")
    surge["surge_ft"] = surge.observed_mllw - surge.predicted_mllw
    surge = surge.asfreq("h")
    surge.reset_index().to_parquet(OUT / "surge_hourly.parquet", index=False)
    met = cat(wind).join(cat(pres), how="outer")
    met.reset_index().to_parquet(OUT / "met_obs.parquet", index=False)
    print(f"surge hours {surge.surge_ft.notna().sum()}, met hours {len(met)}", flush=True)


def pull_models():
    vars_ = [f"{v}_previous_day{d}" for d in (1, 2) for v in ("wind_speed_10m", "wind_direction_10m", "pressure_msl")]
    for model, start in MODELS.items():
        parts = []
        for a, b in chunks(start, END, 90):
            tag = f"{model}_{a:%Y%m%d}_{b:%Y%m%d}.parquet"

            def fetch():
                q = {"latitude": LAT, "longitude": LON, "hourly": ",".join(vars_), "models": model,
                     "start_date": f"{a}", "end_date": f"{b}", "wind_speed_unit": "kn", "timezone": "GMT"}
                h = get(PREV + "?" + urllib.parse.urlencode(q))["hourly"]
                return pd.DataFrame(h).rename(columns={"time": "timestamp"})
            parts.append(cached(tag, fetch))
            print(f"  {tag}", flush=True)
        d = pd.concat(parts, ignore_index=True)
        d["timestamp"] = pd.to_datetime(d["timestamp"])
        d.drop_duplicates("timestamp").to_parquet(OUT / f"fcst_{model}.parquet", index=False)
        print(f"{model}: {len(d)} hours, wind d1 valid {d['wind_speed_10m_previous_day1'].notna().mean():.1%}", flush=True)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    pull_models()
    pull_coops()
    sys.exit(0)
