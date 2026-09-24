"""v0.10.6 surge decay toward the recent average (owner decisions
2026-09-23: fresh-surge-decay, missing-surge-ladder, missing-surge-ladder-decay)."""
import datetime as dt
import json
import math
import os
import tempfile
import unittest
from unittest.mock import patch

from forecast import flood_forecast_daily as ff
from forecast import outlook, surge_decay as sd, surge_mean
try:
    from tests import test_selective_recovery as rec
except ImportError:                     # discover -s tests puts tests/ on sys.path
    import test_selective_recovery as rec

_REAL_LOAD_STATE = ff._load_surge_state          # the tests of the file I/O itself use these
_REAL_MEAN_LOAD = surge_mean.load

# never read the repo's live surge state or the warm job's mean
_isolation = [patch.object(ff, "_load_surge_state", return_value=None),
              patch.object(ff._surge_mean, "load", return_value=None)]


def setUpModule():
    for p in _isolation:
        p.start()


def tearDownModule():
    for p in _isolation:
        p.stop()

UTC = dt.timezone.utc
T0 = dt.datetime(2026, 9, 24, 0, 0, tzinfo=UTC)


class DecayMathTests(unittest.TestCase):
    def test_formula_lookback_and_limits(self):
        a = sd.choose_anchor(T0, 0.5, "test", fresh=(2.5, T0))
        self.assertEqual(a.rung, "fresh")
        self.assertEqual(a.at(T0 - dt.timedelta(hours=3)), 2.5)          # lookback keeps the reading
        self.assertAlmostEqual(a.at(T0 + dt.timedelta(hours=36)), 0.5 + 2.0 * math.exp(-1), places=12)
        self.assertAlmostEqual(a.at(T0 + dt.timedelta(hours=24)), 0.5 + 2.0 * math.exp(-24 / 36), places=12)
        self.assertAlmostEqual(a.at(T0 + dt.timedelta(days=30)), 0.5, places=6)
        neg = sd.choose_anchor(T0, 0.5, "test", fresh=(-1.0, T0))
        self.assertGreater(neg.at(T0 + dt.timedelta(hours=12)), -1.0)   # anti-surge relaxes UP to the mean

    def test_decay_runs_from_the_reading_time_not_the_run_time(self):
        a = sd.choose_anchor(T0, 0.5, "test", stale=(2.5, T0 - dt.timedelta(hours=12)))
        self.assertEqual(a.rung, "stale-download")
        self.assertAlmostEqual(a.at(T0), 0.5 + 2.0 * math.exp(-12 / 36), places=12)
        self.assertIn("12 h ago", a.label(T0))


class LadderTests(unittest.TestCase):
    def test_newest_valid_reading_wins(self):
        a = sd.choose_anchor(T0, 0.5, "m", stale=(1.0, T0 - dt.timedelta(hours=3)),
                             state=(2.0, T0 - dt.timedelta(hours=30)))
        self.assertEqual((a.rung, a.surge_ft), ("stale-download", 1.0))
        a = sd.choose_anchor(T0, 0.5, "m", state=(2.0, T0 - dt.timedelta(hours=30)))
        self.assertEqual(a.rung, "stale-state")

    def test_invalid_and_future_readings_are_ignored(self):
        for bad in ((float("nan"), T0), (1.0, T0.replace(tzinfo=None)), (99.0, T0),
                    (1.0, T0 + dt.timedelta(hours=1))):
            self.assertEqual(sd.choose_anchor(T0, 0.5, "m", stale=bad).rung, "typical-offset")

    def test_snap_to_typical_offset_is_labeled(self):
        old = sd.choose_anchor(T0, 0.5, "m", state=(3.0, T0 - dt.timedelta(hours=200)))
        self.assertEqual(old.rung, "typical-offset")
        faded = sd.choose_anchor(T0, 0.5, "m", state=(0.52, T0 - dt.timedelta(hours=5)))
        self.assertEqual(faded.rung, "typical-offset")                  # departure < 0.05 ft
        self.assertIn("surge unavailable, using the typical offset", faded.label(T0))
        self.assertEqual(faded.at(T0 + dt.timedelta(hours=10)), 0.5)
        near = sd.choose_anchor(T0, 0.5, "m", fresh=(0.52, T0))
        self.assertEqual(near.rung, "fresh")                            # a fresh reading never snaps

    def test_mean_must_be_finite(self):
        with self.assertRaises(ValueError):
            sd.choose_anchor(T0, float("nan"), "m")


