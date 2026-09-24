#!/usr/bin/env python3
"""Deterministic evaluator for the wind-shadow trial (FROZEN before the first
shadow record; plan history/plans/2026-09-24-wind-term-candidate-plan.md).

Rules (declared here, not chosen after seeing results):
- Opportunities: every UTC hour from the first 'candidate'-id record of the
  manifest's candidate_id. One record per hour: the EARLIEST written record
  whose issuance falls in that hour (retries ignored). Hours with no record,
  or an 'error' record, are counted as missing opportunities.
- Primary comparison scores 'fallback' records too (their candidate equals the
  baseline); a healthy-feed-only table is reported separately.
- Observations: CO-OPS 6-min water_level on the hour minus hourly predictions
  (UTC). An hour is VALID if the value exists and none of its four quality
  flags is set. Maturity: a target is scored only once it is >= 48 h old.
- Leads 6/12/24/30/48 h. Pairs are matched on the same issuance and target;
  every comparison uses the same denominator for both methods.
- Views: all hours; high tide / low tide at TARGET (local extrema of the
  prediction); plug band at TARGET (observed bay 2.5..3.8 ft NAVD88 =
  observed MLLW - 2.82); storm start at ISSUANCE (observed surge >= +1.0 ft).
- Episodes: >= 6 consecutive VALID hours with surge >= +1.0 ft; an episode
  ends after 48 VALID hours below +1.0 ft (invalid hours neither count toward
  nor reset either count); shorter breaks merge. A pair belongs to an episode
  if its TARGET lies in [first, last] >= +1 ft hour. Completed = its 48-h
  quiet tail observed inside the data.
- Endpoint: the first UTC midnight after BOTH 60 days since the first
  opportunity AND >= 5 completed episodes. Final scoring after endpoint + 48 h
  + maturity. Before that the report is labeled INTERIM (descriptive).
- Uncertainty: moving-block bootstrap over 7-day blocks of issuance (1000
  resamples, seed 20260924) for MAE differences; hourly pairs are never
  treated as independent storms.
- PASS requires ALL: candidate MAE < baseline at 24 AND 30 h in all hours AND
  storm starts; plug-band MAE loss <= 0.01 ft at every lead; large-under-
  prediction rate (pred - obs < -1 ft) not higher than baseline at every
  lead; candidate wins a strict majority of eligible episodes (per-episode
  MAE) at 24 and at 30 h. Any required comparison empty -> INCONCLUSIVE.
Run: python3 history/scripts/evaluate_wind_shadow.py [--obs-json FILE] [--now ISO]
"""
from __future__ import annotations

import argparse, datetime as dt, glob, json, math, os, random, sys, urllib.parse, urllib.request
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LEADS = (6, 12, 24, 30, 48)
MATURITY_H = 48
UTC = dt.timezone.utc


def _utc(s):
    t = dt.datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    return t if t.tzinfo else t.replace(tzinfo=UTC)


def hour(t):
    return t.replace(minute=0, second=0, microsecond=0)


