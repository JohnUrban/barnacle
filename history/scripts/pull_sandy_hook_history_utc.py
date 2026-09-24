#!/usr/bin/env python3
"""Canonical UTC hourly water history at Sandy Hook 8531680 (audit
2026-09-24-a2 R1). The legacy parquet (pull_sandy_hook_history.py) requests
`lst_ldt` and keeps NAIVE station-local labels; the meteorology pulls use
`gmt`. Joining them directly misaligned water and weather by 4-5 h. This pull
requests `time_zone=gmt` for verified `hourly_height` (with its quality flags)
and hourly `predictions`, and writes an explicitly UTC, tz-aware table:
  history/data/sandy_hook_hourly_utc.parquet
  columns: timestamp_utc (tz-aware UTC), observed_mllw, predicted_mllw,
           surge_ft, obs_sigma, obs_flags   (+ parquet metadata time_zone=UTC)
31-day chunks under history/data/raw_chunks_utc/{product}/, resumable.
Run: python3 history/scripts/pull_sandy_hook_history_utc.py [--begin 2005-01-01 --end 2026-05-17]
"""
from __future__ import annotations

import argparse, datetime as dt, json, sys, time, urllib.parse, urllib.request
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "history" / "data" / "raw_chunks_utc"
OUT = ROOT / "history" / "data" / "sandy_hook_hourly_utc.parquet"
UA = "highlands-flood-history (dr.john.urban@gmail.com)"
URL = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"


def fetch(product, a, b):
    q = {"product": product, "station": "8531680", "begin_date": f"{a:%Y%m%d}", "end_date": f"{b:%Y%m%d}",
         "datum": "MLLW", "time_zone": "gmt", "units": "english", "format": "json", "application": "barnacle-research"}
    if product == "predictions":
        q["interval"] = "h"
    for i in range(6):
        try:
            with urllib.request.urlopen(urllib.request.Request(URL + "?" + urllib.parse.urlencode(q), headers={"User-Agent": UA}), timeout=90) as r:
                return json.loads(r.read())
        except Exception:
            time.sleep(2 ** i)
    raise RuntimeError(f"gave up {product} {a}..{b}")


def pull(product, begin, end):
    d = RAW / product; d.mkdir(parents=True, exist_ok=True)
    a = begin
    while a <= end:
        b = min(a + dt.timedelta(days=30), end)
        path = d / f"{a:%Y%m%d}_{b:%Y%m%d}.parquet"; empty = path.with_suffix(".empty")
        if not (path.exists() or empty.exists()):
            js = fetch(product, a, b)
            rows = js.get("data") or js.get("predictions") or []
            if not rows:
                empty.write_text(json.dumps(js.get("error") or "empty"))
            else:
                df = pd.DataFrame(rows)
                out = pd.DataFrame({"timestamp_utc": pd.to_datetime(df["t"]).dt.tz_localize("UTC"),
                                    "v": pd.to_numeric(df["v"], errors="coerce")})
                if "s" in df:
                    out["sigma"] = pd.to_numeric(df["s"], errors="coerce")
                if "f" in df:
                    out["flags"] = df["f"].astype(str)
                out.to_parquet(path, index=False)
            print(f"  {product} {a}..{b}", flush=True)
            time.sleep(0.35)
        a = b + dt.timedelta(days=1)


def combine():
    def load(product):
        parts = [pd.read_parquet(p) for p in sorted((RAW / product).glob("*.parquet"))]
        return pd.concat(parts).drop_duplicates("timestamp_utc").set_index("timestamp_utc").sort_index()
    o, p = load("hourly_height"), load("predictions")
    df = pd.DataFrame({"observed_mllw": o["v"], "obs_sigma": o.get("sigma"), "obs_flags": o.get("flags")}).join(
        p["v"].rename("predicted_mllw"), how="outer")
    df["surge_ft"] = df.observed_mllw - df.predicted_mllw
    idx = pd.date_range(df.index.min(), df.index.max(), freq="h", tz="UTC")
    df = df.reindex(idx); df.index.name = "timestamp_utc"
    assert df.index.tz is not None and str(df.index.tz) == "UTC"
    df.reset_index().to_parquet(OUT, index=False)
    print(f"wrote {OUT.relative_to(ROOT)}: {len(df)} hours, surge valid {df.surge_ft.notna().sum()}, "
          f"{df.index.min()} .. {df.index.max()}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--begin", default="2005-01-01"); ap.add_argument("--end", default="2026-05-17")
    ap.add_argument("--combine", action="store_true"); a = ap.parse_args()
    if not a.combine:
        for prod in ("hourly_height", "predictions"):
            pull(prod, dt.date.fromisoformat(a.begin), dt.date.fromisoformat(a.end))
    combine()
