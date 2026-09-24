#!/usr/bin/env python3
"""Deterministic evaluator for the wind-shadow trial, candidate c2 (FROZEN before
the first official record; hash in models/wind_shadow/FREEZE.md). Plan:
history/plans/2026-09-24-wind-term-candidate-plan.md; repairs per audit
2026-09-24-a3 (R1 episodes/endpoint, R2 missingness/QC, R3 comparators,
R5 outcome provenance, R6 identity binding).

DECLARED RULES
Identity: a record is EVALUABLE only if collection == "official", candidate_id,
  manifest_sha256 and runtime_sha256 equal the FREEZE table; every other record
  is excluded and counted by reason. Identities are never pooled.
Opportunities: one per UTC hour slot from the first evaluable record's nominal
  issuance hour; per slot the EARLIEST-written evaluable record. Slot states:
  candidate | fallback (baseline kept) | error (no baseline) | missing.
Observations: CO-OPS 6-min water_level on the hour minus hourly predictions,
  UTC. VALID iff the value is finite and the flag field parses to exactly four
  integers, all 0; otherwise invalid with the reason retained. Raw responses are
  saved with SHA-256 (--save-obs DIR) and can be replayed offline (--obs-json).
Maturity: a target is scored only when >= 48 h old at evaluation time.
Episodes: >= 6 CONSECUTIVE valid hours with surge >= +1.0 ft (an invalid or
  missing hour resets the count); the episode ends with 48 CONSECUTIVE valid
  hours below +1.0 ft (an invalid hour resets that count; a high hour resets it
  and extends the episode); completed_at = the 48th quiet hour. Episode span =
  [first, last] high hour. A pair belongs to an episode if its target is in the span.
Scorable episode (at a lead): >= 6 matured valid pairs in the span AND pairs
  covering >= 50 % of the span's valid hours.
Endpoint: first UTC midnight after max(first opportunity + 60 d, completed_at of
  the 5th completed episode). FINAL once now >= endpoint + 48 h + maturity; before
  that the report is INTERIM (descriptive). The end is never chosen from results.
Coverage: evaluable (candidate or fallback) slots / opportunities in the window
  must be >= 0.80, else INCONCLUSIVE.
Comparisons (matched pairs, same issuance and target, same denominator):
  candidate vs FROZEN baseline (primary); candidate and frozen baseline vs the
  ACTUAL production curve (<= its ~30-h reach; cohorts by production version);
  candidate vs NWS/P-ETSS outlook guidance (by source). Leads > 30 h compare with
  the OFFLINE 48-h extension of the frozen baseline, not a published core curve.
Views: all; high/low tide and plug band (observed bay 2.5..3.8 ft NAVD88) at
  TARGET; storm start (observed surge >= +1.0 ft) at ISSUANCE.
Metrics for every method: n, MAE, bias, rate |err| > 1 ft, rate err < -1 ft;
  per-episode MAEs, wins, equal-episode mean; continuity (hour-to-hour change
  along each issued curve) and revisions (same target, consecutive slots);
  status transitions; 7-day moving-block bootstrap 90 % interval (1000, seed
  20260924) for MAE differences.
Rain-tank sensitivity (descriptive): join the replay archive by issuance; with
  the identical as-issued hourly QPF, run the production tank on baseline vs
  candidate bay (astronomy + surge) over the QPF's coverage; wet = max rate >=
  0.25 in/h within 30 h; wet slots within 12 h form one wet event; fewer than 3
  wet events -> descriptive only, never a rain-skill pass/fail.
PASS requires ALL (else FAIL; any required input empty -> INCONCLUSIVE):
  lower MAE than frozen baseline at 24 AND 30 h in all hours AND storm starts;
  plug-band MAE loss <= 0.01 ft at every lead; large-under-prediction rate not
  higher than baseline at every lead; strict majority of SCORABLE episodes won
  at 24 and 30 h with >= 5 scorable episodes at each; coverage >= 0.80.
"""
from __future__ import annotations

import argparse, datetime as dt, glob, hashlib, json, math, os, random, re, sys, urllib.parse, urllib.request
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LEADS = (6, 12, 24, 30, 48)
MATURITY_H = 48
CORE_REACH_H = 30
UTC = dt.timezone.utc
NAVD = -2.82
ENH = 0.0


def _utc(s):
    t = dt.datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    return t if t.tzinfo else t.replace(tzinfo=UTC)


