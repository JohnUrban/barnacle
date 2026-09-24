"""Item 5 bounded comparison for v0.10.6 (audits/2026-09-24-a1 R6); method
predeclared in history/plans/2026-09-23-v0.10.6-outlook-review.md.
Revision r2 (2026-09-24, Codex round 03): every event's reference peak is
labeled by evidence type and primary record; 2025-10-30 (reconstruction) is
kept OUT of the observed-reference aggregates; errors are also scored against
each accepted bracket; issuance uses the last hourly reading AT OR BEFORE the
issuance time, decaying from that reading's time; part B also groups by the
maximum bay over the simulated window; part D is a partial-input
sensitivity experiment (unarchived hours are zero by assumption), not
forecast skill.
B: controlled wet scenarios (sensitivity, not skill). C: measured events with
MRMS rain (reconstructed hindcast, not as-issued skill). D: the Sep 13 as-issued
forecast's saved QPF windows (partial as-issued inputs).
Read-only; needs history/data/forecast_test/surge_hourly.parquet (pull script).
Run: python3 history/scripts/v0106_rain_comparison.py
"""
import csv, datetime as dt, json, math, subprocess, sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from forecast import flood_forecast_daily as ff  # noqa: E402

UTC = dt.timezone.utc
TAU, MEAN_FALLBACK = 36.0, 0.54
GRATE, CURB_IN, LAWN_IN = 3.52, 7.7, 13.7
ENH, OFF = ff.LOCAL_ENHANCEMENT_FT, ff.MLLW_TO_NAVD88_OFFSET
sv = pd.read_parquet(ROOT / "history/data/forecast_test/surge_hourly.parquet").set_index("timestamp").asfreq("h")
sv.index = sv.index.tz_localize("UTC")
trail = sv.surge_ft.rolling(24 * 365, min_periods=24 * 300).mean().shift(1)


def interp(series, t):
    """Linear interpolation of an hourly pandas series at aware time t."""
    t0 = t.replace(minute=0, second=0, microsecond=0)
    t1 = t0 + dt.timedelta(hours=1)
    a, b = series.get(pd.Timestamp(t0)), series.get(pd.Timestamp(t1))
    if a is None or b is None or not (math.isfinite(a) and math.isfinite(b)):
        return a if (a is not None and math.isfinite(a)) else None
    f = (t - t0).total_seconds() / 3600.0
    return a + (b - a) * f


def tank(times, bays, rates):
    out = ff.simulate_pluvial_series(times, bays, rates)
    peaks = [(p if p is not None else b) for p, b in zip(out, bays)]
    return out, peaks


def inches(w):
    return (w - GRATE) * 12.0


def minutes_above(times, levels, inch_thr):
    step = (times[1] - times[0]).total_seconds() / 60.0
    return sum(step for w in levels if w is not None and inches(w) >= inch_thr)


def reading_at_or_before(t_iss):
    """The last hourly observed surge available at issuance, and its time."""
    t0 = t_iss.replace(minute=0, second=0, microsecond=0)
    for k in range(0, 4):
        tt = t0 - dt.timedelta(hours=k)
        v = sv.surge_ft.get(pd.Timestamp(tt))
        if v is not None and math.isfinite(v):
            return float(v), tt
    return None, None


def bay_curves(times, t_iss, mean, reading=None):
    s, t_obs = reading if reading else reading_at_or_before(t_iss)
    astro = [interp(sv.predicted_mllw, t) for t in times]
    obs = [interp(sv.observed_mllw, t) for t in times]
    const = [a + s + ENH + OFF for a in astro]
    decay = [a + mean + (s - mean) * math.exp(-max(0.0, (t - t_obs).total_seconds()) / 3600 / TAU) + ENH + OFF
             for a, t in zip(astro, times)]
    obsb = [(o + ENH + OFF) if o is not None else None for o in obs]
    return s, const, decay, obsb


print("=== B. Controlled wet scenarios (sensitivity under identical rain; NOT skill) ===")
t_iss = dt.datetime(2025, 10, 1, 0, tzinfo=UTC)
pred = sv.predicted_mllw[t_iss: t_iss + dt.timedelta(hours=60)]
vals = pred.values
idx = pred.index
phases = {}
for lead in (6, 12, 24):
    win = [(i, t) for i, t in enumerate(idx) if abs((t - t_iss).total_seconds() / 3600 - lead) <= 6.5 and 0 < i < len(vals) - 1]
    hi = max(win, key=lambda x: vals[x[0]]); lo = min(win, key=lambda x: vals[x[0]])
    mid = min(win, key=lambda x: abs(vals[x[0]] - (vals[hi[0]] + vals[lo[0]]) / 2) if vals[x[0] + 1] > vals[x[0]] else 99)
    phases[lead] = {"low": lo[1].to_pydatetime(), "mid (rising)": mid[1].to_pydatetime(), "high": hi[1].to_pydatetime()}
