#!/usr/bin/env python3
"""LIVE nowcast: latest MRMS radar rates -> v0.10 tank -> street water NOW + next 45 min.

Manual v0 of the HANDOFF-designated MRMS nowcast (built 2026-07-17,
eve of a Flood Watch with QPF smeared to ~0). Run during rain:

    scratchpad-venv/bin/python history/scripts/nowcast_tank.py

Pulls the last ~75 min of MRMS PrecipRate frames (NCEP real-time,
2-min cadence) over the hillside catchment box, integrates the v0.10
tank with the calibrated 14-min lag from a dry start at window open,
then projects 45 min forward under two scenarios (rain persists /
rain stops now). Prints street-water trajectory vs the landmark
ladder. Needs xarray+cfgrib (scratchpad venv) + network.
"""
import datetime as dt
import glob
import gzip
import os
import re
import sys
import tempfile
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "forecast"))
import flood_forecast_daily as ff

UA = {"User-Agent": "barnacle flood model (dr.john.urban@gmail.com)"}
LAT, LON = 40.4015, -73.991
BOX = 0.015
BASE = "https://mrms.ncep.noaa.gov/2D/PrecipRate/"


def latest_frames(minutes=75, step_min=6):
    listing = urllib.request.urlopen(
        urllib.request.Request(BASE, headers=UA), timeout=30).read().decode()
    stamps = sorted(set(re.findall(
        r"MRMS_PrecipRate_00\.00_(\d{8}-\d{6})\.grib2\.gz", listing)))
    if not stamps:
        raise RuntimeError("no MRMS frames listed")
    newest = dt.datetime.strptime(stamps[-1], "%Y%m%d-%H%M%S")
    keep = []
    for s in stamps:
        t = dt.datetime.strptime(s, "%Y%m%d-%H%M%S")
        if (newest - t).total_seconds() <= minutes * 60:
            keep.append((t, s))
    return keep[::max(1, step_min // 2)]


def box_rate(stamp):
    import xarray as xr
    url = f"{BASE}MRMS_PrecipRate_00.00_{stamp}.grib2.gz"
    raw = gzip.decompress(urllib.request.urlopen(
        urllib.request.Request(url, headers=UA), timeout=30).read())
    with tempfile.NamedTemporaryFile(suffix=".grib2", delete=False) as f:
        f.write(raw)
        tmp = f.name
    try:
        ds = xr.open_dataset(tmp, engine="cfgrib", decode_timedelta=True)
        var = list(ds.data_vars)[0]
        box = ds[var].sel(latitude=slice(LAT + BOX, LAT - BOX),
                          longitude=slice(LON + 360 - BOX, LON + 360 + BOX))
        out = float(box.mean()) / 25.4   # mm/hr -> in/hr
        ds.close()
    finally:
        os.remove(tmp)
        for g in glob.glob(tmp + "*.idx"):
            os.remove(g)
    return out


def current_bay():
    import json
    try:
        d = json.load(urllib.request.urlopen(urllib.request.Request(
            "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?"
            "station=8531680&product=water_level&datum=MLLW&time_zone=lst_ldt"
            "&units=english&begin_date={b}&end_date={e}&format=json".format(
                b=(dt.datetime.now() - dt.timedelta(hours=3)
                   ).strftime("%Y%m%d%%20%H:%M"),
                e=dt.datetime.now().strftime("%Y%m%d%%20%H:%M")),
            headers=UA), timeout=15))
        pairs = [(r["t"], float(r["v"])) for r in d["data"]]
        pairs = ff._despike_gauge(pairs)
        return pairs[-1][1] - 2.82
    except Exception:
        return 2.8   # mid-tide fallback


def main():
    ff._load_stage_curve()
    bay = current_bay()
    print(f"bay now: {bay:.2f} NAVD88 "
          f"({(bay - 3.52) * 12:+.1f}\" vs SW grate); "
          f"drain capacity {ff.PLUVIAL_DRAIN_RATE * min(1, max(0, (3.52 - bay) / 0.52)):.2f} in/hr")
    frames = latest_frames()
    print(f"pulling {len(frames)} MRMS frames "
          f"({frames[0][0].strftime('%H:%M')}Z – {frames[-1][0].strftime('%H:%M')}Z)…")
    series = []
    for t, s in frames:
        try:
            r = box_rate(s)
            series.append((t, r))
            bar = "#" * int(r * 10)
            print(f"  {t.strftime('%H:%M')}Z  {r:5.2f} in/hr  {bar}")
        except Exception as e:
            print(f"  {t.strftime('%H:%M')}Z  ERR {str(e)[:40]}")
    if not series:
        sys.exit("no usable frames")
    # tank integration (calibrated constants from the forecast module)
    lag = dt.timedelta(minutes=ff.TANK_LAG_MIN)
    drain = ff.PLUVIAL_DRAIN_RATE * min(1, max(0, (3.52 - bay) / 0.52))
    base_stage = max(0.0, (bay - 3.52) * 12)

    def rate_at(t):
        tl = t - lag
        prev = series[0]
        for pt in series:
            if pt[0] > tl:
                break
            prev = pt
        return prev[1]

    V = 0.0
    t = series[0][0]
    end_obs = series[-1][0]
    dtm = 2.0
    rows = []
    horizon = end_obs + dt.timedelta(minutes=45)
    while t <= horizon:
        persisted = series[-1][1] if t > end_obs else None
        r = rate_at(t) if t <= end_obs + lag else (persisted or 0.0)
        net = max(0.0, r - drain)
        V = max(0.0, V + (ff.TANK_K * net ** ff.TANK_GAMMA
                          - ff.TANK_KOUT * V) * (dtm / 60.0))
        stage = ff._pluvial_fill(ff._STAGE_CURVE, base_stage,
                                 V) if V > 0 else base_stage
        rows.append((t, r, stage))
        t += dt.timedelta(minutes=dtm)
    print("\nTANK NOWCAST (ET; obs rates through "
          f"{(end_obs - dt.timedelta(hours=4)).strftime('%H:%M')}, then persistence):")
    LADDER = [(0, "SW grate"), (3.1, "gutter"), (7.7, "curb"),
              (13.7, "lawn step"), (18.7, "7/9 peak"), (22.7, "porch step1")]
    for t, r, stage in rows[::6]:
        et = (t - dt.timedelta(hours=4)).strftime("%H:%M")
        mark = "dry"
        for lv, name in LADDER:
            if stage >= lv and stage > 0:
                mark = name
        fut = " (proj)" if t > end_obs else ""
        print(f"  {et}  rate {r:4.1f}  street {stage:+5.1f}\" [{mark}]{fut}")
    peak = max(rows, key=lambda x: x[2])
    print(f"\npeak: {peak[2]:+.1f}\" vs SW grate at "
          f"{(peak[0] - dt.timedelta(hours=4)).strftime('%H:%M')} ET"
          + (" (projected)" if peak[0] > end_obs else " (already occurring)"))


if __name__ == "__main__":
    main()
