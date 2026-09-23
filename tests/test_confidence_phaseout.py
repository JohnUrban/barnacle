"""2026-09-23: the confidence labels are gone from every human surface;
measured error by lead time replaces them. The fields are still computed
for the ledgers (gate enum) but nothing shows them."""

import unittest
from unittest import mock

from forecast import flood_forecast_daily as ff
from forecast import rendering


def _forecast(with_acc=True):
    fc = {"confidence_level": "low", "confidence_reason": "should never render",
          "confidence_uncertainty_ft": 0.5, "peak_forecast_observed_mllw": 6.0,
          "accuracy_by_lead": {"window_days": 14, "n_total": 40, "n_tides": 9, "buckets": [
              {"label": "0-3 h before peak", "lo_h": 0, "hi_h": 3, "n": 12, "mae_ft": 0.11, "bias_ft": 0.01},
              {"label": "12-24 h", "lo_h": 12, "hi_h": 24, "n": 20, "mae_ft": 0.2, "bias_ft": -0.05},
              {"label": "24-48 h", "lo_h": 24, "hi_h": 48, "n": 8, "mae_ft": 0.28, "bias_ft": -0.1}]}
          if with_acc else {"window_days": 14, "n_total": 0, "n_tides": 0, "buckets": []}}
    return fc


class ConfidencePhaseOutTests(unittest.TestCase):
    def test_summary_text_shows_error_not_label(self):
        lines = rendering._render_summary_text(_forecast())
        joined = "\n".join(lines)
        self.assertNotIn("Confidence", joined)
        self.assertNotIn("LOW", joined)
        self.assertIn("Forecast error so far", joined)
        self.assertIn("0-3 h ±0.11 ft (n=12)", joined)

    def test_summary_html_shows_error_not_label(self):
        html = rendering._render_summary_html(_forecast())
        self.assertNotIn("Confidence:", html)
        self.assertNotIn("confidence-low", html)
        self.assertIn("tldr-accuracy", html)
        self.assertIn("±0.20 ft", html)

    def test_no_data_is_stated_plainly(self):
        line = ff.format_accuracy_line(_forecast(with_acc=False))
        self.assertIn("no scored tides", line)
        self.assertNotIn("confidence", line.lower())

    def test_accuracy_for_lead_picks_bucket(self):
        fc = _forecast()
        self.assertEqual(ff.accuracy_for_lead(fc, 1.5)["label"], "0-3 h before peak")
        self.assertEqual(ff.accuracy_for_lead(fc, 30.0)["mae_ft"], 0.28)
        self.assertIsNone(ff.accuracy_for_lead(fc, 60.0))       # no bucket scored
        self.assertIsNone(ff.accuracy_for_lead(fc, None))

    def test_summary_builder_shapes_the_table_from_leadtime_accuracy(self):
        lt = {"n_total": 5, "n_tides": 2, "buckets": [
            {"label": "3-6 h", "n": 3, "mean_err_ft": -0.04, "mean_abs_err_ft": 0.123},
            {"label": "6-12 h", "n": 0, "mean_err_ft": 0.0, "mean_abs_err_ft": 0.0}]}
        with mock.patch.object(ff, "_compute_leadtime_accuracy", return_value=lt):
            acc = ff._accuracy_by_lead_summary()
        self.assertEqual(len(acc["buckets"]), 1)
        self.assertEqual(acc["buckets"][0], {"label": "3-6 h", "lo_h": 3, "hi_h": 6, "n": 3,
                                             "mae_ft": 0.123, "bias_ft": -0.04})
        with mock.patch.object(ff, "_compute_leadtime_accuracy", side_effect=OSError("no log")):
            self.assertEqual(ff._accuracy_by_lead_summary()["buckets"], [])

    def test_ledger_label_is_still_computed(self):
        # gate enum for predictions_log / forecast_accuracy still needs a level
        fc = {"surge_source": "surge-persistence", "peak_forecast_observed_mllw": 6.0,
              "surge_swing_6h_ft": 0.1, "all_tides": [], "cold_lockout": False}
        with mock.patch.object(ff, "_compute_leadtime_accuracy", return_value=None), \
                mock.patch.object(ff, "update_forecast_accuracy", return_value=None), \
                mock.patch.object(ff, "load_monthly_peak_percentile", return_value={}), \
                mock.patch.object(ff, "plain_language_summary", return_value="x"), \
                mock.patch.object(ff, "_compute_regime_band", return_value=None):
            ff._attach_summary_and_confidence(fc)
        self.assertIn(fc["confidence_level"], ("low", "medium", "high"))
        self.assertEqual(fc["accuracy_by_lead"]["buckets"], [])


if __name__ == "__main__":
    unittest.main()
