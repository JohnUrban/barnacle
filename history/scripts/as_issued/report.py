"""Descriptive per-event tables from the Study B pairs (published line B0) and
the published conditional burst scenarios beside observed peaks."""
from __future__ import annotations

import datetime as dt
from collections import defaultdict

from . import archive as A
from . import obs as O
from . import street as S


def per_event(pairs):
    times = sorted({p["obs_time"] for p in pairs})
    ev = dict(zip(times, O.events(times)))
    by = defaultdict(list)
    for p in pairs:
        by[ev[p["obs_time"]]].append(p)
    rows = []
    for k in sorted(by):
        ps = by[k]
        obs_rows = {p["obs_row"]: p for p in ps}
        dry = all(p["dry"] for p in obs_rows.values())
        pts = [p for p in obs_rows.values() if p["level_type"] == "POINT" and p["evidence"] != "RECONSTRUCTION"]
        peak = max((p["level"] for p in pts), default=None)
        row = {"event": k, "first_obs": min(p["obs_time"] for p in ps), "observations": len(obs_rows),
               "weather": "dry tidal" if dry else "rain", "observed_peak_navd88": round(peak, 3) if peak else None,
               "versions": sorted({p["model_version"] or "pre-v0.10.1" for p in ps}), "leads": {}}
        for lb in [f"({a},{b}]" for a, b in S.LEAD_BINS]:
            sub = [p for p in ps if p["lead_bin"] == lb]
            errs = [S.score(p, "P")["error"] for p in sub if p["level_type"] == "POINT" and p["evidence"] != "RECONSTRUCTION"
                    and S.score(p, "P") is not None]
            wet_pub = sum(1 for p in sub if p["published_pluvial_at_obs"] is not None)
            cells = defaultdict(int)
            for p in sub:
                sc = S.score(p, "P")
                if sc and sc["observed_wet"] is not None:
                    cells[("hit" if sc["forecast_wet"] else "miss") if sc["observed_wet"] else
                          ("false alarm" if sc["forecast_wet"] else "correct negative")] += 1
            row["leads"][lb] = {"pairs": len(sub), "mae_ft": round(sum(map(abs, errs)) / len(errs), 3) if errs else None,
                                "bias_ft": round(sum(errs) / len(errs), 3) if errs else None,
                                "published_pluvial_at_obs": wet_pub, "threshold": dict(cells)}
        rows.append(row)
    return rows


def conditional_scenarios(ctx, event_rows):
    """For rain events: the last issuance before the first observation, its
    published pluvial_risk (conditional) fields, beside the observed peak."""
    out = []
    for e in event_rows:
        if e["weather"] != "rain":
            continue
        t = e["first_obs"]
        before = [s for s in ctx.issuances if s["_t"] < t]
        if not before:
            continue
        s = before[-1]
        f = ctx.forecast(s)
        pr = f.get("pluvial_risk") or {}
        out.append({"event_first_obs": t, "issuance": s["_t"], "lead_h": round((t - s["_t"]).total_seconds() / 3600, 2),
                    "model_version": s["model_version"], "observed_peak_navd88": e["observed_peak_navd88"],
                    "level": pr.get("level"), "day_max_level": pr.get("day_max_level"),
                    "burst_est_in_hr": pr.get("burst_est_in_hr"), "day_max_burst_est_in_hr": pr.get("day_max_burst_est_in_hr"),
                    "potential_low_tide_navd88": pr.get("potential_low_tide_navd88"),
                    "day_max_potential_low_tide_navd88": pr.get("day_max_potential_low_tide_navd88"),
                    "flood_alerts": [a.get("event") for a in (pr.get("nws_flood_alerts") or [])],
                    "note": "conditional scenario (if a burst occurs), not an hourly forecast or a probability"})
    return out
