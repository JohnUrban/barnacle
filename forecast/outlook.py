#!/usr/bin/env python3
"""7-day outlook: per-tide guidance ladder, day cards, shadow ledger and
promotion scoring (arc opened 2026-09-23; BACKLOG top loop).

Pure functions only: the facade fetches (through outlook_sources.gather)
and passes data in; nothing here touches the network. The outlook is a
NEW field (`outlook_7d`), never a widening of `all_tides`, so alerts,
per-tide pages, the widget and the prediction ledger are untouched.

Two layers on every surface (John, 2026-09-23): the honest astronomical
layer, and a labeled guidance layer whose source and reach are stated.

Surge ladder by lead (first available wins for the central line):
  nws_product   NWS coastal flood product row (matched within 2 h)
  nwps          NWS water-prediction gauge forecast, <= 72 h  (SHADOW)
  petss_mid     midpoint of P-ETSS p10/p90 surge, <= 102 h   (band shown)
  persist_decay this hour's surge decayed toward the trailing mean, tau 36 h (v0.10.6, measured)
  astro         astronomy only, labeled "no surge guidance"
"""

import csv
import datetime as dt
import math
import os

try:
    from .station_time import parse_station_local_time, utc_to_station_local
    from . import outlook_sources as srcs
except ImportError:                      # run as a script from forecast/
    from station_time import parse_station_local_time, utc_to_station_local
    import outlook_sources as srcs

HORIZON_HOURS = 168
NWPS_HORIZON_H = 72
PETSS_HORIZON_H = 102
PRODUCT_MATCH_H = 2.0
PERSISTENCE_DECAY_TAU_H = 36.0     # v0.10.6: measured (surge_decay.SURGE_DECAY_TAU_H); toward the trailing mean
LEAD_BUCKETS = ((0, 24, "0-24 h"), (24, 48, "24-48 h"), (48, 72, "48-72 h"),
                (72, 102, "72-102 h"), (102, 168, "102-168 h"))
REGIME_RANK = {"dry": 0, "cold_lockout": 0, "unknown": 0, "street": 1, "light": 2,
               "moderate": 3, "severe": 4}
READINESS_MIN_N = 28               # distinct observed tides (~two weeks at two per day)
PAIRINGS = (("nwps_mllw", "persist_flat_mllw"), ("nws_product_mllw", "persist_flat_mllw"),
            ("persist_decay_mllw", "persist_flat_mllw"), ("outlook_mllw", "production_mllw"))
LADDER = ("nws_product", "nwps", "petss_mid", "persist_decay")

OUTLOOK_LOG_FIELDS = [
    "generated_utc", "target_tide_time", "lead_h", "astro_mllw",
    "nws_product_mllw", "nwps_mllw", "petss_p10_mllw", "petss_p90_mllw",
    "persist_flat_mllw", "persist_decay_mllw", "production_mllw",
    "production_source", "outlook_mllw", "outlook_source", "qpf6_in",
    "qpf6_source", "pop_pct", "gust_mph", "xcheck_p_half_inch_pct",
    "model_version",
]
SCORED_COLUMNS = ("astro_mllw", "nws_product_mllw", "nwps_mllw",
                  "petss_p10_mllw", "petss_p90_mllw", "persist_flat_mllw",
                  "persist_decay_mllw", "production_mllw", "outlook_mllw")


def _utc(stamp):
    when = dt.datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
    return when if when.tzinfo else when.replace(tzinfo=dt.timezone.utc)


def _r(v, nd=2):
    return None if v is None else round(v, nd)


def _match_production(all_tides, t_utc, tol_min=10):
    for t in all_tides or []:
        try:
            when = parse_station_local_time(t["time"])
        except (KeyError, TypeError, ValueError):
            continue
        if abs((when - t_utc).total_seconds()) <= tol_min * 60:
            return t
    return None


def _bucket_containing(buckets, t_utc):
    """NBM/WPC bucket whose [end - hours, end) window holds t_utc:
    start-inclusive, end-exclusive, matching the forward-step integration
    of simulate_pluvial_series and the NWS-grid lookup (audit R5)."""
    for b in buckets or []:
        end = _utc(b["end_utc"])
        if end - dt.timedelta(hours=b["hours"]) <= t_utc < end:
            return b
    return None


def _overlap_h(s, e, lo, hi):
    """Hours of [s, e) inside [lo, hi)."""
    a, b = max(s, lo), min(e, hi)
    return max(0.0, (b - a).total_seconds() / 3600.0)


def _prorated_day_total(buckets, day_s, day_e, start_key=None):
    """(inches, valid covered hours, explicit-null hours) for a local day from accumulation buckets,
    prorating each bucket by its overlap with the day under the uniform-
    rate assumption (audit R5: mass is conserved across midnight)."""
    total, covered, null_h = 0.0, 0.0, 0.0
    for b in buckets or []:
        if start_key:                       # grid rows: {"start", "hours", "value"}
            s = _utc(b["start"]); e = s + dt.timedelta(hours=b["hours"]); v = b.get("value")
        else:                               # NBM/WPC: {"end_utc", "hours", "qpf_in"}
            e = _utc(b["end_utc"]); s = e - dt.timedelta(hours=b["hours"]); v = b.get("qpf_in")
        ov = _overlap_h(s, e, day_s, day_e)
        if ov <= 0:
            continue
        if v is None:                       # explicit null: unknown hours, never zero rain (round 03 S2)
            null_h += ov
            continue
        total += float(v) * ov / ((e - s).total_seconds() / 3600.0)
        covered += ov
    return round(total, 3), covered, null_h


