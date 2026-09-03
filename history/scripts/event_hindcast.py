"""Tank hindcast + hydrograph plot for an event from cached MRMS
box-mean frames. Usage: event_hindcast.py DATE T0Z T1Z BAY_NAVD88 OUT
(BAY may be 'gauge' to fetch the despiked mean over the window).

Overlays, if present in assets/observations/DATE/:
  observed_points.json  [{t: naive-ET ISO, in: measured}]   — dots
  witness_bounds.json   [{t, min_in, note}]  — hollow circles with
    up-arrows: testimony-derived LOWER bounds [STATED], never
    measurements; the printed model-vs-bound gap quantifies bias
    only in the direction the bound allows (model below a lower
    bound is a real miss; model above it proves nothing).

Run from the repo root. This is the shared recipe cited by event
READMEs (2026-08-27, 2026-09-01); committed 2026-09-02 after living
only in a session scratchpad — rule 4 applies to scripts too."""
import csv, json, sys, os, datetime as dt, urllib.request
sys.path.insert(0, "forecast")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import flood_forecast_daily as ff

date, t0s, t1s, bayarg, out = sys.argv[1:6]
t0 = dt.datetime.fromisoformat(f"{date}T{t0s}:00+00:00")
t1 = dt.datetime.fromisoformat(f"{date}T{t1s}:00+00:00")
if t1 < t0:
    t1 += dt.timedelta(days=1)

frames = []
with open("history/data/mrms/mrms_extracted.csv") as f:
    for r in csv.DictReader(f):
        if r["product"] != "PrecipRate":
            continue
        t = dt.datetime.fromisoformat(r["utc"].replace("Z", "+00:00"))
        if t0 <= t <= t1:
            frames.append((t, float(r["box_mean"]) / 25.4))
frames.sort()
assert frames, "no frames in window"

if bayarg == "gauge":
    b = (t0 - dt.timedelta(hours=1)).astimezone(
        dt.timezone(dt.timedelta(hours=-4)))
    e = t1.astimezone(dt.timezone(dt.timedelta(hours=-4)))
    url = ("https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?"
           "station=8531680&product=water_level&datum=MLLW&"
           "time_zone=lst_ldt&units=english&"
           f"begin_date={b:%Y%m%d%%20%H:%M}&end_date={e:%Y%m%d%%20%H:%M}"
           "&format=json")
    rows = json.load(urllib.request.urlopen(url, timeout=20))["data"]
    bay = sum(float(r["v"]) for r in rows) / len(rows) - 2.82
else:
    bay = float(bayarg)

ff._load_stage_curve()
drain = ff.PLUVIAL_DRAIN_RATE * min(1, max(0, (3.52 - bay) / 0.52))
base = max(0.0, (bay - 3.52) * 12)
lag = dt.timedelta(minutes=ff.TANK_LAG_MIN)

def rate_at(t):
    tl = t - lag
    prev = frames[0]
    for pt in frames:
        if pt[0] > tl:
            break
        prev = pt
    return prev[1] if tl >= frames[0][0] else 0.0

V, t = 0.0, frames[0][0]
traj = []
while t <= frames[-1][0] + dt.timedelta(minutes=40):
    r = rate_at(t)
    net = max(0.0, r - drain)
    V = max(0.0, V + (ff.TANK_K * net ** ff.TANK_GAMMA
                      - ff.TANK_KOUT * V) * (2.0 / 60.0))
    stage = ff._pluvial_fill(ff._STAGE_CURVE, base, V) if V > 0 else base
    traj.append((t, stage))
    t += dt.timedelta(minutes=2)
pk_t, pk = max(traj, key=lambda x: x[1])
print(f"HINDCAST {date}: bay {bay:.2f} NAVD88, drain {drain:.2f}; "
      f"peak +{pk:.1f} in @ {pk_t:%H:%M}Z "
      f"({(pk_t - dt.timedelta(hours=4)):%H:%M} ET)")

ET = dt.timedelta(hours=-4)
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8.6, 6.2), sharex=True,
                               height_ratios=[1, 1.6])
ax1.step([(f[0] + ET) for f in frames], [f[1] for f in frames],
         where="post", color="#2c5f8a", lw=1.6)
ax1.set_ylabel("rain (in/hr)\nMRMS box mean", fontsize=8.5)
ax1.grid(alpha=0.2)
ax2.plot([(p[0] + ET) for p in traj], [p[1] for p in traj],
         color="#d97706", lw=2, label="v0.10.1 tank hindcast")
for elev, col, name in [(0, "#222222", "SW grate 0″"),
                        (3.1, "#2f8f5f", "gutter"),
                        (7.7, "#c0392b", "curb"),
                        (13.7, "#7c4dbc", "lawn step"),
                        (22.7, "#6d4c2f", "porch step top")]:
    ax2.axhline(elev, color=col, lw=1,
                ls="-" if elev == 0 else "--", alpha=0.8)
    ax2.text(1.001, elev, name, transform=ax2.get_yaxis_transform(),
             fontsize=7, color=col, va="center")
obs_file = f"assets/observations/{date}/observed_points.json"
if os.path.exists(obs_file):
    obs = json.load(open(obs_file))
    ax2.plot([dt.datetime.fromisoformat(o["t"]) for o in obs],
             [o["in"] for o in obs], "o", color="#0b3d6b", ms=7,
             label="observed (photos/EXIF)", zorder=5)
wb_file = f"assets/observations/{date}/witness_bounds.json"
if os.path.exists(wb_file):
    lab = "witness lower bound [STATED]"
    for w in json.load(open(wb_file)):
        wt = dt.datetime.fromisoformat(w["t"])
        ax2.annotate("", xy=(wt, w["min_in"] + 2.6),
                     xytext=(wt, w["min_in"]),
                     arrowprops=dict(arrowstyle="-|>", color="#0b6b3d",
                                     lw=1.5))
        ax2.plot([wt], [w["min_in"]], marker="o", mfc="none",
                 mec="#0b6b3d", ms=8, mew=1.8, zorder=5, label=lab)
        lab = None
        ax2.annotate(w["note"], xy=(wt, w["min_in"]),
                     xytext=(7, -11), textcoords="offset points",
                     fontsize=6.5, color="#0b6b3d", ha="left")
        wu = (wt.replace(tzinfo=dt.timezone(dt.timedelta(hours=-4)))
              .astimezone(dt.timezone.utc))
        m = min(traj, key=lambda p: abs((p[0] - wu).total_seconds()))
        print(f"WITNESS {w['t']} ET: bound >= {w['min_in']:.1f} in "
              f"({w['note']}); model {m[1]:.1f} in there "
              f"(model - bound = {m[1] - w['min_in']:+.1f})")
ax2.set_ylabel("street water (in vs SW grate)", fontsize=8.5)
ax2.legend(fontsize=8, loc="upper right")
ax2.grid(alpha=0.2)
import matplotlib.dates as mdates
ax2.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
ax1.set_title(f"{date} — MRMS rain + v0.10.1 tank hindcast "
              f"(bay {bay:.2f} NAVD88, drain {drain:.2f} in/hr)",
              fontsize=9.5)
fig.tight_layout()
plt.savefig(out, dpi=115)
print("wrote", out)
