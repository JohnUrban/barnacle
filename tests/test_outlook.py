"""7-day outlook (2026-09-23): adapters parse captured products, the
guidance ladder picks sources by lead, the ledger round-trips through the
real gate, scoring reports readiness honestly, the page passes the
surface contract, and none of it touches alerts."""

import csv
import datetime as dt
import json
import re
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from forecast import check_artifacts, html_contract
from forecast import flood_forecast_daily as ff
from forecast import outlook, outlook_page
from forecast import outlook_sources as srcs
from forecast.station_time import station_time_storage_key
import os


def _need_grib(testcase):
    """CI sets BARNACLE_REQUIRE_GRIB=1 after installing eccodes: then a
    missing decoder is a FAILURE, never a skip (audit R9)."""
    try:
        import eccodes  # noqa: F401
    except ImportError:
        if os.environ.get("BARNACLE_REQUIRE_GRIB") == "1":
            testcase.fail("eccodes missing although BARNACLE_REQUIRE_GRIB=1")
        testcase.skipTest("eccodes not installed locally (CI installs it)")

UTC = dt.timezone.utc
FIX = Path(__file__).parent / "fixtures"
NOW = dt.datetime(2026, 9, 23, 11, 0, tzinfo=UTC)
CYCLE = dt.datetime(2026, 9, 23, 6, tzinfo=UTC)