def _wind_at(grid, t_utc):
    return {"wind_mph": _r(srcs.grid_value_at(grid.get("wind_mph"), t_utc), 0),
            "gust_mph": _r(srcs.grid_value_at(grid.get("gust_mph"), t_utc), 0),
            "dir_deg": srcs.grid_value_at(grid.get("wind_dir_deg"), t_utc)}


def compass(deg):
    if deg is None:
        return None
    pts = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
           "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    return pts[int((float(deg) + 11.25) // 22.5) % 16]


def _rain_at(grid, nbm, wpc, t_utc, lead_h):
    """6-h QPF proxy at a tide: NWS grid inside its reach, else NBM, else
    WPC's 24-h total (labeled). None when nothing covers the hour."""
    if lead_h <= 72:
        v = srcs.grid_value_at(grid.get("qpf_in"), t_utc)
        if v is not None:
            return {"qpf_in": _r(v, 2), "source": "nws_grid", "hours": None}
    b = _bucket_containing(nbm, t_utc)
    if b is not None and b.get("qpf_in") is not None:
        return {"qpf_in": _r(b["qpf_in"], 2), "source": "nbm", "hours": 6}
    b = _bucket_containing(wpc, t_utc)
    if b is not None and b.get("qpf_in") is not None:
        return {"qpf_in": _r(b["qpf_in"], 2), "source": "wpc_24h", "hours": 24}
    return {"qpf_in": None, "source": None, "hours": None}


def build_tides(now_utc, data, all_tides, persisted_surge, classify_fn,
                depths_fn, mllw_to_navd88_offset, surge_mean_ft=0.0):
    astro = (data.get("astro") or {}).get("highs") or []
    grid = (data.get("grid") or {}).get("series") or {}
    nwps = (data.get("nwps") or {}).get("series")
    petss = data.get("petss") or {}
    nbm = (data.get("nbm") or {}).get("buckets") or []
    wpc = (data.get("wpc") or {}).get("buckets") or []
    xcheck = data.get("xcheck") or {}
    tides = []
    for h in astro:
        t_utc = _utc(h["utc"])
        lead = (t_utc - now_utc).total_seconds() / 3600.0
        if lead < -2 or lead > HORIZON_HOURS:
            continue
        astro_mllw = float(h["mllw"])
        g = {}
        prod = _match_production(all_tides, t_utc)
        if prod and prod.get("source") == "nws-coastal-flood-product":
            g["nws_product"] = float(prod["forecast_peak_mllw"])
        if nwps and lead <= NWPS_HORIZON_H:
            v = srcs.series_max_near(nwps, t_utc, PRODUCT_MATCH_H)
            if v is not None:
                g["nwps"] = float(v)
        if petss and lead <= PETSS_HORIZON_H:
            lo = srcs.series_value_nearest(petss.get("p10"), t_utc)
            hi = srcs.series_value_nearest(petss.get("p90"), t_utc)
            if lo is not None and hi is not None:
                g["petss_p10"] = astro_mllw + lo
                g["petss_p90"] = astro_mllw + hi
                g["petss_mid"] = astro_mllw + (lo + hi) / 2.0
        if persisted_surge is not None:
            g["persist_flat"] = astro_mllw + persisted_surge
            g["persist_decay"] = astro_mllw + surge_mean_ft + (persisted_surge - surge_mean_ft) * math.exp(
                -max(lead, 0.0) / PERSISTENCE_DECAY_TAU_H)
        central, central_src = astro_mllw, "astro"
        for src in LADDER:
            if src in g:
                central, central_src = g[src], src
                break
        band_lo, band_hi = g.get("petss_p10"), g.get("petss_p90")
        depths = depths_fn(central) if depths_fn else {}
        rain = _rain_at(grid, nbm, wpc, t_utc, lead)
        local = utc_to_station_local(t_utc)
        xday = (xcheck.get("ensemble") or {}).get(local.strftime("%Y-%m-%d")) or {}
        tides.append({
            "time": h["time"], "utc": h["utc"], "lead_h": _r(lead, 1),
            "astro_mllw": _r(astro_mllw, 2),
            "outlook_mllw": _r(central, 2), "outlook_source": central_src,
            "band_lo_mllw": _r(band_lo, 2), "band_hi_mllw": _r(band_hi, 2),
            "regime": classify_fn(central + mllw_to_navd88_offset),
            "regime_lo": (classify_fn(band_lo + mllw_to_navd88_offset)
                          if band_lo is not None else None),
            "regime_hi": (classify_fn(band_hi + mllw_to_navd88_offset)
                          if band_hi is not None else None),
            "grate_sw_in": _r(depths.get("grate_SW"), 1),
            "curb_in": _r(depths.get("curb"), 1),
            "guidance": {k: _r(v, 2) for k, v in g.items()},
            "production_mllw": (_r(float(prod["forecast_peak_mllw"]), 2)
                                if prod and prod.get("forecast_peak_mllw") is not None else None),
            "production_source": (prod or {}).get("source"),
            "rain": rain,
            "pop_pct": srcs.grid_value_at(grid.get("pop_pct"), t_utc),
            "wind": _wind_at(grid, t_utc),
            "xcheck_p_half_inch_pct": xday.get("p_half_inch_pct"),
            "nbm_p_ge_half_in_6h_pct": ((_bucket_containing(nbm, t_utc) or {}).get("p_ge_half_in_pct")),
        })
    return tides


def _day_label(i, local_date):
    if i == 0:
        return "Today"
    if i == 1:
        return "Tomorrow"
    return local_date.strftime("%A")


def _grid_rows_in_day(series, day_start_utc, day_end_utc):
    out = []
    for row in series or []:
        s = _utc(row["start"])
        e = s + dt.timedelta(hours=row["hours"])
        if e > day_start_utc and s < day_end_utc and row["value"] is not None:
            out.append((s, e, row["value"]))
    return out