def hour(t):
    return t.replace(minute=0, second=0, microsecond=0)


def freeze_table(path=os.path.join(ROOT, "models", "wind_shadow", "FREEZE.md")):
    out = {}
    with open(path, encoding="utf-8") as fh:
        lines = fh.readlines()
    for line in lines:
        m = re.match(r"\|\s*`([^`]+)`\s*\|\s*`([0-9a-f]{64})`\s*\|", line)
        if m:
            out[m.group(1)] = m.group(2)
    return out


# ------------------------------------------------------------------ records
def load_records(directory, candidate_id, manifest_sha, runtime_sha):
    evaluable, excluded = [], defaultdict(int)
    for path in sorted(glob.glob(os.path.join(directory, "*.jsonl"))):
        with open(path, encoding="utf-8") as fh:
            lines = fh.readlines()
        for line in lines:
            r = json.loads(line)
            if r.get("collection") != "official":
                excluded["not official collection"] += 1
            elif r.get("candidate_id") != candidate_id:
                excluded["other candidate_id"] += 1
            elif r.get("manifest_sha256") != manifest_sha:
                excluded["manifest hash mismatch" if r.get("manifest_sha256") else "missing manifest identity"] += 1
            elif r.get("runtime_sha256") != runtime_sha:
                excluded["runtime hash mismatch"] += 1
            else:
                evaluable.append(r)
    slots = {}
    for r in sorted(evaluable, key=lambda r: (r.get("nominal_issuance_hour_utc") or r["issuance_utc"], r.get("written_utc", ""))):
        slots.setdefault(hour(_utc(r.get("nominal_issuance_hour_utc") or r["issuance_utc"])), r)
    return slots, dict(excluded)


# ------------------------------------------------------------------ observations
def parse_observations(water_level_js, predictions_js):
    """{hour: {surge, obs, pred, valid, reason}} with the declared QC."""
    wl = {}
    for r in water_level_js.get("data") or []:
        try:
            wl[_utc(r["t"].replace(" ", "T") + "Z")] = r
        except (KeyError, ValueError):
            continue
    out = {}
    for r in predictions_js.get("predictions") or []:
        try:
            t = _utc(r["t"].replace(" ", "T") + "Z"); p = float(r["v"])
        except (KeyError, ValueError, TypeError):
            continue
        if not math.isfinite(p):
            continue
        w = wl.get(t)
        rec = {"pred": p, "obs": None, "surge": None, "valid": False, "reason": None}
        if w is None:
            rec["reason"] = "no observation"
        else:
            try:
                v = float(w["v"])
            except (KeyError, TypeError, ValueError):
                v = float("nan")
            fs = str(w.get("f", ""))
            flags = fs.split(",") if fs else []
            if not math.isfinite(v):
                rec["reason"] = "non-finite value"
            elif len(flags) != 4 or not all(x.strip().isdigit() for x in flags):
                rec["reason"] = f"malformed flags {fs!r}"
            elif any(int(x) for x in flags):
                rec["reason"] = f"quality flag set {fs}"
            else:
                rec.update(obs=v, surge=v - p, valid=True)
        out[t] = rec
    return out


def fetch_observations(t0, t1, save_dir=None):
    wl_all, pr_all, raw = {"data": []}, {"predictions": []}, []
    a = t0
    while a < t1:
        b = min(a + dt.timedelta(days=30), t1)
        for product, extra, key, acc in (("water_level", {}, "data", wl_all), ("predictions", {"interval": "h"}, "predictions", pr_all)):
            q = {"product": product, "station": "8531680", "begin_date": a.strftime("%Y%m%d %H:%M"),
                 "end_date": b.strftime("%Y%m%d %H:%M"), "datum": "MLLW", "time_zone": "gmt", "units": "english",
                 "format": "json", "application": "barnacle-wind-shadow-eval", **extra}
            req = urllib.request.Request("https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?" + urllib.parse.urlencode(q),
                                         headers={"User-Agent": "barnacle-wind-shadow-eval"})
            body = urllib.request.urlopen(req, timeout=60).read()
            acc[key] += json.loads(body).get(key) or []
            raw.append({"product": product, "begin": q["begin_date"], "end": q["end_date"],
                        "retrieved_utc": dt.datetime.now(UTC).isoformat(), "sha256": hashlib.sha256(body).hexdigest()})
        a = b
    bundle = {"water_level": wl_all, "predictions": pr_all, "responses": raw}
    if save_dir:
        os.makedirs(save_dir, exist_ok=True)
        path = os.path.join(save_dir, f"observations-{t0:%Y%m%dT%H}-{t1:%Y%m%dT%H}.json")
        with open(path, "w") as f:
            json.dump(bundle, f)
        bundle["saved_to"] = path
    return bundle


