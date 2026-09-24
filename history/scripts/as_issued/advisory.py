"""Study A evaluator (protocol section 3): advisory-corrected versus raw NWPS
on the seven-day outlook's NWPS-supported hourly line.

Pairs come only from issuances whose raw NWPS hourly levels are archived
(v0.10.6 replay records), joined to the same generation's published outlook.

Admission (audit 2026-09-24-a4 R2; Amendment 2): the anchors are rebuilt
INDEPENDENTLY from the record's advisory rows and raw NWPS (advisory total
minus the larger NWPS value of the advisory hour and the next) and must match
the recorded anchors; the hourly correction is reconstructed from the recorded
anchors (linear between anchors, full within 1 h outside the first/last, then
fading to zero over 6 h) and (published - raw) must equal it within
CORR_TOL_FT; the source label must agree (nws_product exactly where a
correction applies). Phase needs NOAA extrema on both sides of the target
within 13 h; otherwise the target is UNAVAILABLE (counted, not MID).
Round 03 (Amendment 3): every required number (raw NWPS, advisory totals,
recorded anchors, published outlook level, outcome) must be finite before any
arithmetic; failures are counted exclusions (a NaN can never pass a tolerance).
"""
from __future__ import annotations

import bisect
import datetime as dt
import math
import random
import sys
from collections import Counter, defaultdict

from . import archive as A
from . import noaa

UTC = dt.timezone.utc
NAVD = -2.82
LEAD_BINS = ((0, 6), (6, 24), (24, 48), (48, 72))
PHASE_WINDOW_H = 1.5
PHASE_COVER_H = 13.0         # an extremum on each side within 13 h (semidiurnal spacing ~6.2 h)
ANCHOR_HOLD_H = 1.0          # model/v0.10.6.md "held 1 h outside the first/last"
ANCHOR_FADE_H = 6.0          # "... and fade to zero over a further 6 h"
CORR_TOL_FT = 0.011          # NWPS stored 0.01 (+-0.005), anchors stored 0.01 (+-0.005), outlook 0.001 (+-0.0005)
EPISODE_GAP_H = 12.0         # protocol 3: one episode while consecutive issuances are < 12 h apart
ZERO_FT = 0.005
UNDER_FT = -0.25
MATURITY_H = 48
MIN_EPISODES = 5


def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def phase_of(t, hilo):
    """HIGH / LOW within 1.5 h of an astronomical high / low, MID between
    covered extrema, UNAVAILABLE without an extremum on each side (13 h)."""
    times = [h[0] for h in hilo]
    i = bisect.bisect_left(times, t)
    before = [x for x in times[max(0, i - 2):i + 1] if x <= t and (t - x).total_seconds() <= PHASE_COVER_H * 3600]
    after = [x for x in times[i:i + 2] if x >= t and (x - t).total_seconds() <= PHASE_COVER_H * 3600]
    if not before or not after:
        return "UNAVAILABLE"
    best = None
    for j in (i - 1, i):
        if 0 <= j < len(hilo):
            d = abs((hilo[j][0] - t).total_seconds()) / 3600.0
            if d <= PHASE_WINDOW_H and (best is None or d < best[0]):
                best = (d, hilo[j][2])
    if best is None:
        return "MID"
    return "HIGH" if best[1] in ("H", "HH") else "LOW"


def correction_at(anchors, t):
    """(correction ft, anchored) from [(utc, ft)] anchors, per the v0.10.6 spec;
    implemented independently of forecast/outlook.py (cross-checked in tests)."""
    if not anchors:
        return 0.0, False
    anchors = sorted(anchors)

    def weight(gap_h):
        return max(0.0, 1.0 - max(0.0, gap_h - ANCHOR_HOLD_H) / ANCHOR_FADE_H)
    if t <= anchors[0][0]:
        w = weight((anchors[0][0] - t).total_seconds() / 3600.0)
        return anchors[0][1] * w, w > 0
    if t >= anchors[-1][0]:
        w = weight((t - anchors[-1][0]).total_seconds() / 3600.0)
        return anchors[-1][1] * w, w > 0
    for (t1, c1), (t2, c2) in zip(anchors, anchors[1:]):
        if t1 <= t <= t2:
            span = max(1.0, (t2 - t1).total_seconds())
            return c1 + (c2 - c1) * (t - t1).total_seconds() / span, True
    return 0.0, False


