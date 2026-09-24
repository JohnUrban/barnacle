#!/usr/bin/env python3
"""Deterministic evaluator for the wind-shadow trial, candidate c2 (FROZEN before
the first official record; hash in models/wind_shadow/FREEZE.md). Plan:
history/plans/2026-09-24-wind-term-candidate-plan.md; repairs per audit
2026-09-24-a3 (R1 episodes/endpoint, R2 missingness/QC, R3 comparators,
R5 outcome provenance, R6 identity binding; round 03: bundle enforcement,
trial start, rain initial condition, raw guidance comparators).

DECLARED RULES
Bundle: before scoring, every FREEZE-listed file (this evaluator included) is
  hashed and must match FREEZE.md, and the FIRST official record of the trial
  log must carry the same bundle identity (bundle_sha256). Otherwise nothing is
  scored (exit 3); --unfrozen scores anyway but labels the report NON-OFFICIAL.
  Editing a file and its FREEZE entry after the trial start therefore cannot
  pass: the first record's bundle is fixed in the append-only log.
Trial start: the nominal issuance hour of the FIRST official record of this
  candidate_id in the log, whatever its status or binding (merge only enables
  the workflow; setup failures and disabled records stay visible as missed
  opportunities instead of moving the start to a later valid record).
Identity: a record is EVALUABLE only if collection == "official", its
  candidate_id, bundle_sha256, manifest_sha256 and runtime_sha256 equal the
  frozen bundle, and its status is candidate, fallback or error. Every other
  official record of this id is a non-evaluable attempt, counted by reason and
  by slot. Identities are never pooled.
Opportunities: one per UTC hour slot from the trial start; per slot the
  EARLIEST-written evaluable record. Slot states: candidate | fallback
  (baseline kept) | error (no baseline) | not_evaluable (only disabled or
  unbound records) | missing.
Observations: CO-OPS 6-min water_level on the hour minus hourly predictions,
  UTC. VALID iff the value is finite, the flag field parses to exactly four
  integers [O,F,R,L], and the tolerance flags F, R, L are all 0; otherwise
  invalid with the reason retained. O is NOT a pass/fail flag: CO-OPS defines
  it as the count of 1-s samples outside a 3-sigma band; it is kept per hour
  (outlier_samples). Requiring O = 0 would drop elevated-surge hours
  preferentially (a3 reply 04: 7.9 % of 1.0-1.5 ft hours vs 1.8 % below 0.5 ft). With --save-obs
  DIR every raw response body is saved under its SHA-256; --obs-json replays a
  saved bundle offline, re-parsing the raw bodies after verifying their hashes.
  A report without retained raw bodies says so (outcome_provenance).
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
  vs RAW NWPS (gauge forecast minus astronomy, no advisory correction) and vs
  the P-ETSS hourly mid, each eligible only where that guidance covered the
  target at issuance, availability reported per scored pair and per
  opportunity; Barnacle's final outlook (a blend of advisory-adjusted NWPS,
  P-ETSS, guidance decay, observed decay and the typical offset) is a separate
  comparator by source and is NOT external guidance. Leads > 30 h compare with
  the OFFLINE 48-h extension of the frozen baseline, not a published core curve.
Views: all; high/low tide and plug band (observed bay 2.5..3.8 ft NAVD88) at
  TARGET; storm start (observed surge >= +1.0 ft) at ISSUANCE.
Metrics for every method: n, MAE, bias, rate |err| > 1 ft, rate err < -1 ft;
  per-episode MAEs, wins, equal-episode mean; continuity (hour-to-hour change
  along each issued curve) and revisions (same target, consecutive slots);
  status transitions; 7-day moving-block bootstrap 90 % interval (1000, seed
  20260924) for MAE differences.
Rain-tank sensitivity (descriptive): from each record's as-issued tank inputs,
  run the FROZEN tank (models/wind_shadow/rain_ref.py) from production's series
  start (storage empty there, as production; the pre-issuance rain and bay are
  the shared history) with identical QPF; after issuance each variant's bay is
  production's bay plus (variant surge - production surge). The frozen tank on
  production's own bay is checked against production's pluvial line. Scored
  after issuance to the series end: peak depth (in) and hours above each
  flood-window landmark, baseline vs candidate; wet = max QPF rate >= 0.25 in/h
  anywhere in the series; wet slots within 12 h form one wet event; fewer than
  3 wet events -> descriptive only, never a rain-skill pass/fail.
PASS requires ALL (else FAIL; any required input empty -> INCONCLUSIVE):
  lower MAE than frozen baseline at 24 AND 30 h in all hours AND storm starts;
  plug-band MAE loss <= 0.01 ft at every lead; large-under-prediction rate not
  higher than baseline at every lead; strict majority of SCORABLE episodes won
  at 24 and 30 h with >= 5 scorable episodes at each; coverage >= 0.80.
"""
from __future__ import annotations

