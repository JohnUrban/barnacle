"""Study A evaluator (protocol section 3): advisory-corrected versus raw NWPS
on the seven-day outlook's NWPS-supported hourly line.

Pairs come only from issuances whose raw NWPS hourly levels are archived
(v0.10.6 replay records), joined to the same generation's published outlook.
"""
from __future__ import annotations

import bisect
import datetime as dt
import random
from collections import Counter, defaultdict

from . import archive as A
from . import noaa

UTC = dt.timezone.utc
NAVD = -2.82
LEAD_BINS = ((0, 6), (6, 24), (24, 48), (48, 72))
PHASE_WINDOW_H = 1.5
ZERO_FT = 0.005
UNDER_FT = -0.25
MATURITY_H = 48
MIN_EPISODES = 5


def phase_of(t, hilo):
    """HIGH / LOW within 1.5 h of an astronomical high / low, else MID."""
    times = [h[0] for h in hilo]
    i = bisect.bisect_left(times, t)
    best = None
    for j in (i - 1, i):
        if 0 <= j < len(hilo):
            d = abs((hilo[j][0] - t).total_seconds()) / 3600.0
            if d <= PHASE_WINDOW_H and (best is None or d < best[0]):
                best = (d, hilo[j][2])
    if best is None:
        return "MID"
    return "HIGH" if best[1] in ("H", "HH") else "LOW"


def build_pairs(replay_rows, forecast_for, hilo):
    """replay_rows: [(record, identity)]; forecast_for(generated_utc) -> published forecast or None."""
    from forecast import replay_archive as ra   # noqa: E402 (read-only helper)
    pairs, skipped = [], Counter()
    for rec, ident in replay_rows:
        gen = A.parse_utc(rec["generated_utc"])
        if not rec.get("nwps"):
            skipped["no raw NWPS in the record"] += 1
            continue
        f = forecast_for(rec["generated_utc"])
        if f is None:
            skipped["published forecast not found for the generation"] += 1
            continue
        raw = {t: v["ft"] for t, v in ra.expand(rec["nwps"]["hourly"]) if v.get("ft") is not None}
        recorded = [c.get("ft") for c in (rec.get("advisory_corrections") or [])]
        for p in ((f.get("outlook_7d") or {}).get("series") or []):
            src = p.get("surge_source")
            t = A.parse_utc(p["utc"])
            if src not in ("nws_product", "nwps"):
                skipped[f"source {src} (not a raw-NWPS row)"] += 1
                continue
            if t not in raw or p.get("tide_navd88") is None:
                skipped["target not covered by raw NWPS"] += 1
                continue
            lead = (t - gen).total_seconds() / 3600.0
            if lead <= 0:
                skipped["target not after issuance"] += 1
                continue
            corrected = p["tide_navd88"] - NAVD
            corr = corrected - raw[t]
            pairs.append({"issuance": gen, "target": t, "lead_h": round(lead, 2), "source": src,
                          "corrected_mllw": round(corrected, 4), "uncorrected_mllw": raw[t], "correction_ft": round(corr, 4),
                          "cohort": "ZERO" if abs(corr) < ZERO_FT else "NONZERO", "phase": phase_of(t, hilo),
                          "replay_line": ident, "recorded_nonzero_corrections": sum(1 for c in recorded if c and abs(c) >= ZERO_FT),
                          "nwps_issued": rec["nwps"].get("issued"), "nwps_retrieved_basis": "run time (outlook gather start)"})
    return pairs, dict(skipped)


def lead_bin(h):
    for a, b in LEAD_BINS:
        if a < h <= b:
            return f"({a},{b}]"
    return None


def attach_outcomes(pairs, levels, now):
    for p in pairs:
        o = levels.get(p["target"])
        p["matured"] = (now - p["target"]).total_seconds() / 3600.0 >= MATURITY_H
        if o is None:
            p["outcome"], p["outcome_reason"] = None, "no observation"
        elif not o["valid"]:
            p["outcome"], p["outcome_reason"] = None, o["reason"]
        else:
            p["outcome"], p["outcome_reason"] = o["v"], None
        p["outcome_q"] = (o or {}).get("q")
    return pairs


