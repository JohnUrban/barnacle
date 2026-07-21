import unittest
from unittest import mock

from forecast import flood_forecast_daily as ff


class AccuracyReportingTests(unittest.TestCase):
    def test_classifier_reports_decision_metrics_and_dry_baseline(self):
        rows = [
            {"date": "2026-01-01", "observed": 6.50, "regime": "street"},
            {"date": "2026-01-10", "observed": 6.10, "regime": "street"},
            {"date": "2026-01-20", "observed": 6.50, "regime": "dry"},
            {"date": "2026-01-30", "observed": 6.10, "regime": "dry"},
        ]
        with mock.patch.object(ff, "_load_accuracy_rows", return_value=rows):
            metrics = ff._compute_classifier_metrics()

        self.assertEqual(
            {key: metrics[key] for key in ("tp", "fp", "fn", "tn")},
            {"tp": 1, "fp": 1, "fn": 1, "tn": 1},
        )
        self.assertEqual(metrics["precision"], 0.5)
        self.assertEqual(metrics["recall"], 0.5)
        self.assertEqual(metrics["always_dry_accuracy"], 0.5)
        self.assertEqual(metrics["balanced_accuracy"], 0.5)
        self.assertEqual(metrics["sample_days"], 30)
        self.assertAlmostEqual(metrics["false_alerts_per_30_days"], 30.44 / 30)

    def test_accuracy_html_leads_with_skill_not_raw_accuracy(self):
        summary = {
            "n_scored_recent": 4,
            "mean_error_ft": 0.1,
            "mean_abs_error_ft": 0.2,
            "max_abs_error_ft": 0.3,
            "n_scored_total": 4,
        }
        rows = [
            {
                "date": "2026-01-01",
                "predicted": 6.5,
                "observed": 6.5,
                "error": 0.0,
                "regime": "street",
            },
            {
                "date": "2026-01-30",
                "predicted": 6.5,
                "observed": 6.1,
                "error": 0.4,
                "regime": "street",
            },
        ]
        with mock.patch.object(ff, "_load_accuracy_rows", return_value=rows), \
             mock.patch.object(ff, "_load_outcome_depth_rows", return_value=[]), \
             mock.patch.object(ff, "_compute_leadtime_accuracy", return_value=None):
            html = ff._render_accuracy_html({"accuracy_summary": summary})

        self.assertIn("Flood recall", html)
        self.assertIn("Alert precision", html)
        self.assertIn("always-predict-dry", html)
        self.assertLess(html.index("Flood-alert skill"), html.index("Peak-height error"))


if __name__ == "__main__":
    unittest.main()