rows = []
for s_obs in (1.0, 2.0):
    for lead, ph in phases.items():
        for pname, center in ph.items():
            for rate in (0.3, 0.6, 1.0):
                start = center - dt.timedelta(hours=1.5)
                times = [start - dt.timedelta(hours=2) + dt.timedelta(minutes=5 * k) for k in range(12 * 9)]
                rates = [rate if start <= t < start + dt.timedelta(hours=3) else 0.0 for t in times]
                astro = [interp(sv.predicted_mllw, t) for t in times]
                const = [a + s_obs + ENH + OFF for a in astro]
                decay = [a + MEAN_FALLBACK + (s_obs - MEAN_FALLBACK) * math.exp(-(t - t_iss).total_seconds() / 3600 / TAU) + ENH + OFF
                         for a, t in zip(astro, times)]
                _, pc = tank(times, const, rates); _, pd_ = tank(times, decay, rates)
                i_bay = times.index(min(times, key=lambda t: abs((t - center).total_seconds())))
                rows.append({"reading": s_obs, "lead": lead, "phase": pname, "rain": rate,
                             "bay_v5": round(const[i_bay], 2), "bay_v6": round(decay[i_bay], 2),
                             "bay_v5_max": round(max(const), 2),
                             "peak_in_v5": round(inches(max(pc)), 1), "peak_in_v6": round(inches(max(pd_)), 1),
                             "curb_min_v5": minutes_above(times, pc, CURB_IN), "curb_min_v6": minutes_above(times, pd_, CURB_IN),
                             "lawn_min_v5": minutes_above(times, pc, LAWN_IN), "lawn_min_v6": minutes_above(times, pd_, LAWN_IN)})
df = pd.DataFrame(rows)
df["d_peak_in"] = (df.peak_in_v6 - df.peak_in_v5).round(1)
pd.set_option("display.width", 220)
print(df.to_string(index=False))
bands = [-9, 3.0, 3.52, 99]
labels = ["below 3.0", "3.0-3.52 (plug band)", "above 3.52"]
print("\nsummary A: peak change grouped by the v0.10.5 bay AT THE BURST CENTER (a single instant):")
df["band_center"] = pd.cut(df.bay_v5, bands, labels=labels)
print(df.groupby("band_center", observed=True).d_peak_in.agg(["count", "mean", "min", "max"]).round(2).to_string())
print("\nsummary B: grouped by the MAXIMUM v0.10.5 bay over the simulated window (the trajectory):")
df["band_max"] = pd.cut(df.bay_v5_max, bands, labels=labels)
print(df.groupby("band_max", observed=True).d_peak_in.agg(["count", "mean", "min", "max"]).round(2).to_string())
print("(a case centered below 3.0 ft can still cross the drain band during the window: grouping by center"
      " time understates where changes occur)")

print("\n=== C. Measured events, MRMS rain, bay from each rule (reconstructed hindcast; NOT as-issued skill) ===")
# Reference peaks, inches over the SW grate: (canonical, bracket lo, bracket hi, evidence type, primary record)
EVENTS = {
    "2026-07-06": (15.4, 15.0, 15.8, "tape series; accepted crest window (DECISION 7/6-anchor)",
                   "assets/observations/2026-07-06/README.md; labeled_observations 2026-07-06T11:34"),
    "2026-08-03": (13.8, 13.7, 13.9, "live-narrated two-landmark bracket (lawn step / porch base)",
                   "assets/observations/2026-08-03/README.md; labeled_observations 2026-08-03T10:35"),
    "2026-08-07": (15.4, 15.0, 15.8, "recession backcast between a photo-timed rise and a receding tape point",
                   "assets/observations/2026-08-07/README.md; labeled_observations 2026-08-07T18:33/18:43/18:49"),
    "2026-09-01": (13.9, 13.7, 14.2, "EXIF-timed photo landmark bracket",
                   "assets/observations/2026-09-01/README.md"),
    "2026-09-13": (13.7, 13.7, 13.7, "photo-verified landmark level (lawn-step top)",
                   "assets/observations/2026-09-13/README.md; labeled_observations 2026-09-13T07:01"),
}
RECONSTRUCTED = {"2025-10-30": (20.8, 13.5, "1:1 tide-decay extrapolation from one photo anchor; only the "
                                "photo's +13.5 in is a bound (README addendum 2026-09-24)")}
print("reference peaks (NOT all tape-measured):")
for d, (c, lo, hi, kind, rec_) in EVENTS.items():
    print(f"  {d}: canonical +{c} in, bracket +{lo}..+{hi}: {kind} [{rec_}]")
