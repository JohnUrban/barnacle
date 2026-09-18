import unittest

from forecast import flood_forecast_daily as ff
from history.scripts import assess_model_v0_11 as assessment
from history.scripts import reproduce_v0_10_3_fill_candidate as fill_candidate


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

    def test_moving_head_candidate_is_not_universally_better(self):
        candidate = self.result["time_varying_head_candidate"]
        self.assertEqual(candidate["fixture"]["rows"], 102)
        self.assertEqual(candidate["fixture"]["astronomical_sample_rows"], 204)
        replay = candidate["historical_head_replay"]
        oct30 = replay["2025-10-30"]
        self.assertLess(
            oct30["moving_astronomy_constant_surge"]["rmse"],
            oct30["fixed_head"]["rmse"],
        )
        dec19 = replay["2025-12-19"]
        self.assertGreaterEqual(
            dec19["moving_astronomy_constant_surge"]["rmse"],
            dec19["fixed_head"]["rmse"],
        )

    def test_moving_head_changes_standardized_rising_and_falling_tanks(self):
        response = self.result["time_varying_head_candidate"][
            "standardized_tank_response"
        ]
        self.assertGreater(response["largest_rise"]["endpoint_delta_in"], 0.5)
        self.assertLess(response["largest_fall"]["endpoint_delta_in"], -0.3)

    def test_surge_age_boundary_does_not_cover_every_accepted_head(self):
        boundary = self.result["time_varying_head_candidate"]["age_boundary"]
        self.assertEqual(
            boundary["max_initial_age_for_full_horizon_surge_validity_min"],
            15,
        )
        self.assertGreater(
            boundary["head_observation_max_age_min"],
            boundary["max_initial_age_for_full_horizon_surge_validity_min"],
        )

    def test_fill_candidate_is_frozen_without_changing_production(self):
        result = fill_candidate.verify_candidate()
        self.assertEqual(result["candidate_model_version"], "v0.10.3")
        self.assertEqual(result["production_model_version"], "v0.10.2")
        self.assertLess(result["worst_reference_error_in"], 1e-10)
        self.assertAlmostEqual(
            result["worst_production_correction_in"], 0.09, places=12
        )


if __name__ == "__main__":
    unittest.main()