class MeanTests(unittest.TestCase):
    def rec(self, **kw):
        base = {"mean_ft": 0.53, "computed_utc": "2026-09-23T12:00:00Z", "n_hours": 8184,
                "window_start": "2025-09-25", "window_end": "2026-08-31"}
        base.update(kw)
        return base

    def test_age_gate_and_fallback(self):
        m, src, h = sd.resolve_mean(T0, self.rec())
        self.assertEqual((m, h["status"]), (0.53, "ok"))
        m, src, h = sd.resolve_mean(T0, self.rec(computed_utc="2026-09-10T00:00:00Z"))
        self.assertEqual((m, h["status"]), (0.53, "degraded"))
        for bad in (None, {"mean_ft": "x"}, self.rec(n_hours=100), self.rec(mean_ft=7.0),
                    self.rec(computed_utc="2026-07-01T00:00:00Z")):
            m, src, h = sd.resolve_mean(T0, bad)
            self.assertEqual((m, h["status"]), (sd.SURGE_MEAN_FALLBACK_FT, "degraded"), bad)
            self.assertIn("fallback", src)

    def test_warm_job_mean_is_over_paired_hours_and_keeps_old_on_failure(self):
        hours = [(T0 - dt.timedelta(hours=h)).strftime("%Y-%m-%d %H:%M") for h in range(1, 7300)]
        def get(params, timeout):
            if params["product"] == "hourly_height":
                return {"data": [{"t": t, "v": "5.6"} for t in hours] + [{"t": "2026-01-01 00:30", "v": ""}]}
            return {"predictions": [{"t": t, "v": "5.0"} for t in hours]}
        r = surge_mean.compute(T0, get=get)
        self.assertAlmostEqual(r["mean_ft"], 0.6, places=6)
        self.assertEqual(r["n_hours"], 7299)
        with tempfile.TemporaryDirectory() as d, patch.object(surge_mean, "load", _REAL_MEAN_LOAD):
            path = os.path.join(d, "m.json")
            r1, note = surge_mean.refresh(T0, path=path, get=get)
            self.assertEqual(note, "recomputed")
            r2, note = surge_mean.refresh(T0 + dt.timedelta(hours=3), path=path, get=get)
            self.assertIn("kept", note)
            r3, note = surge_mean.refresh(T0 + dt.timedelta(days=2), path=path,
                                          get=lambda p, t: (_ for _ in ()).throw(OSError("down")))
            self.assertIn("failed", note)
            self.assertEqual(r3, r1)
        with self.assertRaises(ValueError):
            surge_mean.compute(T0, get=lambda p, t: {"data": [], "predictions": []})


class StateFileTests(unittest.TestCase):
    def test_round_trip_and_bad_file(self):
        with tempfile.TemporaryDirectory() as d, patch.object(ff, "_load_surge_state", _REAL_LOAD_STATE):
            path = os.path.join(d, "s.json")
            self.assertIsNone(ff._load_surge_state(path))
            ff._save_surge_state(1.2345, T0, T0, path=path)
            self.assertEqual(ff._load_surge_state(path), (1.2345, T0))
            with open(path, "w") as f:
                f.write("{not json")
            self.assertIsNone(ff._load_surge_state(path))


class WholeBuildTests(unittest.TestCase):
    """The real build_forecast with frozen inputs (tests/test_selective_recovery.build)."""

    def test_fresh_reading_decays_along_the_curve(self):
        f = rec.build(surge=2.0)
        dec = f["water_series_input"]["decay"]
        self.assertEqual((dec["rung"], dec["surge_obs_ft"], dec["tau_h"]), ("fresh", 2.0, 36.0))
        obs = dt.datetime.fromisoformat(dec["observation_utc"].replace("Z", "+00:00"))
        last = f["water_series"][-1]
        t = ff.parse_station_local_time(last["time"]).astimezone(UTC)
        expect = 1.0 + (0.54 + (2.0 - 0.54) * math.exp(-(t - obs).total_seconds() / 3600 / 36)) \
            + ff.LOCAL_ENHANCEMENT_FT + ff.MLLW_TO_NAVD88_OFFSET
        self.assertAlmostEqual(last["tide_navd88"], round(expect, 3), places=3)
        self.assertLess(last["tide_navd88"], f["water_series"][0]["tide_navd88"])

    def test_stale_download_rung(self):
        stale = (1.5, rec.NOW.astimezone(UTC) - dt.timedelta(hours=3))
        with patch.dict(ff._LAST_SURGE_READING, {"reading": stale}), \
                patch.object(ff, "fetch_current_surge", return_value=None):
            f = rec.build(surge=None)
        si = f["water_series_input"]
        self.assertEqual((si["source"], si["decay"]["rung"], si["status"]), ("surge-persistence", "stale-download", "degraded"))
        self.assertIn("3 h ago", si["detail"])
        self.assertIn("surge_observation", f["degraded_inputs"])

    def test_stale_state_rung(self):
        state = (1.8, rec.NOW.astimezone(UTC) - dt.timedelta(hours=10))
        with patch.object(ff, "_load_surge_state", return_value=state):
            f = rec.build(surge=None)
        self.assertEqual(f["water_series_input"]["decay"]["rung"], "stale-state")
        self.assertAlmostEqual(f["water_series_input"]["surge_ft"],
                               0.54 + (1.8 - 0.54) * math.exp(-10 / 36), places=3)

    def test_build_forecast_never_writes_the_state_file(self):
        with patch.object(ff, "_save_surge_state") as save:
            rec.build(surge=1.0)
        save.assert_not_called()


