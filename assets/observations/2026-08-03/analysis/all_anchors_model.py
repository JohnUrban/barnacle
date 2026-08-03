"""v0.10.1 tank hindcast peaks for all six measured anchors.

Same integration recipe as the 2026-08-03 hindcast (event_plots.py):
step-hold of the latest MRMS frame value, dt=2 min, V=0 at start,
production constants + production stage curve via flood_forecast_daily.
Rain zeroed one frame-interval after the last frame (tail rates are all
below/at drain capacity, so peaks are insensitive to this choice).
"""
import sys, datetime as dt
sys.path.insert(0, "/Users/johnurban/searchPaths/github/barnacle/forecast")
import flood_forecast_daily as ff

ff._load_stage_curve()
GRATE = 3.52
KNEE = 3.0

def drain(bay):
    frac = min(1.0, max(0.0, (GRATE - bay) / (GRATE - KNEE)))
    return 0.25 * frac

def T(y, mo, d, s):
    return dt.datetime(y, mo, d, int(s[:2]), int(s[3:]))

def simulate(day, rain, bay, run_from, run_to, frame_min):
    """rain: [(\"HH:MM\", in/hr)] frames on the given (y,mo,d) day."""
    y, mo, d = day
    times = [T(y, mo, d, s) for s, _ in rain]
    vals = {T(y, mo, d, s): v for s, v in rain}
    cutoff = times[-1] + dt.timedelta(minutes=frame_min)
    lag = dt.timedelta(minutes=ff.TANK_LAG_MIN)
    D = drain(bay)
    base = max(0.0, (bay - GRATE) * 12)
    V = 0.0
    out = []
    t, end = T(y, mo, d, run_from), T(y, mo, d, run_to)
    while t <= end:
        tl = t - lag
        r = 0.0
        if tl <= cutoff:
            for tt in times:
                if tt <= tl:
                    r = vals[tt]
                else:
                    break
        net = max(0.0, r - D)
        V = max(0.0, V + (ff.TANK_K * net ** ff.TANK_GAMMA
                          - ff.TANK_KOUT * V) * (2 / 60.0))
        stage = ff._pluvial_fill(ff._STAGE_CURVE, base, V) if V > 0 else base
        out.append((t, stage))
        t += dt.timedelta(minutes=2)
    return out

EVENTS = {
    # 7/6/2026 — MRMS 4-min point rates, bay LOW 2.55
    "jul6": dict(day=(2026, 7, 6), bay=2.55, frame=4,
        run=("10:20", "12:40"),
        rain=[("10:40",0.34),("10:44",0.99),("10:48",1.02),("10:52",1.32),
              ("10:56",0.93),("11:00",0.64),("11:04",1.61),("11:08",1.43),
              ("11:12",2.95),("11:16",2.37),("11:20",2.07),("11:24",0.54),
              ("11:28",0.78),("11:32",0.31),("11:36",0.23),("11:40",0.34),
              ("11:50",0.10),("12:00",0.05)]),
    # 7/9/2026 — MRMS 10-min point rates, bay at grates 3.2
    "jul9": dict(day=(2026, 7, 9), bay=3.20, frame=10,
        run=("14:50", "16:50"),
        rain=[("15:00",0.07),("15:10",0.29),("15:20",0.61),("15:30",4.18),
              ("15:40",5.53),("15:50",3.46),("16:00",0.0),("16:10",0.0),
              ("16:20",0.0),("16:30",0.0)]),
    # Oct 30 2025 — MRMS 10-min rates, bay HIGH 4.81 (base +15.5)
    "oct30": dict(day=(2025, 10, 30), bay=4.81, frame=10,
        run=("13:00", "16:40"),
        rain=[("13:30",0.16),("13:40",0.32),("13:50",0.33),("14:00",0.14),
              ("14:10",0.21),("14:20",0.37),("14:30",0.23),("14:40",0.89),
              ("14:50",2.71),("15:00",2.35),("15:10",0.15),("15:20",0.06),
              ("15:30",0.03),("15:40",0.0),("16:00",0.0)]),
    # Dec 19 2025 — MRMS 20-min rates, bay HIGH 4.043 (base +6.3)
    "dec19": dict(day=(2025, 12, 19), bay=4.043, frame=20,
        run=("05:30", "10:20"),
        rain=[("06:00",0.02),("06:20",0.08),("06:40",0.01),("07:00",1.83),
              ("07:20",0.44),("07:40",0.31),("08:00",0.31),("08:20",0.21),
              ("08:40",0.26),("09:00",0.09),("09:20",0.07),("09:40",0.0)]),
    # 7/18/2026 — MRMS catchment land-only box means (NEW geometry,
    # box_geometry_backtest.txt), bay LOW ebbing neap ~2.2. Core underread.
    "jul18": dict(day=(2026, 7, 18), bay=2.20, frame=4,
        run=("14:20", "16:50"),
        rain=[("14:40",0.05),("14:44",0.05),("14:48",0.40),("14:52",2.34),
              ("14:56",2.62),("15:00",1.72),("15:04",1.25),("15:08",1.52),
              ("15:12",1.58),("15:16",2.47),("15:20",2.38),("15:24",3.82),
              ("15:28",1.92),("15:32",2.34),("15:36",1.21),("15:40",0.49),
              ("15:44",0.71)]),
    # 8/3/2026 — MRMS 2-min catchment means, bay LOW 2.3-2.95
    "aug3": dict(day=(2026, 8, 3), bay=2.30, frame=2,
        run=("09:50", "11:30"),
        rain=[("09:50",.01),("09:52",.04),("09:54",.04),("09:56",.04),
              ("09:58",.09),("10:00",.15),("10:02",.14),("10:04",.26),
              ("10:06",.14),("10:08",.30),("10:10",.34),("10:12",.52),
              ("10:14",1.35),("10:16",2.42),("10:18",2.47),("10:20",2.10),
              ("10:22",2.84),("10:24",2.44),("10:26",2.36),("10:28",.94),
              ("10:30",.67),("10:32",.36),("10:34",.33),("10:36",.21),
              ("10:38",.35),("10:40",.36),("10:42",.35),("10:44",.19),
              ("10:46",.27),("10:48",.27),("10:50",.20)]),
}

RESULTS = {}
for name, ev in EVENTS.items():
    sim = simulate(ev["day"], ev["rain"], ev["bay"],
                   ev["run"][0], ev["run"][1], ev["frame"])
    pk_t, pk = max(sim, key=lambda x: x[1])
    RESULTS[name] = (pk, pk_t)
    print(f"{name:6s} bay {ev['bay']:.2f}  v0.10.1 peak +{pk:.1f} in @ {pk_t:%H:%M} ET")
    if name == "dec19":
        t812 = min(sim, key=lambda x: abs((x[0] - T(2025,12,19,'08:12')).total_seconds()))
        RESULTS["dec19_at_obs"] = (t812[1], t812[0])
        print(f"       dec19 AT 08:12 obs time: +{t812[1]:.1f} in (obs band 10.1-12.2)")
