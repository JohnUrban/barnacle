"""7-day outlook (2026-09-23): adapters parse captured products, the
guidance ladder picks sources by lead, the ledger round-trips through the
real gate, scoring reports readiness honestly, the page passes the
surface contract, and none of it touches alerts."""

import csv
import datetime as dt
import json
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

UTC = dt.timezone.utc
FIX = Path(__file__).parent / "fixtures"
NOW = dt.datetime(2026, 9, 23, 11, 0, tzinfo=UTC)
CYCLE = dt.datetime(2026, 9, 23, 6, tzinfo=UTC)


def _fixture_data():
    return {
        "astro": json.loads((FIX / "astro_highs_20260923.json").read_text()),
        "grid": srcs.parse_nws_grid(json.loads(
            (FIX / "nws_grid_phi_61_102_20260923.json").read_text())["properties"]),
        "nwps": srcs.parse_nwps(json.loads((FIX / "nwps_sdhn4_stageflow_20260923.json").read_text())),
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


def _build(data=None, surge=1.8):
    data = data or _fixture_data()
    return outlook.build_outlook_7d(
        NOW, data, _health(data), _product_tides(), surge, 6.0,
        ff.classify_regime_from_water, lambda p: ff.predict_landmark_depths(p, 0.0, False),
        ff.MLLW_TO_NAVD88_OFFSET, "v0.10.4")


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
        try:
            import eccodes  # noqa: F401
        except ImportError:
            self.skipTest("eccodes not installed locally (CI installs it)")
        got = srcs.parse_nbm_subset((FIX / "nbm_t06z_core_f096_house_20260923.grib2").read_bytes())
        self.assertAlmostEqual(got["qpf_in"], 0.14, places=2)
        self.assertAlmostEqual(got["pop_pct"], 51.0, places=0)

    def test_cache_refresh_contract(self):
        cache, now = {}, NOW
        calls = []

        def fetch():
            calls.append(1)
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
        with mock.patch.object(srcs, "MAX_STALE_H", {**srcs.MAX_STALE_H, "nwps": 0}):
            calls.append(1)   # make the next call the failing one
            d5, h5 = srcs.refresh({"nwps": {"fetched_at": "2026-09-23T00:00:00Z", "data": {"v": 9}}},
                                  "nwps", lambda: (_ for _ in ()).throw(OSError("down")), now)
        self.assertIsNone(d5)
        self.assertEqual(h5["status"], "unavailable")


class LadderTests(unittest.TestCase):
    def test_sources_by_lead(self):
        ol = _build()
        by = {t["time"]: t for t in ol["tides"]}
        self.assertEqual(by["2026-09-23 18:19-04:00"]["outlook_source"], "nws_product")
        self.assertEqual(by["2026-09-23 18:19-04:00"]["outlook_mllw"], 6.9)
        self.assertEqual(by["2026-09-26 08:01-04:00"]["outlook_source"], "petss_mid")   # 73 h: product row absent, NWPS out of reach
        self.assertEqual(by["2026-09-27 20:58-04:00"]["outlook_source"], "persist_decay")  # 110 h
        self.assertEqual(len(ol["tides"]), 14)
        self.assertTrue(all(t["band_lo_mllw"] is None for t in ol["tides"] if t["lead_h"] > 102))

    def test_astronomy_layer_and_guidance_layer_both_present(self):
        ol = _build()
        for t in ol["tides"]:
            self.assertIsNotNone(t["astro_mllw"])
            self.assertIsNotNone(t["outlook_mllw"])
            self.assertIn(t["outlook_source"], outlook.LADDER + ("astro",))
        for d in ol["days"]:
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
        self.assertEqual(ol["assumptions"]["persistence_decay_tau_h"], 48.0)
        late = [t for t in ol["tides"] if t["outlook_source"] == "persist_decay"]
        self.assertTrue(late)
        for t in late:
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
        big = rows * 10
        sc = outlook.score_shadow(big, observed)
        self.assertTrue(sc["readiness"]["nwps_vs_persistence_le72h"]["verdict"].startswith("READY"))
        worse = {k: v + 3.0 for k, v in observed.items()}   # everything far off: persistence flat wins? both err; make nwps lose
        worse = {r["target_tide_time"]: float(r["persist_flat_mllw"]) for r in rows if r["persist_flat_mllw"]}
        sc = outlook.score_shadow(big, worse)
        self.assertTrue(sc["readiness"]["nwps_vs_persistence_le72h"]["verdict"].startswith("NOT BETTER"))

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
        self.assertIn("Seven days at the corner", html)
        self.assertIn("Model cross-check", html)
        self.assertIn("Shadow scoreboard", html)
        self.assertIn("astronomy only", html.lower())

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
        with mock.patch.object(ff._outlook_sources, "load_cache", return_value={}), \
                mock.patch.object(ff._outlook_sources, "gather", return_value=(data, health)), \
                mock.patch.object(ff._outlook_sources, "save_cache"), \
                mock.patch.object(ff, "_load_observed_peaks_cache", return_value={}), \
                mock.patch.object(ff._outlook, "read_outlook_log", return_value=[]):
            ol, entries = ff.build_outlook_7d_field(NOW, _product_tides(), 1.8, 6.0)
        self.assertEqual(len(ol["tides"]), 14)
        self.assertEqual(entries["outlook_nbm"]["status"], "unavailable")
        self.assertEqual(entries["outlook_7d"]["status"], "ok")
        self.assertIn("with surge guidance", entries["outlook_7d"]["detail"])


if __name__ == "__main__":
    unittest.main()
