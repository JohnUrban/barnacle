import datetime as dt
import math
import unittest
from pathlib import Path

from forecast import flood_forecast_daily as ff
from history.scripts import reproduce_v0_10_1 as repro


ROOT = Path(__file__).resolve().parents[1]


class ModelReproductionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = repro.load_fixture()
        cls.result = repro.verify_reproduction(cls.fixture)

    def test_pinned_fit_reproduces_documented_rms(self):
        self.assertEqual(self.result["fit"]["points"], 24)
        self.assertAlmostEqual(
            self.result["fit"]["rms_inches"], 1.3167779158984265, places=10
        )
        self.assertEqual(round(self.result["fit"]["rms_inches"], 2), 1.32)

    def test_all_six_hindcast_peaks_and_times_are_golden(self):
        expected = {
            event["id"]: (
                event["expected_peak_stage_in"],
                event["expected_peak_local"],
            )
            for event in self.fixture["hindcast"]["events"]
        }
        self.assertEqual(set(self.result["hindcasts"]), set(expected))
        for event_id, (peak, peak_time) in expected.items():
            actual = self.result["hindcasts"][event_id]
            self.assertAlmostEqual(actual["peak_stage_in"], peak, places=10)
            self.assertEqual(actual["peak_local"], peak_time)

    def test_dec19_observation_time_lands_in_measured_band(self):
        event = next(
            item for item in self.fixture["hindcast"]["events"]
            if item["id"] == "dec19"
        )
        actual = self.result["hindcasts"]["dec19"]["stage_at_observation_in"]
        lower, upper = event["observed_stage_band_in"]
        self.assertGreaterEqual(actual, lower)
        self.assertLessEqual(actual, upper)

    def test_evidence_registry_uses_precise_categories(self):
        evidence = self.fixture["evidence"]
        self.assertEqual(len(evidence["measured_peak_anchors"]), 6)
        self.assertEqual(len(evidence["full_fit_hydrographs"]), 2)
        self.assertEqual(len(evidence["measured_recession_constraints"]), 1)
        self.assertEqual(evidence["out_of_sample_hindcasts"], ["aug3"])

        source = (ROOT / "forecast" / "flood_forecast_daily.py").read_text(
            encoding="utf-8"
        ) + (ROOT / "forecast" / "rendering.py").read_text(encoding="utf-8")
        spec = (ROOT / "model" / "v0.10.1.md").read_text(encoding="utf-8")
        self.assertNotIn("validated on four measured floods", source)
        self.assertNotIn("currently four measured rain events", source)
        # survived audit a2/L2 in the one renderer its close-out missed
        # (found 2026-09-02 sweep); guard both halves of the split
        self.assertNotIn("calibrated on FOUR events", source)
        self.assertIn("six measured peak anchors", source)
        self.assertIn("Measured peak anchors: six", spec)
        self.assertIn("Full fit hydrographs: two", spec)

    def test_prediction_log_cutover_is_frozen(self):
        self.assertEqual(
            self.result["cutover"]["first_v0.10.1_prediction_utc"],
            "2026-07-21T15:27:30Z",
        )

    def test_all_anchor_recipe_has_no_machine_local_path(self):
        # widened 2026-09-03 (audit sweep): the 2026-09-01 copies and two
        # fit scripts sat outside the original guard's file list
        targets = [
            ROOT / "assets" / "observations" / d / "analysis" / name
            for d in ("2026-08-03", "2026-09-01")
            for name in ("all_anchors_model.py", "all_anchors_figure.py")
        ] + [
            ROOT / "history" / "scripts" / "tank_model_fit.py",
            ROOT / "history" / "scripts" / "fit_crdt.py",
            ROOT / "history" / "scripts" / "event_hindcast.py",
        ]
        for path in targets:
            source = path.read_text(encoding="utf-8")
            self.assertNotIn("/private/tmp/", source, path.name)
            self.assertNotIn("/Users/", source, path.name)


class ModelPhysicsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ff._STAGE_CURVE = None
        cls.curve = ff._load_stage_curve()

    def test_stage_curve_and_storage_response_are_monotonic(self):
        stages = [point[0] for point in self.curve]
        areas = [point[1] for point in self.curve]
        self.assertTrue(all(left < right for left, right in zip(stages, stages[1:])))
        self.assertTrue(all(area > 0 for area in areas))
        filled = [
            ff._pluvial_fill(self.curve, 0.0, volume)
            for volume in (0.0, 1_000.0, 10_000.0, 100_000.0, 500_000.0)
        ]
        self.assertTrue(all(left <= right for left, right in zip(filled, filled[1:])))
        self.assertAlmostEqual(filled[2], 3.852626795128158, places=10)

    def test_zero_and_rising_rain_have_zero_then_rising_response(self):
        bay = 2.5
        rates = (0.0, 0.2, 0.25, 0.5, 1.0, 2.0, 4.0)
        depths = [
            (ff.estimate_pluvial_water(rate, bay, model="tank") - 3.52) * 12.0
            for rate in rates
        ]
        self.assertEqual(depths[:3], [0.0, 0.0, 0.0])
        self.assertTrue(all(left <= right for left, right in zip(depths, depths[1:])))
        self.assertGreater(depths[-1], depths[3])

    def test_head_dependent_drainage_changes_low_rate_response(self):
        rate = 0.2
        open_drain = ff.estimate_pluvial_water(rate, 2.5, model="tank")
        blocked_drain = ff.estimate_pluvial_water(rate, 3.52, model="tank")
        self.assertEqual(open_drain, ff.PLUVIAL_STREET_BASE)
        self.assertGreater(blocked_drain, ff.PLUVIAL_STREET_BASE)

    def test_dynamic_tank_rises_then_recedes_without_negative_mass(self):
        start = dt.datetime(2026, 1, 1)
        times = [start + dt.timedelta(minutes=5 * index) for index in range(37)]
        rain = [2.0 if index < 12 else 0.0 for index in range(len(times))]
        water = ff.simulate_pluvial_series(
            times, [2.5] * len(times), rain, dt_min=1.0
        )
        depths = [
            0.0 if value is None else (value - ff.PLUVIAL_STREET_BASE) * 12.0
            for value in water
        ]
        peak_index = max(range(len(depths)), key=depths.__getitem__)
        self.assertGreater(peak_index, 0)
        self.assertGreater(depths[peak_index], 15.0)
        self.assertLess(depths[-1], depths[peak_index])
        self.assertTrue(all(math.isfinite(depth) and depth >= 0.0 for depth in depths))


if __name__ == "__main__":
    unittest.main()
