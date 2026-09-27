#!/usr/bin/env python3
"""Archive raw NOAA CO-OPS water-level responses for the 2026-09-25..27
storm (audit 2026-09-27-a1 R4): GMT transport, MLLW datum, every field
NOAA returns (v, sigma s, flags f, quality q) plus a request receipt with
the retrieval time. Station-local display conversion happens in
event10_gauge_qc.py through the shared station-time helpers, never here.

A retrieval is a snapshot of NOAA's server state at retrieved_utc; a
'p' quality flag means PRELIMINARY. A later download is not automatically
the final verified observation. Re-running writes NEW dated files and
never overwrites an earlier snapshot.

Run: ~/.barnacle/venv/bin/python fetch_event_gauges.py
"""
import datetime as dt
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "gauge-sources"
UA = {"User-Agent": "barnacle flood model (dr.john.urban@gmail.com)"}
STATIONS = {"8531680": "sandy-hook", "8518750": "battery"}
BEGIN, END = "20260925 12:00", "20260927 22:00"   # GMT window


def fetch(station):
    params = {"product": "water_level", "application": "barnacle_event_archive",
              "begin_date": BEGIN, "end_date": END, "datum": "MLLW",
              "station": station, "time_zone": "gmt", "units": "english",
              "format": "json"}
    url = ("https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?"
           + urllib.parse.urlencode(params))
    retrieved = dt.datetime.now(dt.timezone.utc)
    body = urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                  timeout=60).read()
    data = json.loads(body)
    stamp = retrieved.strftime("%Y%m%dT%H%M%SZ")
    name = STATIONS[station]
    (OUT / f"{name}-{stamp}.json").write_bytes(body)
    (OUT / f"{name}-{stamp}-request.json").write_text(json.dumps({
        "url": url, "parameters": params,
        "retrieved_utc": retrieved.isoformat(),
        "rows": len(data.get("data", [])),
        "quality_flags_present": sorted({r.get("q") for r in data.get("data", [])}),
        "description": ("Raw NOAA response as served at retrieved_utc; q='p' rows are "
                        "preliminary. Not an as-issued forecast input and not a "
                        "street measurement."),
    }, indent=1))
    return name, stamp, len(data.get("data", []))


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for st in STATIONS:
        print(*fetch(st))
