import unittest
from pathlib import Path

from forecast import check_artifacts
from forecast import flood_forecast_daily as ff


ROOT = Path(check_artifacts.ROOT)


class ModelVersionTests(unittest.TestCase):
    def test_production_constants_are_stamped_v0_10_3(self):
        self.assertEqual(ff.CURRENT_MODEL_VERSION, "v0.10.3")
        self.assertEqual(ff.TANK_K, 1.296e6)
        self.assertEqual(ff.TANK_GAMMA, 0.78)
        self.assertEqual(ff.TANK_KOUT, 3.50)
        self.assertEqual(ff.TANK_LAG_MIN, 15)

    def test_current_spec_and_readmes_match_source_stamp(self):
        version = ff.CURRENT_MODEL_VERSION
        spec = ROOT / "model" / f"{version}.md"
        self.assertTrue(spec.exists())
        self.assertIn(
            f"Flood Prediction Model {version}", spec.read_text(encoding="utf-8")
        )
        self.assertTrue((ROOT / "model" / "archive" / "v0.10.md").exists())
        self.assertFalse((ROOT / "model" / "v0.10.md").exists())
        self.assertTrue((ROOT / "model" / "archive" / "v0.10.1.md").exists())
        self.assertFalse((ROOT / "model" / "v0.10.1.md").exists())
        self.assertTrue((ROOT / "model" / "archive" / "v0.10.2.md").exists())
        self.assertFalse((ROOT / "model" / "v0.10.2.md").exists())
        self.assertIn(
            f"model/{version}.md", (ROOT / "README.md").read_text(encoding="utf-8")
        )
        self.assertIn(
            f"`{version}`",
            (ROOT / "data" / "predictions_log_README.md").read_text(
                encoding="utf-8"
            ),
        )

    def test_gate_reads_same_model_stamp(self):
        self.assertEqual(
            check_artifacts.source_model_version(), ff.CURRENT_MODEL_VERSION
        )

    def test_driveway_threshold_is_distinct_from_road_map_point(self):
        driveway = next(row for row in ff.LANDMARKS if row[0] == "driveway_central")
        self.assertEqual(driveway[2], 4.67)
        self.assertIn("threshold", driveway[1].lower())
        self.assertIn("cross-fit", driveway[1].lower())

        map_rows = (ROOT / "assets" / "map_points.csv").read_text(
            encoding="utf-8"
        ).splitlines()
        self.assertTrue(
            any(row.startswith("driveway_road_central,") for row in map_rows)
        )
        self.assertFalse(any(row.startswith("driveway_central,") for row in map_rows))

        widget = (ROOT / "docs" / "barnacle-widget.js").read_text(encoding="utf-8")
        self.assertIn('const WIDGET_VERSION = "v7.28a";', widget)
        self.assertIn('"Driveway entry · cross-fit"', widget)


if __name__ == "__main__":
    unittest.main()
