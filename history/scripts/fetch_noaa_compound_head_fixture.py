#!/usr/bin/env python3
"""Refresh the NOAA six-minute head fixture for compound-event replay.

The output is a compact, deterministic join of official Sandy Hook
astronomical predictions and verified water-level observations.  The model
assessment reads the committed fixture offline; this command is the explicit
network refresh path.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = REPO_ROOT / "history" / "data" / "noaa_head_replay_fixture.json"
BASE_URL = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
USER_AGENT = "barnacle flood model (dr.john.urban@gmail.com)"
EVENTS = {
    "2025-10-30": ("20251030 16:00", "20251030 21:00"),
    "2025-12-19": ("20251219 10:00", "20251219 15:00"),
}
ASTRONOMICAL_SAMPLE = ("20260915 16:30", "20260919 22:00")


def _fetch(
    product: str, start: str, end: str, interval: str | None = None
) -> tuple[list[dict], str]:
    params = {
        "station": "8531680",
        "product": product,
        "datum": "MLLW",
        "time_zone": "gmt",
        "units": "english",
        "begin_date": start,
        "end_date": end,
        "format": "json",
    }
    if product == "predictions":
        params["interval"] = interval or "6"
    url = BASE_URL + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    key = "predictions" if product == "predictions" else "data"
    rows = payload.get(key) or []
    if not rows:
        raise RuntimeError(f"NOAA returned no {product} rows for {start}–{end}")
    return rows, url


def build_fixture() -> dict:
    events = {}
    for event_date, (start, end) in EVENTS.items():
        predictions, prediction_url = _fetch("predictions", start, end)
        observations, observation_url = _fetch("water_level", start, end)
        predicted = {row["t"]: row for row in predictions}
        observed = {row["t"]: row for row in observations}
        if predicted.keys() != observed.keys():
            raise RuntimeError(f"NOAA timestamps do not align for {event_date}")
        rows = []
        for stamp in sorted(predicted):
            observation = observed[stamp]
            if observation.get("q") != "v":
                raise RuntimeError(
                    f"unverified NOAA observation for {event_date} at {stamp}"
                )
            rows.append({
                "utc": stamp.replace(" ", "T") + ":00Z",
                "astronomical_mllw_ft": float(predicted[stamp]["v"]),
                "observed_mllw_ft": float(observation["v"]),
                "flags": observation.get("f", ""),
                "quality": observation.get("q", ""),
            })
        if len(rows) != 51:
            raise RuntimeError(
                f"expected 51 six-minute rows for {event_date}, got {len(rows)}"
            )
        events[event_date] = {
            "window_utc": [start.replace(" ", "T") + ":00Z",
                           end.replace(" ", "T") + ":00Z"],
            "prediction_url": prediction_url,
            "observation_url": observation_url,
            "rows": rows,
        }
    sample_start, sample_end = ASTRONOMICAL_SAMPLE
    sample, sample_url = _fetch(
        "predictions", sample_start, sample_end, interval="30"
    )
    sample_rows = [
        {
            "utc": row["t"].replace(" ", "T") + ":00Z",
            "astronomical_mllw_ft": float(row["v"]),
        }
        for row in sample
    ]
    if len(sample_rows) != 204:
        raise RuntimeError(
            f"expected 204 half-hour sample rows, got {len(sample_rows)}"
        )
    return {
        "schema_version": 1,
        "station": "8531680 Sandy Hook, NJ",
        "datum": "MLLW",
        "units": "feet",
        "retrieved_utc_date": dt.datetime.now(dt.timezone.utc).date().isoformat(),
        "note": (
            "Official NOAA CO-OPS six-minute predictions and verified "
            "observations. Automated flag strings are retained verbatim."
        ),
        "events": events,
        "astronomical_sample": {
            "window_utc": [
                sample_start.replace(" ", "T") + ":00Z",
                sample_end.replace(" ", "T") + ":00Z",
            ],
            "prediction_url": sample_url,
            "rows": sample_rows,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    fixture = build_fixture()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(
        prefix=args.out.name + ".", dir=args.out.parent
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(fixture, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, args.out)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise
    compound_rows = sum(len(e["rows"]) for e in fixture["events"].values())
    sample_rows = len(fixture["astronomical_sample"]["rows"])
    print(
        f"wrote {args.out} ({compound_rows} compound rows; "
        f"{sample_rows} astronomical sample rows)"
    )


if __name__ == "__main__":
    main()