def build_days(now_utc, tides, data):
    grid = (data.get("grid") or {}).get("series") or {}
    nbm = (data.get("nbm") or {}).get("buckets") or []
    wpc = (data.get("wpc") or {}).get("buckets") or []
    xcheck = data.get("xcheck") or {}
    grid_reach = _utc((data.get("grid") or {}).get("reach", {}).get("qpf_in")) \
        if (data.get("grid") or {}).get("reach", {}).get("qpf_in") else None
    local_now = utc_to_station_local(now_utc)
    horizon_end = series_end_utc(now_utc)
    local_end = utc_to_station_local(horizon_end)
    days = []
    n_days = (local_end.date() - local_now.date()).days + 1     # every calendar date the horizon touches
    for i in range(n_days):
        d = (local_now + dt.timedelta(days=i)).date()
        start_local = dt.datetime(d.year, d.month, d.day, tzinfo=local_now.tzinfo)
        end_local = start_local + dt.timedelta(days=1)
        s_utc, e_utc = start_local.astimezone(dt.timezone.utc), end_local.astimezone(dt.timezone.utc)
        # hours of this calendar date inside [now, now+168 h): first/last cards are partial
        in_scope_h = _overlap_h(s_utc, e_utc, now_utc, horizon_end)
        day_tides = [t for t in tides if t["time"][:10] == d.isoformat() and t["lead_h"] >= -2]
        worst = max(day_tides, key=lambda t: (REGIME_RANK.get(t["regime"], 0), t["outlook_mllw"]), default=None)
        # rain amount for the local day, PRORATED by each bucket's overlap with
        # the day (audit R5): NWS grid when it covers the whole day, else NBM,
        # else WPC; the covered hours are reported with the source.
        day_h = (e_utc - s_utc).total_seconds() / 3600.0
        qpf, qsrc, qcov, qnull = None, None, 0.0, 0.0
        if grid_reach is not None and e_utc <= grid_reach:
            # the NWS grid lists only intervals with rain: inside its reach,
            # ABSENT hours are dry; an interval carrying an explicit null is
            # unknown and reduces the covered hours (round 03 S2)
            tot, cov, nul = _prorated_day_total(grid.get("qpf_in"), s_utc, e_utc, start_key="start")
            qpf, qsrc, qcov, qnull = round(tot, 2), "nws_grid", day_h - nul, nul
        if qpf is None:
            tot, cov, nul = _prorated_day_total(nbm, s_utc, e_utc)
            if cov >= 12.0:
                qpf, qsrc, qcov, qnull = round(tot, 2), "nbm", cov, nul
        if qpf is None:
            tot, cov, nul = _prorated_day_total(wpc, s_utc, e_utc)
            if cov >= 12.0:
                qpf, qsrc, qcov, qnull = round(tot, 2), "wpc_24h", cov, nul
        pops = [v for _, _, v in _grid_rows_in_day(grid.get("pop_pct"), s_utc, e_utc)]
        gusts = _grid_rows_in_day(grid.get("gust_mph"), s_utc, e_utc)
        gust_max = max((v for _, _, v in gusts), default=None)
        gust_dir = None
        if gust_max is not None:
            when = next(s for s, _, v in gusts if v == gust_max)
            gust_dir = compass(srcs.grid_value_at(grid.get("wind_dir_deg"), when))
        day_b = [b for b in nbm if _overlap_h(_utc(b["end_utc"]) - dt.timedelta(hours=b["hours"]),
                                              _utc(b["end_utc"]), s_utc, e_utc) > 0]
        nbm_pops = [b["pop_pct"] for b in day_b if b.get("pop_pct") is not None]
        nbm_band = None
        if any(b.get("p90_in") is not None for b in day_b):
            def _sum(key):
                vals = [b[key] for b in day_b if b.get(key) is not None]
                return round(sum(vals), 2) if vals else None
            def _max(key):
                vals = [b[key] for b in day_b if b.get(key) is not None]
                return max(vals) if vals else None
            nbm_band = {
                # sums of MARGINAL 6-h percentiles, not percentiles of the daily
                # sum (audit R12); displayed nowhere as a daily percentile
                "p10_6h_sum_in": _sum("p10_in"), "p50_6h_sum_in": _sum("p50_in"),
                "p90_6h_sum_in": _sum("p90_in"),
                "p90_6h_max_in": _max("p90_in"),
                "p_ge_quarter_in_6h_max_pct": _max("p_ge_quarter_in_pct"),
                "p_ge_half_in_6h_max_pct": _max("p_ge_half_in_pct"),
                "p_ge_1in_6h_max_pct": _max("p_ge_1in_pct"),
                "buckets": len(day_b),
            }
        days.append({
            "date": d.isoformat(), "label": _day_label(i, d),
            "hours_in_scope": round(in_scope_h, 1), "partial": in_scope_h < 23.0,
            "tides": [{"time": t["time"][11:16], "outlook_mllw": t["outlook_mllw"],
                       "astro_mllw": t["astro_mllw"], "regime": t["regime"],
                       "source": t["outlook_source"]} for t in day_tides],
            "astro_max_mllw": max((t["astro_mllw"] for t in day_tides), default=None),
            "outlook_max_mllw": worst["outlook_mllw"] if worst else None,
            "outlook_source": worst["outlook_source"] if worst else None,
            "regime_max": worst["regime"] if worst else "dry",
            "band_hi_max_mllw": max((t["band_hi_mllw"] for t in day_tides
                                     if t["band_hi_mllw"] is not None), default=None),
            "regime_hi_max": max((t["regime_hi"] for t in day_tides if t["regime_hi"]),
                                 key=lambda r: REGIME_RANK.get(r, 0), default=None),
            "qpf_in": qpf, "qpf_source": qsrc, "qpf_covered_h": round(qcov, 1),
            "qpf_null_h": round(qnull, 1), "qpf_partial": (qpf is not None and qcov < day_h - 0.5),
            "pop_max_pct": max(pops, default=None),
            "nbm_pop_max_pct": max(nbm_pops, default=None),
            "gust_max_mph": _r(gust_max, 0), "gust_dir": gust_dir,
            "nbm_band": nbm_band,
            "xcheck_models": (xcheck.get("models") or {}).get(d.isoformat()),
            "xcheck_ensemble": (xcheck.get("ensemble") or {}).get(d.isoformat()),
        })
    return days


