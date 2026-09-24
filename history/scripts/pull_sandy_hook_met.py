#!/usr/bin/env python3
"""Pull NOAA CO-OPS hourly meteorology at Sandy Hook (8531680): wind
(speed kn, direction deg true FROM, gust kn) and air pressure (mb), for the
surge-decay research (2026-09-23). Same conventions as
pull_sandy_hook_history.py: 31-day chunks, one parquet per chunk under
history/data/raw_chunks/{product}/, resumable, ".empty" markers, polite
sleep with backoff. Then --combine writes history/data/sandy_hook_met_hourly.parquet.

Run:
  python3 history/scripts/pull_sandy_hook_met.py --begin 2006-01-01 --end 2026-05-17
  python3 history/scripts/pull_sandy_hook_met.py --combine
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

STATION = "8531680"
BASE_URL = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
USER_AGENT = "highlands-flood-history (dr.john.urban@gmail.com)"
ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "history" / "data" / "raw_chunks"
COMBINED = ROOT / "history" / "data" / "sandy_hook_met_hourly.parquet"
PRODUCTS = ("wind", "air_pressure")


def fetch(product, begin, end):
    params = {"product": product, "station": STATION, "begin_date": f"{begin:%Y%m%d}",
              "end_date": f"{end:%Y%m%d}", "time_zone": "gmt", "units": "english",
              "interval": "h", "format": "json", "application": "barnacle-research"}
    url = BASE_URL + "?" + urllib.parse.urlencode(params)
    for attempt in range(6):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(min(60, 2 ** attempt + random.random()))
                continue
            raise
        except (urllib.error.URLError, TimeoutError):
            time.sleep(min(60, 2 ** attempt + random.random()))
    raise RuntimeError(f"gave up on {product} {begin}..{end}")


def to_frame(payload, product):
    rows = payload.get("data") or []
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    out = pd.DataFrame({"timestamp": pd.to_datetime(df["t"])})
    if product == "wind":
        for src, dst in (("s", "wind_speed_kn"), ("d", "wind_dir_deg"), ("g", "wind_gust_kn")):
            out[dst] = pd.to_numeric(df[src], errors="coerce")
    else:
        out["pressure_mb"] = pd.to_numeric(df["v"], errors="coerce")
    return out


def pull(product, begin, end, sleep):
    d = RAW / product
    d.mkdir(parents=True, exist_ok=True)
    cb = begin
    while cb <= end:
        ce = min(cb + dt.timedelta(days=30), end)
        path = d / f"{cb:%Y%m%d}_{ce:%Y%m%d}.parquet"
        marker = path.with_suffix(".empty")
        if not (path.exists() or marker.exists()):
            payload = fetch(product, cb, ce)
            if "error" in payload:
                msg = payload["error"].get("message", "")
                marker.write_text(msg or "error")
                print(f"  [{product}] {cb}..{ce} api-error: {msg}", flush=True)
            else:
                df = to_frame(payload, product)
                if df.empty:
                    marker.write_text("empty payload")
                else:
                    df.to_parquet(path, index=False)
                print(f"  [{product}] {cb}..{ce} -> {len(df)} rows", flush=True)
            time.sleep(sleep)
        cb = ce + dt.timedelta(days=1)


def combine():
    frames = {}
    for product in PRODUCTS:
        # only this script's chunks (YYYYMMDD_YYYYMMDD); the hyphen-named chunks in the same
        # folders belong to cold_weather_retrospective.py and use other column names
        parts = [pd.read_parquet(p) for p in sorted((RAW / product).glob("[0-9]*_[0-9]*.parquet"))]
        frames[product] = (pd.concat(parts).drop_duplicates("timestamp").set_index("timestamp").sort_index()
                           if parts else pd.DataFrame())
    met = frames["wind"].join(frames["air_pressure"], how="outer")
    met.reset_index().to_parquet(COMBINED, index=False)
    print(f"combined {len(met)} rows -> {COMBINED.relative_to(ROOT)}; "
          f"wind valid {met['wind_speed_kn'].notna().sum()}, pressure valid {met['pressure_mb'].notna().sum()}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--begin", default="2006-01-01")
    ap.add_argument("--end", default="2026-05-17")
    ap.add_argument("--sleep", type=float, default=0.6)
    ap.add_argument("--combine", action="store_true")
    a = ap.parse_args()
    if a.combine:
        combine()
        return
    for product in PRODUCTS:
        pull(product, dt.date.fromisoformat(a.begin), dt.date.fromisoformat(a.end), a.sleep)
    combine()


if __name__ == "__main__":
    sys.exit(main())
