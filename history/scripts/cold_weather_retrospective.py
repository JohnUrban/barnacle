#!/usr/bin/env python3
"""
Cold-weather retrospective: find past events where the v0.6 cold-lockout
override SHOULD have applied — i.e., 72-h mean air temperature < 32°F
AND Sandy Hook peak water level > 6.58 ft MLLW (curb threshold).

HANDOFF item 16, "X" in the 2026-05-19 solo-work backlog.

The cold-lockout override (v0.6 model) sets predicted flood depth to 0
when temp_avg_72h < 32°F AND SH_peak < 8.0 ft. It's calibrated from a
SINGLE observed event (Feb 22-23 2026: SH 7.19 + onshore winds + cold →
no observed flooding). This script identifies candidate historical
events that would meet the same condition, so the user can cross-check
against newspaper / borough archives:

  - If most candidate events DIDN'T flood → strong retrospective
    validation of the override.
  - If many candidate events DID flood → the override is wrong or
    needs a different temperature threshold.

Outputs:
  - history/data/cold_weather_candidates.csv : per-event rows with
    date, SH peak, 72-h mean temp, ranking, neighboring tide context.
  - history/reports/cold_weather_retrospective.md : short summary +
    next steps for the user to manually cross-check newspaper archives.

Usage:
  python history/scripts/cold_weather_retrospective.py
  python history/scripts/cold_weather_retrospective.py --begin 2000-01-01

Dependencies: same as the rest of history/scripts — pandas, pyarrow,
requests (or urllib). See `history/HANDOFF.md` for env setup.

Approach:
  1. Pull NOAA air_temperature at Sandy Hook (station 8531680) via the
     chunked + resumable pattern in pull_sandy_hook_history.py.
  2. Load the existing hourly_height parquet (or rebuild via build_dataset.py
     if it's gitignored).
  3. Join on timestamp (both are hourly).
  4. Compute 72-h trailing mean temperature.
  5. Identify days with at least one hourly height >= 6.58 ft AND the
     72-h trailing mean temp at that hour < 32°F. Group adjacent hours
     into one event.
  6. Rank by peak height (highest = most-stretched override).
  7. Write candidates CSV + summary report.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
HISTORY_DIR = REPO_ROOT / "history"
RAW_CHUNKS_DIR = HISTORY_DIR / "data" / "raw_chunks" / "air_temperature"
RAW_CHUNKS_WIND = HISTORY_DIR / "data" / "raw_chunks" / "wind"
HOURLY_HEIGHT_PARQUET = HISTORY_DIR / "data" / "sandy_hook_hourly_history.parquet"
CANDIDATES_CSV = HISTORY_DIR / "data" / "cold_weather_candidates.csv"
REPORT_MD = HISTORY_DIR / "reports" / "cold_weather_retrospective.md"

# v0.6 model constants — match forecast/flood_forecast_daily.py so the
# predicted_depth_at_curb_without_lockout column reflects what the
# model would have said had the cold-lockout NOT been applied.
LOCAL_ENHANCEMENT_FT  = 0.40
MLLW_TO_NAVD88_OFFSET = -2.82
CURB_NAVD88           = 4.16  # 342 Bay curb elevation

NOAA_STATION = "8531680"  # Sandy Hook
NOAA_API = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"

# Model thresholds
CURB_THRESHOLD_MLLW = 6.58       # SH peak at which curb wets at 342 Bay
COLD_LOCKOUT_F      = 32.0        # 72-h mean temp threshold
LOCKOUT_CEILING_MLLW = 8.0        # Override only applies when SH < this
ROLLING_HOURS       = 72          # Rolling mean window


def _fetch_chunk(product: str, begin: dt.date, end: dt.date) -> dict:
    """Generic NOAA CO-OPS chunk fetcher. `product` is one of NOAA's
    product names (air_temperature, wind, etc.)."""
    params = {
        "station":    NOAA_STATION,
        "product":    product,
        "units":      "english",
        "time_zone":  "lst_ldt",
        "interval":   "h",
        "begin_date": begin.strftime("%Y%m%d %H:%M"),
        "end_date":   end.strftime("%Y%m%d %H:%M"),
        "format":     "json",
    }
    url = NOAA_API + "?" + urllib.parse.urlencode(params)
    backoff = 1.0
    for attempt in range(6):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "barnacle-cold-weather-retrospective"
            })
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            if attempt == 5:
                raise
            sleep_for = backoff + random.uniform(0, 0.5)
            print(f"  retry {attempt+1}: {e} (sleeping {sleep_for:.1f}s)",
                  file=sys.stderr)
            time.sleep(sleep_for)
            backoff *= 2


def fetch_air_temperature_chunk(begin: dt.date, end: dt.date) -> dict:
    """Backwards-compat wrapper around _fetch_chunk for air_temperature."""
    return _fetch_chunk("air_temperature", begin, end)


def pull_air_temperature(begin: dt.date, end: dt.date) -> pd.DataFrame:
    """Walk forward in 31-day chunks, cache each as parquet under
    history/data/raw_chunks/air_temperature/, return combined dataframe.
    Resumable: chunks already on disk are skipped."""
    RAW_CHUNKS_DIR.mkdir(parents=True, exist_ok=True)
    cur = begin
    chunks = []
    while cur < end:
        nxt = min(cur + dt.timedelta(days=31), end)
        chunk_name = f"{cur:%Y%m%d}-{nxt:%Y%m%d}.parquet"
        chunk_path = RAW_CHUNKS_DIR / chunk_name
        empty_marker = RAW_CHUNKS_DIR / (chunk_name + ".empty")

        if chunk_path.exists():
            chunks.append(pd.read_parquet(chunk_path))
        elif empty_marker.exists():
            pass  # known empty span
        else:
            print(f"fetch {cur:%Y-%m-%d} → {nxt:%Y-%m-%d}")
            try:
                payload = fetch_air_temperature_chunk(cur, nxt)
            except Exception as e:
                print(f"  ERROR: {e} (skipping)", file=sys.stderr)
                cur = nxt
                continue
            rows = payload.get("data") or []
            if not rows:
                empty_marker.touch()
            else:
                df = pd.DataFrame(rows)
                df = df.rename(columns={"t": "time", "v": "temp_f"})
                df["time"] = pd.to_datetime(df["time"], errors="coerce")
                df["temp_f"] = pd.to_numeric(df["temp_f"], errors="coerce")
                df = df.dropna(subset=["time", "temp_f"])
                df = df[["time", "temp_f"]]
                df.to_parquet(chunk_path, index=False)
                chunks.append(df)
            time.sleep(0.6)  # be polite
        cur = nxt

    if not chunks:
        return pd.DataFrame(columns=["time", "temp_f"])
    return pd.concat(chunks, ignore_index=True).sort_values("time")


def pull_wind(begin: dt.date, end: dt.date) -> pd.DataFrame:
    """Pull NOAA `wind` at Sandy Hook in chunked + resumable fashion,
    cached under history/data/raw_chunks/wind/. Returns combined
    dataframe with columns: time, wind_speed_kts (max during hour),
    wind_dir_deg. NOAA returns wind direction in degrees from true
    north (0 = N, 90 = E, 180 = S, 270 = W)."""
    RAW_CHUNKS_WIND.mkdir(parents=True, exist_ok=True)
    cur = begin
    chunks = []
    while cur < end:
        nxt = min(cur + dt.timedelta(days=31), end)
        chunk_name = f"{cur:%Y%m%d}-{nxt:%Y%m%d}.parquet"
        chunk_path = RAW_CHUNKS_WIND / chunk_name
        empty_marker = RAW_CHUNKS_WIND / (chunk_name + ".empty")

        if chunk_path.exists():
            chunks.append(pd.read_parquet(chunk_path))
        elif empty_marker.exists():
            pass
        else:
            print(f"wind  {cur:%Y-%m-%d} → {nxt:%Y-%m-%d}")
            try:
                payload = _fetch_chunk("wind", cur, nxt)
            except Exception as e:
                print(f"  ERROR: {e} (skipping)", file=sys.stderr)
                cur = nxt
                continue
            rows = payload.get("data") or []
            if not rows:
                empty_marker.touch()
            else:
                df = pd.DataFrame(rows)
                # NOAA `wind` returns: t (time), s (speed kts), d (dir deg),
                # dr (direction code, e.g. "NE"), g (gust kts), f (flags).
                df = df.rename(columns={
                    "t":  "time",
                    "s":  "wind_speed_kts",
                    "d":  "wind_dir_deg",
                })
                df["time"] = pd.to_datetime(df["time"], errors="coerce")
                df["wind_speed_kts"] = pd.to_numeric(
                    df["wind_speed_kts"], errors="coerce")
                df["wind_dir_deg"] = pd.to_numeric(
                    df["wind_dir_deg"], errors="coerce")
                df = df.dropna(subset=["time"])
                df = df[["time", "wind_speed_kts", "wind_dir_deg"]]
                df.to_parquet(chunk_path, index=False)
                chunks.append(df)
            time.sleep(0.6)
        cur = nxt

    if not chunks:
        return pd.DataFrame(columns=["time", "wind_speed_kts", "wind_dir_deg"])
    return pd.concat(chunks, ignore_index=True).sort_values("time")


def _dir_label(deg):
    """Convert a degrees-from-true-north heading to compass label
    (16-point rose). Returns '' for NaN."""
    if pd.isna(deg):
        return ""
    labels = ["N","NNE","NE","ENE","E","ESE","SE","SSE",
              "S","SSW","SW","WSW","W","WNW","NW","NNW"]
    idx = int(round(deg / 22.5)) % 16
    return labels[idx]


def load_hourly_height() -> pd.DataFrame:
    """Load the existing combined hourly_height parquet. Raises a helpful
    message when the file is gitignored and hasn't been regenerated."""
    if not HOURLY_HEIGHT_PARQUET.exists():
        sys.exit(
            f"ERROR: {HOURLY_HEIGHT_PARQUET} not found.\n"
            "  This file is gitignored — regenerate via:\n"
            "  python history/scripts/pull_sandy_hook_history.py && "
            "python history/scripts/build_dataset.py"
        )
    df = pd.read_parquet(HOURLY_HEIGHT_PARQUET)
    # Normalize column names — the build_dataset.py output may use 't' / 'v'
    # or 'time' / 'observed_mllw'. Handle both.
    if "time" not in df.columns:
        for c in df.columns:
            if "time" in c.lower() or c == "t":
                df = df.rename(columns={c: "time"})
                break
    if "observed_mllw" not in df.columns:
        for c in df.columns:
            if "mllw" in c.lower() or c == "v":
                df = df.rename(columns={c: "observed_mllw"})
                break
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    df = df.dropna(subset=["time", "observed_mllw"])
    return df[["time", "observed_mllw"]]