def load_records(directory, candidate_id):
    recs = []
    for path in sorted(glob.glob(os.path.join(directory, "*.jsonl"))):
        with open(path, encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                if r.get("candidate_id") == candidate_id:
                    recs.append(r)
    chosen = {}
    for r in sorted(recs, key=lambda r: (r["issuance_utc"], r.get("written_utc", ""))):
        chosen.setdefault(hour(_utc(r["issuance_utc"])), r)          # earliest per hour
    return chosen


def fetch_observations(t0, t1):
    """{hour: (surge_ft, observed_mllw, predicted_mllw, valid)} from CO-OPS (UTC)."""
    out, a = {}, t0
    while a < t1:
        b = min(a + dt.timedelta(days=30), t1)
        def get(product, extra):
            q = {"product": product, "station": "8531680", "begin_date": a.strftime("%Y%m%d %H:%M"),
                 "end_date": b.strftime("%Y%m%d %H:%M"), "datum": "MLLW", "time_zone": "gmt", "units": "english",
                 "format": "json", "application": "barnacle-wind-shadow-eval", **extra}
            req = urllib.request.Request("https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?" + urllib.parse.urlencode(q),
                                         headers={"User-Agent": "barnacle-wind-shadow-eval"})
            return json.load(urllib.request.urlopen(req, timeout=60))
        wl = {_utc(r["t"].replace(" ", "T") + "Z"): r for r in get("water_level", {}).get("data") or []}
        pr = {_utc(r["t"].replace(" ", "T") + "Z"): float(r["v"]) for r in get("predictions", {"interval": "h"}).get("predictions") or []}
        for t, p in pr.items():
            r = wl.get(t)
            if r is None or r.get("v") in (None, ""):
                out[t] = (None, None, p, False)
                continue
            flags = [int(x) for x in str(r.get("f") or "0,0,0,0").split(",") if x.strip().isdigit()]
            v = float(r["v"])
            out[t] = (v - p, v, p, not any(flags))
        a = b
    return out


def episodes(obs, t0, t1):
    hrs, t = [], hour(t0)
    while t <= t1:
        o = obs.get(t)
        hrs.append((t, None if (o is None or not o[3]) else (o[0] >= 1.0)))
        t += dt.timedelta(hours=1)
    eps, i, n = [], 0, len(hrs)
    while i < n:
        run, j, first = 0, i, None
        while j < n and hrs[j][1] is not False and run < 6:          # count valid 'high' hours, skip invalid
            if hrs[j][1]:
                run += 1; first = first or hrs[j][0]
            j += 1
        if run < 6:
            i = max(i + 1, j if j > i else i + 1)
            continue
        last, quiet, k = hrs[j - 1][0], 0, j
        while k < n and quiet < 48:
            if hrs[k][1] is True:
                last, quiet = hrs[k][0], 0
            elif hrs[k][1] is False:
                quiet += 1
            k += 1
        eps.append({"start": first, "end": last, "completed": quiet >= 48})
        i = k
    return eps


def extrema(obs):
    ts = sorted(obs)
    hi, lo = set(), set()
    for a, b, c in zip(ts, ts[1:], ts[2:]):
        pa, pb, pc = obs[a][2], obs[b][2], obs[c][2]
        if pb > pa and pb >= pc:
            hi.add(b)
        if pb < pa and pb <= pc:
            lo.add(b)
    return hi, lo


def pairs(records, obs, now, lead, which):
    """[(issuance, target, candidate, baseline, observed)] for matured, valid targets."""
    out = []
    for t_iss, r in records.items():
        if r.get("status") == "error" or not r.get("leads"):
            continue
        if which == "healthy" and r["status"] != "candidate":
            continue
        start = _utc(r["leads"]["start"])
        tgt = start + dt.timedelta(hours=lead - 1)
        if (now - tgt).total_seconds() / 3600 < MATURITY_H:
            continue
        o = obs.get(tgt)
        if o is None or not o[3]:
            continue
        c, b = r["candidate_surge_ft"][lead - 1], r["baseline_surge_ft"][lead - 1]
        if c is None or b is None:
            continue
        out.append((t_iss, tgt, c, b, o[0]))
    return out


def mae(xs):
    return sum(abs(x) for x in xs) / len(xs) if xs else None


def block_ci(prs, seed=20260924, n=1000):
    if not prs:
        return None
    blocks = defaultdict(list)
    for p in prs:
        blocks[(p[0] - dt.datetime(2026, 1, 1, tzinfo=UTC)).days // 7].append(p)
    keys = sorted(blocks)
    rnd, diffs = random.Random(seed), []
    for _ in range(n):
        sample = [q for _k in keys for q in blocks[rnd.choice(keys)]]
        diffs.append(mae([q[2] - q[4] for q in sample]) - mae([q[3] - q[4] for q in sample]))
    diffs.sort()
    return [round(diffs[int(0.05 * n)], 4), round(diffs[int(0.95 * n)], 4)]


def evaluate(records, obs, now):
    if not records:
        return {"verdict": "INCONCLUSIVE", "reason": "no records"}
    first = min(records)
    hi, lo = extrema(obs)
    eps = episodes(obs, first, now)
    completed = [e for e in eps if e["completed"]]
    endpoint, elapsed_ok = None, first + dt.timedelta(days=60)
    if len(completed) >= 5:
        e5 = sorted(completed, key=lambda e: e["end"])[4]["end"] + dt.timedelta(hours=48)
        cut = max(elapsed_ok, e5)
        endpoint = (cut + dt.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    final = endpoint is not None and now >= endpoint + dt.timedelta(hours=48 + MATURITY_H)
    window = {t: r for t, r in records.items() if endpoint is None or t < endpoint}
    opportunities = int(((min(now, endpoint) if endpoint else now) - first).total_seconds() // 3600)
    rep = {"first_opportunity": first.isoformat(), "endpoint": endpoint.isoformat() if endpoint else None,
           "status": "FINAL" if final else "INTERIM (descriptive only)", "opportunities": opportunities,
           "records": len(window), "missing_or_error": opportunities - sum(1 for r in window.values() if r.get("status") != "error"),
           "fallback_records": sum(1 for r in window.values() if r.get("status") == "fallback"),
           "episodes_completed": len(completed), "episodes_open": len(eps) - len(completed), "leads": {}}
    checks = []
    for lead in LEADS:
        row = {}
        for which in ("primary", "healthy"):
            P = pairs(window, obs, now, lead, which)
            views = {"all": P, "high_tide_target": [p for p in P if p[1] in hi],
                     "low_tide_target": [p for p in P if p[1] in lo],
                     "plug_band_target": [p for p in P if obs[p[1]][1] is not None and 2.5 <= obs[p[1]][1] - 2.82 <= 3.8],
                     "storm_start_issuance": [p for p in P if obs.get(p[0]) and obs[p[0]][3] and obs[p[0]][0] >= 1.0]}
            v = {}
            for name, ps in views.items():
                v[name] = {"n": len(ps), "mae_candidate": mae([p[2] - p[4] for p in ps]),
                           "mae_baseline": mae([p[3] - p[4] for p in ps]),
                           "bias_candidate": (sum(p[2] - p[4] for p in ps) / len(ps)) if ps else None,
                           "large_under_rate_candidate": (sum(1 for p in ps if p[2] - p[4] < -1) / len(ps)) if ps else None,
                           "large_under_rate_baseline": (sum(1 for p in ps if p[3] - p[4] < -1) / len(ps)) if ps else None,
                           "large_abs_rate_candidate": (sum(1 for p in ps if abs(p[2] - p[4]) > 1) / len(ps)) if ps else None,
                           "mae_diff_ci90_7d_blocks": block_ci(ps) if which == "primary" else None}
            ep_wins, ep_n = 0, 0
            for e in eps:
                ps = [p for p in P if e["start"] <= p[1] <= e["end"]]
                if ps:
                    ep_n += 1
                    ep_wins += mae([p[2] - p[4] for p in ps]) < mae([p[3] - p[4] for p in ps])
            v["episodes"] = {"n": ep_n, "candidate_wins": ep_wins}
            row[which] = v
        rep["leads"][lead] = row
        pv = row["primary"]
        def lower(view):
            x = pv[view]
            return None if not x["n"] else x["mae_candidate"] < x["mae_baseline"]
        if lead in (24, 30):
            checks += [("mae all %dh" % lead, lower("all")), ("mae storm %dh" % lead, lower("storm_start_issuance")),
                       ("episode majority %dh" % lead,
                        None if not pv["episodes"]["n"] else pv["episodes"]["candidate_wins"] * 2 > pv["episodes"]["n"])]
        pb = pv["plug_band_target"]
        checks.append(("plug band %dh" % lead, None if not pb["n"] else pb["mae_candidate"] - pb["mae_baseline"] <= 0.01))
        al = pv["all"]
        checks.append(("large under %dh" % lead, None if not al["n"] else al["large_under_rate_candidate"] <= al["large_under_rate_baseline"]))
    rep["checks"] = [{"check": c, "pass": ok} for c, ok in checks]
    if any(ok is None for _c, ok in checks):
        rep["verdict"] = "INCONCLUSIVE"
    else:
        rep["verdict"] = "PASS" if all(ok for _c, ok in checks) else "FAIL"
    if not final:
        rep["verdict"] = f"INTERIM ({rep['verdict']} so far; not a decision)"
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=os.path.join(ROOT, "data", "wind_shadow"))
    ap.add_argument("--manifest", default=os.path.join(ROOT, "models", "wind_shadow", "manifest.json"))
    ap.add_argument("--now", default=None)
    a = ap.parse_args()
    cid = json.load(open(a.manifest))["candidate_id"]
    recs = load_records(a.dir, cid)
    now = _utc(a.now) if a.now else dt.datetime.now(UTC)
    if not recs:
        print(json.dumps({"verdict": "INCONCLUSIVE", "reason": "no records yet"}))
        return 0
    obs = fetch_observations(min(recs) - dt.timedelta(days=1), now)
    print(json.dumps(evaluate(recs, obs, now), indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
