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
TAU_H = 36.0
FIXED_LOW_BAY = 2.50
LEAD_BINS = ((0, 6), (6, 12), (12, 24), (24, 30))
ARMS = ("P", "K", "D", "T", "L")


def issuance_time(s):
    if s.get("generated_utc"):
        return A.parse_utc(s["generated_utc"]), "generated_utc"
    return dt.datetime.fromisoformat(s["commit_time"]).astimezone(UTC), "commit time (no generation stamp)"


def interp(times, values, t):
    """Linear between the bracketing half-hour points; None outside or at a gap."""
    if not times or t < times[0] or t > times[-1]:
        return None
    for i in range(1, len(times)):
        if times[i] >= t:
            a, b = values[i - 1], values[i]
            if a is None or b is None:
                return None
            span = (times[i] - times[i - 1]).total_seconds()
            return a + (b - a) * ((t - times[i - 1]).total_seconds() / span if span else 0.0)
    return values[0] if times[0] == t else None


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


def arms(ctx, s):
    """Half-hourly arm series and the input-class facts for one issuance."""
    if s["blob"] in ctx._arms:
        return ctx._arms[s["blob"]]
    f = ctx.forecast(s)
    pts = [(t, p) for t, p in F.core_points(f) if p.get("tide_navd88") is not None]
    times = [t for t, _p in pts]
    res = {"times": times, "P": [p.get("water_navd88") for _t, p in pts],
           "P_pluvial": [p.get("pluvial_navd88") for _t, p in pts], "reasons": [], "facts": {}}
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
    astro = [ctx.p30[t] + NAVD for t in times]
    bay_k = [a + val for a in astro]
    bay_d = [a + decay(val, t_r, mean, t) for a, t in zip(astro, times)]
    res.update(bay_K=bay_k, bay_D=bay_d, T=list(bay_d))
    if src:
        rates = [rain.get(t.replace(minute=0), 0.0) for t in times]
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
    fa = res["facts"]
    if fa["rain_source"] in ("replay record qpf_hourly", "outlook hourly rain (nws_grid)"):
        if fa["reading_exact"] and fa["mean_exact"] and fa["rain_complete"]:
            return "EXACT", None
        if fa["reading_exact"]:
            return "NEAR", ("mean reconstructed; " if not fa["mean_exact"] else "") + (
                "" if fa["rain_complete"] else f"rain hours {fa['rain_hours']}")
        return "EXCLUDED", fa["reading_basis"]
    pub_pluv = interp(res["times"], [0.0 if x is None else 1.0 for x in res["P_pluvial"]], t_o)
    if o["dry"] and fa["reading_exact"] and (pub_pluv or 0.0) == 0.0:
        return "APPROX-TIDE", "rain not archived; dry window; no published pluvial water"
    return "EXCLUDED", "rain not archived and not a dry tidal window" if fa["reading_exact"] else fa["reading_basis"]


def build_pairs(ctx, observations):
    pairs = []
    for o in observations:
        if not o["eligible"]:
            continue
        t_o = o["time_utc"]
        cands = [s for s in ctx.issuances if s["_t"] < t_o and (t_o - s["_t"]) <= dt.timedelta(hours=30)]
        for lo, hi in LEAD_BINS:
            inbin = [s for s in cands if dt.timedelta(hours=lo) < (t_o - s["_t"]) <= dt.timedelta(hours=hi)]
            chosen = None
            for s in sorted(inbin, key=lambda s: s["_t"], reverse=True):
                res = arms(ctx, s)
                if res["times"] and res["times"][0] <= t_o <= res["times"][-1]:
                    chosen = (s, res)
                    break
            if chosen is None:
                continue
            s, res = chosen
            cls, why = pair_class(res, o, t_o)
            rec = {"obs_row": o["row"], "obs_time": t_o, "landmark": o["landmark"], "elevation": o["elevation"],
                   "level_type": o["level_type"], "level": o["level_navd88"], "evidence": o["evidence"], "dry": o["dry"],
                   "issuance": s["_t"], "issuance_basis": s["_basis"], "model_version": s["model_version"],
                   "blob": s["blob"], "lead_h": round((t_o - s["_t"]).total_seconds() / 3600, 2),
                   "lead_bin": f"({lo},{hi}]", "class": cls, "class_note": why}
            for arm in ARMS:
                series = res.get(arm)
                rec[arm] = None if series is None else interp(res["times"], series, t_o)
            rates = res.get("rates")
            if rates:
                w = [r for t, r in zip(res["times"], rates) if dt.timedelta(0) <= (t_o - t) <= dt.timedelta(hours=6)]
                rec["wet"] = bool(w and max(w) >= 0.25)
            else:
                rec["wet"] = None
            rec["published_pluvial_at_obs"] = interp(res["times"], res["P_pluvial"], t_o)
            if rec["published_pluvial_at_obs"] is not None:
                rec["wet"] = True
            pairs.append(rec)
    return pairs


