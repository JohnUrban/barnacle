import unittest

from forecast import flood_forecast_daily as ff
from history.scripts import assess_model_v0_11 as assessment


class ModelV011AssessmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = assessment.assess()

    def test_corrected_fill_never_starts_below_non_grid_base(self):
        curve = ff._load_stage_curve()
        base = 0.08
        current = ff._pluvial_fill(curve, base, 0.001)
        corrected = assessment.corrected_pluvial_fill(curve, base, 0.001)
        self.assertLess(current, base)
        self.assertGreaterEqual(corrected, base)

    def test_lag_evidence_rejects_one_replacement_constant(self):
        lag = self.result["lag_sensitivity"]
        self.assertEqual(lag["event8"]["best_sampled_lag_min"], 10)
        self.assertEqual(lag["event9_round1"]["best_sampled_lag_min"], 3)

    def test_point_forcing_is_not_a_universal_improvement(self):
        forcing = self.result["forcing"]
        self.assertGreater(
            abs(forcing["event7"]["point"]["peak_error_in"]),
            abs(forcing["event7"]["box_mean"]["peak_error_in"]),
        )
        self.assertLess(
            abs(forcing["event8"]["point"]["peak_error_in"]),
            abs(forcing["event8"]["box_mean"]["peak_error_in"]),
        )

    def test_segmented_hourly_record_rejects_legacy_bias_retune(self):
        tide = self.result["tide_accuracy"]
        self.assertGreater(tide["legacy_daily"]["mean_bias"], 0.30)
        current = tide["hourly_join"]["by_model_version"]["v0.10.2"]
        self.assertLess(abs(current["mean_bias"]), 0.05)

    def test_fixed_head_can_move_materially_inside_projection(self):
        change = self.result["tide_head_sample"][
            "largest_45_minute_change"
        ]["change_ft"]
        self.assertGreater(abs(change), 0.52)


if __name__ == "__main__":
    unittest.main()