# ---------------------------------------------------------------------------
# continuous series: tide + guidance surge, and the RAIN PATHWAY through the
# production tank (rain doctrine: never deferred, never subordinate to tide)
# ---------------------------------------------------------------------------
BURST_RATE_FLAG_IN_HR = 0.15      # production rule: an hour >= this is burst-capable
BURST_ANALOG_MAX_IN_HR = 3.0
BURST_LOW_TIDE_BAY_NAVD88 = 2.5   # production convention for the potential level


def _surge_knots(tides):
    knots = []
    for t in tides:
        if t.get("outlook_mllw") is None or t.get("astro_mllw") is None:
            continue
        knots.append((_utc(t["utc"]), t["outlook_mllw"] - t["astro_mllw"],
                      t["outlook_source"]))
    return sorted(knots)


def _surge_at(knots, t_utc):
    """Linear interpolation of the per-tide guidance surge between tides;
    held flat before the first and after the last knot."""
    if not knots:
        return 0.0, "astro"
    if t_utc <= knots[0][0]:
        return knots[0][1], knots[0][2]
    if t_utc >= knots[-1][0]:
        return knots[-1][1], knots[-1][2]
    for (t1, s1, src1), (t2, s2, src2) in zip(knots, knots[1:]):
        if t1 <= t_utc <= t2:
            f = (t_utc - t1).total_seconds() / max(1.0, (t2 - t1).total_seconds())
            return s1 + (s2 - s1) * f, (src1 if f < 0.5 else src2)
    return knots[-1][1], knots[-1][2]


ANCHOR_FADE_H = 6.0
ANCHOR_HOLD_H = 1.0


def _product_anchors(tides, nwps_by_hour):
    """(instant, product_mllw - nwps_mllw) for every tide whose ladder source
    is the CFW product and whose hour NWPS covers."""
    out = []
    for t in tides:
        if t.get("outlook_source") != "nws_product" or t.get("outlook_mllw") is None:
            continue
        inst = _utc(t["utc"])
        key = inst.replace(minute=0, second=0, microsecond=0)
        near = [nwps_by_hour[k] for k in (key, key + dt.timedelta(hours=1)) if k in nwps_by_hour]
        if not near:
            continue
        out.append((inst, float(t["outlook_mllw"]) - max(near)))
    return sorted(out)


def _anchor_correction(anchors, t_utc):
    """Additive correction at t: linear between consecutive anchors, fading to
    zero over ANCHOR_FADE_H beyond the first/last anchor. (value, anchored)."""
    if not anchors:
        return 0.0, False
    def fade(gap_h):
        # full correction within ANCHOR_HOLD_H of the anchor, then linear to 0
        return max(0.0, 1.0 - max(0.0, gap_h - ANCHOR_HOLD_H) / ANCHOR_FADE_H)
    if t_utc <= anchors[0][0]:
        w = fade((anchors[0][0] - t_utc).total_seconds() / 3600.0)
        return anchors[0][1] * w, w > 0
    if t_utc >= anchors[-1][0]:
        w = fade((t_utc - anchors[-1][0]).total_seconds() / 3600.0)
        return anchors[-1][1] * w, w > 0
    for (t1, c1), (t2, c2) in zip(anchors, anchors[1:]):
        if t1 <= t_utc <= t2:
            f = (t_utc - t1).total_seconds() / max(1.0, (t2 - t1).total_seconds())
            return c1 + (c2 - c1) * f, True
    return 0.0, False


def _hourly_rain_lookup(qpf_hourly, nbm, wpc):
    prod = {}
    for tt, rate in qpf_hourly or []:
        try:
            prod[tt.astimezone(dt.timezone.utc).replace(minute=0, second=0, microsecond=0)] = float(rate)
        except Exception:
            continue

    def at(t_utc):
        key = t_utc.replace(minute=0, second=0, microsecond=0)
        if key in prod:
            return prod[key], "nws_grid"
        b = _bucket_containing(nbm, t_utc)
        if b is not None and b.get("qpf_in") is not None:
            return b["qpf_in"] / float(b["hours"]), "nbm"
        b = _bucket_containing(wpc, t_utc)
        if b is not None and b.get("qpf_in") is not None:
            return b["qpf_in"] / float(b["hours"]), "wpc_24h"
        return None, None
    return at