# ------------------------------------------------------------------ episodes, pairs
def episodes(obs, t0, t1):
    eps, cur, run, first, quiet = [], None, 0, None, 0
    t = hour(t0)
    while t <= t1:
        o = obs.get(t)
        state = None if (o is None or not o["valid"]) else ("hi" if o["surge"] >= 1.0 else "lo")
        if cur is None:
            if state == "hi":
                run += 1; first = first or t
                if run >= 6:
                    cur = {"start": first, "end": t, "completed": False, "completed_at": None}
                    quiet = 0
            else:
                run, first = 0, None
        else:
            if state == "hi":
                cur["end"], quiet = t, 0
            elif state == "lo":
                quiet += 1
                if quiet >= 48:
                    cur.update(completed=True, completed_at=t)
                    eps.append(cur); cur, run, first, quiet = None, 0, None, 0
            else:
                quiet = 0                                      # invalid hour breaks the quiet run
        t += dt.timedelta(hours=1)
    if cur is not None:
        eps.append(cur)
    return eps


def extrema(obs):
    ts = sorted(obs)
    hi, lo = set(), set()
    for a, b, c in zip(ts, ts[1:], ts[2:]):
        pa, pb, pc = obs[a]["pred"], obs[b]["pred"], obs[c]["pred"]
        if pb > pa and pb >= pc:
            hi.add(b)
        if pb < pa and pb <= pc:
            lo.add(b)
    return hi, lo


def pairs_for(slots, obs, now, lead, counts):
    out = []
    for t_slot, r in slots.items():
        counts["opportunity_records"] += 1
        if r.get("status") == "error" or not r.get("baseline_surge_ft"):
            counts["error_no_baseline"] += 1
            continue
        tgt = _utc(r["leads"]["start"]) + dt.timedelta(hours=lead - 1)
        if (now - tgt).total_seconds() / 3600 < MATURITY_H:
            counts["immature"] += 1
            continue
        o = obs.get(tgt)
        if o is None:
            counts["outcome_missing"] += 1
            continue
        if not o["valid"]:
            counts["outcome_invalid"] += 1
            continue
        b, c = r["baseline_surge_ft"][lead - 1], r["candidate_surge_ft"][lead - 1]
        prod = None
        pc = (r.get("production_curve_tide_navd88") or [None] * 48)[lead - 1]
        if pc is not None:
            prod = pc - NAVD - ENH - o["pred"]
        nw = (r.get("nws_outlook_surge") or [None] * 48)[lead - 1]
        out.append({"issuance": t_slot, "target": tgt, "cand": c, "base": b, "prod": prod,
                    "prod_version": r.get("production_model_version"),
                    "nws": nw[0] if nw else None, "nws_source": nw[1] if nw else None,
                    "obs": o["surge"], "status": r["status"]})
        counts["scored"] += 1
        counts["scored_fallback"] += r["status"] == "fallback"
    return out


def stats(ps, key):
    errs = [p[key] - p["obs"] for p in ps if p.get(key) is not None]
    if not errs:
        return {"n": 0}
    return {"n": len(errs), "mae": sum(abs(e) for e in errs) / len(errs), "bias": sum(errs) / len(errs),
            "large_abs_rate": sum(abs(e) > 1 for e in errs) / len(errs),
            "large_under_rate": sum(e < -1 for e in errs) / len(errs)}


