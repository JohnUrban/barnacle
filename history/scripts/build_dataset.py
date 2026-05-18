#!/usr/bin/env python3
"""
Build the derived hourly dataset and the per-event table.

Inputs (all under history/data/raw_chunks/):
  - hourly_height/*.parquet  : observed water level (MLLW)
  - predictions/*.parquet    : astronomical predicted tide (MLLW)

Outputs:
  - history/data/sandy_hook_hourly_history.parquet
        one row per hour with: timestamp, observed_mllw, predicted_mllw,
        surge_ft, water_at_342_navd88, depth_*_in, year, month, dow, hour
  - history/data/342_bay_flood_events.csv
        one row per contiguous flood event at the 6.58 ft (curb) threshold,
        with peak height, duration, max depth at each landmark, year, month.

Model constants from history/HANDOFF.md (matching v0.5 spec).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

# Model constants (v0.5)
LOCAL_ENHANCEMENT_FT = 0.40
MLLW_TO_NAVD88 = -2.82  # NAVD88 = MLLW + offset

CURB_TOP = 4.16       # ft NAVD88 - flood onset at SH 6.58
ROAD_MIDDLE = 4.36    # ft NAVD88 - SH 6.78
INTERSECTION = 4.54   # ft NAVD88 - SH 6.96
LAWN_STEP = 4.58      # ft NAVD88 - SH 7.00

# Sandy Hook MLLW thresholds (consistent with v0.5)
SH_CURB = 6.58
SH_ROAD = 6.78
SH_INTERSECTION = 6.96
SH_LAWN = 7.00

# Event detection threshold for the events file
EVENT_THRESHOLD_FT = SH_CURB  # 6.58 ft MLLW = curb wet at 342 Bay


def load_product(product_dir: Path) -> pd.DataFrame:
    files = sorted(product_dir.glob("*.parquet"))
    if not files:
        return pd.DataFrame()
    dfs = [pd.read_parquet(f) for f in files]
    df = pd.concat(dfs, ignore_index=True)
    df = df.drop_duplicates(subset=["timestamp"]).sort_values("timestamp")
    df = df.reset_index(drop=True)
    return df


def build_hourly(raw_dir: Path) -> pd.DataFrame:
    obs = load_product(raw_dir / "hourly_height")[["timestamp", "observed_mllw"]]
    pred = load_product(raw_dir / "predictions")[["timestamp", "predicted_mllw"]]
    df = obs.merge(pred, on="timestamp", how="outer").sort_values("timestamp").reset_index(drop=True)
    df["surge_ft"] = df["observed_mllw"] - df["predicted_mllw"]
    df["water_at_342_mllw"]   = df["observed_mllw"] + LOCAL_ENHANCEMENT_FT
    df["water_at_342_navd88"] = df["water_at_342_mllw"] + MLLW_TO_NAVD88
    for name, elev in [
        ("curb", CURB_TOP),
        ("road_middle", ROAD_MIDDLE),
        ("intersection", INTERSECTION),
        ("lawn_step", LAWN_STEP),
    ]:
        df[f"depth_at_{name}_in"] = np.clip(df["water_at_342_navd88"] - elev, 0, None) * 12
    df["year"] = df["timestamp"].dt.year
    df["month"] = df["timestamp"].dt.month
    df["dow"] = df["timestamp"].dt.dayofweek
    df["hour"] = df["timestamp"].dt.hour
    df["doy"] = df["timestamp"].dt.dayofyear
    return df


def detect_events(df: pd.DataFrame, threshold: float) -> pd.DataFrame:
    """Group contiguous hours where observed_mllw >= threshold into events.

    Hours don't have to be perfectly consecutive in calendar terms — we treat
    any gap > 1 hour as a new event. Within an event, a single sub-threshold
    hour breaks the run."""
    s = df.dropna(subset=["observed_mllw"]).copy()
    s["above"] = s["observed_mllw"] >= threshold
    s = s.sort_values("timestamp").reset_index(drop=True)
    # event_id increments each time we enter the above-threshold state
    above = s["above"].to_numpy()
    starts = above & ~np.concatenate(([False], above[:-1]))
    event_id = np.where(above, starts.cumsum(), 0)
    s["event_id"] = event_id
    events = s[s["event_id"] > 0]
    return events


def summarize_events(events: pd.DataFrame) -> pd.DataFrame:
    if events.empty:
        return pd.DataFrame()
    g = events.groupby("event_id")
    out = pd.DataFrame({
        "start":            g["timestamp"].min(),
        "end":              g["timestamp"].max(),
        "duration_h":       g["timestamp"].count(),
        "peak_obs_mllw":    g["observed_mllw"].max(),
        "peak_pred_mllw":   g["predicted_mllw"].max(),
        "peak_surge_ft":    g["surge_ft"].max(),
        "max_depth_curb_in":         g["depth_at_curb_in"].max(),
        "max_depth_road_in":         g["depth_at_road_middle_in"].max(),
        "max_depth_intersection_in": g["depth_at_intersection_in"].max(),
        "max_depth_lawn_in":         g["depth_at_lawn_step_in"].max(),
    }).reset_index(drop=True)
    out["year"] = out["start"].dt.year
    out["month"] = out["start"].dt.month
    return out


def main():
    repo = Path(__file__).resolve().parent.parent
    raw_dir = repo / "data" / "raw_chunks"
    out_dir = repo / "data"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"loading from {raw_dir}", flush=True)
    df = build_hourly(raw_dir)
    print(f"hourly rows: {len(df):,}  span: {df['timestamp'].min()} .. {df['timestamp'].max()}",
          flush=True)

    out_parquet = out_dir / "sandy_hook_hourly_history.parquet"
    df.to_parquet(out_parquet, index=False)
    print(f"wrote {out_parquet}", flush=True)

    events = detect_events(df, EVENT_THRESHOLD_FT)
    summary = summarize_events(events)
    out_csv = out_dir / "342_bay_flood_events.csv"
    summary.to_csv(out_csv, index=False)
    print(f"wrote {out_csv} -- {len(summary):,} events at {EVENT_THRESHOLD_FT} ft MLLW",
          flush=True)


if __name__ == "__main__":
    main()