class OutlookRungTests(unittest.TestCase):
    def test_outlook_persistence_decays_toward_the_mean(self):
        try:
            from tests.test_outlook import _fixture_data, NOW, _health, _product_tides
        except ImportError:
            from test_outlook import _fixture_data, NOW, _health, _product_tides
        data = _fixture_data(); data["nwps"] = None; data["petss"] = None
        ol = outlook.build_outlook_7d(NOW, data, _health(data), _product_tides(), 1.8, 6.0,
                                      ff.classify_regime_from_water,
                                      lambda p: ff.predict_landmark_depths(p, 0.0, False),
                                      ff.MLLW_TO_NAVD88_OFFSET, "v", surge_mean_ft=0.54)
        far = [t for t in ol["tides"] if t["lead_h"] > 100]
        self.assertTrue(far)
        for t in far:
            lead = t["lead_h"]
            self.assertAlmostEqual(t["guidance"]["persist_decay"] - t["astro_mllw"],
                                   0.54 + 1.26 * math.exp(-lead / 36), delta=0.02)
        self.assertEqual(ol["assumptions"]["persistence_decay_mean_ft"], 0.54)


if __name__ == "__main__":
    unittest.main()


def srcs_hour(stamp):
    return outlook._utc(stamp).replace(minute=0, second=0, microsecond=0)