def augment_candidates(events: pd.DataFrame,
                        wind: pd.DataFrame,
                        water: pd.DataFrame) -> pd.DataFrame:
    """Add the 4 enrichment columns to the candidate event rows
    (per user 2026-05-19 follow-up):

      predicted_depth_at_curb_without_lockout (inches) — what v0.6
        would have predicted at the curb if cold-lockout were NOT
        applied. Tells you how big each "claim" is.
      rain_24h_in — total precipitation in the 24h around peak.
        Lets you filter pure-tidal candidates from rain-confounded ones.
        Pulled from a separate met source if needed; for now we leave
        this column empty when no precip data is available (NOAA's
        precipitation product isn't reliably reported at 8531680).
      wind_dir / wind_speed_max — wind at peak hour. Onshore wind
        (NE-ESE roughly 30-110° for Sandy Hook Bay) drives surge AND
        may prevent drain-outfall ice formation by continuously
        bathing the outfall in bay water.
    """
    if events.empty:
        return events

    out = events.copy()

    # predicted_depth_at_curb_without_lockout
    # Match the model formula at the BARE TIDE level (no rain bonus
    # — rain isn't in this analysis pipeline yet).
    water_navd88 = out["observed_mllw"] + LOCAL_ENHANCEMENT_FT + MLLW_TO_NAVD88_OFFSET
    out["predicted_depth_at_curb_without_lockout_in"] = (
        (water_navd88 - CURB_NAVD88).clip(lower=0) * 12
    ).round(1)

    # rain_24h_in — placeholder (NOAA precipitation isn't reliably
    # available at this station). Real precipitation requires a
    # separate met source (e.g., NWS Mt Holly gridded precip,
    # NJ State Climatologist station network). For now: empty.
    out["rain_24h_in"] = pd.NA

    # wind_dir + wind_speed_max — match each event's peak hour to
    # the nearest wind reading (merge_asof, 90-min tolerance).
    if not wind.empty:
        wind_sorted = wind.sort_values("time").reset_index(drop=True)
        events_sorted = out.sort_values("time").reset_index(drop=True)
        matched = pd.merge_asof(
            events_sorted, wind_sorted,
            on="time", direction="nearest",
            tolerance=pd.Timedelta("90min"),
        )
        out = matched.sort_values("time").reset_index(drop=True)
        out["wind_dir"] = out["wind_dir_deg"].apply(_dir_label)
        out = out.rename(columns={
            "wind_speed_kts": "wind_speed_max_kts",
        })
    else:
        out["wind_dir"] = ""
        out["wind_speed_max_kts"] = pd.NA
        out["wind_dir_deg"] = pd.NA

    return out


