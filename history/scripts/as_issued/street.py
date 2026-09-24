"""Study B evaluator (protocol sections 1, 2, 4 and Amendment 1).

Arms at each issuance (half-hourly, NAVD88 ft), all from that issuance's
archived inputs:
  P   the PUBLISHED combined line water_navd88 (genuine as-issued output)
  K   v0.10.5 persisted reading: bay = astronomy - 2.82 + reading (constant)
  D   v0.10.6 decay: bay = astronomy - 2.82 + mean + (reading - mean) e^(-age/36)
  T   tide only: D's bay, no tank                          (B2 diagnostic)
  L   max(D's bay, tank run with the bay fixed at 2.50)     (B2 diagnostic)
K, D and L use the tank from the series start with empty storage and the
as-used hourly rain when archived; otherwise street = bay and the pair can be
at best APPROX-TIDE. Pair classes: EXACT, NEAR, APPROX-TIDE, EXCLUDED.

Admission gates (audit 2026-09-24-a4 R1; Amendment 2): EXACT and NEAR need a
CONTROL replay of the issuance's own published rule to match the published
bay (<= 0.0015 ft) and, with rain, the published pluvial line (no presence
mismatch, <= 0.002 ft), a tank implementation whose fingerprint is supported,
a gap-free half-hour grid and finite inputs; rain must cover every hour from
the series start through the observation (NEAR: only the first core hour
missing). Counterfactual arms are never required to equal the published line.
Round 03 completion (Amendment 3): the published combined line must equal
max(published bay, published pluvial) within 0.002 ft; the 0.0015-ft bay
control applies to every rule (decay, v0.10.5 constant reading, older
constant tide surge); required numbers are validated BEFORE any arithmetic
(finite bay/combined/astronomy/reading/mean, pluvial finite or absent = dry,
rain finite and >= 0; a null rain hour is UNAVAILABLE, never zero) and
failures are reasoned exclusions, never crashes.
Round 05 (Amendment 4): the published series and rule metadata are validated
BEFORE the astronomy check or the reading parse; an invalid published value
is UNSCORABLE (with a reason) in every arm and summary, never a number or a
wet/dry cell; a valid published line stays scorable for B0 whatever
happens to the counterfactual arms.
Observations come from the normalization manifest (R3): points, tolerance
intervals, brackets, bounds, time windows, primary vs sensitivity rows.
"""
from __future__ import annotations

import datetime as dt
import math
import random
from collections import Counter, defaultdict

from . import archive as A
from . import fidelity as F
from . import mean as M
from . import obs as O

UTC = dt.timezone.utc
NAVD = -2.82
BAY_TOL_FT = 0.0015          # published bay stored to 0.001 ft
TANK_TOL_FT = 0.002          # published pluvial stored to 0.001 ft; bay input rounded
MAX_STEP = dt.timedelta(minutes=30, seconds=1)
# tank implementations verified equal to models/wind_shadow/rain_ref.py (14,600 points, 2026-09-24)
SUPPORTED_TANKS = {"c4bb702b2c5d37422bc7415eda7a1c392c052a03865744216d8c39648f9faf0e":
                   "production tank v0.10.1-v0.10.6 (fingerprint of simulate_pluvial_series, _pluvial_fill, constants, curve)"}
TAU_H = 36.0
FIXED_LOW_BAY = 2.50
LEAD_BINS = ((0, 6), (6, 12), (12, 24), (24, 30))
ARMS = ("P", "K", "D", "T", "L")


_num = F.num


def clean_rain(rain):
    """({hour: rate} of valid rates, n_null, n_invalid). Null = unavailable hour;
    negative, non-finite or non-numeric = invalid (the issuance is excluded)."""
    ok, n_null, n_bad = {}, 0, 0
    for h, v in (rain or {}).items():
        if v is None:
            n_null += 1
        elif _num(v) and v >= 0:
            ok[h] = float(v)
        else:
            n_bad += 1
    return ok, n_null, n_bad