def episodes(issuances, gap_h=12):
    out, idx, last = {}, -1, None
    for t in sorted(issuances):
        if last is None or (t - last) > dt.timedelta(hours=gap_h):
            idx += 1
        out[t] = idx
        last = t
    return out


def _stats(ps):
    ec = [p["corrected_mllw"] - p["outcome"] for p in ps]
    eu = [p["uncorrected_mllw"] - p["outcome"] for p in ps]
    n = len(ps)
    if not n:
        return {"n": 0}
    return {"n": n, "unique_targets": len({p["target"] for p in ps}), "issuances": len({p["issuance"] for p in ps}),
            "mae_corrected": round(sum(map(abs, ec)) / n, 4), "mae_uncorrected": round(sum(map(abs, eu)) / n, 4),
            "bias_corrected": round(sum(ec) / n, 4), "bias_uncorrected": round(sum(eu) / n, 4),
            "under_rate_corrected": round(sum(e < UNDER_FT for e in ec) / n, 4),
            "under_rate_uncorrected": round(sum(e < UNDER_FT for e in eu) / n, 4)}


def landmark_flips(ps, landmarks):
    """Targets where corrected and uncorrected levels fall on opposite sides of a
    landmark (NAVD88 = MLLW - 2.82), with the observed side."""
    out = {}
    for k, e in landmarks.items():
        flips = [p for p in ps if ((p["corrected_mllw"] + NAVD) > e) != ((p["uncorrected_mllw"] + NAVD) > e)]
        if flips:
            out[k] = {"flips": len(flips), "observed_above": sum((p["outcome"] + NAVD) > e for p in flips)}
    return out


def evaluate(pairs, landmarks, n_boot=2000, seed=20260924):
    scored = [p for p in pairs if p.get("matured") and p.get("outcome") is not None]
    rep = {"pairs": len(pairs), "cohorts": dict(Counter(p["cohort"] for p in pairs)),
           "matured_valid": len(scored),
           "unscored": dict(Counter("immature" if not p.get("matured") else p.get("outcome_reason") for p in pairs
                                    if not (p.get("matured") and p.get("outcome") is not None)))}
    nz_iss = sorted({p["issuance"] for p in pairs if p["cohort"] == "NONZERO"})
    ep = episodes(nz_iss)
    rep["nonzero_episodes_total"] = len(set(ep.values()))
    rep["phases"] = {}
    for ph in ("HIGH", "MID", "LOW"):
        block = {}
        for cohort in ("ZERO", "NONZERO"):
            ps = [p for p in scored if p["phase"] == ph and p["cohort"] == cohort]
            block[cohort] = {"all leads": _stats(ps)}
            for a, b in LEAD_BINS:
                lb = f"({a},{b}]"
                block[cohort][lb] = _stats([p for p in ps if lead_bin(p["lead_h"]) == lb])
            if cohort == "NONZERO":
                block[cohort]["landmark_flips"] = landmark_flips(ps, landmarks)
        nz = [p for p in scored if p["phase"] == ph and p["cohort"] == "NONZERO"]
        per_ep = defaultdict(list)
        for p in nz:
            per_ep[ep[p["issuance"]]].append(abs(p["corrected_mllw"] - p["outcome"]) - abs(p["uncorrected_mllw"] - p["outcome"]))
        diffs = {k: sum(v) / len(v) for k, v in per_ep.items()}
        block["episodes_with_outcomes"] = len(diffs)
        if len(diffs) < MIN_EPISODES:
            block["verdict"] = "NOT YET EVALUABLE" if not diffs else f"NOT YET EVALUABLE ({len(diffs)} < {MIN_EPISODES} episodes)"
        else:
            rnd, keys, vals = random.Random(seed), list(diffs), []
            for _ in range(n_boot):
                s = [diffs[rnd.choice(keys)] for _k in keys]
                vals.append(sum(s) / len(s))
            vals.sort()
            ci = [vals[int(0.05 * n_boot)], vals[int(0.95 * n_boot)]]
            block["episode_mae_diff_ci90"] = [round(x, 4) for x in ci]
            block["verdict"] = "IMPROVES" if ci[1] < 0 else "HARMS" if ci[0] > 0 else "INCONCLUSIVE"
        rep["phases"][ph] = block
    rep["pooled_note"] = "no pooled claim is reported apart from the per-phase results"
    return rep
