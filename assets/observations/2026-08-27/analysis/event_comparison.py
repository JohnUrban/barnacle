#!/usr/bin/env python3
"""Aug 27 2026 vs every logged storm — onset-aligned street-water
overlay (audience: the witnesses, Kevin + Jackie; user request
2026-09-02).

One axes: v0.10.1 tank replay of each storm's street-water curve,
x = minutes since that storm's rain first exceeded full drain
capacity (0.25 in/hr), so rise/crest/recession shapes compare
directly. Aug 27 is the thick red line; the other eight are thin
references. Curves are MODEL reconstructions from radar rain —
measured peaks in the legend are the ground truth where John
measured (the model typically reads 1-2 inches low with the storm
core overhead). Aug 27 itself is unmeasured; its one witness bound
(water entering the driveway at ~2:43 PM, elapsed ~31 min) is the
green marker.

Rain sources: the six frozen-replay events come from
model/data/v0.10.1-reproduction.json via
history/scripts/reproduce_v0_10_1.py (read-only); Aug 7 / Aug 27 /
Sep 1 come from the committed MRMS cache
history/data/mrms/mrms_extracted.csv. Aug 7's gauge ramp
(0.77->~2.1 NAVD88) never leaves the full-drain / zero-base regime,
so a constant bay is physically identical over the window.

Run from anywhere: python3 event_comparison.py
Output: event_comparison.png beside this script.
"""
import csv
import datetime as dt
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

HERE = Path(__file__).resolve()
REPO = HERE.parents[4]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
from history.scripts.reproduce_v0_10_1 import (  # noqa: E402
    load_fixture, simulate_hindcast_event, _local_time)
sys.path.insert(0, str(REPO / "forecast"))
import flood_forecast_daily as ff  # noqa: E402

ONSET_IN_HR = ff.PLUVIAL_DRAIN_RATE   # t=0: rain first beats the drains
STAR = "2026-08-27"

# ---- six frozen-replay events (fixture rain, local naive times) ----
fx = load_fixture()
curves = {}   # id -> (elapsed_minutes[], stage[])
for ev in fx["hindcast"]["events"]:
    rain = [(_local_time(ev["date"], w), float(r))
            for w, r in ev["rain_in_hr"]]
    onset = next(t for t, r in rain if r >= ONSET_IN_HR)
    traj = simulate_hindcast_event(ev, fx)
    curves[ev["id"]] = (
        [(t - onset).total_seconds() / 60 for t, _ in traj],
        [s for _, s in traj])

# ---- three MRMS-cache events (recipe physics, 2-min step-held) ----
CSV_EVENTS = [   # id, window t0/t1 (UTC), bay NAVD88 (constant ok: see doc)
    ("aug7",  "2026-08-07T21:50", "2026-08-08T00:30", 0.9),
    ("aug27", "2026-08-27T18:00", "2026-08-27T20:30", -1.32),
    ("sep1",  "2026-09-01T22:00", "2026-09-02T00:30", -0.7),
]
rows = [r for r in csv.DictReader(
            open(REPO / "history" / "data" / "mrms" / "mrms_extracted.csv"))
        if r["product"] == "PrecipRate"]
ff._load_stage_curve()
for eid, t0s, t1s, bay in CSV_EVENTS:
    t0 = dt.datetime.fromisoformat(t0s + ":00+00:00")
    t1 = dt.datetime.fromisoformat(t1s + ":00+00:00")
    frames = sorted(
        (dt.datetime.fromisoformat(r["utc"].replace("Z", "+00:00")),
         float(r["box_mean"]) / 25.4)
        for r in rows
        if t0 <= dt.datetime.fromisoformat(r["utc"].replace("Z", "+00:00")) <= t1)
    assert frames, f"no frames for {eid}"
    onset = next(t for t, r in frames if r >= ONSET_IN_HR)
    drain = ff.PLUVIAL_DRAIN_RATE * min(1, max(0, (3.52 - bay) / 0.52))
    base = max(0.0, (bay - 3.52) * 12)
    lag = dt.timedelta(minutes=ff.TANK_LAG_MIN)
    V, t = 0.0, frames[0][0]
    el, st = [], []
    while t <= frames[-1][0] + dt.timedelta(minutes=40):
        tl, r = t - lag, 0.0
        for tt, rr in frames:
            if tt > tl:
                break
            r = rr
        if tl < frames[0][0]:
            r = 0.0
        net = max(0.0, r - drain)
        V = max(0.0, V + (ff.TANK_K * net ** ff.TANK_GAMMA
                          - ff.TANK_KOUT * V) * (2.0 / 60.0))
        el.append((t - onset).total_seconds() / 60)
        st.append(ff._pluvial_fill(ff._STAGE_CURVE, base, V) if V > 0 else base)
        t += dt.timedelta(minutes=2)
    curves[eid] = (el, st)