class HourlyEstimatorTests(unittest.TestCase):
    """v0.10.6 checklist items 1-4: one estimator for the chart line and the table."""

    def _ol(self, **kw):
        try:
            from tests import test_outlook as to
        except ImportError:
            import test_outlook as to
        return to, to._build(**kw)

    def test_line_and_table_agree_at_every_tide(self):
        to, ol = self._ol()
        S = {p["time"][:13]: p for p in ol["series"]}
        for t in ol["tides"]:
            p = S.get(t["time"][:13])
            if p is None or t["outlook_source"] not in ("guidance_decay",):
                continue
            # one estimator: the table evaluates it at the tide's minute, the line on
            # the hour; they may differ only by <= 1 h of decay (and 0.01 ft rounding)
            line = p["tide_navd88"] - ff.LOCAL_ENHANCEMENT_FT - ff.MLLW_TO_NAVD88_OFFSET - p["astro_mllw"]
            table = t["outlook_mllw"] - t["astro_mllw"]
            self.assertLessEqual(abs(table - line), abs(line) * (1 - math.exp(-1 / 36)) + 0.011)

    def test_sources_in_order_and_petss_used_hourly(self):
        to, ol = self._ol()
        order = ["observed_decay", "nws_product", "nwps", "petss_hourly", "guidance_decay"]
        seen = []
        for p in ol["series"]:
            if not seen or seen[-1] != p["surge_source"]:
                seen.append(p["surge_source"])
        self.assertIn("petss_hourly", seen)
        self.assertEqual(seen[-1], "guidance_decay")
        ranks = [order.index(x) for x in seen if x in order and x not in ("nws_product", "nwps")]
        self.assertEqual(ranks, sorted(ranks))                           # never back to an earlier source
        # P-ETSS fills exactly the hours the gauge forecast does not cover, out to 102 h
        nwps_hours = {srcs_hour(q["utc"]) for q in to._fixture_data()["nwps"]["series"]}
        petss = [p for p in ol["series"] if p["surge_source"] == "petss_hourly"]
        self.assertTrue(petss)
        for p in petss:
            self.assertLessEqual(p["lead_h"], 102)
            self.assertTrue(srcs_hour(p["utc"]) not in nwps_hours or p["lead_h"] > 72)

    def test_decay_starts_from_the_last_guidance_value_without_smoothing(self):
        to, ol = self._ol()
        S = ol["series"]
        i = next(k for k, p in enumerate(S) if p["surge_source"] == "guidance_decay" and k > 0)
        last_g, first_d = S[i - 1], S[i]
        sg = lambda p: p["tide_navd88"] - ff.LOCAL_ENHANCEMENT_FT - ff.MLLW_TO_NAVD88_OFFSET - p["astro_mllw"]
        # one hour of decay toward the mean (0.0 in this fixture build), no blending
        self.assertAlmostEqual(sg(first_d), sg(last_g) * math.exp(-1 / 36), delta=0.01)

    def test_advisory_corrections_are_reported_and_chart_draws_sources(self):
        from forecast import outlook_page
        import re
        to, ol = self._ol()
        self.assertTrue(ol["assumptions"]["advisory_corrections"])
        html = outlook_page._chart(ol)
        D = json.loads(re.search(r"var D = (\{.*?\});", html, re.S).group(1))
        self.assertEqual([r["src"] for r in D["runs"]][-1], "guidance_decay")
        self.assertTrue(any(v is not None for v in D["advisory"]))
        self.assertIn("A step at a boundary is a change of source", html)

    def test_no_guidance_matches_the_production_rule(self):
        to, _ = self._ol()
        data = to._fixture_data(); data["nwps"] = None; data["petss"] = None
        obs = (1.8, to.NOW - dt.timedelta(minutes=20))
        est = outlook.hourly_surge_estimator(to.NOW, data, [], 0.54, obs)
        prod = sd.SurgeAnchor("fresh", 0.54, "m", 1.8, obs[1])
        for h in (1, 12, 30, 100):
            t = to.NOW + dt.timedelta(hours=h)
            s, src = est(t)
            self.assertEqual(src, "observed_decay")
            self.assertAlmostEqual(s, prod.at(t), places=9)


class SourceExpiryTests(unittest.TestCase):
    """Checklist item 4/6: expired or missing sources fall to the next rung,
    visibly, and the tail decays from whatever guidance was last available."""

    def _est(self, drop):
        try:
            from tests import test_outlook as to
        except ImportError:
            import test_outlook as to
        data = to._fixture_data()
        for k in drop:
            data[k] = None
        return to, data, outlook.hourly_surge_estimator(to.NOW, data, [], 0.54, (1.8, to.NOW))

    def test_no_gauge_forecast_uses_petss_from_the_start(self):
        to, data, est = self._est(["nwps"])
        s, src = est(to.NOW + dt.timedelta(hours=5))
        self.assertEqual(src, "petss_hourly")

    def test_no_petss_decays_from_the_last_gauge_hour(self):
        to, data, est = self._est(["petss"])
        last = max(outlook._utc(p["utc"]) for p in data["nwps"]["series"])
        s_last, src_last = est(last)
        self.assertIn(src_last, ("nwps", "nws_product"))
        s, src = est(last + dt.timedelta(hours=10))
        self.assertEqual(src, "guidance_decay")
        self.assertAlmostEqual(s, 0.54 + (s_last - 0.54) * math.exp(-10 / 36), places=9)

    def test_nothing_but_the_reading(self):
        to, data, est = self._est(["nwps", "petss"])
        self.assertEqual(est(to.NOW + dt.timedelta(hours=50))[1], "observed_decay")
        est0 = outlook.hourly_surge_estimator(to.NOW, data, [], 0.54, None)
        self.assertEqual(est0(to.NOW + dt.timedelta(hours=50)), (0.54, "typical_offset"))


class GoldenTests(unittest.TestCase):
    """Rule 5 class (a): the v0.10.6 formula change carries a NEW replay golden."""

    def test_v0_10_6_golden_reproduces(self):
        import importlib.util
        from pathlib import Path
        path = Path(__file__).resolve().parents[1] / "history" / "scripts" / "reproduce_v0_10_6.py"
        spec = importlib.util.spec_from_file_location("reproduce_v0_10_6", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        golden = mod.verify()
        self.assertEqual(golden["constants"]["tau_h"], 36.0)