import argparse, datetime as dt, glob, hashlib, json, math, os, random, re, sys, urllib.parse, urllib.request
import base64, gzip, importlib.util
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from forecast import wind_shadow as ws  # noqa: E402  (frozen runtime: bundle check, time grid)
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
    return ws.read_freeze(path)[1]


def rain_ref():
    spec = importlib.util.spec_from_file_location("wind_shadow_rain_ref",
                                                  os.path.join(ROOT, "models", "wind_shadow", "rain_ref.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ------------------------------------------------------------------ records
def read_log(directory):
    """All parsable object records, in file order (months sorted)."""
    out, unreadable = [], 0
    for path in sorted(glob.glob(os.path.join(directory, "*.jsonl"))):
        with open(path, encoding="utf-8") as fh:
            lines = fh.readlines()
        for line in lines:
            try:
                r = json.loads(line)
            except ValueError:
                unreadable += 1
                continue
            if isinstance(r, dict):
                out.append(r)
            else:
                unreadable += 1
    return out, unreadable


def _slot(r):
    try:
        return hour(_utc(r.get("nominal_issuance_hour_utc") or r["issuance_utc"]))
    except (KeyError, TypeError, ValueError):
        return None


def load_records(directory, candidate_id, bundle_sha, manifest_sha, runtime_sha):
    """(slots, attempts, excluded, trial) — slots: evaluable records by hour;
    attempts: hour -> reasons for non-evaluable official records of this id;
    trial: {start, first_record_bundle_sha256}."""
    records, unreadable = read_log(directory)
    excluded, attempts, evaluable = defaultdict(int), defaultdict(list), []
    if unreadable:
        excluded["unparsable line"] += unreadable
    official = [r for r in records if r.get("collection") == "official" and r.get("candidate_id") == candidate_id]
    for r in records:
        if r.get("collection") != "official":
            excluded["not official collection"] += 1
        elif r.get("candidate_id") != candidate_id:
            excluded["other candidate_id"] += 1
    for r in official:
        why = None
        if r.get("status") == "disabled":
            why = "disabled (bundle check failed at collection)"
        elif r.get("bundle_sha256") != bundle_sha:
            why = "bundle mismatch"
        elif r.get("manifest_sha256") != manifest_sha:
            why = "manifest hash mismatch" if r.get("manifest_sha256") else "missing manifest identity"
        elif r.get("runtime_sha256") != runtime_sha:
            why = "runtime hash mismatch"
        elif r.get("status") not in ("candidate", "fallback", "error"):
            why = f"status {r.get('status')!r}"
        if why:
            excluded[why] += 1
            if _slot(r) is not None:
                attempts[_slot(r)].append(why)
        else:
            evaluable.append(r)
    slots = {}
    for r in sorted(evaluable, key=lambda r: (_slot(r), r.get("written_utc", ""))):
        slots.setdefault(_slot(r), r)
    starts = [t for t in (_slot(r) for r in official) if t is not None]
    trial = {"start": min(starts) if starts else None,
             "first_record_bundle_sha256": official[0].get("bundle_sha256") if official else None}
    return slots, dict(attempts), dict(excluded), trial


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
            elif any(int(x) for x in flags[1:]):
                rec["reason"] = f"tolerance flag set {fs}"
            else:
                rec.update(obs=v, surge=v - p, valid=True, outlier_samples=int(flags[0]))
        out[t] = rec
    return out


def _merge_raw(parts):
    """[(product, body bytes)] -> the merged water_level / predictions JSON."""
    wl_all, pr_all = {"data": []}, {"predictions": []}
    for product, body in parts:
        js = json.loads(body)
        if product == "water_level":
            wl_all["data"] += js.get("data") or []
        else:
            pr_all["predictions"] += js.get("predictions") or []
    return wl_all, pr_all


def fetch_observations(t0, t1, save_dir=None):
    parts, raw = [], []
    a = t0
    while a < t1:
        b = min(a + dt.timedelta(days=30), t1)
        for product, extra in (("water_level", {}), ("predictions", {"interval": "h"})):
            q = {"product": product, "station": "8531680", "begin_date": a.strftime("%Y%m%d %H:%M"),
                 "end_date": b.strftime("%Y%m%d %H:%M"), "datum": "MLLW", "time_zone": "gmt", "units": "english",
                 "format": "json", "application": "barnacle-wind-shadow-eval", **extra}
            req = urllib.request.Request("https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?" + urllib.parse.urlencode(q),
                                         headers={"User-Agent": "barnacle-wind-shadow-eval"})
            body = urllib.request.urlopen(req, timeout=60).read()
            sha = hashlib.sha256(body).hexdigest()
            entry = {"product": product, "begin": q["begin_date"], "end": q["end_date"],
                     "retrieved_utc": dt.datetime.now(UTC).isoformat(), "sha256": sha}
            if save_dir:
                os.makedirs(os.path.join(save_dir, "raw"), exist_ok=True)
                with open(os.path.join(save_dir, "raw", f"{sha}.json"), "wb") as f:
                    f.write(body)                                  # the original response bytes
                entry["file"] = f"raw/{sha}.json"
            parts.append((product, body)); raw.append(entry)
        a = b
    wl_all, pr_all = _merge_raw(parts)
    bundle = {"water_level": wl_all, "predictions": pr_all, "responses": raw}
    if save_dir:
        path = os.path.join(save_dir, f"observations-{t0:%Y%m%dT%H}-{t1:%Y%m%dT%H}.json")
        with open(path, "w") as f:
            json.dump(bundle, f)
        bundle["saved_to"] = path
    return bundle


def load_observation_bundle(path):
    """Offline replay. If every response's raw body was retained, re-parse the
    raw bodies after verifying each SHA-256 (a mismatch is an error); otherwise
    use the merged rows and report that raw bodies were not retained."""
    with open(path) as f:
        bundle = json.load(f)
    base = os.path.dirname(os.path.abspath(path))
    resp = bundle.get("responses") or []
    if resp and all(r.get("file") for r in resp):
        parts = []
        for r in resp:
            with open(os.path.join(base, r["file"]), "rb") as f:
                body = f.read()
            if hashlib.sha256(body).hexdigest() != r["sha256"]:
                raise ValueError(f"raw observation body {r['file']} does not match its SHA-256")
            parts.append((r["product"], body))
        bundle["water_level"], bundle["predictions"] = _merge_raw(parts)
        bundle["outcome_provenance"] = "raw response bodies retained; hashes verified; re-parsed from raw"
    else:
        bundle["outcome_provenance"] = "merged rows only: raw response bodies NOT retained"
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
        ol = (r.get("barnacle_outlook_surge") or [None] * 48)[lead - 1]
        g = r.get("guidance") or {}
        out.append({"issuance": t_slot, "target": tgt, "cand": c, "base": b, "prod": prod,
                    "prod_version": r.get("production_model_version"),
                    "nwps": ((g.get("nwps_raw") or {}).get("surge_ft") or [None] * 48)[lead - 1],
                    "petss": ((g.get("petss_mid") or {}).get("surge_ft") or [None] * 48)[lead - 1],
                    "outlook": ol[0] if ol else None, "outlook_source": ol[1] if ol else None,
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
def rain_tank_sensitivity(slots, rr=None):
    rr = rr or rain_ref()
    marks = rr.LANDMARKS_NAVD88
    rows, missing, check = [], defaultdict(int), []
    for t, r in sorted(slots.items()):
        ri = r.get("rain_inputs") or {}
        if "production_tide_navd88" not in ri:
            missing[ri.get("reason") or "no as-issued tank inputs in the record"] += 1
            continue
        if ri.get("qpf_in_hr") is None:
            missing[ri.get("qpf_reason") or "QPF unavailable at issuance"] += 1
            continue
        if not ri.get("baseline_surge_ft") or not ri.get("candidate_surge_ft"):
            missing["variant surges unavailable"] += 1
            continue
        times, rates = ws.rain_times(ri), ri["qpf_in_hr"]
        prod, sp = ri["production_tide_navd88"], ri["production_surge_ft"]
        if any(x is None for x in prod) or len(times) < 2:
            missing["incomplete production bay series"] += 1
            continue
        bb = [pt if b is None else pt - s0 + b for pt, s0, b in zip(prod, sp, ri["baseline_surge_ft"])]
        bc = [pt if c is None else pt - s0 + c for pt, s0, c in zip(prod, sp, ri["candidate_surge_ft"])]
        pp = rr.simulate_pluvial_series(times, prod, rates)
        diffs = [abs(x - y) for x, y in zip(pp, ri["production_pluvial_navd88"]) if x is not None and y is not None]
        mism = sum((x is None) != (y is None) for x, y in zip(pp, ri["production_pluvial_navd88"]))
        check.append((max(diffs) if diffs else 0.0, mism))
        pb, pc = rr.simulate_pluvial_series(times, bb, rates), rr.simulate_pluvial_series(times, bc, rates)
        wb = [max(x, y) if y is not None else x for x, y in zip(bb, pb)]
        wc = [max(x, y) if y is not None else x for x, y in zip(bc, pc)]
        after = [i for i, tt in enumerate(times) if tt > _utc(ri["issuance_utc"])]
        if not after:
            missing["no points after issuance"] += 1
            continue
        step_h = ((times[-1] - times[0]).total_seconds() / 3600.0) / (len(times) - 1)
        lm = {}
        for k, e in marks.items():
            db = max(max(wb[i] - e, 0.0) for i in after) * 12
            dc = max(max(wc[i] - e, 0.0) for i in after) * 12
            hb = sum(wb[i] > e for i in after) * step_h
            hc = sum(wc[i] > e for i in after) * step_h
            lm[k] = (round(db, 2), round(dc, 2), hb, hc)
        rows.append({"issuance": t, "wet": max(rates) >= 0.25, "landmarks": lm})

    def summarize(sub):
        out = {}
        for k in marks:
            d = [x["landmarks"][k][1] - x["landmarks"][k][0] for x in sub]
            dh = [x["landmarks"][k][3] - x["landmarks"][k][2] for x in sub]
            reached_b = sum(x["landmarks"][k][0] > 0 for x in sub)
            reached_c = sum(x["landmarks"][k][1] > 0 for x in sub)
            out[k] = {"issuances_reached_baseline": reached_b, "issuances_reached_candidate": reached_c,
                      "peak_depth_change_in_mean": round(sum(d) / len(d), 3) if d else None,
                      "peak_depth_change_in_range": [round(min(d), 2), round(max(d), 2)] if d else None,
                      "hours_above_change_total": round(sum(dh), 1)}
        return out
    wet_rows = [x for x in rows if x["wet"]]
    events, last = 0, None
    for x in wet_rows:
        if last is None or (x["issuance"] - last) > dt.timedelta(hours=12):
            events += 1
        last = x["issuance"]
    return {"issuances_with_inputs": len(rows), "wet_issuances": len(wet_rows), "wet_events": events,
            "treatment": "descriptive only (< 3 wet events)" if events < 3 else "paired evidence for independent review",
            "landmarks_wet": summarize(wet_rows), "landmarks_all_issuances": summarize(rows),
            "frozen_tank_vs_production_pluvial": {
                "issuances": len(check), "max_abs_diff_ft": max((c[0] for c in check), default=None),
                "presence_mismatches": sum(c[1] for c in check)},
            "missing_inputs": dict(missing),
            "note": ("scenario sensitivity (same rain, two bays), not observed street-depth skill; "
                     "from production's series start with its empty-storage initial condition")}


# ------------------------------------------------------------------ evaluation
def evaluate(slots, obs, now, rain=True, excluded=None, attempts=None, trial_start=None):
    rep = {"excluded_records": excluded or {}}
    attempts = attempts or {}
    if not slots:
        rep.update(verdict="INCONCLUSIVE", reason="no evaluable records", trial_start=trial_start and trial_start.isoformat())
        return rep
    first = min([min(slots)] + ([trial_start] if trial_start else []) + list(attempts))
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
    states["not_evaluable"] = sum(1 for t in attempts if first <= t <= last_slot and t not in window)
    states["missing"] = n_opp - len(window) - states["not_evaluable"]
    coverage = (states["candidate"] + states["fallback"]) / n_opp if n_opp else 0.0
    rep.update(trial_start=first.isoformat(), first_opportunity=first.isoformat(), endpoint=endpoint.isoformat() if endpoint else None,
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
        def avail_per_opp(field, key):
            n = 0
            for r in window.values():
                g = ((r.get("guidance") or {}).get(field) or {}).get("surge_ft") if field else r.get(key)
                n += bool(g and g[lead - 1] is not None)
            return round(n / n_opp, 4) if n_opp else None
        guid = {}
        for name, key, field in (("nwps_raw", "nwps", "nwps_raw"), ("petss_mid", "petss", "petss_mid")):
            sub = [p for p in P if p[key] is not None]
            guid[name] = {"available_in_scored_pairs": round(len(sub) / len(P), 4) if P else None,
                          "available_per_opportunity": avail_per_opp(field, None),
                          "candidate": stats(sub, "cand"), "baseline_frozen": stats(sub, "base"),
                          name: stats(sub, key)}
        row["vs_external_guidance"] = guid
        by_src = defaultdict(list)
        for p in P:
            if p["outlook"] is not None:
                by_src[p["outlook_source"]].append(p)
        row["vs_barnacle_outlook"] = {
            "note": ("Barnacle's final outlook, NOT external guidance: a blend of advisory-adjusted NWPS, "
                     "P-ETSS, guidance decay, observed decay and the typical offset"),
            "available_in_scored_pairs": round(sum(len(v) for v in by_src.values()) / len(P), 4) if P else None,
            "available_per_opportunity": avail_per_opp(None, "barnacle_outlook_surge"),
            "by_source": {src: {"candidate": stats(ps, "cand"), "barnacle_outlook": stats(ps, "outlook")}
                          for src, ps in by_src.items()}}
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
    rep["rain_tank_sensitivity"] = rain_tank_sensitivity(window) if rain else "not requested"
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
    ap.add_argument("--unfrozen", action="store_true",
                    help="score despite a bundle mismatch; the report is labeled NON-OFFICIAL")
    a = ap.parse_args()
    bundle = ws.check_bundle(ROOT)
    table = bundle["table"]
    m = json.load(open(os.path.join(ROOT, "models", "wind_shadow", "manifest.json")))
    slots, attempts, excluded, trial = load_records(a.dir, m["candidate_id"], bundle["bundle_sha256"],
                                                    table.get(ws.MANIFEST_REL), table.get(ws.RUNTIME_REL))
    problems = list(bundle["problems"])
    if trial["start"] is not None and trial["first_record_bundle_sha256"] != bundle["bundle_sha256"]:
        problems.append(f"trial log's first record binds bundle {str(trial['first_record_bundle_sha256'])[:12]}; "
                        f"FREEZE.md now gives {str(bundle['bundle_sha256'])[:12]}")
    now = _utc(a.now) if a.now else dt.datetime.now(UTC)
    header = {"evaluator_sha256": hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(),
              "bundle_sha256": bundle["bundle_sha256"], "bundle_problems": problems, "now": now.isoformat(),
              "trial_start": trial["start"].isoformat() if trial["start"] else None}
    if problems and not a.unfrozen:
        print(json.dumps({**header, "verdict": "NOT SCORED: frozen bundle mismatch", "excluded": excluded}, indent=1))
        return 3
    if not slots:
        print(json.dumps({**header, "verdict": "INCONCLUSIVE", "reason": "no evaluable records", "excluded": excluded}))
        return 0
    if a.obs_json:
        obs_bundle = load_observation_bundle(a.obs_json)
    else:
        start = min([min(slots)] + ([trial["start"]] if trial["start"] else []))
        obs_bundle = fetch_observations(start - dt.timedelta(days=1), now, a.save_obs)
        obs_bundle["outcome_provenance"] = ("raw response bodies retained under --save-obs" if a.save_obs
                                            else "raw response bodies NOT retained (no --save-obs)")
    obs = parse_observations(obs_bundle["water_level"], obs_bundle["predictions"])
    rep = evaluate(slots, obs, now, excluded=excluded, attempts=attempts, trial_start=trial["start"])
    if problems:
        rep["verdict"] = "NON-OFFICIAL (bundle mismatch; --unfrozen): " + str(rep.get("verdict"))
    rep.update(header, observation_responses=obs_bundle.get("responses"),
               observation_bundle=obs_bundle.get("saved_to") or a.obs_json,
               outcome_provenance=obs_bundle.get("outcome_provenance"))
    print(json.dumps(rep, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