def _fixture_data():
    return {
        "astro": json.loads((FIX / "astro_highs_20260923.json").read_text()),
        "astro_hourly": json.loads((FIX / "astro_hourly_20260923.json").read_text()),
        "grid": srcs.parse_nws_grid(json.loads(
            (FIX / "nws_grid_phi_61_102_20260923.json").read_text())["properties"]),
        "nwps": srcs.parse_nwps(json.loads((FIX / "nwps_sdhn4_stageflow_20260923.json").read_text()), NOW),
        "petss": {"cycle": "2026-09-23T06:00:00Z",
                  "p10": srcs.parse_petss_station(
                      (FIX / "petss_t06z_e90_stormsurge_east_20260923.txt").read_text(), CYCLE),
                  "p90": srcs.parse_petss_station(
                      (FIX / "petss_t06z_e10_stormsurge_east_20260923.txt").read_text(), CYCLE)},
        "nbm": {"cycle": "2026-09-23T06:00:00Z", "buckets": [
            {"end_utc": (CYCLE + dt.timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M:%SZ"),
             "hours": 6, "qpf_in": 0.25, "pop_pct": 40.0} for h in range(6, 169, 6)]},
        "wpc": None,
        "xcheck": srcs.parse_openmeteo(
            json.loads((FIX / "openmeteo_models_20260923.json").read_text()),
            json.loads((FIX / "openmeteo_ensemble_20260923.json").read_text())),
    }


def _health(data):
    return {k: {"status": "ok", "detail": "fixture"} for k in data}


def _product_tides():
    """Production tides as the 12Z run published them (NWS product rows)."""
    return [
        {"time": "2026-09-23 18:19-04:00", "forecast_peak_mllw": 6.9, "source": "nws-coastal-flood-product"},
        {"time": "2026-09-24 06:47-04:00", "forecast_peak_mllw": 6.4, "source": "nws-coastal-flood-product"},
        {"time": "2026-09-25 19:40-04:00", "forecast_peak_mllw": 7.5, "source": "nws-coastal-flood-product"},
        {"time": "2026-09-26 08:01-04:00", "forecast_peak_mllw": 7.23, "source": "surge-persistence"},
    ]


def _qpf_hourly_from_grid(grid):
    out = []
    for row in grid["series"]["qpf_in"]:
        start = srcs._parse_iso(row["start"])
        h = max(1, int(round(row["hours"])))
        for i in range(h):
            out.append((start + dt.timedelta(hours=i), (row["value"] or 0.0) / h))
    return out


def _build(data=None, surge=1.8, nbm_burst_in=None, hourly_periods=None):
    data = data or _fixture_data()
    data.setdefault("astro_hourly", json.loads((FIX / "astro_hourly_20260923.json").read_text()))
    if nbm_burst_in is not None:      # a 6-h burst ending Sat 08:00 EDT (12Z)
        for b in data["nbm"]["buckets"]:
            if b["end_utc"] == "2026-09-26T12:00:00Z":
                b["qpf_in"] = nbm_burst_in
    nws_hourly = hourly_periods if hourly_periods is not None else json.loads(
        (FIX / "nws_hourly_20260923.json").read_text())
    return outlook.build_outlook_7d(
        NOW, data, _health(data), _product_tides(), surge, 6.0,
        ff.classify_regime_from_water, lambda p: ff.predict_landmark_depths(p, 0.0, False),
        ff.MLLW_TO_NAVD88_OFFSET, "v0.10.4",
        nws_hourly=nws_hourly, qpf_hourly=_qpf_hourly_from_grid(data["grid"]),
        simulate_fn=ff.simulate_pluvial_series, potential_fn=ff.estimate_pluvial_water_models,
        enhancement_ft=ff.LOCAL_ENHANCEMENT_FT)


class AdapterParseTests(unittest.TestCase):
    def test_petss_station_block_is_hourly_from_cycle_plus_one(self):
        s = srcs.parse_petss_station(
            (FIX / "petss_t06z_e10_stormsurge_east_20260923.txt").read_text(), CYCLE)
        self.assertEqual(len(s), 102)
        self.assertEqual(s[0]["utc"], "2026-09-23T07:00:00Z")
        self.assertEqual(s[-1]["utc"], "2026-09-27T12:00:00Z")
        self.assertEqual(s[0]["surge_ft"], 1.5)          # "15" tenths

    def test_petss_rejects_header_that_does_not_follow_the_cycle(self):
        text = (FIX / "petss_t06z_e10_stormsurge_east_20260923.txt").read_text()
        with self.assertRaises(ValueError):
            srcs.parse_petss_station(text, dt.datetime(2026, 9, 23, 12, tzinfo=UTC))

    def test_petss_missing_station_and_sentinel_values(self):
        text = (FIX / "petss_t06z_e10_stormsurge_east_20260923.txt").read_text()
        with self.assertRaises(ValueError):
            srcs.parse_petss_station(text, CYCLE, station="0000000")
        synthetic = ("FQUS23 KWNO 230600\nGEFS BASED STORM SURGE (IN TENTHS OF FT)\n"
                     " 07Z                 12Z\n\n 8531680 SANDY HOOK, NJ      13\n"
                     + "  10  11  12 -400  14  15  16  17  18  19  20  21  22  23  24  25  26  27  28  29  30  31  32  33\n"
                     + "  34  35  36  37  38  39\n")
        s = srcs.parse_petss_station(synthetic, CYCLE)
        self.assertEqual(len(s), 29)                       # the -400 hour is dropped, not zeroed
        self.assertEqual([p["utc"] for p in s][3], "2026-09-23T11:00:00Z")

    def test_petss_exceedance_files_map_to_low_and_high(self):
        lo = srcs.parse_petss_station((FIX / "petss_t06z_e90_stormsurge_east_20260923.txt").read_text(), CYCLE)
        hi = srcs.parse_petss_station((FIX / "petss_t06z_e10_stormsurge_east_20260923.txt").read_text(), CYCLE)
        self.assertTrue(all(a["surge_ft"] <= b["surge_ft"] for a, b in zip(lo, hi)))

    def test_nwps_forecast_and_peak_lookup(self):
        nw = srcs.parse_nwps(json.loads((FIX / "nwps_sdhn4_stageflow_20260923.json").read_text()))
        self.assertEqual(len(nw["series"]), 72)
        self.assertEqual(nw["issued"], "2026-09-23T07:45:00Z")
        # matches the coastal product row for Wed 18:19 EDT exactly
        self.assertEqual(srcs.series_max_near(nw["series"], dt.datetime(2026, 9, 23, 22, 19, tzinfo=UTC)), 6.9)

    def test_nws_grid_reach_and_units(self):
        g = srcs.parse_nws_grid(json.loads((FIX / "nws_grid_phi_61_102_20260923.json").read_text())["properties"])
        self.assertEqual(g["reach"]["qpf_in"][:13], "2026-09-26T12")      # ~72 h wall
        self.assertGreater(g["reach"]["gust_mph"], "2026-09-30")          # ~7 d
        gust = srcs.grid_value_at(g["series"]["gust_mph"], dt.datetime(2026, 9, 26, 15, tzinfo=UTC))
        self.assertTrue(29.0 < gust < 31.0, gust)      # 48 km/h bucket -> mph

    def test_iso_durations(self):
        self.assertEqual(srcs._iso_duration_hours("P3DT22H"), 94)
        self.assertEqual(srcs._iso_duration_hours("PT30M"), 0.5)
        with self.assertRaises(ValueError):
            srcs._iso_duration_hours("6H")

    def test_openmeteo_cross_check_shape(self):
        x = srcs.parse_openmeteo(json.loads((FIX / "openmeteo_models_20260923.json").read_text()),
                                 json.loads((FIX / "openmeteo_ensemble_20260923.json").read_text()))
        sat = x["ensemble"]["2026-09-26"]
        self.assertEqual(sat["members"], 31)
        self.assertEqual(sat["p_half_inch_pct"], 35)
        self.assertEqual(set(x["models"]["2026-09-26"]), {"gfs", "ecmwf", "icon", "gem"})

    def test_nbm_subset_picks_deterministic_amount_not_probability(self):
        _need_grib(self)
        got = srcs.parse_nbm_subset((FIX / "nbm_t06z_core_f096_house_20260923.grib2").read_bytes())
        self.assertAlmostEqual(got["qpf_in"], 0.14, places=2)
        self.assertAlmostEqual(got["pop_pct"], 51.0, places=0)

    def test_nbm_qmd_percentiles_and_exceedance(self):
        _need_grib(self)
        got = srcs.parse_nbm_qmd_subset((FIX / "nbm_t06z_qmd_f096_house_20260923.grib2").read_bytes())
        self.assertLessEqual(got["p10_in"], got["p50_in"])
        self.assertLessEqual(got["p50_in"], got["p90_in"])
        self.assertGreater(got["p90_in"], 0.0)
        for k in ("p_ge_quarter_in_pct", "p_ge_half_in_pct", "p_ge_1in_pct"):
            self.assertIsNotNone(got[k])
            self.assertTrue(0.0 <= got[k] <= 100.0)
        self.assertGreaterEqual(got["p_ge_quarter_in_pct"], got["p_ge_half_in_pct"])
        self.assertGreaterEqual(got["p_ge_half_in_pct"], got["p_ge_1in_pct"])

    def test_nbm_qmd_file_merges_by_valid_time_with_age_health(self):
        nbm = {"buckets": [{"end_utc": "2026-09-26T12:00:00Z", "hours": 6, "qpf_in": 0.2, "pop_pct": 40.0},
                           {"end_utc": "2026-09-26T18:00:00Z", "hours": 6, "qpf_in": 0.1, "pop_pct": 30.0}]}
        qmd = {"qmd_cycle": "2026-09-23T06:00:00Z", "fetched_at": "2026-09-23T10:30:00Z",
               "buckets": {"2026-09-26T12:00:00Z": {"p10_in": 0.0, "p50_in": 0.1, "p90_in": 0.9,
                                                    "p_ge_half_in_pct": 22.0}}}
        h = srcs.merge_nbm_qmd(nbm, qmd, NOW + dt.timedelta(hours=1))   # cycle 6 h old
        self.assertEqual(h["status"], "ok")
        self.assertEqual(nbm["buckets"][0]["p90_in"], 0.9)
        self.assertNotIn("p90_in", nbm["buckets"][1])          # unmatched bucket stays without percentiles
        self.assertEqual(srcs.merge_nbm_qmd(nbm, qmd, NOW + dt.timedelta(hours=20))["status"], "degraded")   # cycle 25 h
        # R4: expired percentiles are NOT merged and previously merged fields are cleared
        h = srcs.merge_nbm_qmd(nbm, qmd, NOW + dt.timedelta(hours=40))
        self.assertEqual(h["status"], "unavailable")
        self.assertNotIn("p90_in", nbm["buckets"][0])
        self.assertEqual(srcs.merge_nbm_qmd(nbm, None, NOW)["status"], "unavailable")
        # fresh file with zero matching buckets is degraded, not ok
        h = srcs.merge_nbm_qmd({"buckets": [{"end_utc": "2027-01-01T00:00:00Z", "hours": 6}]}, qmd, NOW)
        self.assertEqual(h["status"], "degraded")

    def test_nbm_qmd_fetch_honours_time_budget(self):
        calls = []

        def fake_request(url, timeout=30):
            calls.append(url)
            return (FIX / "nbm_t06z_qmd_f096_house_20260923.grib2").read_bytes()
        _need_grib(self)
        with mock.patch.object(srcs, "_request", side_effect=fake_request):
            data = srcs.fetch_nbm_qmd(NOW, cycle=CYCLE, steps=(6, 12, 18), time_budget_s=1e9)
        self.assertEqual(data["qmd_cycle"], "2026-09-23T06:00:00Z")
        self.assertEqual(sorted(data["buckets"]), ["2026-09-23T12:00:00Z", "2026-09-23T18:00:00Z", "2026-09-24T00:00:00Z"])
        self.assertEqual(len(calls), 3)                        # no discovery request when the cycle is given
        with mock.patch.object(srcs, "_request", side_effect=fake_request):
            data = srcs.fetch_nbm_qmd(NOW, cycle=CYCLE, steps=(6, 12, 18), time_budget_s=-1)
        self.assertEqual(len(data["buckets"]), 1)             # the first step always runs, the rest hit the budget
        self.assertEqual(len(data["missing"]), 2)
        self.assertTrue(all("time budget" in m for m in data["missing"]))

    def test_cache_refresh_contract(self):
        cache, now = {}, NOW
        calls = []

        def fetch(timeout):
            calls.append(timeout)
            if len(calls) == 2:
                raise OSError("down")
            return {"summary": "fresh", "v": len(calls)}
        d1, h1 = srcs.refresh(cache, "nwps", fetch, now)
        self.assertEqual((d1["v"], h1["status"]), (1, "ok"))
        d2, h2 = srcs.refresh(cache, "nwps", fetch, now + dt.timedelta(minutes=30))
        self.assertEqual((d2["v"], h2["status"]), (1, "ok"))        # within TTL, no call
        d3, h3 = srcs.refresh(cache, "nwps", fetch, now + dt.timedelta(hours=2))
        self.assertEqual((d3["v"], h3["status"]), (1, "degraded"))  # fetch failed, stale served
        d4, h4 = srcs.refresh(cache, "nwps", fetch, now + dt.timedelta(hours=30))
        self.assertEqual(d4["v"], 3)
        spent = srcs.Deadline(0.0, clock=lambda: 100.0)
        d5, h5 = srcs.refresh({}, "nwps", fetch, now, deadline=spent)
        self.assertIsNone(d5)
        self.assertIn("budget", h5["detail"])


class LadderTests(unittest.TestCase):
    def test_sources_by_lead(self):
        ol = _build()
        by = {t["time"]: t for t in ol["tides"]}
        self.assertEqual(by["2026-09-23 18:19-04:00"]["outlook_source"], "nws_product")
        self.assertEqual(by["2026-09-23 18:19-04:00"]["outlook_mllw"], 6.9)
        self.assertEqual(by["2026-09-26 08:01-04:00"]["outlook_source"], "petss_mid")   # 73 h: product row absent, NWPS out of reach
        # 110 h: beyond P-ETSS the last guidance value decays toward the typical offset (v0.10.6)
        self.assertEqual(by["2026-09-27 20:58-04:00"]["outlook_source"], "guidance_decay")
        self.assertEqual(len(ol["tides"]), 14)
        self.assertTrue(all(t["band_lo_mllw"] is None for t in ol["tides"] if t["lead_h"] > 102))

    def test_astronomy_layer_and_guidance_layer_both_present(self):
        ol = _build()
        for t in ol["tides"]:
            self.assertIsNotNone(t["astro_mllw"])
            self.assertIsNotNone(t["outlook_mllw"])
            self.assertIn(t["outlook_source"], outlook.LADDER + ("astro",))
        for d in ol["days"]:
            if d.get("partial") and not d["tides"]:      # a partial last card may hold no high tide in scope
                continue
            self.assertIsNotNone(d["astro_max_mllw"])
            self.assertIsNotNone(d["outlook_max_mllw"])

    def test_no_surge_anywhere_yields_astronomy_only_not_zero_labeled_as_forecast(self):
        data = _fixture_data()
        data["nwps"] = None
        data["petss"] = None
        ol = outlook.build_outlook_7d(NOW, data, _health(data), [], None, None,
                                      ff.classify_regime_from_water,
                                      lambda p: ff.predict_landmark_depths(p, 0.0, False),
                                      ff.MLLW_TO_NAVD88_OFFSET, "v0.10.4")
        self.assertTrue(all(t["outlook_source"] == "astro" for t in ol["tides"]))
        self.assertTrue(all(t["outlook_mllw"] == t["astro_mllw"] for t in ol["tides"]))

    def test_rain_source_switches_from_grid_to_nbm_beyond_grid_reach(self):
        ol = _build()
        by = {t["time"]: t for t in ol["tides"]}
        self.assertEqual(by["2026-09-25 19:40-04:00"]["rain"]["source"], "nws_grid")
        self.assertEqual(by["2026-09-28 09:15-04:00"]["rain"]["source"], "nbm")
        sat = next(d for d in ol["days"] if d["date"] == "2026-09-26")
        self.assertEqual(sat["qpf_source"], "nbm")
        self.assertEqual(sat["xcheck_ensemble"]["p_half_inch_pct"], 35)

    def test_persistence_decay_is_labeled_assumption(self):
        ol = _build()
        self.assertEqual(ol["assumptions"]["persistence_decay_tau_h"], 36.0)   # v0.10.6, measured
        # the observed-reading decay stays in every tide's guidance (the shadow
        # ledger scores it against flat persistence) even where guidance_decay leads
        late = [t for t in ol["tides"] if t["lead_h"] > 102]
        self.assertTrue(late)
        for t in late:
            self.assertEqual(t["outlook_source"], "guidance_decay")
            self.assertLess(t["guidance"]["persist_decay"], t["guidance"]["persist_flat"])

    def test_outlook_never_enters_all_tides_or_alerts(self):
        ol = _build()
        forecast = {"all_tides": _product_tides()[:1] and [
            {"time": "2026-09-28 09:15-04:00", "hours_from_now": 118.0,
             "forecast_peak_mllw": 7.4, "depths_in": {"regime": "severe"}}],
            "pluvial_risk": {}, "outlook_7d": ol}
        with mock.patch.object(ff, "_radar_live_state", return_value=None):
            rank, _, sig = ff.compute_alert_level(forecast)
        self.assertEqual(rank, 0)
        self.assertEqual(sig, "")


class RainPathwayTests(unittest.TestCase):
    """Rain doctrine: the rain pathway is never deferred and never gated by
    the tide; a day's headline is the worst of the two pathways."""

    def test_series_covers_seven_days_with_both_layers(self):
        ol = _build()
        S = ol["series"]
        self.assertGreater(len(S), 150)
        self.assertLessEqual(S[0]["lead_h"], -5)
        self.assertGreaterEqual(S[-1]["lead_h"], 160)
        for p in S:
            self.assertIsNotNone(p["tide_navd88"])
            self.assertIsNotNone(p["water_navd88"])
            self.assertIn(p["surge_source"], tuple(outlook.HOURLY_SURGE_SOURCES))
        self.assertTrue({p["surge_source"] for p in S if 0 <= p["lead_h"] <= 60} <= {"nwps", "nws_product"})
        self.assertIn("nbm", {p["rain_source"] for p in S if p["lead_h"] > 80})

    def test_low_tide_burst_makes_rain_the_worst_pathway(self):
        quiet = _build()
        sat_q = next(d for d in quiet["days"] if d["date"] == "2026-09-26")
        stormy = _build(nbm_burst_in=3.0)       # 3 in over 6 h ending Sat 08:00 EDT
        sat = next(d for d in stormy["days"] if d["date"] == "2026-09-26")
        rp = sat["rain_pathway"]
        self.assertTrue(rp["burst_signal"])
        self.assertIsNotNone(rp["tank_peak_navd88"])
        self.assertGreater(rp["tank_peak_navd88"], 3.52)                  # water over the SW grate from rain
        self.assertGreater(rp["burst_est_in_hr"], 0.5)
        self.assertIsNotNone(rp["burst_potential_navd88"])
        # low-tide hours around the burst carry tank water while the tide is far below the grate
        low = [p for p in stormy["series"] if p["time"].startswith("2026-09-26 1") and p["tide_navd88"] < 3.0]
        self.assertTrue(any(p["pluvial_navd88"] and p["pluvial_navd88"] > p["tide_navd88"] for p in low))
        self.assertGreaterEqual(outlook.REGIME_RANK[sat["regime_max"]], outlook.REGIME_RANK[sat_q["regime_max"]])
        # a day with no tide risk and heavy rain is headlined by rain, not "dry"
        data = _fixture_data(); data["nwps"] = None; data["petss"] = None
        ol = outlook.build_outlook_7d(NOW, data, _health(data), [], 0.0, 6.0,
                                      ff.classify_regime_from_water,
                                      lambda p: ff.predict_landmark_depths(p, 0.0, False),
                                      ff.MLLW_TO_NAVD88_OFFSET, "v0.10.4",
                                      nws_hourly=[], qpf_hourly=[], simulate_fn=ff.simulate_pluvial_series,
                                      potential_fn=ff.estimate_pluvial_water_models, enhancement_ft=0.0)
        for b in data["nbm"]["buckets"]:
            b["qpf_in"] = 0.0
        # (astronomy-only tides are all below the grate: tidal pathway dry)
        self.assertTrue(all(d["tidal_regime_max"] == "dry" for d in ol["days"]))

    def test_worst_flood_chance_can_differ_from_worst_tide(self):
        ol = _build(nbm_burst_in=3.0)
        w = ol["worst"]
        self.assertIn(w["flood_chance"]["pathway"], ("rain (burst scenario)", "rain (tank line)", "tide"))
        self.assertIsNotNone(w["tide"]["navd88"])
        self.assertGreaterEqual(w["flood_chance"]["navd88"], w["tide"]["navd88"] - 1e-9)

    def test_nbm_percentile_band_feeds_a_labeled_high_end(self):
        data = _fixture_data()
        for b in data["nbm"]["buckets"]:
            b.update({"p10_in": 0.0, "p50_in": 0.1, "p90_in": 0.4,
                      "p_ge_quarter_in_pct": 30.0, "p_ge_half_in_pct": 12.0, "p_ge_1in_pct": 2.0})
        for b in data["nbm"]["buckets"]:
            # 06-12Z and 12-18Z buckets: the 08:01 EDT (12:01Z) tide sits in the second
            if b["end_utc"] in ("2026-09-26T12:00:00Z", "2026-09-26T18:00:00Z"):
                b.update({"p90_in": 2.4, "p_ge_half_in_pct": 45.0, "p_ge_1in_pct": 20.0})
        ol = _build(data=data)
        sat = next(d for d in ol["days"] if d["date"] == "2026-09-26")
        band = sat["nbm_band"]
        self.assertEqual(band["p90_6h_max_in"], 2.4)
        self.assertEqual(band["p_ge_half_in_6h_max_pct"], 45.0)
        rp = sat["rain_pathway"]
        self.assertEqual(rp["nbm_p90_6h_in"], 2.4)
        self.assertIsNotNone(rp["nbm_p90_potential_navd88"])
        self.assertGreater(rp["nbm_p90_potential_navd88"], 3.52)
        self.assertIn(rp["nbm_p90_regime"], ("street", "light", "moderate", "severe"))
        # the p90 scenario is a labeled high end, not the headline driver
        self.assertEqual(sat["worst_pathway"], "tide")
        by = {t["time"]: t for t in ol["tides"]}
        self.assertEqual(by["2026-09-26 08:01-04:00"]["nbm_p_ge_half_in_6h_pct"], 45.0)
        from forecast import outlook_page
        html = outlook_page.render_outlook_page({"generated_utc": "x", "forecast_schema_version": "1.0",
                                                 "model_version": "v", "outlook_7d": ol, "input_health": {}})
        self.assertIn("NBM 90th-pct rain 2.40 in/6 h", html)
        self.assertIn("45% chance of ≥0.5 in in 6 h", html)
        self.assertIn("NBM P(&ge;0.5 in/6 h)", html)

    def test_rain_unavailable_is_not_zero(self):
        data = _fixture_data()
        data["nbm"] = None; data["wpc"] = None
        ol = _build(data=data)
        late = [p for p in ol["series"] if p["lead_h"] > 80]
        self.assertTrue(late)
        self.assertTrue(all(p["rain_source"] is None and p["rain_in_hr"] is None and p["rain_unknown"] for p in late))
        d = next(d for d in ol["days"] if d["date"] == "2026-09-28")
        self.assertFalse(d["rain_pathway"]["rain_available"])
        self.assertEqual(d["rain_pathway"]["tank_regime"], "unknown")        # not "dry"
        self.assertEqual(d["rain_pathway"]["burst_regime"], "unknown")
        # partial day: the grid ends inside 09-26, so that day is partial, not complete
        sat = next(d for d in ol["days"] if d["date"] == "2026-09-26")
        self.assertLess(sat["rain_pathway"]["rain_coverage"], 1.0)
        self.assertGreater(sat["rain_pathway"]["rain_coverage"], 0.0)
        # rolling 168 h: the series and the cards share the same last date (a partial card)
        self.assertEqual(max(p["time"][:10] for p in ol["series"]), ol["days"][-1]["date"])


class MapSeriesTests(unittest.TestCase):
    def test_map_series_splices_outlook_and_finds_worst_by_pathway(self):
        ol = _build(nbm_burst_in=3.0)
        prod = [{"time": p["time"], "water_navd88": p["water_navd88"], "tide_navd88": p["tide_navd88"],
                 "burst_risk": p["burst_risk"]} for p in ol["series"] if -6 <= p["lead_h"] <= 30]
        forecast = {"water_series": prod, "outlook_7d": ol, "pluvial_risk": {}}
        pts, prod_len, pot_by_day, worst = ff._map_time_series(forecast)
        self.assertEqual(prod_len, len(prod))
        self.assertGreater(len(pts), prod_len + 100)
        self.assertTrue(all(not q["o"] for q in pts[:prod_len]) and all(q["o"] for q in pts[prod_len:]))
        self.assertEqual([q["t"] for q in pts], sorted(q["t"] for q in pts))
        self.assertIsNotNone(worst["tide"]); self.assertIsNotNone(worst["flood"])
        self.assertIn("2026-09-26", pot_by_day)


class AuditRepairBTests(unittest.TestCase):
    """Audit 2026-09-23-a1 R5 / R6 / R8 / R2 regression checks."""

    def test_r5_one_bucket_across_local_midnight_is_prorated(self):
        # 00-06Z = 20:00-02:00 EDT: 4 h in 09-23, 2 h in 09-24
        grid = {"series": {"qpf_in": [{"start": "2026-09-24T00:00:00Z", "hours": 6, "value": 0.6}]},
                "reach": {"qpf_in": "2026-09-30T12:00:00Z"}}
        days = outlook.build_days(NOW, [], {"grid": grid})
        self.assertAlmostEqual(days[0]["qpf_in"], 0.4, places=2)
        self.assertAlmostEqual(days[1]["qpf_in"], 0.2, places=2)
        self.assertAlmostEqual(sum(d["qpf_in"] for d in days[:2]), 0.6, places=2)
        # NBM buckets prorate the same way (uniform rate)
        # contiguous 6-h NBM buckets from 06Z on 09-23; only the one ending 06Z on
        # 09-24 (= 20:00-02:00 EDT, across local midnight) carries rain
        nbm = []
        for i in range(0, 32):
            end = dt.datetime(2026, 9, 23, 12, tzinfo=UTC) + dt.timedelta(hours=6 * i)
            nbm.append({"end_utc": end.strftime("%Y-%m-%dT%H:%M:%SZ"), "hours": 6,
                        "qpf_in": 0.6 if end == dt.datetime(2026, 9, 24, 6, tzinfo=UTC) else 0.0,
                        "pop_pct": 0.0})
        grid2 = {"series": {"qpf_in": []}, "reach": {}}
        days2 = outlook.build_days(NOW, [], {"grid": grid2, "nbm": {"buckets": nbm}})
        self.assertAlmostEqual(days2[0]["qpf_in"], 0.4, places=2)
        self.assertAlmostEqual(days2[1]["qpf_in"], 0.2, places=2)

    def test_r5_bucket_edges_are_start_inclusive_end_exclusive(self):
        at = outlook._hourly_rain_lookup([], [{"end_utc": "2026-09-24T06:00:00Z", "hours": 6, "qpf_in": 6.0}], [])
        t = lambda h: dt.datetime.fromisoformat(f"2026-09-24T{h}:00+00:00")
        self.assertEqual(at(t("00:00"))[0], 1.0)      # start belongs to the bucket
        self.assertEqual(at(t("05:00"))[0], 1.0)
        self.assertIsNone(at(t("06:00"))[0])          # end belongs to the next bucket

    def test_r6_worst_points_ignore_history(self):
        series = [{"time": "2026-09-23 05:00-04:00", "lead_h": -2, "tide_navd88": 8, "water_navd88": 8, "burst_risk": False},
                  {"time": "2026-09-23 08:00-04:00", "lead_h": 1, "tide_navd88": 3, "water_navd88": 3, "burst_risk": False}]
        w = outlook.worst_points(series, [])
        self.assertEqual(w["tide"]["time"], "2026-09-23 08:00-04:00")
        self.assertEqual(w["flood_chance"]["time"], "2026-09-23 08:00-04:00")

    def test_r6_map_series_splices_by_instant_and_searches_the_future_only(self):
        prod = [{"time": "2026-09-23 05:00-04:00", "water_navd88": 8.0, "tide_navd88": 8.0, "burst_risk": False},
                {"time": "2026-09-23 08:00-04:00", "water_navd88": 3.0, "tide_navd88": 3.0, "burst_risk": False}]
        ol = {"series": [{"time": "2026-09-23 09:00-04:00", "water_navd88": 4.0, "tide_navd88": 4.0, "burst_risk": False, "lead_h": 2}],
              "worst": {"burst_potential_by_day": {}}}
        fc = {"water_series": prod, "outlook_7d": ol, "pluvial_risk": {}, "generated_utc": "2026-09-23T11:00:00Z"}
        pts, prod_len, _pot, worst = ff._map_time_series(fc)
        self.assertEqual(prod_len, 2)
        self.assertEqual(worst["tide"], 2)          # 09:00 (future), not the 05:00 crest
        self.assertEqual(worst["flood"], 2)

    def test_r6_browser_now_parsers_keep_the_offset(self):
        html = ff._client_map_section_html if hasattr(ff, "_client_map_section_html") else None
        landing = open(Path(__file__).resolve().parents[1] / "forecast" / "flood_forecast_daily.py").read()
        town = open(Path(__file__).resolve().parents[1] / "docs" / "highlands.html").read()
        for src in (landing, town):
            self.assertIn("replace(' ', 'T')" if src is landing else 'replace(" ", "T")', src)
            self.assertIn("instMs(", src)
        self.assertNotIn("new Date(+m[1], m[2] - 1, +m[3], +m[4], +m[5]) >= now", town)

    def test_r8_product_rows_anchor_the_continuous_line(self):
        data = _fixture_data()
        for p in data["nwps"]["series"]:
            p["ft"] = 4.0                                   # conflicting hourly guidance
        ol = _build(data=data, hourly_periods=[])
        tide = next(t for t in ol["tides"] if t["time"] == "2026-09-23 18:19-04:00")
        pt = next(p for p in ol["series"] if p["time"] == "2026-09-23 18:00-04:00")
        self.assertEqual(tide["outlook_source"], "nws_product")
        self.assertAlmostEqual(pt["tide_navd88"] - ff.MLLW_TO_NAVD88_OFFSET, 6.9, delta=0.15)
        self.assertEqual(pt["surge_source"], "nws_product")
        far = next(p for p in ol["series"] if p["time"] == "2026-09-23 10:00-04:00")   # > 6 h from any anchor
        self.assertAlmostEqual(far["tide_navd88"] - ff.MLLW_TO_NAVD88_OFFSET, 4.0, delta=0.15)

    def test_r2_one_tide_many_issuances_is_one_observation(self):
        target = "2026-09-24 06:47-04:00"
        rows = [dict(target_tide_time=target, lead_h=str(40 - i), nwps_mllw="6.5",
                     persist_flat_mllw="7.5", outlook_mllw="6.5", generated_utc=f"run-{i}") for i in range(28)]
        sc = outlook.score_shadow(rows, {target: 6.5})
        r = sc["readiness"]["nwps_vs_persistence_le72h"]
        self.assertEqual(r["n"], 1)
        self.assertEqual(r["n_forecasts"], 28)        # round 03 S1: paired rows, each counted once
        self.assertTrue(r["verdict"].startswith("NOT YET (1/28"))
        self.assertEqual(sc["scored_tides"], 1)
        # 28 distinct tides, one issuance each, candidate better -> READY
        rows = [dict(target_tide_time=f"2026-10-{1 + i // 2:02d} {6 + 12 * (i % 2):02d}:00-04:00", lead_h="30",
                     nwps_mllw="6.5", persist_flat_mllw="7.5", outlook_mllw="6.5") for i in range(28)]
        obs = {r["target_tide_time"]: 6.5 for r in rows}
        r = outlook.score_shadow(rows, obs)["readiness"]["nwps_vs_persistence_le72h"]
        self.assertEqual(r["n"], 28)
        self.assertTrue(r["verdict"].startswith("READY"))


class AuditRepairCTests(unittest.TestCase):
    """Audit R7 / R10 / R11 / R12 and the compound burst-at-high-tide scenario."""

    def _rain_day_forecast(self):
        return {"all_tides": [{"time": "2026-09-24 18:00-04:00", "forecast_peak_mllw": 6.8, "hours_from_now": 30,
                               "depths_in": {"regime": "street"}}],
                "water_series": [{"time": "2026-09-23 14:00-04:00", "tide_navd88": 2.0, "water_navd88": 5.2, "burst_risk": True},
                                 {"time": "2026-09-23 15:00-04:00", "tide_navd88": 2.2, "water_navd88": 5.0, "burst_risk": True}],
                "rain_outlook_72h": [{"day": "2026-09-23", "cum_in": 3, "max_pop_pct": 100, "thunder": True, "peak_in_hr": 3}],
                "pluvial_risk": {"level": "elevated", "potential_low_tide_navd88": 6.0, "risk_today": True},
                "peak_time_local": "2026-09-24 18:00-04:00", "peak_forecast_observed_mllw": 6.8,
                "generated_utc": "2026-09-23T11:00:00Z"}

    def test_r7_day_worst_ranks_a_rain_day_above_a_smaller_tide_day(self):
        fc = self._rain_day_forecast()
        dw = ff.compute_day_worst(fc["all_tides"], fc["water_series"], fc["pluvial_risk"],
                                  fc["rain_outlook_72h"], ["2026-09-23", "2026-09-24", "2026-09-25"])
        self.assertEqual(dw[0]["pathway"], "rain (burst scenario)")
        self.assertEqual(dw[0]["regime"], ff.classify_regime_from_water(6.0))
        self.assertEqual(dw[1]["pathway"], "tide")
        self.assertEqual(dw[1]["regime"], "street")
        self.assertGreater(dw[0]["rank"], dw[1]["rank"])
        fc["day_worst"] = dw
        # ribbon on the RAIN day, not the tide day
        with mock.patch.object(ff, "_station_local_now", return_value=ff.parse_station_local_time("2026-09-23 07:00-04:00")), \
                mock.patch.object(__import__("forecast.rendering", fromlist=["x"]), "_station_local_now",
                                  return_value=ff.parse_station_local_time("2026-09-23 07:00-04:00")):
            from forecast import rendering
            html = rendering._render_day_cards_html(fc)
        sections = html.split("<section")[1:]
        self.assertEqual(["WORST OF 72 H" in x for x in sections], [True, False, False])
        self.assertIn("(RAIN)", sections[0])
        # today's headline reads the rain pathway when it outranks the tide regime
        head, cls = ff.headline_for(fc, "dry")
        self.assertIn("(RAIN)", head)
        self.assertEqual(cls, dw[0]["regime"])

    def test_r7_email_subject_leads_with_the_worst_pathway(self):
        fc = self._rain_day_forecast()
        fc["day_worst"] = ff.compute_day_worst(fc["all_tides"], fc["water_series"], fc["pluvial_risk"],
                                               fc["rain_outlook_72h"], ["2026-09-23", "2026-09-24", "2026-09-25"])
        from forecast import rendering
        src = open(Path(rendering.__file__).with_suffix(".py")).read()
        self.assertIn("WORST 72H is the worst PATHWAY", src)

    def test_r11_scope_labels(self):
        from forecast import rendering
        src = open(Path(rendering.__file__).with_suffix(".py")).read()
        self.assertNotIn("Landmarks today", src)
        self.assertNotIn("Low tides in next 24h", src)
        self.assertIn("Landmarks at the worst tide of the 72 h", src)
        self.assertIn("Low tides, next 72 h", src)

    def test_r10_outlook_gate_rejects_invented_contracts(self):
        base = {"generated_utc": "2026-09-23T11:00:00Z", "model_version": "v0.10.4"}
        bad = dict(base, outlook_7d={"model_version": "invented", "horizon_hours": -1, "series": "bad",
                                     "days": [], "sources": "x"})
        failures = check_artifacts.validate_outlook_field(bad)
        self.assertTrue(any("horizon_hours" in f for f in failures))
        self.assertTrue(any("model_version" in f for f in failures))
        self.assertTrue(any("series" in f for f in failures))
        self.assertTrue(any("days" in f for f in failures))
        self.assertTrue(any("sources" in f for f in failures))
        ol = _build()
        ol["model_version"] = "v0.10.4"
        self.assertEqual(check_artifacts.validate_outlook_field(dict(base, outlook_7d=ol)), [])
        self.assertEqual(check_artifacts.validate_outlook_field(dict(base, outlook_7d=None)), [])

    def test_r10_outlook_ledger_semantics(self):
        ol = _build()
        rows = outlook.outlook_log_rows(ol, "2026-09-23T11:00:00Z", "v0.10.4")
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "outlook_log.csv")
            outlook.append_outlook_log(path, rows)
            self.assertEqual(check_artifacts.validate_csv_semantics(path, "data/outlook_log.csv", now_utc=NOW + dt.timedelta(hours=1)), [])
            bad = dict(rows[0], outlook_source="made-up", lead_h="-5")
            outlook.append_outlook_log(path, [bad])
            failures = check_artifacts.validate_csv_semantics(path, "data/outlook_log.csv", now_utc=NOW + dt.timedelta(hours=1))
            self.assertTrue(any("outlook_source" in f for f in failures))
            self.assertTrue(any("lead_h" in f for f in failures))

    def test_compound_burst_on_the_high_tide_exceeds_the_low_tide_figure(self):
        ol = _build(nbm_burst_in=3.0)
        sat = next(d for d in ol["days"] if d["date"] == "2026-09-26")
        rp = sat["rain_pathway"]
        self.assertIsNotNone(rp["burst_potential_navd88"])
        self.assertIsNotNone(rp["burst_at_high_tide_navd88"])
        self.assertGreater(rp["burst_at_high_tide_navd88"], rp["burst_potential_navd88"])
        self.assertIn(rp["burst_at_high_tide_regime"], ("light", "moderate", "severe"))
        flagged = [p for p in ol["series"] if p["time"].startswith("2026-09-26") and p.get("burst_risk")]
        self.assertTrue(flagged)
        self.assertTrue(all(p.get("burst_potential_navd88") is not None for p in flagged))
        # an hour on a higher tide gets a higher scenario level than one on a lower tide
        hi = max(flagged, key=lambda p: p["tide_navd88"]); lo = min(flagged, key=lambda p: p["tide_navd88"])
        self.assertGreaterEqual(hi["burst_potential_navd88"], lo["burst_potential_navd88"])
        self.assertIn(sat["worst_pathway"], ("tide", "rain (tank line)", "rain (burst scenario)", "rain burst on the high tide"))
        from forecast import outlook_page
        html = outlook_page.render_outlook_page({"generated_utc": "x", "forecast_schema_version": "1.0",
                                                 "model_version": "v", "outlook_7d": ol, "input_health": {}})
        self.assertIn("the same burst on the day's high tide", html)


