#!/usr/bin/env python3
"""Gauge provenance and QC for the 2026-09-25..27 storm (audit 2026-09-27-a1 R4).

Reads the raw GMT/MLLW archives in gauge-sources/ (quality flags retained),
converts display times with the shared station-time helpers, and writes
gauge_qc.json with:
  * per-tide Sandy Hook and Battery peaks with FLAT-PEAK INTERVALS
    (samples within a tolerance of the maximum), not a single minute;
  * corner-vs-gauge lag as an INTERVAL (gauge flat peak vs corner crest
    window) for each measured flood;
  * a spike screen: 6-min Sandy Hook steps >= 1 ft that The Battery does
    not echo (PLAYBOOK step 2), plus the production despike verdict;
  * the committed gauge_cache.json (lst_ldt NAVD, no flags, no retrieval
    time) compared against the archived preliminary series;
  * the 2026-09-27 nowcast bay inputs (02:40 local day-max origin) against
    the archived series.
Quality: NOAA 'p' = preliminary. Nothing here is a street measurement.
Run: ~/.barnacle/venv/bin/python event10_gauge_qc.py
"""
import csv
import datetime as dt
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO))
from forecast import flood_forecast_daily as ff  # noqa: E402
sys.path.insert(0, str(HERE))
from station_datums import mllw_to_navd88_offset  # noqa: E402

MLLW_TO_NAVD = ff.MLLW_TO_NAVD88_OFFSET   # -2.82 ft, Sandy Hook (production constant)
OFFSET = {"sandy-hook": mllw_to_navd88_offset("8531680"),   # -2.82
          "battery": mllw_to_navd88_offset("8518750")}      # -2.77 (round 05 R6)
assert OFFSET["sandy-hook"] == MLLW_TO_NAVD
SRC = HERE / "gauge-sources"
CACHE = REPO / "assets/observations/2026-09-26/analysis/gauge_cache.json"
LEDGER = REPO / "data/labeled_observations.csv"
FLAT_TOL_FT = 0.03

TIDES = [  # episode, station-local window (offset-bearing via helpers)
    ("2026-09-25-e01", "2026-09-25 17:00", "2026-09-26 00:30"),
    ("2026-09-26-e01", "2026-09-26 04:00", "2026-09-26 13:30"),
    ("2026-09-26-e02", "2026-09-26 17:30", "2026-09-27 00:00"),
    ("2026-09-27-e01", "2026-09-27 04:00", "2026-09-27 13:30"),
]
# corner crest windows from the ledger/README (tape plateau, local)
CORNER_CREST = {
    "2026-09-26-e01": ("2026-09-26 09:06", "2026-09-26 09:13", 5.701),
    "2026-09-26-e02": ("2026-09-26 22:11", "2026-09-26 22:29", 4.223),
    "2026-09-27-e01": ("2026-09-27 09:44", "2026-09-27 10:06", 5.618),
}
# nowcast.json history (git) for the 39.0-in day-max trace
NOWCAST_BAY_INPUTS = [
    ("62a848d5f", "2026-09-27T05:31:07Z", 4.633, "observed", 14.8),
    ("67b031d52", "2026-09-27T05:42:42Z", 4.633, "observed", 15.1),
    ("3e70b6108", "2026-09-27T05:50:25Z", 4.633, "observed", 15.2),
    ("a5020b395", "2026-09-27T06:33:11Z", 5.667, "observed", 26.7),
    ("5f80bcf04", "2026-09-27T06:54:48Z", 6.677, "observed", 38.9),
    ("e5c15508c", "2026-09-27T07:21:55Z", 6.625, "observed", 37.8),
    ("68c86c575", "2026-09-27T07:55:19Z", 0.325, "observed", None),
]


def latest(prefix):
    files = sorted(SRC.glob(f"{prefix}-*Z.json"))
    assert files, f"no archive for {prefix}"
    path = files[-1]
    req = json.loads(path.with_name(path.stem + "-request.json").read_text())
    rows = json.loads(path.read_text())["data"]
    offset = OFFSET[prefix]
    series = []
    for r in rows:
        if not r.get("v"):
            continue
        t_local = ff.noaa_gmt_to_station_time(r["t"])
        series.append({"gmt": r["t"], "local": t_local.isoformat(" ", "minutes"),
                       "_t": t_local, "mllw": float(r["v"]),
                       "navd88": round(float(r["v"]) + offset, 3),
                       "sigma": r.get("s"), "flags": r.get("f"), "q": r.get("q")})
    return path.name, req["retrieved_utc"], series


def window(series, a, b):
    ta, tb = ff.parse_station_local_time(a), ff.parse_station_local_time(b)
    return [r for r in series if ta <= r["_t"] <= tb]


def peak_interval(rows, tol=FLAT_TOL_FT):
    pk = max(rows, key=lambda r: r["mllw"])
    flat = [r for r in rows if r["mllw"] >= pk["mllw"] - tol]
    return {"max_navd88": pk["navd88"], "max_local": pk["local"],
            "flat_tol_ft": tol, "flat_from_local": flat[0]["local"],
            "flat_to_local": flat[-1]["local"], "flat_n": len(flat),
            "quality": sorted({r["q"] for r in rows})}


def spike_screen(sh, bat, tol=1.0):
    bat_by = {r["gmt"]: r for r in bat}
    out = []
    for prev, cur in zip(sh, sh[1:]):
        d = cur["mllw"] - prev["mllw"]
        if abs(d) >= tol:
            b0, b1 = bat_by.get(prev["gmt"]), bat_by.get(cur["gmt"])
            bd = (b1["mllw"] - b0["mllw"]) if b0 and b1 else None
            out.append({"local": cur["local"], "sh_step_ft": round(d, 3),
                        "battery_step_ft": None if bd is None else round(bd, 3),
                        "verdict": ("instrument (Battery flat)" if bd is not None
                                    and abs(bd) < 0.3 else "unresolved")})
    return out