def _burst_hours(nws_hourly, qpf_hourly, nbm):
    """Station-local 'YYYY-MM-DD HH' keys that are burst-capable, by the
    production rule (PoP >= 60 with thunder/heavy-rain wording, PoP >= 80,
    or a rate >= 0.15 in/hr), extended over the whole hourly forecast and
    the NBM buckets."""
    hours = set()
    convective_days = set()
    for p in nws_hourly or []:
        try:
            tt = _utc(p["startTime"])
        except (KeyError, ValueError, TypeError):
            continue
        local = utc_to_station_local(tt)
        pop = ((p.get("probabilityOfPrecipitation") or {}).get("value")) or 0
        sf = (p.get("shortForecast") or "").lower()
        conv = pop >= 60 and ("thunder" in sf or "heavy rain" in sf)
        if conv or pop >= 80:
            hours.add(local.strftime("%Y-%m-%d %H"))
        if conv:
            convective_days.add(local.strftime("%Y-%m-%d"))
    for tt, rate in qpf_hourly or []:
        if rate is not None and rate >= BURST_RATE_FLAG_IN_HR:
            hours.add(utc_to_station_local(tt).strftime("%Y-%m-%d %H"))
    for b in nbm or []:
        if b.get("qpf_in") is not None and b["qpf_in"] / float(b["hours"]) >= BURST_RATE_FLAG_IN_HR:
            end = _utc(b["end_utc"])
            for h in range(int(b["hours"])):
                hours.add(utc_to_station_local(end - dt.timedelta(hours=h + 1)).strftime("%Y-%m-%d %H"))
    return hours, convective_days


def series_end_utc(now_utc):
    """Rolling horizon: now + HORIZON_HOURS (audit round 03 S3: the declared
    168 h, the series, the tide table and the slider share one scope)."""
    return now_utc + dt.timedelta(hours=HORIZON_HOURS)


def build_series(now_utc, data, tides, nws_hourly, qpf_hourly, simulate_fn,
                 mllw_to_navd88_offset, enhancement_ft):
    """Hourly points from -6 h to +168 h:
    tide_navd88 = astro + guidance surge (NWPS hourly inside its reach,
    else the per-tide ladder interpolated), pluvial_navd88 from the
    production tank driven by NWS-grid / NBM / WPC rain, water = max."""
    hourly = (data.get("astro_hourly") or {}).get("points") or []
    if not hourly:
        return []
    nwps = (data.get("nwps") or {}).get("series") or []
    nwps_by_hour = {_utc(p["utc"]).replace(minute=0, second=0, microsecond=0): p["ft"] for p in nwps}
    nbm = (data.get("nbm") or {}).get("buckets") or []
    wpc = (data.get("wpc") or {}).get("buckets") or []
    knots = _surge_knots(tides)
    anchors = _product_anchors(tides, nwps_by_hour)
    rain_at = _hourly_rain_lookup(qpf_hourly, nbm, wpc)
    burst_hours, _conv = _burst_hours(nws_hourly, qpf_hourly, nbm)
    lo = now_utc - dt.timedelta(hours=6)
    # The series runs the full rolling horizon (round 03 S3); every calendar
    # date it touches gets a card (audit R3: no tail without a card).
    hi = series_end_utc(now_utc)
    times, tide_w, rates, pts = [], [], [], []
    for p in hourly:
        t = _utc(p["utc"])
        if t < lo or t >= hi:            # end exclusive: no eighth-date point
            continue
        astro = float(p["mllw"])
        key = t.replace(minute=0, second=0, microsecond=0)
        lead = (t - now_utc).total_seconds() / 3600.0
        if key in nwps_by_hour and lead <= NWPS_HORIZON_H:
            # NWPS supplies the hourly SHAPE; the CFW product rows stay the
            # anchor (audit R8): an additive correction interpolated between
            # product-anchored tides pulls the curve through each row.
            corr, csrc = _anchor_correction(anchors, t)
            total, src = float(nwps_by_hour[key]) + corr, ("nws_product" if csrc else "nwps")
        else:
            sg, src = _surge_at(knots, t)
            total = astro + sg
        tide_navd = total + enhancement_ft + mllw_to_navd88_offset
        rate, rsrc = rain_at(t)
        times.append(t)
        tide_w.append(tide_navd)
        rates.append(rate if rate is not None else 0.0)
        pts.append({"time": p["time"], "utc": p["utc"], "lead_h": _r(lead, 1),
                    "astro_mllw": _r(astro, 3), "tide_navd88": _r(tide_navd, 3),
                    "surge_source": src, "rain_in_hr": _r(rate, 3),
                    "rain_source": rsrc,
                    # R3: an hour with no rain forecast is UNKNOWN, not dry;
                    # the tank runs with 0 for it, and every consumer sees
                    # the flag (water_navd88 there is tide-only).
                    "rain_unknown": rate is None,
                    "burst_risk": p["time"][:13] in burst_hours})
    pluv = simulate_fn(times, tide_w, rates) if simulate_fn and len(times) >= 2 else [None] * len(times)
    for pt, tw, pv in zip(pts, tide_w, pluv):
        pt["pluvial_navd88"] = _r(pv, 3) if pv is not None else None
        pt["water_navd88"] = _r(max(tw, pv) if pv is not None else tw, 3)
    return pts