def find_candidate_events(joined: pd.DataFrame) -> pd.DataFrame:
    """Identify cold-weather candidate flood events.

    A row is a candidate if:
      observed_mllw >= CURB_THRESHOLD_MLLW (6.58)
      AND 72h_mean_temp_f < COLD_LOCKOUT_F (32)
      AND observed_mllw < LOCKOUT_CEILING_MLLW (8.0) — Override only
          applies below this; events above are extreme regardless of
          temp and would have flooded anyway.

    Adjacent qualifying hours within the same calendar day are
    grouped into one event represented by the max-height row.
    """
    # 72-h rolling mean temperature (trailing). Requires hourly index.
    df = joined.set_index("time").sort_index()
    df["temp_72h_mean"] = df["temp_f"].rolling("72h", min_periods=24).mean()
    df = df.reset_index()

    candidates = df[
        (df["observed_mllw"] >= CURB_THRESHOLD_MLLW) &
        (df["observed_mllw"] <  LOCKOUT_CEILING_MLLW) &
        (df["temp_72h_mean"] <  COLD_LOCKOUT_F)
    ].copy()

    if candidates.empty:
        return candidates

    # Group consecutive qualifying hours into events. We use calendar
    # date as the grouping key — within a day, take the row with the
    # highest observed_mllw as the event peak.
    candidates["date"] = candidates["time"].dt.date
    events = (
        candidates
        .sort_values("observed_mllw", ascending=False)
        .drop_duplicates(subset=["date"], keep="first")
        .sort_values("time")
    )
    return events.reset_index(drop=True)