def main():
    sh_name, sh_ret, sh = latest("sandy-hook")
    bat_name, bat_ret, bat = latest("battery")
    cache = json.loads(CACHE.read_text())
    out = {
        "prepared_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "sources": {"sandy_hook": {"file": sh_name, "retrieved_utc": sh_ret,
                                   "quality_flags": sorted({r["q"] for r in sh})},
                    "battery": {"file": bat_name, "retrieved_utc": bat_ret,
                                "quality_flags": sorted({r["q"] for r in bat})},
                    "datum_note": "NOAA MLLW transported in GMT; station-specific NAVD88 = MLLW + offset: "
                                  "Sandy Hook -2.82, The Battery -2.77 (station_datums.py; NOAA 1983-2001 "
                                  "epoch receipts in audits/2026-09-27-a1/05-noaa-*-datums.json). The committed "
                                  "gauge_cache.json asked NOAA for datum=NAVD directly, which sits 0.005 ft "
                                  "lower (NOAA's own offset).",
                    "datum_offsets_ft": OFFSET},
        "caveat": "All rows are NOAA PRELIMINARY (q='p') at retrieval; a later download "
                  "is not automatically the verified record. Bay level is not street water.",
        "tides": {}, "lags": {}, "spike_screen": spike_screen(sh, bat),
        "cache_comparison": {}, "nowcast_bay_input_trace": [],
    }
    for eid, a, b in TIDES:
        w_sh, w_bat = window(sh, a, b), window(bat, a, b)
        raw_pk = peak_interval(w_sh)
        desp = ff._despike_gauge([(r["local"], r["mllw"]) for r in w_sh])
        desp_rows = [{"local": t, "mllw": v, "navd88": round(v + MLLW_TO_NAVD, 3)}
                     for t, v in desp]
        removed = len(w_sh) - len(desp)
        out["tides"][eid] = {
            "window_local": [a, b], "n_samples": len(w_sh),
            "sandy_hook_raw": raw_pk,
            "sandy_hook_despiked_max": max(desp_rows, key=lambda r: r["mllw"]) if desp_rows else None,
            "despike_removed_samples": removed,
            "battery": peak_interval(w_bat),
            "battery_minus_sh_peak_minutes": round(
                (ff.parse_station_local_time(peak_interval(w_bat)["max_local"])
                 - ff.parse_station_local_time(raw_pk["max_local"])).total_seconds() / 60),
        }
        if eid in CORNER_CREST:
            c0, c1, cnav = CORNER_CREST[eid]
            g0 = ff.parse_station_local_time(raw_pk["flat_from_local"])
            g1 = ff.parse_station_local_time(raw_pk["flat_to_local"])
            gm = ff.parse_station_local_time(raw_pk["max_local"])
            t0, t1 = ff.parse_station_local_time(c0), ff.parse_station_local_time(c1)
            out["lags"][eid] = {
                "corner_crest_window_local": [c0, c1], "corner_crest_navd88": cnav,
                "gauge_max_local": raw_pk["max_local"],
                "gauge_flat_window_local": [raw_pk["flat_from_local"], raw_pk["flat_to_local"]],
                "lag_vs_single_max_minutes": [round((t0 - gm).total_seconds() / 60),
                                              round((t1 - gm).total_seconds() / 60)],
                "lag_vs_flat_window_minutes": [round((t0 - g1).total_seconds() / 60),
                                               round((t1 - g0).total_seconds() / 60)],
                "corner_minus_gauge_peak_ft": round(cnav - raw_pk["max_navd88"], 3),
                "note": "Lag is an interval: 6-min sampling and a flat gauge peak "
                        "do not support a single-minute lag claim.",
            }
    # committed cache vs archived preliminary series
    for key, rows in cache.items():
        by_local = {r["local"][:16]: r for r in sh}
        diffs, missing = [], 0
        for t, v in rows:
            r = by_local.get(t)
            if r is None:
                missing += 1
                continue
            diffs.append(round(r["navd88"] - v, 3))
        out["cache_comparison"][key] = {
            "n_cache": len(rows), "n_unmatched": missing,
            "diff_archive_minus_cache_ft": {"min": min(diffs), "max": max(diffs)} if diffs else None,
            "cache_max": max(rows, key=lambda x: x[1]),
        }
    for sha, gen, bay, src, street in NOWCAST_BAY_INPUTS:
        t = ff.utc_to_station_local(gen)
        near = min(sh, key=lambda r: abs((r["_t"] - t).total_seconds()))
        out["nowcast_bay_input_trace"].append({
            "nowcast_commit": sha, "generated_utc": gen,
            "generated_local": t.isoformat(" ", "minutes"),
            "nowcast_bay_navd88": bay, "nowcast_bay_source": src,
            "nowcast_street_now_in": street,
            "archived_sh_nearest_local": near["local"], "archived_sh_navd88": near["navd88"],
            "archived_sh_q": near["q"], "discrepancy_ft": round(bay - near["navd88"], 3),
        })
    (HERE / "gauge_qc.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in ("tides", "lags", "spike_screen")}, indent=1))
    print("cache:", json.dumps(out["cache_comparison"], indent=1))
    print("trace:", json.dumps(out["nowcast_bay_input_trace"], indent=1))


if __name__ == "__main__":
    main()