def add_rain_pathway(days, series, nws_hourly, potential_fn, classify_fn):
    """Per day: the tank line's peak, the burst scenario and its potential
    level, the rain regime, and the CROSS-PATHWAY headline (worst of tidal
    and rain). The tide never gates the rain pathway."""
    _hours, convective_days = _burst_hours(nws_hourly, [], [])
    for d in days:
        pts = [p for p in series if p["time"][:10] == d["date"]]
        known = [p for p in pts if not p.get("rain_unknown")]
        coverage = (len(known) / len(pts)) if pts else 0.0
        rated = [(_utc(p["utc"]), p["rain_in_hr"]) for p in known if p.get("rain_in_hr") is not None]
        rates = [r for _, r in rated]
        peak_rate = max(rates, default=0.0)
        # max 6-h accumulation over TIMESTAMPED windows (a gap can never make
        # six samples span more than six hours); incomplete windows are flagged
        max_6h, window_complete = 0.0, True
        for t0, _r0 in rated:
            win = [r for t, r in rated if t0 <= t < t0 + dt.timedelta(hours=6)]
            acc = sum(win)
            if acc > max_6h:
                max_6h, window_complete = acc, len(win) >= 6
        pluv_vals = [p["pluvial_navd88"] for p in pts if p.get("pluvial_navd88") is not None]
        pluv_peak = max(pluv_vals, default=None)
        pluv_peak_time = None
        if pluv_peak is not None:
            pluv_peak_time = next(p["time"][11:16] for p in pts if p.get("pluvial_navd88") == pluv_peak)
        water_peak = max((p["water_navd88"] for p in pts if p.get("water_navd88") is not None), default=None)
        burst_signal = (d["date"] in convective_days) or any(p["burst_risk"] for p in pts)
        burst_est = peak_rate
        if burst_signal:
            analog = 1.7 * (max_6h / 0.55) if max_6h > 0 else 1.7
            burst_est = max(burst_est, min(analog, BURST_ANALOG_MAX_IN_HR))
        potential = None
        if burst_est > 0.1 and potential_fn:
            pots = [v for v in potential_fn(burst_est, BURST_LOW_TIDE_BAY_NAVD88) if v is not None]
            potential = max(pots) if pots else None

        def _pot_at(rate, bay):
            if rate is None or rate <= 0.1 or not potential_fn or bay is None:
                return None
            vals = [v for v in potential_fn(rate, max(bay, BURST_LOW_TIDE_BAY_NAVD88)) if v is not None]
            return max(vals) if vals else None
        # COMPOUND (John 2026-09-23): the burst evaluated at each burst-capable
        # hour's OWN tide level (the tank sits on the bay), and at the day's
        # highest tide. The low-tide figure above stays as the rain-alone view.
        high_tide = max((p["tide_navd88"] for p in pts if p.get("tide_navd88") is not None), default=None)
        compound = _pot_at(burst_est, high_tide) if burst_signal else None
        for p in pts:
            if p.get("burst_risk") and burst_est > 0.1:
                p["burst_potential_navd88"] = _r(_pot_at(burst_est, p.get("tide_navd88")), 3)
        # NBM 90th-percentile scenario (NOAA probabilistic rain): the rain
        # band's HIGH END, labeled, shown beside its exceedance chance. It
        # does not drive the headline (the P-ETSS high end does not either).
        band = d.get("nbm_band") or {}
        p90_6h = band.get("p90_6h_max_in")
        p90_est = p90_pot = p90_compound = None
        if p90_6h:
            p90_est = min(1.7 * (p90_6h / 0.55), BURST_ANALOG_MAX_IN_HR)
            if p90_est > 0.1 and potential_fn:
                pots = [v for v in potential_fn(p90_est, BURST_LOW_TIDE_BAY_NAVD88) if v is not None]
                p90_pot = max(pots) if pots else None
                p90_compound = _pot_at(p90_est, high_tide)
        # R3: with no rain forecast for the day the rain regimes are UNKNOWN,
        # never "dry"; with partial coverage they are labeled partial.
        if coverage == 0.0:
            rain_regime = burst_regime = "unknown"
        else:
            rain_regime = classify_fn(pluv_peak) if pluv_peak is not None else "dry"
            burst_regime = classify_fn(potential) if potential is not None else "dry"
        p90_regime = classify_fn(p90_pot) if p90_pot is not None else None
        tidal_regime = d.get("regime_max") or "dry"
        compound_regime = classify_fn(compound) if compound is not None else "dry"
        candidates = [(REGIME_RANK.get(tidal_regime, 0), tidal_regime, "tide"),
                      (REGIME_RANK.get(rain_regime, 0), rain_regime, "rain (tank line)"),
                      (REGIME_RANK.get(burst_regime, 0), burst_regime, "rain (burst scenario)"),
                      (REGIME_RANK.get(compound_regime, 0), compound_regime, "rain burst on the high tide")]
        rank, regime, pathway = max(candidates)
        d.update({
            "rain_pathway": {
                "peak_rate_in_hr": _r(peak_rate, 2), "max_6h_in": _r(max_6h, 2),
                "max_6h_window_complete": window_complete,
                "tank_peak_navd88": _r(pluv_peak, 2), "tank_peak_time": pluv_peak_time,
                "tank_regime": rain_regime,
                "burst_signal": burst_signal, "burst_est_in_hr": _r(burst_est, 2),
                "burst_potential_navd88": _r(potential, 2), "burst_regime": burst_regime,
                "nbm_p90_6h_in": _r(p90_6h, 2), "nbm_p90_est_in_hr": _r(p90_est, 2),
                "nbm_p90_potential_navd88": _r(p90_pot, 2), "nbm_p90_regime": p90_regime,
                "high_tide_navd88": _r(high_tide, 2),
                "burst_at_high_tide_navd88": _r(compound, 2),
                "burst_at_high_tide_regime": classify_fn(compound) if compound is not None else None,
                "nbm_p90_at_high_tide_navd88": _r(p90_compound, 2),
                "nbm_p90_at_high_tide_regime": classify_fn(p90_compound) if p90_compound is not None else None,
                "nbm_p_ge_half_in_6h_pct": band.get("p_ge_half_in_6h_max_pct"),
                "nbm_p_ge_1in_6h_pct": band.get("p_ge_1in_6h_max_pct"),
                "rain_available": coverage > 0.0,
                "rain_coverage": round(coverage, 2),
                "rain_known_hours": len(known), "rain_hours": len(pts),
            },
            "tidal_regime_max": tidal_regime,
            "water_peak_navd88": _r(water_peak, 2),
            "regime_max": regime,
            "worst_pathway": pathway,
        })
    return days


