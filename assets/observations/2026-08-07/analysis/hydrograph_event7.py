#!/usr/bin/env python3
"""Event #7 (2026-08-07) hydrograph + v0.10.1 hindcast figure.

Two panels, site chart grammar (inches vs SW grate; landmark palette;
stacked panels, no dual axes):
  top    — MRMS catchment-mean rain rate (2-min, from the committed
           cache history/data/mrms/mrms_extracted.csv)
  bottom — measured street water (8 observations, two observers) vs
           the v0.10.1 tank run on true 2-min rates (V=0 @ 21:50Z,
           bay from the despiked gauge, head-dependent drainage)

Also prints the hindcast peak/time vs the measured crest bracket and
the stateless-window question (rising undershoot / falling overshoot
seen live in the 22:35Z/22:57Z production runs).

Run: ~/.barnacle/venv/bin/python hydrograph_event7.py  (from this dir)
"""
import csv
import datetime as dt
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                     "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(_REPO, "forecast"))
import flood_forecast_daily as ff

UTC = dt.timezone.utc
EDT = dt.timezone(dt.timedelta(hours=-4))

# ---- rain forcing: 2-min PrecipRate box means from the cache ----
rates = []
with open(os.path.join(_REPO, "history", "data", "mrms",
                       "mrms_extracted.csv")) as f:
    for r in csv.DictReader(f):
        if r["product"] != "PrecipRate":
            continue
        if not r["utc"].startswith("2026-08-07T2"):
            continue
        t = dt.datetime.strptime(r["utc"], "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=UTC)
        if t < dt.datetime(2026, 8, 7, 21, 50, tzinfo=UTC):
            continue
        rates.append((t, float(r["box_mean"]) / 25.4))
rates.sort()
assert rates, "no cached PrecipRate rows for the window — run the extraction"

# ---- bay level through the event (approx linear from gauge reads) ----
# 18:30 3.59 MLLW = 0.77 NAVD88; slow rise toward 19:30 ~1.2. Water was
# > 2.5 ft below every grate all evening: drains at full head; the
# drain term is effectively constant 0.25 in/hr.
def bay_at(t):
    m = (t - dt.datetime(2026, 8, 7, 22, 30, tzinfo=UTC)).total_seconds() / 3600
    return 0.77 + 0.45 * max(0.0, m)

# ---- v0.10.1 tank on true rates (step-held, dt=2 min, V=0 start) ----
ff._load_stage_curve()
V = 0.0
t = rates[0][0]
end = rates[-1][0] + dt.timedelta(minutes=20)
lag = dt.timedelta(minutes=ff.TANK_LAG_MIN)
traj = []
while t <= end:
    tl = t - lag
    r = 0.0
    for tt, rr in rates:
        if tt > tl:
            break
        r = rr
    bay = bay_at(t)
    drain = ff.PLUVIAL_DRAIN_RATE * min(1, max(0, (3.52 - bay) / 0.52))
    net = max(0.0, r - drain)
    V = max(0.0, V + (ff.TANK_K * net ** ff.TANK_GAMMA
                      - ff.TANK_KOUT * V) * (2.0 / 60.0))
    base = max(0.0, (bay - 3.52) * 12)
    stage = ff._pluvial_fill(ff._STAGE_CURVE, base, V) if V > 0 else base
    traj.append((t, stage))
    t += dt.timedelta(minutes=2)

pk_t, pk = max(traj, key=lambda x: x[1])
print(f"hindcast peak: +{pk:.1f} in at {pk_t.astimezone(EDT):%H:%M} EDT")

# ---- observations (ledger; times EDT) ----
OBS = [
    ("18:26", 9.7, "over sidewalk (rising)", 1.0),
    ("18:33", 13.7, "lawn step (photo 18:33:16)", 1.0),
    ("18:37", 13.9, "porch base (photos 18:37:00)", 1.0),
    ("18:43", 14.9, "1 in up riser (receding)", 1.0),
    ("18:49", 13.7, "level w/ lawn step", 1.0),
    ("18:58", 11.7, "2 in above sidewalk", 1.0),
    ("19:04", 9.7, "sidewalk at lawn step exposed", 1.0),
    ("19:16", 9.7, "household-2: ~sidewalk top (50-60%)", 0.55),
]
CREST = (dt.datetime(2026, 8, 7, 22, 40, tzinfo=UTC), 15.0, 15.8)

fig, (ax1, ax2) = plt.subplots(
    2, 1, figsize=(8.6, 6.4), sharex=True,
    gridspec_kw={"height_ratios": [1, 2.1]})
tt = [x[0].astimezone(EDT) for x in rates]
ax1.step([x for x in tt], [x[1] for x in rates], where="post",
         color="#2c66a0", lw=1.6)
ax1.set_ylabel("rain, in/hr\n(catchment mean)", fontsize=8.5)
ax1.set_title("Event #7 — 2026-08-07: surprise burst on a dead-low tide",
              fontsize=10, weight="bold")
ax1.grid(alpha=0.2)

mt = [x[0].astimezone(EDT) for x in traj]
ax2.plot(mt, [x[1] for x in traj], color="#d97706", lw=2,
         label="v0.10.1 tank hindcast (true 2-min rates)")
for hhmm, level, note, conf in OBS:
    h, m = map(int, hhmm.split(":"))
    ts = dt.datetime(2026, 8, 7, h, m, tzinfo=EDT)
    ax2.plot(ts, level, "o", ms=7,
             color="#1a3a5c" if conf > 0.9 else "#8aa4bd",
             zorder=5)
ax2.plot([], [], "o", color="#1a3a5c", label="measured (john)")
ax2.plot([], [], "o", color="#8aa4bd",
         label="household-2 (stated 50-60%)")
ax2.axhspan(CREST[1], CREST[2],
            xmin=0.0, color="#1a3a5c", alpha=0.10)
ax2.annotate("crest bracket +15.0–15.8\n(~18:40, backcast)",
             xy=(CREST[0].astimezone(EDT), 15.4), fontsize=7.5,
             xytext=(dt.datetime(2026, 8, 7, 19, 5, tzinfo=EDT), 16.6),
             arrowprops=dict(arrowstyle="->", lw=0.8))
for lv, col, name in [(0, "#222222", 'SW grate 0"'),
                      (3.1, "#2f8f5f", "gutter"),
                      (7.7, "#c0392b", "curb"),
                      (13.7, "#7c4dbc", "lawn step"),
                      (22.7, "#6d4c2f", "1st porch step TOP")]:
    ax2.axhline(lv, color=col, lw=1.0,
                ls="-" if lv == 0 else (0, (4, 3)), alpha=0.85)
    ax2.text(mt[-1], lv + 0.25, name, fontsize=7, color=col, ha="right")
ax2.set_ylabel("street water, inches vs SW grate", fontsize=8.5)
ax2.set_ylim(-1, 24)
ax2.legend(fontsize=7.5, loc="upper right")
ax2.grid(alpha=0.2)
import matplotlib.dates as mdates
ax2.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M", tz=EDT))
fig.tight_layout(pad=0.7)
out = os.path.join(os.path.dirname(__file__), "hydrograph.png")
fig.savefig(out, dpi=115)
print("wrote", out)