def score(p, arm):
    """Per-pair scores for one arm: error (POINT), exceedance/deficit (bounds), threshold cell."""
    f = p.get(arm)
    if f is None:
        return None
    e = p["elevation"]
    out = {"forecast": f, "forecast_wet": f > e}
    if p["level_type"] == "POINT":
        out["error"] = f - p["level"]
        out["observed_wet"] = None if abs(p["level"] - e) < 1e-9 else p["level"] > e
    elif p["level_type"] == "UPPER":
        out["exceedance"] = max(0.0, f - e)
        out["observed_wet"] = False
    else:
        out["deficit"] = max(0.0, e - f)
        out["observed_wet"] = True
    return out


def _bootstrap(per_event, n=2000, seed=20260924):
    if len(per_event) < 2:
        return None
    rnd, keys, vals = random.Random(seed), list(per_event), []
    for _ in range(n):
        s = [per_event[rnd.choice(keys)] for _k in keys]
        vals.append(sum(s) / len(s))
    vals.sort()
    return [round(vals[int(0.05 * n)], 4), round(vals[int(0.95 * n)], 4)]


def summarize(pairs, arm, events_of):
    rows = [(p, score(p, arm)) for p in pairs]
    rows = [(p, sc) for p, sc in rows if sc is not None]
    pts = [(p, sc) for p, sc in rows if "error" in sc and p["evidence"] != "RECONSTRUCTION"]
    out = {"pairs": len(rows), "point_pairs": len(pts)}
    if pts:
        errs = [sc["error"] for _p, sc in pts]
        per_ev = defaultdict(list)
        for p, sc in pts:
            per_ev[events_of[p["obs_row"]]].append(abs(sc["error"]))
        ev_mae = {k: sum(v) / len(v) for k, v in per_ev.items()}
        out.update(mae_ft=round(sum(map(abs, errs)) / len(errs), 4), bias_ft=round(sum(errs) / len(errs), 4),
                   large_rate=round(sum(abs(x) > 0.25 for x in errs) / len(errs), 4), events=len(ev_mae),
                   event_weighted_mae_ft=round(sum(ev_mae.values()) / len(ev_mae), 4),
                   event_mae_ci90=_bootstrap(ev_mae))
    ub = [sc["exceedance"] for _p, sc in rows if "exceedance" in sc]
    lb = [sc["deficit"] for _p, sc in rows if "deficit" in sc]
    out["upper_bound"] = {"n": len(ub), "false_wet": sum(x > 0 for x in ub), "max_exceedance_ft": round(max(ub), 3) if ub else None}
    out["lower_bound"] = {"n": len(lb), "missed_wet": sum(x > 0 for x in lb), "max_deficit_ft": round(max(lb), 3) if lb else None}
    cell = Counter()
    for _p, sc in rows:
        if sc["observed_wet"] is None:
            continue
        cell[("hit" if sc["forecast_wet"] else "miss") if sc["observed_wet"] else
             ("false alarm" if sc["forecast_wet"] else "correct negative")] += 1
    out["threshold"] = dict(cell)
    return out


def compare(pairs, a, b, events_of):
    """Paired event-level comparison of two arms on POINT pairs (a minus b)."""
    per_ev = defaultdict(lambda: [[], []])
    for p in pairs:
        sa, sb = score(p, a), score(p, b)
        if sa is None or sb is None or "error" not in sa or p["evidence"] == "RECONSTRUCTION":
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
    rep = {"pairs": len(pairs), "class_counts": dict(Counter(p["class"] for p in pairs)),
           "exclusion_reasons": dict(Counter(p["class_note"] for p in pairs if p["class"] == "EXCLUDED")),
           "events_total": len(set(events_of.values()))}
    rep["B0_published_by_version"] = {}
    for v in sorted({p["model_version"] or "pre-v0.10.1" for p in pairs}):
        sub = [p for p in pairs if (p["model_version"] or "pre-v0.10.1") == v]
        rep["B0_published_by_version"][v] = {lb: summarize([p for p in sub if p["lead_bin"] == lb], "P", events_of)
                                             for lb in [f"({a},{b}]" for a, b in LEAD_BINS]}
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
