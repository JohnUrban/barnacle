#!/usr/bin/env python3
"""Event #10 (2026-09-25..27 nor'easter): corner readings vs the Sandy Hook
gauge for all four surge tides, gate state annotated.

Corner water = landmark NAVD88 + observed_depth_in/12 from
data/labeled_observations.csv (observer john; depth-bearing rows only).
"Dry" / qualitative rows are drawn as ticks on the grate line.
Gauge (NAVD88, 6-min, NOAA 8531680) is cached beside this script in
gauge_cache.json on first run so the figure rebuilds offline.
Run: ~/.barnacle/venv/bin/python event10_corner_vs_gauge.py
"""
import csv, json, sys, datetime as dt, urllib.request
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "forecast"))
import flood_forecast_daily as ff  # noqa: E402

ELEV = {k: e for k, _l, e, _s in ff.LANDMARKS}
TIDES = [  # (title, start, end, gate note)
    ("Fri 9/25 PM — gate closed (believed)", "2026-09-25 17:00", "2026-09-26 00:30",
     "corner DRY as far as observed (user check 20:00-20:30; wife home all evening; flooding elsewhere in town)"),
    ("Sat 9/26 AM — gate closed (inferred)", "2026-09-26 04:00", "2026-09-26 13:30",
     "crest 5.70 @ 09:06-09:13; garage flooded"),
    ("Sat 9/26 PM — gate CLOSED (seen 18:19, ~21:58)", "2026-09-26 17:30", "2026-09-27 00:00",
     "dry through the bay peak; late small crest ~4.22"),
    ("Sun 9/27 AM — gate closed (almost certainly)", "2026-09-27 04:00", "2026-09-27 13:30",
     "crest 5.62 @ 09:44-10:06; garage ~90%"),
]
CACHE = HERE / "gauge_cache.json"


def gauge(start, end):
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    key = f"{start}|{end}"
    if key not in cache:
        b = start.replace("-", "").replace(" ", "%20")
        e = end.replace("-", "").replace(" ", "%20")
        u = ("https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?station=8531680"
             "&product=water_level&datum=NAVD&time_zone=lst_ldt&units=english&format=json"
             f"&begin_date={b}&end_date={e}")
        cache[key] = [(r["t"], float(r["v"])) for r in
                      json.load(urllib.request.urlopen(u, timeout=30))["data"] if r["v"]]
        CACHE.write_text(json.dumps(cache, indent=0))
    return [(dt.datetime.fromisoformat(t), v) for t, v in cache[key]]


rows = list(csv.DictReader(open(REPO / "data" / "labeled_observations.csv")))
fig, axes = plt.subplots(4, 1, figsize=(10, 15))
for ax, (title, s, e, note) in zip(axes, TIDES):
    t0, t1 = dt.datetime.fromisoformat(s), dt.datetime.fromisoformat(e)
    g = gauge(s, e)
    ax.plot([t for t, _ in g], [v for _, v in g], color="#555", lw=1.6,
            label="Sandy Hook gauge (bay)")
    pts, ticks = [], []
    for r in rows:
        try:
            t = dt.datetime.fromisoformat(r["observation_time_local"])
        except ValueError:
            continue
        if not (t0 <= t <= t1) or r.get("observer") != "john":
            continue
        k = r["landmark_key"]
        try:
            pts.append((t, ELEV[k] + float(r["observed_depth_in"]) / 12))
        except (KeyError, ValueError):
            if k in ELEV:
                ticks.append(t)
    if pts:
        pts.sort()
        ax.plot([t for t, _ in pts], [v for _, v in pts], "D-", color="#d97706",
                ms=4, lw=1, label="corner (your readings)")
    for t in ticks:
        ax.plot([t], [3.52], "|", color="#0b6b3d", ms=12, mew=2)
    if ticks:
        ax.plot([], [], "|", color="#0b6b3d", ms=10, mew=2,
                label="qualitative report (e.g. 'no flooding')")
    for y, c, lbl in [(3.52, "#222", "SW grate"), (4.16, "#c0392b", "curb"),
                      (4.66, "#7c4dbc", "lawn step"), (5.41, "#6d4c2f",
                      "1st porch step top = garage entry")]:
        ax.axhline(y, color=c, ls="--", lw=0.9, alpha=0.7)
        ax.text(t1, y, " " + lbl, color=c, fontsize=7, va="center")
    ax.set_title(title, fontsize=10)
    ax.text(0.01, 0.95, note, transform=ax.transAxes, fontsize=8, va="top")
    ax.set_xlim(t0, t1)
    ax.set_ylim(0, 6.2)
    ax.set_ylabel("ft NAVD88")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax.grid(alpha=0.2)
    ax.legend(fontsize=7, loc="lower right")
fig.suptitle("Event #10 — corner vs Sandy Hook across four surge tides "
             "(tide gate closed)", fontsize=12)
fig.tight_layout(rect=(0, 0, 0.93, 0.98))
out = HERE / "corner_vs_gauge.png"
fig.savefig(out, dpi=110)
print("wrote", out)
