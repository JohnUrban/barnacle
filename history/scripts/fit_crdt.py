"""Fit V = C·(R−D)·T across the three rain anchors using MRMS forcing.

For each event: fill volume (stage-storage curve, tide-set base ->
observed peak) vs net rain input integrated from MRMS. C = V / net.
If C is roughly constant, the linear rate×duration input model holds
and the tanh proxy can be retired.
"""
import csv
from datetime import datetime, timedelta

CURVE = "/Users/johnurban/searchPaths/github/barnacle/history/data/stage_storage_curve.csv"
MRMS = "/Users/johnurban/searchPaths/github/barnacle/history/data/mrms/mrms_extracted.csv"

rows = list(csv.DictReader(open(CURVE)))
stages = [float(r["stage_in_vs_sw_grate"]) for r in rows]
wet = [float(r["wet_area_cells"]) for r in rows]

def vol_between(s0, s1):
    """cell-inches of storage between stages s0 and s1 (inches vs grate)"""
    v = 0.0
    for i in range(1, len(rows)):
        lo, hi = stages[i-1], stages[i]
        if hi <= s0 or lo >= s1:
            continue
        a, b = max(lo, s0), min(hi, s1)
        v += 0.5 * (wet[i-1] + wet[i]) * (b - a)
    return v

# load MRMS PrecipRate series (mm/hr) per date
prec = {}
for r in csv.DictReader(open(MRMS)):
    if r["product"] != "PrecipRate":
        continue
    t = datetime.fromisoformat(r["utc"].replace("Z", "+00:00"))
    prec.setdefault(t.date().isoformat(), []).append((t, float(r["point"]) / 25.4))

def net_input(date, t0_utc, t1_utc, D):
    """integrate max(0, rate - D) dt (inches) over [t0, t1] UTC 'HH:MM',
    trapezoid over available MRMS samples"""
    pts = sorted(prec[date])
    t0 = datetime.fromisoformat(f"{date}T{t0_utc}:00+00:00")
    t1 = datetime.fromisoformat(f"{date}T{t1_utc}:00+00:00")
    sel = [(t, max(0.0, v - D)) for t, v in pts if t0 <= t <= t1]
    tot = 0.0
    for i in range(1, len(sel)):
        dt = (sel[i][0] - sel[i-1][0]).total_seconds() / 3600.0
        tot += 0.5 * (sel[i][1] + sel[i-1][1]) * dt
    return tot, sel

GRATE = 3.52
events = [
    # (label, date, base NAVD88, peak NAVD88, D in/hr, rise window UTC)
    ("7/6/2026  (bay low, drains open)", "2026-07-06", 3.52, 4.803, 0.25, ("14:40", "15:34")),
    ("Oct 30 25 (compound, drains blocked)", "2025-10-30", 4.81, 5.26, 0.0, ("17:30", "19:45")),
    ("Dec 19 25 (moderate rain, drains blocked)", "2025-12-19", 4.04, 4.45, 0.0, ("11:30", "13:15")),
]

print(f"{'event':42s} {'V fill':>10} {'net in':>7} {'C=V/net':>9}")
for label, date, base, peak, D, (t0, t1) in events:
    s0 = max(0.0, (base - GRATE) * 12)
    s1 = (peak - GRATE) * 12
    V = vol_between(s0, s1)
    net, sel = net_input(date, t0, t1, D)
    C = V / net if net > 0 else float("nan")
    print(f"{label:42s} {V:10,.0f} {net:7.2f} {C:9,.0f}   (stage {s0:.1f}->{s1:.1f} in, {len(sel)} samples)")