for d, (c, floor, kind) in RECONSTRUCTED.items():
    print(f"  {d}: +{c} in RECONSTRUCTED, floor +{floor}: {kind}; kept OUT of the aggregates")
OBS_PEAK = {d: v[0] for d, v in EVENTS.items()}
OBS_PEAK.update({d: v[0] for d, v in RECONSTRUCTED.items()})
frames = {}
for r in csv.DictReader(open(ROOT / "history/data/mrms/mrms_extracted.csv")):
    if r["product"] == "PrecipRate":
        t = dt.datetime.fromisoformat(r["utc"].replace("Z", "+00:00"))
        frames.setdefault(t.date().isoformat(), []).append((t, float(r["box_mean"]) / 25.4))
crow = []
for day, peak_obs in OBS_PEAK.items():
    fr = sorted(frames.get(day, []))
    if not fr:
        print(day, "no frames"); continue
    wet = [t for t, v in fr if v >= 0.3]
    onset = wet[0] if wet else fr[0][0]
    t0, t1 = fr[0][0] - dt.timedelta(hours=1), fr[-1][0] + dt.timedelta(hours=2)
    times = [t0 + dt.timedelta(minutes=5 * k) for k in range(int((t1 - t0).total_seconds() // 300) + 1)]
    def rate_at(t):
        r = 0.0
        for tt, v in fr:
            if tt <= t:
                r = v
        return r if (t - fr[-1][0]).total_seconds() <= 600 else 0.0
    rates = [rate_at(t) for t in times]
    for lead in (6, 12, 24):
        t_iss = onset - dt.timedelta(hours=lead)
        mean = trail.get(pd.Timestamp(t_iss.replace(minute=0, second=0, microsecond=0)))
        mean = MEAN_FALLBACK if mean is None or not math.isfinite(mean) else float(mean)
        s, const, decay, obsb = bay_curves(times, t_iss, mean)
        if s is None or any(b is None for b in obsb):
            print(day, lead, "missing surge/observed bay"); continue
        _, po = tank(times, obsb, rates); _, pc = tank(times, const, rates); _, pdd = tank(times, decay, rates)
        i_on = times.index(min(times, key=lambda t: abs((t - onset).total_seconds())))
        s_used, t_used = reading_at_or_before(t_iss)
        crow.append({"event": day, "lead": lead, "reading": round(s_used, 2), "reading_utc": t_used.strftime("%m-%d %H:%MZ"),
                     "mean": round(mean, 2), "ref": "reconstructed" if day in RECONSTRUCTED else "observed",
                     "bay_obs": round(obsb[i_on], 2), "bay_v5": round(const[i_on], 2), "bay_v6": round(decay[i_on], 2),
                     "peak_ref": peak_obs, "peak_obsbay": round(inches(max(po)), 1),
                     "peak_v5": round(inches(max(pc)), 1), "peak_v6": round(inches(max(pdd)), 1)})
cd = pd.DataFrame(crow)
cd["baybias_v5"] = (cd.bay_v5 - cd.bay_obs).round(2); cd["baybias_v6"] = (cd.bay_v6 - cd.bay_obs).round(2)
cd["err_v5"] = (cd.peak_v5 - cd.peak_ref).round(1); cd["err_v6"] = (cd.peak_v6 - cd.peak_ref).round(1)


def bracket_err(v, day):
    lo, hi = EVENTS[day][1], EVENTS[day][2]
    return 0.0 if lo <= v <= hi else min(abs(v - lo), abs(v - hi))
print(cd.to_string(index=False))
ob = cd[cd.ref == "observed"]
print(f"\nBAY (gauge-based; all six events incl. 2025-10-30): mean |bay error| at onset "
      f"v0.10.5 {cd.baybias_v5.abs().mean():.2f} ft, v0.10.6 {cd.baybias_v6.abs().mean():.2f} ft (n={len(cd)}); "
      f"five observed-reference events only: {ob.baybias_v5.abs().mean():.2f} vs {ob.baybias_v6.abs().mean():.2f} ft")
print(f"PEAK vs OBSERVED references (five events, 2025-10-30 excluded, n={len(ob)}): mean |error| vs canonical "
      f"v0.10.5 {ob.err_v5.abs().mean():.2f} in, v0.10.6 {ob.err_v6.abs().mean():.2f} in; vs accepted bracket "
      f"{sum(bracket_err(v, d) for v, d in zip(ob.peak_v5, ob.event)) / len(ob):.2f} vs "
      f"{sum(bracket_err(v, d) for v, d in zip(ob.peak_v6, ob.event)) / len(ob):.2f} in; "
      f"simulated peaks differ (|v6-v5| >= 0.1 in) in {int(((ob.peak_v6 - ob.peak_v5).abs() >= 0.1).sum())} of {len(ob)}")
rc = cd[cd.ref == "reconstructed"]
for _, r in rc.iterrows():
    print(f"2025-10-30 (SENSITIVITY ONLY, reconstructed reference) lead {r.lead} h: v0.10.5 +{r.peak_v5} in, v0.10.6 "
          f"+{r.peak_v6} in, tank on the observed gauge bay +{r.peak_obsbay} in; reference unknown between the "
          f"+13.5 floor and the +20.8 reconstruction -> which rule was closer is undetermined")

print("\n=== D. Sep 13 PARTIAL-INPUT SENSITIVITY EXPERIMENT (not forecast skill): commit 3a6c96faf, 2026-09-13T03:14:36Z ===")
print("Only the saved v0.10.3 curve is a genuine archived OUTPUT; the constant/decay curves are counterfactual"
      " reconstructions from the archived surge reading; rain = the saved hourly QPF window, with every"
      " unarchived hour set to ZERO by assumption (a coverage limitation, not a forecast value).")
f = json.loads(subprocess.check_output(["git", "-C", str(ROOT), "show", "3a6c96faf:docs/forecast.json"]))
issued = dt.datetime.fromisoformat(f["generated_utc"].replace("Z", "+00:00"))
qpf = {}
for t in f.get("all_tides") or []:
    if not t["time"].startswith("2026-09-13 09:58"):
        continue                          # the event's tide window only
    # rain_window_3h = [[hour offset of the bucket CENTER from the tide, in/hr], ...]
    tide_utc = ff.parse_station_local_time(t["time"]).astimezone(UTC)
    for off, rate in (t.get("rain_window_3h") or []):
        start = tide_utc + dt.timedelta(hours=off - 0.5)
        qpf[start.replace(minute=0, second=0, microsecond=0) if start.minute < 30
            else (start + dt.timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)] = float(rate or 0.0)
if not qpf:
    print("no hourly QPF found in the saved windows; keys:", list((f.get("all_tides") or [{}])[0].keys()))
else:
    covered = sorted(qpf)
    t0, t1 = covered[0] - dt.timedelta(hours=2), covered[-1] + dt.timedelta(hours=3)
    meas = dt.datetime(2026, 9, 13, 11, 1, tzinfo=UTC)     # photographed peak 07:01 EDT
    print(f"note: the saved window covers {covered[0]:%H:%MZ}-{covered[-1] + dt.timedelta(hours=1):%H:%MZ}; "
          f"the measured burst peaked 10:54-10:58Z (MRMS), inside the 10Z hour, which the window does "
          f"{'' if any(c.hour == 10 for c in covered) else 'NOT '}cover. Uncovered hours are zero rain by assumption.")
    times = [t0 + dt.timedelta(minutes=5 * k) for k in range(int((t1 - t0).total_seconds() // 300) + 1)]
    rates = [qpf.get(t.replace(minute=0, second=0, microsecond=0), 0.0) for t in times]
    mean = float(trail.get(pd.Timestamp(issued.replace(minute=0, second=0, microsecond=0))))
    archived = float(f["current_surge_ft"])     # the reading the issued forecast used (+0.487 ft)
    # its observation time was not archived; the forecast called it fresh, so it is
    # anchored at the issuance time (<= 60 min error in the decay's start)
    s, const, decay, obsb = bay_curves(times, issued, mean, reading=(archived, issued))
    ws = {ff.parse_station_local_time(p["time"]).astimezone(UTC): p["tide_navd88"] for p in f.get("water_series") or []}
    as_issued = [ws.get(t.replace(minute=(0 if t.minute < 30 else 30), second=0, microsecond=0)) for t in times]
    res = {"issued": f["generated_utc"], "qpf_hours_covered": [t.strftime("%H:%MZ") for t in covered],
           "reading_at_issuance": round(s, 2), "mean": round(mean, 2)}
    for name, bays in (("observed bay", obsb), ("as-issued v0.10.3 curve", as_issued), ("v0.10.5 constant", const), ("v0.10.6 decay", decay)):
        if any(b is None for b in bays):
            res[name] = "bay unavailable over the window"; continue
        _, pk = tank(times, bays, rates)
        res[name] = {"bay_range_navd88": [round(min(bays), 2), round(max(bays), 2)],
                     "tank_max_over_window_in": round(inches(max(pk)), 1)}
    res["reference_peak_in"] = "13.7 (photo-verified lawn-step level at 07:01 EDT)"
    res["note"] = ("maxima over the constructed window, not values at the observed crest; the 10Z burst hour "
                   "is not in the saved window, so no forecast-error attribution is possible from this run")
    print(json.dumps(res, indent=1))