def render_report(events: pd.DataFrame, since: dt.date) -> str:
    n = len(events)
    if n == 0:
        body = (
            "## Result\n\n"
            f"No candidate events found since {since.isoformat()}. "
            "Either:\n\n"
            "- The cold-lockout regime (72-h mean temp < 32°F AND SH "
            "peak ≥ 6.58 ft AND < 8.0 ft) is genuinely rare at Sandy Hook, OR\n"
            "- The air-temperature data series at Sandy Hook is too "
            "sparse for the lookback window (NOAA's air_temperature "
            "product coverage is uneven pre-2000).\n\n"
            "Either result strengthens the case that cold-lockout is "
            "a low-frequency override — the Feb 22-23 2026 event may "
            "be the only modern analog."
        )
    else:
        top = events.nlargest(min(20, n), "observed_mllw")
        lines = ["| Date | SH peak (ft MLLW) | 72-h mean temp (°F) | Notes to check |",
                 "|---|---:|---:|---|"]
        for _, r in top.iterrows():
            lines.append(
                f"| {r['date']} | {r['observed_mllw']:.2f} | "
                f"{r['temp_72h_mean']:.1f} | newspaper / borough archive |"
            )
        body = (
            f"## Result\n\n**{n} candidate events** since "
            f"{since.isoformat()} — top {min(20, n)} by SH peak shown "
            f"below. Each is a date when the v0.6 cold-lockout override "
            f"would have suppressed predicted flooding because:\n"
            f"  - SH peak was between {CURB_THRESHOLD_MLLW} and "
            f"{LOCKOUT_CEILING_MLLW} ft MLLW (would otherwise cross "
            f"the curb), AND\n"
            f"  - 72-h trailing mean air temperature was below "
            f"{COLD_LOCKOUT_F}°F.\n\n"
            f"**Action**: cross-check each date against the Highlands "
            f"Star-Ledger / Asbury Park Press / Borough records to see "
            f"whether flooding was actually reported. If most dates "
            f"have no flooding mention → strong retrospective "
            f"validation of cold-lockout. If many DID flood → the "
            f"override is wrong or needs a different threshold.\n\n"
            + "\n".join(lines) + "\n\n"
            "Full candidate list: `history/data/cold_weather_candidates.csv`."
        )

    return (
        "# Cold-Weather Retrospective\n\n"
        "_HANDOFF item 16, X in the 2026-05-19 solo-work backlog._\n\n"
        "## Method\n\n"
        "1. Pulled NOAA `air_temperature` for Sandy Hook (8531680) "
        f"from {since.isoformat()} onward.\n"
        "2. Joined to the existing hourly_height parquet from the "
        "history project.\n"
        "3. Computed 72-h trailing mean temperature.\n"
        f"4. Filtered to hours with `SH peak ≥ {CURB_THRESHOLD_MLLW} "
        f"ft AND < {LOCKOUT_CEILING_MLLW} ft AND 72-h mean temp < "
        f"{COLD_LOCKOUT_F}°F`.\n"
        "5. Grouped consecutive qualifying hours into one event per "
        "calendar date (peak row).\n\n"
        + body + "\n"
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--begin", default="2010-01-01",
                    help="Start date for the air-temperature pull "
                         "(YYYY-MM-DD; default: 2010-01-01).")
    ap.add_argument("--end", default=None,
                    help="End date (YYYY-MM-DD; default: yesterday).")
    ap.add_argument("--write-report", action="store_true",
                    help="Overwrite history/reports/cold_weather_retrospective.md "
                         "with the auto-generated table. Off by default — the "
                         "report is curated by hand (web-evidence section, "
                         "augmented analysis, decisions) and a naive rerun "
                         "would clobber those additions. The CSV at "
                         "history/data/cold_weather_candidates.csv is "
                         "ALWAYS overwritten — it's a pure derived view.")
    args = ap.parse_args()
    begin = dt.date.fromisoformat(args.begin)
    end = (dt.date.fromisoformat(args.end) if args.end
           else dt.date.today() - dt.timedelta(days=1))

    print(f"Cold-weather retrospective: {begin} → {end}")
    print("Step 1: pull air_temperature (resumable, chunked)…")
    air = pull_air_temperature(begin, end)
    print(f"  {len(air):,} hourly air-temperature rows")

    print("Step 2: load hourly water-level history…")
    water = load_hourly_height()
    print(f"  {len(water):,} hourly water-level rows")

    print("Step 3: join + compute 72-h rolling mean temp…")
    joined = pd.merge_asof(
        water.sort_values("time"),
        air.sort_values("time"),
        on="time",
        direction="nearest",
        tolerance=pd.Timedelta("90min"),
    ).dropna(subset=["temp_f"])
    print(f"  {len(joined):,} joined hourly rows")

    print("Step 4: identify candidate cold-weather flood events…")
    events = find_candidate_events(joined)
    print(f"  {len(events)} candidate events")

    print("Step 4b: pull wind data + augment candidates with the 4 "
          "additional columns…")
    wind = pull_wind(begin, end)
    print(f"  {len(wind):,} hourly wind rows")
    events = augment_candidates(events, wind, water)
    print(f"  augmented columns: predicted_depth_at_curb_without_lockout_in, "
          f"rain_24h_in (placeholder), wind_dir, wind_speed_max_kts")

    CANDIDATES_CSV.parent.mkdir(parents=True, exist_ok=True)
    events.to_csv(CANDIDATES_CSV, index=False)
    print(f"  → {CANDIDATES_CSV.relative_to(REPO_ROOT)}")

    if args.write_report:
        print("Step 5: write summary report (--write-report set)…")
        report = render_report(events, since=begin)
        REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
        REPORT_MD.write_text(report)
        print(f"  → {REPORT_MD.relative_to(REPO_ROOT)}")
    else:
        print("Step 5: skipped — report is curated by hand; pass "
              "--write-report to overwrite with the auto-generated "
              "template.")
    print("done.")


if __name__ == "__main__":
    main()