def issuance_time(s):
    if s.get("generated_utc"):
        return A.parse_utc(s["generated_utc"]), "generated_utc"
    return dt.datetime.fromisoformat(s["commit_time"]).astimezone(UTC), "commit time (no generation stamp)"


def interp(times, values, t):
    """Linear between the bracketing half-hour points; None outside the grid,
    at a missing value, or across a gap longer than 30 min (a4 R1)."""
    if not times or t < times[0] or t > times[-1]:
        return None
    if t == times[0]:
        return values[0] if _num(values[0]) else None
    for i in range(1, len(times)):
        if times[i] >= t:
            a, b = values[i - 1], values[i]
            if not _num(a) or not _num(b) or (times[i] - times[i - 1]) > MAX_STEP:
                return None
            span = (times[i] - times[i - 1]).total_seconds()
            return a + (b - a) * ((t - times[i - 1]).total_seconds() / span if span else 0.0)
    return None


def window_range(times, values, t0, t1):
    """(min, max) of the interpolated line over [t0, t1] (grid points inside plus ends)."""
    pts = [interp(times, values, t0), interp(times, values, t1)]
    pts += [v for t, v in zip(times, values) if t0 < t < t1]
    if any(not _num(x) for x in pts):
        return None
    return min(pts), max(pts)


def decay(reading, t_read, mean, t, tau=TAU_H):
    age = (t - t_read).total_seconds() / 3600.0
    return reading if age <= 0 else mean + (reading - mean) * math.exp(-age / tau)


class Context:
    def __init__(self, inv_rows=None):
        inv = A.inventory() if inv_rows is None else {"rows": inv_rows}
        self.issuances = [s for s in inv["rows"] if s.get("core_has_tide")]
        for s in self.issuances:
            s["_t"], s["_basis"] = issuance_time(s)
        self.issuances.sort(key=lambda s: s["_t"])
        self.p30, self.p6, self.hilo = F.load_astronomy()
        self.means = M.MeanSeries()
        self.replay = {r["generated_utc"]: r for r, _i in A.replay_records()}
        self.tank = F._tank()
        self._blobs, self._arms = {}, {}

    def tank_fingerprint(self, s):
        return F.tank_fingerprint(s["commit"])

    def forecast(self, s):
        if s["blob"] not in self._blobs:
            self._blobs[s["blob"]] = A.load_forecast(s["blob"])
        return self._blobs[s["blob"]]


def reading_of(f, p30):
    """(value, time, basis, exact) of the observed-surge reading at issuance."""
    wsi = f.get("water_series_input") or {}
    dec = wsi.get("decay") or {}
    if dec.get("surge_obs_ft") is not None and dec.get("observation_utc"):
        return dec["surge_obs_ft"], A.parse_utc(dec["observation_utc"]), "published (v0.10.6)", True
    if wsi.get("surge_ft") is not None and wsi.get("observation_time"):
        t = F.parse_station_local_time(wsi["observation_time"]).astimezone(UTC)
        return float(wsi["surge_ft"]), t, "published (v0.10.5)", True
    r = F.f4_reading(f, p30)
    if r.get("status") != "rebuilt":
        return None, None, r.get("status"), False
    t = A.parse_utc(r["reading_time_utc"])
    if f.get("surge_source") == "surge-persistence" and f.get("current_surge_ft") is not None:
        if abs(r["rebuilt_ft"] - f["current_surge_ft"]) <= 0.0005:
            return r["rebuilt_ft"], t, "rebuilt = published persistence surge", True
        return None, None, "rebuilt reading disagrees with the published persistence surge", False
    return r["rebuilt_ft"], t, "rebuilt from published gauge levels (unverified)", False


