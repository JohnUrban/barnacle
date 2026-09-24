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
        m, src, h = sd.resolve_mean(T0, self.rec(computed_utc="2026-09-18T00:00:00Z"))
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