def worst_points(series, days):
    """The two map buttons: worst TIDE (bay water) and worst FLOOD CHANCE
    (tide, tank line, or a burst scenario, whichever is highest)."""
    future = [p for p in series if (p.get("lead_h") or 0) >= 0]   # audit R6: never history
    if not future:
        return {}
    pot_by_day = {d["date"]: (d.get("rain_pathway") or {}).get("burst_potential_navd88")
                  for d in days}
    wt = max(future, key=lambda p: p["tide_navd88"])
    best = None
    for p in future:
        lvl, path = p["water_navd88"], ("rain (tank line)" if p.get("pluvial_navd88") is not None
                                        and p["pluvial_navd88"] >= p["tide_navd88"] else "tide")
        pot = p.get("burst_potential_navd88")
        if pot is None:
            pot = pot_by_day.get(p["time"][:10])
        if p.get("burst_risk") and pot is not None and pot > lvl:
            lvl, path = pot, "rain (burst scenario)"
        if best is None or lvl > best[0]:
            best = (lvl, p["time"], path)
    return {"tide": {"time": wt["time"], "navd88": wt["tide_navd88"]},
            "flood_chance": {"time": best[1], "navd88": _r(best[0], 3), "pathway": best[2]},
            "burst_potential_by_day": pot_by_day}


def build_outlook_7d(now_utc, data, health, all_tides, persisted_surge,
                     surge_age_min, classify_fn, depths_fn,
                     mllw_to_navd88_offset, model_version, shadow=None,
                     nws_hourly=None, qpf_hourly=None, simulate_fn=None,
                     potential_fn=None, enhancement_ft=0.0, surge_mean_ft=0.0):
    tides = build_tides(now_utc, data, all_tides, persisted_surge,
                        classify_fn, depths_fn, mllw_to_navd88_offset,
                        surge_mean_ft=surge_mean_ft)
    days = build_days(now_utc, tides, data)
    series = build_series(now_utc, data, tides, nws_hourly, qpf_hourly,
                          simulate_fn, mllw_to_navd88_offset, enhancement_ft)
    days = add_rain_pathway(days, series, nws_hourly, potential_fn, classify_fn)
    worst = worst_points(series, days)
    petss = data.get("petss") or {}
    nwps = data.get("nwps") or {}
    nbm = data.get("nbm") or {}
    return {
        "generated_utc": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "horizon_hours": HORIZON_HOURS,
        "model_version": model_version,
        "sources": health,
        "reach": {
            "nws_product_h": 72, "nwps_h": NWPS_HORIZON_H, "petss_h": PETSS_HORIZON_H,
            "grid_qpf_end_utc": ((data.get("grid") or {}).get("reach") or {}).get("qpf_in"),
            "grid_wind_end_utc": ((data.get("grid") or {}).get("reach") or {}).get("gust_mph"),
            "nbm_cycle": nbm.get("cycle"), "petss_cycle": petss.get("cycle"),
            "nwps_issued": nwps.get("issued"),
        },
        "assumptions": {
            "persistence_decay_tau_h": PERSISTENCE_DECAY_TAU_H,
            "persistence_decay_mean_ft": _r(surge_mean_ft, 3),
            "persisted_surge_ft": _r(persisted_surge, 3),
            "persisted_surge_age_min": surge_age_min,
            "petss_central": "midpoint of the p10/p90 surge band",
            "shadow": ("NWPS gauge forecast and P-ETSS are guidance only; production "
                       "surge stays product-or-persistence until the shadow ledger "
                       "shows a lower error (BACKLOG DECISION nwps-gauge-forecast-shadow)"),
        },
        "tides": tides,
        "days": days,
        "series": series,
        "worst": worst,
        "shadow": shadow,
    }


# ---------------------------------------------------------------------------
# shadow ledger (append-only, strict CSV, gate-checked)
# ---------------------------------------------------------------------------
def _fmt(v, nd=3):
    if v is None or v == "":
        return ""
    if isinstance(v, float):
        return f"{v:.{nd}f}"
    return str(v)


def outlook_log_rows(outlook, generated_utc, model_version):
    rows = []
    for t in outlook.get("tides") or []:
        if t["lead_h"] is None or t["lead_h"] < 0:
            continue
        g = t.get("guidance") or {}
        rain = t.get("rain") or {}
        rows.append({
            "generated_utc": generated_utc,
            "target_tide_time": t["time"],
            "lead_h": _fmt(float(t["lead_h"]), 1),
            "astro_mllw": _fmt(t["astro_mllw"]),
            "nws_product_mllw": _fmt(g.get("nws_product")),
            "nwps_mllw": _fmt(g.get("nwps")),
            "petss_p10_mllw": _fmt(g.get("petss_p10")),
            "petss_p90_mllw": _fmt(g.get("petss_p90")),
            "persist_flat_mllw": _fmt(g.get("persist_flat")),
            "persist_decay_mllw": _fmt(g.get("persist_decay")),
            "production_mllw": _fmt(t.get("production_mllw")),
            "production_source": t.get("production_source") or "",
            "outlook_mllw": _fmt(t["outlook_mllw"]),
            "outlook_source": t["outlook_source"],
            "qpf6_in": _fmt(rain.get("qpf_in")),
            "qpf6_source": rain.get("source") or "",
            "pop_pct": _fmt(t.get("pop_pct"), 0),
            "gust_mph": _fmt((t.get("wind") or {}).get("gust_mph"), 0),
            "xcheck_p_half_inch_pct": _fmt(t.get("xcheck_p_half_inch_pct"), 0),
            "model_version": model_version,
        })
    return rows