def control_constant(f, p30, pts):
    """The constant surge a constant-rule curve used: the v0.10.5 published
    reading, else the published tide surge that the curve implies (within
    0.002 ft); None when neither is established."""
    wsi = f.get("water_series_input") or {}
    if _num(wsi.get("surge_ft")):
        return float(wsi["surge_ft"])
    implied = [p["tide_navd88"] - (p30[t] + NAVD) for t, p in pts]
    mid = sorted(implied)[len(implied) // 2]
    cands = [t.get("surge_ft") for t in (f.get("all_tides") or []) if _num(t.get("surge_ft"))]
    near = [c for c in cands if abs(c - mid) <= 0.002]
    return min(near, key=lambda c: abs(c - mid)) if near else None


def arms(ctx, s):
    """Half-hourly arm series and the input-class facts for one issuance."""
    if s["blob"] in ctx._arms:
        return ctx._arms[s["blob"]]
    f = ctx.forecast(s)
    pts = [(t, p) for t, p in F.core_points(f) if p.get("tide_navd88") is not None]
    times = [t for t, _p in pts]
    # the published line: invalid values become None (UNSCORABLE), never numbers
    res = {"times": times, "P": [p.get("water_navd88") if _num(p.get("water_navd88")) else None for _t, p in pts],
           "P_pluvial": [p.get("pluvial_navd88") if _num(p.get("pluvial_navd88")) else None for _t, p in pts],
           "reasons": [], "facts": {}}
    sp, rp = F.series_problems(pts), F.rule_problems(f)
    res["facts"]["published_invalid"] = sp
    if sp or rp:
        # validated before any astronomy/reading arithmetic (a4 round 05)
        res["reasons"].append("invalid published input: " + "; ".join(
            [f"{n} invalid {k} value(s)" for k, n in sorted(sp.items())] + rp))
        ctx._arms[s["blob"]] = res
        return res
    f1 = F.f1_astronomy(f, ctx.p30)
    astro_ok = ("max_abs_vs_rule" in f1 and f1["max_abs_vs_rule"] <= 0.0025) or (
        f1.get("spread") is not None and f1["spread"] <= 0.0025 and f1.get("matches_a_tide_surge"))
    if f1.get("stale_tides_flag") or not astro_ok:
        res["reasons"].append("astronomy not reproduced (outage synthesis or rule mismatch)")
    val, t_r, basis, r_exact = reading_of(f, ctx.p30)
    res["facts"].update(reading=val, reading_time=t_r, reading_basis=basis, reading_exact=r_exact)
    if val is None:
        res["reasons"].append(f"reading unavailable: {basis}")
    dec = ((f.get("water_series_input") or {}).get("decay")) or {}
    if dec.get("mean_ft") is not None:
        mean, m_exact, m_basis = dec["mean_ft"], True, "published (v0.10.6)"
    else:
        mean, n, _a, _b = ctx.means.as_of(s["_t"])
        m_exact, m_basis = False, f"reconstructed as of issuance, verified lag {M.LAG_D} d assumed ({n} h)"
        if mean is None:
            res["reasons"].append("mean not reconstructable")
    res["facts"].update(mean=mean, mean_exact=m_exact, mean_basis=m_basis)
    replay = ctx.replay.get(s.get("generated_utc"))
    src, rain = F.archived_rain(f, replay)
    hours = sorted({t.replace(minute=0) for t in times})
    covered = [h for h in hours if src and h in rain]
    res["facts"].update(rain_source=src or rain, rain_complete=bool(src) and len(covered) == len(hours),
                        rain_hours=f"{len(covered)}/{len(hours)}")
    if res["reasons"] or not times or any(t not in ctx.p30 for t in times):
        if times and any(t not in ctx.p30 for t in times):
            res["reasons"].append("astronomy not covered")
        ctx._arms[s["blob"]] = res
        return res
    # ---- a4 R1 (+ round 03): validate required numbers, then control replays
    gates = []
    if any((b - a) != dt.timedelta(minutes=30) for a, b in zip(times, times[1:])):
        gates.append("irregular or gapped half-hour grid")
    pub_bay = [p.get("tide_navd88") for _t, p in pts]
    pub_water = [p.get("water_navd88") for _t, p in pts]
    pub_pl = res["P_pluvial"]
    bad = (sum(not _num(x) for x in pub_bay) + sum(not _num(x) for x in pub_water)
           + sum(x is not None and not _num(x) for x in pub_pl) + sum(not _num(ctx.p30[t]) for t in times)
           + (not _num(val)) + (not _num(mean)))
    if bad:
        gates.append(f"invalid required number ({bad})")
        res["gates"] = gates
        ctx._arms[s["blob"]] = res
        return res
    comb = max(abs(w - (b if pl is None else max(b, pl))) for w, b, pl in zip(pub_water, pub_bay, pub_pl))
    res["facts"]["control_combined_max_diff_ft"] = round(comb, 5)
    if comb > TANK_TOL_FT:
        gates.append(f"control combined output mismatch ({comb:.4f} ft)")
    if dec:
        ctrl_surge = lambda t: decay(dec["surge_obs_ft"], A.parse_utc(dec["observation_utc"]), dec["mean_ft"], t,
                                     dec.get("tau_h") or TAU_H)
        rule = "decay (published metadata)"
    else:
        const = control_constant(f, ctx.p30, pts)
        ctrl_surge = (lambda t: const) if const is not None else None
        rule = "constant (published reading or matched tide surge)"
    if ctrl_surge is None:
        gates.append("no published control rule to replay")
    else:
        d = max(abs(ctx.p30[t] + NAVD + ctrl_surge(t) - b) for t, b in zip(times, pub_bay))
        res["facts"].update(control_rule=rule, control_bay_max_diff_ft=round(d, 5))
        if d > BAY_TOL_FT:
            gates.append(f"control bay replay mismatch ({d:.4f} ft)")
    if src:
        rain, n_null, n_bad = clean_rain(rain)
        res["facts"].update(rain_null_hours=n_null, rain_invalid_values=n_bad)
        if n_bad:
            gates.append(f"invalid archived rain value ({n_bad})")
            res["gates"] = gates
            ctx._arms[s["blob"]] = res
            return res
        rates_c = [rain.get(t.replace(minute=0), 0.0) for t in times]
        tc = ctx.tank.simulate_pluvial_series(times, pub_bay, rates_c)
        pres = sum((x is None) != (y is None) for x, y in zip(tc, pub_pl))
        diffs = [abs(x - y) for x, y in zip(tc, pub_pl) if x is not None and y is not None]
        res["facts"].update(control_tank_presence_mismatches=pres,
                            control_tank_max_diff_ft=round(max(diffs), 5) if diffs else 0.0)
        if pres or (diffs and max(diffs) > TANK_TOL_FT):
            gates.append(f"control tank replay mismatch ({pres} presence, max {max(diffs) if diffs else 0:.4f} ft)")
        fp = ctx.tank_fingerprint(s)
        res["facts"]["tank_fingerprint"] = fp
        if fp not in SUPPORTED_TANKS:
            gates.append("unsupported tank implementation")
        res["rain_by_hour"] = rain
    res["gates"] = gates
    astro = [ctx.p30[t] + NAVD for t in times]
    bay_k = [a + val for a in astro]
    bay_d = [a + decay(val, t_r, mean, t) for a, t in zip(astro, times)]
    res.update(bay_K=bay_k, bay_D=bay_d, T=list(bay_d))
    if src:
        rates = [rain.get(t.replace(minute=0), 0.0) for t in times]    # cleaned; missing hours gate EXACT below
        res["rates"] = rates
        pk = ctx.tank.simulate_pluvial_series(times, bay_k, rates)
        pd_ = ctx.tank.simulate_pluvial_series(times, bay_d, rates)
        pl = ctx.tank.simulate_pluvial_series(times, [FIXED_LOW_BAY] * len(times), rates)
        mx = lambda b, p: [x if y is None else max(x, y) for x, y in zip(b, p)]
        res.update(K=mx(bay_k, pk), D=mx(bay_d, pd_), L=mx(bay_d, pl))
    else:
        res.update(K=bay_k, D=bay_d, L=None)
    if dec:
        pub_bay = [p["tide_navd88"] for _t, p in pts]
        res["facts"]["decay_vs_published_bay_max_ft"] = round(max(abs(x - y) for x, y in zip(bay_d, pub_bay)), 4)
    ctx._arms[s["blob"]] = res
    return res


def pair_class(res, o, t_o):
    if res["reasons"]:
        return "EXCLUDED", "; ".join(res["reasons"])
    if res.get("gates"):
        return "EXCLUDED", "admission gate: " + "; ".join(res["gates"])
    fa = res["facts"]
    if fa["rain_source"] in ("replay record qpf_hourly", "outlook hourly rain (nws_grid)"):
        rain = res.get("rain_by_hour") or {}
        needed = sorted({t.replace(minute=0) for t in res["times"] if t <= t_o})
        missing = [h for h in needed if h not in rain]
        if not fa["reading_exact"]:
            return "EXCLUDED", fa["reading_basis"]
        if not missing and fa["mean_exact"]:
            return "EXACT", None
        if missing and missing != needed[:1]:
            return "EXCLUDED", f"rain not archived for {len(missing)} antecedent hours"
        return "NEAR", ("mean reconstructed; " if not fa["mean_exact"] else "") + (
            "first core hour's rain not archived" if missing else "")
    pub_pluv = interp(res["times"], [0.0 if x is None else 1.0 for x in res["P_pluvial"]], t_o)
    if o["dry"] and fa["reading_exact"] and (pub_pluv or 0.0) == 0.0:
        return "APPROX-TIDE", "rain not archived; dry window; no published pluvial water"
    return "EXCLUDED", "rain not archived and not a dry tidal window" if fa["reading_exact"] else fa["reading_basis"]


def build_pairs(ctx, observations):
    """observations: normalization-manifest entries (see normalization.py)."""
    pairs = []
    for o in observations:
        t_o = A.parse_utc(o["time_utc"]) if isinstance(o["time_utc"], str) else o["time_utc"]
        win = o.get("time_window_utc")
        w0, w1 = ((A.parse_utc(win[0]), A.parse_utc(win[1])) if win else (None, None))
        t_ref = w0 + (w1 - w0) / 2 if win else t_o
        t_last = w1 if win else t_o
        cands = [s for s in ctx.issuances if s["_t"] < (w0 or t_o) and (t_ref - s["_t"]) <= dt.timedelta(hours=30)]
        for lo, hi in LEAD_BINS:
            inbin = [s for s in cands if dt.timedelta(hours=lo) < (t_ref - s["_t"]) <= dt.timedelta(hours=hi)]
            chosen = None
            for s in sorted(inbin, key=lambda s: s["_t"], reverse=True):
                res = arms(ctx, s)
                if res["times"] and res["times"][0] <= (w0 or t_o) and t_last <= res["times"][-1]:
                    chosen = (s, res)
                    break
            if chosen is None:
                continue
            s, res = chosen
            cls, why = pair_class(res, o, t_last)
            rec = {"obs_row": o["row"], "obs_time": t_ref, "obs_window": [w0, w1] if win else None,
                   "landmark": o["landmark"], "elevation": o["elevation"], "level_type": o["level_type"],
                   "point": o.get("point"), "lo": o.get("lo"), "hi": o.get("hi"),
                   "point_is_midpoint": bool(o.get("point_is_midpoint")), "method": o["method"],
                   "primary": o.get("primary", True), "dry": o["dry"],
                   "issuance": s["_t"], "issuance_basis": s["_basis"], "model_version": s["model_version"],
                   "blob": s["blob"], "lead_h": round((t_ref - s["_t"]).total_seconds() / 3600, 2),
                   "lead_bin": f"({lo},{hi}]", "class": cls, "class_note": why}
            for arm in ARMS:
                series = res.get(arm)
                rec[arm] = None if series is None else interp(res["times"], series, t_ref)
                rec[arm + "_range"] = (None if series is None or not win else window_range(res["times"], series, w0, w1))
                if rec[arm] is None or (win and rec[arm + "_range"] is None):
                    rec[arm] = rec[arm + "_range"] = None
                    rec[arm + "_why"] = ("published line invalid or missing at the observation time" if arm == "P"
                                         else "arm not computed: " + (why or "rain not archived") if series is None
                                         else "arm invalid or missing at the observation time")
            rates = res.get("rates")
            if rates:
                w = [r for t, r in zip(res["times"], rates) if dt.timedelta(0) <= (t_ref - t) <= dt.timedelta(hours=6)]
                rec["wet"] = bool(w and max(w) >= 0.25)
            else:
                rec["wet"] = None
            rec["published_pluvial_at_obs"] = interp(res["times"], res["P_pluvial"], t_ref)
            if rec["published_pluvial_at_obs"] is not None:
                rec["wet"] = True
            pairs.append(rec)
    return pairs


def observed_wet(p):
    """Declared rule (protocol 4.6): POINT above the elevation = wet, at/below =
    dry. Brackets (Amendment 2): wet if lo > elevation, dry if hi <= elevation,
    otherwise UNKNOWN (reported, never dropped). UPPER: dry if hi <= elevation;
    LOWER: wet if lo >= elevation."""
    e, t = p["elevation"], p["level_type"]
    if t == "POINT":
        return p["point"] > e
    if t == "INTERVAL":
        return True if p["lo"] > e else False if p["hi"] <= e else None
    if t == "UPPER":
        return False if p["hi"] <= e else None
    return True if p["lo"] >= e else None


def score(p, arm):
    """Per-pair scores for one arm (ft): point error (POINT), interval error
    (distance from the forecast, or its range over a time window, to [lo, hi];
    0 inside), midpoint error (INTERVAL, sensitivity only), bound
    exceedance/deficit, local depth error (inches, POINT), threshold cell."""
    f = p.get(arm)
    if not _num(f):
        return None
    e = p["elevation"]
    need = {"POINT": ("point",), "INTERVAL": ("point", "lo", "hi"), "UPPER": ("hi",), "LOWER": ("lo",)}.get(p["level_type"], ())
    if not _num(e) or any(not _num(p.get(k)) for k in need):
        return None
    rng = p.get(arm + "_range") or (f, f)
    if not all(_num(x) for x in rng):
        return None
    out = {"forecast": f, "forecast_wet": f > e, "observed_wet": observed_wet(p)}
    lo, hi = p.get("lo"), p.get("hi")
    if p["level_type"] == "POINT":
        out["error"] = f - p["point"]
        out["depth_error_in"] = (max(0.0, f - e) - max(0.0, p["point"] - e)) * 12
    if p["level_type"] == "INTERVAL":
        out["midpoint_error"] = f - p["point"]
    if p["level_type"] in ("POINT", "INTERVAL") and lo is not None and hi is not None:
        out["interval_error"] = 0.0 if (rng[1] >= lo and rng[0] <= hi) else (lo - rng[1] if rng[1] < lo else rng[0] - hi)
    if p["level_type"] == "UPPER":
        out["exceedance"] = max(0.0, rng[0] - hi)
    if p["level_type"] == "LOWER":
        out["deficit"] = max(0.0, lo - rng[1])
    return out


def cell(sc):
    if sc["observed_wet"] is None:
        return "unknown (bracket straddles the landmark)"
    if sc["observed_wet"]:
        return "hit" if sc["forecast_wet"] else "miss"
    return "false alarm" if sc["forecast_wet"] else "correct negative"


def _bootstrap(per_event, n=2000, seed=20260924):
    if len(per_event) < 2:
        return None
    rnd, keys, vals = random.Random(seed), list(per_event), []
    for _ in range(n):
        s = [per_event[rnd.choice(keys)] for _k in keys]
        vals.append(sum(s) / len(s))
    vals.sort()
    return [round(vals[int(0.05 * n)], 4), round(vals[int(0.95 * n)], 4)]


def summarize(pairs, arm, events_of, primary_only=True):
    rows = [(p, score(p, arm)) for p in pairs if (p["primary"] or not primary_only)]
    unscorable = Counter(p.get(arm + "_why") or "observation or forecast value not a finite number"
                         for p, sc in rows if sc is None)
    rows = [(p, sc) for p, sc in rows if sc is not None]
    pts = [(p, sc) for p, sc in rows if "error" in sc]
    out = {"pairs": len(rows), "point_pairs": len(pts)}
    if pts:
        errs = [sc["error"] for _p, sc in pts]
        per_ev = defaultdict(list)
        for p, sc in pts:
            per_ev[events_of[p["obs_row"]]].append(abs(sc["error"]))
        ev_mae = {k: sum(v) / len(v) for k, v in per_ev.items()}
        dep = [sc["depth_error_in"] for _p, sc in pts]
        out.update(mae_ft=round(sum(map(abs, errs)) / len(errs), 4), bias_ft=round(sum(errs) / len(errs), 4),
                   large_rate=round(sum(abs(x) > 0.25 for x in errs) / len(errs), 4), events=len(ev_mae),
                   event_weighted_mae_ft=round(sum(ev_mae.values()) / len(ev_mae), 4), event_mae_ci90=_bootstrap(ev_mae),
                   depth_mae_in=round(sum(map(abs, dep)) / len(dep), 2), depth_bias_in=round(sum(dep) / len(dep), 2))
    iv = [sc["interval_error"] for _p, sc in rows if "interval_error" in sc]
    out["interval"] = {"n": len(iv), "inside": sum(x == 0 for x in iv),
                       "mean_distance_ft": round(sum(iv) / len(iv), 4) if iv else None}
    mid = [sc["midpoint_error"] for _p, sc in rows if "midpoint_error" in sc]
    out["bracket_midpoint_sensitivity"] = {"n": len(mid), "mae_ft": round(sum(map(abs, mid)) / len(mid), 4) if mid else None}
    ub = [sc["exceedance"] for _p, sc in rows if "exceedance" in sc]
    lb = [sc["deficit"] for _p, sc in rows if "deficit" in sc]
    out["upper_bound"] = {"n": len(ub), "false_wet": sum(x > 0 for x in ub), "max_exceedance_ft": round(max(ub), 3) if ub else None}
    out["lower_bound"] = {"n": len(lb), "missed_wet": sum(x > 0 for x in lb), "max_deficit_ft": round(max(lb), 3) if lb else None}
    out["threshold"] = dict(Counter(cell(sc) for _p, sc in rows))
    out["unscorable"] = dict(unscorable)
    return out


def compare(pairs, a, b, events_of):
    """Paired event-level comparison of two arms on PRIMARY POINT pairs (a minus b)."""
    per_ev = defaultdict(lambda: [[], []])
    for p in pairs:
        if not p["primary"]:
            continue
        sa, sb = score(p, a), score(p, b)
        if sa is None or sb is None or "error" not in sa:
            continue
        ev = events_of[p["obs_row"]]
        per_ev[ev][0].append(abs(sa["error"])); per_ev[ev][1].append(abs(sb["error"]))
    diff = {k: sum(v[0]) / len(v[0]) - sum(v[1]) / len(v[1]) for k, v in per_ev.items()}
    if not diff:
        return {"events": 0}
    return {"events": len(diff), "event_mean_mae_diff_ft": round(sum(diff.values()) / len(diff), 4),
            "events_won_by_first": sum(d < 0 for d in diff.values()), "events_won_by_second": sum(d > 0 for d in diff.values()),
            "ties": sum(d == 0 for d in diff.values()), "ci90": _bootstrap(diff)}


def verdict(cmp, events_needed=5):
    n = cmp.get("events", 0)
    if n < 3:
        return "NOT YET EVALUABLE"
    if n < events_needed:
        return "DESCRIPTIVE (3-4 events)"
    ci = cmp.get("ci90")
    if cmp["event_mean_mae_diff_ft"] < 0 and cmp["events_won_by_first"] * 2 > n and ci and ci[1] < 0:
        return "FIRST BETTER"
    if cmp["event_mean_mae_diff_ft"] > 0 and cmp["events_won_by_second"] * 2 > n and ci and ci[0] > 0:
        return "FIRST WORSE"
    return "INCONCLUSIVE"


def evaluate(ctx, observations):
    pairs = build_pairs(ctx, observations)
    times = sorted({p["obs_time"] for p in pairs})
    ev_idx = dict(zip(times, O.events(times)))
    events_of = {p["obs_row"]: ev_idx[p["obs_time"]] for p in pairs}
    prim = [p for p in pairs if p["primary"]]
    rep = {"pairs": len(pairs),
           "populations": {"total_pairs": len(pairs), "primary_pairs": len(prim),
                           "sensitivity_only_pairs": len(pairs) - len(prim),
                           "sensitivity_only_rows": sorted({p["obs_row"] for p in pairs if not p["primary"]}),
                           "primary_class_counts": dict(Counter(p["class"] for p in prim)),
                           "sensitivity_class_counts": dict(Counter(p["class"] for p in pairs if not p["primary"]))},
           "class_counts": dict(Counter(p["class"] for p in pairs)),
           "exclusion_reasons": dict(Counter(p["class_note"] for p in pairs if p["class"] == "EXCLUDED")),
           "events_total": len(set(events_of.values()))}
    rep["B0_published_by_version"] = {}
    for v in sorted({p["model_version"] or "pre-v0.10.1" for p in pairs}):
        sub = [p for p in pairs if (p["model_version"] or "pre-v0.10.1") == v]
        rep["B0_published_by_version"][v] = {lb: summarize([p for p in sub if p["lead_bin"] == lb], "P", events_of)
                                             for lb in [f"({a},{b}]" for a, b in LEAD_BINS]}
    rep["sensitivity_all_rows"] = {cls: summarize([p for p in pairs if p["class"] == cls], "D", events_of, primary_only=False)
                                   for cls in ("EXACT", "NEAR", "APPROX-TIDE")}
    rep["published_all_rows_sensitivity"] = summarize(pairs, "P", events_of, primary_only=False)
    for cls in ("EXACT", "NEAR", "APPROX-TIDE"):
        sub = [p for p in pairs if p["class"] == cls]
        block = {"pairs": len(sub), "events": len({events_of[p["obs_row"]] for p in sub})}
        for lb in [f"({a},{b}]" for a, b in LEAD_BINS] + ["all leads"]:
            ss = sub if lb == "all leads" else [p for p in sub if p["lead_bin"] == lb]
            block[lb] = {arm: summarize(ss, arm, events_of) for arm in ("K", "D")}
            block[lb]["B1_D_vs_K"] = compare(ss, "D", "K", events_of)
            if cls in ("EXACT", "NEAR"):
                wet = [p for p in ss if p.get("wet")]
                block[lb]["B2_wet_pairs"] = len(wet)
                block[lb]["B2_D_vs_T"] = compare(wet, "D", "T", events_of)
                block[lb]["B2_D_vs_L"] = compare(wet, "D", "L", events_of)
        rep[f"class_{cls}"] = block
    ex = rep.get("class_EXACT", {}).get("all leads", {})
    rep["verdicts"] = {
        "B1 decay vs persisted (EXACT only)": verdict(ex.get("B1_D_vs_K", {})),
        "B2 decay vs tide-only (EXACT wet only)": verdict(ex.get("B2_D_vs_T", {})),
        "B2 decay vs fixed-low-bay tank (EXACT wet only)": verdict(ex.get("B2_D_vs_L", {})),
        "note": "NEAR and APPROX-TIDE blocks are diagnostics and never produce a verdict; B0 is descriptive"}
    return rep, pairs