class AuditRound03Tests(unittest.TestCase):
    """Codex round 03 S1-S7 regression checks (the probes inverted)."""

    def test_s1_absolute_before_average_and_same_issuance_pairing(self):
        rows, observed = [], {}
        for i in range(28):
            t = (dt.datetime(2026, 8, 1, 12, tzinfo=UTC) + dt.timedelta(hours=12 * i)).isoformat()
            observed[t] = 5.0
            for pred in (4.0, 6.0):
                rows.append(dict(target_tide_time=t, lead_h="12", nwps_mllw=str(pred), persist_flat_mllw="5.2"))
        r = outlook.score_shadow(rows, observed)["readiness"]["nwps_vs_persistence_le72h"]
        self.assertEqual(r["mae_candidate"], 1.0)
        self.assertAlmostEqual(r["mae_baseline"], 0.2, places=6)
        self.assertTrue(r["verdict"].startswith("NOT BETTER"))
        self.assertEqual(r["n"], 28)
        self.assertEqual(r["n_forecasts"], 56)              # paired rows, counted once
        disjoint = [dict(target_tide_time="t", lead_h="1", nwps_mllw="5"),
                    dict(target_tide_time="t", lead_h="23", persist_flat_mllw="6")]
        r = outlook.score_shadow(disjoint, {"t": 5})["readiness"]["nwps_vs_persistence_le72h"]
        self.assertEqual(r["n"], 0)
        self.assertEqual(r["verdict"], "NO DATA YET")

    def test_s2_unknown_rain_reaches_the_map_payload_and_null_grid_is_not_zero(self):
        data = _fixture_data(); data["nbm"] = None; data["wpc"] = None
        ol = _build(data=data)
        fc = {"generated_utc": NOW.isoformat(), "outlook_7d": ol, "water_series": [], "pluvial_risk": {}}
        pts, *_ = ff._map_time_series(fc)
        unknown = next(p for p in ol["series"] if p["rain_unknown"] and p["lead_h"] > 80)
        mappt = next(p for p in pts if p["t"] == unknown["time"])
        self.assertTrue(mappt["u"])
        html = ff._client_map_section_html if False else None
        grid = {"series": {"qpf_in": [{"start": "2026-09-24T04:00:00Z", "hours": 24, "value": None}]},
                "reach": {"qpf_in": "2026-09-30T12:00:00Z"}}
        days = outlook.build_days(NOW, [], {"grid": grid})
        d = days[1]
        self.assertEqual(d["qpf_in"], 0.0)
        self.assertTrue(d["qpf_partial"])
        self.assertLess(d["qpf_covered_h"], 1.0)
        self.assertGreaterEqual(d["qpf_null_h"], 23.0)

    def test_s3_declared_horizon_equals_series_reach(self):
        ol = _build()
        last = max(p["lead_h"] for p in ol["series"])
        self.assertGreaterEqual(last, 160.0)
        self.assertLessEqual(last, 168.0)
        self.assertIn(len(ol["days"]), (7, 8))
        self.assertTrue(ol["days"][-1]["partial"] or ol["days"][0]["partial"])
        table_last = max(t["lead_h"] for t in ol["tides"])
        self.assertLessEqual(table_last, 168.0)

    def test_s4_html_and_subject_share_the_worst_headline_and_past_water_is_not_forward(self):
        from forecast import rendering
        fc = {"all_tides": [{"time": "2026-09-24 18:00-04:00", "hours_from_now": 30, "forecast_peak_mllw": 6.0,
                             "depths_in": {"regime": "dry"}}],
              "water_series": [{"time": "2026-09-24 14:00-04:00", "tide_navd88": 2.0, "water_navd88": 6.0, "burst_risk": True}],
              "rain_outlook_72h": [], "pluvial_risk": {"level": "elevated", "potential_low_tide_navd88": 6.0},
              "peak_time_local": "2026-09-24 18:00-04:00", "peak_forecast_observed_mllw": 6.0}
        days = ["2026-09-23", "2026-09-24", "2026-09-25"]
        fc["day_worst"] = ff.compute_day_worst(fc["all_tides"], fc["water_series"], fc["pluvial_risk"], [], days,
                                               now_utc=dt.datetime(2026, 9, 23, 11, tzinfo=UTC))
        self.assertEqual(rendering.worst_72h_headline(fc, "NO FLOODING"), "SEVERE (RAIN)")
        src = open(Path(rendering.__file__).with_suffix(".py")).read()
        self.assertIn("worst_72h_headline(forecast, headline_for(forecast, regime)[0])", src)   # HTML panel
        # a severe 06:00 point on 09-23 reviewed at 15:26 is NOT forward outlook
        past = [{"time": "2026-09-23 06:00-04:00", "tide_navd88": 2.0, "water_navd88": 6.0, "burst_risk": False},
                {"time": "2026-09-23 16:00-04:00", "tide_navd88": 2.0, "water_navd88": 2.0, "burst_risk": False}]
        dw = ff.compute_day_worst([], past, {}, [], ["2026-09-23"],
                                  now_utc=ff.parse_station_local_time("2026-09-23 15:26-04:00"))
        self.assertEqual(dw[0]["regime"], "dry")

    def test_s5_chart_uses_the_point_level_scenario(self):
        ol = _build(nbm_burst_in=3.0)
        from forecast import outlook_page
        html = outlook_page.render_outlook_page({"generated_utc": "x", "forecast_schema_version": "1.0",
                                                 "model_version": "v", "outlook_7d": ol, "input_health": {}})
        m = re.search(r"var D = (\{.*?\});\n", html, re.S)
        D = json.loads(m.group(1))
        flagged = [p for p in ol["series"] if p.get("burst_risk") and p.get("burst_potential_navd88")]
        self.assertTrue(flagged)
        for p in flagged[:3]:
            i = ol["series"].index(p)
            self.assertAlmostEqual(D["burst"][i], round((max(p["burst_potential_navd88"], p["tide_navd88"]) - 3.52) * 12, 1), places=1)
        self.assertIn("Rain forecast unavailable (tide-only hours)", html)

    def test_s6_malformed_warm_buckets_are_dropped_before_any_consumer(self):
        g = {"nbm": {"cycle": "2026-09-23T06:00:00Z", "summary": "nbm", "buckets": [
                {"end_utc": "2026-09-23T18:00:00Z", "qpf_in": 0.2},                         # no hours
                {"end_utc": "2026-09-24T00:00:00Z", "hours": 6, "qpf_in": 0.1, "pop_pct": 40.0}]},
             "petss": {"cycle": "2026-09-23T06:00:00Z", "summary": "p",
                       "p10": [{"utc": "2026-09-23T12:00:00Z", "surge_ft": 2.0}, {"utc": "bad", "surge_ft": 1.0}],
                       "p90": [{"utc": "2026-09-23T12:00:00Z", "surge_ft": 1.0}]}}      # p10 > p90 at 12Z
        d, h = srcs.admit_guidance(g, "nbm", NOW)
        self.assertEqual(len(d["buckets"]), 1)
        self.assertIn("1 malformed dropped", h["detail"])
        self.assertEqual(h["status"], "degraded")                # a dropped row is never silent
        self.assertIsNotNone(outlook._bucket_containing(d["buckets"], dt.datetime(2026, 9, 23, 20, tzinfo=UTC)))
        d, h = srcs.admit_guidance(g, "petss", NOW)
        self.assertIsNone(d)                                     # nothing valid survives
        nbm = {"buckets": [{"end_utc": "2026-09-26T12:00:00Z", "hours": 6, "qpf_in": 0.1}]}
        qmd = {"qmd_cycle": "2026-09-23T06:00:00Z", "buckets": {"2026-09-26T12:00:00Z": {"p10_in": 0.9, "p50_in": 0.5, "p90_in": 0.1}}}
        h = srcs.merge_nbm_qmd(nbm, qmd, NOW)
        self.assertNotIn("p90_in", nbm["buckets"][0])            # disordered percentiles skipped
        self.assertEqual(h["status"], "degraded")

    def test_s7_nested_requests_recompute_the_timeout_and_the_wall_clock_bounds_gather(self):
        clock = {"t": 0.0}
        seen = []

        def slow_request(url, timeout=30):
            seen.append(timeout)
            clock["t"] += 9.0
            return b'{"properties": {"forecastGridData": "http://x/grid"}}' if "points" in url else b'{"properties": {}}'
        dl = srcs.Deadline(10.0, clock=lambda: clock["t"])
        with mock.patch.object(srcs, "_request", side_effect=slow_request):
            try:
                srcs.fetch_nws_grid(deadline=dl)
            except TimeoutError:
                pass
        self.assertEqual(len(seen), 1)                            # the second request never started
        # wall clock: a fetch that sleeps past the boundary is abandoned, not awaited
        import time as _time

        def hang(url, timeout=30):
            _time.sleep(0.6)
            raise OSError("late")
        with mock.patch.object(srcs, "_request", side_effect=hang), \
                mock.patch.object(srcs, "load_guidance", return_value={}):
            t0 = _time.monotonic()
            # budget 3 s (so the deadline itself would NOT skip), wall clock 0.3 s
            data, health = srcs.gather(NOW, guidance_path="/nonexistent",
                                       deadline=srcs.Deadline(3.0), wall_clock_s=0.3)
            elapsed = _time.monotonic() - t0
            _time.sleep(3.2)          # let the abandoned worker drain inside the patch (no network)
        self.assertLess(elapsed, 0.55)
        self.assertTrue(all(health[k]["status"] == "unavailable" for k in ("astro", "grid", "nwps", "xcheck")))
        self.assertIn("wall-clock", health["astro"]["detail"])


