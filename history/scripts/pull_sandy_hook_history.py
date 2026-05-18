#!/usr/bin/env python3
"""
Pull NOAA CO-OPS hourly history at Sandy Hook (station 8531680).

Two products:
  - hourly_height : verified hourly observed water level (MLLW)
  - predictions   : astronomical predicted tide (MLLW)

Strategy:
  - Walk forward in 31-day chunks from --begin to --end (yesterday by default).
  - One chunk -> one parquet under history/data/raw_chunks/{product}/.
  - Resumable: chunks already on disk are skipped.
  - Empty responses (no data published for that span) write a small ".empty"
    marker so we don't keep re-requesting old gaps.
  - Polite: 0.6 s base sleep, exponential backoff with jitter on 429 / 5xx.

Run:
  python pull_sandy_hook_history.py                       # full default range
  python pull_sandy_hook_history.py --begin 2025-05-01    # smoke test
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

STATION = "8531680"  # Sandy Hook
BASE_URL = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
USER_AGENT = "highlands-flood-history (dr.john.urban@gmail.com)"

PRODUCTS = {
    # NOAA's hourly_height returns "data" rows with keys: t, v, s, f
    # (time, value, sigma, flags). predictions returns rows with keys: t, v.
    "hourly_height": {"value_col": "observed_mllw"},
    "predictions":   {"value_col": "predicted_mllw"},
}

DEFAULT_BEGIN = dt.date(1910, 1, 1)


def fetch(product: str, begin: dt.date, end: dt.date) -> dict:
    """One API call. Returns parsed JSON. Raises on persistent failure."""
    params = {
        "station": STATION,
        "product": product,
        "datum": "MLLW",
        "begin_date": begin.strftime("%Y%m%d"),
        "end_date": end.strftime("%Y%m%d"),
        "units": "english",
        "time_zone": "lst_ldt",
        "format": "json",
        "application": "highlands-flood-history",
    }
    if product == "predictions":
        params["interval"] = "h"  # predictions defaults to 6-min; we want hourly
    url = BASE_URL + "?" + urllib.parse.urlencode(params)

    delay = 1.0
    for attempt in range(6):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=60) as r:
                body = r.read()
            return json.loads(body)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < 5:
                time.sleep(delay + random.random() * 0.5)
                delay *= 2
                continue
            raise
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt < 5:
                time.sleep(delay + random.random() * 0.5)
                delay *= 2
                continue
            raise
    raise RuntimeError(f"giving up on {url}")


def chunk_to_dataframe(payload: dict, product: str) -> pd.DataFrame:
    """Convert API JSON to a tidy DataFrame. Returns empty DF on no data."""
    # hourly_height returns rows under "data"; predictions returns under "predictions".
    rows = payload.get("data") or payload.get("predictions") or []
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    # NOAA timestamps come as 'YYYY-MM-DD HH:MM' in lst_ldt.
    df["t"] = pd.to_datetime(df["t"], errors="coerce")
    df["v"] = pd.to_numeric(df["v"], errors="coerce")
    out = pd.DataFrame({"timestamp": df["t"]})
    out[PRODUCTS[product]["value_col"]] = df["v"]
    if "s" in df.columns:
        out["sigma"] = pd.to_numeric(df["s"], errors="coerce")
    if "f" in df.columns:
        out["flags"] = df["f"].astype(str)
    out = out.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    return out


def iter_chunks(begin: dt.date, end: dt.date, days: int = 31):
    """Yield (chunk_begin, chunk_end) date pairs, inclusive."""
    cur = begin
    step = dt.timedelta(days=days - 1)  # inclusive range, so step is days-1
    while cur <= end:
        nxt = min(cur + step, end)
        yield cur, nxt
        cur = nxt + dt.timedelta(days=1)


def chunk_path(out_dir: Path, product: str, begin: dt.date, end: dt.date) -> Path:
    return out_dir / product / f"{begin:%Y%m%d}_{end:%Y%m%d}.parquet"


def pull_product(product: str, begin: dt.date, end: dt.date, out_dir: Path,
                 polite_sleep: float = 0.6, verbose: bool = True) -> None:
    """Pull one product across the date range, chunk by chunk."""
    (out_dir / product).mkdir(parents=True, exist_ok=True)
    chunks = list(iter_chunks(begin, end))
    n = len(chunks)
    for i, (cb, ce) in enumerate(chunks, 1):
        path = chunk_path(out_dir, product, cb, ce)
        empty_marker = path.with_suffix(".empty")
        if path.exists() or empty_marker.exists():
            if verbose and i % 50 == 0:
                print(f"  [{product} {i}/{n}] skip existing {cb}..{ce}", flush=True)
            continue
        try:
            payload = fetch(product, cb, ce)
        except Exception as e:
            print(f"  [{product} {i}/{n}] ERROR {cb}..{ce}: {e}", flush=True)
            time.sleep(polite_sleep * 4)
            continue
        if "error" in payload:
            msg = payload["error"].get("message", "")
            # NOAA returns 'No data was found' for spans before gauge coverage
            if "No data was found" in msg or "No data" in msg:
                empty_marker.write_text(msg)
                if verbose:
                    print(f"  [{product} {i}/{n}] empty {cb}..{ce}", flush=True)
            else:
                print(f"  [{product} {i}/{n}] api-error {cb}..{ce}: {msg}", flush=True)
            time.sleep(polite_sleep)
            continue
        df = chunk_to_dataframe(payload, product)
        if df.empty:
            empty_marker.write_text("empty payload")
            if verbose:
                print(f"  [{product} {i}/{n}] empty {cb}..{ce}", flush=True)
        else:
            df.to_parquet(path, index=False)
            if verbose:
                print(f"  [{product} {i}/{n}] {cb}..{ce} -> {len(df)} rows", flush=True)
        time.sleep(polite_sleep)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--begin", default=str(DEFAULT_BEGIN),
                    help="YYYY-MM-DD start date (default 1910-01-01)")
    ap.add_argument("--end", default=None,
                    help="YYYY-MM-DD end date (default: yesterday local)")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent.parent / "data" / "raw_chunks"),
                    help="Output dir for parquet chunks")
    ap.add_argument("--products", nargs="+", default=list(PRODUCTS.keys()),
                    choices=list(PRODUCTS.keys()))
    ap.add_argument("--sleep", type=float, default=0.6)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    begin = dt.date.fromisoformat(args.begin)
    end = (dt.date.fromisoformat(args.end) if args.end
           else dt.date.today() - dt.timedelta(days=1))
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    verbose = not args.quiet

    print(f"Station {STATION} | {begin} .. {end} | products={args.products}", flush=True)
    for product in args.products:
        print(f"=== {product} ===", flush=True)
        pull_product(product, begin, end, out_dir,
                     polite_sleep=args.sleep, verbose=verbose)
    print("done", flush=True)


if __name__ == "__main__":
    sys.exit(main())
