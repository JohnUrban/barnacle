"""Descriptive per-event tables from the Study B pairs (published line B0) and
the published conditional burst scenarios beside ESTABLISHED peaks
(audit 2026-09-24-a4 R5; Amendment 2).

- "highest sampled water" = the largest primary POINT/bracket level logged in
  the event; it is NOT the event peak.
- the event peak is taken only from the normalization manifest's EVENT_PEAKS
  (primary records: tape peak, photo bracket, or a lower bound when the
  observer missed the crest).
- a scenario is "above"/"below" the peak only when it lies outside the
  bracket; with only a lower bound, "below" is decidable, "above" is not.
- misses are reported per event and lead as threshold cells, signed level
  error and local-depth error, separately.
"""
from __future__ import annotations

from collections import Counter, defaultdict

from . import obs as O
from . import street as S


def per_event(pairs, event_peaks):
    times = sorted({p["obs_time"] for p in pairs})
    ev = dict(zip(times, O.events(times)))
    by = defaultdict(list)
    for p in pairs:
        by[ev[p["obs_time"]]].append(p)
    rows = []
    for k in sorted(by):
        ps = by[k]
        obs_rows = {p["obs_row"]: p for p in ps}
        prim = [p for p in obs_rows.values() if p["primary"]]
        dry = all(p["dry"] for p in obs_rows.values())
        sampled = [p["point"] if p["level_type"] == "POINT" else p["lo"] for p in prim
                   if p["level_type"] in ("POINT", "INTERVAL", "LOWER")]
        day = min(p["obs_time"] for p in ps).astimezone(O.NY).strftime("%Y-%m-%d")
        pk = event_peaks.get(day)
        row = {"event": k, "first_obs": min(p["obs_time"] for p in ps), "observations": len(obs_rows),
               "primary_observations": len(prim), "weather": "dry tidal" if dry else "rain",
               "highest_sampled_navd88": round(max(sampled), 3) if sampled else None,
               "established_peak": ({"lo": round(pk["lo"], 3) if pk["lo"] is not None else None,
                                     "hi": round(pk["hi"], 3) if pk.get("hi") is not None else None, "basis": pk["basis"]}
                                    if pk else None),
               "versions": sorted({p["model_version"] or "pre-v0.10.1" for p in ps}), "leads": {}}
        for lb in [f"({a},{b}]" for a, b in S.LEAD_BINS]:
            sub = [p for p in ps if p["lead_bin"] == lb and p["primary"]]
            scs = [(p, S.score(p, "P")) for p in sub]
            scs = [(p, sc) for p, sc in scs if sc is not None]
            errs = [sc["error"] for _p, sc in scs if "error" in sc]
            dep = [sc["depth_error_in"] for _p, sc in scs if "depth_error_in" in sc]
            iv = [sc["interval_error"] for _p, sc in scs if "interval_error" in sc]
            row["leads"][lb] = {
                "pairs": len(scs), "point_pairs": len(errs),
                "level_bias_ft": round(sum(errs) / len(errs), 3) if errs else None,
                "level_mae_ft": round(sum(map(abs, errs)) / len(errs), 3) if errs else None,
                "depth_bias_in": round(sum(dep) / len(dep), 1) if dep else None,
                "interval_inside": f"{sum(x == 0 for x in iv)}/{len(iv)}" if iv else None,
                "published_pluvial_at_obs": sum(1 for p, _sc in scs if p["published_pluvial_at_obs"] is not None),
                "threshold": dict(Counter(S.cell(sc) for _p, sc in scs))}
        rows.append(row)
    return rows


def _vs_peak(x, pk):
    if x is None or pk is None:
        return "not comparable"
    lo, hi = pk.get("lo"), pk.get("hi")
    if lo is not None and x < lo:
        return "below the established peak"
    if hi is not None and x > hi:
        return "above the established peak"
    if hi is None:
        return "indeterminate (peak bounded below only)"
    return "within the established bracket"


def conditional_scenarios(ctx, event_rows):
    """For rain events: the last issuance before the first observation and its
    published pluvial_risk (conditional) fields beside the established peak."""
    out = []
    for e in event_rows:
        if e["weather"] != "rain":
            continue
        t = e["first_obs"]
        before = [s for s in ctx.issuances if s["_t"] < t]
        if not before:
            continue
        s = before[-1]
        pr = ctx.forecast(s).get("pluvial_risk") or {}
        dm = pr.get("day_max_potential_low_tide_navd88")
        out.append({"event_first_obs": t, "issuance": s["_t"], "lead_h": round((t - s["_t"]).total_seconds() / 3600, 2),
                    "model_version": s["model_version"], "established_peak": e["established_peak"],
                    "highest_sampled_navd88": e["highest_sampled_navd88"],
                    "level": pr.get("level"), "day_max_level": pr.get("day_max_level"),
                    "burst_est_in_hr": pr.get("burst_est_in_hr"), "day_max_burst_est_in_hr": pr.get("day_max_burst_est_in_hr"),
                    "potential_low_tide_navd88": pr.get("potential_low_tide_navd88"),
                    "day_max_potential_low_tide_navd88": dm,
                    "day_max_vs_peak": _vs_peak(dm, e["established_peak"]),
                    "flood_alerts": [a.get("event") for a in (pr.get("nws_flood_alerts") or [])],
                    "note": "conditional scenario (if a burst occurs), not an hourly forecast or a probability"})
    return out