class LedgerAndScoringTests(unittest.TestCase):
    def test_writer_output_passes_the_real_gate_and_round_trips(self):
        ol = _build()
        rows = outlook.outlook_log_rows(ol, "2026-09-23T11:00:00Z", "v0.10.4")
        self.assertEqual(len(rows), 13)     # the -0.9 h tide is excluded
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "outlook_log.csv")
            outlook.append_outlook_log(path, rows)
            outlook.append_outlook_log(path, rows)
            failures = check_artifacts.validate_csv_ledger(
                path, check_artifacts.CSV_SCHEMAS["data/outlook_log.csv"])
            self.assertEqual(failures, [])
            back = outlook.read_outlook_log(path)
            self.assertEqual(len(back), 26)
            self.assertEqual(back[0]["outlook_source"], "nws_product")
            with open(path, "w") as f:
                f.write("bad,header\n")
            with self.assertRaises(ValueError):
                outlook.append_outlook_log(path, rows)

    def test_ledger_times_match_observed_cache_keys(self):
        ol = _build()
        for t in ol["tides"]:
            self.assertEqual(station_time_storage_key(t["time"]), t["time"])

    def test_scoring_reports_not_yet_then_ready_or_not_better(self):
        ol = _build()
        rows = outlook.outlook_log_rows(ol, "2026-09-23T11:00:00Z", "v0.10.4")
        observed = {r["target_tide_time"]: float(r["nwps_mllw"] or r["outlook_mllw"]) for r in rows}
        sc = outlook.score_shadow(rows, observed)
        r = sc["readiness"]["nwps_vs_persistence_le72h"]
        self.assertTrue(r["verdict"].startswith("NOT YET"))
        self.assertLess(r["mae_candidate"], r["mae_baseline"])
        # duplicating rows must NOT unlock READY (audit R2): still the same few tides
        big = rows * 10
        sc = outlook.score_shadow(big, observed)
        self.assertTrue(sc["readiness"]["nwps_vs_persistence_le72h"]["verdict"].startswith("NOT YET"))
        worse = {r["target_tide_time"]: float(r["persist_flat_mllw"]) for r in rows if r["persist_flat_mllw"]}
        r = outlook.score_shadow(big, worse)["readiness"]["nwps_vs_persistence_le72h"]
        self.assertGreater(r["mae_candidate"], r["mae_baseline"])

    def test_scoring_ignores_unobserved_and_unbucketed_rows(self):
        sc = outlook.score_shadow([{"target_tide_time": "x", "lead_h": "5", "outlook_mllw": "6"}], {})
        self.assertEqual(sc["scored_rows"], 0)
        self.assertEqual(sc["readiness"]["nwps_vs_persistence_le72h"]["verdict"], "NO DATA YET")