# ---- styling: chronological; measured peaks are legend ground truth ----
EVENTS = [
    ("oct30", "#17365d", "Oct 30 2025 — bay HIGH (measured ≥ +20.8″)"),
    ("dec19", "#708090", "Dec 19 2025 — steady rain, bay high (measured ≈ +11.2″)"),
    ("jul6",  "#6d4c2f", "Jul 6 2026 (measured +15.4″)"),
    ("jul9",  "#d97706", "Jul 9 2026 (measured +18.7″)"),
    ("jul18", "#7c4dbc", "Jul 18 2026 (measured +19.9″)"),
    ("aug3",  "#0f766e", "Aug 3 2026 (measured +13.8″)"),
    ("aug7",  "#2f8f5f", "Aug 7 2026 (measured ≈ +15.4″)"),
    ("aug27", "#c1272d", "AUG 27 2026 — THIS STORM (model +16.4″; unmeasured)"),
    ("sep1",  "#2e6da4", "Sep 1 2026 (measured +13.9″)"),
]

fig, ax = plt.subplots(figsize=(10.5, 6.8))
for y, c, ls, lw, lbl in [(0.0, "#222222", "-", 1.3, "storm-drain grate 0″"),
                          (3.1, "#2f8f5f", "--", 0.9, "gutter"),
                          (7.7, "#c0392b", "--", 0.9, "curb"),
                          (13.7, "#7c4dbc", "--", 0.9, "lawn step"),
                          (22.7, "#6d4c2f", "--", 1.2, "porch step top")]:
    ax.axhline(y, color=c, ls=ls, lw=lw, alpha=0.6, zorder=1)
    ax.text(1.003, y, lbl, transform=ax.get_yaxis_transform(),
            fontsize=7, color=c, va="center")

for eid, color, label in EVENTS:
    el, st = curves[eid]
    star = eid == "aug27"
    ax.plot(el, st, color=color, label=label,
            lw=3.4 if star else 1.25, alpha=1.0 if star else 0.8,
            zorder=10 if star else 3)

# Kevin + Jackie's own data point: driveway-reach as they left ~2:43
wx = 31   # 14:43 ET minus the 14:12 ET onset
ax.plot([wx], [13.8], marker="o", mfc="none", mec="#0b6b3d", ms=9,
        mew=2, zorder=11)
ax.annotate("water entering the driveway\nas you left (~2:43)",
            xy=(wx + 1, 14.2), xytext=(-2, 20.4), fontsize=7.5,
            color="#0b6b3d", ha="left", va="center",
            arrowprops=dict(arrowstyle="->", color="#0b6b3d", lw=1.1,
                            shrinkB=4))

ax.set_xlim(-5, 215)
ax.set_ylim(-1, 24.5)
ax.xaxis.set_major_locator(MultipleLocator(30))
ax.xaxis.set_minor_locator(MultipleLocator(15))
ax.grid(alpha=0.18, which="major")
ax.set_xlabel("minutes since rain first beat the storm drains (0.25 in/hr)",
              fontsize=9)
ax.set_ylabel("street water at Bay & Central (inches above the grate)",
              fontsize=9)
ax.set_title("How big was the Aug 27 storm? — nine logged storms, "
             "aligned at rain onset\n"
             "curves = v0.10.1 model replay from radar rain; measured "
             "peaks in the legend are ground truth (model tends 1–2″ "
             "low with the core overhead)", fontsize=9.5)
ax.legend(fontsize=6.8, ncol=3, loc="upper center",
          bbox_to_anchor=(0.5, -0.12), frameon=False)
fig.subplots_adjust(bottom=0.26, right=0.87)
out = HERE.parent / "event_comparison.png"
plt.savefig(out, dpi=130)
print("wrote", out)
for eid, _, label in EVENTS:
    el, st = curves[eid]
    i = max(range(len(st)), key=lambda j: st[j])
    print(f"  {eid:6s} model peak +{st[i]:4.1f}″ @ {el[i]:3.0f} min — {label}")