def append_outlook_log(path, rows):
    """Strict append. A header mismatch raises so the ship chain fails
    loudly (rule 11) instead of writing a mixed-schema ledger."""
    exists = os.path.exists(path) and os.path.getsize(path) > 0
    if exists:
        with open(path, newline="") as f:
            header = next(csv.reader(f, strict=True), None)
        if header != OUTLOOK_LOG_FIELDS:
            raise ValueError(f"{path}: header {header} != schema")
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=OUTLOOK_LOG_FIELDS, lineterminator="\n",
                           quoting=csv.QUOTE_MINIMAL, strict=True)
        if not exists:
            w.writeheader()
        for r in rows:
            w.writerow(r)
    return len(rows)


def read_outlook_log(path):
    try:
        with open(path, newline="") as f:
            return list(csv.DictReader(f, strict=True))
    except (OSError, ValueError):
        return []


# ---------------------------------------------------------------------------
# promotion scoring: does guidance beat production persistence?
# ---------------------------------------------------------------------------
def _lead_bucket(lead):
    for lo, hi, label in LEAD_BUCKETS:
        if lo <= lead < hi:
            return label
    return None


def score_shadow(rows, observed_by_time):
    """MAE / bias per source per lead bucket, plus promotion readiness.

    Scoring unit (round 03 S1, predeclared): one ISSUED FORECAST of one
    tide. Absolute errors are averaged within each tide FIRST (a +1/-1 pair
    scores 1.0, never 0), then across tides with equal weight; signed errors
    are averaged the same way for bias. Candidate and baseline are paired
    only on the SAME ROW (same issuance, same target), so disjoint
    opportunities are never compared. `n` = distinct tides; `n_obs` =
    tide-bucket pairs; `n_forecasts` = paired rows. READY needs
    READINESS_MIN_N distinct tides and a lower MAE.
    """
    abs_by, sgn_by, pair_by = {}, {}, {}
    for r in rows:
        obs = observed_by_time.get(r.get("target_tide_time"))
        if obs is None:
            continue
        try:
            lead = float(r.get("lead_h") or "")
        except ValueError:
            continue
        b = _lead_bucket(lead)
        if b is None:
            continue
        tide = r["target_tide_time"]
        errs = {}
        for col in SCORED_COLUMNS:
            v = r.get(col)
            if v in (None, ""):
                continue
            try:
                errs[col] = float(v) - obs
            except ValueError:
                continue
        for col, e in errs.items():
            abs_by.setdefault((b, col), {}).setdefault(tide, []).append(abs(e))
            sgn_by.setdefault((b, col), {}).setdefault(tide, []).append(e)
        for a, c in PAIRINGS:
            if a in errs and c in errs:                       # same issuance only
                pair_by.setdefault((b, a, c), {}).setdefault(tide, []).append((abs(errs[a]), abs(errs[c])))

    def _mean(v):
        return sum(v) / len(v)

    buckets = []
    for lo, hi, label in LEAD_BUCKETS:
        srcs_out = {}
        for col in SCORED_COLUMNS:
            per_tide = abs_by.get((label, col)) or {}
            if not per_tide:
                continue
            tide_mae = [_mean(v) for v in per_tide.values()]
            tide_bias = [_mean(v) for v in sgn_by[(label, col)].values()]
            srcs_out[col.replace("_mllw", "")] = {
                "n": len(tide_mae), "n_forecasts": sum(len(v) for v in per_tide.values()),
                "mae": round(_mean(tide_mae), 3), "bias": round(_mean(tide_bias), 3)}
        buckets.append({"label": label, "sources": srcs_out})

    def pairwise(a, c, max_lead):
        tides, per_tide_pairs, n_rows = set(), [], 0
        for lo, _hi, label in LEAD_BUCKETS:
            if lo >= max_lead:
                continue
            for tide, pairs in (pair_by.get((label, a, c)) or {}).items():
                tides.add(tide)
                n_rows += len(pairs)
                per_tide_pairs.append((_mean([x for x, _ in pairs]), _mean([y for _, y in pairs])))
        if not per_tide_pairs:
            return {"n": 0, "n_obs": 0, "n_forecasts": 0, "verdict": "NO DATA YET",
                    "mae_candidate": None, "mae_baseline": None}
        ma = _mean([x for x, _ in per_tide_pairs])
        mb = _mean([y for _, y in per_tide_pairs])
        n_tides = len(tides)
        if n_tides < READINESS_MIN_N:
            verdict = f"NOT YET ({n_tides}/{READINESS_MIN_N} scored tides)"
        elif ma < mb:
            verdict = "READY: candidate beats baseline"
        else:
            verdict = "NOT BETTER: baseline wins so far"
        return {"n": n_tides, "n_obs": len(per_tide_pairs), "n_forecasts": n_rows,
                "mae_candidate": round(ma, 3), "mae_baseline": round(mb, 3), "verdict": verdict}

    scored_tides = len({tide for (b, col), d in abs_by.items() if col == "outlook_mllw" for tide in d})
    scored_rows = sum(len(v) for (b, col), d in abs_by.items() if col == "outlook_mllw" for v in d.values())
    return {
        "scored_rows": scored_rows,
        "scored_tides": scored_tides,
        "sampling": ("unit = one issued forecast of one tide; absolute errors averaged within a tide, "
                     "then across tides; candidate and baseline paired on the same issuance row"),
        "buckets": buckets,
        "readiness": {
            "nwps_vs_persistence_le72h": pairwise("nwps_mllw", "persist_flat_mllw", 72),
            "product_vs_persistence_le72h": pairwise("nws_product_mllw", "persist_flat_mllw", 72),
            "decay_vs_flat_persistence_le168h": pairwise("persist_decay_mllw", "persist_flat_mllw", 168),
            "outlook_vs_production_le72h": pairwise("outlook_mllw", "production_mllw", 72),
        },
    }