def rebuilt_anchors(rec, raw):
    """[(utc, ft)] from the record's advisory rows: total minus the larger raw
    NWPS value of the advisory hour and the next (spec); rows NWPS does not cover
    are skipped."""
    sys.path.insert(0, A.ROOT)
    from forecast.station_time import parse_station_local_time
    out = []
    for row in ((rec.get("advisory") or {}).get("rows") or []):
        try:
            inst = parse_station_local_time(row[0]).astimezone(UTC)
            total = float(row[1])
        except (TypeError, ValueError, IndexError):
            continue
        if not math.isfinite(total):
            continue
        key = inst.replace(minute=0, second=0, microsecond=0)
        near = [raw[k] for k in (key, key + dt.timedelta(hours=1)) if k in raw]
        if near:
            out.append((inst, total - max(near)))
    return sorted(out)


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
        raw_all = {t: v.get("ft") for t, v in ra.expand(rec["nwps"]["hourly"])}
        n_bad_raw = sum(1 for v in raw_all.values() if v is not None and not _num(v))
        if n_bad_raw:
            skipped["record with invalid raw NWPS values"] += 1
            continue
        raw = {t: float(v) for t, v in raw_all.items() if v is not None}
        corr_rows = rec.get("advisory_corrections") or []
        if any(not _num(c.get("ft")) for c in corr_rows):
            skipped["record with a missing or invalid recorded anchor"] += 1
            continue
        recorded = sorted((A.parse_utc(c["utc"]), float(c["ft"])) for c in corr_rows)
        rebuilt = rebuilt_anchors(rec, raw)
        anchor_ok = (len(rebuilt) == len(recorded) and all(
            abs((a1 - a2).total_seconds()) <= 60 and abs(c1 - c2) <= CORR_TOL_FT for (a1, c1), (a2, c2) in zip(rebuilt, recorded)))
        if not anchor_ok:
            skipped["recorded anchors disagree with anchors rebuilt from the advisory rows and raw NWPS"] += 1
            continue
        for p in ((f.get("outlook_7d") or {}).get("series") or []):
            src = p.get("surge_source")
            t = A.parse_utc(p["utc"])
            if src not in ("nws_product", "nwps"):
                skipped[f"source {src} (not a raw-NWPS row)"] += 1
                continue
            if t not in raw:
                skipped["target not covered by raw NWPS"] += 1
                continue
            if not _num(p.get("tide_navd88")):
                skipped["invalid or missing published outlook level"] += 1
                continue
            lead = (t - gen).total_seconds() / 3600.0
            if lead <= 0:
                skipped["target not after issuance"] += 1
                continue
            corrected = p["tide_navd88"] - NAVD
            corr_expected, anchored = correction_at(recorded, t)
            corr_seen = corrected - raw[t]
            if abs(corr_seen - corr_expected) > CORR_TOL_FT:
                skipped["published minus raw disagrees with the reconstructed correction"] += 1
                continue
            if (src == "nws_product") != anchored:
                skipped["source label disagrees with the reconstructed anchoring"] += 1
                continue
            ph = phase_of(t, hilo)
            if ph == "UNAVAILABLE":
                skipped["phase unavailable (astronomy coverage)"] += 1
                continue
            pairs.append({"issuance": gen, "target": t, "lead_h": round(lead, 2), "source": src,
                          "corrected_mllw": round(corrected, 4), "uncorrected_mllw": raw[t],
                          "correction_ft": round(corr_expected, 4), "correction_seen_ft": round(corr_seen, 4),
                          "cohort": "ZERO" if abs(corr_expected) < ZERO_FT else "NONZERO", "phase": ph,
                          "replay_line": ident, "recorded_anchors": len(recorded),
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
        elif not _num(o.get("v")):
            p["outcome"], p["outcome_reason"] = None, "invalid outcome value"
        else:
            p["outcome"], p["outcome_reason"] = o["v"], None
        p["outcome_q"] = (o or {}).get("q")
    return pairs


def episodes(issuances, gap_h=EPISODE_GAP_H):
    """One episode while consecutive issuances are < gap_h apart (a gap of
    exactly gap_h starts a new episode; protocol 3)."""
    out, idx, last = {}, -1, None
    for t in sorted(issuances):
        if last is None or (t - last) >= dt.timedelta(hours=gap_h):
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