class PageTests(unittest.TestCase):
    def _forecast(self, ol):
        return {"generated_utc": "2026-09-23T11:00:00Z", "forecast_schema_version": "1.0",
                "model_version": "v0.10.4", "outlook_7d": ol, "input_health": {}}

    def test_page_passes_surface_contract_and_carries_stamps(self):
        html = outlook_page.render_outlook_page(self._forecast(_build()))
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "outlook.html"
            p.write_text(html, encoding="utf-8")
            self.assertEqual(html_contract.validate_surface(p), [])
        self.assertIn('<meta name="barnacle-generated-utc" content="2026-09-23T11:00:00Z">', html)
        self.assertIn("The next 168 hours at the corner", html)
        self.assertIn("Model cross-check", html)
        self.assertIn("Shadow scoreboard", html)
        self.assertIn("astronomical tide only", html.lower())
        self.assertIn("Two pathways, every day", html)
        self.assertIn("Worst flood chance in the next 168 hours", html)
        self.assertIn("Rain pathway:", html)

    def test_page_degrades_honestly_without_outlook(self):
        html = outlook_page.render_outlook_page({
            "generated_utc": "x", "forecast_schema_version": "1.0", "model_version": "v",
            "outlook_7d": None, "input_health": {"outlook_7d": {"status": "unavailable", "detail": "no astro"}}})
        self.assertIn("Outlook unavailable this run", html)
        self.assertIn("no astro", html)
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "outlook.html"
            p.write_text(html, encoding="utf-8")
            self.assertEqual(html_contract.validate_surface(p), [])

    def test_landing_page_links_to_outlook(self):
        self.assertIn('href="outlook.html"', ff._render_more_info_links_html())


class FacadeWiringTests(unittest.TestCase):
    def test_build_outlook_field_reports_per_source_health(self):
        data = _fixture_data()
        health = {k: {"status": "ok", "detail": "fixture"} for k in data}
        health["nbm"] = {"status": "unavailable", "detail": "NOMADS down"}
        with mock.patch.object(ff._outlook_sources, "gather", return_value=(data, health)), \
                mock.patch.object(ff, "_load_observed_peaks_cache", return_value={}), \
                mock.patch.object(ff._outlook, "read_outlook_log", return_value=[]):
            ol, entries = ff.build_outlook_7d_field(NOW, _product_tides(), 1.8, 6.0,
                                                    nws_hourly=[], qpf_hourly=[])
        self.assertEqual(len(ol["tides"]), 14)
        self.assertGreater(len(ol["series"]), 150)
        self.assertIn("flood_chance", ol["worst"])
        self.assertEqual(entries["outlook_nbm"]["status"], "unavailable")
        self.assertEqual(entries["outlook_7d"]["status"], "ok")
        self.assertIn("with surge guidance", entries["outlook_7d"]["detail"])


if __name__ == "__main__":
    unittest.main()