def block_ci(ps, a="cand", b="base", seed=20260924, n=1000):
    ps = [p for p in ps if p.get(a) is not None and p.get(b) is not None]
    if not ps:
        return None
    blocks = defaultdict(list)
    for p in ps:
        blocks[(p["issuance"] - dt.datetime(2026, 1, 1, tzinfo=UTC)).days // 7].append(p)
    keys, rnd, diffs = sorted(blocks), random.Random(seed), []
    for _ in range(n):
        s = [q for _k in keys for q in blocks[rnd.choice(keys)]]
        diffs.append(sum(abs(q[a] - q["obs"]) for q in s) / len(s) - sum(abs(q[b] - q["obs"]) for q in s) / len(s))
    diffs.sort()
    return [round(diffs[int(0.05 * n)], 4), round(diffs[int(0.95 * n)], 4)]


def continuity_and_revisions(slots):
    cont_c, cont_b, rev_c, rev_b, trans = [], [], [], [], 0
    prev_status, prev = None, None
    for t in sorted(slots):
        r = slots[t]
        if prev_status is not None and r.get("status") != prev_status:
            trans += 1
        prev_status = r.get("status")
        c, b = r.get("candidate_surge_ft"), r.get("baseline_surge_ft")
        if c and b:
            cont_c.append(max(abs(x - y) for x, y in zip(c[1:], c[:-1])))
            cont_b.append(max(abs(x - y) for x, y in zip(b[1:], b[:-1])))
            if prev is not None and (t - prev[0]) == dt.timedelta(hours=1) and prev[1] and prev[2]:
                # same target: this slot's lead h vs the previous slot's lead h+1
                rev_c += [abs(c[h] - prev[1][h + 1]) for h in range(47)]
                rev_b += [abs(b[h] - prev[2][h + 1]) for h in range(47)]
        prev = (t, c, b)
    m = lambda xs: (sum(xs) / len(xs)) if xs else None
    return {"max_hourly_step_mean_candidate": m(cont_c), "max_hourly_step_mean_baseline": m(cont_b),
            "revision_mean_candidate": m(rev_c), "revision_mean_baseline": m(rev_b), "status_transitions": trans}


# ------------------------------------------------------------------ rain-tank sensitivity
def load_replay(directory=os.path.join(ROOT, "data", "replay_inputs")):
    out = {}
    for path in sorted(glob.glob(os.path.join(directory, "*.jsonl"))):
        with open(path, encoding="utf-8") as fh:
            lines = fh.readlines()
        for line in lines:
            try:
                r = json.loads(line)
                out[r["generated_utc"]] = r
            except (ValueError, KeyError):
                continue
    return out


def rain_tank_sensitivity(slots, replay):
    sys.path.insert(0, ROOT)
    from forecast import flood_forecast_daily as ff
    from forecast import replay_archive as ra
    rows, missing = [], defaultdict(int)
    for t, r in sorted(slots.items()):
        if not r.get("baseline_surge_ft"):
            continue
        rp = replay.get(r["issuance_utc"])
        if rp is None:
            missing["no replay record for the issuance"] += 1
            continue
        if not rp.get("qpf_hourly") or not rp.get("outlook_hourly"):
            missing["as-issued QPF or astronomy unavailable"] += 1
            continue
        qpf = {tt: v["in_hr"] for tt, v in ra.expand(rp["qpf_hourly"])}
        astro = {tt: v["astro_mllw"] for tt, v in ra.expand(rp["outlook_hourly"])}
        start = _utc(r["leads"]["start"])
        times, bb, bc, rates = [], [], [], []
        for h in range(48):
            tt = start + dt.timedelta(hours=h)
            if tt not in qpf or tt not in astro or qpf[tt] is None or astro[tt] is None:
                break
            times.append(tt); rates.append(qpf[tt])
            bb.append(astro[tt] + r["baseline_surge_ft"][h] + ENH + NAVD)
            bc.append(astro[tt] + r["candidate_surge_ft"][h] + ENH + NAVD)
        if len(times) < 6:
            missing["QPF/astronomy cover < 6 h"] += 1
            continue
        wet = max(rates[:CORE_REACH_H]) >= 0.25
        pb, pc = ff.simulate_pluvial_series(times, bb, rates), ff.simulate_pluvial_series(times, bc, rates)
        wb = [max(x, y) if y is not None else x for x, y in zip(bb, pb)]
        wc = [max(x, y) if y is not None else x for x, y in zip(bc, pc)]
        curb = 4.16
        rows.append({"issuance": t, "wet": wet, "hours": len(times),
                     "peak_in_baseline": round((max(wb) - 3.52) * 12, 1), "peak_in_candidate": round((max(wc) - 3.52) * 12, 1),
                     "hours_above_curb_baseline": sum(x >= curb for x in wb), "hours_above_curb_candidate": sum(x >= curb for x in wc)})
    wet_rows = [x for x in rows if x["wet"]]
    events, last = 0, None
    for x in wet_rows:
        if last is None or (x["issuance"] - last) > dt.timedelta(hours=12):
            events += 1
        last = x["issuance"]
    d = [x["peak_in_candidate"] - x["peak_in_baseline"] for x in wet_rows]
    return {"issuances_with_inputs": len(rows), "wet_issuances": len(wet_rows), "wet_events": events,
            "treatment": "descriptive only (< 3 wet events)" if events < 3 else "paired evidence for independent review",
            "wet_peak_change_in_mean": (sum(d) / len(d)) if d else None,
            "wet_peak_change_in_range": [min(d), max(d)] if d else None,
            "wet_hours_above_curb_change": sum(x["hours_above_curb_candidate"] - x["hours_above_curb_baseline"] for x in wet_rows),
            "missing_inputs": dict(missing),
            "note": "leads > 30 h use the offline 48-h extension of the frozen baseline, not a published core curve"}


# ------------------------------------------------------------------ evaluation
def evaluate(slots, obs, now, replay=None, excluded=None):
    rep = {"excluded_records": excluded or {}}
    if not slots:
        rep.update(verdict="INCONCLUSIVE", reason="no evaluable records")
        return rep
    first = min(slots)
    eps = episodes(obs, first, now)
    completed = [e for e in eps if e["completed"]]
    endpoint = None
    if len(completed) >= 5:
        fifth = sorted(completed, key=lambda e: e["completed_at"])[4]["completed_at"]
        cut = max(first + dt.timedelta(days=60), fifth)
        endpoint = (cut + dt.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    final = endpoint is not None and now >= endpoint + dt.timedelta(hours=48 + MATURITY_H)
    last_slot = hour(min(now, endpoint - dt.timedelta(hours=1))) if endpoint else hour(now)
    window = {t: r for t, r in slots.items() if t <= last_slot}
    n_opp = int((last_slot - first).total_seconds() // 3600) + 1
    states = defaultdict(int)
    for t, r in window.items():
        states[r.get("status")] += 1
    states["missing"] = n_opp - len(window)
    coverage = (states["candidate"] + states["fallback"]) / n_opp if n_opp else 0.0
    rep.update(first_opportunity=first.isoformat(), endpoint=endpoint.isoformat() if endpoint else None,
               status="FINAL" if final else "INTERIM (descriptive only)", opportunities=n_opp,
               slot_states=dict(states), coverage=round(coverage, 4),
               episodes=[{k: (v.isoformat() if isinstance(v, dt.datetime) else v) for k, v in e.items()} for e in eps],
               continuity=continuity_and_revisions(window), leads={})
    hi, lo = extrema(obs)
    checks, inconclusive = [], []
    if coverage < 0.80:
        inconclusive.append(f"coverage {coverage:.2f} < 0.80")
    for lead in LEADS:
        counts = defaultdict(int)
        P = pairs_for(window, obs, now, lead, counts)
        views = {"all": P, "high_tide_target": [p for p in P if p["target"] in hi],
                 "low_tide_target": [p for p in P if p["target"] in lo],
                 "plug_band_target": [p for p in P if 2.5 <= obs[p["target"]]["obs"] + NAVD <= 3.8],
                 "storm_start_issuance": [p for p in P if obs.get(p["issuance"]) and obs[p["issuance"]]["valid"]
                                          and obs[p["issuance"]]["surge"] >= 1.0]}
        row = {"counts": dict(counts), "views": {}}
        for name, ps in views.items():
            row["views"][name] = {"candidate": stats(ps, "cand"), "baseline_frozen": stats(ps, "base"),
                                  "mae_diff_ci90_7d_blocks": block_ci(ps)}
        prod = [p for p in P if p["prod"] is not None]
        cohorts = defaultdict(list)
        for p in prod:
            cohorts[p["prod_version"]].append(p)
        row["vs_actual_production_curve"] = {v: {"candidate": stats(ps, "cand"), "production": stats(ps, "prod"),
                                                 "baseline_frozen": stats(ps, "base")} for v, ps in cohorts.items()}
        row["vs_actual_production_curve_note"] = ("within the published core reach" if lead <= CORE_REACH_H
                                                  else "beyond the ~30-h core curve: no production comparator")
        by_src = defaultdict(list)
        for p in P:
            if p["nws"] is not None:
                by_src[p["nws_source"]].append(p)
        row["vs_nws_petss_guidance"] = {src: {"candidate": stats(ps, "cand"), "nws_petss": stats(ps, "nws")}
                                        for src, ps in by_src.items()}
        row["nws_petss_coverage"] = round(sum(len(v) for v in by_src.values()) / len(P), 4) if P else None
        ep_rows = []
        for e in eps:
            span_valid = [t for t, o in obs.items() if e["start"] <= t <= e["end"] and o["valid"]]
            ps = [p for p in P if e["start"] <= p["target"] <= e["end"]]
            scorable = len(ps) >= 6 and span_valid and len({p["target"] for p in ps}) >= 0.5 * len(span_valid)
            ep_rows.append({"start": e["start"].isoformat(), "completed": e["completed"], "pairs": len(ps),
                            "scorable": bool(scorable),
                            "mae_candidate": stats(ps, "cand").get("mae"), "mae_baseline": stats(ps, "base").get("mae")})
        sc = [x for x in ep_rows if x["scorable"] and x["completed"]]
        row["episodes"] = {"rows": ep_rows, "scorable_completed": len(sc),
                           "candidate_wins": sum(x["mae_candidate"] < x["mae_baseline"] for x in sc),
                           "equal_episode_mean_candidate": (sum(x["mae_candidate"] for x in sc) / len(sc)) if sc else None,
                           "equal_episode_mean_baseline": (sum(x["mae_baseline"] for x in sc) / len(sc)) if sc else None}
        rep["leads"][lead] = row
        v = row["views"]
        def lower(name):
            c, b = v[name]["candidate"], v[name]["baseline_frozen"]
            return None if not c["n"] else c["mae"] < b["mae"]
        if lead in (24, 30):
            checks += [(f"mae all {lead}h", lower("all")), (f"mae storm {lead}h", lower("storm_start_issuance"))]
            if len(sc) < 5:
                inconclusive.append(f"only {len(sc)} scorable completed episodes at {lead} h")
                checks.append((f"episode majority {lead}h", None))
            else:
                checks.append((f"episode majority {lead}h", row["episodes"]["candidate_wins"] * 2 > len(sc)))
        pb = v["plug_band_target"]
        checks.append((f"plug band {lead}h", None if not pb["candidate"]["n"]
                       else pb["candidate"]["mae"] - pb["baseline_frozen"]["mae"] <= 0.01))
        al = v["all"]
        checks.append((f"large under {lead}h", None if not al["candidate"]["n"]
                       else al["candidate"]["large_under_rate"] <= al["baseline_frozen"]["large_under_rate"]))
    rep["rain_tank_sensitivity"] = rain_tank_sensitivity(window, replay or {}) if replay is not None else "not requested"
    rep["checks"] = [{"check": c, "pass": ok} for c, ok in checks]
    if inconclusive or any(ok is None for _c, ok in checks):
        verdict = "INCONCLUSIVE"
        rep["inconclusive_because"] = inconclusive + [c for c, ok in checks if ok is None]
    else:
        verdict = "PASS" if all(ok for _c, ok in checks) else "FAIL"
    rep["verdict"] = verdict if final else f"INTERIM ({verdict} so far; not a decision)"
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=os.path.join(ROOT, "data", "wind_shadow"))
    ap.add_argument("--now", default=None)
    ap.add_argument("--obs-json", default=None, help="replay a saved observation bundle offline")
    ap.add_argument("--save-obs", default=None, help="directory to save the fetched raw observations")
    a = ap.parse_args()
    fr = freeze_table()
    m = json.load(open(os.path.join(ROOT, "models", "wind_shadow", "manifest.json")))
    slots, excluded = load_records(a.dir, m["candidate_id"], fr["models/wind_shadow/manifest.json"],
                                   fr["forecast/wind_shadow.py"])
    now = _utc(a.now) if a.now else dt.datetime.now(UTC)
    header = {"evaluator_sha256": hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(),
              "freeze_evaluator_sha256": fr.get("history/scripts/evaluate_wind_shadow.py"), "now": now.isoformat()}
    if not slots:
        print(json.dumps({**header, "verdict": "INCONCLUSIVE", "reason": "no evaluable records", "excluded": excluded}))
        return 0
    if a.obs_json:
        bundle = json.load(open(a.obs_json))
    else:
        bundle = fetch_observations(min(slots) - dt.timedelta(days=1), now, a.save_obs)
    obs = parse_observations(bundle["water_level"], bundle["predictions"])
    rep = evaluate(slots, obs, now, replay=load_replay(), excluded=excluded)
    rep.update(header, observation_responses=bundle.get("responses"), observation_bundle=bundle.get("saved_to") or a.obs_json)
    print(json.dumps(rep, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
